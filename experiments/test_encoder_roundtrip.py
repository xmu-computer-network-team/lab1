#!/usr/bin/env python3
"""
实验0：编码器自检（简化版，跳过视频）

目的：确认 FrameBuilder 生成的帧内容正确。
- 用已知内容的测试数据生成帧
- 在内存中验证帧结构：finder patterns、分隔带、header、数据区
- 不读写视频文件
"""

import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAB1_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, LAB1_DIR)

import numpy as np
from encoder.frame_builder import FrameBuilder
from common.pattern import generate_finder_pattern, generate_align_pattern
from common.config import *


def test_template_structure():
    """验证模板：finder patterns 和 separators 在正确位置"""
    fb = FrameBuilder()
    frame = fb.template

    errors = []

    # Finder pattern 1: 左上角 (row=0, col=0)
    expected_block = generate_finder_pattern()
    for r in range(FINDER_SIZE):
        for c in range(FINDER_SIZE):
            x = c * BLOCK_SIZE
            y = r * BLOCK_SIZE
            actual = frame[y, x]
            exp = 255 if expected_block[r, c] == 1 else 0
            if actual != exp:
                errors.append(f"Finder TL mismatch at block ({r},{c}), pixel ({y},{x}): expected {exp}, got {actual}")

    # Finder pattern 2: 右上角 (row=0, col=GRID_COLS-FINDER_SIZE)
    for r in range(FINDER_SIZE):
        for c in range(FINDER_SIZE):
            x = (GRID_COLS - FINDER_SIZE + c) * BLOCK_SIZE
            y = r * BLOCK_SIZE
            actual = frame[y, x]
            exp = 255 if expected_block[r, c] == 1 else 0
            if actual != exp:
                errors.append(f"Finder TR mismatch at block ({r},{c}), pixel ({y},{x}): expected {exp}, got {actual}")

    # Finder pattern 3: 左下角 (row=GRID_ROWS-FINDER_SIZE, col=0)
    for r in range(FINDER_SIZE):
        for c in range(FINDER_SIZE):
            x = c * BLOCK_SIZE
            y = (GRID_ROWS - FINDER_SIZE + r) * BLOCK_SIZE
            actual = frame[y, x]
            exp = 255 if expected_block[r, c] == 1 else 0
            if actual != exp:
                errors.append(f"Finder BL mismatch at block ({r},{c}), pixel ({y},{x}): expected {exp}, got {actual}")

    # Alignment pattern: 右下角
    align_block = generate_align_pattern()
    for r in range(ALIGN_SIZE):
        for c in range(ALIGN_SIZE):
            x = (GRID_COLS - ALIGN_SIZE + c) * BLOCK_SIZE
            y = (GRID_ROWS - ALIGN_SIZE + r) * BLOCK_SIZE
            actual = frame[y, x]
            exp = 255 if align_block[r, c] == 1 else 0
            if actual != exp:
                errors.append(f"Align pattern mismatch at block ({r},{c}), pixel ({y},{x}): expected {exp}, got {actual}")

    # Separator rows: 白色行在 row=7 和 row=GRID_ROWS-8
    sep_row_top = (FINDER_SIZE) * BLOCK_SIZE
    sep_row_bot = (GRID_ROWS - 1 - FINDER_SIZE) * BLOCK_SIZE
    for c in range(GRID_COLS):
        x = c * BLOCK_SIZE
        if frame[sep_row_top, x] != 255:
            errors.append(f"Top separator row pixel ({sep_row_top},{x}) should be 255, got {frame[sep_row_top, x]}")
        if frame[sep_row_bot, x] != 255:
            errors.append(f"Bottom separator row pixel ({sep_row_bot},{x}) should be 255, got {frame[sep_row_bot, x]}")

    # Data area should be all zeros (black) in template
    data_row_start = FINDER_SIZE + SEPARATOR_WIDTH
    data_row_end = GRID_ROWS - FINDER_SIZE - SEPARATOR_WIDTH
    nonzero = 0
    for row in range(data_row_start, data_row_end):
        for col in range(GRID_COLS):
            x = col * BLOCK_SIZE
            y = row * BLOCK_SIZE
            if frame[y, x] != 0:
                nonzero += 1
    if nonzero > 0:
        errors.append(f"Data area in template should be all black, found {nonzero} non-zero pixels")

    if errors:
        print(f"FAIL - {len(errors)} errors:")
        for e in errors[:10]:
            print(f"  {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    else:
        print("PASS - Template structure correct")


def test_frame_id_difference():
    """验证不同 frame_id 生成的帧头不同"""
    fb = FrameBuilder()
    frame0 = fb.build_frame(0, [])
    frame1 = fb.build_frame(1, [])
    frame42 = fb.build_frame(42, [])

    # Header area: row=0, col=FINDER_SIZE..GRID_COLS-FINDER_SIZE
    # These should differ between different frame_ids
    diff_01 = np.sum(frame0[0, FINDER_SIZE*BLOCK_SIZE:(GRID_COLS-FINDER_SIZE)*BLOCK_SIZE] !=
                     frame1[0, FINDER_SIZE*BLOCK_SIZE:(GRID_COLS-FINDER_SIZE)*BLOCK_SIZE])
    diff_42 = np.sum(frame0[0, FINDER_SIZE*BLOCK_SIZE:(GRID_COLS-FINDER_SIZE)*BLOCK_SIZE] !=
                     frame42[0, FINDER_SIZE*BLOCK_SIZE:(GRID_COLS-FINDER_SIZE)*BLOCK_SIZE])

    if diff_01 == 0 or diff_42 == 0:
        print(f"FAIL - Different frame_ids produced identical or no header differences")
        print(f"  diff(0,1)={diff_01}, diff(0,42)={diff_42}")
    else:
        print(f"PASS - Different frame_ids produce different headers")
        print(f"  diff(0,1)={diff_01} pixels differ, diff(0,42)={diff_42} pixels differ")


def test_scan_order_direction():
    """验证 Z 字扫描方向正确：偶数行从左到右，奇数行从右到左"""
    fb = FrameBuilder()
    coords = fb.scan_order

    # 检查 data_row_start=8, data_row_end=127
    data_row_start = FINDER_SIZE + SEPARATOR_WIDTH  # 8
    data_row_end = GRID_ROWS - FINDER_SIZE - SEPARATOR_WIDTH  # 127

    errors = []
    # 验证相邻两行的方向相反
    for row in range(data_row_start, min(data_row_start + 10, data_row_end - 1)):
        row_coords = [(r, c) for r, c in coords if r == row]
        next_row_coords = [(r, c) for r, c in coords if r == row + 1]

        if len(row_coords) < 2 or len(next_row_coords) < 2:
            continue

        # 当前行方向
        cur_dir = row_coords[1][1] - row_coords[0][1]  # +1 = left-to-right, -1 = right-to-left
        # 下一行方向
        next_dir = next_row_coords[1][1] - next_row_coords[0][1]

        # 相邻行方向应该相反
        if cur_dir == next_dir:
            errors.append(f"Row {row} and row {row+1} have same direction ({cur_dir}), should be opposite")

    if errors:
        print(f"FAIL - Scan order direction errors:")
        for e in errors:
            print(f"  {e}")
    else:
        print(f"PASS - Scan order alternates direction correctly")


def test_data_write():
    """验证数据写入：将已知 bit 序列写入帧，读取回来"""
    fb = FrameBuilder()

    # 用 0x00..0xFF 重复填满一小块区域
    test_data = []
    for i in range(256):
        byte = i % 256
        bits = [(byte >> (7 - j)) & 1 for j in range(8)]
        test_data.extend(bits)

    # 只填前 256 bits
    frame = fb.build_frame(0, [])
    original = frame.copy()
    fb.write_bits_to_data_area(frame, test_data)

    # 读取回来
    recovered = []
    for idx, (row, col) in enumerate(fb.scan_order[:len(test_data)]):
        x = col * BLOCK_SIZE + BLOCK_SIZE // 2
        y = row * BLOCK_SIZE + BLOCK_SIZE // 2
        recovered.append(1 if frame[y, x] > 127 else 0)

    if recovered == test_data:
        print(f"PASS - Data write/read roundtrip correct ({len(test_data)} bits)")
    else:
        mismatches = sum(1 for i in range(len(test_data)) if recovered[i] != test_data[i])
        print(f"FAIL - {mismatches}/{len(test_data)} bits mismatch")
        # 找出前几个不匹配的位置
        for i in range(min(5, len(test_data))):
            if recovered[i] != test_data[i]:
                row, col = fb.scan_order[i]
                print(f"  bit[{i}] at ({row},{col}): expected {test_data[i]}, got {recovered[i]}")


def test_empty_segments():
    """验证空 segments 不会崩"""
    fb = FrameBuilder()
    try:
        frame = fb.build_frame(99, [])
        print(f"PASS - Empty segments handled (frame shape: {frame.shape})")
    except Exception as e:
        print(f"FAIL - Empty segments raised: {e}")


def run_tests():
    print("=" * 60)
    print("实验0：编码器自检")
    print("=" * 60)

    tests = [
        test_template_structure,
        test_frame_id_difference,
        test_scan_order_direction,
        test_data_write,
        test_empty_segments,
    ]

    passed = 0
    failed = 0
    for t in tests:
        print(f"\n[{t.__name__}]")
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"ERROR - {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"结果: {passed}/{passed+failed} 通过")
    if failed > 0:
        print("有测试失败，请检查编码器实现")


if __name__ == "__main__":
    run_tests()
