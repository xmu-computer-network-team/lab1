#!/usr/bin/env python3
"""
frame_builder_test.py — 标准 QR 帧生成器测试

用法:
  python test/frame_builder_test.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import cv2
from encoder.frame_builder import (
    make_qr_frame, split_file, build_qr_frames,
    MAX_RAW_BYTES, HEADER_SIZE, QR_VERSION, QR_BOX_SIZE
)
from decoder.frame_assembler import FrameAssembler, parse_frame
from pyzbar.pyzbar import decode, ZBarSymbol
import hashlib


OUT_DIR = "test/frame_builder_test_attachments"


def test_make_qr_frame_returns_correct_shape():
    """测试1: make_qr_frame 返回 (1080, 1920) 灰度图"""
    b64_dummy = b'A=='  # 最小有效 Base64
    frame = make_qr_frame(b64_dummy)
    assert isinstance(frame, np.ndarray), f"应返回 np.ndarray, 实际 {type(frame)}"
    assert frame.shape == (1080, 1920), f"尺寸应为 (1080, 1920), 实际 {frame.shape}"
    assert frame.dtype == np.uint8, f"dtype 应为 uint8, 实际 {frame.dtype}"
    print("PASS: test_make_qr_frame_returns_correct_shape")


def test_make_qr_frame_white_border():
    """测试2: QR 帧四周应为白色（白边）"""
    b64_dummy = b'A=='
    frame = make_qr_frame(b64_dummy)
    # 边角应为 255（白色）
    assert frame[0, 0] == 255, "左上角应为白色"
    assert frame[0, 1919] == 255, "右上角应为白色"
    assert frame[1079, 0] == 255, "左下角应为白色"
    assert frame[1079, 1919] == 255, "右下角应为白色"
    print("PASS: test_make_qr_frame_white_border")


def test_split_file_single_frame():
    """测试3: 小文件（< MAX_RAW_BYTES）应生成单帧"""
    data = b'Hello VLC!' * 50  # ~600 bytes
    frames = split_file(data)
    assert len(frames) == 1, f"小文件应生成1帧，实际{len(frames)}帧"
    print("PASS: test_split_file_single_frame")


def test_split_file_large():
    """测试4: 大文件应生成多帧"""
    data = b'X' * (MAX_RAW_BYTES * 2 + 100)
    frames = split_file(data)
    assert len(frames) == 3, f"大文件应生成3帧，实际{len(frames)}帧"
    print("PASS: test_split_file_large")


def test_split_file_random_binary():
    """测试5: 随机二进制数据分段正确"""
    import random
    data = bytes(random.randint(0, 255) for _ in range(10000))
    frames = split_file(data)
    assert len(frames) > 1, "随机数据应生成多帧"
    # 验证每帧 Base64 编码长度一致（除了最后一帧）
    lens = [len(f) for f in frames]
    assert lens[-1] <= lens[0], "最后一帧应<=其他帧"
    print(f"PASS: test_split_file_random_binary ({len(frames)} frames)")


def test_frame_decodes_with_pyzbar():
    """测试6: 生成的帧能被 pyzbar 正确解码"""
    data = b'Test VLC ' * 100
    frames_raw = split_file(data)
    for raw in frames_raw:
        frame = make_qr_frame(raw)
        result = decode(frame, symbols=[ZBarSymbol.QRCODE])
        assert result, "pyzbar 应能解码帧"
        assert bytes(result[0].data) == raw, "解码数据应与原始 Base64 完全一致"
    print("PASS: test_frame_decodes_with_pyzbar")


def test_end_to_end_small_file():
    """测试7: 小文件端到端 roundtrip（MD5 比对）"""
    data = b'Test VLC ' * 100
    frames_raw = split_file(data)
    decoded_raw = [bytes(decode(make_qr_frame(f), symbols=[ZBarSymbol.QRCODE])[0].data)
                   for f in frames_raw]

    assembler = FrameAssembler()
    for raw in decoded_raw:
        if assembler.add(raw):
            break
    result = assembler.assemble()
    assert result == data, f"roundtrip 失败: {len(result)} != {len(data)}"
    print("PASS: test_end_to_end_small_file")


def test_end_to_end_large_random():
    """测试8: 大随机文件端到端 roundtrip"""
    import random
    data = bytes(random.randint(0, 255) for _ in range(50000))
    frames_raw = split_file(data)
    decoded_raw = [bytes(decode(make_qr_frame(f), symbols=[ZBarSymbol.QRCODE])[0].data)
                   for f in frames_raw]

    assembler = FrameAssembler()
    for raw in decoded_raw:
        if assembler.add(raw):
            break
    result = assembler.assemble()
    assert result == data, "大文件 roundtrip 失败"
    print(f"PASS: test_end_to_end_large_random ({len(frames_raw)} frames, {len(data)} bytes)")


def test_parse_frame_header():
    """测试9: parse_frame 正确解析帧头"""
    data = b'A' * 1000
    frames_raw = split_file(data)
    raw = frames_raw[0]
    info = parse_frame(raw)
    assert 'seg_id' in info
    assert 'frame_id' in info
    assert 'frame_count' in info
    assert 'total_segs' in info
    assert 'payload_length' in info
    assert 'crc' in info
    assert 'payload' in info
    assert info['payload_length'] <= MAX_RAW_BYTES
    print("PASS: test_parse_frame_header")


def test_visual_save():
    """测试10: 保存可视化 QR 帧"""
    os.makedirs(OUT_DIR, exist_ok=True)
    data = b'VLC Test Frame ' * 50
    frames = build_qr_frames(data)
    for i, frame in enumerate(frames[:3]):
        out = os.path.join(OUT_DIR, f"qr_frame_{i:02d}.png")
        cv2.imwrite(out, frame)
    print(f"PASS: test_visual_save — {min(3, len(frames))} frames saved to {OUT_DIR}/")


# ==================== 主入口 ====================

if __name__ == "__main__":
    tests = [
        test_make_qr_frame_returns_correct_shape,
        test_make_qr_frame_white_border,
        test_split_file_single_frame,
        test_split_file_large,
        test_split_file_random_binary,
        test_frame_decodes_with_pyzbar,
        test_end_to_end_small_file,
        test_end_to_end_large_random,
        test_parse_frame_header,
        test_visual_save,
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
