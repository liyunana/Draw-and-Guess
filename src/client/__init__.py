"""
客户端模块

负责游戏界面、用户交互、网络通信等客户端功能。

模块组成：
- game: 客户端游戏状态与网络封装（连接、房间、绘图/聊天/猜词动作）
- ui: UI 组件（画布、聊天缓冲、HUD、按钮等），供界面层组合

入口提示：
- 运行 src/client/main.py 启动 Pygame 客户端
- 与服务器通信基于行分隔 JSON（Message.to_json() + "\n"）
"""

from . import game, ui, network

__all__ = ["game", "ui", "network"]
