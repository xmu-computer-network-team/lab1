# decoder/grid_sampler.py
import numpy as np
from common.config import *

class GridSampler:
   

    def sample(self, corrected_gray: np.ndarray):
       
        bits = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.uint8)
        confidences = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.float32)

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                # 采样块中心的 3x3 区域取均值，比单像素更稳定
                cy = row * BLOCK_SIZE + BLOCK_SIZE // 2
                cx = col * BLOCK_SIZE + BLOCK_SIZE // 2
                region = corrected_gray[cy-1:cy+2, cx-1:cx+2]
                value = float(np.mean(region))

                # 判定 bit 值和置信度
                if value < BLACK_THRESHOLD:
                    bits[row, col] = 0
                    confidences[row, col] = (BLACK_THRESHOLD - value) / BLACK_THRESHOLD
                elif value > WHITE_THRESHOLD:
                    bits[row, col] = 1
                    confidences[row, col] = (value - WHITE_THRESHOLD) / (255 - WHITE_THRESHOLD)
                else:
                    # 灰色地带: 硬判但置信度低
                    bits[row, col] = 0 if value < 128 else 1
                    confidences[row, col] = abs(value - 128) / 128 * 0.5

        return bits, confidences
