"""
frame_builder.py — 标准 QR 码帧生成器

帧格式（每帧 QR 数据区）:
    Base64([FrameHeader 10B][RawPayload])

FrameHeader (10 bytes, big-endian):
    [1B:  frames_in_segment]
    [1B:  total_segments]
    [2B:  payload_length]
    [4B:  CRC32]
    [1B:  frame_id]
    [1B:  segment_id]

整个 (header + payload) 用 Base64 编码后再存入 QR，
保证 QR 数据全是 ASCII 字符，避免高位字节被 UTF-8 误解码。
"""
import qrcode
import base64
import numpy as np
from common.crc import crc32


QR_VERSION = 37
QR_BOX_SIZE = 6
QR_BORDER = 1
ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_L

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080

# 最大原始数据字节数（V37 L级 + 整个帧 Base64 编码，实测）
MAX_RAW_BYTES = 1568
HEADER_SIZE = 10


def _make_qr_inner(data: bytes) -> np.ndarray:
    qr = qrcode.QRCode(
        version=QR_VERSION,
        error_correction=ERROR_CORRECTION,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    qr.add_data(data)
    qr.make(fit=False)
    img = qr.make_image(fill_color="black", back_color="white")
    return np.array(img.convert('L'))


def make_qr_frame(b64_encoded: bytes) -> np.ndarray:
    """
    将已 Base64 编码的数据转为 QR 帧图像。

    Args:
        b64_encoded: Base64 字符串（全是 ASCII 字符）
    """
    qr_img = _make_qr_inner(b64_encoded)

    frame = np.full((FRAME_HEIGHT, FRAME_WIDTH), 255, dtype=np.uint8)
    top = (FRAME_HEIGHT - qr_img.shape[0]) // 2
    left = (FRAME_WIDTH - qr_img.shape[1]) // 2
    frame[top:top + qr_img.shape[0], left:left + qr_img.shape[1]] = qr_img
    return frame


def _make_header(seg_id: int, frame_id: int, frame_count: int,
                  total_segs: int, payload_length: int, crc: int) -> bytes:
    return bytes([
        frame_count,
        total_segs,
        (payload_length >> 8) & 0xFF,
        payload_length & 0xFF,
    ]) + crc.to_bytes(4, 'big') + bytes([frame_id, seg_id])


def split_file(data: bytes) -> list[bytes]:
    """
    将文件分段，每段返回完整的 Base64 编码数据（可直接送入 make_qr_frame）。

    Returns:
        list of b64_encoded bytes
    """
    max_raw = MAX_RAW_BYTES
    seg_max_raw = max_raw * 255

    # 分 segment
    segments = []
    offset = 0
    while offset < len(data):
        seg_data = data[offset:offset + seg_max_raw]
        segments.append(seg_data)
        offset += len(seg_data)

    total_segs = len(segments)
    result = []

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


def build_qr_frames(data: bytes) -> list[np.ndarray]:
    return [make_qr_frame(b64) for b64 in split_file(data)]
