import common.pattern
import numpy as np
from common.config import *

class FrameBuilder:
    def __init__(self):
        self.template = self.build_template()

    def build_template(self) -> np.ndarray:
        frame = np.zeros((FRAME_HEIGHT,FRAME_WIDTH))

        #左三侧pattern
        self.draw_pattern(frame,0,0,common.pattern.generate_finder_pattern(),FINDER_SIZE)
        self.draw_pattern(frame,0,GRID_COLS - FINDER_SIZE,common.pattern.generate_finder_pattern(),FINDER_SIZE) #右上
        self.draw_pattern(frame,GRID_ROWS - FINDER_SIZE, 0, common.pattern.generate_finder_pattern(),FINDER_SIZE) #左下

        # 右下
        self.draw_pattern(frame,GRID_ROWS - ALIGN_SIZE,GRID_COLS - ALIGN_SIZE,common.pattern.generate_align_pattern(),ALIGN_SIZE)

        # 画分隔带
        self.draw_separators(frame)
        
        return frame



    def draw_pattern(self, frame, row, col, pattern, SIZE):
        #外黑内白中间3x3黑
        for r in range(SIZE):
            for c in range(SIZE):
                x = (col + c) * BLOCK_SIZE
                y = (row + r) * BLOCK_SIZE
                color = 0 if pattern[r][c] == 1 else 255
                frame[y:y+BLOCK_SIZE,x:x+BLOCK_SIZE] = color

    def draw_separators(self, frame):
        for c in range(GRID_COLS):
            x = c * BLOCK_SIZE
            y1 = (0 + FINDER_SIZE) * BLOCK_SIZE
            y2 = ((GRID_ROWS - 1) - FINDER_SIZE) * BLOCK_SIZE
            frame[y1:y1+BLOCK_SIZE,x:x+BLOCK_SIZE] = 255 
            frame[y2:y2+BLOCK_SIZE,x:x+BLOCK_SIZE] = 255 
    
    def build_scan_order(self) -> list:
        coords = []
        data_row_start = FINDER_SIZE + SEPARATOR_WIDTH
        data_row_end = GRID_ROWS - FINDER_SIZE - SEPARATOR_WIDTH

        for row in range(data_row_start, data_row_end):
            if (row - data_row_end) % 2 == 0:
                col_range = range(0,GRID_COLS)
            else:
                col_range = range(GRID_COLS - 1, -1, -1)
            for col in col_range:
                coords.append((row,col))
        return coords