3.10：20.03
# commom/config
该文件定义常量
- BLOCK_SIZE 这个参数做了实验，[实验文件](../../../test/argument_test.py)

# common/pattern
该文件定义一些常见样式
- 用numpy创建多维数组带更多可用的对象方法

# encoder/frame_builder
这是帧生成
## draw_pattern
一个函数实现对finder块和align块的作画
- 调用相应的pattern生成函数和大小（5/7）
## build_template
该函数作画模板帧，结合draw_pattern 讲讲一些参数的计算
- 按8逻辑像素为1块的话，总共有135行（0-based）
- 第0块的逻辑像素开始于0逻辑像素，结束于第4逻辑像素，所以第n块<br>
开始于第 n * BLOCK_SIZE,结束于 n * (BLOCK_SIZE + 1) - 1,用0based去数第几块就不会混乱
- 举ALIGN块，ALIGIN块应该开始于第130行，结束于第134行，所以用GRID_ROWS - ALIGN_SIZE
## build_scan_order
蛇形扫描提高扫描效率
```python
偶数列的话，就从左往右取列表
if (row - data_row_start) % 2 == 0:

奇数列，从右往左
col_range = range(GRID_COLS - 1, -1, -1) 左闭右开不达-1，步长为-1
```