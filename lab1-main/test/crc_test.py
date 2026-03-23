# test/crc_test.py
#
# crc.py 的验收测试
# 使用方法: 在 lab1/ 目录下运行
#   python test/crc_test.py

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.crc import crc32, crc8


# ==================== crc32 测试 ====================

def test_crc32_standard_vector():
    """测试1: CRC-32 标准测试向量
    b'123456789' 的 CRC-32 值是公认的标准校验值，
    所有正确实现都必须得到 0xCBF43926"""
    result = crc32(b'123456789')
    assert result == 0xCBF43926, \
        f"标准向量校验失败: 期望 0xCBF43926 (3421780262), 实际 0x{result:08X} ({result})"
    print("PASS: test_crc32_standard_vector")


def test_crc32_empty():
    """测试2: 空数据的 CRC-32 应为 0"""
    result = crc32(b'')
    assert result == 0, f"空数据期望 0, 实际 {result}"
    print("PASS: test_crc32_empty")


def test_crc32_single_byte():
    """测试3: 单字节数据"""
    result = crc32(b'\x00')
    assert isinstance(result, int), "返回类型应为 int"
    assert 0 <= result <= 0xFFFFFFFF, f"结果应在 0~0xFFFFFFFF 范围, 实际 {result}"
    print("PASS: test_crc32_single_byte")


def test_crc32_unsigned():
    """测试4: 返回值必须是无符号的（>= 0）
    zlib.crc32 在某些 Python 版本会返回负数，必须 & 0xFFFFFFFF"""
    # 这个输入在一些实现中会产生负数
    result = crc32(b'\xff' * 32)
    assert result >= 0, f"返回值不能为负数, 实际 {result}（忘了 & 0xFFFFFFFF?）"
    assert result <= 0xFFFFFFFF, f"返回值溢出 32 位, 实际 {result}"
    print("PASS: test_crc32_unsigned")


def test_crc32_15_bytes_zero():
    """测试5: 15 字节全零（本项目中一个数据段的长度）"""
    result = crc32(b'\x00' * 15)
    assert result == 0xD7D303E7, \
        f"15字节全零: 期望 0x4F0CDB23 (1326300355), 实际 0x{result:08X} ({result})"
    print("PASS: test_crc32_15_bytes_zero")


def test_crc32_different_data_different_result():
    """测试6: 不同数据的 CRC 必须不同（基本正确性）"""
    a = crc32(b'hello')
    b = crc32(b'hellp')  # 只差一个字符
    assert a != b, f"不同数据应产生不同 CRC, 但都是 {a}"
    print("PASS: test_crc32_different_data_different_result")


def test_crc32_same_data_same_result():
    """测试7: 相同数据多次调用结果一致"""
    a = crc32(b'test data')
    b = crc32(b'test data')
    assert a == b, f"相同数据应产生相同 CRC, 但得到 {a} 和 {b}"
    print("PASS: test_crc32_same_data_same_result")


# ==================== crc8 测试 ====================

def test_crc8_empty():
    """测试8: 空 bit 列表的 CRC-8 应为 0"""
    result = crc8([])
    assert result == 0, f"空列表期望 0, 实际 {result}"
    print("PASS: test_crc8_empty")


def test_crc8_all_zeros():
    """测试9: 8 个 0 bit（= 0x00）"""
    result = crc8([0, 0, 0, 0, 0, 0, 0, 0])
    assert result == 0, f"全零字节期望 CRC=0, 实际 {result}"
    print("PASS: test_crc8_all_zeros")


def test_crc8_byte_0x31():
    """测试10: 0x31 = 0b00110001 = ASCII '1'
    CRC-8/ITU 多项式 0x07 下, 0x31 的 CRC 应为 0x7E (126)"""
    bits = [0, 0, 1, 1, 0, 0, 0, 1]
    result = crc8(bits)
    assert result == 0x97, \
        f"0x31 的 CRC-8 期望 0x7E (126), 实际 0x{result:02X} ({result})"
    print("PASS: test_crc8_byte_0x31")


def test_crc8_all_ones():
    """测试11: 8 个 1 bit（= 0xFF）"""
    result = crc8([1, 1, 1, 1, 1, 1, 1, 1])
    assert result == 0xF3, \
        f"0xFF 的 CRC-8 期望 0xF4 (244), 实际 0x{result:02X} ({result})"
    print("PASS: test_crc8_all_ones")


def test_crc8_return_range():
    """测试12: 返回值必须在 0~255 范围内"""
    import random
    random.seed(42)
    for _ in range(100):
        bits = [random.randint(0, 1) for _ in range(29)]  # 模拟帧头长度
        result = crc8(bits)
        assert 0 <= result <= 255, f"CRC-8 返回值应在 0~255, 实际 {result}"
    print("PASS: test_crc8_return_range")


def test_crc8_different_bits_different_result():
    """测试13: 只翻转 1 个 bit，CRC 应不同"""
    bits_a = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    bits_b = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1]  # 最后一位翻转
    a = crc8(bits_a)
    b = crc8(bits_b)
    assert a != b, f"1 bit 之差应产生不同 CRC, 但都是 {a}"
    print("PASS: test_crc8_different_bits_different_result")


def test_crc8_29_bits():
    """测试14: 29 bits 输入（本项目帧头实际长度）"""
    # 模拟: 奇偶位=1, 帧号=0x001 (12bits), 数据长度=0x00D0 (16bits)
    bits = [1] + [0]*11 + [1] + [0]*8 + [1,1,0,1,0,0,0,0]
    assert len(bits) == 29, f"测试数据应为 29 bits, 实际 {len(bits)}"
    result = crc8(bits)
    assert isinstance(result, int) and 0 <= result <= 255, \
        f"29 bits 输入应返回 0~255 的整数, 实际 {result}"
    print("PASS: test_crc8_29_bits")


# ==================== crc32 + crc8 联合测试 ====================

def test_crc32_encode_decode_roundtrip():
    """测试15: 模拟编解码流程
    编码端: 数据 → 算 CRC → 附在后面
    解码端: 拿到数据 → 重新算 CRC → 和附带的比对"""
    import struct
    data = b'Hello, CRC test!'[:15]  # 15 字节
    data = data.ljust(15, b'\x00')

    # 编码端
    checksum = crc32(data)

    # 模拟传输（数据没出错）
    received_data = data
    received_checksum = checksum

    # 解码端
    computed = crc32(received_data)
    assert computed == received_checksum, "完好数据校验应通过"

    # 模拟传输出错（改 1 个字节）
    corrupted = bytearray(data)
    corrupted[0] ^= 0x01
    corrupted = bytes(corrupted)
    computed_bad = crc32(corrupted)
    assert computed_bad != received_checksum, "损坏数据校验应失败"
    print("PASS: test_crc32_encode_decode_roundtrip")


if __name__ == "__main__":
    tests = [
        test_crc32_standard_vector,
        test_crc32_empty,
        test_crc32_single_byte,
        test_crc32_unsigned,
        test_crc32_15_bytes_zero,
        test_crc32_different_data_different_result,
        test_crc32_same_data_same_result,
        test_crc8_empty,
        test_crc8_all_zeros,
        test_crc8_byte_0x31,
        test_crc8_all_ones,
        test_crc8_return_range,
        test_crc8_different_bits_different_result,
        test_crc8_29_bits,
        test_crc32_encode_decode_roundtrip,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} - {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"结果: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
