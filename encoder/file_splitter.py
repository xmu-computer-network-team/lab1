# lab1/encoder/file_splitter.py
import base64
from common.crc import crc32
from common.config import MAX_RAW_BYTES


def _ceil_div(a: int, b: int) -> int:
    return (a + b - 1) // b

def _make_header(seg_id: int, frame_id: int, frame_count: int,
                  total_segs: int, payload_length: int, crc: int) -> bytes:
    """创建 10 字节的帧头。"""
    return bytes([
        frame_count,
        total_segs,
        (payload_length >> 8) & 0xFF,
        payload_length & 0xFF,
    ]) + crc.to_bytes(4, 'big') + bytes([frame_id, seg_id])


def split_file(data: bytes) -> list[bytes]:
    """
    将文件分段，每段返回完整的 Base64 编码数据（可直接送入 make_qr_frame）。

    帧格式: Base64([FrameHeader 10B][RawPayload])

    Returns:
        list of b64_encoded bytes
    """
    return list(iter_b64_frames(data))


def iter_b64_frames(data: bytes, max_frames: int | None = None):
    """流式产出 Base64 编码帧（可用于限帧/避免一次性生成大列表）。

    Args:
        data: 原始文件字节
        max_frames: 最多产出多少帧；None 表示不限制

    Yields:
        每帧对应的 b64_encoded bytes
    """
    if not data:
        return

    max_raw = MAX_RAW_BYTES
    seg_max_raw = max_raw * 255
    total_segs = _ceil_div(len(data), seg_max_raw)

    frames_yielded = 0
    for seg_idx in range(total_segs):
        seg_start = seg_idx * seg_max_raw
        seg_data = data[seg_start:seg_start + seg_max_raw]
        frames_in_seg = _ceil_div(len(seg_data), max_raw)

        for frame_id in range(frames_in_seg):
            if max_frames is not None and frames_yielded >= max_frames:
                return

            start = frame_id * max_raw
            payload = seg_data[start:start + max_raw]
            crc_val = crc32(payload)
            header = _make_header(
                seg_id=seg_idx,
                frame_id=frame_id,
                frame_count=frames_in_seg,
                total_segs=total_segs,
                payload_length=len(payload),
                crc=crc_val,
            )
            yield base64.b64encode(header + payload)
            frames_yielded += 1