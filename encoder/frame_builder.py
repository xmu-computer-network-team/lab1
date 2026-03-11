import common.pattern
import numpy as np
from common.config import *

class FrameBuilder:
    def __init__(self):
        pass 

    def build_template(self) -> np.ndarray:
        frame = np.zeros((FRAME_HEIGHT,FRAME_WIDTH))

        #左三侧pattern
        self.draw_pattern(frame,0,0,common.pattern.generate_finder_pattern,7)
            



    def draw_pattern(self, frame, row, col, pattern, SIZE):
        #外黑内白中间3x3黑
        for r in range(SIZE):
            for c in range(SIZE):
                x = (col + c) * BLOCK_SIZE
                y = (row + r) * BLOCK_SIZE
                color = 255 if pattern[r][c] == 1 else 0
                frame[y:y+BLOCK_SIZE,x:x+BLOCK_SIZE] = color