# test/test_locator_unit.py
import sys
import os
import cv2
import numpy as np

# 1. 正确设置路径：将项目根目录加入系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # project_root
sys.path.append(parent_dir)

# 导入核心函数
# 注意：确保 decoder/locator.py 中已经导出了 order_points 或者我们在本地重新定义它用于画图
try:
    from decoder.locator import locate_and_process, order_points
except ImportError:
    print(" 导入失败：请确保 decoder/locator.py 存在且包含 locate_and_process 和 order_points 函数。")
    # 如果 locator.py 没导出 order_points，我们在本地定义一个备用
    def order_points(pts):
        pts = pts.astype(np.float32)
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmax(diff)]
        rect[3] = pts[np.argmin(diff)]
        return rect

def run_unit_test():
    # 1. 定位测试图片
    assets_path = os.path.join(parent_dir, 'test')
    
    # 支持多种可能的文件名
    possible_names = [
        "locator_test_img5.jpg", 
        "locator_test_img5.png", 
        "test_qr.jpg", 
        "test_qr.png",
        "frame_00.png" # 兼容之前的命名
    ]
    
    img_path = None
    for name in possible_names:
        path = os.path.join(assets_path, name)
        if os.path.exists(path):
            img_path = path
            break
    
    if not img_path:
        print(f" 错误：在 {assets_path} 下未找到测试图片。")
        print(f" 请放入以下任一文件：{', '.join(possible_names)}")
        return

    print(f"正在加载图片：{os.path.basename(img_path)} ...")
    frame = cv2.imread(img_path)
    
    if frame is None:
        print(" 错误：无法读取图片文件（文件可能损坏或格式不支持）。")
        return

    print(" 开始执行 locate_and_process (含预处理+增强+外扩)...")
    
    # 【关键修改】修改 locate_and_process 的返回值以包含角点，方便画图验证
    # 如果你的 locator.py 还没改返回值，请看下方的【重要提示】
    result = locate_and_process(frame)
    
    # 兼容性处理：如果 locate_and_process 只返回了 image
    # 我们需要一种机制来获取角点用于画图。
    # 方案 A: 修改 locate_and_process 返回 (image, pts) -> 推荐
    # 方案 B: 如果只能返回 image，我们这里只能简单展示结果，无法画精确的外扩框
    
    # 假设我们已经按照最佳实践修改了 locate_and_process 返回 (binary_img, pts)
    if isinstance(result, tuple):
        binary_qr, detected_pts = result
    else:
        binary_qr = result
        detected_pts = None
        print(" 注意：locate_and_process 仅返回了图像，未返回角点坐标，跳过原图画框步骤。")

    if binary_qr is None:
        print("\n 测试失败：未检测到二维码。")
        print("    建议解决方案：")
        print("   1. 检查图片是否清晰，二维码是否完整。")
        print("   2. 打开 decoder/locator.py，调整 preprocess_for_qr 中的参数：")
        print("      - blockSize: 尝试 9, 11, 15, 21 (必须是奇数)")
        print("      - C: 尝试 -2, 2, 5, 10")
        print("   3. 确认二维码是否有足够的静区（周围白边/黑边）。")
        return

    print("\n测试成功！二维码已提取并校正。")
    print(f"   输出图像尺寸：{binary_qr.shape}")

    # --- 可视化验证 ---
    debug_frame = frame.copy()
    
    if detected_pts is not None:
        # 使用检测到的（已排序、已外扩、已亚像素优化）的点画框
        pts_int = detected_pts.astype(np.int32)
        
        # 画绿色多边形
        cv2.polylines(debug_frame, [pts_int], True, (0, 255, 0), 3)
        
        # 标出四个角 (红点)
        labels = ["TL", "TR", "BR", "BL"]
        for i, pt in enumerate(pts_int):
            cv2.circle(debug_frame, tuple(pt), 8, (0, 0, 255), -1)
            cv2.putText(debug_frame, labels[i], (pt[0]-15, pt[1]-15), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        cv2.putText(debug_frame, "Optimized Box (Expanded)", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        cv2.putText(debug_frame, "Detected (Box info unavailable)", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # --- 额外验证：尝试解码矫正后的图 ---
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(binary_qr)
    
    if data:
        print(f"    解码验证成功！内容：{data[:50]}{'...' if len(data)>50 else ''}")
        cv2.putText(debug_frame, f"Decoded: {data[:20]}...", (10, frame.shape[0]-20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
    else:
        print("     解码验证失败：矫正后的图像仍无法被识别。")
        print("      可能是二值化过度或透视变换失真，请检查 binary_qr 窗口。")
        cv2.putText(debug_frame, "Decode Failed", (10, frame.shape[0]-20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1)

    # 显示窗口
    cv2.imshow("Original Frame (with Optimized Box)", debug_frame)
    cv2.imshow("Processed QR (Binary)", binary_qr)
    
    print("\n   -> 窗口已打开。")
    print("   -> 按任意键关闭并退出测试。")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_unit_test()