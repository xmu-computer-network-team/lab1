"""
locator.py — 标准 QR 码解码器

用 pyzbar 直接解码视频帧中的标准 QR 码，返回原始字节数据。
"""
import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol


def decode_qr_frame(img: np.ndarray) -> bytes | None:
    """
    解码视频帧中的 QR 码，返回原始字节数据。

    Args:
        img: BGR 图像（shape: H×W×3, dtype: uint8），
             或灰度图像（shape: H×W, dtype: uint8）

    Returns:
        解码后的原始字节数据，失败返回 None
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 先试原图
    decoded = decode(gray, symbols=[ZBarSymbol.QRCODE])
    if decoded:
        return decoded[0].data

    # 手机拍照时 QR 码相对整图较小，需要多尺度缩放检测
    h, w = gray.shape
    for scale in [0.5, 0.25, 0.125]:
        new_w = int(w * scale)
        new_h = int(h * scale)
        if new_w < 200 or new_h < 200:
            break
        scaled = cv2.resize(gray, (new_w, new_h))
        decoded = decode(scaled, symbols=[ZBarSymbol.QRCODE])
        if decoded:
            return decoded[0].data

    return None


class FrameLocator:
    """
    兼容旧接口（保留，方便后续扩展）。

    locate_and_rectify 返回解码后的字节列表（每帧一个 bytes）
    """

    def locate_and_rectify(self, raw_img: np.ndarray) -> list[bytes] | None:
        """
        解码原始图片中的 QR 码。

        Returns:
            包含所有解码数据的列表，每元素是一帧的 bytes。
            如果找不到 QR 码返回 None。
        """
        if len(raw_img.shape) == 3:
            gray = cv2.cvtColor(raw_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = raw_img

        decoded = decode(gray, symbols=[ZBarSymbol.QRCODE])
        if not decoded:
            return None

        return [d.data for d in decoded]
