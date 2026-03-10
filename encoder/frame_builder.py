import common.pattern
from common.config import *

class FrameBuilder:
    def __init__(self):
        pass 

    def draw_pattern(self, frame, row, col, pattern, SIZE):
        #外黑内白中间3x3黑
        for r in range(SIZE):
            for c in range(SIZE):
                x = (col + c) * BLOCK_SIZE
                y = (row + r) * BLOCK_SIZE
                color = 255 if pattern[r][c] == 1 else 0
                frame[y:y+BLOCK_SIZE,x:x+BLOCK_SIZE] = color