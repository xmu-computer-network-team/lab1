# 迭代1
## commom/config
该文件定义常量
- BLOCK_SIZE 这个参数做了实验，[实验文件](../../../test/argument_test.py)

## common/pattern
该文件定义一些常见样式
- 用numpy创建多维数组带更多可用的对象方法

## common/crc
crc的本质是利用余数的特异性进行校验，这里的除法是模2除法，通过异或运算使得余数具有离散性，crc32已有标准库实现，这里crc8实质上是在模拟模2除法，试着讲解
```python
extended_bits = bits + [0, 0, 0, 0, 0, 0, 0, 0]
补8个0，使得刚好能进行8次余数运算

crc = (crc << 1) | bit
python的数字有“无限长度”特性
crc左移1位最右边的位变成0
| 按位或运算可以实现对bit数据的复制

0x100 的二进制是 1 0000 0000
if crc & 0x100: 这个语句实现了模二除法里最高位是否为1的检查

crc ^= 0x107 
做除法——对生成多项式做异或运算

crc &= 0xFF
最后一步用来保持位数
```

## encoder/frame_builder
这是帧生成
### draw_pattern
一个函数实现对finder块和align块的作画
- 调用相应的pattern生成函数和大小（5/7）
### build_template
该函数作画模板帧，结合draw_pattern 讲讲一些参数的计算
- 按8逻辑像素为1块的话，总共有135行（0-based）
- 第0块的逻辑像素开始于0逻辑像素，结束于第4逻辑像素，所以第n块<br>
开始于第 n * BLOCK_SIZE,结束于 n * (BLOCK_SIZE + 1) - 1,用0based去数第几块就不会混乱
- 举ALIGN块，ALIGIN块应该开始于第130行，结束于第134行，所以用GRID_ROWS - ALIGN_SIZE
### build_scan_order
蛇形扫描提高扫描效率
```python
偶数列的话，就从左往右取列表
if (row - data_row_start) % 2 == 0:

奇数列，从右往左
col_range = range(GRID_COLS - 1, -1, -1) 左闭右开不达-1，步长为-1
```
### int_to_bits
```python
value >> length - 1 - i 把正在读取的那一位移到最低位
&1 把最低位取出来
```

# 迭代2
迭代1方案在写最后的解码模块时，图像识别率和误码率都太高了。<br>
分析原因后选择了重构，不再手写定位模块，用pyzbar库实现<br>
现介绍跑通 图片拍摄并解码闭环的代码设计

## encode/file_splitter
### 参数解析
- 一个file被切成多个segment
- 一帧的最大数据容量是 MAX_RAW_BYTES
- 一个segment最多255帧，所以最大容量是 max_raw * 255

### 思路
- 用offset做游标，每次切seg_max_raw大小，分成多个segment
- 然后按编码方式计算帧头，把帧头和数据用base64编码写入字节列表

### 为什么用base64编码
因为测试过程中，qr库读取字节时，会把一些字节用utf-8处理，为了避免这种现象，用base64最稳定

## encode/frame_builder

### 为什么能这么写 np.array(img.convert('L'))
因为qr库这里返回的是一个pillow image对象，而pillow image实现了numpy接口，所以可以把一张灰度图转numpy数组对象

## decpde/locator
直接用qr库