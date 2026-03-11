# test/test_video_writer.py
#
# video_writer.py 的验收测试
# 使用方法: 在 lab1/ 目录下运行
#   python -m pytest test/test_video_writer.py -v
# 或者直接:
#   python test/test_video_writer.py

import sys
import os
import tempfile
import numpy as np
import cv2

# 让 import 能找到项目模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.config import FRAME_WIDTH, FRAME_HEIGHT, FPS
from encoder.video_writer import frames_to_video, VideoWriterContext


def make_test_frames(n=5):
    """生成 n 帧测试用灰度图（交替黑白）"""
    frames = []
    for i in range(n):
        val = 0 if i % 2 == 0 else 255
        frame = np.full((FRAME_HEIGHT, FRAME_WIDTH), val, dtype=np.uint8)
        frames.append(frame)
    return frames


def test_frames_to_video_basic():
    """测试1: frames_to_video 能正常生成视频文件"""
    frames = make_test_frames(3)
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        frames_to_video(frames, path)
        assert os.path.exists(path), "视频文件未生成"
        assert os.path.getsize(path) > 0, "视频文件为空"
    finally:
        os.unlink(path)
    print("PASS: test_frames_to_video_basic")


def test_frames_to_video_frame_count():
    """测试2: 生成的视频帧数正确"""
    n = 10
    frames = make_test_frames(n)
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        frames_to_video(frames, path)
        cap = cv2.VideoCapture(path)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        assert count == n, f"期望 {n} 帧，实际 {count} 帧"
    finally:
        os.unlink(path)
    print("PASS: test_frames_to_video_frame_count")


def test_frames_to_video_resolution():
    """测试3: 视频分辨率与 config 一致"""
    frames = make_test_frames(1)
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        frames_to_video(frames, path)
        cap = cv2.VideoCapture(path)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        assert w == FRAME_WIDTH, f"宽度期望 {FRAME_WIDTH}，实际 {w}"
        assert h == FRAME_HEIGHT, f"高度期望 {FRAME_HEIGHT}，实际 {h}"
    finally:
        os.unlink(path)
    print("PASS: test_frames_to_video_resolution")


def test_frames_to_video_empty_raises():
    """测试4: 空列表应该抛 ValueError"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        frames_to_video([], path)
        assert False, "应该抛出 ValueError 但没有抛出"
    except ValueError:
        pass  # 期望行为
    finally:
        if os.path.exists(path):
            os.unlink(path)
    print("PASS: test_frames_to_video_empty_raises")


def test_context_manager_basic():
    """测试5: VideoWriterContext 基本写入"""
    frames = make_test_frames(5)
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        with VideoWriterContext(path) as vw:
            for frame in frames:
                vw.write_frame(frame)
        assert vw.frame_count == 5, f"frame_count 期望 5，实际 {vw.frame_count}"

        cap = cv2.VideoCapture(path)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        assert count == 5, f"视频帧数期望 5，实际 {count}"
    finally:
        os.unlink(path)
    print("PASS: test_context_manager_basic")


def test_context_manager_releases_on_exception():
    """测试6: with 块中抛异常时 VideoWriter 应正常释放"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        try:
            with VideoWriterContext(path) as vw:
                vw.write_frame(make_test_frames(1)[0])
                raise RuntimeError("模拟异常")
        except RuntimeError:
            pass
        # 关键：文件应该存在且至少写了 1 帧
        assert os.path.exists(path), "异常后文件应该存在"
        assert vw.frame_count == 1, f"frame_count 期望 1，实际 {vw.frame_count}"
    finally:
        if os.path.exists(path):
            os.unlink(path)
    print("PASS: test_context_manager_releases_on_exception")


def test_pixel_values_preserved():
    """测试7: 写入后读回的像素值大致正确（MJPG有轻微压缩损失，允许误差）"""
    # 生成一帧：左半黑，右半白
    frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)
    frame[:, FRAME_WIDTH // 2:] = 255

    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        frames_to_video([frame], path)
        cap = cv2.VideoCapture(path)
        ret, read_frame = cap.read()
        cap.release()
        assert ret, "无法读取视频帧"

        gray = cv2.cvtColor(read_frame, cv2.COLOR_BGR2GRAY)
        left_mean = np.mean(gray[:, :FRAME_WIDTH // 4])
        right_mean = np.mean(gray[:, 3 * FRAME_WIDTH // 4:])
        # MJPG 有压缩损失，放宽到 ±30
        assert left_mean < 30, f"左侧均值应接近 0，实际 {left_mean:.1f}"
        assert right_mean > 225, f"右侧均值应接近 255，实际 {right_mean:.1f}"
    finally:
        os.unlink(path)
    print("PASS: test_pixel_values_preserved")


if __name__ == "__main__":
    tests = [
        test_frames_to_video_basic,
        test_frames_to_video_frame_count,
        test_frames_to_video_resolution,
        test_frames_to_video_empty_raises,
        test_context_manager_basic,
        test_context_manager_releases_on_exception,
        test_pixel_values_preserved,
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
