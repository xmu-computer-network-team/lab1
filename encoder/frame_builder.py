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
from common.config import FRAME_WIDTH, FRAME_HEIGHT, MAX_RAW_BYTES, QR_VERSION, QR_BOX_SIZE, QR_BORDER
from encoder.file_splitter import split_file

ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_L

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

def build_qr_frames(data: bytes) -> list[np.ndarray]:
    return [make_qr_frame(b64) for b64 in split_file(data)]
