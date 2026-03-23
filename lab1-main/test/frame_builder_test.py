# test/frame_builder_test.py
#
# encoder/frame_builder.py 的验收测试
# 使用方法: 在 lab1/ 目录下运行
#   python test/frame_builder_test.py
#
# 可视化输出会保存到 test/frame_builder_test_attachments/

import sys
import os
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from encoder.frame_builder import FrameBuilder
from common.config import FRAME_HEIGHT, FRAME_WIDTH, GRID_ROWS, GRID_COLS, FINDER_SIZE, SEPARATOR_WIDTH

import matplotlib.pyplot as plt

#测试
'''print(f"!!! 调试信息：读取到的配置 -> WIDTH: {FRAME_WIDTH}, HEIGHT: {FRAME_HEIGHT}")
if FRAME_WIDTH != FRAME_HEIGHT:
    print("!!! 警告：配置的宽高不相等，生成的帧将是长方形！")

OUT_DIR = "test/frame_builder_test_attachments"
'''


def _make_segments(total_bits: int) -> list:
    """辅助函数: 生成指定总比特数的 segment 列表（每 segment 8bit，模拟一字节）"""
    segments = []
    for i in range(total_bits // 8):
        byte_val = i & 0xFF
        bits = [(byte_val >> (7 - b)) & 1 for b in range(8)]
        segments.append(bits)
    return segments


def _data_capacity() -> int:
    """每帧数据区最大比特容量"""
    data_row_start = FINDER_SIZE + SEPARATOR_WIDTH
    data_row_end = GRID_ROWS - FINDER_SIZE - SEPARATOR_WIDTH
    return (data_row_end - data_row_start) * GRID_COLS


# ==================== 测试函数 ====================

def test_build_frame_returns_ndarray():
    """测试1: build_frame 应返回 numpy.ndarray"""
    fb = FrameBuilder()
    segments = _make_segments(64)
    frame = fb.build_frame(0, segments)
    assert isinstance(frame, np.ndarray), \
        f"返回类型应为 np.ndarray, 实际为 {type(frame).__name__}"
    print("PASS: test_build_frame_returns_ndarray")


def test_build_frame_shape():
    """测试2: 返回帧的尺寸应为 (FRAME_HEIGHT, FRAME_WIDTH)"""
    fb = FrameBuilder()
    segments = _make_segments(64)
    frame = fb.build_frame(0, segments)
    assert frame.shape == (FRAME_HEIGHT, FRAME_WIDTH), \
        f"帧尺寸期望 ({FRAME_HEIGHT}, {FRAME_WIDTH}), 实际 {frame.shape}"
    print("PASS: test_build_frame_shape")


def test_build_frame_pixel_values_binary():
    """测试3: 所有像素值应为 0 或 255 (纯黑白帧)"""
    fb = FrameBuilder()
    segments = _make_segments(128)
    frame = fb.build_frame(1, segments)
    unique_vals = set(np.unique(frame).tolist())
    assert unique_vals <= {0, 255}, \
        f"像素值应只含 0 和 255, 实际出现了 {unique_vals - {0, 255}}"
    print("PASS: test_build_frame_pixel_values_binary")


def test_build_frame_does_not_modify_template():
    """测试4: build_frame 不应修改内部模板 (template 应保持不变)"""
    fb = FrameBuilder()
    template_before = fb.template.copy()
    segments = _make_segments(256)
    fb.build_frame(3, segments)
    assert np.array_equal(fb.template, template_before), \
        "build_frame 不应修改 fb.template"
    print("PASS: test_build_frame_does_not_modify_template")


def test_build_frame_different_ids_differ():
    """测试5: 不同 frame_id 应在 header 区生成不同的帧"""
    fb = FrameBuilder()
    segments = _make_segments(128)
    frame0 = fb.build_frame(0, segments)
    frame1 = fb.build_frame(1, segments)
    assert not np.array_equal(frame0, frame1), \
        "frame_id 不同时，生成的帧应有差异（header 区应不同）"
    print("PASS: test_build_frame_different_ids_differ")


def test_build_frame_overflow_bits_safe():
    """测试6: 当 segments 的总 bit 数超过数据区容量时，不应抛出异常"""
    fb = FrameBuilder()
    capacity = _data_capacity()
    # 提供 2 倍容量的 bits
    segments = _make_segments((capacity // 8 + 1) * 8 * 2)
    try:
        fb.build_frame(0, segments)
    except Exception as e:
        assert False, f"超出容量时不应抛异常, 实际抛出: {e}"
    print("PASS: test_build_frame_overflow_bits_safe")


def test_build_4_frames_visual():
    """测试7 (可视化): 生成 4 帧并保存为 PNG，直观验证帧结构"""
    os.makedirs(OUT_DIR, exist_ok=True)
    fb = FrameBuilder()

    # 准备数据: 用递增字节填充，每帧用不同的 segments 以便区分
    capacity_bits = _data_capacity()
    # 每帧填一整页数据（按容量）
    base_segments = _make_segments(capacity_bits)

    frame_count = 0
    MAX_FRAMES = 4

    for frame_id in range(MAX_FRAMES):
        if frame_count >= MAX_FRAMES:
            break

        # 用不同偏移让每帧数据不同
        shifted = base_segments[frame_id:] + base_segments[:frame_id]
        frame = fb.build_frame(frame_id, shifted)

        out_path = os.path.join(OUT_DIR, f"frame_{frame_id:02d}.png")
        plt.imsave(out_path, frame, cmap="gray", vmin=0, vmax=255)
        frame_count += 1

    assert frame_count == MAX_FRAMES, \
        f"期望生成 {MAX_FRAMES} 帧, 实际生成 {frame_count} 帧"
    print(f"PASS: test_build_4_frames_visual — 已保存 {MAX_FRAMES} 帧至 {OUT_DIR}/")


# ==================== 主入口 ====================

if __name__ == "__main__":
    tests = [
        test_build_frame_returns_ndarray,
        test_build_frame_shape,
        test_build_frame_pixel_values_binary,
        test_build_frame_does_not_modify_template,
        test_build_frame_different_ids_differ,
        test_build_frame_overflow_bits_safe,
        test_build_4_frames_visual,
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
