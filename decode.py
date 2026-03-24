#!/usr/bin/env python3
"""
decode.py — QR 视频 → 文件解码器

用法:
  python decode.py <input_video> [output_file]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import cv2
from decoder.frame_reader import read_frames
from decoder.locator import decode_qr_frame
from decoder.frame_assembler import FrameAssembler


def decode_video(video_path: str, output_path: str | None = None) -> bytes:
    assembler = FrameAssembler()
    frame_count = 0
    found = 0

    for raw_frame in read_frames(video_path):
        frame_count += 1
        result = decode_qr_frame(raw_frame)
        if result:
            found += 1
            if assembler.add(result):
                print(f"File complete after {found} QR frames")
                break

    data = assembler.assemble()
    if data is None:
        print(f"No complete file found ({found}/{frame_count} frames detected)")
        sys.exit(1)
    if output_path:
        open(output_path, 'wb').write(data)
        print(f"Written {len(data)} bytes to {output_path}")
    return data


def decode_image(image_path: str, output_path: str | None = None) -> bytes:
    img = cv2.imread(image_path)
    if img is None:
        print(f"Cannot read image: {image_path}")
        sys.exit(1)

    result = decode_qr_frame(img)
    if result is None:
        print("No QR code found in image")
        sys.exit(1)

    assembler = FrameAssembler()
    complete = assembler.add(result)
    if complete:
        data = assembler.assemble()
        if data is None:
            print("Frame parsed but assembly failed")
            sys.exit(1)
    else:
        # 查看当前收集进度
        total_segs = assembler._total_segs or 1
        seg_id = 0
        seg_frames = assembler._segments.get(seg_id, {})
        frame_count = assembler._seg_meta.get(seg_id, 0)
        print(f"Frame parsed but file incomplete: seg={seg_id}, frames={len(seg_frames)}/{frame_count}, total_segs={total_segs}")
        print("(Tip: take photos of all QR frames or use the video directly)")
        sys.exit(1)

    if output_path:
        open(output_path, 'wb').write(data)
        print(f"Written {len(data)} bytes to {output_path}")
    return data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <input_video_or_image> [output_file]")
        sys.exit(1)
    path = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) >= 3 else None
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        decode_image(path, output)
    else:
        decode_video(path, output)
