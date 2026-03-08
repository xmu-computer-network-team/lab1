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
