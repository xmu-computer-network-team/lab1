import cv2
import numpy as np
from pyzbar.pyzbar import decode, ZBarSymbol
from common.config import (
    BLOCK_SIZE, FRAME_WIDTH, FRAME_HEIGHT,
    GRID_COLS, GRID_ROWS, FINDER_SIZE
)


class FrameLocator:
    def locate_and_rectify(self, raw_img: np.ndarray) -> np.ndarray | None:
        """
        输入原始图片，输出矫正后的灰度图（1920×1080），失败返回 None。
        """
        gray = raw_img
        if len(gray.shape) == 3:
            if gray.dtype != np.uint8:
                gray = gray.astype(np.uint8)
            if gray.shape[2] == 3:
                gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
            elif gray.shape[2] == 4:
                gray = cv2.cvtColor(gray, cv2.COLOR_BGRA2GRAY)
        elif len(gray.shape) == 2:
            if gray.dtype != np.uint8:
                gray = gray.astype(np.uint8)
        corners = self._detect_corners_multiscale(gray)
        if corners is None:
            return None
        return self._warp(gray, corners)

    def _detect_corners_multiscale(self, gray) -> list | None:
        """尝试多个尺度，返回四个角点坐标 [(x,y),...] 或 None"""
        scales = [0.1, 0.2, 0.3, 0.5, 1.0]
        for scale in scales:
            h, w = gray.shape
            if scale != 1.0:
                small = cv2.resize(gray, (int(w * scale), int(h * scale)))
            else:
                small = gray

            decoded = decode(small, symbols=[ZBarSymbol.QRCODE])
            if decoded:
                poly = decoded[0].polygon
                # pyzbar 返回顺序: 左上→右上→右下→左下
                # 缩放过则还原到原图尺度
                if scale != 1.0:
                    corners = [(int(p.x / scale), int(p.y / scale)) for p in poly]
                else:
                    corners = [(int(p.x), int(p.y)) for p in poly]
                return corners
        return None

    def _warp(self, gray, corners) -> np.ndarray:
        """四点到透视变换，返回矫正图"""
        BS = BLOCK_SIZE
        FS = FINDER_SIZE
        GC = GRID_COLS
        GR = GRID_ROWS

        src = np.float32(corners)
        # 四个目标角点: Finder Pattern 的中心位置
        dst = np.float32([
            [FS / 2 * BS,        FS / 2 * BS],        # 左上
            [(GC - FS / 2) * BS, FS / 2 * BS],        # 右上
            [(GC - FS / 2) * BS, (GR - FS / 2) * BS],  # 右下
            [FS / 2 * BS,        (GR - FS / 2) * BS],  # 左下
        ])

        M = cv2.getPerspectiveTransform(src, dst)
        result = cv2.warpPerspective(gray, M, (FRAME_WIDTH, FRAME_HEIGHT))
        return result
