# test/frame_reader_test.py
#
# frame_reader.py 的验收测试
# 使用方法: 在 lab1/ 目录下运行
#   python test/frame_reader_test.py
#
# 注意: 测试会临时生成视频文件，测试完自动删除

import sys
import os
import tempfile
import numpy as np
import cv2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from decoder.frame_reader import read_frames, get_video_info


def _make_test_video(path, n_frames=5, width=1920, height=1080, fps=24.0):
    """辅助函数: 生成一个测试视频"""
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
    for i in range(n_frames):
        val = (i * 50) % 256
        frame = np.full((height, width, 3), val, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_read_frames_basic():
    """测试1: 能正常读取视频并返回帧"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        _make_test_video(path, n_frames=3)
        frames = list(read_frames(path))
        assert len(frames) == 3, f"期望 3 帧, 实际 {len(frames)} 帧"
    finally:
        os.unlink(path)
    print("PASS: test_read_frames_basic")


def test_read_frames_is_generator():
    """测试2: read_frames 应返回生成器，不是列表"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        _make_test_video(path, n_frames=2)
        result = read_frames(path)
        import types
        assert isinstance(result, types.GeneratorType), \
            f"应返回生成器, 实际返回 {type(result).__name__}"
    finally:
        os.unlink(path)
    print("PASS: test_read_frames_is_generator")


def test_read_frames_shape():
    """测试3: 每帧应为 BGR 三通道，shape=(H, W, 3)"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        _make_test_video(path, n_frames=1, width=1920, height=1080)
        frames = list(read_frames(path))
        frame = frames[0]
        assert frame.ndim == 3, f"帧应为 3 维, 实际 {frame.ndim} 维"
        assert frame.shape[2] == 3, f"第 3 维应为 3 (BGR), 实际 {frame.shape[2]}"
        assert frame.dtype == np.uint8, f"dtype 应为 uint8, 实际 {frame.dtype}"
    finally:
        os.unlink(path)
    print("PASS: test_read_frames_shape")


def test_read_frames_frame_count():
    """测试4: 读出的帧数应与写入的一致"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        n = 10
        _make_test_video(path, n_frames=n)
        frames = list(read_frames(path))
        assert len(frames) == n, f"期望 {n} 帧, 实际 {len(frames)} 帧"
    finally:
        os.unlink(path)
    print("PASS: test_read_frames_frame_count")


def test_read_frames_file_not_found():
    """测试5: 文件不存在应抛 FileNotFoundError"""
    try:
        list(read_frames("/tmp/definitely_not_exist_12345.avi"))
        assert False, "应抛出 FileNotFoundError 但没有抛出"
    except FileNotFoundError:
        pass
    print("PASS: test_read_frames_file_not_found")


def test_read_frames_not_modify():
    """测试6: read_frames 不应修改帧（不做灰度化等处理）"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        _make_test_video(path, n_frames=1)
        frames = list(read_frames(path))
        frame = frames[0]
        # BGR 三通道应存在，不应被转为单通道灰度
        assert len(frame.shape) == 3 and frame.shape[2] == 3, \
            "帧不应被转为灰度图，应保持 BGR 三通道原样输出"
    finally:
        os.unlink(path)
    print("PASS: test_read_frames_not_modify")


def test_get_video_info_basic():
    """测试7: get_video_info 返回正确的视频信息"""
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as f:
        path = f.name
    try:
        _make_test_video(path, n_frames=8, width=1920, height=1080, fps=24.0)
        info = get_video_info(path)

        assert isinstance(info, dict), f"应返回 dict, 实际 {type(info).__name__}"
        assert "frame_count" in info, "缺少 frame_count 键"
        assert "fps" in info, "缺少 fps 键"
        assert "width" in info, "缺少 width 键"
        assert "height" in info, "缺少 height 键"

        assert info["frame_count"] == 8, f"帧数期望 8, 实际 {info['frame_count']}"
        assert info["width"] == 1920, f"宽度期望 1920, 实际 {info['width']}"
        assert info["height"] == 1080, f"高度期望 1080, 实际 {info['height']}"
        assert abs(info["fps"] - 24.0) < 1.0, f"帧率期望约 24, 实际 {info['fps']}"
    finally:
        os.unlink(path)
    print("PASS: test_get_video_info_basic")


def test_get_video_info_file_not_found():
    """测试8: 文件不存在应抛 FileNotFoundError"""
    try:
        get_video_info("/tmp/definitely_not_exist_12345.avi")
        assert False, "应抛出 FileNotFoundError 但没有抛出"
    except FileNotFoundError:
        pass
    print("PASS: test_get_video_info_file_not_found")


if __name__ == "__main__":
    tests = [
        test_read_frames_basic,
        test_read_frames_is_generator,
        test_read_frames_shape,
        test_read_frames_frame_count,
        test_read_frames_file_not_found,
        test_read_frames_not_modify,
        test_get_video_info_basic,
        test_get_video_info_file_not_found,
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
