#!/usr/bin/env python3
"""
encode.py — 文件 → QR 视频编码器

用法:
    python encode.py <input_file> <output_video> <max_duration_ms>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from encoder.frame_builder import build_qr_frames
from encoder.video_writer import VideoWriterContext
from common.config import (
    FPS,
    FRAME_WIDTH,
    FRAME_HEIGHT,
    LEADER_DURATION_SECONDS,
    MAX_INPUT_BYTES,
)


def _duration_ms_from_frames(frame_count: int) -> float:
    return frame_count * 1000.0 / FPS


def encode_file(input_path: str, output_path: str, max_duration_ms: int) -> None:
    data = open(input_path, 'rb').read()
    print(f"Encoding {len(data)} bytes ({len(data) / 1024:.1f} KB)")

    frames = build_qr_frames(data)
    print(f"Generated {len(frames)} frames at {FPS} FPS")

    leader_frames = int(LEADER_DURATION_SECONDS * FPS)
    planned_total_frames = leader_frames + len(frames)
    planned_duration_ms = _duration_ms_from_frames(planned_total_frames)
    if planned_duration_ms > max_duration_ms:
        raise ValueError(
            "Planned video duration exceeds limit: "
            f"{planned_duration_ms:.2f}ms > {max_duration_ms}ms"
        )

    with VideoWriterContext(output_path) as vw:
        # 写 2 秒纯白帧，避免播放器 UI 遮挡 QR
        white = np.full((FRAME_HEIGHT, FRAME_WIDTH), 255, dtype=np.uint8)
        for _ in range(leader_frames):
            vw.write_frame(white)

        for i, frame in enumerate(frames):
            vw.write_frame(frame)
            if (i + 1) % 100 == 0:
                print(f"  Written {i + 1}/{len(frames)} frames")

    actual_duration_ms = _duration_ms_from_frames(vw.frame_count)
    if actual_duration_ms > max_duration_ms:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise RuntimeError(
            "Generated video exceeds max duration and was removed: "
            f"{actual_duration_ms:.2f}ms > {max_duration_ms}ms"
        )

    print(f"Done: {output_path} ({actual_duration_ms:.2f} ms)")


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
