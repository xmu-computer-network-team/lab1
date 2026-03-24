#!/usr/bin/env python3
"""
locator_test.py — 标准 QR 解码器测试

验证策略:
- 用 frame_builder 生成的帧验证 decode_qr_frame 能正确解码
- 用真实照片验证 pyzbar 在实际场景中的表现

用法:
  python test/locator_test.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

from encoder.frame_builder import make_qr_frame, split_file
from decoder.locator import decode_qr_frame
from decoder.frame_assembler import FrameAssembler


OUT_DIR = "test/locator_test_attachments"


def test_decode_qr_frame_basic():
    """测试1: decode_qr_frame 能正确解码生成的 QR 帧"""
    data = b'Test VLC frame data'
    frames_raw = split_file(data)
    for raw in frames_raw:
        frame = make_qr_frame(raw)
        result = decode_qr_frame(frame)
        assert result is not None, "应能解码"
        assert bytes(result) == raw, "解码数据应与原始 Base64 一致"
    print("PASS: test_decode_qr_frame_basic")


def test_decode_qr_frame_random_data():
    """测试2: 随机二进制数据帧能被正确解码"""
    import random
    data = bytes(random.randint(0, 255) for _ in range(5000))
    frames_raw = split_file(data)
    assembler = FrameAssembler()
    for raw in frames_raw:
        frame = make_qr_frame(raw)
        result = decode_qr_frame(frame)
        assert result is not None, "随机数据帧应能解码"
        assembler.add(bytes(result))
        if assembler.assemble() == data:
            break
    assert assembler.assemble() == data, "随机数据 roundtrip 失败"
    print("PASS: test_decode_qr_frame_random_data")


def test_decode_qr_frame_no_qr():
    """测试3: 无 QR 码的图片应返回 None"""
    black_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    result = decode_qr_frame(black_img)
    assert result is None, "纯黑图应返回 None"
    print("PASS: test_decode_qr_frame_no_qr")


def test_decode_qr_frame_grayscale_input():
    """测试4: 直接输入灰度图也能解码"""
    data = b'Gray input test'
    frames_raw = split_file(data)
    raw = frames_raw[0]
    frame = make_qr_frame(raw)
    # make_qr_frame 已返回灰度图，直接传给 decode_qr_frame 验证灰度输入路径
    result = decode_qr_frame(frame)
    assert result is not None, "灰度图输入应能解码"
    assert bytes(result) == raw, "解码数据应一致"
    print("PASS: test_decode_qr_frame_grayscale_input")



# ==================== 主入口 ====================

if __name__ == "__main__":
    tests = [
        test_decode_qr_frame_basic,
        test_decode_qr_frame_random_data,
        test_decode_qr_frame_no_qr,
        test_decode_qr_frame_grayscale_input,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__} — {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"结果: {passed} passed, {failed} failed, {len(tests)} total")
    if failed > 0:
        sys.exit(1)
