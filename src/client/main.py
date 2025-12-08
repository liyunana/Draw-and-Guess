"""
客户端主程序入口

启动游戏客户端，连接到服务器并显示游戏界面。
"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pygame  # noqa: E402

from src.shared.constants import WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("client.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def main():
    """启动客户端主函数"""
    logger.info("=" * 50)
    logger.info("Draw & Guess 游戏客户端启动中...")
    logger.info("=" * 50)

    try:
        # 初始化 Pygame
        pygame.init()

        # 创建游戏窗口
        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)

        logger.info(f"游戏窗口已创建: {WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # TODO: 实现游戏主循环
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            # 填充背景
            screen.fill((255, 255, 255))

            # TODO: 绘制游戏内容

            pygame.display.flip()
            clock.tick(60)  # 60 FPS

    except Exception as e:
        logger.error(f"客户端错误: {e}", exc_info=True)
    finally:
        pygame.quit()
        logger.info("客户端已关闭")


if __name__ == "__main__":
    main()
