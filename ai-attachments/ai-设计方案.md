# 可见光通信编解码方案 v1.0

## 一、项目概述

将二进制文件编码为黑白二维码视频，在屏幕上播放，用手机摄像头拍摄后解码还原文件。

**核心策略：宁丢不错。** 评分规则要求从第一个 bit 开始计，遇到第一个未检出的错误就截断。因此：
- 用黑白编码（1 bit/块），可靠性远优于彩色
- 用 CRC-32 强校验（未检出概率 1/43亿）
- 对低置信度的 bit 主动标记为"丢失"，不猜

---

## 二、编码方案

### 2.1 基本参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 视频分辨率 | 1920 × 1080 | 全高清 |
| 块大小 | 8 × 8 像素（初始），可调至 6×6 | 每块表示 1 bit |
| 网格尺寸 | 240 列 × 135 行 = 32,400 块 | 1920/8 × 1080/8 |
| 颜色 | 黑 = 0，白 = 1 | 仅两色 |
| 帧率 | 24 fps | 可调至 30 |
| 视频编码 | MJPG 或无损 | 避免 H.264 压缩破坏细节 |

### 2.2 帧布局

```
240 列 × 135 行 (8px块)
┌──────────┬─────────────────────────────────────┬──────────┐
│ Finder A │              帧头区域                │ Finder B │
│  7×7 块  │                                      │  7×7 块  │
│          │ [奇偶1b][帧号12b][数据长度16b][CRC8]  │          │
├──────────┴─────────────────────────────────────┴──────────┤
│ 分隔带 (第7行全白)                                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│                       数 据 区                            │
│                                                          │
│          每段: 120 bits 数据 + 32 bits CRC-32             │
│          (共 152 bits/段)                                 │
│                                                          │
│          S 形扫描顺序 (从左到右再从右到左蛇形)              │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ 分隔带 (第127行全白)                                      │
├──────────┬─────────────────────────────────────┬─────────┤
│ Finder C │              填充区域                │ Align D │
│  7×7 块  │                                      │  5×5 块 │
└──────────┴─────────────────────────────────────┴─────────┘
```

### 2.3 定位图案 (Finder Pattern)

采用类 QR 码的 Finder Pattern，三个角各放一个 7×7 块的定位图案。

```
█ █ █ █ █ █ █
█ ░ ░ ░ ░ ░ █
█ ░ █ █ █ ░ █
█ ░ █ █ █ ░ █
█ ░ █ █ █ ░ █
█ ░ ░ ░ ░ ░ █
█ █ █ █ █ █ █
```

比例 1:1:3:1:1（黑:白:黑:白:黑），与标准 QR 码一致。便于使用成熟的检测算法。

**Alignment Pattern** 放在右下角，5×5 块：

```
█ █ █ █ █
█ ░ ░ ░ █
█ ░ █ ░ █
█ ░ ░ ░ █
█ █ █ █ █
```

四个图案提供四个定位点，用于透视变换矫正。

### 2.4 帧头格式

帧头紧跟在第 0 行的 Finder A 和 Finder B 之间（列 7 到列 232），共 226 个块可用。

| 字段 | 位数 | 说明 |
|------|------|------|
| 奇偶标志 | 1 bit | 奇数帧=1，偶数帧=0，用于帧同步和去重 |
| 帧序号 | 12 bits | 0~4095 循环，支持识别丢帧和重复帧 |
| 数据长度 | 16 bits | 本帧有效数据段数量 |
| 帧头 CRC-8 | 8 bits | 帧头自身的校验 |
| **合计** | **37 bits** | 剩余块为预留/填充 |

### 2.5 数据区编码

#### 分段结构

```
┌──────────────────┬──────────────┐
│  120 bits 数据    │ 32 bits CRC │  = 152 bits/段
└──────────────────┴──────────────┘
```

- 每段 15 字节数据 + 4 字节 CRC-32
- 纠错效率：120/152 = 78.9%
- CRC-32 多项式：0x04C11DB7（标准 IEEE 802.3）

#### 扫描顺序

数据区（第 8 行到第 126 行，240 列）按 S 形蛇形扫描：

```
第 8 行:  → → → → → (列 0 到 239)
第 9 行:  ← ← ← ← ← (列 239 到 0)
第 10 行: → → → → →
...
```

### 2.6 容量计算

```
总块数:            240 × 135 = 32,400
定位图案:          7×7 × 3 + 5×5 = 172 块
分隔带:            7×1 × 4 边 + 分隔行 × 2 ≈ 508 块
帧头:              37 块（占用第 0 行部分）
────────────────────────────────────────
可用数据块:         ≈ 31,683 块 = 31,683 bits

每段 152 bits:      31,683 / 152 = 208 段
有效数据:           208 × 120 = 24,960 bits = 3,120 bytes/帧
```

---

## 三、预期效率计算

### 3.1 方案 A — 保守方案 (8px 块, 24fps)

```
有效数据/帧:     24,960 bits (3,120 bytes)
帧率:            24 fps
────────────────────────────────────────
理论传输率:       24,960 × 24 = 599,040 bps
                = 74,880 bytes/s ≈ 73.1 kB/s

考虑实际因素（约 80% 帧成功解码）:
实际传输率:       599,040 × 0.8 ≈ 479,232 bps ≈ 58.5 kB/s
```

### 3.2 方案 B — 进阶方案 (6px 块, 24fps)

```
网格:            320 × 180 = 57,600 块
可用数据块:       ≈ 56,400 块
段数:            56,400 / 152 = 371 段
有效数据/帧:     371 × 120 = 44,520 bits (5,565 bytes)
帧率:            24 fps
────────────────────────────────────────
理论传输率:       44,520 × 24 = 1,068,480 bps
                = 133,560 bytes/s ≈ 130.4 kB/s

考虑实际因素（约 70% 帧成功解码，块小了识别率下降）:
实际传输率:       1,068,480 × 0.7 ≈ 747,936 bps ≈ 91.3 kB/s
```

### 3.3 方案 C — 提高帧率 (8px 块, 30fps)

```
有效数据/帧:     24,960 bits
帧率:            30 fps
────────────────────────────────────────
理论传输率:       24,960 × 30 = 748,800 bps ≈ 91.5 kB/s
实际(80%):       ≈ 73.2 kB/s
```

### 3.4 对比参考代码

```
参考代码 (黑白, 10px, 20fps):  ≈ 46 kB/s (理论)
参考代码 (4色, 10px, 20fps):   ≈ 91 kB/s (理论)
────────────────────────────────────────
我们方案 A (黑白, 8px, 24fps): ≈ 73 kB/s (理论) — 超过参考BW方案 59%
我们方案 B (黑白, 6px, 24fps): ≈ 130 kB/s (理论) — 超过参考4色方案 43%
```

**注：以上均为理论值。实际效果取决于拍摄条件（手机型号、距离、光照）。建议先用方案 A 跑通，再切方案 B 提速。**

---

## 四、解码方案

### 4.1 解码流程

```
拍摄视频
   ↓
逐帧提取 (OpenCV VideoCapture)
   ↓
灰度化 + 自适应二值化 (OTSU 或局部自适应阈值)
   ↓
Finder Pattern 检测 (1:1:3:1:1 比例扫描)
   ↓
定位四个锚点 (3 Finder + 1 Alignment)
   ↓
透视变换矫正 (cv2.getPerspectiveTransform + warpPerspective)
   ↓
按网格采样每个块中心像素
   ↓
判定黑/白 + 计算置信度
   ↓
帧头解析 → 帧序号去重/排序
   ↓
逐段 CRC-32 校验
   ↓
通过 → 取数据 / 失败 → 标记为丢失
   ↓
拼接所有段 → 输出文件
```

### 4.2 置信度机制

每个块在采样时，不仅判定 0/1，还计算置信度：

```python
# 矫正后图像中，块 (row, col) 中心像素值 (0~255)
pixel_value = corrected_img[cy, cx]

if pixel_value < LOW_THRESHOLD:       # 例如 < 60
    bit = 0, confidence = HIGH
elif pixel_value > HIGH_THRESHOLD:     # 例如 > 195
    bit = 1, confidence = HIGH
else:
    bit = 0 if pixel_value < 128 else 1
    confidence = LOW   # 这个 bit 不可靠
```

当一个段内存在低置信度 bit 且 CRC-32 校验失败时，整段标记为"丢失"。

---

## 五、代码架构建议

### 5.1 项目结构

```
project/
├── encoder/
│   ├── encoder.py          # 入口: encode in.bin out.mp4 1000
│   ├── frame_builder.py    # 生成单帧图像
│   ├── data_formatter.py   # 文件 → 分段 + CRC
│   └── video_writer.py     # 帧序列 → 视频文件
├── decoder/
│   ├── decoder.py          # 入口: decode in.mp4 out.bin
│   ├── frame_reader.py     # 视频 → 逐帧提取
│   ├── locator.py          # Finder/Alignment 检测 + 透视矫正
│   ├── grid_sampler.py     # 矫正图 → 提取 bit 矩阵
│   └── data_recovery.py    # bit 矩阵 → CRC 校验 → 恢复文件
├── common/
│   ├── config.py           # 所有参数常量
│   ├── crc.py              # CRC-32 / CRC-8 实现
│   └── pattern.py          # 定位图案的生成与检测逻辑
└── tests/
    ├── test_encode_decode.py   # 编码后直接解码，验证数据一致
    └── test_frame.py           # 单帧生成与识别测试
```

### 5.2 关键文件：config.py

所有可调参数集中在一个文件里，方便调优：

```python
# common/config.py

# === 帧参数 ===
FRAME_WIDTH = 1920          # 视频宽度 (像素)
FRAME_HEIGHT = 1080         # 视频高度 (像素)
BLOCK_SIZE = 8              # 每个块的像素边长 (可改为6)
FPS = 24                    # 帧率

# === 自动计算的网格参数 ===
GRID_COLS = FRAME_WIDTH // BLOCK_SIZE    # 240
GRID_ROWS = FRAME_HEIGHT // BLOCK_SIZE   # 135

# === 定位图案 ===
FINDER_SIZE = 7             # Finder Pattern 边长 (块数)
ALIGN_SIZE = 5              # Alignment Pattern 边长 (块数)
SEPARATOR_WIDTH = 1         # 分隔带宽度 (块数)

# === 帧头 ===
HEADER_PARITY_BITS = 1
HEADER_FRAME_ID_BITS = 12
HEADER_DATA_LEN_BITS = 16
HEADER_CRC_BITS = 8
HEADER_TOTAL_BITS = 37

# === 数据段 ===
SEGMENT_DATA_BITS = 120     # 每段数据位数 (15 字节)
SEGMENT_CRC_BITS = 32       # CRC-32 位数
SEGMENT_TOTAL_BITS = SEGMENT_DATA_BITS + SEGMENT_CRC_BITS  # 152

# === 解码阈值 ===
BLACK_THRESHOLD = 60        # 低于此值判定为黑 (bit=0)
WHITE_THRESHOLD = 195       # 高于此值判定为白 (bit=1)
CONFIDENCE_THRESHOLD = 0.7  # 置信度低于此值标记为不可靠
```

### 5.3 关键文件：frame_builder.py

```python
# encoder/frame_builder.py
import numpy as np
import cv2
from common.config import *
from common.pattern import generate_finder_pattern, generate_align_pattern

class FrameBuilder:
    """负责将一帧的 bit 数据绘制成图像"""

    def __init__(self):
        # 预计算定位图案等不变的部分
        self.template = self._build_template()
        # 预计算数据区的扫描坐标序列
        self.scan_order = self._build_scan_order()

    def _build_template(self) -> np.ndarray:
        """生成包含定位图案和分隔带的空白模板帧"""
        frame = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)

        # 画三个 Finder Pattern
        self._draw_finder(frame, 0, 0)                                    # 左上
        self._draw_finder(frame, 0, GRID_COLS - FINDER_SIZE)             # 右上
        self._draw_finder(frame, GRID_ROWS - FINDER_SIZE, 0)            # 左下

        # 画 Alignment Pattern (右下)
        ar = GRID_ROWS - ALIGN_SIZE
        ac = GRID_COLS - ALIGN_SIZE
        self._draw_align(frame, ar, ac)

        # 画分隔带 (定位图案外围一圈白色)
        self._draw_separators(frame)

        return frame

    def _draw_finder(self, frame, row, col):
        """在 (row, col) 处画 7x7 的 Finder Pattern"""
        # 7x7 finder pattern: 外圈黑, 次圈白, 内核3x3黑
        pattern = generate_finder_pattern()  # 返回 7x7 的 0/1 数组
        for r in range(FINDER_SIZE):
            for c in range(FINDER_SIZE):
                x = (col + c) * BLOCK_SIZE
                y = (row + r) * BLOCK_SIZE
                color = 255 if pattern[r][c] == 1 else 0
                frame[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = color

    def _draw_align(self, frame, row, col):
        """在 (row, col) 处画 5x5 的 Alignment Pattern"""
        pattern = generate_align_pattern()  # 返回 5x5 的 0/1 数组
        for r in range(ALIGN_SIZE):
            for c in range(ALIGN_SIZE):
                x = (col + c) * BLOCK_SIZE
                y = (row + r) * BLOCK_SIZE
                color = 255 if pattern[r][c] == 1 else 0
                frame[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = color

    def _draw_separators(self, frame):
        """画分隔带"""
        # 具体实现: 在 finder pattern 外围画一行/列白色块
        pass  # 根据实际布局实现

    def _build_scan_order(self) -> list:
        """预计算数据区所有块的坐标，按S形蛇形扫描排列"""
        coords = []
        data_row_start = FINDER_SIZE + SEPARATOR_WIDTH      # 第 8 行
        data_row_end = GRID_ROWS - FINDER_SIZE - SEPARATOR_WIDTH  # 第 127 行
        for row in range(data_row_start, data_row_end):
            if (row - data_row_start) % 2 == 0:
                col_range = range(0, GRID_COLS)             # 左→右
            else:
                col_range = range(GRID_COLS - 1, -1, -1)    # 右→左
            for col in col_range:
                coords.append((row, col))
        return coords

    def build_frame(self, frame_id: int, segments: list) -> np.ndarray:
        """
        生成一帧完整图像

        Args:
            frame_id: 帧序号 (0~4095)
            segments: 该帧的数据段列表，每段是 bytes

        Returns:
            numpy 图像数组 (H, W), dtype=uint8
        """
        frame = self.template.copy()

        # 1. 写入帧头
        header_bits = self._encode_header(frame_id, len(segments))
        self._write_bits_to_header_area(frame, header_bits)

        # 2. 写入数据段
        all_bits = []
        for seg in segments:
            all_bits.extend(seg)  # 每段已包含 data + CRC-32
        self._write_bits_to_data_area(frame, all_bits)

        return frame

    def _encode_header(self, frame_id, segment_count):
        """编码帧头为 bit 列表"""
        bits = []
        bits.append(frame_id % 2)                           # 奇偶标志
        bits.extend(int_to_bits(frame_id, 12))              # 帧序号
        bits.extend(int_to_bits(segment_count, 16))         # 数据段数
        crc = crc8(bits)
        bits.extend(int_to_bits(crc, 8))                    # 帧头CRC
        return bits

    def _write_bits_to_data_area(self, frame, bits):
        """将 bit 列表按扫描顺序写入数据区"""
        for i, bit in enumerate(bits):
            if i >= len(self.scan_order):
                break
            row, col = self.scan_order[i]
            x = col * BLOCK_SIZE
            y = row * BLOCK_SIZE
            color = 255 if bit == 1 else 0
            frame[y:y+BLOCK_SIZE, x:x+BLOCK_SIZE] = color


def int_to_bits(value, length):
    """整数转固定长度 bit 列表 (MSB first)"""
    return [(value >> (length - 1 - i)) & 1 for i in range(length)]
```

### 5.4 关键文件：data_formatter.py

```python
# encoder/data_formatter.py
import struct
from common.config import SEGMENT_DATA_BITS

SEGMENT_DATA_BYTES = SEGMENT_DATA_BITS // 8  # 15 字节

def file_to_segments(file_path: str) -> list:
    """
    读取文件，切分为固定大小的段，每段附加 CRC-32

    Returns:
        list of bit lists, 每个元素是 152 个 bit 的列表
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read()

    segments = []
    offset = 0
    while offset < len(raw_data):
        chunk = raw_data[offset:offset + SEGMENT_DATA_BYTES]
        if len(chunk) < SEGMENT_DATA_BYTES:
            chunk = chunk + b'\x00' * (SEGMENT_DATA_BYTES - len(chunk))  # 补零

        # 计算 CRC-32
        crc = zlib_crc32(chunk) & 0xFFFFFFFF
        crc_bytes = struct.pack('>I', crc)  # 大端序 4 字节

        # 转为 bit 列表
        segment_bits = bytes_to_bits(chunk) + bytes_to_bits(crc_bytes)
        segments.append(segment_bits)

        offset += SEGMENT_DATA_BYTES

    return segments


def bytes_to_bits(data: bytes) -> list:
    """字节串转 bit 列表"""
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def zlib_crc32(data: bytes) -> int:
    """计算 CRC-32，使用 Python 标准库"""
    import zlib
    return zlib.crc32(data)
```

### 5.5 关键文件：locator.py（解码器最核心的部分）

```python
# decoder/locator.py
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
        # 1. 转灰度
        gray = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)

        # 2. 自适应二值化 (比固定阈值 80 强很多)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=51, C=10
        )
        # 或者用 OTSU:
        # _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. 寻找三个 Finder Pattern
        finders = self._find_finder_patterns(binary)
        if len(finders) < 3:
            return None

        # 4. 排列三个 finder: 左上、右上、左下
        top_left, top_right, bottom_left = self._order_finders(finders)

        # 5. 估算右下 Alignment Pattern 位置并搜索
        est_x = top_right[0] - top_left[0] + bottom_left[0]
        est_y = top_right[1] - top_left[1] + bottom_left[1]
        align = self._find_alignment(binary, est_x, est_y)
        if align is None:
            # 退化: 用三点做仿射变换
            align = (est_x, est_y)

        # 6. 四点透视变换
        src = np.float32([top_left, top_right, bottom_left, align])
        dst = np.float32([
            [FINDER_SIZE/2 * BLOCK_SIZE,  FINDER_SIZE/2 * BLOCK_SIZE],
            [(GRID_COLS - FINDER_SIZE/2) * BLOCK_SIZE, FINDER_SIZE/2 * BLOCK_SIZE],
            [FINDER_SIZE/2 * BLOCK_SIZE,  (GRID_ROWS - FINDER_SIZE/2) * BLOCK_SIZE],
            [(GRID_COLS - ALIGN_SIZE/2) * BLOCK_SIZE, (GRID_ROWS - ALIGN_SIZE/2) * BLOCK_SIZE],
        ])
        M = cv2.getPerspectiveTransform(src, dst)
        corrected = cv2.warpPerspective(
            gray, M,
            (GRID_COLS * BLOCK_SIZE, GRID_ROWS * BLOCK_SIZE)
        )
        return corrected

    def _find_finder_patterns(self, binary):
        """
        扫描二值图像，找到 1:1:3:1:1 比例的 Finder Pattern 中心点
        算法与 ZXing / 参考代码一致: 逐行扫描状态机
        """
        # 实现要点:
        # 1. 逐行扫描，维护 5 段计数器 (黑白黑白黑)
        # 2. 当比例符合 1:1:3:1:1 时，做十字交叉验证
        # 3. 返回所有候选中心点 [(x, y), ...]
        pass  # 可移植参考代码的 FinderPatternFinder 逻辑

    def _order_finders(self, finders):
        """
        将三个 finder 排序为: 左上、右上、左下
        方法: 找最远的两个点确定对角线，第三个点用叉积判断方向
        """
        # 可移植参考代码的 OrderBestPatterns 逻辑
        pass

    def _find_alignment(self, binary, est_x, est_y):
        """
        在估算位置附近搜索 Alignment Pattern (1:1:1 比例)
        搜索范围逐步扩大
        """
        pass
```

### 5.6 关键文件：grid_sampler.py

```python
# decoder/grid_sampler.py
import numpy as np
from common.config import *

class GridSampler:
    """从矫正后的图像中提取 bit 矩阵和置信度"""

    def sample(self, corrected_gray: np.ndarray):
        """
        输入: 矫正后的灰度图
        输出: (bits, confidences) 两个二维数组，shape=(GRID_ROWS, GRID_COLS)
        """
        bits = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.uint8)
        confidences = np.zeros((GRID_ROWS, GRID_COLS), dtype=np.float32)

        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                # 采样块中心的 3x3 区域取均值，比单像素更稳定
                cy = row * BLOCK_SIZE + BLOCK_SIZE // 2
                cx = col * BLOCK_SIZE + BLOCK_SIZE // 2
                region = corrected_gray[cy-1:cy+2, cx-1:cx+2]
                value = float(np.mean(region))

                # 判定 bit 值和置信度
                if value < BLACK_THRESHOLD:
                    bits[row, col] = 0
                    confidences[row, col] = (BLACK_THRESHOLD - value) / BLACK_THRESHOLD
                elif value > WHITE_THRESHOLD:
                    bits[row, col] = 1
                    confidences[row, col] = (value - WHITE_THRESHOLD) / (255 - WHITE_THRESHOLD)
                else:
                    # 灰色地带: 硬判但置信度低
                    bits[row, col] = 0 if value < 128 else 1
                    confidences[row, col] = abs(value - 128) / 128 * 0.5

        return bits, confidences
```

### 5.7 关键文件：data_recovery.py

```python
# decoder/data_recovery.py
import struct
import zlib
from common.config import *

class DataRecovery:
    """从 bit 矩阵恢复原始数据"""

    def __init__(self, scan_order):
        self.scan_order = scan_order  # 与编码器相同的扫描顺序

    def recover_frame(self, bits, confidences) -> list:
        """
        从一帧中恢复数据

        Returns:
            list of (segment_data_bytes, is_valid)
            is_valid=False 时该段标记为丢失
        """
        # 1. 读帧头
        header = self._read_header(bits)
        if header is None:
            return []

        frame_id, segment_count = header

        # 2. 按扫描顺序提取数据区 bit 流
        data_bits = []
        data_confs = []
        for row, col in self.scan_order:
            data_bits.append(bits[row, col])
            data_confs.append(confidences[row, col])

        # 3. 逐段校验
        results = []
        for i in range(segment_count):
            start = i * SEGMENT_TOTAL_BITS
            end = start + SEGMENT_TOTAL_BITS
            if end > len(data_bits):
                break

            seg_bits = data_bits[start:end]
            seg_confs = data_confs[start:end]

            payload_bits = seg_bits[:SEGMENT_DATA_BITS]
            crc_bits = seg_bits[SEGMENT_DATA_BITS:]

            payload_bytes = bits_to_bytes(payload_bits)
            received_crc = bits_to_int(crc_bits)
            computed_crc = zlib.crc32(payload_bytes) & 0xFFFFFFFF

            # 检查: CRC 通过 且 没有低置信度 bit
            min_conf = min(seg_confs)
            if computed_crc == received_crc and min_conf > CONFIDENCE_THRESHOLD:
                results.append((payload_bytes, True))
            else:
                results.append((payload_bytes, False))  # 标记为丢失

        return results


def bits_to_bytes(bits) -> bytes:
    """bit 列表转 bytes"""
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte = (byte << 1) | bits[i + j]
        result.append(byte)
    return bytes(result)

def bits_to_int(bits) -> int:
    """bit 列表转整数"""
    value = 0
    for b in bits:
        value = (value << 1) | b
    return value
```

---

## 六、与参考代码的关键差异

| 维度 | 参考代码 | 本方案 |
|------|---------|--------|
| 语言 | C++ | Python |
| 块大小 | 10px (固定) | 8px → 6px (可调) |
| 颜色 | 4色或黑白 | 纯黑白 |
| 二值化 | `threshold(gray, 80)` 固定阈值 | 自适应阈值 (OTSU/Gaussian) |
| 纠错 | CRC-8 (漏检率 1/256) | CRC-32 (漏检率 1/43亿) |
| 帧同步 | 奇偶位 | 12位帧序号 + 奇偶位 |
| 置信度 | 无，硬判 | 有，低置信度标记丢失 |
| 块采样 | 中心单像素 | 中心 3×3 均值 |
| 参数管理 | 硬编码 | 集中 config.py |

---

## 七、依赖库

```bash
pip install opencv-python numpy
```

- `opencv-python`: 图像/视频读写、二值化、透视变换
- `numpy`: 矩阵运算
- `zlib`: CRC-32（Python 内置）
- `struct`: 字节打包（Python 内置）
