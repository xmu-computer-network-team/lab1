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
        self._segments: dict[int, dict[int, bytes]] = {}
        self._seg_meta: dict[int, int] = {}  # seg_id -> frame_count
        self._total_segs: int | None = None

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

        self._segments[seg_id][frame_id] = payload
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
