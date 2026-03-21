# encoder/frame_builder.py
import numpy as np
import cv2
from common.config import *
from common.pattern import generate_finder_pattern, generate_align_pattern

class FrameBuilder:
  

    def __init__(self):
       
        self.template = self._build_template()
        
        self.scan_order = self._build_scan_order()

    def _build_template(self) -> np.ndarray:
        
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)

        
        self._draw_finder(frame, 0, 0)                                    
        self._draw_finder(frame, 0, GRID_COLS - FINDER_SIZE)             
        self._draw_finder(frame, GRID_ROWS - FINDER_SIZE, 0)            

       
        ar = GRID_ROWS - ALIGN_SIZE
        ac = GRID_COLS - ALIGN_SIZE
        self._draw_align(frame, ar, ac)

       
        self._draw_separators(frame)

        return frame

    def _draw_finder(self, frame, row, col):
        """在 (row, col) 处画 7x7 的 Finder Pattern"""
       
        pattern = generate_finder_pattern()  
        for r in range(FINDER_SIZE):
            for c in range(FINDER_SIZE):
                x = (col + c) * BLOCK_SIZE
                y = (row + r) * BLOCK_SIZE
                color = 255 if pattern[r][c] == 1 else 0
                frame[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = color

    def _draw_align(self, frame, row, col):
       
        pattern = generate_align_pattern()  
        for r in range(ALIGN_SIZE):
            for c in range(ALIGN_SIZE):
                x = (col + c) * BLOCK_SIZE
                y = (row + r) * BLOCK_SIZE
                color = 255 if pattern[r][c] == 1 else 0
                frame[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = color

    def _draw_separators(self, frame):
        
        # 具体实现: 在 finder pattern 外围画一行/列白色块
        pass  # 根据实际布局实现

    def _build_scan_order(self) -> list:
        
        coords = []
        data_row_start = FINDER_SIZE + SEPARATOR_WIDTH      
        data_row_end = GRID_ROWS - FINDER_SIZE - SEPARATOR_WIDTH  
        for row in range(data_row_start, data_row_end):
            if (row - data_row_start) % 2 == 0:
                col_range = range(0, GRID_COLS)             
            else:
                col_range = range(GRID_COLS - 1, -1, -1)    
            for col in col_range:
                coords.append((row, col))
        return coords

    def build_frame(self, frame_id: int, segments: list) -> np.ndarray:
       
        frame = self.template.copy()

        # 1. 写入帧头
        header_bits = self._encode_header(frame_id, len(segments))
        self._write_bits_to_header_area(frame, header_bits)

        # 2. 写入数据段
        all_bits = []
        for seg in segments:
            all_bits.extend(seg)  # 每段已包含 data + CRC-32
        self._write_bits_to_data_area(frame, all_bits)

        return frame

    def _encode_header(self, frame_id, segment_count):
       
        bits = []
        bits.append(frame_id % 2)                           
        bits.extend(int_to_bits(frame_id, 12))             
        bits.extend(int_to_bits(segment_count, 16))        
        crc = crc8(bits)
        bits.extend(int_to_bits(crc, 8))                    
        return bits

    def _write_bits_to_data_area(self, frame, bits):
      
        for i, bit in enumerate(bits):
            if i >= len(self.scan_order):
                break
            row, col = self.scan_order[i]
            x = col * BLOCK_SIZE
            y = row * BLOCK_SIZE
            color = 255 if bit == 1 else 0
            frame[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = color


def int_to_bits(value, length):
    
    return [(value >> (length - 1 - i)) & 1 for i in range(length)]
