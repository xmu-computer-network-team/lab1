#!/usr/bin/env python3
"""
生成并全屏显示 6px/7px/8px 的棋盘格，用于块大小标定实验。

用法示例：
  python lab1/test/argument_test.py
  python lab1/test/argument_test.py --outdir ../tools/calibration --duration 5000

按任意键切换到下一张；按 ESC 退出。
"""
import argparse
import os
import math
import tkinter as tk

import cv2
import numpy as np


def screen_size():
    root = tk.Tk()
    root.withdraw()
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.destroy()
    return w, h


def make_checkerboard(width, height, tile):
    cols = math.ceil(width / tile)
    rows = math.ceil(height / tile)
    board = (np.add.outer(range(rows), range(cols)) % 2).astype(np.uint8)
    tile_block = np.kron(board, np.ones((tile, tile), dtype=np.uint8))
    img = tile_block[:height, :width] * 255
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def main():
    p = argparse.ArgumentParser(description="生成并全屏显示棋盘格（6/7/8px）")
    p.add_argument("--outdir", default="./test/argument_test_attachments", help="保存目录（相对于当前工作目录）")
    p.add_argument("--duration", type=int, default=0, help="自动切换毫秒（0 为按键切换）")
    args = p.parse_args()

    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)

    w, h = screen_size()
    sizes = [6, 7, 8, 9, 10]
    window = "BLOCK_CALIBRATION"
    cv2.namedWindow(window, cv2.WND_PROP_FULLSCREEN)
    cv2.setWindowProperty(window, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    for s in sizes:
        img = make_checkerboard(w, h, s)
        outpath = os.path.join(outdir, f"checker_{s}px.png")
        cv2.imwrite(outpath, img)
        cv2.imshow(window, img)
        if args.duration > 0:
            key = cv2.waitKey(args.duration)
        else:
            key = cv2.waitKey(0)
        if key == 27:  # ESC
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
