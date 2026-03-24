#!/usr/bin/env python3
"""
locator.py 的验收测试

验证策略:
- 用 experiments/input/ 中的真实拍摄照片验证 pyzbar 定位能力
- 用 FrameBuilder 生成帧来验证透视变换的正确性（绕过 pyzbar，直接注入角点）

用法:
  python test/locator_test.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import numpy as np

from encoder.frame_builder import FrameBuilder
from decoder.locator import FrameLocator
from common.config import FRAME_WIDTH, FRAME_HEIGHT, BLOCK_SIZE, FINDER_SIZE, GRID_COLS, GRID_ROWS


OUT_DIR = "test/locator_test_attachments"
os.makedirs(OUT_DIR, exist_ok=True)


def test_locator_pyzbar_on_real_photos():
    """测试1: 验证 pyzbar 能检测到真实拍摄照片中的 QR 码"""
    locator = FrameLocator()
    photo_dir = "experiments/input"
    found = 0
    total = 0
    for fname in sorted(os.listdir(photo_dir)):
        if not fname.endswith(('.jpg', '.png', '.jpeg')):
            continue
        img_path = os.path.join(photo_dir, fname)
        img = cv2.imread(img_path)
        if img is None:
            print(f"  ⚠ {fname}: 无法读取，跳过")
            continue
        total += 1
        result = locator.locate_and_rectify(img)
        if result is not None:
            found += 1
            out_path = os.path.join(OUT_DIR, f"real_{fname[:-4]}_corrected.png")
            cv2.imwrite(out_path, result)
        print(f"  {'✓' if result is not None else '✗'} {fname}: {'矫正成功' if result is not None else '未检测到'}")
    print(f"\n检测结果: {found}/{total}")
    assert found == total, f"应有 {total} 张全部检测成功，实际 {found} 张"
    print("PASS: test_locator_pyzbar_on_real_photos")


def test_locator_perspective_transform_accuracy():
    """测试2: 验证透视变换本身是正确的（绕过 pyzbar，直接注入角点）"""
    fb = FrameBuilder()
    frame = fb.build_frame(0, []).astype(np.uint8)
    margin = 40
    frame_padded = cv2.copyMakeBorder(
        frame, margin, margin, margin, margin,
        cv2.BORDER_CONSTANT, value=255
    )

    # 手动构造四个角点（Finder Pattern 中心在原图中的位置，加 margin 偏移）
    BS = BLOCK_SIZE
    FS = FINDER_SIZE
    GC = GRID_COLS
    GR = GRID_ROWS

    corners = [
        (int(FS / 2 * BS) + margin, int(FS / 2 * BS) + margin),  # 左上
        (int((GC - FS / 2) * BS) + margin, int(FS / 2 * BS) + margin),  # 右上
        (int((GC - FS / 2) * BS) + margin, int((GR - FS / 2) * BS) + margin),  # 右下
        (int(FS / 2 * BS) + margin, int((GR - FS / 2) * BS) + margin),  # 左下
    ]
    print(f"手动角点: {corners}")

    # 用 FrameLocator 的 _warp 方法
    locator = FrameLocator()
    corrected = locator._warp(frame_padded, corners)

    # 透视变换后直接得到 1920x1080，与原始帧对比
    corrected_crop = corrected
    orig = frame

    # PSNR
    mse = np.mean((orig.astype(np.float64) - corrected_crop.astype(np.float64)) ** 2)
    p = float('inf') if mse < 1e-10 else 20 * np.log10(255.0 / np.sqrt(mse))
    print(f"透视变换 PSNR: {p:.2f} dB")

    # 保存对比图
    side_by_side = np.hstack([orig, corrected_crop])
    diff = cv2.absdiff(orig, corrected_crop)
    cv2.imwrite(os.path.join(OUT_DIR, "warp_side_by_side.png"), side_by_side)
    cv2.imwrite(os.path.join(OUT_DIR, "warp_diff.png"), diff)
    print(f"透视变换对比图已保存至 {OUT_DIR}/")

    assert p > 40, f"透视变换 PSNR {p:.2f}dB 过低"
    print("PASS: test_locator_perspective_transform_accuracy")


def test_locator_no_qr_detected():
    """测试3: 无 QR 码的图片应返回 None"""
    locator = FrameLocator()
    black_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    result = locator.locate_and_rectify(black_img)
    assert result is None, "纯黑图应返回 None"
    print("PASS: test_locator_no_qr_detected")


# ==================== 主入口 ====================

if __name__ == "__main__":
    tests = [
        test_locator_pyzbar_on_real_photos,
        test_locator_perspective_transform_accuracy,
        test_locator_no_qr_detected,
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
    print(f"结果: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
