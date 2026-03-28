# calc_max_raw.py（也可以直接 python 里粘贴跑）
import qrcode, base64
from qrcode.exceptions import DataOverflowError
from common.config import QR_VERSION, QR_BOX_SIZE, QR_BORDER

def can_fit(raw_size: int) -> bool:
    header = b'\x00' * 10      # 10B 帧头
    payload = b'a' * raw_size  # 模拟数据
    b64 = base64.b64encode(header + payload)

    qr = qrcode.QRCode(
        version=QR_VERSION,                         # 用你想要的新版本
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER,
    )
    try:
        qr.add_data(b64)
        qr.make(fit=False)
        return True
    except DataOverflowError:
        return False

lo, hi = 1, 5000  # 上限可以按需要调大
while lo < hi:
    mid = (lo + hi + 1) // 2
    if can_fit(mid):
        lo = mid
    else:
        hi = mid - 1

print("Safe MAX_RAW_BYTES =", lo)