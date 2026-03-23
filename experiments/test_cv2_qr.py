#!/usr/bin/env python3
"""
实验1：二维码定位能力测试

目的：测试不同拍摄条件下的 QR 码识别率。
- 生成标准 QR 码图片
- 用户拍照放入 experiments/input/
- 测试识别成功率
"""

import glob
import os
import sys

import cv2
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAB1_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, LAB1_DIR)

INPUT_DIR = os.path.join(SCRIPT_DIR, "input")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")


def generate_qr_images():
    """生成几张测试 QR 码图片到 output/（需要 qrcode 库）"""
    try:
        import qrcode
    except ImportError:
        print("需要安装 qrcode 库：pip install qrcode pillow")
        print()
        print("或者用在线 QR 码生成器生成测试图片，放入 input/ 目录")
        print()
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    test_data_list = [
        ("hello", "test_hello.png"),
        ("ABCDEFGH1234567890", "test_alphanumeric.png"),
        ("0123456789" * 5, "test_numeric.png"),
        ("这是一段中文测试文字", "test_chinese.png"),
        ("http://example.com/path/to/file?param=value" * 2, "test_url.png"),
        ("test" * 50, "test_repeated.png"),
        ("~!@#$%^&*()_+-=[]{}|;':\",./<>?" * 2, "test_symbols.png"),
    ]

    print("生成测试 QR 码图片到 output/：")
    for data, filename in test_data_list:
        try:
            img = qrcode.make(data)
            img.save(os.path.join(OUTPUT_DIR, filename))
            print(f"  生成: {filename} ({len(data)} chars)")
        except Exception as e:
            print(f"  失败: {filename} - {e}")

    print()
    print("下一步：")
    print("1. 打开 output/ 目录下的图片，在电脑全屏显示")
    print("2. 用手机拍照（或截图）存入 input/ 目录")
    print("3. 运行: python experiments/test_cv2_qr.py")
    print()


def detect_qr_multi_scale(img):
    """
    多尺度 + 多策略 QR 码检测（pyzbar）。

    返回: (data, strategy_name) 或 (None, None)
    """
    from pyzbar.pyzbar import decode as pyzbar_decode
    from pyzbar.pyzbar import ZBarSymbol

    # 策略1: 直接检测
    decoded = pyzbar_decode(img, symbols=[ZBarSymbol.QRCODE])
    if decoded:
        return decoded[0].data.decode('utf-8'), "原图"

    # 策略2: 多尺度缩放（先放大再缩小）
    for scale in [0.3, 0.5, 0.7, 1.0, 1.5, 2.0]:
        scaled = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        decoded = pyzbar_decode(scaled, symbols=[ZBarSymbol.QRCODE])
        if decoded:
            return decoded[0].data.decode('utf-8'), f"缩放{scale}x"

    # 策略3: CLAHE 自适应直方图均衡化
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    enhanced_bgr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    decoded = pyzbar_decode(enhanced_bgr, symbols=[ZBarSymbol.QRCODE])
    if decoded:
        return decoded[0].data.decode('utf-8'), "CLAHE"

    # 策略4: Otsu 二值化
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    decoded = pyzbar_decode(binary_bgr, symbols=[ZBarSymbol.QRCODE])
    if decoded:
        return decoded[0].data.decode('utf-8'), "Otsu二值化"

    return None, None


def test_input_images():
    """测试 input/ 目录下所有图片的 QR 识别率"""
    os.makedirs(INPUT_DIR, exist_ok=True)

    images = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]:
        images.extend(glob.glob(os.path.join(INPUT_DIR, ext)))

    if not images:
        print("input/ 目录为空，请放入手机拍摄的 QR 码图片")
        print()
        print("建议测试场景：")
        print("  1. 近距离（10cm）正对拍摄")
        print("  2. 中距离（30cm）正对拍摄")
        print("  3. 远距离（50cm+）正对拍摄")
        print("  4. 倾斜角度拍摄")
        print("  5. 不同光照条件")
        print()
        print("也可以用电脑摄像头实时测试（自动多尺度检测）：")
        print("  python -c \"import cv2; from experiments.test_cv2_qr import detect_qr_multi_scale; ")
        print("    cap = cv2.VideoCapture(0); ")
        print("    while True: ret, frame = cap.read(); ")
        print("    data, strategy = detect_qr_multi_scale(frame); ")
        print("    if data: print(strategy, '->', data[:40]); ")
        print("    cv2.waitKey(1)\"")
        print()
        print("或者生成测试图片：")
        print("  pip install qrcode pillow")
        print("  python experiments/test_cv2_qr.py --generate")
        return

    print(f"测试 {len(images)} 张图片（多尺度检测）：")
    print("-" * 70)

    success = 0
    failed = 0

    for path in sorted(images):
        img = cv2.imread(path)
        if img is None:
            print(f"  [FAIL] {os.path.basename(path)} - 无法读取")
            failed += 1
            continue

        data, strategy = detect_qr_multi_scale(img)

        if data:
            print(f"  [ OK ] {os.path.basename(path)}  [{strategy}]")
            print(f"        内容: {data[:60]}{'...' if len(data) > 60 else ''}")
            success += 1
        else:
            print(f"  [FAIL] {os.path.basename(path)}")
            failed += 1

    print("-" * 70)
    print(f"结果: {success} 成功 / {failed} 失败 ({len(images)} 张总计)")
    print()

    if success == len(images):
        print("所有图片识别成功！拍摄质量良好，继续下一步。")
    elif success > 0:
        print(f"部分识别成功（{success}/{success+failed}）。")
        print("  如果失败率高：")
        print("  - 尝试让 QR 码占满整个屏幕")
        print("  - 用电脑摄像头实时检测效果最好")
        print("  - 倾斜角度太大会失败")
    else:
        print("全部识别失败！建议：")
        print("  1. 确认图片中有清晰的 QR 码")
        print("  2. 让 QR 码占满屏幕再拍")
        print("  3. 确保正对拍摄，无反光")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--generate":
        generate_qr_images()
    else:
        test_input_images()
