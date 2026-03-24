#!/usr/bin/env python3
"""
encode.py — 文件 → QR 视频编码器

用法:
  python encode.py <input_file> <output_video>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from encoder.frame_builder import build_qr_frames
from encoder.video_writer import VideoWriterContext
from common.config import FPS, FRAME_WIDTH, FRAME_HEIGHT


def encode_file(input_path: str, output_path: str) -> None:
    data = open(input_path, 'rb').read()
    print(f"Encoding {len(data)} bytes ({len(data) / 1024:.1f} KB)")

    frames = build_qr_frames(data)
    print(f"Generated {len(frames)} frames at {FPS} FPS")

    with VideoWriterContext(output_path) as vw:
        # 写 2 秒纯白帧，避免播放器 UI 遮挡 QR
        white = np.full((FRAME_HEIGHT, FRAME_WIDTH), 255, dtype=np.uint8)
        for _ in range(int(2 * FPS)):
            vw.write_frame(white)

        for i, frame in enumerate(frames):
            vw.write_frame(frame)
            if (i + 1) % 100 == 0:
                print(f"  Written {i + 1}/{len(frames)} frames")

    print(f"Done: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <input_file> <output_video>")
        sys.exit(1)
    encode_file(sys.argv[1], sys.argv[2])
