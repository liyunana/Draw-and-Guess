# 🎨 Draw & Guess - 你画我猜联机游戏

## 🌟 项目简介

Draw & Guess 是一个基于 Python 和 Socket 的多人联机"你画我猜"游戏。玩家可以创建或加入房间，轮流作画并让其他玩家猜词，支持实时绘图同步、聊天交流、分数统计等功能。

### ✨ 主要特性

* 🎮  **实时多人游戏** ：支持 2-8 人同时在线游戏
* 🎨  **流畅绘图体验** ：优化的绘图算法，支持多种画笔
* 💬  **实时聊天** ：游戏内聊天系统，支持猜测和讨论
* 🏆  **积分系统** ：完整的分数统计和排行榜
* 🏠  **房间管理** ：支持创建私人房间和快速匹配
* 🔒  **安全可靠** ：数据验证、异常处理、断线重连
* 🎯  **跨平台** ：支持 Windows、macOS、Linux

## 🚀 快速开始

### 环境要求

* Python 3.8 或更高版本
* Pygame 2.5.0+
* 稳定的网络连接

### 安装步骤

1. **克隆仓库**

**bash**复制

```bash
git clone https://github.com/your-username/draw-and-guess.git
cd draw-and-guess
```

2. **创建虚拟环境**

**bash**复制

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **安装依赖**

**bash**复制

```bash
pip install -r requirements/dev.txt
```

4. **启动服务器**

**bash**复制

```bash
# 开发环境
python src/server/main.py

# 或使用脚本
./scripts/run_server.sh
```

5. **启动客户端**

**bash**复制

```bash
# 新终端，激活虚拟环境
python src/client/main.py

# 或使用脚本
./scripts/run_client.sh
```

## 📖 使用说明

### 创建游戏

1. 启动服务器后，客户端输入玩家名称
2. 选择"创建房间"或"加入房间"
3. 等待其他玩家加入（至少2人）
4. 房主点击"开始游戏"
5. 系统随机选择画家和词语
6. 画家作画，其他玩家猜词
7. 猜对得分，进入下一轮

### 游戏控制

* **鼠标左键** ：绘图
* **鼠标右键** ：橡皮擦
* **滚轮** ：调整画笔大小
* **颜色面板** ：选择颜色
* **Enter** ：发送猜测
* **Ctrl+Z** ：撤销操作

## 🏗️ 项目架构

### 技术栈

* **后端** ：Python 3.8+、Socket、Threading、JSON
* **前端** ：Pygame、Python Tkinter（配置界面）
* **网络** ：TCP Socket、自定义协议、心跳机制
* **架构** ：客户端-服务器模式、事件驱动设计

### 模块结构

复制

```
src/
├── server/          # 服务器端
│   ├── network/     # 网络通信层
│   ├── game/        # 游戏逻辑层
│   └── models/      # 数据模型层
├── client/          # 客户端
│   ├── ui/          # 用户界面
│   ├── network/     # 网络通信
│   └── game/        # 游戏逻辑
└── shared/          # 共享代码
    ├── constants.py # 常量定义
    └── protocols.py # 通信协议
```

## 👨‍💻 开发团队

感谢以下开发者对本项目的贡献：

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/vegetablech1cken">
        <img src="https://github.com/vegetablech1cken.png" width="100px;" alt="vegetablech1cken"/>
        <br />
        <sub><b>@vegetablech1cken</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Zoxel-rin">
        <img src="https://github.com/Zoxel-rin.png" width="100px;" alt="Zoxel-rin"/>
        <br />
        <sub><b>@Zoxel-rin</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/liyunana">
        <img src="https://github.com/liyunana.png" width="100px;" alt="liyunana"/>
        <br />
        <sub><b>@liyunana</b></sub>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Kyunana097">
        <img src="https://github.com/Kyunana097.png" width="100px;" alt="Kyunana097"/>
        <br />
        <sub><b>@Kyunana097</b></sub>
      </a>
    </td>
  </tr>
</table>

## 👥 团队开发指南

### 角色分工

我们的四人团队采用以下分工模式：

#### 🏗️ 开发者 A - 服务器架构师

* **负责模块** ：`src/server/network/`、`src/server/game/`
* **核心任务** ：Socket通信、并发处理、游戏状态管理
* **协作接口** ：与开发者C密切合作定义网络协议

#### 🎨 开发者 B - 客户端架构师

* **负责模块** ：`src/client/ui/`、`src/client/game/`
* **核心任务** ：界面设计、绘图引擎、用户交互
* **协作接口** ：与开发者D合作优化用户体验

#### 🔗 开发者 C - 网络协议专家

* **负责模块** ：`src/shared/`、网络优化、异常处理
* **核心任务** ：协议设计、数据同步、安全性
* **协作接口** ：连接前后端，确保数据流畅

#### ✨ 开发者 D - 用户体验设计师

* **负责模块** ：UI/UX、动画效果、游戏平衡
* **核心任务** ：界面美化、交互优化、音效系统
* **协作接口** ：与B合作实现视觉效果

### 开发流程

1. **功能开发** ：在对应分支上开发，遵循代码规范
2. **代码审查** ：每个PR需要至少1人审查
3. **集成测试** ：开发者C负责系统集成测试
4. **文档更新** ：功能完成后更新相关文档

## 🧪 测试

### 运行测试

**bash**复制

```bash
# 所有测试
pytest

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 端到端测试
pytest tests/e2e/

# 覆盖率报告
pytest --cov=src tests/
```

### 测试结构

复制

```
tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
└── e2e/           # 端到端测试
```

## 📊 性能指标

* **网络延迟** ：< 100ms（局域网）
* **帧率** ：30+ FPS
* **并发连接** ：支持 8 个客户端
* **内存使用** ：< 500MB（服务器）
* **CPU 占用** ：< 10%（单核）

## 🔧 配置选项

### 服务器配置

**Python**复制

```python
# config/settings.py
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5555
MAX_PLAYERS = 8
GAME_ROUND_TIME = 60  # 秒
HEARTBEAT_INTERVAL = 5  # 秒
```

### 客户端配置

**Python**复制

```python
# 客户端设置
CANVAS_WIDTH = 800
CANVAS_HEIGHT = 600
BRUSH_SIZES = [1, 3, 5, 10, 20]
COLORS = ['#000000', '#FF0000', '#00FF00', '#0000FF', ...]
```

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. **Fork 仓库**
2. **创建功能分支**

**bash**复制

```bash
git checkout -b feature/amazing-feature
```

3. **提交更改**

**bash**复制

```bash
git commit -m 'feat: add amazing feature'
```

4. **推送到分支**

**bash**复制

```bash
git push origin feature/amazing-feature
```

5. **创建 Pull Request**

### 提交规范

* **feat** : 新功能
* **fix** : Bug修复
* **docs** : 文档更新
* **style** : 代码格式
* **refactor** : 代码重构
* **test** : 测试相关
* **chore** : 构建/工具

### 代码规范

* 遵循 [PEP 8](https://pep8.org/) 规范
* 使用 [Black](https://black.readthedocs.io/) 格式化代码
* 添加类型提示
* 编写单元测试
* 更新相关文档

详细贡献指南请查看 [CONTRIBUTING.md](https://www.kimi.com/chat/CONTRIBUTING.md)

## 🗺️ 路线图

### 近期计划 (v1.1.0)

* [ ] 添加房间密码功能
* [ ] 实现观战模式
* [ ] 优化网络协议
* [ ] 添加更多画笔工具

### 中期计划 (v1.2.0)

* [ ] Web版本开发
* [ ] 移动端支持
* [ ] 语音聊天功能
* [ ] 自定义词库

### 长期愿景 (v2.0.0)

* [ ] AI智能提示
* [ ] 游戏回放系统
* [ ] 高级统计功能
* [ ] 社区功能

## 📚 文档

* [架构设计](https://www.kimi.com/chat/docs/architecture.md) - 系统架构详细说明
* [开发指南](https://www.kimi.com/chat/docs/development.md) - 开发环境搭建和流程
* [API文档](https://www.kimi.com/chat/docs/api.md) - 接口规范说明
* [部署指南](https://www.kimi.com/chat/docs/deployment.md) - 生产环境部署

## 🐛 常见问题

**Q: 连接服务器失败怎么办？**
A: 检查防火墙设置，确保服务器端口开放，确认IP地址正确。

**Q: 绘图延迟高怎么解决？**
A: 检查网络连接，关闭其他占用带宽的程序，尝试降低画质设置。

**Q: 支持的最大玩家数？**
A: 默认支持8人，可通过配置文件调整。

**更多问题请查看 [FAQ](https://www.kimi.com/chat/docs/faq.md)**

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](https://www.kimi.com/chat/LICENSE) 文件了解详情。

## 🙏 致谢

* 感谢 Pygame 社区提供的优秀游戏开发库
* 感谢所有贡献者的辛勤付出
* 感谢测试玩家的宝贵反馈

## 📞 联系我们

* **Issue跟踪** : [GitHub Issues](https://github.com/your-username/draw-and-guess/issues)
* **讨论区** : [GitHub Discussions](https://github.com/your-username/draw-and-guess/discussions)
* **邮件** : [team@draw-and-guess.com](mailto:team@draw-and-guess.com)

---

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**

**🚀 准备好开始你的创作之旅了吗？加入我们，一起画出精彩！**
