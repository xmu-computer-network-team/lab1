import zlib

def crc32(data: bytes) -> int: 
    return zlib.crc32(data) & 0xFFFFFFFF


def crc8(bits: list) -> int:
    """计算 CRC-8 校验值（基于 bit 列表输入）

    使用 CRC-8/ITU 标准，生成多项式 0x07 (x^8 + x^2 + x + 1)

    算法步骤（逐 bit 计算）:
        1. 初始化 crc = 0x00
        2. 对输入的每一个 bit:
           a. 把 crc 左移 1 位，最低位填入当前 bit
           b. 如果左移后 crc 的第 8 位（bit 8）为 1:
              说明溢出了 8 位范围，需要做一次"除法"
              crc ^= 0x107  (0x107 = 0b1_0000_0111，即 x^8 + x^2 + x + 1)
           c. crc &= 0xFF  (只保留低 8 位)
        3. 返回 crc

    Args:
        bits: 由 0 和 1 组成的列表，例如 [1, 0, 1, 1, 0, ...]
              在本项目中是帧头的前 29 bits（奇偶位 + 帧号 + 数据长度）
    """
    # TODO: 请实现此函数
    crc = 0x00
    extended_bits = bits + [0, 0, 0, 0, 0, 0, 0, 0]
    for bit in extended_bits:
        crc = (crc << 1) | bit
        if crc & 0x100:
            crc ^= 0x107
        crc &= 0xFF
    
    return crc
