#!/usr/bin/env python3
"""
decode.py — QR 视频 → 文件解码器

用法:
    python decode.py <input_video> <out.bin> <out.val>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import cv2
from decoder.frame_reader import read_frames
from decoder.locator import decode_qr_frame
from decoder.frame_assembler import FrameAssembler


def _build_all_valid_val(data_len: int) -> bytes:
    # 位打包格式下，每个 out.bin 字节对应一个 val 字节，按位全 1 表示都正确。
    return b"\xFF" * data_len


def decode_video(video_path: str) -> bytes:
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
        raise RuntimeError(f"No complete file found ({found}/{frame_count} frames detected)")
    return data


def decode_image(image_path: str) -> bytes:
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Cannot read image: {image_path}")

    result = decode_qr_frame(img)
    if result is None:
        raise RuntimeError("No QR code found in image")

    assembler = FrameAssembler()
    complete = assembler.add(result)
    if complete:
        data = assembler.assemble()
        if data is None:
            raise RuntimeError("Frame parsed but assembly failed")
    else:
        # 查看当前收集进度
        total_segs = assembler._total_segs or 1
        seg_id = 0
        seg_frames = assembler._segments.get(seg_id, {})
        frame_count = assembler._seg_meta.get(seg_id, 0)
        raise RuntimeError(
            "Frame parsed but file incomplete: "
            f"seg={seg_id}, frames={len(seg_frames)}/{frame_count}, total_segs={total_segs}"
        )

    return data


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <input_video> <out.bin> <out.val>")
        sys.exit(1)

    path = sys.argv[1]
    out_bin = sys.argv[2]
    out_val = sys.argv[3]

    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            data = decode_image(path)
        else:
            data = decode_video(path)

        val = _build_all_valid_val(len(data))
        open(out_bin, 'wb').write(data)
        open(out_val, 'wb').write(val)
        print(f"Written {len(data)} bytes to {out_bin}")
        print(f"Written {len(val)} bytes to {out_val}")
    except Exception as exc:
        # 失败时仍创建空文件，便于批处理链路检测输出路径。
        open(out_bin, 'wb').write(b'')
        open(out_val, 'wb').write(b'')
        print(f"Error: {exc}")
        sys.exit(1)
