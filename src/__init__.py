"""
Draw & Guess - 你画我猜联机游戏

A multiplayer drawing and guessing game built with Python and Pygame.
"""

__version__ = "0.1.0"
__author__ = "Draw & Guess Team"
__license__ = "MIT"

# 导出主要组件
from . import client, server, shared

__all__ = ["client", "server", "shared", "__version__"]
