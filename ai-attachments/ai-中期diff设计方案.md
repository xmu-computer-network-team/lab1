# 中期设计调整方案

> 基于实验验证的结论，对原设计方案的关键调整。实验驱动，不改则继续用原方案。

---

## 一、实验结论

### 实验0：编码器自检
- 结果：**5/5 通过**
- 确认了 `FrameBuilder` 生成的帧结构正确
- 修复了 parity bug（`build_scan_order()` 中 `data_row_end` 应为 `data_row_start`）

### 实验1：QR 码定位能力测试
- **OpenCV QRCodeDetector**: 5/7（多尺度增强后）
- **pyzbar (zbar C 库)**: **7/7 全部成功**
- 关键发现：所有图片都在 **0.3x 缩放** 尺度下识别成功
- 结论：pyzbar 对手机拍摄的高分辨率照片识别率远高于 OpenCV 内置检测器

---

## 二、核心设计变更：locator.py 实现路线

### 原方案
手写 Finder Pattern 检测（1:1:3:1:1 比例状态机），参考 ZXing 思路自己实现定位。

### 新方案
**用 pyzbar 替代 Finder Pattern 检测 + 定位**，手写代码专注在数据解析。

### 为什么可以这样做
1. 课设要求"编码方案原创"，解码端无限制
2. pyzbar 能返回标准 QR 码的**四个角点坐标**（`.polygon`）
3. pyzbar 不认识我们的自定义数据格式（`.data` 对我们无用），但它能做定位
4. 手写版 locator 失败率 50%，pyzbar 定位成功率 100%

### pyzbar 返回值分析
```python
from pyzbar.pyzbar import decode, ZBarSymbol

decoded = decode(img, symbols=[ZBarSymbol.QRCODE])
# decoded[0].polygon → [(x,y), ...]  4个角点坐标（像素精度）
# decoded[0].data    → 标准QR解码内容（对我们无用）
```

pyzbar **只负责定位**，返回四个角点坐标，不做透视矫正，不解析数据。

### 新的解码流程
```
拍摄视频
   ↓
逐帧提取 (VideoCapture)
   ↓
pyzbar 检测角点坐标
   ↓
透视变换矫正（手写 cv2.getPerspectiveTransform + warpPerspective）
   ↓
按 zigzag 顺序逐块采样中心像素 → 判定 0/1
   ↓
帧头解析 → frame_id + segment_count
   ↓
逐段 CRC-32 校验
   ↓
拼接所有段 → 输出文件
```

### locator.py 职责重新划分
| 模块 | 职责 | 实现方式 |
|------|------|---------|
| `locator.py` | 定位角点 + 透视矫正 | pyzbar 定位 + 手写透视变换 |
| `grid_sampler.py` | 块采样 + 判定 0/1 | 手写（不变） |
| `data_recovery.py` | CRC 校验 + 数据恢复 | 手写（不变） |

---

## 三、实现细节

### 角点坐标系说明
pyzbar 返回的 `polygon` 角点顺序：**左上 → 右上 → 右下 → 左下**

```
0 ---- 1
|      |
|      |
3 ---- 2
```

### 透视变换目标
矫正后的图像尺寸为 `GRID_COLS * BLOCK_SIZE × GRID_ROWS * BLOCK_SIZE`（1920×1080），角点目标坐标：

```python
dst = np.float32([
    [FINDER_SIZE/2 * BLOCK_SIZE,  FINDER_SIZE/2 * BLOCK_SIZE],        # 左上
    [(GRID_COLS - FINDER_SIZE/2) * BLOCK_SIZE, FINDER_SIZE/2 * BLOCK_SIZE],  # 右上
    [(GRID_COLS - ALIGN_SIZE/2) * BLOCK_SIZE, (GRID_ROWS - ALIGN_SIZE/2) * BLOCK_SIZE],  # 右下
    [FINDER_SIZE/2 * BLOCK_SIZE,  (GRID_ROWS - FINDER_SIZE/2) * BLOCK_SIZE],  # 左下
])
```

### 缩放策略
实验证明 **0.3x 缩放** 检测效果最好。在 `decode()` 前先对图像做缩放，或尝试多个尺度取成功率最高的。

---

## 四、与原方案差异对比

| 模块 | 原方案 | 新方案 |
|------|--------|--------|
| Finder Pattern 检测 | 手写 1:1:3:1:1 状态机 | pyzbar |
| 角点排序 | OrderBestPatterns 手写 | 直接用 pyzbar polygon 顺序 |
| 透视矫正 | 手写 | 手写（不变） |
| 数据解析 | 手写 | 手写（不变） |

**唯一变化：Finder Pattern 检测环节由 pyzbar 接管。**

---

## 五、下一步

1. 实现 `locator.py` 的 pyzbar 版本
2. 用实验1 的照片做离线测试（直接读图片，不走视频）
3. 验证透视矫正 + 块采样的准确性
4. Sprint 1 图片闭环：用 encoder 生成帧 → 拍照片 → decoder 解码 → 比对 MD5
