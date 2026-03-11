# encoder/video_writer.py
#
# 【任务说明】
# 本模块负责：把一系列 numpy 灰度帧图像写入一个视频文件。
# 仅此一个职责，不涉及编码逻辑。
#
# 【重要约束】
# - 视频编码必须用 MJPG（fourcc = 'MJPG'），不能用 H.264/H.265，
#   因为它们的帧间压缩会破坏二维码的像素细节
# - 灰度帧（单通道）写入前需要转为 BGR 三通道，OpenCV VideoWriter 不接受单通道
# - 所有参数（分辨率、帧率）从 common/config.py 读取，不要硬编码数字
#
# 【依赖】
# - opencv-python (cv2)
# - numpy
# - common/config.py 中的 FRAME_WIDTH, FRAME_HEIGHT, FPS
#
# 【验收标准】
# 运行 test/test_video_writer.py 全部通过即合格

import cv2
import numpy as np
from common.config import FRAME_WIDTH, FRAME_HEIGHT, FPS


def frames_to_video(frames: list, output_path: str) -> None:
    """将帧列表一次性写入视频文件（简单接口，帧少时用）

    Args:
        frames: 灰度帧列表，每个元素是 np.ndarray，
                shape=(FRAME_HEIGHT, FRAME_WIDTH)，dtype=uint8，单通道
        output_path: 输出视频文件路径，例如 "output.avi"

    Returns:
        None

    Raises:
        ValueError: 如果 frames 为空
        RuntimeError: 如果 VideoWriter 打开失败

    示例:
        >>> import numpy as np
        >>> black = np.zeros((1080, 1920), dtype=np.uint8)
        >>> white = np.full((1080, 1920), 255, dtype=np.uint8)
        >>> frames_to_video([black, white, black], "test.avi")
        # 生成一个 3 帧的视频

    实现提示:
        1. 校验 frames 非空
        2. 用 cv2.VideoWriter_fourcc(*'MJPG') 创建 fourcc
        3. 创建 cv2.VideoWriter(output_path, fourcc, FPS, (FRAME_WIDTH, FRAME_HEIGHT))
        4. 检查 writer.isOpened()，失败则 raise RuntimeError
        5. 遍历 frames，每帧用 cv2.cvtColor 转 GRAY→BGR 后 writer.write()
        6. 最后 writer.release()
    """
    # TODO: 请实现此函数
    raise NotImplementedError


class VideoWriterContext:
    """支持逐帧写入的视频写入器（帧多时用，节省内存）

    用法:
        >>> with VideoWriterContext("output.avi") as vw:
        ...     for frame in frame_generator():
        ...         vw.write_frame(frame)
        >>> print(vw.frame_count)  # 查看写入了多少帧

    实现提示:
        - __init__: 保存 output_path，初始化 self._writer = None, self.frame_count = 0
        - __enter__: 创建 cv2.VideoWriter（fourcc='MJPG'），检查 isOpened()，返回 self
        - write_frame: 灰度转BGR，调用 self._writer.write()，frame_count += 1
        - __exit__: 调用 self._writer.release()
    """

    def __init__(self, output_path: str):
        """
        Args:
            output_path: 输出视频文件路径
        """
        # TODO: 请实现
        raise NotImplementedError

    def __enter__(self):
        """打开 VideoWriter，返回 self

        Raises:
            RuntimeError: 如果 VideoWriter 打开失败
        """
        # TODO: 请实现
        raise NotImplementedError

    def write_frame(self, frame: np.ndarray) -> None:
        """写入一帧

        Args:
            frame: 灰度图，shape=(FRAME_HEIGHT, FRAME_WIDTH)，dtype=uint8

        Raises:
            RuntimeError: 如果 writer 未打开（没在 with 块中使用）
        """
        # TODO: 请实现
        raise NotImplementedError

    def __exit__(self, exc_type, exc_val, exc_tb):
        """释放 VideoWriter 资源"""
        # TODO: 请实现
        raise NotImplementedError
