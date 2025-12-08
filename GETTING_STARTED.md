# 🚀 新手入门指南

欢迎来到 **Draw & Guess（你画我猜）** 项目！这是一份专为零基础开发者准备的完整入门指南。

---

## 📖 目录

1. [项目是什么？](#项目是什么)
2. [完整文件结构说明](#完整文件结构说明)
3. [核心概念解释](#核心概念解释)
4. [如何开始开发](#如何开始开发)
5. [常见问题解答](#常见问题解答)

---

## 🎮 项目是什么？

### 简单来说
这是一个**多人在线"你画我猜"游戏**，就像你可能玩过的手机 App 一样：
- 👨‍🎨 一个玩家画画
- 🤔 其他玩家猜词
- 🏆 猜对得分

### 技术架构
- **编程语言**: Python（一种简单易学的编程语言）
- **游戏库**: Pygame（用来画图、显示窗口）
- **网络通信**: Socket（让多个玩家的电脑能互相通信）

### 工作原理
```
[玩家A的电脑（客户端）] ←→ [服务器（后端）] ←→ [玩家B的电脑（客户端）]
```

---

## 📁 完整文件结构说明

### 根目录文件（项目配置）

#### 📄 `.editorconfig`
**作用**: 统一代码风格（比如缩进用几个空格）
**新手需要了解**: 不用管它，编辑器会自动读取
**内容示例**: 设置缩进、换行符等规则

#### 📄 `.env.example`
**作用**: 环境变量模板（存放配置信息，如服务器地址）
**新手需要了解**: 复制为 `.env` 文件后可以修改配置
**内容**:
- `SERVER_HOST=127.0.0.1` - 服务器地址
- `SERVER_PORT=5555` - 服务器端口
- `DEBUG=False` - 是否开启调试模式

#### 📄 `.gitignore`
**作用**: 告诉 Git 哪些文件不要上传（如临时文件、密码）
**新手需要了解**: 不用修改
**常见内容**:
- `__pycache__/` - Python 自动生成的缓存
- `venv/` - 虚拟环境文件夹
- `.env` - 包含敏感信息的配置文件

#### 📄 `.pre-commit-config.yaml`
**作用**: 在提交代码前自动检查代码质量
**新手需要了解**: 运行 `pre-commit install` 后自动生效
**功能**: 自动格式化代码、检查错误

#### 📄 `pyproject.toml`
**作用**: ⭐ 项目的主配置文件（现代 Python 项目标准）
**新手需要了解**: 这是最重要的配置文件
**包含内容**:
- 项目名称、版本、作者
- 依赖包列表
- 测试、格式化工具配置

#### 📄 `setup.py`
**作用**: 传统的 Python 项目安装脚本
**新手需要了解**: 为了兼容旧版本 pip，与 `pyproject.toml` 作用类似

#### 📄 `requirements.txt`
**作用**: ⭐ 列出项目需要的所有外部库
**新手需要了解**: 运行 `pip install -r requirements.txt` 安装依赖
**内容**: `pygame>=2.5.0` - 游戏库

#### 📄 `MANIFEST.in`
**作用**: 打包时包含哪些非代码文件（如图片、音效）
**新手需要了解**: 暂时不用关心

#### 📄 `start.bat` / `start.sh`
**作用**: ⭐ 快速启动脚本
**新手需要了解**:
- Windows 双击 `start.bat`
- Linux/Mac 运行 `./start.sh`
- 提供菜单选择启动服务器或客户端

#### 📄 `README.md`
**作用**: ⭐ 项目介绍和使用说明
**新手需要了解**: 这是你应该第一个阅读的文件

#### 📄 `LICENSE`
**作用**: 开源许可证（MIT 许可证 - 可以自由使用、修改）
**新手需要了解**: 说明代码可以被如何使用

#### 📄 `CODE_OF_CONDUCT.md`
**作用**: 社区行为准则
**新手需要了解**: 参与项目的礼仪规范

#### 📄 `CONTRIBUTING.md`
**作用**: 如何为项目贡献代码的指南
**新手需要了解**: 想提交代码时参考

#### 📄 `TODO.md`
**作用**: ⭐ 开发计划和任务清单
**新手需要了解**: 想做点什么？看这里选任务！

#### 📄 `INIT_REPORT.md`
**作用**: 项目初始化完成报告
**新手需要了解**: 了解项目已完成的部分

#### 📄 `SUCCESS_REPORT.md`
**作用**: 初始化成功验证报告
**新手需要了解**: 查看测试结果和项目状态

---

### 📂 `.github/` - GitHub 配置

#### 📄 `.github/CODEOWNERS`
**作用**: 指定代码负责人
**新手需要了解**: 提 PR 时自动通知相关人员

#### 📄 `.github/workflows/ci.yml`
**作用**: ⭐ 自动化测试配置（GitHub Actions）
**新手需要了解**: 每次推送代码会自动运行测试
**内容**:
- 安装依赖
- 运行代码检查
- 运行测试

---

### 📂 `.vscode/` - VS Code 编辑器配置

#### 📄 `.vscode/launch.json`
**作用**: ⭐ 调试配置
**新手需要了解**: 按 F5 可以一键启动调试
**包含配置**:
- 调试服务器
- 调试客户端
- 调试测试

#### 📄 `.vscode/settings.json`
**作用**: VS Code 编辑器设置
**新手需要了解**: 自动配置代码格式化、测试等功能
**功能**:
- 保存时自动格式化
- 启用代码检查
- 配置测试框架

---

### 📂 `src/` - 源代码目录（核心代码）

这是项目的核心，所有游戏代码都在这里！

#### 📄 `src/__init__.py`
**作用**: ⭐ 标识这是一个 Python 包
**新手需要了解**: 每个文件夹都需要这个文件才能被导入
**内容**:
```python
__version__ = "0.1.0"  # 项目版本号
```

---

### 📂 `src/server/` - 服务器端代码

服务器负责连接所有玩家，管理游戏状态。

#### 📄 `src/server/__init__.py`
**作用**: 服务器包初始化
**新手需要了解**: 导入服务器模块时会加载这个文件

#### 📄 `src/server/main.py`
**作用**: ⭐⭐⭐ 服务器启动入口（最重要的文件之一）
**新手需要了解**: 运行 `python src/server/main.py` 启动服务器
**主要功能**:
```python
def main():
    # 1. 配置日志（记录运行信息）
    # 2. 启动服务器
    # 3. 监听客户端连接
    # 4. 处理游戏逻辑
```

#### 📂 `src/server/network/`
**作用**: ⭐ 网络通信模块（处理 Socket 连接）
**新手需要了解**: 这里要实现客户端和服务器的通信
**待实现功能**:
- 接受客户端连接
- 发送/接收消息
- 管理在线玩家列表

#### 📂 `src/server/game/`
**作用**: ⭐ 游戏逻辑模块
**新手需要了解**: 游戏规则在这里实现
**待实现功能**:
- 回合控制（谁该画画）
- 分数计算
- 游戏状态管理

#### 📂 `src/server/models/`
**作用**: ⭐ 数据模型（定义玩家、房间等数据结构）
**新手需要了解**: 定义游戏中的"对象"
**待实现**:
- `Player` 类 - 玩家信息
- `Room` 类 - 房间信息
- `Game` 类 - 游戏状态

---

### 📂 `src/client/` - 客户端代码

客户端是玩家看到的界面和交互部分。

#### 📄 `src/client/__init__.py`
**作用**: 客户端包初始化

#### 📄 `src/client/main.py`
**作用**: ⭐⭐⭐ 客户端启动入口（最重要的文件之一）
**新手需要了解**: 运行 `python src/client/main.py` 启动游戏
**主要功能**:
```python
def main():
    # 1. 初始化 Pygame（游戏库）
    # 2. 创建游戏窗口
    # 3. 游戏主循环（绘图、处理输入）
    # 4. 连接服务器
```

#### 📂 `src/client/ui/`
**作用**: ⭐ 用户界面组件
**新手需要了解**: 按钮、输入框、画布都在这里
**待实现组件**:
- `Button` - 按钮类
- `Canvas` - 画布类
- `ChatBox` - 聊天框类
- `PlayerList` - 玩家列表类

#### 📂 `src/client/game/`
**作用**: ⭐ 客户端游戏逻辑
**新手需要了解**: 处理用户交互、绘图
**待实现功能**:
- 处理鼠标绘图
- 发送绘图数据
- 接收其他玩家的绘图

---

### 📂 `src/shared/` - 共享代码

服务器和客户端都会用到的代码。

#### 📄 `src/shared/__init__.py`
**作用**: 共享包初始化

#### 📄 `src/shared/constants.py`
**作用**: ⭐⭐ 常量定义（重要！）
**新手需要了解**: 所有固定的数值都在这里
**内容示例**:
```python
# 网络配置
DEFAULT_HOST = "127.0.0.1"  # 服务器地址
DEFAULT_PORT = 5555         # 端口号

# 游戏配置
MAX_PLAYERS = 8      # 最多8个玩家
ROUND_TIME = 60      # 每轮60秒

# 窗口配置
WINDOW_WIDTH = 1280  # 窗口宽度
WINDOW_HEIGHT = 720  # 窗口高度

# 颜色定义（RGB）
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
```

#### 📄 `src/shared/protocols.py`
**作用**: ⭐⭐ 通信协议（重要！）
**新手需要了解**: 定义客户端和服务器如何交换消息
**内容示例**:
```python
class Message:
    """消息基类"""
    def __init__(self, msg_type, data):
        self.type = msg_type  # 消息类型（如 "draw", "chat"）
        self.data = data      # 消息数据

    def to_json(self):
        """转换为 JSON 字符串（网络传输用）"""
        return json.dumps({"type": self.type, "data": self.data})
```

---

### 📂 `test/` - 测试代码

确保代码正确运行的测试。

#### 📄 `test/conftest.py`
**作用**: ⭐ pytest 配置和共享测试工具
**新手需要了解**: 定义测试用的假数据（fixtures）
**内容**:
```python
@pytest.fixture
def sample_player_data():
    """测试用的玩家数据"""
    return {
        "name": "TestPlayer",
        "score": 0
    }
```

#### 📂 `test/unit/` - 单元测试
**作用**: 测试单个函数/类是否正常工作

#### 📄 `test/unit/test_basic.py`
**作用**: 基础测试
**内容**:
- 测试项目能否导入
- 测试版本号是否正确

#### 📂 `test/unit/test_server/`
**作用**: 服务器端测试

#### 📄 `test/unit/test_server/test_server_basic.py`
**作用**: 测试服务器基础功能
**测试内容**:
- 能否导入服务器模块
- 配置是否正确

#### 📂 `test/unit/test_client/`
**作用**: 客户端测试

#### 📄 `test/unit/test_client/test_client_basic.py`
**作用**: 测试客户端基础功能

#### 📂 `test/unit/test_shared/`
**作用**: 共享模块测试

#### 📄 `test/unit/test_shared/test_constants.py`
**作用**: 测试常量定义是否正确

---

### 📂 `assets/` - 资源文件

游戏用到的图片、音效等。

#### 📄 `assets/README.md`
**作用**: 资源文件使用说明
**新手需要了解**: 添加图片、音效的规范

#### 📂 `assets/images/`
**作用**: 存放图片（图标、背景、UI 元素）
**格式**: PNG、JPG

#### 📂 `assets/sounds/`
**作用**: 存放音效和音乐
**格式**: WAV、MP3

---

### 📂 `data/` - 数据文件

#### 📄 `data/words.txt`
**作用**: ⭐ 词库（游戏要猜的词）
**新手需要了解**: 一行一个词，游戏会随机选择
**内容示例**:
```
猫
狗
苹果
汽车
...
```

---

### 📂 `docs/` - 文档

#### 📄 `docs/API.md`
**作用**: ⭐ API 文档（接口说明）
**新手需要了解**: 想知道某个函数怎么用？看这里
**内容**:
- 消息协议格式
- 各个类的方法说明
- 数据模型定义

#### 📄 `docs/DEVELOPMENT.md`
**作用**: ⭐⭐ 开发指南（必读！）
**新手需要了解**: 详细的开发流程和规范
**内容**:
- 环境配置步骤
- 代码规范
- 提交规范
- 调试技巧
- 常见问题

---

### 📂 `requirements/` - 依赖配置

#### 📄 `requirements/dev.txt`
**作用**: 开发工具依赖
**新手需要了解**: `pip install -r requirements/dev.txt` 安装开发工具
**包含**:
- black - 代码格式化
- flake8 - 代码检查
- pytest - 测试框架

---

## 🔑 核心概念解释

### 1. 什么是"客户端"和"服务器"？

**简单比喻**:
- **服务器** = 游戏房间的管理员
  - 知道谁在玩
  - 记录分数
  - 决定谁该画画

- **客户端** = 你的游戏窗口
  - 显示画面
  - 发送你画的线条
  - 显示别人画的内容

### 2. 什么是 Socket？

**简单比喻**: Socket 就像电话线
- 客户端"打电话"给服务器
- 服务器"接听"并"回复"
- 可以互相发送信息

### 3. 什么是 Pygame？

**简单说明**: Pygame 是一个游戏库
- 可以创建窗口
- 可以画图形
- 可以处理键盘/鼠标输入
- 可以播放声音

### 4. 什么是"协议"（Protocol）？

**简单比喻**: 协议就像"暗号"
- 客户端说："我要画一条线，从(100,200)到(150,250)"
- 服务器理解后转发给其他玩家
- 大家都用同样的"暗号"，才能互相理解

**具体例子**:
```json
{
  "type": "draw",
  "data": {
    "x": 100,
    "y": 200,
    "color": [0, 0, 0],
    "size": 5
  }
}
```

### 5. 什么是测试？

**简单说明**: 测试就是检查代码是否正常工作
- 写一个函数 `add(a, b)` 返回 a+b
- 测试: `assert add(2, 3) == 5`（检查 2+3 是否等于 5）
- 如果通过，说明函数正确

---

## 🎯 如何开始开发

### 第一步：理解项目结构（现在）
✅ 你正在做这一步！阅读这份文档。

### 第二步：配置开发环境

1. **安装 Python**
   - 下载: https://www.python.org/downloads/
   - 版本: 3.8 或更高

2. **安装依赖**
   ```bash
   # 进入项目目录
   cd Draw-and-Guess

   # 安装运行时依赖
   py -m pip install -r requirements.txt

   # 安装开发工具
   py -m pip install -r requirements/dev.txt
   ```

3. **验证安装**
   ```bash
   # 运行测试
   py -m pytest -v

   # 应该看到: 7 passed
   ```

### 第三步：运行项目

1. **启动服务器**
   ```bash
   py src/server/main.py
   ```

   看到这个说明成功：
   ```
   Draw & Guess 游戏服务器启动中...
   监听地址: 127.0.0.1:5555
   服务器运行中
   ```

2. **启动客户端**（新开一个终端）
   ```bash
   py src/client/main.py
   ```

   应该会弹出一个游戏窗口（目前是白屏，因为还没画UI）

### 第四步：选择第一个任务

从 `TODO.md` 选择一个简单任务，推荐新手从这些开始：

#### 任务1：实现一个简单的 UI 按钮
**位置**: `src/client/ui/button.py`（需要新建）
**难度**: ⭐⭐☆☆☆
**学到**: Pygame 绘图、事件处理

**提示代码**:
```python
import pygame

class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = (100, 100, 255)  # 蓝色

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # TODO: 画文字

    def is_clicked(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)
```

#### 任务2：完善消息协议类
**位置**: `src/shared/protocols.py`
**难度**: ⭐⭐☆☆☆
**学到**: 类的继承、JSON 序列化

**提示**:
```python
class DrawMessage(Message):
    """绘图消息"""
    def __init__(self, x, y, color, size):
        super().__init__("draw", {
            "x": x,
            "y": y,
            "color": color,
            "size": size
        })
```

#### 任务3：实现基础的 Socket 服务器
**位置**: `src/server/network/server.py`（需要新建）
**难度**: ⭐⭐⭐☆☆
**学到**: Socket 编程、多线程

**参考资料**: `docs/DEVELOPMENT.md` 的 Socket 部分

### 第五步：编写测试

每写一个功能，都要写对应的测试！

**示例** - 测试按钮类:
```python
# test/unit/test_client/test_ui.py
def test_button_creation():
    """测试按钮创建"""
    from src.client.ui.button import Button

    btn = Button(0, 0, 100, 50, "点我")
    assert btn.text == "点我"
    assert btn.rect.width == 100

def test_button_click():
    """测试按钮点击检测"""
    from src.client.ui.button import Button

    btn = Button(0, 0, 100, 50, "点我")

    # 点击按钮内部 - 应该返回 True
    assert btn.is_clicked((50, 25)) == True

    # 点击按钮外部 - 应该返回 False
    assert btn.is_clicked((200, 200)) == False
```

### 第六步：提交代码

```bash
# 1. 格式化代码
py -m black src/

# 2. 检查代码
py -m flake8 src/

# 3. 运行测试
py -m pytest -v

# 4. 提交
git add .
git commit -m "feat: 添加 Button 组件"
git push
```

---

## ❓ 常见问题解答

### Q1: 我从来没学过 Python，能参与吗？
**答**: 可以！但建议先学习：
- Python 基础语法（变量、函数、类）
- 推荐教程: https://www.runoob.com/python3/python3-tutorial.html
- 时间: 1-2周

### Q2: 我不懂网络编程，能做什么？
**答**: 可以从 UI 部分开始！
- 实现按钮、输入框等组件
- 完善客户端界面
- 不需要网络知识

### Q3: 什么是虚拟环境？需要用吗？
**答**:
- **作用**: 隔离项目依赖，不影响系统 Python
- **是否需要**: 强烈推荐
- **创建方法**:
  ```bash
  python -m venv venv
  venv\Scripts\activate  # Windows
  source venv/bin/activate  # Linux/Mac
  ```

### Q4: 运行测试报错怎么办？
**答**:
1. 检查是否在项目根目录
2. 检查是否安装了 pytest: `pip install pytest`
3. 查看具体错误信息
4. 搜索错误或在 Issues 提问

### Q5: 代码写在哪个文件？
**答**: 看你要实现什么功能：
- **UI 组件** → `src/client/ui/`
- **服务器网络** → `src/server/network/`
- **游戏逻辑** → `src/server/game/` 或 `src/client/game/`
- **数据模型** → `src/server/models/`
- **通信协议** → `src/shared/protocols.py`

### Q6: 如何调试代码？
**答**:
1. **使用 print()**: 最简单的方法
   ```python
   print(f"当前坐标: {x}, {y}")
   ```

2. **使用 VS Code 调试器**:
   - 打开文件
   - 点击行号左侧设置断点（红点）
   - 按 F5 启动调试

3. **使用日志**:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("这是一条日志")
   ```

### Q7: Git 命令不会用怎么办？
**答**: 基础命令：
```bash
# 查看状态
git status

# 添加文件
git add 文件名

# 提交
git commit -m "说明"

# 推送
git push

# 拉取最新代码
git pull
```

### Q8: 看不懂某个函数怎么办？
**答**:
1. 看函数的文档字符串（三引号部分）
2. 查看 `docs/API.md`
3. 使用 `help()` 函数: `help(Message)`
4. 在 GitHub Issues 提问

### Q9: 如何知道我的改动有没有破坏其他功能？
**答**: 运行测试！
```bash
py -m pytest -v
```
所有测试通过 = 没有破坏功能

### Q10: 项目太大了，不知道从哪开始？
**答**: 推荐顺序：
1. ✅ 阅读 `GETTING_STARTED.md`（这份文档）
2. ✅ 阅读 `README.md`（项目介绍）
3. ✅ 运行一次服务器和客户端
4. ✅ 从 `TODO.md` 选一个 ⭐⭐ 难度的任务
5. ✅ 参考 `docs/DEVELOPMENT.md` 开始编码

---

## 🎓 推荐学习资源

### Python 基础
- [菜鸟教程 Python3](https://www.runoob.com/python3/python3-tutorial.html)
- [廖雪峰 Python 教程](https://www.liaoxuefeng.com/wiki/1016959663602400)

### Pygame
- [Pygame 官方文档](https://www.pygame.org/docs/)
- [Pygame 中文教程](https://eyehere.net/2011/python-pygame-novice-professional-index/)

### Socket 编程
- [Python Socket 编程](https://docs.python.org/zh-cn/3/howto/sockets.html)
- [Socket 通信示例](https://realpython.com/python-sockets/)

### Git
- [Git 教程](https://www.liaoxuefeng.com/wiki/896043488029600)
- [GitHub 快速入门](https://docs.github.com/cn/get-started/quickstart)

---

## 📞 获得帮助

### 遇到问题时
1. **查看文档**: `docs/` 目录
2. **搜索 Issues**: GitHub Issues 页面
3. **提问**: 新建 Issue（详细描述问题、贴上错误信息）
4. **讨论**: GitHub Discussions

### 好的提问方式
```
标题: [客户端] 启动时出现 pygame 错误

描述:
- 系统: Windows 10
- Python 版本: 3.9.13
- 执行命令: py src/client/main.py
- 错误信息:
  [贴上完整的错误信息]
- 已尝试:
  1. 重装了 pygame
  2. 检查了 Python 版本
```

---

## 🎉 总结

恭喜你读完了这份入门指南！现在你应该：

✅ 知道项目是什么
✅ 理解每个文件的作用
✅ 了解核心概念
✅ 知道如何开始开发
✅ 知道遇到问题怎么办

**下一步**:
1. 配置开发环境
2. 运行一次项目
3. 从简单任务开始

**记住**:
- 💪 不要害怕犯错，多尝试
- 📚 遇到不懂的就查文档
- 🤝 需要帮助就提问
- 🎯 从小任务开始，慢慢积累

**祝你开发愉快！** 🚀

---

*这份文档会持续更新，有任何建议请提 Issue！*
