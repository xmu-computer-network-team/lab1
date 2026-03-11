# decoder/frame_reader.py
#
# 【任务说明】
# 本模块负责：把一个视频文件拆成逐帧的 numpy 数组。
# 仅此一个职责，不做任何图像处理（灰度化、二值化、矫正都是后续模块的事）。
#
# 【重要约束】
# - 使用 cv2.VideoCapture 读取视频
# - 输出的帧是 OpenCV 默认格式：BGR 彩色，shape=(H, W, 3)，dtype=uint8
# - 不要在这里做灰度转换或任何图像处理
# - 用生成器（yield）逐帧返回，不要一次性全部读入内存
#   （一个 1080p 视频 1000 帧 ≈ 6GB 内存，全读进来会爆）
#
# 【依赖】
# - opencv-python (cv2)
# - numpy
#
# 【验收标准】
# 运行 test/frame_reader_test.py 全部通过即合格

import cv2
import numpy as np


def read_frames(video_path: str):
    """从视频文件逐帧读取，返回生成器

    Args:
        video_path: 视频文件路径，例如 "input.avi"

    Yields:
        np.ndarray: BGR 彩色帧，shape=(H, W, 3)，dtype=uint8
        每次 yield 一帧，视频读完自动停止

    Raises:
        FileNotFoundError: 如果视频文件不存在
        RuntimeError: 如果视频文件存在但无法打开（格式不支持等）

    示例:
        >>> for frame in read_frames("input.avi"):
        ...     print(frame.shape)  # (1080, 1920, 3)
        ...     # 传给 locator.py 做后续处理

        >>> frames = list(read_frames("input.avi"))  # 也可以一次性收集
        >>> len(frames)  # 视频总帧数

    实现提示:
        1. 先用 os.path.exists() 检查文件是否存在，不存在抛 FileNotFoundError
        2. cap = cv2.VideoCapture(video_path)
        3. 检查 cap.isOpened()，失败则 raise RuntimeError
        4. while 循环: ret, frame = cap.read()，ret 为 False 时 break
        5. yield frame
        6. 循环结束后 cap.release()
    """
    # TODO: 请实现此函数
    raise NotImplementedError


def get_video_info(video_path: str) -> dict:
    """获取视频的基本信息（调试和验证用）

    Args:
        video_path: 视频文件路径

    Returns:
        dict，包含以下键：
        {
            "frame_count": int,    # 总帧数
            "fps": float,          # 帧率
            "width": int,          # 宽度（像素）
            "height": int,         # 高度（像素）
        }

    Raises:
        FileNotFoundError: 如果视频文件不存在
        RuntimeError: 如果视频文件存在但无法打开

    示例:
        >>> info = get_video_info("input.avi")
        >>> print(info)
        {'frame_count': 100, 'fps': 24.0, 'width': 1920, 'height': 1080}

    实现提示:
        1. 同样先检查文件存在，再 VideoCapture 打开
        2. 用 cap.get(cv2.CAP_PROP_FRAME_COUNT) 等获取属性
        3. 别忘了 cap.release()
    """
    # TODO: 请实现此函数
    raise NotImplementedError
