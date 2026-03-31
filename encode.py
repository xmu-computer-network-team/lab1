#!/usr/bin/env python3
"""
encode.py — 文件 → QR 视频编码器

用法:
    python encode.py <input_file> <output_video> <max_duration_ms>
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

import numpy as np
from encoder.frame_builder import iter_qr_frames
from encoder.video_writer import VideoWriterContext
from common.config import (
    FPS,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    LEADER_DURATION_SECONDS,
    MAX_INPUT_BYTES,
    MAX_RAW_BYTES,
)


def _duration_ms_from_frames(frame_count: int) -> float:
    return frame_count * 1000.0 / FPS


def _max_data_frames_from_budget_ms(max_duration_ms: int) -> int:
    # 只约束“有效数据帧”的时长：leader 不计入。
    # floor(max_duration_ms * FPS / 1000)
    return (max_duration_ms * FPS) // 1000


def encode_file(input_path: str, output_path: str, max_duration_ms: int) -> None:
    data = open(input_path, 'rb').read()
    print(f"Encoding {len(data)} bytes ({len(data) / 1024:.1f} KB)")

    max_data_frames = _max_data_frames_from_budget_ms(max_duration_ms)
    if max_data_frames <= 0:
        raise ValueError(
            "max_duration_ms too small to carry any data frames (leader is excluded): "
            f"{max_duration_ms}ms at {FPS} FPS"
        )

    max_data_bytes = max_data_frames * MAX_RAW_BYTES
    if len(data) > max_data_bytes:
        original = len(data)
        data = data[:max_data_bytes]
        print(
            "Truncated input to fit effective duration budget: "
            f"{original} -> {len(data)} bytes (max_data_frames={max_data_frames})"
        )

    leader_frames = int(LEADER_DURATION_SECONDS * FPS)

    with VideoWriterContext(output_path) as vw:
        # 写 2 秒纯白帧，避免播放器 UI 遮挡 QR
        white = np.full((FRAME_HEIGHT, FRAME_WIDTH), 255, dtype=np.uint8)
        for _ in range(leader_frames):
            vw.write_frame(white)

        data_frames_written = 0
        for frame in iter_qr_frames(data, max_frames=max_data_frames):
            vw.write_frame(frame)
            data_frames_written += 1
            if data_frames_written % 100 == 0:
                print(f"  Written {data_frames_written} data frames")

    effective_duration_ms = _duration_ms_from_frames(data_frames_written)
    total_duration_ms = _duration_ms_from_frames(leader_frames + data_frames_written)
    if effective_duration_ms > max_duration_ms:
        # 理论上不会发生（因为 max_data_frames 用 floor 计算），但保底。
        raise RuntimeError(
            "Effective data duration exceeds limit: "
            f"{effective_duration_ms:.2f}ms > {max_duration_ms}ms"
        )

    print(
        f"Done: {output_path} (effective={effective_duration_ms:.2f} ms, total={total_duration_ms:.2f} ms)"
    )


def _parse_positive_int(raw: str, name: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got: {raw}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be > 0, got: {value}")
    return value


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: python {sys.argv[0]} <input_file> <output_video> <max_duration_ms>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_video = sys.argv[2]

    try:
        max_duration_ms = _parse_positive_int(sys.argv[3], "max_duration_ms")
        if not os.path.isfile(input_file):
            raise ValueError(f"Input file not found: {input_file}")
        size = os.path.getsize(input_file)
        if size <= 0:
            raise ValueError("Input file is empty")
        if size > MAX_INPUT_BYTES:
            raise ValueError(
                f"Input file too large: {size} bytes > {MAX_INPUT_BYTES} bytes"
            )

        encode_file(input_file, output_video, max_duration_ms)
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)
