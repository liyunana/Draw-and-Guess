"""
共享模块

存放客户端和服务器共用的代码，如常量、协议定义、工具函数等。

组件说明：
- constants: 网络端口、窗口参数、颜色/画笔配置、消息类型枚举
- protocols: 基于 JSON 的消息格式（Message 及 Connect/Draw/Chat 等派生）

提示：
- 协议层约定按行分隔的 JSON 串，网络层直接透传 Message.to_json() + "\n"
- 若新增公共工具，可在此模块下添加并在 __all__ 中显式导出
"""

from . import constants, protocols

__all__ = ["constants", "protocols"]
