"""
常量定义

定义游戏中使用的各种常量。
"""

# 网络配置
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555
BUFFER_SIZE = 4096

# 游戏配置
MAX_PLAYERS = 8
MIN_PLAYERS = 2
ROUND_TIME = 60  # 秒
DRAW_TIME = 60  # 秒

# 窗口配置
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 960
WINDOW_TITLE = "Draw & Guess - 你画我猜"
FPS = 60

# 颜色定义 (RGB)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)

# 画笔配置
BRUSH_SIZES = [2, 5, 10, 15, 20]
DEFAULT_BRUSH_SIZE = 5
BRUSH_COLORS = [
    BLACK,
    RED,
    GREEN,
    BLUE,
    (255, 255, 0),  # Yellow
    (255, 165, 0),  # Orange
    (128, 0, 128),  # Purple
    (165, 42, 42),  # Brown
]

# 消息类型
MSG_CONNECT = "connect"
MSG_DISCONNECT = "disconnect"
MSG_JOIN_ROOM = "join_room"
MSG_CREATE_ROOM = "create_room"
MSG_LIST_ROOMS = "list_rooms"
MSG_LEAVE_ROOM = "leave_room"
MSG_KICK_PLAYER = "kick_player"
MSG_ROOM_UPDATE = "room_update"  # 用于同步房间状态（玩家列表等）
MSG_DRAW = "draw"
MSG_GUESS = "guess"
MSG_CHAT = "chat"
MSG_START_GAME = "start_game"
MSG_END_GAME = "end_game"
MSG_NEXT_ROUND = "next_round"
MSG_ERROR = "error"
