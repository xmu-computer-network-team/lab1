# lab1/encoder/file_splitter.py
import base64
from common.crc import crc32
from common.config import MAX_RAW_BYTES

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
    max_raw = MAX_RAW_BYTES
    # 每个 segment 最多包含 255 帧
    seg_max_raw = max_raw * 255

    # 1. 按 segment 大小切分
    segments = []
    offset = 0
    while offset < len(data):
        seg_data = data[offset:offset + seg_max_raw]
        segments.append(seg_data)
        offset += len(seg_data)

    total_segs = len(segments)
    result = []

    # 2. 为每个 segment 生成带头信息的帧
    for seg_idx, seg_data in enumerate(segments):
        frames_in_seg = (len(seg_data) + max_raw - 1) // max_raw
        for frame_id in range(frames_in_seg):
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
            # header + payload 整体 Base64 编码
            b64_data = base64.b64encode(header + payload)
            result.append(b64_data)

    return result