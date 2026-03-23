import cv2
import numpy as np

def order_points(pts):
    """
    将无序的 4 个点排序为：左上、右上、右下、左下
    输入: (4, 2) numpy array
    输出: (4, 2) sorted numpy array
    """
    pts = pts.astype(np.float32)
    rect = np.zeros((4, 2), dtype="float32")

    # 1. 按 (x + y) 的和排序 -> 区分 左上/右下
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # 左上 (和最小)
    rect[2] = pts[np.argmax(s)]  # 右下 (和最大)
    
    # 2. 按 (x - y) 的差排序 -> 区分 右上/左下
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmax(diff)]  # 右上 (差最大: x大y小)
    rect[3] = pts[np.argmin(diff)]  # 左下 (差最小: x小y大)
    
    return rect

def preprocess_for_qr(frame):
    """
    【核心解决方案】预处理 → 增强对比度
    针对彩色、渐变、低对比度二维码进行优化
    """
    # 1. 转灰度
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 2. 去噪 (可选，如果图片噪点非常多才需要，一般二维码不需要太强去噪)
    # gray = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 3. 【关键】自适应阈值二值化
    # 原理：不全局使用一个阈值，而是计算每个小区域(11x11)的阈值
    # 效果：能完美处理光照不均、彩色渐变导致的对比度低问题
    # THRESH_BINARY_INV: 因为原图可能是黑底彩字，我们要转成 白底黑字 (标准QR格式)
    binary = cv2.adaptiveThreshold(
        gray, 
        255, 
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # 高斯加权，边缘更柔和
        cv2.THRESH_BINARY_INV,           # 反转颜色：深色变黑(0)，浅色变白(255)
        blockSize=11,                    # 邻域大小 (必须是奇数，9, 11, 15...)
        C=2                              # 常数偏移，微调灵敏度 (通常 2~5)
    )
    
    # 4. 【可选】形态学操作 (如果二值化后有很多噪点/空洞)
    # 先膨胀再腐蚀，填补二维码内部的小白点，连接断裂的线条
    kernel = np.ones((3,3),np.uint8)
    # dilation = cv2.dilate(binary, kernel, iterations=1)
    # cleaned_binary = cv2.erode(dilation, kernel, iterations=1)
    
    # 返回：原始灰度图(用于亚像素优化) + 增强后的二值图(用于检测)
    return gray, binary

def locate_and_process(frame):
    """
    主流程：预处理 -> 检测 -> 优化 -> 矫正
    """
    if frame is None:
        return None, None

    # --- 第一步：预处理与增强对比度 ---
    gray, binary = preprocess_for_qr(frame)
    
    # --- 第二步：检测角点 ---
    detector = cv2.QRCodeDetector()
    
    # 策略：优先用增强后的 binary 图检测 (对彩色码最有效)
    retval, points_raw = detector.detect(binary)
    
    # Fallback: 如果 binary 没检测到，尝试用原始 gray 图 (双重保险)
    if not retval or points_raw is None:
        retval, points_raw = detector.detect(gray)

    if not retval or points_raw is None:
        return None, None  # 彻底失败

    # --- 第三步：数据清洗与精修 ---
    pts = points_raw[0].astype(np.float32) # 取出第一个二维码 (4, 2)

    # 【亚像素优化】让角点从整数坐标变为浮点数，精确贴合边缘
    # 注意：这里必须用 gray 图做亚像素搜索，不能用 binary (二值图边缘太硬，无法亚像素化)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    pts_refined = cv2.cornerSubPix(
        gray, 
        pts.reshape(-1, 1, 2), 
        winSize=(5, 5), 
        zeroZone=(-1, -1), 
        criteria=criteria
    )
    pts = pts_refined.reshape(-1, 2)

    # 【排序】确保点的顺序是 左上->右上->右下->左下
    ordered_pts = order_points(pts)

    # 【外扩】解决“框画小了”的问题，向外扩展 15%
    center = ordered_pts.mean(axis=0)
    scale = 1.15 
    expanded_pts = center + (ordered_pts - center) * scale

    # --- 第四步：透视矫正 ---
    output_w, output_h = 800, 800
    
    # 目标点 (对应排序后的顺序)
    dst_pts = np.array([
        [0, 0], 
        [output_w - 1, 0], 
        [output_w - 1, output_h - 1], 
        [0, output_h - 1]
    ], dtype="float32")

    # 计算变换矩阵 (使用外扩后的点)
    matrix = cv2.getPerspectiveTransform(expanded_pts, dst_pts)
    
    # 执行变换 (使用原始 gray 图，保留细节)
    warped_qr = cv2.warpPerspective(gray, matrix, (output_w, output_h))
    
    # --- 第五步：最终二值化输出 ---
    # 再次阈值化，确保输出给解码器的是纯净黑白图
    _, final_binary = cv2.threshold(warped_qr, 127, 255, cv2.THRESH_BINARY)
    
    return final_binary, expanded_pts

