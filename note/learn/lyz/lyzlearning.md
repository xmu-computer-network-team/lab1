### 需求思考
- 项目评分时有效传输位遇到第一个错误就停止了，所以先考虑可靠性

### 错误处理
- crc可以类似为一种类似哈希校验的方式，可以放在色块的最后32个进行校验

### 像素点物理距离计算
- 系统里查出显示器27英寸,原分辨率2560 1440,放缩分辨率为1600 900,1英寸是25.4mm
- 总像素除以总距离
$$d = \frac{27 * 25.4}{\sqrt{2560^2 + 1440^2}}  \approx \mathbf{0.2335mm}$$
- 总共2560个像素点，软件只分配了1600个，所以每个像素点占据<br>
0.2335 * 2560/1600 = 0.3736mm

### git
- git help revisions 查操作对象名称
- HEAD~1 表上次提交的上次

### python虚拟环境
- 创建环境:python3 -m venv (虚拟环境名字)
- 激活环境：source 路径里的activate激活
- 命令查询
    - python3 --help
    - python3 -m venv --help 都能查帮助
- 环境导出:python -m pip freeze > requirements.txt

### python回顾
- -> 用来修饰返回值的类型，不强制检查
- def __init__(self):  双下划线
- zeros: Final[_ConstructorEmpty] = ...
    - 类型存根文件语法
    - Final表不可重新赋值
    - 中括号内是类型
    - ...表实现在别处

### 计图
- color=255表白色