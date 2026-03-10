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