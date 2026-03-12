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
    # 校验帧列表非空
    if not frames:
        raise ValueError("Frames list cannot be empty")
    
    # 创建MJPG编码的fourcc（必须使用MJPG避免帧间压缩）
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')
    
    # 初始化VideoWriter，参数从配置文件读取
    writer = cv2.VideoWriter(
        output_path,
        fourcc,
        FPS,
        (FRAME_WIDTH, FRAME_HEIGHT)
    )
    
    # 检查VideoWriter是否成功打开
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open VideoWriter for output path: {output_path}")
    
    try:
        # 遍历所有帧，转换为BGR并写入（OpenCV不支持单通道）
        for frame in frames:
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            writer.write(bgr_frame)
    finally:
        # 确保资源释放，即使发生异常
        writer.release()


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
        self.output_path = output_path
        self._writer = None  # 视频写入器实例（在__enter__中初始化）
        self.frame_count = 0  # 已写入的帧数统计

    def __enter__(self):
        """打开 VideoWriter，返回 self

        Raises:
            RuntimeError: 如果 VideoWriter 打开失败
        """
        # 创建MJPG编码的fourcc
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        
        # 初始化VideoWriter
        self._writer = cv2.VideoWriter(
            self.output_path,
            fourcc,
            FPS,
            (FRAME_WIDTH, FRAME_HEIGHT)
        )
        
        # 检查VideoWriter是否成功打开
        if not self._writer.isOpened():
            raise RuntimeError(f"Failed to open VideoWriter for output path: {self.output_path}")
        
        return self

    def write_frame(self, frame: np.ndarray) -> None:
        """写入一帧

        Args:
            frame: 灰度图，shape=(FRAME_HEIGHT, FRAME_WIDTH)，dtype=uint8

        Raises:
            RuntimeError: 如果 writer 未打开（没在 with 块中使用）
        """
        # 检查写入器是否已正确打开
        if self._writer is None or not self._writer.isOpened():
            raise RuntimeError("VideoWriter is not opened. Please use 'with' statement to initialize it first.")
        
        # 灰度转BGR三通道
        bgr_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        
        # 写入帧并更新计数
        self._writer.write(bgr_frame)
        self.frame_count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        """释放 VideoWriter 资源（上下文管理器自动调用）"""
        # 确保资源释放，即使发生异常
        if self._writer is not None:
            self._writer.release()
            self._writer = None  # 清空引用，避免重复释放
