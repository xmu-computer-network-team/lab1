import cv2
import numpy as np
from common.config import *

class FrameLocator:
    """负责从拍摄图像中定位和矫正帧"""

    def locate_and_rectify(self, raw_frame: np.ndarray):
        """
        输入: 手机拍摄的原始帧 (彩色)
        输出: 矫正后的灰度帧 (GRID_ROWS*BLOCK_SIZE x GRID_COLS*BLOCK_SIZE)
              如果定位失败返回 None
        """
        gray = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        out_w = GRID_COLS * BLOCK_SIZE
        out_h = GRID_ROWS * BLOCK_SIZE

        # ---- 阶段1: 用帧边界做粗矫正 ----
        frame_quad = self._find_frame_boundary(gray)
        if frame_quad is not None:
            src_boundary = np.float32(frame_quad)  # TL, TR, BR, BL
            dst_boundary = np.float32([[0, 0], [out_w, 0], [out_w, out_h], [0, out_h]])
            M_coarse = cv2.getPerspectiveTransform(src_boundary, dst_boundary)
            coarse = cv2.warpPerspective(gray, M_coarse, (out_w, out_h))

            # ---- 阶段2: 在粗矫正图上精确定位 finder 中心 ----
            cp = FINDER_SIZE / 2.0 * BLOCK_SIZE
            expected_finders = [
                (int(cp), int(cp)),                                          # TL
                (int((GRID_COLS - FINDER_SIZE/2.0) * BLOCK_SIZE), int(cp)),  # TR
                (int(cp), int((GRID_ROWS - FINDER_SIZE/2.0) * BLOCK_SIZE)),  # BL
            ]

            coarse_blur = cv2.GaussianBlur(coarse, (5, 5), 0)
            coarse_binary = cv2.adaptiveThreshold(
                coarse_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, blockSize=51, C=10
            )

            refined = []
            search_r = FINDER_SIZE * BLOCK_SIZE  # 搜索半径
            for ex, ey in expected_finders:
                pt = self._refine_finder_center(coarse_binary, ex, ey, search_r)
                refined.append(pt if pt is not None else (ex, ey))

            # 估算右下 alignment
            tl_r, tr_r, bl_r = refined
            est_br = (tr_r[0] - tl_r[0] + bl_r[0], tr_r[1] - tl_r[1] + bl_r[1])

            # 用精确的 finder 中心做最终透视变换
            src_fine = np.float32(refined + [est_br])
            dst_fine = np.float32([
                [cp, cp],
                [(GRID_COLS - FINDER_SIZE/2.0) * BLOCK_SIZE, cp],
                [cp, (GRID_ROWS - FINDER_SIZE/2.0) * BLOCK_SIZE],
                [(GRID_COLS - ALIGN_SIZE/2.0) * BLOCK_SIZE, (GRID_ROWS - ALIGN_SIZE/2.0) * BLOCK_SIZE],
            ])

            M_fine = cv2.getPerspectiveTransform(src_fine, dst_fine)
            corrected = cv2.warpPerspective(coarse, M_fine, (out_w, out_h))
            return corrected

        # ---- 回退: 无法检测帧边界时，用原来的 finder 扫描法 ----
        binary_normal = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, blockSize=51, C=10
        )
        binary_inv = cv2.bitwise_not(binary_normal)

        finders = self._find_finder_patterns(binary_normal)
        if len(finders) < 3:
            finders = self._find_finder_patterns(binary_inv)
        if len(finders) < 3:
            return None

        if len(finders) > 3:
            finders = self._select_best_finders(finders, binary_normal.shape)
        else:
            finders = finders[:3]

        top_left, top_right, bottom_left = self._order_finders(finders)
        est_x = top_right[0] - top_left[0] + bottom_left[0]
        est_y = top_right[1] - top_left[1] + bottom_left[1]
        align = self._find_alignment(binary_normal, est_x, est_y)
        if align is None:
            align = self._find_alignment(binary_inv, est_x, est_y)
        if align is None:
            align = (est_x, est_y)

        src = np.float32([top_left, top_right, bottom_left, align])
        cp = FINDER_SIZE / 2.0 * BLOCK_SIZE
        dst = np.float32([
            [cp, cp],
            [(GRID_COLS - FINDER_SIZE/2.0) * BLOCK_SIZE, cp],
            [cp, (GRID_ROWS - FINDER_SIZE/2.0) * BLOCK_SIZE],
            [(GRID_COLS - ALIGN_SIZE/2.0) * BLOCK_SIZE, (GRID_ROWS - ALIGN_SIZE/2.0) * BLOCK_SIZE],
        ])
        M = cv2.getPerspectiveTransform(src, dst)
        corrected = cv2.warpPerspective(gray, M, (out_w, out_h))
        return corrected

    def _refine_finder_center(self, binary, est_x, est_y, search_r):
        """在粗矫正图上，在预期位置附近精确定位 finder 中心"""
        h, w = binary.shape
        max_run = search_r * 2
        min_run = max(1, BLOCK_SIZE // 2)

        # 在搜索区域内做水平扫描
        candidates = []
        y_start = max(0, est_y - search_r)
        y_end = min(h, est_y + search_r)
        x_start = max(0, est_x - search_r)
        x_end = min(w, est_x + search_r)

        row_step = max(1, BLOCK_SIZE // 2)
        for y in range(y_start, y_end, row_step):
            counts = [0, 0, 0, 0, 0]
            state = 0
            for x in range(x_start, x_end):
                is_black = binary[y, x] < 128
                if is_black:
                    if state % 2 == 0:
                        counts[state] += 1
                    else:
                        if state == 4:
                            if self._check_finder_ratio(counts, min_run):
                                center_x = self._center_from_end(counts, x)
                                center_y = self._cross_check_vertical(binary, int(center_x), y, counts[2], max_run)
                                if center_y is not None:
                                    center_x2 = self._cross_check_horizontal(binary, int(center_x), int(center_y), counts[2], max_run)
                                    if center_x2 is not None:
                                        candidates.append((float(center_x2), float(center_y)))
                            counts = [counts[2], counts[3], counts[4], 1, 0]
                            state = 3
                        else:
                            state += 1
                            counts[state] += 1
                else:
                    if state % 2 == 1:
                        counts[state] += 1
                    else:
                        if state == 4:
                            if self._check_finder_ratio(counts, min_run):
                                center_x = self._center_from_end(counts, x)
                                center_y = self._cross_check_vertical(binary, int(center_x), y, counts[2], max_run)
                                if center_y is not None:
                                    center_x2 = self._cross_check_horizontal(binary, int(center_x), int(center_y), counts[2], max_run)
                                    if center_x2 is not None:
                                        candidates.append((float(center_x2), float(center_y)))
                            counts = [counts[2], counts[3], counts[4], 1, 0]
                            state = 3
                        else:
                            state += 1
                            counts[state] += 1

        if not candidates:
            return None

        # 选离预期位置最近的候选点
        best = min(candidates, key=lambda p: np.hypot(p[0]-est_x, p[1]-est_y))
        return (int(round(best[0])), int(round(best[1])))

    def _find_frame_boundary(self, gray):
        """用 Canny 边缘检测找帧的四边形边界，返回4个角点或 None"""
        edges = cv2.Canny(cv2.GaussianBlur(gray, (7, 7), 0), 30, 100)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        h, w = gray.shape
        img_area = h * w

        for c in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(c)
            if area < img_area * 0.05:
                break
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                pts = approx.reshape(4, 2)
                # 按左上、右上、右下、左下排序
                s = pts.sum(axis=1)
                d = np.diff(pts, axis=1).flatten()
                ordered = np.zeros((4, 2), dtype=np.float32)
                ordered[0] = pts[np.argmin(s)]   # 左上
                ordered[1] = pts[np.argmin(d)]   # 右上
                ordered[2] = pts[np.argmax(s)]   # 右下
                ordered[3] = pts[np.argmax(d)]   # 左下
                return ordered
        return None

    def _find_finder_patterns(self, binary):
        """
        使用 1:1:3:1:1 比例行扫描 + 十字交叉验证定位 Finder Pattern。
        若数量不足，回退到轮廓嵌套法做兜底。
        """
        h, w = binary.shape
        max_run = int(max(h, w) / 2)
        min_run = max(1, BLOCK_SIZE // 2)
        candidates = []

        # 为避免过慢，按步长扫描；当 BLOCK_SIZE 很小时退化为逐行扫描
        row_step = max(1, BLOCK_SIZE // 2)
        for y in range(0, h, row_step):
            counts = [0, 0, 0, 0, 0]
            state = 0
            for x in range(w):
                is_black = binary[y, x] < 128
                if is_black:
                    if state % 2 == 0:
                        counts[state] += 1
                    else:
                        if state == 4:
                            if self._check_finder_ratio(counts, min_run):
                                center_x = self._center_from_end(counts, x)
                                center_y = self._cross_check_vertical(binary, int(center_x), y, counts[2], max_run)
                                if center_y is not None:
                                    center_x2 = self._cross_check_horizontal(binary, int(center_x), int(center_y), counts[2], max_run)
                                    if center_x2 is not None and self._cross_check_diagonal(binary, int(center_x2), int(center_y), max_run):
                                        self._append_center(candidates, (float(center_x2), float(center_y)))
                            counts = [counts[2], counts[3], counts[4], 1, 0]
                            state = 3
                        else:
                            state += 1
                            counts[state] += 1
                else:
                    if state % 2 == 1:
                        counts[state] += 1
                    else:
                        if state == 4:
                            if self._check_finder_ratio(counts, min_run):
                                center_x = self._center_from_end(counts, x)
                                center_y = self._cross_check_vertical(binary, int(center_x), y, counts[2], max_run)
                                if center_y is not None:
                                    center_x2 = self._cross_check_horizontal(binary, int(center_x), int(center_y), counts[2], max_run)
                                    if center_x2 is not None and self._cross_check_diagonal(binary, int(center_x2), int(center_y), max_run):
                                        self._append_center(candidates, (float(center_x2), float(center_y)))
                            counts = [counts[2], counts[3], counts[4], 1, 0]
                            state = 3
                        else:
                            state += 1
                            counts[state] += 1

            if self._check_finder_ratio(counts, min_run):
                center_x = self._center_from_end(counts, w)
                center_y = self._cross_check_vertical(binary, int(center_x), y, counts[2], max_run)
                if center_y is not None:
                    center_x2 = self._cross_check_horizontal(binary, int(center_x), int(center_y), counts[2], max_run)
                    if center_x2 is not None and self._cross_check_diagonal(binary, int(center_x2), int(center_y), max_run):
                        self._append_center(candidates, (float(center_x2), float(center_y)))

        if len(candidates) >= 3:
            # 按命中次数降序排列，优先返回高置信度的点
            candidates.sort(key=lambda c: -c[2])
            return [(int(round(x)), int(round(y))) for x, y, cnt in candidates]

        # 回退兜底: 轮廓嵌套法
        fallback = self._find_finder_patterns_by_contours(binary)
        for center in fallback:
            self._append_center(candidates, (float(center[0]), float(center[1])))

        candidates.sort(key=lambda c: -c[2])
        return [(int(round(x)), int(round(y))) for x, y, cnt in candidates]

    def _check_finder_ratio(self, counts, min_run):
        total = sum(counts)
        if total < 7 * min_run:
            return False

        module = total / 7.0
        max_dev = module * 0.5  # 收紧容差（原0.8太宽松）
        expected = [1, 1, 3, 1, 1]
        for c, e in zip(counts, expected):
            if abs(c - e * module) > max_dev * max(1, e):
                return False
        return True

    def _center_from_end(self, counts, end_x):
        return end_x - counts[4] - counts[3] - counts[2] / 2.0

    def _cross_check_vertical(self, binary, center_x, center_y, center_count, max_count):
        h, _ = binary.shape
        if center_x < 0:
            return None

        counts = [0, 0, 0, 0, 0]

        y = center_y
        while y >= 0 and binary[y, center_x] < 128:
            counts[2] += 1
            y -= 1
        if y < 0:
            return None
        while y >= 0 and binary[y, center_x] >= 128 and counts[1] <= max_count:
            counts[1] += 1
            y -= 1
        if y < 0 or counts[1] > max_count:
            return None
        while y >= 0 and binary[y, center_x] < 128 and counts[0] <= max_count:
            counts[0] += 1
            y -= 1
        if counts[0] > max_count:
            return None

        y = center_y + 1
        while y < h and binary[y, center_x] < 128:
            counts[2] += 1
            y += 1
        if y == h:
            return None
        while y < h and binary[y, center_x] >= 128 and counts[3] <= max_count:
            counts[3] += 1
            y += 1
        if y == h or counts[3] > max_count:
            return None
        while y < h and binary[y, center_x] < 128 and counts[4] <= max_count:
            counts[4] += 1
            y += 1
        if counts[4] > max_count:
            return None

        if not self._check_finder_ratio(counts, max(1, BLOCK_SIZE // 2)):
            return None
            
        final_y = center_y - counts[1] - counts[0] + counts[2] / 2.0
        if final_y < 0 or final_y >= h:
            return None
        return final_y

    def _cross_check_horizontal(self, binary, center_x, center_y, center_count, max_count):
        h, w = binary.shape
        if center_y < 0 or center_y >= h:
            return None

        counts = [0, 0, 0, 0, 0]

        x = center_x
        while x >= 0 and binary[center_y, x] < 128:
            counts[2] += 1
            x -= 1
        if x < 0:
            return None
        while x >= 0 and binary[center_y, x] >= 128 and counts[1] <= max_count:
            counts[1] += 1
            x -= 1
        if x < 0 or counts[1] > max_count:
            return None
        while x >= 0 and binary[center_y, x] < 128 and counts[0] <= max_count:
            counts[0] += 1
            x -= 1
        if counts[0] > max_count:
            return None

        x = center_x + 1
        while x < w and binary[center_y, x] < 128:
            counts[2] += 1
            x += 1
        if x == w:
            return None
        while x < w and binary[center_y, x] >= 128 and counts[3] <= max_count:
            counts[3] += 1
            x += 1
        if x == w or counts[3] > max_count:
            return None
        while x < w and binary[center_y, x] < 128 and counts[4] <= max_count:
            counts[4] += 1
            x += 1
        if counts[4] > max_count:
            return None

        if not self._check_finder_ratio(counts, max(1, BLOCK_SIZE // 2)):
            return None
            
        final_x = center_x - counts[1] - counts[0] + counts[2] / 2.0
        if final_x < 0 or final_x >= w:
            return None
        return final_x

    def _cross_check_diagonal(self, binary, center_x, center_y, max_count):
        """对角线方向交叉验证，过滤非正方形的误检"""
        h, w = binary.shape
        counts = [0, 0, 0, 0, 0]

        # 左上方向
        i = 0
        while center_y - i >= 0 and center_x - i >= 0 and binary[center_y - i, center_x - i] < 128:
            counts[2] += 1
            i += 1
        if center_y - i < 0 or center_x - i < 0:
            return False
        while center_y - i >= 0 and center_x - i >= 0 and binary[center_y - i, center_x - i] >= 128 and counts[1] <= max_count:
            counts[1] += 1
            i += 1
        if center_y - i < 0 or center_x - i < 0 or counts[1] > max_count:
            return False
        while center_y - i >= 0 and center_x - i >= 0 and binary[center_y - i, center_x - i] < 128 and counts[0] <= max_count:
            counts[0] += 1
            i += 1

        # 右下方向
        i = 1
        while center_y + i < h and center_x + i < w and binary[center_y + i, center_x + i] < 128:
            counts[2] += 1
            i += 1
        if center_y + i >= h or center_x + i >= w:
            return False
        while center_y + i < h and center_x + i < w and binary[center_y + i, center_x + i] >= 128 and counts[3] <= max_count:
            counts[3] += 1
            i += 1
        if center_y + i >= h or center_x + i >= w or counts[3] > max_count:
            return False
        while center_y + i < h and center_x + i < w and binary[center_y + i, center_x + i] < 128 and counts[4] <= max_count:
            counts[4] += 1
            i += 1

        total = sum(counts)
        if total == 0:
            return False
        module = total / 7.0
        # 对角线用更宽松的容差（因为像素步进不均匀）
        max_dev = module * 0.7
        expected = [1, 1, 3, 1, 1]
        for c, e in zip(counts, expected):
            if abs(c - e * module) > max_dev * max(1, e):
                return False
        return True

    def _append_center(self, centers, pt):
        dedup_dist = max(6.0, BLOCK_SIZE * 1.5)
        for i, (ex, ey, cnt) in enumerate(centers):
            if np.hypot(pt[0] - ex, pt[1] - ey) < dedup_dist:
                # 合并坐标并增加命中计数
                centers[i] = ((ex + pt[0]) / 2.0, (ey + pt[1]) / 2.0, cnt + 1)
                return
        centers.append((pt[0], pt[1], 1))

    def _find_finder_patterns_by_contours(self, binary):
        contours, hierarchy = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is None:
            return []

        hierarchy = hierarchy[0]
        candidates = []
        min_area = (BLOCK_SIZE * 3) * (BLOCK_SIZE * 3)

        for i, contour in enumerate(contours):
            child_idx = hierarchy[i][2]
            if child_idx == -1:
                continue
            grandchild_idx = hierarchy[child_idx][2]
            if grandchild_idx == -1:
                continue

            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            M1 = cv2.moments(contour)
            M2 = cv2.moments(contours[child_idx])
            M3 = cv2.moments(contours[grandchild_idx])
            if M1['m00'] == 0 or M2['m00'] == 0 or M3['m00'] == 0:
                continue

            cx1, cy1 = M1['m10'] / M1['m00'], M1['m01'] / M1['m00']
            cx2, cy2 = M2['m10'] / M2['m00'], M2['m01'] / M2['m00']
            cx3, cy3 = M3['m10'] / M3['m00'], M3['m01'] / M3['m00']

            tol = max(10.0, BLOCK_SIZE * 2.5)
            if (
                abs(cx1 - cx2) < tol and abs(cy1 - cy2) < tol and
                abs(cx2 - cx3) < tol and abs(cy2 - cy3) < tol
            ):
                candidates.append((int(round(cx1)), int(round(cy1))))

        unique_centers = []
        for pt in candidates:
            is_dup = False
            for up in unique_centers:
                if np.hypot(pt[0] - up[0], pt[1] - up[1]) < max(10, int(BLOCK_SIZE * 1.5)):
                    is_dup = True
                    break
            if not is_dup:
                unique_centers.append(pt)
        return unique_centers

    def _select_best_finders(self, finders, image_shape=None):
        if len(finders) <= 3:
            return finders[:3]

        # 先给每个候选点计算 finder 质量分数
        # 需要二值图，但这里只有坐标，所以质量分数在调用前计算
        # 改为：用几何约束选择，但不让面积主导

        expected_ratio = (GRID_COLS - FINDER_SIZE) / float(GRID_ROWS - FINDER_SIZE)

        points = [np.array(p, dtype=np.float32) for p in finders]
        best = None
        best_score = -1.0
        n = len(points)

        for i in range(n - 2):
            for j in range(i + 1, n - 1):
                for k in range(j + 1, n):
                    a, b, c = points[i], points[j], points[k]
                    d_ab = np.sum((a - b) ** 2)
                    d_ac = np.sum((a - c) ** 2)
                    d_bc = np.sum((b - c) ** 2)

                    ds = sorted([d_ab, d_ac, d_bc])
                    short2, mid2, long2 = ds

                    if long2 < (BLOCK_SIZE * BLOCK_SIZE * 50):
                        continue

                    # 直角校验
                    error = abs(short2 + mid2 - long2) / (long2 + 1e-6)
                    rightness = max(0.0, 1.0 - error)
                    if rightness < 0.7:
                        continue

                    # 长宽比校验（放宽容差，透视变形会改变比例）
                    ratio = np.sqrt(mid2 / (short2 + 1e-6))
                    if ratio < expected_ratio * 0.4 or ratio > expected_ratio * 2.5:
                        continue
                    ratio_score = 1.0 / (1.0 + abs(ratio - expected_ratio))

                    # 面积用对数，防止它主导评分
                    area = np.sqrt(short2 * mid2)
                    log_area = np.log1p(area)

                    score = rightness * ratio_score * log_area

                    if score > best_score:
                        best_score = score
                        best = [finders[i], finders[j], finders[k]]

        if best is None:
            return finders[:3]
        return best

    def _order_finders(self, finders):
        """
        将三个 finder 排序为: 左上、右上、左下
        方法: 找距离最远的两个点（对角线），余下的一个是左上。
        然后再利用叉积区分右上和左下。
        """
        f0, f1, f2 = finders
        
        # 计算两两之间的平方距离
        d01 = (f0[0]-f1[0])**2 + (f0[1]-f1[1])**2
        d02 = (f0[0]-f2[0])**2 + (f0[1]-f2[1])**2
        d12 = (f1[0]-f2[0])**2 + (f1[1]-f2[1])**2

        # 找出距离最远的借此确定哪两个是对角线，剩余一个是左上角点
        if d01 >= d02 and d01 >= d12:
            top_left = f2
            p1, p2 = f0, f1
        elif d02 >= d01 and d02 >= d12:
            top_left = f1
            p1, p2 = f0, f2
        else:
            top_left = f0
            p1, p2 = f1, f2

        # 利用向量叉积确定右上和左下
        # 向量 A = p1 - top_left, 向量 B = p2 - top_left
        cross_product = (p1[0] - top_left[0]) * (p2[1] - top_left[1]) - \
                        (p1[1] - top_left[1]) * (p2[0] - top_left[0])
        
        # 图像坐标系(y轴向下)下：
        # 若 cross_product > 0，通常 p1 在右上、p2 在左下；反之交换。
        if cross_product > 0:
            top_right = p1
            bottom_left = p2
        else:
            top_right = p2
            bottom_left = p1

        return top_left, top_right, bottom_left

    def _find_alignment(self, binary, est_x, est_y):
        """
        在估算位置附近搜索 Alignment Pattern (嵌套一层)
        如果找不到就返回 None，由上层退化处理
        """
        # 初级版本: 为了容错与简化，可直接先用投影点。
        # 进阶版本: 框出一个感兴趣区域(ROI)，用 _find_finder_patterns 类似的寻点逻辑查一层嵌套。
        # 这里暂不强制实现精准 Alignment 搜索，因为对于短距离拍摄，仿射补偿通常够用，留空等进阶接入。
        return None