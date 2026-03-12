import common.pattern
import numpy as np
from common.config import *
from common.crc import *

class FrameBuilder:
    def __init__(self):
        self.template = self.build_template()
        self.scan_order = self.build_scan_order()

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
                color = 255 if pattern[r][c] == 1 else 0
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

    def write_bits_to_data_area(self, frame, bits):
        for i, bit in enumerate(bits):
            if i >= len(self.scan_order):
                break ## 文件分段如果正确实现，不会出现bit比容量多
            row, col = self.scan_order[i]
            x = col * BLOCK_SIZE
            y = row * BLOCK_SIZE
            color = 255 if bit == 1 else 0
            frame[y:y+BLOCK_SIZE,x : x+BLOCK_SIZE] = color 

    def write_bits_to_header_area(self, frame, bits):
        start_col = FINDER_SIZE
        end_col = GRID_COLS - FINDER_SIZE  # 不覆盖右侧 Finder
        row = 0

        for i, bit in enumerate(bits):
            col = start_col + i
            if col >= end_col:
                break
            x = col * BLOCK_SIZE
            y = row * BLOCK_SIZE
            color = 255 if bit == 1 else 0
            frame[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = color

    def encoder_header(self, frame_id, segment_count):
        bits = []
        bits.append(frame_id % 2)

        bits.extend(self.int_to_bits(frame_id,12))
        bits.extend(self.int_to_bits(segment_count,16))
        crc = crc8(bits)
        bits.extend(self.int_to_bits(crc,8))
        return bits            

    def int_to_bits(self, value, length):
        """整数转固定长度 bit 列表 (MSB first)。

        返回长度为 `length` 的 0/1 列表；超出位会被截断。
        """
        bits = []
        for i in range(length):
            bits.append((value >> (length - 1 - i)) & 1)
        return bits

    def build_frame(self, frame_id: list,segments: list) -> np.ndarray:
        """
        segment 字节列表
        """
        frame = self.template.copy()

        header_bits = self.encoder_header(frame_id,len(segments))
        self.write_bits_to_header_area(frame,header_bits)

        all_bits = []
        for seg in segments:
            all_bits.extend(seg)
        self.write_bits_to_data_area(frame,all_bits)

        return frame