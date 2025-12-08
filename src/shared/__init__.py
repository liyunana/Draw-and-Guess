"""
共享模块

存放客户端和服务器共用的代码，如常量、协议定义、工具函数等。
"""

from . import constants, protocols

__all__ = ["constants", "protocols"]
