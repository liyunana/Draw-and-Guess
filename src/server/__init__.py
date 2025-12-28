"""
服务器端模块

负责处理客户端连接、游戏逻辑、房间管理等服务器功能。

模块组成：
- game: 回合/计分/玩家状态机
- models: 数据模型与序列化工具
- network: TCP 会话、消息路由与广播

使用方式：
- 入口参见 src/server/main.py，启动 NetworkServer 并绑定 GameRoom
"""

from . import game, models, network

__all__ = ["game", "models", "network"]
