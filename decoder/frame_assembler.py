"""
frame_assembler.py — 文件重组器

帧格式:
    Base64([FrameHeader 10B][RawPayload])

FrameHeader (10 bytes):
    [1B:  frames_in_segment]
    [1B:  total_segments]
    [2B:  payload_length (big-endian)]
    [4B:  CRC32]
    [1B:  frame_id]
    [1B:  segment_id]
"""
import base64
from common.crc import crc32


HEADER_SIZE = 10


def parse_frame(raw: bytes) -> dict:
    """解析帧: 先 Base64 解码，再拆帧头"""
    try:
        decoded = base64.b64decode(raw)
    except Exception:
        raise ValueError(f"Invalid Base64")

    if len(decoded) < HEADER_SIZE:
        raise ValueError(f"Frame too short: {len(decoded)} < {HEADER_SIZE}")

    hdr = decoded[:HEADER_SIZE]
    payload = decoded[HEADER_SIZE:]

    frame_count = hdr[0]
    total_segs = hdr[1]
    payload_length = int.from_bytes(hdr[2:4], 'big')
    crc = int.from_bytes(hdr[4:8], 'big')
    frame_id = hdr[8]
    seg_id = hdr[9]

    return {
        'seg_id': seg_id,
        'frame_id': frame_id,
        'frame_count': frame_count,
        'total_segs': total_segs,
        'payload_length': payload_length,
        'crc': crc,
        'payload': payload,
    }


class FrameAssembler:
    def __init__(self):
        # 已通过 CRC 校验并缓存的载荷，按 seg_id -> frame_id -> payload 存储
        self._segments: dict[int, dict[int, bytes]] = {}
        # 每个 segment 的帧总数（来自帧头）
        self._seg_meta: dict[int, int] = {}  # seg_id -> frame_count
        # 总 segment 数（来自帧头）
        self._total_segs: int | None = None

        # 记录每个 (seg_id, frame_id) 对应的 payload_length，方便后续在缺帧时估算长度
        self._payload_lengths: dict[tuple[int, int], int] = {}
        # 所有已知帧中的最大 payload_length，作为缺失帧长度的兜底值
        self._max_payload_length: int = 0

        # 统计信息：被成功接收并通过 CRC 校验的帧数
        self._accepted_frames: int = 0

    def add(self, raw: bytes) -> bool:
        info = parse_frame(raw)
        seg_id = info['seg_id']
        frame_id = info['frame_id']
        frame_count = info['frame_count']
        total_segs = info['total_segs']
        payload_length = info['payload_length']
        crc = info['crc']
        payload = info['payload']

        if self._total_segs is None:
            self._total_segs = total_segs
        elif self._total_segs != total_segs:
            return False

        if seg_id not in self._segments:
            self._segments[seg_id] = {}
            self._seg_meta[seg_id] = frame_count
        elif self._seg_meta[seg_id] != frame_count:
            return False

        if len(payload) != payload_length:
            print(f"Length mismatch: decoded={len(payload)}, expected={payload_length}")
            return False

        if crc32(payload) != crc:
            print(f"CRC mismatch: frame {frame_id}/seg {seg_id}")
            return False

        # 记录该帧的载荷长度信息
        key = (seg_id, frame_id)
        self._payload_lengths[key] = payload_length
        if payload_length > self._max_payload_length:
            self._max_payload_length = payload_length

        # 缓存通过校验的 payload
        self._segments[seg_id][frame_id] = payload
        self._accepted_frames += 1
        return self._is_complete()

    def _is_complete(self) -> bool:
        if self._total_segs is None:
            return False
        for seg_id in range(self._total_segs):
            if seg_id not in self._segments:
                return False
            if len(self._segments[seg_id]) < self._seg_meta[seg_id]:
                return False
        return True

    def assemble(self) -> bytes | None:
        if self._total_segs is None or not self._segments:
            return None

        result = b''
        for seg_id in range(self._total_segs):
            if seg_id not in self._segments:
                return None
            for frame_id in range(self._seg_meta[seg_id]):
                if frame_id not in self._segments[seg_id]:
                    return None
                result += self._segments[seg_id][frame_id]
        return result


    def assemble_with_mask(self) -> tuple[bytes, bytes] | None:
        """组装数据并生成与之对齐的有效性掩码。

        返回:
            (data, mask) 或 None

        约定:
            - data: 按 seg_id、frame_id 顺序拼接的载荷字节流；
              对于缺失或校验失败的帧，会用 0x00 填充与预期 payload_length
              等长的占位字节。
            - mask: 与 data 等长的字节流，逐比特标记有效性：
              * 0xFF 表示该字节的 8 个比特都来自通过 CRC 的真实数据；
              * 0x00 表示该字节对应“弃权位”（缺帧/坏帧的填充），不参与
                有效位和错误位统计。

        注意:
            - 如果整体信息极少（例如几乎没收到任何合法帧），则返回 None。
            - 当某个 seg 完全缺失时，后续 seg 不再尝试填充，返回此前能
              确定长度的前缀部分。
        """

        if self._total_segs is None or not self._segments:
            return None

        result = bytearray()
        mask = bytearray()

        # 为每个 frame_id 预聚合一个“全局预期长度”，用于缺失帧兜底
        frame_len_global: dict[int, int] = {}
        for (seg_id, frame_id), length in self._payload_lengths.items():
            prev = frame_len_global.get(frame_id)
            if prev is None or length < prev:
                # 理论上同一 frame_id 在不同 seg 中长度应一致，
                # 取较小值更安全，避免溢出原始长度。
                frame_len_global[frame_id] = length

        for seg_id in range(self._total_segs):
            frame_count = self._seg_meta.get(seg_id)
            if frame_count is None:
                # 完整缺失的 segment：后续内容长度难以可靠推断，
                # 直接终止，返回当前已组装的前缀。
                break

            seg_frames = self._segments.get(seg_id, {})

            for frame_id in range(frame_count):
                payload = seg_frames.get(frame_id)
                key = (seg_id, frame_id)

                if payload is not None:
                    result.extend(payload)
                    mask.extend(b"\xFF" * len(payload))
                    continue

                # 缺失或损坏的帧：根据已有信息估算预期长度
                expected_len = self._payload_lengths.get(key)
                if expected_len is None:
                    expected_len = frame_len_global.get(frame_id)
                if expected_len is None:
                    expected_len = self._max_payload_length

                if expected_len and expected_len > 0:
                    # 用 0 填充数据，用 0 掩码标记为“弃权位”
                    result.extend(b"\x00" * expected_len)
                    mask.extend(b"\x00" * expected_len)

        if not result:
            return None

        return bytes(result), bytes(mask)
