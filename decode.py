#!/usr/bin/env python3
"""
decode.py — QR 视频 → 文件解码器

用法:
    python decode.py <input_video> <out.bin> <out.val>
"""
import sys
import os

# PyInstaller 打包后需要从临时目录加载模块
if getattr(sys, 'frozen', False):
    # 打包后的 exe
    sys.path.insert(0, sys._MEIPASS)
else:
    # 直接运行
    sys.path.insert(0, os.path.dirname(__file__))

import cv2
from decoder.frame_reader import read_frames
from decoder.locator import decode_qr_frame
from decoder.frame_assembler import FrameAssembler


def decode_video(video_path: str) -> tuple[bytes, bytes]:
    """从视频中解码出完整的数据流及其有效性掩码。

    返回:
        (data, val_mask)

    约定:
        - data: 按发送顺序拼接的所有帧 payload；对于完全缺失或 CRC 失败的
          帧，用 0x00 填充与预期长度相同的占位字节。
        - val_mask: 与 data 等长的字节流，逐比特标记有效位：0xFF 表示该
          字节的 8 bit 都来自通过 CRC 的真实数据；0x00 表示该字节对应
          “弃权位”，不参与错误统计。
    """

    assembler = FrameAssembler()
    frame_count = 0
    qr_detected = 0  # pyzbar 成功返回 QR 原始数据的帧数

    for raw_frame in read_frames(video_path):
        frame_count += 1
        result = decode_qr_frame(raw_frame)
        if result:
            qr_detected += 1
            if assembler.add(result):
                # 全部 segment 和 frame 都已齐全
                print(f"File complete after {qr_detected} QR frames (total video frames: {frame_count})")
                break

    print(
        f"Decode stats: total_frames={frame_count}, "
        f"qr_detected={qr_detected}, qr_accepted={assembler._accepted_frames}"
    )

    assembled = assembler.assemble_with_mask()
    if assembled is None:
        raise RuntimeError(
            f"No usable data assembled (qr_detected={qr_detected}, total_frames={frame_count})"
        )

    data, val_mask = assembled
    return data, val_mask


def decode_image(image_path: str) -> tuple[bytes, bytes]:
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"Cannot read image: {image_path}")

    result = decode_qr_frame(img)
    if result is None:
        raise RuntimeError("No QR code found in image")

    assembler = FrameAssembler()
    complete = assembler.add(result)
    if not complete:
        # 单帧模式下，理论上只有 1 个 segment、若干帧，这里仍然通过
        # assemble_with_mask 组装，可兼容将来多帧图片场景。
        print("Warning: frame parsed but file incomplete in image mode")

    assembled = assembler.assemble_with_mask()
    if assembled is None:
        raise RuntimeError("Frame parsed but assembly failed")

    data, val_mask = assembled
    return data, val_mask


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
            data, val = decode_image(path)
        else:
            data, val = decode_video(path)

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
