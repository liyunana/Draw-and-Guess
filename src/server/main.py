"""
服务器主程序入口

启动游戏服务器，监听客户端连接。
"""

import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.shared.constants import DEFAULT_HOST, DEFAULT_PORT  # noqa: E402

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("server.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def main():
    """启动服务器主函数"""
    logger.info("=" * 50)
    # 支持通过环境变量覆盖主机与端口
    host = os.environ.get("HOST", DEFAULT_HOST)
    try:
        port = int(os.environ.get("PORT", DEFAULT_PORT))
    except Exception:
        port = DEFAULT_PORT

    logger.info("Draw & Guess 游戏服务器启动中...")
    logger.info(f"监听地址: {host}:{port}")
    logger.info("=" * 50)

    try:
        from src.server.network import NetworkServer
        server = NetworkServer(host, port)
        server.start()
        
        logger.info("服务器运行中，按 Ctrl+C 停止")

        # 保持服务器运行
        while True:
            import time
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n服务器正在关闭...")
        if 'server' in locals():
            server.stop()
    except Exception as e:
        logger.error(f"服务器错误: {e}", exc_info=True)
    finally:
        logger.info("服务器已停止")


if __name__ == "__main__":
    main()
