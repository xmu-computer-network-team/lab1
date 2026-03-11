### 渲染问题
表现:tkinkter没有按照显示设备的大小，去相对地绘制图片<br>
环境:笔记本电脑连接显示器,python运行环境为wsl<br>
原因：tkinter默认dpi不感知，也就是它默认没法处理高分辨率显示器的缩放<br>
```python
w = root.winfo_screenwidth()
h = root.winfo_screenheight()
```
解决办法:调用系统接口
```python
w = int(ctypes.windll.user32.GetSystemMetrics(0))
h = int(ctypes.windll.user32.GetSystemMetrics(1))
```
### python模块导入问题
表现：
```bash
(.venv) ➜  lab1 git:(main) ✗ python test/template_test.py
Traceback (most recent call last):
  File "/home/jade/projects/school-network-lab1/lab1/test/template_test.py", line 3, in <module>
    from encoder.frame_builder import FrameBuilder
ModuleNotFoundError: No module named 'encoder'
```
原因：运行某个文件时，就会以那个文件在的目录为工作目录
解决方法：<br>
在测试脚本开头把它的父目录加入到python的系统路径
- sys.path：把后面的路径参数按前面的索引插入
- os.path.dirname(__file__)返回去掉文件名的路径
- 再补上..刚好是父目录
```python
sys.path.insert(0,os.path.join(os.path.dirname(__file__),".."))
```
