"""
客户端主程序入口

启动游戏客户端，连接到服务器并显示游戏界面。
"""

import logging
import sys
from pathlib import Path
import math
import uuid
import os
import subprocess
from typing import Any, Callable, Dict, List, Optional

# 添加项目根目录到路径（保留以便直接运行脚本时能找到包）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pygame
import json

# Ensure logger is configured early so modules can use it
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.shared.constants import (
    WINDOW_HEIGHT, WINDOW_TITLE, WINDOW_WIDTH,
    MSG_CREATE_ROOM, MSG_JOIN_ROOM, MSG_LIST_ROOMS, MSG_KICK_PLAYER, MSG_START_GAME, MSG_ROOM_UPDATE, MSG_LEAVE_ROOM,
    MSG_CHAT, MSG_NEXT_ROUND, MSG_GIVE_SCORE, MSG_GAME_RESULT,
    DEFAULT_HOST, DEFAULT_PORT
)
from src.client.network import NetworkClient
from src.client.ui.button import Button
from src.client.ui.buttons_config import BUTTONS_CONFIG
from src.client.ui.canvas import Canvas
from src.client.ui.toolbar import Toolbar
from src.client.ui.text_input import TextInput
from src.client.ui.chat import ChatPanel
# Project root and resource paths
ROOT = Path(__file__).parent.parent.parent
SETTINGS_PATH = ROOT / "settings.json"
LOGO_PATH = ROOT / "assets" / "images" / "logo.png"
CONFIRM_SOUND_PATH = ROOT / "data" / "confirm.mp3"

# Runtime maps used by create_buttons_from_config / event dispatch
BUTTON_ORIG_BG: Dict[int, tuple] = {}
BUTTON_HOVER_BG: Dict[int, tuple] = {}
BUTTON_CALLBACKS: Dict[int, Callable[..., Any]] = {}
BUTTON_ANIMS: Dict[int, Dict[str, Any]] = {}

# Logo animation defaults
LOGO_BREATH_AMPLITUDE = 0.06
LOGO_BREATH_FREQ = 0.5
LOGO_SWING_AMP = 4.0
LOGO_SWING_FREQ = 0.2
# Button entrance animation parameters
BUTTON_SLIDE_DURATION = 1.0  # seconds
BUTTON_STAGGER = 0.2  # seconds between staggered starts

# App state
APP_STATE: Dict[str, Any] = {
    "screen": "menu",  # menu | room_list | lobby | play | settings | creating_room
    "ui": None,
    "settings": {
        "player_name": "玩家",
        "difficulty": "普通",  # 简单 | 普通 | 困难
        "volume": 80,
        "theme": "light",  # light | dark
        "fullscreen": False,
        "player_id": None,
        "server_host": "127.0.0.1",
        "server_port": 5555,
    },
    "net": None,
    "rooms": [],  # List of room info
    "current_room": None,  # Room info dict
    "notifications": [],  # List[Dict[str, Any]] with text, color, end_time
    # resize 防抖：在窗口调整结束后再重建 UI，减少频繁重建导致的卡顿
    "pending_resize_until": 0,
    "pending_resize_size": None,
    # 保存聊天消息和滚动状态（窗口改变时）
    "_saved_chat_messages": None,
    "_saved_chat_scroll": None,
    # 创建房间加载界面使用的实时日志
    "creating_logs": [],
}


def load_settings() -> None:
    """从 JSON 文件加载设置（如果存在）。"""
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k in ("player_name", "difficulty", "volume", "theme", "fullscreen", "player_id", "server_host", "server_port"):
                    if k in data:
                        APP_STATE["settings"][k] = data[k]
    except Exception as exc:
        logger.warning("加载设置失败: %s", exc)


def save_settings() -> None:
    """将当前设置保存到 JSON 文件（不保存 player_id，每次启动会重新生成）。"""
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        # 排除 player_id，因为它是每次启动时动态生成的
        settings_to_save = {k: v for k, v in APP_STATE["settings"].items() if k != "player_id"}
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings_to_save, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("保存设置失败: %s", exc)


def add_notification(text: str, color=(50, 200, 50), duration=2.0) -> None:
    """添加一个临时的屏幕通知。"""
    APP_STATE["notifications"].append({
        "text": text,
        "color": color,
        "end_time": pygame.time.get_ticks() + duration * 1000
    })


def ensure_player_identity() -> str:
    """为本次会话生成唯一 player_id（每次启动都不同，支持多客户端）。"""
    # 每次启动生成新的 player_id，支持同一台机器运行多个客户端
    pid = str(uuid.uuid4())
    APP_STATE["settings"]["player_id"] = pid
    # 不保存 player_id 到文件，避免多客户端冲突
    return pid


def get_network_client() -> NetworkClient:
    net = APP_STATE.get("net")
    if net is None:
        # 从设置读取服务器地址
        shost = APP_STATE["settings"].get("server_host", DEFAULT_HOST)
        sport = int(APP_STATE["settings"].get("server_port", DEFAULT_PORT))
        net = NetworkClient(host=shost, port=sport)
        APP_STATE["net"] = net
    return net


def detect_local_ip() -> str:
    """检测本机可用于局域网连接的 IPv4 地址。

    优先使用 UDP 套接字连接外部地址的方式，获取本机出口 IP；
    失败则回退到 127.0.0.1。
    """
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 不会真的发送，但可得到本机选择的出站 IP
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip or "127.0.0.1"
    except Exception:
        return "127.0.0.1"


def _cleanup_local_server_process(port: int) -> bool:
    """尝试清理占用指定端口的旧本地服务器进程。

    仅作用于本机的 5555 等游戏端口，用于解决上一次游戏遗留的服务器进程
    挤占端口的问题，不会影响远程专用服务器。
    """
    try:
        killed_any = False
        if os.name == "nt":
            # Windows: 使用 netstat 查找监听端口的 PID，并用 taskkill 结束
            try:
                cmd = f"netstat -ano | findstr :{port} | findstr LISTENING"
                output = subprocess.check_output(cmd, shell=True, encoding="utf-8", errors="ignore")
            except Exception:
                return False

            pids = set()
            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.add(pid)

            for pid in pids:
                try:
                    subprocess.run([
                        "taskkill",
                        "/F",
                        "/PID",
                        pid,
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    killed_any = True
                except Exception:
                    continue
        else:
            # 类 Unix: 优先尝试 fuser，其次 lsof
            try:
                subprocess.run(
                    ["fuser", "-k", f"{port}/tcp"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                killed_any = True
            except Exception:
                try:
                    pid_output = subprocess.check_output(
                        ["lsof", "-ti", f"tcp:{port}"],
                        encoding="utf-8",
                        errors="ignore",
                    )
                    pids = {p.strip() for p in pid_output.splitlines() if p.strip()}
                    for pid in pids:
                        subprocess.run([
                            "kill",
                            "-9",
                            pid,
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                        killed_any = True
                except Exception:
                    pass

        if killed_any:
            add_notification(f"已尝试清理端口 {port} 上的旧服务器进程", color=(60, 160, 220))
        return killed_any
    except Exception as exc:
        logger.warning("清理本地服务器进程失败: %s", exc)
        return False


def start_local_server(port: int = 5555) -> bool:
    """在本机后台启动服务器进程（HOST=0.0.0.0）。

    返回是否成功启动。保存进程对象到 APP_STATE，以便后续管理。
    """
    try:
        # 启动前检测端口占用，避免重复启动导致 Address already in use
        def _port_in_use(p: int) -> bool:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            try:
                # 仅检查本地环回端口是否有服务
                s.connect(("127.0.0.1", p))
                return True
            except Exception:
                return False
            finally:
                try:
                    s.close()
                except Exception:
                    pass

        if _port_in_use(port):
            # 端口被占用时，优先尝试清理上一次游戏遗留的本地服务器进程
            cleaned = _cleanup_local_server_process(port)
            if cleaned:
                # 略微等待端口释放
                try:
                    import time as _t
                    _t.sleep(0.5)
                except Exception:
                    pass
                if _port_in_use(port):
                    add_notification(f"端口 {port} 仍被占用，未启动本地服务器", color=(200, 60, 60))
                    return False
            else:
                add_notification(f"端口 {port} 已被占用，未启动本地服务器", color=(200, 60, 60))
                return False

        server_path = Path(__file__).parent.parent.parent / "server-deploy" / "server.py"
        if not server_path.exists():
            add_notification("未找到服务器脚本 server-deploy/server.py", color=(200, 60, 60))
            return False
        env = os.environ.copy()
        env["HOST"] = "0.0.0.0"
        env["PORT"] = str(port)
        # 使用当前 Python 可执行文件启动，防止虚拟环境不一致
        proc = subprocess.Popen([sys.executable, str(server_path)], env=env)
        APP_STATE["_local_server_proc"] = proc
        add_notification(f"本地服务器已启动，端口 {port}", color=(60, 160, 220))
        return True
    except Exception as e:
        add_notification(f"启动本地服务器失败: {e}", color=(200, 60, 60))
        return False


def load_logo(path: Path, screen_size: tuple):
    """Load original logo surface and compute a base size + anchor.

    Returns (orig_surface or None, (base_w, base_h), anchor_pos)
    """
    try:
        orig = pygame.image.load(str(path)).convert_alpha()
    except Exception as exc:  # pragma: no cover - runtime resource handling
        logger.warning("Failed loading logo %s: %s", path, exc)
        return None, (0, 0), (0, 0)

    sw, sh = screen_size
    base_w = max(16, int(sw * 0.20))  # base logo width = 20% screen width
    orig_w, orig_h = orig.get_size()
    if orig_w <= 0:
        return None, (0, 0), (0, 0)

    base_h = max(1, int(base_w * orig_h / orig_w))
    # anchor at top-right with small margin from the screen edge
    anchor_pos = (sw - int(sw * 0.04), int(sh * 0.04))
    return orig, (base_w, base_h), anchor_pos


def anchor_to_pos(
    anchor: str, dx: int, dy: int, screen_w: int, screen_h: int, btn_w: int, btn_h: int
) -> tuple:
    """Convert anchor+offset to topleft (x,y).

    Supported anchors: 'topleft', 'topright', 'bottomleft', 'bottomright', 'center'
    """
    if anchor == "topleft":
        x, y = dx, dy
    elif anchor == "topright":
        x, y = screen_w - btn_w + dx, dy
    elif anchor == "bottomleft":
        x, y = dx, screen_h - btn_h + dy
    elif anchor == "bottomright":
        x, y = screen_w - btn_w + dx, screen_h - btn_h + dy
    elif anchor == "center":
        x, y = (screen_w - btn_w) // 2 + dx, (screen_h - btn_h) // 2 + dy
    else:
        x, y = dx, dy
    return int(x), int(y)


def resolve_position_and_size(cfg: Dict[str, Any], screen_size: tuple) -> tuple:
    """Resolve (x,y,w,h) from configuration.

    Supports percentage fields (`x_pct`, `y_pct`, `w_pct`, `h_pct`) and
    `anchor` with pixel offsets `dx`/`dy`.
    """
    sw, sh = screen_size

    # width / height by absolute px or percentage
    w = int(cfg.get("w", int(max(80, sw * cfg.get("w_pct", 0) if cfg.get("w_pct") else max(80, 0.2 * sw)))))
    h = int(cfg.get("h", int(sh * cfg.get("h_pct", 0) if cfg.get("h_pct") else 40)))

    # position resolution
    if "x_pct" in cfg:
        x = int(cfg["x_pct"] * sw)
        y = int(cfg.get("y", int(cfg.get("y_pct", 0) * sh if "y_pct" in cfg else 0)))
    elif "y_pct" in cfg and "x" in cfg:
        x = int(cfg.get("x", 0))
        y = int(cfg["y_pct"] * sh)
    elif "anchor" in cfg:
        dx = int(cfg.get("dx", 0))
        dy = int(cfg.get("dy", 0))
        x, y = anchor_to_pos(cfg["anchor"], dx, dy, sw, sh, w, h)
    else:
        x = int(cfg.get("x", 0))
        y = int(cfg.get("y", 0))

    return x, y, w, h


def create_buttons_from_config(
    config_list: List[Dict[str, Any]],
    callbacks_map: Dict[str, Callable[..., Any]],
    screen_size: tuple,
    logo_anchor: Optional[tuple] = None,
    screen_filter: Optional[str] = None,
    click_sound: Optional[pygame.mixer.Sound] = None,
) -> List[Button]:
    """Create and return Button instances from configuration.

    This function also registers original/hover colors and callbacks in
    module-level dictionaries for runtime use.
    """
    buttons: List[Button] = []
    for idx, cfg in enumerate(config_list):
        # 如果指定了 screen_filter，只创建属于该 screen 的按钮
        if screen_filter is not None and cfg.get("screen") != screen_filter:
            continue
        x, y, w, h = resolve_position_and_size(cfg, screen_size)

        # start off-screen to the right (for menu animation) or place directly for other screens
        start_x = screen_size[0] + 20 + idx * 8
        # compute target_x; respect explicit position from cfg by default.
        if cfg.get("align_to_logo") and logo_anchor is not None:
            logo_right_x = int(logo_anchor[0])
            gap = int(cfg.get("align_gap", 0))
            target_x = logo_right_x - w - gap
        else:
            target_x = x

        initial_x = start_x if screen_filter == "menu" else target_x

        orig = tuple(cfg.get("bg_color", (0, 0, 0)))
        hover = tuple(
            cfg.get(
                "hover_bg",
                (min(255, orig[0] + 40), min(255, orig[1] + 40), min(255, orig[2] + 40)),
            )
        )

        cb_name = cfg.get("callback")
        callback = None
        if cb_name and cb_name in callbacks_map:
            callback = callbacks_map[cb_name]

        btn = Button(
            x=initial_x,
            y=y,
            width=w,
            height=h,
            text=cfg.get("text", ""),
            bg_color=orig,
            fg_color=tuple(cfg.get("fg_color", (255, 255, 255))),
            hover_bg_color=hover,
            font_size=cfg.get("font_size", 24),
            font_name=cfg.get("font_name", None),
            click_sound=click_sound,
            on_click=callback,
        )
        # attach config id for callers to find specific buttons
        try:
            setattr(btn, "_cfg_id", cfg.get("id"))
        except Exception:
            pass

        BUTTON_ORIG_BG[id(btn)] = orig
        BUTTON_HOVER_BG[id(btn)] = hover

        if callback:
            BUTTON_CALLBACKS[id(btn)] = callback

        # register animation state for slide-in from right
        BUTTON_ANIMS[id(btn)] = {
            "start_x": start_x,
            "target_x": target_x,
            "y": y,
            "duration": BUTTON_SLIDE_DURATION,
            "delay": idx * BUTTON_STAGGER,
            "finished": False if screen_filter == "menu" else True,
        }

        buttons.append(btn)

    return buttons


def on_start() -> None:
    logger.info("Start pressed")
    APP_STATE["screen"] = "room_list"
    APP_STATE["ui"] = None
    # Connect and list rooms
    net = get_network_client()
    if net.connect(APP_STATE["settings"]["player_name"], APP_STATE["settings"].get("player_id")):
        net.list_rooms()


def on_settings() -> None:
    logger.info("Settings pressed")
    APP_STATE["screen"] = "settings"
    APP_STATE["ui"] = None


def on_quit() -> None:
    logger.info("Quit pressed")
    try:
        net = APP_STATE.get("net")
        if net:
            net.close()
    except Exception:
        pass
    pygame.quit()
    sys.exit(0)


CALLBACKS: Dict[str, Callable[..., Any]] = {
    "on_start": on_start,
    "on_settings": on_settings,
    "on_quit": on_quit,
}


def build_play_ui(screen_size: tuple) -> Dict[str, Any]:
    """根据屏幕尺寸构建游戏界面组件。窗口大小改变时会自动保留聊天消息。"""
    sw, sh = screen_size
    pad = 16
    sidebar_w = 260
    scoreboard_w = 180  # 左侧预留积分榜区域宽度
    chat_h = 140
    input_h = 40
    topbar_h = 44

    canvas_rect = pygame.Rect(
        pad + scoreboard_w + pad,
        pad + topbar_h,
        sw - sidebar_w - scoreboard_w - pad * 4,
        sh - chat_h - input_h - pad * 4 - topbar_h,
    )
    toolbar_rect = pygame.Rect(canvas_rect.right + pad, pad + topbar_h, sidebar_w, canvas_rect.height)
    chat_rect = pygame.Rect(pad, canvas_rect.bottom + pad, sw - pad * 2, chat_h)
    send_w = 90
    input_rect = pygame.Rect(pad, chat_rect.bottom + pad, sw - pad * 3 - send_w, input_h)

    # 组件
    canvas = Canvas(canvas_rect)

    # 颜色与画笔大小来自常量
    from src.shared.constants import BRUSH_COLORS, BRUSH_SIZES

    # 获取预加载的音效（如果存在）
    confirm_sound = None
    try:
        confirm_sound = pygame.mixer.Sound(str(CONFIRM_SOUND_PATH)) if CONFIRM_SOUND_PATH.exists() else None
    except Exception:
        pass

    toolbar = Toolbar(toolbar_rect, colors=BRUSH_COLORS, sizes=BRUSH_SIZES, font_name="Microsoft YaHei", click_sound=confirm_sound)

    # 创建新聊天框，从保存的消息中恢复
    chat = ChatPanel(chat_rect, font_size=18, font_name="Microsoft YaHei")

    # 尝试从保存的消息恢复（窗口大小改变时）
    saved_messages = APP_STATE.get("_saved_chat_messages")
    if saved_messages:
        chat.messages = saved_messages
        # 恢复滚动状态
        saved_scroll = APP_STATE.get("_saved_chat_scroll", 0)
        chat.scroll_offset = saved_scroll
        # 清除保存的数据
        APP_STATE["_saved_chat_messages"] = None
        APP_STATE["_saved_chat_scroll"] = None
    else:
        # 尝试从旧 UI 恢复消息（备用方案）
        old_ui = APP_STATE.get("ui")
        if old_ui and isinstance(old_ui, dict) and "chat" in old_ui:
            old_chat = old_ui["chat"]
            if hasattr(old_chat, "messages") and old_chat.messages:
                chat.messages = old_chat.messages[:]
                if hasattr(old_chat, "scroll_offset"):
                    chat.scroll_offset = old_chat.scroll_offset

    text_input = TextInput(input_rect, font_name="Microsoft YaHei", font_size=22, placeholder="输入猜词或聊天... Enter发送 / Shift+Enter换行")
    # 发送按钮将在配置中创建并附加到 UI（位置依赖输入区域）

    # 回调绑定
    toolbar.on_color = canvas.set_color
    toolbar.on_brush = canvas.set_brush_size
    toolbar.on_mode = canvas.set_mode
    toolbar.on_clear = canvas.clear

    # 初始化工具栏选中状态为画布当前值
    try:
        toolbar.set_selected_color(canvas.brush_color)
        toolbar.set_selected_size(canvas.brush_size)
    except Exception:
        pass

    def _on_submit(msg: str) -> None:
        safe = msg.replace("\n", " ")
        try:
            net = APP_STATE.get("net")
            if net and net.connected:
                net.send_chat(safe)
        except Exception:
            pass
        chat.add_message("你", safe)

    text_input.on_submit = _on_submit

    # 绘画同步回调：当本地画布有绘画操作时，发送给服务器
    def _on_draw_action(action: dict) -> None:
        try:
            net = APP_STATE.get("net")
            if net and net.connected:
                net.send_draw(action)
        except Exception:
            pass

    canvas.on_draw_action = _on_draw_action

    # 返回菜单按钮将在配置中创建并附加到 UI

    # HUD 状态（计时与词语），具体数值将在进入房间 / 接收服务器状态时由网络消息覆盖
    hud_state = {
        "topbar_h": topbar_h,
        "round_time_total": 60,
        "round_time_left": 60,
        "is_drawer": False,
        "current_word": None,
        "last_tick": pygame.time.get_ticks(),
    }

    return {
        "canvas": canvas,
        "toolbar": toolbar,
        "chat": chat,
        "input": text_input,
        "hud": hud_state,
    }


def build_settings_ui(screen_size: tuple, confirm_sound: Optional[pygame.mixer.Sound] = None) -> Dict[str, Any]:
    """构建设置界面组件。"""
    sw, sh = screen_size
    # Responsive layout: use percentages so window/fullscreen changes keep UI readable
    left_x = int(sw * 0.08)
    control_x = int(sw * 0.22)
    row1_y = int(sh * 0.16)
    row2_y = int(sh * 0.36)

    input_w = max(220, min(520, int(sw * 0.36)))
    input_h = max(36, min(48, int(sh * 0.06)))

    slider_w = max(260, min(620, int(sw * 0.46)))
    slider_h = 25

    from src.client.ui.setting_components import make_slider_rect

    # 玩家名字输入框
    player_name_label = "玩家名字"
    player_name_input = TextInput(
        rect=pygame.Rect(control_x, row1_y, input_w, input_h),
        font_name="Microsoft YaHei",
        font_size=20,
        placeholder=APP_STATE["settings"]["player_name"],
    )
    # 初始填充为当前玩家名并绑定提交保存
    try:
        player_name_input.text = APP_STATE["settings"].get("player_name", "玩家")
    except Exception:
        pass
    def _update_player_name(name: str) -> None:
        APP_STATE["settings"]["player_name"] = name.strip() or APP_STATE["settings"].get("player_name", "玩家")
        save_settings()
        add_notification(f"名字已修改为: {APP_STATE['settings']['player_name']}")
    player_name_input.on_submit = _update_player_name

    # 确认名字按钮 (绿色打钩)
    confirm_btn_x = control_x + input_w + 10
    confirm_name_btn = Button(
        x=confirm_btn_x,
        y=row1_y,
        width=input_h, # Square
        height=input_h,
        text="√",
        bg_color=(50, 200, 50),
        fg_color=(255, 255, 255),
        hover_bg_color=(70, 220, 70),
        font_size=24,
        font_name="Microsoft YaHei",
        click_sound=confirm_sound,
    )
    def _on_confirm_name():
        _update_player_name(player_name_input.text)
    confirm_name_btn.on_click = _on_confirm_name

    # 难度选择按钮
    # 难度设置已移除（改为使用默认/固定难度）

    # 音量滑块范围
    volume_slider_rect = make_slider_rect(control_x, row2_y, slider_w, slider_h)

    # 服务器地址输入框
    row3_y = int(sh * 0.52)
    server_host_label = "服务器地址"
    server_host_input = TextInput(
        rect=pygame.Rect(control_x, row3_y, input_w, input_h),
        font_name="Microsoft YaHei",
        font_size=20,
        placeholder=APP_STATE["settings"].get("server_host", "127.0.0.1"),
    )
    try:
        server_host_input.text = APP_STATE["settings"].get("server_host", "127.0.0.1")
    except Exception:
        pass
    def _update_server_host(host: str) -> None:
        host = host.strip() or "127.0.0.1"
        APP_STATE["settings"]["server_host"] = host
        # 关闭旧连接，下次会用新地址
        net = APP_STATE.get("net")
        if net:
            net.close()
            APP_STATE["net"] = None
        save_settings()
        add_notification(f"服务器地址已设置为: {host}")
    server_host_input.on_submit = _update_server_host

    # 确认服务器地址按钮
    confirm_host_btn = Button(
        x=confirm_btn_x,
        y=row3_y,
        width=input_h,
        height=input_h,
        text="√",
        bg_color=(50, 200, 50),
        fg_color=(255, 255, 255),
        hover_bg_color=(70, 220, 70),
        font_size=24,
        font_name="Microsoft YaHei",
        click_sound=confirm_sound,
    )
    def _on_confirm_host():
        _update_server_host(server_host_input.text)
    confirm_host_btn.on_click = _on_confirm_host

    # 局域网按钮：自动检测本机IP、填入并可继续修改；必要时启动本地服务器
    lan_btn = Button(
        x=confirm_btn_x,
        y=row3_y + input_h + 12,
        width=max(120, int(input_w * 0.42)),
        height=input_h,
        text="局域网",
        bg_color=(80, 150, 200),
        fg_color=(255, 255, 255),
        hover_bg_color=(90, 170, 220),
        font_size=20,
        font_name="Microsoft YaHei",
        click_sound=confirm_sound,
    )
    def _on_lan():
        ip = detect_local_ip()
        # 填入输入框，便于用户进一步修改
        try:
            server_host_input.text = ip
        except Exception:
            pass
        _update_server_host(ip)
        # 若本地尚未启动服务器，则尝试启动
        proc = APP_STATE.get("_local_server_proc")
        if not proc or (hasattr(proc, "poll") and proc.poll() is not None):
            start_local_server(APP_STATE["settings"].get("server_port", 5555))
        else:
            add_notification("本地服务器已运行", color=(60, 160, 220))
    lan_btn.on_click = _on_lan

    # 服务器按钮：直接设置为远程固定地址
    remote_btn = Button(
        x=confirm_btn_x + max(130, int(input_w * 0.46)) + 10,
        y=row3_y + input_h + 12,
        width=max(120, int(input_w * 0.42)),
        height=input_h,
        text="服务器",
        bg_color=(50, 180, 80),
        fg_color=(255, 255, 255),
        hover_bg_color=(70, 200, 100),
        font_size=20,
        font_name="Microsoft YaHei",
        click_sound=confirm_sound,
    )
    def _on_remote():
        # 预填入远程地址，仍可在输入框中修改
        try:
            server_host_input.text = "81.68.144.16"
        except Exception:
            pass
        _update_server_host("81.68.144.16")
    remote_btn.on_click = _on_remote

    # 主题与全屏按钮由配置创建并在主循环中附加到 UI

    # 快捷键说明已移除（快捷键仍然存在于运行时，但不在设置界面展示）

    return {
        "player_name_input": player_name_input,
        "confirm_name_btn": confirm_name_btn,
        "server_host_input": server_host_input,
        "confirm_host_btn": confirm_host_btn,
        "server_lan_btn": lan_btn,
        "server_remote_btn": remote_btn,
        # difficulty buttons removed
        "volume_slider_rect": volume_slider_rect,
        # theme/fullscreen buttons attached from config
        # shortcuts removed from UI dict
    }


def build_room_list_ui(screen_size: tuple) -> Dict[str, Any]:
    sw, sh = screen_size

    # Refresh button
    refresh_btn = Button(
        x=sw - 150, y=50, width=100, height=40,
        text="刷新", bg_color=(100, 100, 200), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=20
    )
    def _on_refresh():
        # 确保本地拥有唯一的 player_id（用于识别房主）
        player_id = APP_STATE["settings"].get("player_id") or ensure_player_identity()
        net = get_network_client()
        if net.connect(APP_STATE["settings"]["player_name"], player_id):
            net.list_rooms()
        else:
            add_notification("无法连接服务器，检查地址与端口", color=(200, 60, 60))
    refresh_btn.on_click = _on_refresh

    # Create Room button
    create_btn = Button(
        x=sw - 270, y=50, width=100, height=40,
        text="创建房间", bg_color=(50, 200, 50), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=20
    )
    def _on_create():
        try:
            logger.info("创建房间按钮被点击")
            net = get_network_client()
            logger.info(f"网络客户端: host={net.host}, port={net.port}, connected={net.connected}")
            player_name = APP_STATE["settings"].get("player_name", "玩家")
            # 确保存在唯一 player_id（用于服务器端认定房主）
            player_id = APP_STATE["settings"].get("player_id") or ensure_player_identity()
            logger.info(f"尝试连接: player_name={player_name}, player_id={player_id}")
            if net.connect(player_name, player_id):
                logger.info("连接成功，发送创建房间请求")
                # 切换到简易加载界面，避免用户误以为卡死
                APP_STATE["screen"] = "creating_room"
                APP_STATE["ui"] = None
                # 初始化创建房间日志
                APP_STATE["creating_logs"] = [
                    "已连接到服务器",
                    "正在发送创建房间请求...",
                ]
                add_notification("正在创建房间...", color=(50, 180, 80))
                net.create_room(f"{player_name}的房间")
                # 预填充最小房间状态，待服务器广播覆盖
                try:
                    APP_STATE["current_room"] = {
                        "room_id": None,
                        "status": "waiting",
                        "owner_id": player_id,
                        "players": {
                            str(player_id): {"name": player_name, "score": 0}
                        }
                    }
                except Exception:
                    pass
            else:
                logger.info("连接失败")
                add_notification("无法连接服务器，检查地址与端口", color=(200, 60, 60))
        except Exception as e:
            logger.exception(f"创建房间出错: {e}")
            add_notification(f"创建房间出错: {e}", color=(200, 60, 60))
    create_btn.on_click = _on_create

    # Back button
    back_btn = Button(
        x=50, y=50, width=100, height=40,
        text="返回", bg_color=(200, 100, 100), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=20
    )
    def _on_back():
        # 关闭网络连接，确保下次进入时用新的名称重新连接
        net = APP_STATE.get("net")
        if net:
            net.close()
            APP_STATE["net"] = None
        APP_STATE["screen"] = "menu"
        APP_STATE["ui"] = None
    back_btn.on_click = _on_back

    return {
        "refresh_btn": refresh_btn,
        "create_btn": create_btn,
        "back_btn": back_btn,
        "room_buttons": [] # Dynamic list of buttons for rooms
    }


def build_result_ui(screen_size: tuple) -> Dict[str, Any]:
    """构建游戏结果界面"""
    sw, sh = screen_size

    # 返回大厅按钮
    back_btn = Button(
        x=sw // 2 - 80, y=sh - 100, width=160, height=45,
        text="返回大厅", bg_color=(50, 150, 200), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=22
    )
    def _on_back():
        APP_STATE["screen"] = "lobby"
        APP_STATE["ui"] = None
        APP_STATE["game_result"] = None
    back_btn.on_click = _on_back

    return {
        "back_btn": back_btn,
    }


def build_lobby_ui(screen_size: tuple) -> Dict[str, Any]:
    sw, sh = screen_size

    # Start Game button (Owner only, but we show it disabled or handle logic)
    start_btn = Button(
        x=sw - 150, y=50, width=100, height=40,
        text="开始游戏", bg_color=(50, 200, 50), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=20
    )
    def _on_start_game():
        net = get_network_client()
        net.start_game()
    start_btn.on_click = _on_start_game

    # Leave button
    leave_btn = Button(
        x=50, y=50, width=100, height=40,
        text="离开房间", bg_color=(200, 100, 100), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=20
    )
    def _on_leave():
        net = get_network_client()
        net.leave_room()
        APP_STATE["screen"] = "room_list"
        APP_STATE["ui"] = None
        net.list_rooms()
    leave_btn.on_click = _on_leave

    # 房主设置折叠状态（使用全局 APP_STATE 存储，避免重建 UI 时丢失）
    APP_STATE.setdefault("_lobby_settings_collapsed", False)

    # 房主设置折叠/展开按钮（放在右上角靠近“开始游戏”按钮）
    settings_toggle_btn = Button(
        x=sw - 320, y=50, width=150, height=36,
        text="收起房主设置", bg_color=(180, 180, 200), fg_color=(40, 40, 40),
        font_name="Microsoft YaHei", font_size=18,
    )

    def _on_toggle_settings():
        APP_STATE["_lobby_settings_collapsed"] = not APP_STATE.get("_lobby_settings_collapsed", False)

    settings_toggle_btn.on_click = _on_toggle_settings

    # 游戏设置输入框（仅房主可见）
    # 默认值优先从当前房间状态读取，方便房主看到真实配置
    current_room = APP_STATE.get("current_room") or {}
    try:
        default_rounds = str(int(current_room.get("max_rounds") or 3))
    except Exception:
        default_rounds = "3"
    try:
        default_round_time = str(int(current_room.get("round_duration") or 60))
    except Exception:
        default_round_time = "60"

    # 聊天区域高度（与下方聊天面板保持一致），用于避免房主设置面板遮挡聊天
    pad = 20
    chat_h = max(140, int(sh * 0.22))
    chat_top = sh - chat_h - pad

    # 将设置面板整体移动到右侧竖直排列，减小输入框宽度，避免遮挡中间区域文字
    # 输入框稍窄一些，并保证整个面板始终贴近屏幕右侧
    input_w = 100
    panel_x = max(int(sw * 0.65), sw - (input_w + 460))
    right_margin = 40
    panel_y = 140
    row_h = 35
    row_gap = 18

    # 三个输入框统一右对齐到屏幕右侧（right_margin 内），让房主设置整体“靠右排列”
    input_x = sw - right_margin - input_w

    rounds_input = TextInput(
        rect=pygame.Rect(input_x, panel_y + 0 * (row_h + row_gap), input_w, row_h),
        font_name="Microsoft YaHei",
        font_size=18,
        placeholder=default_rounds,
    )
    rounds_input.text = default_rounds

    time_input = TextInput(
        rect=pygame.Rect(input_x, panel_y + 1 * (row_h + row_gap), input_w, row_h),
        font_name="Microsoft YaHei",
        font_size=18,
        placeholder=default_round_time,
    )
    time_input.text = default_round_time

    rest_input = TextInput(
        rect=pygame.Rect(input_x, panel_y + 2 * (row_h + row_gap), input_w, row_h),
        font_name="Microsoft YaHei",
        font_size=18,
        placeholder="10"
    )
    rest_input.text = "10"

    # 应用设置按钮（宽度与输入框接近，后续在绘制阶段按面板居中）
    apply_btn = Button(
        x=panel_x + 40, y=panel_y + 3 * (row_h + row_gap) + 10, width=220, height=35,
        text="应用设置", bg_color=(80, 150, 200), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=18
    )
    def _on_apply_settings():
        try:
            max_rounds = int(rounds_input.text or "3")
            round_time = int(time_input.text or "60")
            rest_time = int(rest_input.text or "10")
            net = get_network_client()
            net.set_game_config(max_rounds, round_time, rest_time)
            # 本地立即更新当前房间配置，避免在服务器广播前界面仍显示旧值
            try:
                current_room = APP_STATE.get("current_room") or {}
                current_room["max_rounds"] = max_rounds
                current_room["round_duration"] = round_time
                APP_STATE["current_room"] = current_room
            except Exception:
                pass
            add_notification(f"设置已更新: {max_rounds}轮, {round_time}秒/轮, {rest_time}秒休息", color=(50, 180, 80))
        except ValueError:
            add_notification("请输入有效的数字", color=(200, 60, 60))
    apply_btn.on_click = _on_apply_settings

    # 根据聊天区域顶部位置，必要时整体上移房主设置面板，避免遮挡聊天框
    panel_top = min(rounds_input.rect.y, time_input.rect.y, rest_input.rect.y) - 40
    panel_bottom = apply_btn.rect.bottom + 20
    if panel_bottom > chat_top - 10:
        # 需要上移的距离
        shift = panel_bottom - (chat_top - 10)
        # 避免移得过高压住房间标题，这里限制最小顶部高度
        min_top = 140  # 与初始 panel_y 一致
        if panel_top - shift < min_top:
            shift = max(0, panel_top - min_top)
        if shift > 0:
            rounds_input.rect.y -= shift
            time_input.rect.y -= shift
            rest_input.rect.y -= shift
            apply_btn.rect.y -= shift

    # 聊天面板（放置在大厅底部，横向铺满，避免遮挡玩家列表）
    chat_rect = pygame.Rect(pad, sh - chat_h - pad, sw - pad * 2, chat_h)
    chat = ChatPanel(chat_rect, font_size=18, font_name="Microsoft YaHei")

    # 聊天输入框
    chat_input_w = max(240, chat_rect.width - 100)
    # 将输入框与发送按钮保持在窗口内，紧贴聊天面板底部
    chat_input_y = chat_rect.bottom - 35 - 8
    chat_input = TextInput(
        rect=pygame.Rect(chat_rect.x, chat_input_y, chat_input_w, 35),
        font_name="Microsoft YaHei",
        font_size=16,
        placeholder="输入消息..."
    )

    # 发送按钮
    send_btn = Button(
        x=chat_rect.right - 80, y=chat_input_y,
        width=70, height=35,
        text="发送", bg_color=(50, 150, 200), fg_color=(255, 255, 255),
        font_name="Microsoft YaHei", font_size=16
    )
    def _on_send():
        msg = chat_input.text.strip()
        if msg:
            net = get_network_client()
            if net and net.connected:
                net.send_chat(msg)
            chat.add_message("你", msg)
            chat_input.text = ""
    send_btn.on_click = _on_send
    chat_input.on_submit = lambda text: _on_send()

    return {
        "start_btn": start_btn,
        "leave_btn": leave_btn,
        "settings_toggle_btn": settings_toggle_btn,
        "kick_buttons": [],  # Dynamic
        "rounds_input": rounds_input,
        "time_input": time_input,
        "rest_input": rest_input,
        "apply_btn": apply_btn,
        "chat": chat,
        "chat_input": chat_input,
        "send_btn": send_btn,
    }


def process_network_messages(ui: Optional[Dict[str, Any]]) -> None:
    """从网络事件队列消费消息并更新 UI。"""
    net = APP_STATE.get("net")
    if net is None:
        return

    self_id = APP_STATE.get("settings", {}).get("player_id")

    for msg in net.drain_events():
        data = msg.data or {}

        # 服务器使用 ack 封装事件：统一处理
        if msg.type == "ack":
            event = data.get("event")
            if event == MSG_LIST_ROOMS and data.get("ok"):
                APP_STATE["rooms"] = data.get("rooms", [])
                if APP_STATE["screen"] == "room_list":
                    APP_STATE["ui"] = None
                # 不显示通知，UI 更新本身就是反馈
            elif event == MSG_CREATE_ROOM and data.get("ok"):
                # 创建房间成功时，向加载界面追加日志
                try:
                    logs = APP_STATE.get("creating_logs")
                    if isinstance(logs, list):
                        room_id = data.get("room_id") or "?"
                        logs.append(f"服务器已创建房间 (ID={room_id})")
                        logs.append("正在进入房间大厅...")
                except Exception:
                    pass
                APP_STATE["screen"] = "lobby"
                APP_STATE["ui"] = None
                # 预填充房间状态，等待服务器广播覆盖
                try:
                    self_id = APP_STATE.get("settings", {}).get("player_id")
                    room_id = data.get("room_id")
                    player_name = APP_STATE["settings"].get("player_name", "玩家")
                    APP_STATE["current_room"] = {
                        "room_id": room_id,
                        "owner_id": self_id,
                        "status": "waiting",
                        "players": {
                            str(self_id): {"name": player_name, "score": 0}
                        }
                    }
                except Exception:
                    pass
                add_notification("房间创建成功，已进入大厅", color=(50, 180, 80))
            elif event == MSG_JOIN_ROOM:
                if data.get("ok"):
                    # 预填充当前房间的最小状态，等待服务器广播覆盖
                    try:
                        self_id = APP_STATE.get("settings", {}).get("player_id")
                        room_id = data.get("room_id")
                        player_name = APP_STATE["settings"].get("player_name", "玩家")
                        APP_STATE["current_room"] = {
                            "room_id": room_id,
                            "status": "waiting",
                            "players": {
                                str(self_id): {"name": player_name, "score": 0}
                            }
                        }
                    except Exception:
                        pass
                    APP_STATE["screen"] = "lobby"
                    APP_STATE["ui"] = None
                    add_notification("加入房间成功，已进入大厅", color=(50, 180, 80))
                else:
                    add_notification(f"加入房间失败: {data.get('msg', '未知错误')}", color=(200, 50, 50))
            elif event == MSG_LEAVE_ROOM and data.get("ok"):
                APP_STATE["screen"] = "room_list"
                APP_STATE["ui"] = None
                APP_STATE["current_room"] = None
                net.list_rooms()
                # 不显示额外通知，返回房间列表本身就是反馈
            continue

        # 房间状态更新（兼容老的 room_state）
        if msg.type == MSG_ROOM_UPDATE or msg.type == "room_state":
            APP_STATE["current_room"] = data

            # 更新 HUD（倒计时 + 词语），以服务器状态为准，保证所有玩家统一
            if APP_STATE["screen"] == "play" and ui and "hud" in ui:
                hud = ui["hud"]
                player_id = APP_STATE["settings"].get("player_id")
                drawer_id = data.get("drawer_id")
                hud["is_drawer"] = (player_id == drawer_id)
                # 如果是绘者，显示服务器给的词语；否则隐藏
                if hud["is_drawer"]:
                    hud["current_word"] = data.get("current_word")
                else:
                    hud["current_word"] = None

                # 同步回合时长与剩余时间，保证中途加入的玩家看到一致的倒计时
                try:
                    if "round_duration" in data:
                        hud["round_time_total"] = float(data.get("round_duration") or hud.get("round_time_total", 60))
                    if "time_left" in data:
                        hud["round_time_left"] = float(data.get("time_left") or hud.get("round_time_left", 60))
                except Exception:
                    pass

            if APP_STATE["screen"] == "lobby":
                APP_STATE["ui"] = None
            if data.get("status") == "playing" and APP_STATE["screen"] == "lobby":
                APP_STATE["screen"] = "play"
                APP_STATE["ui"] = None
            continue

        # 服务器主动广播的房间列表更新（无需客户端手动刷新）
        if msg.type == "rooms_update":
            rooms = data.get("rooms", [])
            APP_STATE["rooms"] = rooms
            if APP_STATE.get("screen") == "room_list":
                # 重建UI以刷新房间按钮列表
                APP_STATE["ui"] = None
            continue

        # 服务器发送的 event 类型消息（游戏事件）
        if msg.type == "event":
            event_type = data.get("type")
            if event_type == MSG_START_GAME and data.get("ok"):
                APP_STATE["screen"] = "play"
                APP_STATE["ui"] = None
                drawer_name = data.get("drawer_name") or "某人"
                # 优先使用服务器提供的 round_number/max_rounds，保证与房主设置一致
                try:
                    round_num = int(data.get("round_number") or data.get("round") or 1)
                except Exception:
                    round_num = 1
                try:
                    # 若事件中未显式提供，则退回到 current_room 的 max_rounds 或默认 3
                    max_rounds = int(data.get("max_rounds") or (APP_STATE.get("current_room") or {}).get("max_rounds") or 3)
                except Exception:
                    max_rounds = 3
                add_notification(f"游戏开始！第{round_num}/{max_rounds}轮，{drawer_name}是绘画者", color=(50, 200, 50))
                continue
            if event_type == MSG_NEXT_ROUND:
                drawer_name = data.get("drawer_name") or "某人"
                try:
                    round_num = int(data.get("round_number") or data.get("round") or 1)
                except Exception:
                    round_num = 1
                try:
                    max_rounds = int(data.get("max_rounds") or (APP_STATE.get("current_room") or {}).get("max_rounds") or 3)
                except Exception:
                    max_rounds = 3
                add_notification(f"第{round_num}/{max_rounds}轮开始，{drawer_name}是绘画者", color=(80, 150, 200))
                # 清空画布
                if ui and "canvas" in ui:
                    ui["canvas"].clear()
                continue
            if event_type == "guess_correct":
                player_name = data.get("player_name", "某人")
                word = data.get("word", "")
                add_notification(f"🎉 {player_name} 猜对了：{word}！", color=(50, 200, 50))
                continue
            if event_type == MSG_GIVE_SCORE:
                player_name = data.get("player_name", "某人")
                score = data.get("score", 0)
                add_notification(f"{player_name} 获得 {score} 分", color=(80, 150, 200))
                continue
            if event_type == MSG_KICK_PLAYER:
                APP_STATE["screen"] = "room_list"
                APP_STATE["ui"] = None
                APP_STATE["current_room"] = None
                add_notification("你被踢出了房间", color=(200, 50, 50))
                net.list_rooms()
                continue

        # 游戏结果
        if msg.type == MSG_GAME_RESULT:
            APP_STATE["game_result"] = data.get("ranking", [])
            APP_STATE["screen"] = "result"
            APP_STATE["ui"] = None
            add_notification("游戏结束！查看最终排名", color=(200, 150, 50))
            continue

        # 聊天
        if msg.type == MSG_CHAT and ui and "chat" in ui:
            by_id = data.get("by") or data.get("by_id")
            name = data.get("by_name") or by_id or "玩家"
            # 跳过自己发送的消息（因为已经在本地显示了）
            if by_id and self_id and str(by_id) == str(self_id):
                continue
            text = str(data.get("text") or "").replace("\n", " ")
            try:
                ui["chat"].add_message(name, text)
            except Exception:
                pass
        elif msg.type == "draw_sync":
            # 处理远程绘画同步
            # 若 UI 尚未初始化（例如刚切换到 play 时），直接丢弃该帧以避免崩溃
            if not ui:
                continue
            by_id = data.get("by")
            if by_id and self_id and str(by_id) == str(self_id):
                # 跳过自己的绘画动作（已在本地显示）
                continue
            draw_data = data.get("data", {})
            try:
                canvas = ui.get("canvas")
                if canvas:
                    canvas.apply_remote_action(draw_data)
            except Exception:
                pass
        elif msg.type == "room_state":
            if not ui:
                continue
            hud = ui.get("hud")
            if hud:
                try:
                    hud["round_time_left"] = data.get("time_left", hud.get("round_time_left", 60))
                except Exception:
                    pass

        # 错误反馈
        if msg.type == "error":
            err = data.get("msg") or "操作失败"
            # 在创建房间加载界面中，将错误写入实时日志
            try:
                if APP_STATE.get("screen") == "creating_room":
                    logs = APP_STATE.get("creating_logs")
                    if isinstance(logs, list):
                        logs.append(f"错误: {err}")
            except Exception:
                pass
            add_notification(f"错误: {err}", color=(200, 60, 60))
            continue


def update_and_draw_hud(screen: pygame.Surface, ui: Dict[str, Any]) -> None:
    """更新倒计时并绘制顶部 HUD（计时、词、模式与画笔状态）。"""
    hud = ui.get("hud", {})
    if not hud:
        return
    now = pygame.time.get_ticks()
    dt_ms = now - hud.get("last_tick", now)
    hud["last_tick"] = now
    # 更新倒计时（每秒减少）
    hud["round_time_left"] = max(0, hud.get("round_time_left", 60) - dt_ms / 1000.0)

    # 背景条
    pad = 16
    top_h = int(hud.get("topbar_h", 44))
    rect = pygame.Rect(pad, pad, screen.get_width() - pad * 2 - 260 - pad, top_h)
    pygame.draw.rect(screen, (245, 245, 245), rect)
    pygame.draw.rect(screen, (200, 200, 200), rect, 2)

    # 内容：时间、词、模式、颜色与大小
    try:
        font = pygame.font.SysFont("Microsoft YaHei", 20)
    except Exception:
        font = pygame.font.SysFont(None, 20)

    # 时间
    t_left = int(hud.get("round_time_left", 60))
    time_txt = font.render(f"剩余时间: {t_left}s", True, (60, 60, 60))
    screen.blit(time_txt, (rect.x + 12, rect.y + (top_h - time_txt.get_height()) // 2))

    # 当前词（仅绘者看得见，其他玩家隐藏）
    is_drawer = hud.get("is_drawer", False)
    if is_drawer:
        word = hud.get("current_word") or "(未选择)"
        word_display = f"当前词: {word}"
    else:
        word_display = "当前词: (隐藏)"  # 非绘者看不到词语
    word_txt = font.render(word_display, True, (60, 60, 60))
    screen.blit(word_txt, (time_txt.get_rect(topleft=(rect.x + 12, rect.y)).right + 24, rect.y + (top_h - word_txt.get_height()) // 2))

    # 模式与画笔
    canvas: Canvas = ui["canvas"]
    mode_txt = font.render("模式: 橡皮" if canvas.mode == "erase" else "模式: 画笔", True, (60, 60, 60))
    screen.blit(mode_txt, (rect.right - 360, rect.y + (top_h - mode_txt.get_height()) // 2))

    # 颜色与大小展示
    color_rect = pygame.Rect(rect.right - 220, rect.y + 10, 24, top_h - 20)
    pygame.draw.rect(screen, canvas.brush_color, color_rect)
    pygame.draw.rect(screen, (180, 180, 180), color_rect, 1)
    size_txt = font.render(f"大小: {canvas.brush_size}", True, (60, 60, 60))
    screen.blit(size_txt, (color_rect.right + 12, rect.y + (top_h - size_txt.get_height()) // 2))


def main() -> None:
    """Start the Pygame client and run the main loop."""
    logger.info("%s", "=" * 50)
    logger.info("Draw & Guess 游戏客户端启动中...")
    logger.info("%s", "=" * 50)

    try:
        pygame.init()
        # 显式初始化 mixer 以确保音效正常播放
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            logger.warning(f"初始化音频设备失败: {e}")

        # 初始化SDL文本输入支持（用于中文输入法）
        try:
            import os
            os.environ['SDL_IME_SHOW_UI'] = '1'
            # 重新初始化显示模块以应用环境变量
            pygame.display.quit()
            pygame.display.init()
        except Exception as e:
            logger.warning(f"初始化输入法支持失败: {e}")

        # 加载持久化设置并确保玩家标识
        load_settings()
        ensure_player_identity()

        # 预加载音效
        confirm_sound = None
        if CONFIRM_SOUND_PATH.exists():
            try:
                confirm_sound = pygame.mixer.Sound(str(CONFIRM_SOUND_PATH))
            except Exception as e:
                logger.warning(f"加载确认音效失败: {e}")
        # 应用音量到音效
        try:
            vol = float(APP_STATE["settings"].get("volume", 80)) / 100.0
            if confirm_sound:
                confirm_sound.set_volume(max(0.0, min(1.0, vol)))
        except Exception:
            pass
        # 将音效保存到全局状态以便设置界面动态调整
        APP_STATE["confirm_sound"] = confirm_sound

        # Create a window or fullscreen depending on saved settings
        flags = pygame.RESIZABLE
        if APP_STATE["settings"].get("fullscreen"):
            flags = pygame.FULLSCREEN_DESKTOP
            screen = pygame.display.set_mode((0, 0), flags)
        else:
            screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)
        pygame.display.set_caption(WINDOW_TITLE)

        logo_orig, logo_base_size, logo_anchor = load_logo(LOGO_PATH, screen.get_size())
        APP_STATE["ui"] = None

        # 防抖延迟（毫秒），在连续调整窗口时等待短暂静默期再重建 UI
        RESIZE_DEBOUNCE_MS = 140

        def on_back():
            APP_STATE["screen"] = "menu"
            APP_STATE["ui"] = None
            nonlocal logo_orig, logo_base_size, logo_anchor, buttons
            logo_orig, logo_base_size, logo_anchor = load_logo(LOGO_PATH, screen.get_size())
            buttons = create_buttons_from_config(BUTTONS_CONFIG, CALLBACKS, screen.get_size(), logo_anchor, screen_filter="menu", click_sound=confirm_sound)

        def on_light_theme():
            APP_STATE["settings"]["theme"] = "light"
            save_settings()

        def on_dark_theme():
            APP_STATE["settings"]["theme"] = "dark"
            save_settings()

        def on_fullscreen():
            nonlocal screen, logo_orig, logo_base_size, logo_anchor
            cur = bool(APP_STATE["settings"].get("fullscreen", False))
            new = not cur
            APP_STATE["settings"]["fullscreen"] = new
            save_settings()
            try:
                if new:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN_DESKTOP)
                else:
                    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
                logo_orig, logo_base_size, logo_anchor = load_logo(LOGO_PATH, screen.get_size())
                APP_STATE["ui"] = None
            except Exception:
                pass

        def on_send():
            ui = APP_STATE["ui"]
            if ui and ui.get("input"):
                txt = ui["input"].text.strip()
                if txt:
                    cb = ui["input"].on_submit
                    if cb:
                        cb(txt)
                    ui["input"].text = ""

        CALLBACKS.update({
            "on_back": on_back,
            "on_light_theme": on_light_theme,
            "on_dark_theme": on_dark_theme,
            "on_fullscreen": on_fullscreen,
            "on_send": on_send,
        })

        clock = pygame.time.Clock()
        running = True

        buttons = create_buttons_from_config(BUTTONS_CONFIG, CALLBACKS, screen.get_size(), logo_anchor, screen_filter="menu", click_sound=confirm_sound)

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    # 记录待处理的尺寸（不在每次事件中重建显示），等待防抖期结束后一次性调用 set_mode
                    APP_STATE["pending_resize_size"] = event.size
                    APP_STATE["pending_resize_until"] = pygame.time.get_ticks() + RESIZE_DEBOUNCE_MS
                    # 保存当前聊天框的消息，以便窗口改变后恢复
                    ui = APP_STATE.get("ui")
                    if ui and isinstance(ui, dict) and "chat" in ui:
                        chat = ui["chat"]
                        if hasattr(chat, "messages"):
                            APP_STATE["_saved_chat_messages"] = chat.messages[:]
                            if hasattr(chat, "scroll_offset"):
                                APP_STATE["_saved_chat_scroll"] = chat.scroll_offset
                else:
                    # 根据当前界面分发事件
                    if APP_STATE["screen"] == "menu":
                        for b in buttons:
                            b.handle_event(event)

                        # 进入 play/settings 时在渲染阶段统一构建 UI（含配置按钮）
                        if APP_STATE["screen"] in ("play", "settings"):
                            APP_STATE["ui"] = None
                    elif APP_STATE["screen"] == "play":
                        ui = APP_STATE["ui"]
                        if ui is None:
                            ui = build_play_ui(screen.get_size())
                            # create play-specific buttons from config and attach to ui
                            play_buttons = create_buttons_from_config(BUTTONS_CONFIG, CALLBACKS, screen.get_size(), logo_anchor, screen_filter="play", click_sound=confirm_sound)
                            for pb in play_buttons:
                                cid = getattr(pb, "_cfg_id", None)
                                if cid == "play_back":
                                    ui["back_btn"] = pb
                                elif cid == "play_send":
                                    ui["send_btn"] = pb
                            APP_STATE["ui"] = ui

                        # 更新画布权限：只有绘画者可以绘画
                        current_room = APP_STATE.get("current_room") or {}
                        drawer_id = current_room.get("drawer_id")
                        self_id = APP_STATE.get("settings", {}).get("player_id")
                        is_drawer = drawer_id and self_id and str(drawer_id) == str(self_id)

                        if "canvas" in ui:
                            ui["canvas"].drawing_enabled = is_drawer
                        if "hud" in ui:
                            ui["hud"]["is_drawer"] = is_drawer

                        # 处理按钮事件
                        if ui.get("back_btn"):
                            ui["back_btn"].handle_event(event)
                        if ui.get("send_btn"):
                            ui["send_btn"].handle_event(event)

                        # 先处理鼠标事件到组件（工具栏、画布、输入框）
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            ui["toolbar"].handle_event(event)
                            ui["canvas"].handle_event(event)
                            ui["input"].handle_event(event)
                        elif event.type == pygame.MOUSEMOTION:
                            ui["toolbar"].handle_event(event)
                            ui["canvas"].handle_event(event)
                            ui["input"].handle_event(event)
                        elif event.type == pygame.MOUSEWHEEL and ui:
                            # 处理聊天框的滚轮事件（只在 UI 已初始化时）
                            try:
                                chat_rect = ui.get("chat").rect if ui.get("chat") else None
                                mouse_pos = pygame.mouse.get_pos()
                                if chat_rect and chat_rect.collidepoint(mouse_pos):
                                    # 如果鼠标在聊天框上，处理滚轮
                                    ui["chat"].handle_scroll(event.y)
                            except Exception:
                                pass
                        else:
                            # 其他事件（键盘等）
                            ui["input"].handle_event(event)
                            ui["canvas"].handle_event(event)
                        # 快捷键（输入框未激活时）
                        if event.type == pygame.KEYDOWN and not ui["input"].active:
                            from src.shared.constants import BRUSH_COLORS, BRUSH_SIZES
                            if event.key in (pygame.K_e,):
                                ui["canvas"].set_mode("erase" if ui["canvas"].mode == "draw" else "draw")
                            elif event.key in (pygame.K_k,):
                                ui["canvas"].clear()
                            elif event.key in (pygame.K_LEFTBRACKET,):  # [
                                # 降低画笔大小
                                cur = ui["canvas"].brush_size
                                sizes = sorted(BRUSH_SIZES)
                                smaller = max(s for s in sizes if s < cur) if any(s < cur for s in sizes) else cur
                                ui["canvas"].set_brush_size(smaller)
                                ui["toolbar"].set_selected_size(smaller)
                            elif event.key in (pygame.K_RIGHTBRACKET,):  # ]
                                cur = ui["canvas"].brush_size
                                sizes = sorted(BRUSH_SIZES)
                                larger = min(s for s in sizes if s > cur) if any(s > cur for s in sizes) else cur
                                ui["canvas"].set_brush_size(larger)
                                ui["toolbar"].set_selected_size(larger)
                            elif pygame.K_1 <= event.key <= pygame.K_9:
                                idx = event.key - pygame.K_1
                                if 0 <= idx < len(BRUSH_COLORS):
                                    chosen = BRUSH_COLORS[idx]
                                    ui["canvas"].set_color(chosen)
                                    ui["toolbar"].set_selected_color(chosen)
                    elif APP_STATE["screen"] == "room_list":
                        ui = APP_STATE["ui"]
                        need_rebuild_rooms = False
                        if ui is None:
                            ui = build_room_list_ui(screen.get_size())
                            APP_STATE["ui"] = ui
                            need_rebuild_rooms = True
                            # 进入房间列表时自动拉取一次列表
                            try:
                                player_id = APP_STATE["settings"].get("player_id") or ensure_player_identity()
                                net = get_network_client()
                                if net.connect(APP_STATE["settings"]["player_name"], player_id):
                                    net.list_rooms()
                                else:
                                    add_notification("无法连接服务器，检查地址与端口", color=(200, 60, 60))
                            except Exception:
                                pass

                        # 每次都根据 APP_STATE["rooms"] 重建房间按钮，确保刷新生效
                        if need_rebuild_rooms or ui.get("_rooms_version") != id(APP_STATE.get("rooms")):
                            rooms = APP_STATE.get("rooms", [])
                            room_buttons = []
                            start_y = 150
                            for i, r in enumerate(rooms):
                                rid = r["room_id"]
                                count = r["player_count"]
                                status = r["status"]
                                btn = Button(
                                    x=50, y=start_y + i * 60, width=400, height=50,
                                    text=f"房间 {rid} ({count}人) - {status}",
                                    bg_color=(200, 200, 200), fg_color=(0, 0, 0),
                                    font_name="Microsoft YaHei", font_size=20
                                )
                                def _join(rid=rid):
                                    net = get_network_client()
                                    if net.connect(APP_STATE["settings"]["player_name"], APP_STATE["settings"].get("player_id")):
                                        add_notification(f"尝试加入房间 {rid}...", color=(50, 150, 220))
                                        net.join_room(rid)
                                    else:
                                        add_notification("无法连接服务器，检查地址与端口", color=(200, 60, 60))
                                btn.on_click = _join
                                room_buttons.append(btn)
                            ui["room_buttons"] = room_buttons
                            ui["_rooms_version"] = id(APP_STATE.get("rooms"))

                        # 事件分发：确保 ui 存在后再处理
                        if ui:
                            if ui.get("refresh_btn"): ui["refresh_btn"].handle_event(event)
                            if ui.get("create_btn"): ui["create_btn"].handle_event(event)
                            if ui.get("back_btn"): ui["back_btn"].handle_event(event)
                            for btn in ui.get("room_buttons", []):
                                btn.handle_event(event)
                        # 定时自动刷新房间列表（每2秒）
                        if APP_STATE.get("screen") == "room_list":
                            last = APP_STATE.get("rooms_last_refresh", 0)
                            now = pygame.time.get_ticks()
                            if now - last > 2000:
                                APP_STATE["rooms_last_refresh"] = now
                                try:
                                    player_id = APP_STATE["settings"].get("player_id") or ensure_player_identity()
                                    net = get_network_client()
                                    if net.connected or net.connect(APP_STATE["settings"]["player_name"], player_id):
                                        net.list_rooms()
                                except Exception:
                                    pass

                    elif APP_STATE["screen"] == "lobby":
                        ui = APP_STATE["ui"]
                        if ui is None:
                            ui = build_lobby_ui(screen.get_size())
                            APP_STATE["ui"] = ui
                            # Rebuild kick buttons if owner
                            current_room = APP_STATE.get("current_room") or {}
                            players = current_room.get("players") or {}
                            owner_id = current_room.get("owner_id")
                            self_id = APP_STATE.get("settings", {}).get("player_id")

                            kick_buttons = []
                            if str(owner_id) == str(self_id):
                                start_y = 150
                                idx = 0
                                for pid, pdata in players.items():
                                    if str(pid) == str(self_id):
                                        idx += 1
                                        continue
                                    btn = Button(
                                        x=400, y=start_y + idx * 40, width=60, height=30,
                                        text="踢出", bg_color=(200, 50, 50), fg_color=(255, 255, 255),
                                        font_name="Microsoft YaHei", font_size=16
                                    )
                                    def _kick(pid=pid):
                                        net = get_network_client()
                                        net.kick_player(pid)
                                    btn.on_click = _kick
                                    kick_buttons.append(btn)
                                    idx += 1
                            ui["kick_buttons"] = kick_buttons

                        # 开始游戏按钮对所有人可点击，服务器侧仍做权限校验
                        if ui.get("start_btn"): ui["start_btn"].handle_event(event)

                        # 房主设置折叠/展开按钮
                        current_room = APP_STATE.get("current_room") or {}
                        owner_id = current_room.get("owner_id")
                        self_id = APP_STATE.get("settings", {}).get("player_id")
                        is_owner = owner_id and self_id and str(owner_id) == str(self_id)
                        if is_owner and ui.get("settings_toggle_btn"):
                            ui["settings_toggle_btn"].handle_event(event)

                        # 仅房主可编辑游戏参数
                        if is_owner and not APP_STATE.get("_lobby_settings_collapsed", False):
                            if ui.get("rounds_input"): ui["rounds_input"].handle_event(event)
                            if ui.get("time_input"): ui["time_input"].handle_event(event)
                            if ui.get("rest_input"): ui["rest_input"].handle_event(event)
                            if ui.get("apply_btn"): ui["apply_btn"].handle_event(event)

                        if ui.get("leave_btn"): ui["leave_btn"].handle_event(event)
                        if ui.get("chat_input"): ui["chat_input"].handle_event(event)
                        if ui.get("send_btn"): ui["send_btn"].handle_event(event)
                        # 聊天框滚轮
                        if event.type == pygame.MOUSEWHEEL and ui.get("chat"):
                            try:
                                chat_rect = ui["chat"].rect
                                mouse_pos = pygame.mouse.get_pos()
                                if chat_rect.collidepoint(mouse_pos):
                                    ui["chat"].handle_scroll(event.y)
                            except Exception:
                                pass
                        for btn in ui.get("kick_buttons", []):
                            btn.handle_event(event)

                    elif APP_STATE["screen"] == "creating_room":
                        # 创建房间加载界面：仅需要处理“返回房间列表”按钮
                        ui = APP_STATE["ui"]
                        if ui is None:
                            # 在右上角放置一个返回按钮，允许用户中断等待并回到房间列表
                            back_btn = Button(
                                x=50,
                                y=50,
                                width=160,
                                height=45,
                                text="返回房间列表",
                                bg_color=(200, 100, 100),
                                fg_color=(255, 255, 255),
                                font_name="Microsoft YaHei",
                                font_size=20,
                            )

                            def _on_back_from_creating() -> None:
                                # 返回房间列表并重新拉取一次列表
                                APP_STATE["screen"] = "room_list"
                                APP_STATE["ui"] = None
                                try:
                                    player_id = APP_STATE["settings"].get("player_id") or ensure_player_identity()
                                    net = get_network_client()
                                    if net.connected or net.connect(APP_STATE["settings"]["player_name"], player_id):
                                        net.list_rooms()
                                except Exception:
                                    pass

                            back_btn.on_click = _on_back_from_creating
                            ui = {"back_btn": back_btn}
                            APP_STATE["ui"] = ui

                        if ui.get("back_btn"):
                            ui["back_btn"].handle_event(event)

                    elif APP_STATE["screen"] == "result":
                        ui = APP_STATE["ui"]
                        if ui and ui.get("back_btn"):
                            ui["back_btn"].handle_event(event)

                    elif APP_STATE["screen"] == "settings":
                        ui = APP_STATE["ui"]
                        if ui is None:
                            ui = build_settings_ui(screen.get_size(), confirm_sound=confirm_sound)
                            # attach settings buttons from config
                            settings_buttons = create_buttons_from_config(BUTTONS_CONFIG, CALLBACKS, screen.get_size(), logo_anchor, screen_filter="settings", click_sound=confirm_sound)
                            for sb in settings_buttons:
                                cid = getattr(sb, "_cfg_id", None)
                                if cid == "settings_back":
                                    ui["back_btn"] = sb
                                elif cid == "settings_light":
                                    ui["light_btn"] = sb
                                elif cid == "settings_dark":
                                    ui["dark_btn"] = sb
                                elif cid == "settings_fullscreen":
                                    ui["fullscreen_btn"] = sb
                            APP_STATE["ui"] = ui

                        # 处理设置界面事件
                        ui["player_name_input"].handle_event(event)
                        if ui.get("server_host_input"):
                            ui["server_host_input"].handle_event(event)

                        # 处理按钮事件
                        for btn_key in ["back_btn", "light_btn", "dark_btn", "fullscreen_btn", "confirm_name_btn", "confirm_host_btn", "server_lan_btn", "server_remote_btn"]:
                            if ui.get(btn_key):
                                ui[btn_key].handle_event(event)

                        # 音量滑块拖动
                        if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                            if ui["volume_slider_rect"].collidepoint(event.pos):
                                rel_x = event.pos[0] - ui["volume_slider_rect"].x
                                vol = max(0, min(100, int(rel_x / ui["volume_slider_rect"].width * 100)))
                                APP_STATE["settings"]["volume"] = vol
                                save_settings()
                                # 动态调整点击音效音量
                                try:
                                    snd = APP_STATE.get("confirm_sound")
                                    if snd:
                                        snd.set_volume(vol / 100.0)
                                except Exception:
                                    pass

            if APP_STATE["screen"] == "play":
                process_network_messages(APP_STATE.get("ui"))
            elif APP_STATE["screen"] in ("room_list", "lobby", "creating_room"):
                process_network_messages(APP_STATE.get("ui"))

            # 如果存在待处理的 resize 且防抖期已过，则执行一次性的重建操作
            now_tick = pygame.time.get_ticks()
            pending_until = APP_STATE.get("pending_resize_until", 0)
            pending_size = APP_STATE.get("pending_resize_size")
            if pending_size and now_tick >= pending_until:
                # finalize resize handling once: set display mode once and rebuild UI
                # 保留全屏状态，不要在resize时强制改变全屏标志
                try:
                    is_fullscreen = bool(APP_STATE["settings"].get("fullscreen", False))
                    if is_fullscreen:
                        screen = pygame.display.set_mode(pending_size, pygame.FULLSCREEN_DESKTOP)
                    else:
                        screen = pygame.display.set_mode(pending_size, pygame.RESIZABLE)
                except Exception:
                    pass
                try:
                    if APP_STATE["screen"] == "menu":
                        logo_orig, logo_base_size, logo_anchor = load_logo(LOGO_PATH, pending_size)
                        buttons = create_buttons_from_config(
                            BUTTONS_CONFIG, CALLBACKS, pending_size, logo_anchor, screen_filter="menu", click_sound=confirm_sound
                        )
                    elif APP_STATE["screen"] in ("play", "settings"):
                        # 在渲染阶段重建 UI（play/settings 会在后续逻辑中重建）
                        APP_STATE["ui"] = None
                except Exception:
                    pass
                APP_STATE["pending_resize_size"] = None
                APP_STATE["pending_resize_until"] = 0

            screen.fill((245, 248, 255))  # 淡蓝白色背景，更柔和

            if APP_STATE["screen"] == "menu":
                if logo_orig is not None:
                    # Animate: breathing (scale) + small swing (rotation)
                    base_w, base_h = logo_base_size
                    t = pygame.time.get_ticks() / 1000.0
                    scale = 1.0 + LOGO_BREATH_AMPLITUDE * math.sin(2 * math.pi * LOGO_BREATH_FREQ * t)
                    angle = LOGO_SWING_AMP * math.sin(2 * math.pi * LOGO_SWING_FREQ * t)

                    sw_scaled = max(1, int(base_w * scale))
                    sh_scaled = max(1, int(base_h * scale))
                    try:
                        scaled = pygame.transform.smoothscale(logo_orig, (sw_scaled, sh_scaled))
                    except Exception:
                        scaled = pygame.transform.scale(logo_orig, (sw_scaled, sh_scaled))

                    rotated = pygame.transform.rotate(scaled, angle)
                    rrect = rotated.get_rect()
                    # place logo using top-right anchor
                    rrect.topright = logo_anchor
                    screen.blit(rotated, rrect)

                # Update button slide-in animations
                now = pygame.time.get_ticks() / 1000.0
                for b in buttons:
                    anim = BUTTON_ANIMS.get(id(b))
                    if anim and not anim.get("finished", False):
                        elapsed = now - anim.get("delay", 0)
                        dur = anim.get("duration", 0.5)
                        if elapsed <= 0:
                            b.set_position(anim["start_x"], anim["y"])
                        else:
                            prog = min(1.0, elapsed / dur)
                            eased = 1 - pow(1 - prog, 3)
                            sx = anim["start_x"]
                            tx = anim["target_x"]
                            cur_x = int(sx + (tx - sx) * eased)
                            b.set_position(cur_x, anim["y"])
                            if prog >= 1.0:
                                anim["finished"] = True

                for b in buttons:
                    b.draw(screen)
            elif APP_STATE["screen"] == "play":
                ui = APP_STATE["ui"]
                if ui is None:
                    ui = build_play_ui(screen.get_size())
                    # create play-specific buttons from config and attach to ui
                    play_buttons = create_buttons_from_config(BUTTONS_CONFIG, CALLBACKS, screen.get_size(), logo_anchor, screen_filter="play", click_sound=confirm_sound)
                    for pb in play_buttons:
                        cid = getattr(pb, "_cfg_id", None)
                        if cid == "play_back":
                            ui["back_btn"] = pb
                        elif cid == "play_send":
                            ui["send_btn"] = pb
                    # 初次进入游戏界面时，用服务器的 current_room 状态同步 HUD，
                    # 确保中途加入的玩家看到与已有玩家一致的回合、倒计时与词语。
                    try:
                        current_room = APP_STATE.get("current_room") or {}
                        hud = ui.get("hud")
                        if isinstance(hud, dict) and current_room:
                            # 同步回合时长与剩余时间
                            rd = current_room.get("round_duration")
                            if isinstance(rd, (int, float)):
                                hud["round_time_total"] = float(rd)
                            tl = current_room.get("time_left")
                            if isinstance(tl, (int, float)):
                                hud["round_time_left"] = float(tl)

                            # 同步绘者身份与当前词语
                            drawer_id = current_room.get("drawer_id")
                            self_id = APP_STATE.get("settings", {}).get("player_id")
                            hud["is_drawer"] = bool(drawer_id and self_id and str(drawer_id) == str(self_id))
                            if hud["is_drawer"]:
                                hud["current_word"] = current_room.get("current_word")
                            else:
                                hud["current_word"] = None
                    except Exception:
                        pass
                    APP_STATE["ui"] = ui

                # 根据主题绘制背景
                theme = APP_STATE["settings"].get("theme", "light")
                if theme == "dark":
                    screen.fill((28, 30, 35))
                else:
                    screen.fill((250, 250, 252))

                # 渲染各组件
                update_and_draw_hud(screen, ui)
                ui["canvas"].draw(screen)
                ui["toolbar"].draw(screen)
                ui["chat"].draw(screen)
                ui["input"].draw(screen)
                if ui.get("send_btn"):
                    ui["send_btn"].draw(screen)
                if ui.get("back_btn"):
                    ui["back_btn"].draw(screen)

                # 显示玩家得分排行：使用画布左侧预留区域，避免遮挡画笔工具栏
                current_room = APP_STATE.get("current_room") or {}
                players = current_room.get("players", {})
                if players and ui.get("canvas"):
                    try:
                        font_score = pygame.font.SysFont("Microsoft YaHei", 20)
                    except:
                        font_score = pygame.font.SysFont(None, 20)

                    canvas_rect = ui["canvas"].rect
                    # 画布左侧预留约 180 像素作为积分榜区域，这里整体贴着左侧边缘
                    score_x = max(10, canvas_rect.x - 180)
                    score_y = canvas_rect.y + 10

                    # 标题
                    title = font_score.render("得分榜", True, (60, 60, 60))
                    screen.blit(title, (score_x + 40, score_y))

                    # 排序玩家
                    sorted_players = sorted(players.items(), key=lambda x: x[1].get("score", 0), reverse=True)

                    # 当前绘制起始 y 位置（支持根据内容高度动态累积）
                    row_y = score_y + 40
                    max_name_width = 120  # 名字区域最大宽度，超出时自动换行

                    for pid, pdata in sorted_players:
                        name = pdata.get("name", "玩家")
                        score = pdata.get("score", 0)
                        drawer_id = current_room.get("drawer_id")
                        is_drawer = (pid == drawer_id)

                        # 名字前缀：标记当前绘画者
                        prefix = "正在创作 " if is_drawer else ""
                        full_name = f"{prefix}{name}"

                        # 简单按字符宽度自动换行，保证文本不延伸到画板上
                        lines = []
                        current_line = ""
                        for ch in full_name:
                            test = current_line + ch
                            if not current_line:
                                current_line = ch
                                continue
                            test_surf = font_score.render(test, True, (40, 40, 40))
                            if test_surf.get_width() <= max_name_width:
                                current_line = test
                            else:
                                lines.append(current_line)
                                current_line = ch
                        if current_line:
                            lines.append(current_line)
                        if not lines:
                            lines = [full_name]

                        line_height = font_score.get_height()
                        text_h = line_height * len(lines)

                        # 背景（高度根据行数自适应，完全在画布左侧的单独区域内）
                        bg_height = max(28, text_h + 6)
                        bg_rect = pygame.Rect(score_x, row_y - 5, 160, bg_height)
                        color = (255, 250, 200) if is_drawer else (245, 245, 245)
                        pygame.draw.rect(screen, color, bg_rect)
                        pygame.draw.rect(screen, (200, 200, 200), bg_rect, 1)

                        # 名字多行绘制
                        for li, line in enumerate(lines):
                            line_surf = font_score.render(line, True, (40, 40, 40))
                            screen.blit(line_surf, (score_x + 5, row_y + li * line_height))

                        # 分数垂直居中绘制在背景右侧
                        score_txt = font_score.render(f"{score}", True, (40, 40, 40))
                        score_y_center = row_y + (bg_height - score_txt.get_height()) // 2
                        screen.blit(score_txt, (score_x + 120, score_y_center))

                        # 为下一名玩家向下偏移，预留少量行间距
                        row_y += bg_height + 4

                # 移除“下一轮”按钮显示
            elif APP_STATE["screen"] == "room_list":
                process_network_messages(APP_STATE.get("ui"))
                ui = APP_STATE["ui"]
                if ui is None:
                    ui = build_room_list_ui(screen.get_size())
                    APP_STATE["ui"] = ui

                if ui:
                    if ui.get("refresh_btn"): ui["refresh_btn"].draw(screen)
                    if ui.get("create_btn"): ui["create_btn"].draw(screen)
                    if ui.get("back_btn"): ui["back_btn"].draw(screen)
                    for btn in ui.get("room_buttons", []):
                        btn.draw(screen)

                    # Title
                    try:
                        font = pygame.font.SysFont("Microsoft YaHei", 40)
                    except:
                        font = pygame.font.SysFont(None, 40)
                    title = font.render("房间列表", True, (0, 0, 0))
                    screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 50))

            elif APP_STATE["screen"] == "creating_room":
                # 创建房间加载界面：显示主提示、返回按钮和实时日志
                process_network_messages(APP_STATE.get("ui"))
                screen.fill((240, 242, 250))

                ui = APP_STATE.get("ui") or {}

                try:
                    font_title = pygame.font.SysFont("Microsoft YaHei", 40)
                    font_tip = pygame.font.SysFont("Microsoft YaHei", 24)
                    font_log = pygame.font.SysFont("Microsoft YaHei", 20)
                except Exception:
                    font_title = pygame.font.SysFont(None, 40)
                    font_tip = pygame.font.SysFont(None, 24)
                    font_log = pygame.font.SysFont(None, 20)

                text = "正在创建房间..."
                title = font_title.render(text, True, (50, 80, 150))
                tx = (screen.get_width() - title.get_width()) // 2
                ty = screen.get_height() // 2 - 80
                screen.blit(title, (tx, ty))

                tip_txt = font_tip.render("如长时间无响应，可点击左上角返回房间列表", True, (100, 100, 110))
                tip_x = (screen.get_width() - tip_txt.get_width()) // 2
                tip_y = ty + 60
                screen.blit(tip_txt, (tip_x, tip_y))

                # 绘制实时日志（仅显示最近若干条）
                logs = APP_STATE.get("creating_logs") or []
                max_lines = 8
                start_y = tip_y + 50
                line_spacing = 26
                visible_logs = logs[-max_lines:]
                for i, line in enumerate(visible_logs):
                    log_surf = font_log.render(str(line), True, (80, 80, 90))
                    lx = (screen.get_width() - log_surf.get_width()) // 2
                    ly = start_y + i * line_spacing
                    screen.blit(log_surf, (lx, ly))

                # 返回按钮（如果已创建）
                if ui.get("back_btn"):
                    ui["back_btn"].draw(screen)

            elif APP_STATE["screen"] == "lobby":
                process_network_messages(APP_STATE.get("ui"))
                ui = APP_STATE["ui"]
                if ui is None:
                    ui = build_lobby_ui(screen.get_size())
                    APP_STATE["ui"] = ui

                if ui:
                    # 背景按主题
                    theme = APP_STATE["settings"].get("theme", "light")
                    if theme == "dark":
                        screen.fill((28, 30, 35))
                        title_color = (200, 220, 255)
                        text_color = (220, 220, 220)
                    else:
                        screen.fill((240, 242, 250))
                        title_color = (0, 0, 0)
                        text_color = (0, 0, 0)

                    sw, sh = screen.get_size()
                    # 检查是否为房主
                    current_room = APP_STATE.get("current_room") or {}
                    owner_id = current_room.get("owner_id")
                    self_id = APP_STATE.get("settings", {}).get("player_id")
                    is_owner = owner_id and self_id and str(owner_id) == str(self_id)

                    # 显示“开始游戏”按钮（非房主点击后由服务器拒绝）
                    if ui.get("start_btn"): ui["start_btn"].draw(screen)
                    if ui.get("leave_btn"): ui["leave_btn"].draw(screen)
                    for btn in ui.get("kick_buttons", []):
                        btn.draw(screen)

                    # Room Info（允许 current_room 为 None，使用空字典兜底）
                    current_room = APP_STATE.get("current_room") or {}
                    rid = current_room.get("room_id", "Unknown")
                    try:
                        font = pygame.font.SysFont("Microsoft YaHei", 30)
                        font_p = pygame.font.SysFont("Microsoft YaHei", 24)
                    except:
                        font = pygame.font.SysFont(None, 30)
                        font_p = pygame.font.SysFont(None, 24)

                    title = font.render(f"房间: {rid}", True, title_color)
                    screen.blit(title, (screen.get_width() // 2 - title.get_width() // 2, 50))
                    # 显示房主
                    owner_id = current_room.get("owner_id")
                    owner_name = None
                    if owner_id:
                        try:
                            owner_name = (current_room.get("players", {}) or {}).get(str(owner_id), {}).get("name")
                        except Exception:
                            owner_name = None
                    try:
                        font_owner = pygame.font.SysFont("Microsoft YaHei", 22)
                    except:
                        font_owner = pygame.font.SysFont(None, 22)
                    owner_label = f"房主: {owner_name or '未指定'}"
                    owner_txt = font_owner.render(owner_label, True, text_color)
                    screen.blit(owner_txt, (100, 110))

                    # Player List
                    players = current_room.get("players", {})
                    start_y = 150
                    idx = 0
                    for pid, pdata in players.items():
                        name = pdata.get("name", "Unknown")
                        score = pdata.get("score", 0)
                        txt = font_p.render(f"{name} - {score}分", True, text_color)
                        screen.blit(txt, (100, start_y + idx * 40))
                        idx += 1

                    # 游戏参数设置（仅房主）
                    # 房主设置面板：放到画面右侧竖直排列，并支持折叠
                    collapsed = APP_STATE.get("_lobby_settings_collapsed", False)
                    if ui.get("settings_toggle_btn") and is_owner:
                        # 根据当前折叠状态更新按钮文字
                        ui["settings_toggle_btn"].text = "展开房主设置" if collapsed else "收起房主设置"
                        ui["settings_toggle_btn"].draw(screen)

                    if is_owner and not collapsed:
                        try:
                            font_s = pygame.font.SysFont("Microsoft YaHei", 20)
                        except:
                            font_s = pygame.font.SysFont(None, 20)

                        # 使用输入框的位置来对齐文字和背景面板
                        rounds_rect = ui["rounds_input"].rect
                        time_rect = ui["time_input"].rect
                        rest_rect = ui["rest_input"].rect

                        # 预先计算标签最大宽度，用于为标签预留足够的左侧空间
                        label_texts = ["轮数", "时间/轮", "休息"]
                        max_label_w = 0
                        for text in label_texts:
                            surf = font_s.render(text, True, (60, 60, 60))
                            if surf.get_width() > max_label_w:
                                max_label_w = surf.get_width()

                        # 面板整体区域（包含标题、三个输入框和按钮）
                        panel_left = min(rounds_rect.x, time_rect.x, rest_rect.x) - (max_label_w + 30)
                        panel_top = min(rounds_rect.y, time_rect.y, rest_rect.y) - 40
                        panel_right = max(
                            rounds_rect.right,
                            time_rect.right,
                            rest_rect.right,
                            ui["apply_btn"].rect.right,
                        ) + 20
                        panel_bottom = ui["apply_btn"].rect.bottom + 20
                        panel_rect = pygame.Rect(
                            panel_left,
                            panel_top,
                            panel_right - panel_left,
                            panel_bottom - panel_top,
                        )

                        # 背景与边框
                        pygame.draw.rect(screen, (245, 245, 250), panel_rect)
                        pygame.draw.rect(screen, (200, 200, 220), panel_rect, 1)

                        # 标题
                        title_txt = font_s.render("房主游戏设置", True, (60, 60, 80))
                        screen.blit(title_txt, (panel_left + 10, panel_top + 10))

                        # 标签与输入框：根据 TextInput 位置对齐
                        def _draw_label(label: str, target_rect: pygame.Rect) -> None:
                            # 标签与对应输入框右对齐到同一“行”，并整体位于输入框左侧，不会被盖住
                            label_surf = font_s.render(label, True, (60, 60, 60))
                            ly = target_rect.y + (target_rect.height - label_surf.get_height()) // 2
                            lx = target_rect.x - label_surf.get_width() - 10
                            screen.blit(label_surf, (lx, ly))

                        _draw_label("轮数", rounds_rect)
                        _draw_label("时间/轮", time_rect)
                        _draw_label("休息", rest_rect)

                        ui["rounds_input"].draw(screen)
                        ui["time_input"].draw(screen)
                        ui["rest_input"].draw(screen)
                        # 让“应用设置”按钮在设置面板内水平居中，并同步更新文字位置
                        apply_btn = ui["apply_btn"]
                        new_x = panel_left + (panel_rect.width - apply_btn.rect.width) // 2
                        if apply_btn.rect.x != new_x:
                            apply_btn.set_position(new_x, apply_btn.rect.y)
                        apply_btn.draw(screen)

                    # 聊天面板
                    if ui.get("chat"):
                        ui["chat"].draw(screen)
                    if ui.get("chat_input"):
                        ui["chat_input"].draw(screen)
                    if ui.get("send_btn"):
                        ui["send_btn"].draw(screen)

            elif APP_STATE["screen"] == "result":
                # 游戏结果界面
                ui = APP_STATE["ui"]
                if ui is None:
                    ui = build_result_ui(screen.get_size())
                    APP_STATE["ui"] = ui

                screen.fill((240, 245, 250))

                # 标题
                try:
                    font_title = pygame.font.SysFont("Microsoft YaHei", 50, bold=True)
                    font_rank = pygame.font.SysFont("Microsoft YaHei", 32)
                    font_name = pygame.font.SysFont("Microsoft YaHei", 28)
                except:
                    font_title = pygame.font.SysFont(None, 50)
                    font_rank = pygame.font.SysFont(None, 32)
                    font_name = pygame.font.SysFont(None, 28)

                title = font_title.render("🏆 游戏结束 - 最终排名 🏆", True, (200, 100, 50))
                screen.blit(title, (sw // 2 - title.get_width() // 2, 80))

                # 显示排名
                ranking = APP_STATE.get("game_result", [])
                start_y = 200
                colors = [(255, 215, 0), (192, 192, 192), (205, 127, 50)]  # 金银铜

                for i, player_data in enumerate(ranking[:10]):  # 最多显示前10名
                    rank = i + 1
                    name = player_data.get("name", "玩家")
                    score = player_data.get("score", 0)

                    # 背景框
                    bg_color = colors[i] if i < 3 else (220, 220, 220)
                    bg_alpha = 120 if i < 3 else 80
                    bg_rect = pygame.Rect(sw // 2 - 250, start_y + i * 50, 500, 45)
                    s = pygame.Surface((bg_rect.width, bg_rect.height))
                    s.set_alpha(bg_alpha)
                    s.fill(bg_color)
                    screen.blit(s, bg_rect.topleft)

                    # 排名
                    rank_txt = font_rank.render(f"#{rank}", True, (60, 60, 60) if i >= 3 else (40, 40, 40))
                    screen.blit(rank_txt, (sw // 2 - 230, start_y + i * 50 + 8))

                    # 名字
                    name_txt = font_name.render(name, True, (20, 20, 20))
                    screen.blit(name_txt, (sw // 2 - 150, start_y + i * 50 + 10))

                    # 分数
                    score_txt = font_name.render(f"{score} 分", True, (20, 20, 20))
                    screen.blit(score_txt, (sw // 2 + 150, start_y + i * 50 + 10))

                # 返回按钮
                if ui.get("back_btn"):
                    ui["back_btn"].draw(screen)

            elif APP_STATE["screen"] == "settings":
                ui = APP_STATE["ui"]
                if ui is None:
                    ui = build_settings_ui(screen.get_size())
                    # attach settings buttons from config
                    settings_buttons = create_buttons_from_config(BUTTONS_CONFIG, CALLBACKS, screen.get_size(), logo_anchor, screen_filter="settings", click_sound=confirm_sound)
                    for sb in settings_buttons:
                        cid = getattr(sb, "_cfg_id", None)
                        if cid == "settings_back":
                            ui["back_btn"] = sb
                        elif cid == "settings_light":
                            ui["light_btn"] = sb
                        elif cid == "settings_dark":
                            ui["dark_btn"] = sb
                        elif cid == "settings_fullscreen":
                            ui["fullscreen_btn"] = sb
                    APP_STATE["ui"] = ui

                # 根据主题绘制设置界面背景
                theme = APP_STATE["settings"].get("theme", "light")
                if theme == "dark":
                    bg_color = (28, 30, 35)
                    panel_bg = (40, 44, 52)
                    panel_border = (80, 90, 110)
                    title_color = (200, 220, 255)
                    label_color = (210, 210, 210)
                    value_color = (220, 220, 220)
                else:
                    bg_color = (240, 242, 250)
                    panel_bg = (255, 255, 255)
                    panel_border = (180, 200, 220)
                    title_color = (50, 80, 150)
                    label_color = (60, 60, 60)
                    value_color = (80, 80, 80)
                screen.fill(bg_color)

                # 绘制设置面板（白色背景，有边框）
                panel_rect = pygame.Rect(20, 20, screen.get_width() - 40, screen.get_height() - 40)
                pygame.draw.rect(screen, panel_bg, panel_rect)
                pygame.draw.rect(screen, panel_border, panel_rect, 3)

                # 将返回按钮放置在面板的右上角，避免遮挡面板内部内容
                if ui.get("back_btn"):
                    try:
                        bb = ui["back_btn"]
                        margin = 20
                        new_x = panel_rect.right - bb.rect.width - margin
                        new_y = panel_rect.y + margin
                        bb.set_position(new_x, new_y)
                    except Exception:
                        pass

                try:
                    font_title = pygame.font.SysFont("Microsoft YaHei", 40)
                    font_label = pygame.font.SysFont("Microsoft YaHei", 24)
                    font_value = pygame.font.SysFont("Microsoft YaHei", 20)
                except Exception:
                    font_title = pygame.font.SysFont(None, 40)
                    font_label = pygame.font.SysFont(None, 24)
                    font_value = pygame.font.SysFont(None, 20)

                # 标题
                title = font_title.render("游戏设置", True, title_color)
                screen.blit(title, (50, 30))

                # 分隔线
                pygame.draw.line(screen, (200, 200, 200), (50, 90), (screen.get_width() - 50, 90), 2)

                # 玩家名字标签与输入框
                pn_rect = ui["player_name_input"].rect
                label = font_label.render("玩家名字:", True, label_color)
                label_x = max(panel_rect.x + 20, pn_rect.x - label.get_width() - 16)
                label_y = pn_rect.y + (pn_rect.height - label.get_height()) // 2
                screen.blit(label, (label_x, label_y))
                ui["player_name_input"].draw(screen)
                if ui.get("confirm_name_btn"):
                    ui["confirm_name_btn"].draw(screen)

                # 难度设置已从界面移除

                # 音量标签与滑块
                slider_rect = ui["volume_slider_rect"]
                label = font_label.render("音量:", True, label_color)
                label_x = max(panel_rect.x + 20, slider_rect.x - label.get_width() - 16)
                label_y = slider_rect.y + (slider_rect.height - label.get_height()) // 2
                screen.blit(label, (label_x, label_y))

                # 音量滑块背景
                pygame.draw.rect(screen, (220, 220, 220), slider_rect)
                pygame.draw.rect(screen, (150, 170, 220), slider_rect, 2)

                # 音量进度条
                vol = APP_STATE["settings"]["volume"]
                progress_rect = pygame.Rect(slider_rect.x, slider_rect.y, slider_rect.width * vol / 100, slider_rect.height)
                pygame.draw.rect(screen, (100, 150, 255), progress_rect)

                # 音量滑块游标
                slider_x = slider_rect.x + (vol / 100.0) * slider_rect.width
                pygame.draw.circle(screen, (50, 100, 200), (int(slider_x), int(slider_rect.centery)), 10)
                pygame.draw.circle(screen, (100, 150, 255), (int(slider_x), int(slider_rect.centery)), 8)

                # 音量百分比显示
                vol_label = font_value.render(f"音量: {vol}%", True, value_color)
                screen.blit(vol_label, (slider_rect.right + 16, slider_rect.y - 2))

                # 服务器地址标签与输入框
                if ui.get("server_host_input"):
                    sh_rect = ui["server_host_input"].rect
                    label = font_label.render("服务器地址:", True, label_color)
                    label_x = max(panel_rect.x + 20, sh_rect.x - label.get_width() - 16)
                    label_y = sh_rect.y + (sh_rect.height - label.get_height()) // 2
                    screen.blit(label, (label_x, label_y))
                    ui["server_host_input"].draw(screen)
                    if ui.get("confirm_host_btn"):
                        ui["confirm_host_btn"].draw(screen)
                    if ui.get("detect_ip_btn"):
                        ui["detect_ip_btn"].draw(screen)
                    if ui.get("server_lan_btn"):
                        ui["server_lan_btn"].draw(screen)
                    if ui.get("server_remote_btn"):
                        ui["server_remote_btn"].draw(screen)

                # 主题切换标签与按钮
                theme_y = None
                if ui.get("light_btn"):
                    theme_y = ui["light_btn"].rect.y
                elif ui.get("dark_btn"):
                    theme_y = ui["dark_btn"].rect.y
                theme_label = font_label.render("主题:", True, label_color)
                if theme_y is None:
                    screen.blit(theme_label, (panel_rect.x + 20, panel_rect.y + 220))
                else:
                    screen.blit(theme_label, (panel_rect.x + 20, theme_y + 6))
                if ui.get("light_btn"):
                    ui["light_btn"].draw(screen)
                if ui.get("dark_btn"):
                    ui["dark_btn"].draw(screen)
                # 全屏切换按钮
                if ui.get("fullscreen_btn"):
                    # 动态刷新文案，避免显示状态不一致
                    try:
                        is_fs = bool(APP_STATE["settings"].get("fullscreen", False))
                        ui["fullscreen_btn"].update_text(f"全屏: {'是' if is_fs else '否'}")
                    except Exception:
                        pass
                    ui["fullscreen_btn"].draw(screen)

                # 快捷键说明已从设置界面移除

                # 返回按钮
                if ui.get("back_btn"):
                    ui["back_btn"].draw(screen)

            # 绘制通知
            now_ms = pygame.time.get_ticks()
            APP_STATE["notifications"] = [n for n in APP_STATE["notifications"] if n["end_time"] > now_ms]
            for i, n in enumerate(APP_STATE["notifications"]):
                try:
                    n_font = pygame.font.SysFont("Microsoft YaHei", 24, bold=True)
                except Exception:
                    n_font = pygame.font.SysFont(None, 24)

                txt_surf = n_font.render(n["text"], True, n["color"])
                # 居中显示在屏幕顶部
                tx = (screen.get_width() - txt_surf.get_width()) // 2
                ty = 50 + i * 50
                # 绘制背景框
                bg_rect = pygame.Rect(tx - 15, ty - 10, txt_surf.get_width() + 30, txt_surf.get_height() + 20)
                pygame.draw.rect(screen, (255, 255, 255), bg_rect, border_radius=8)
                pygame.draw.rect(screen, n["color"], bg_rect, 2, border_radius=8)
                screen.blit(txt_surf, (tx, ty))

            pygame.display.flip()
            clock.tick(60)

    except Exception as exc:  # pragma: no cover - main runtime errors
        logger.error("客户端错误: %s", exc, exc_info=True)
    finally:
        pygame.quit()
        logger.info("客户端已关闭")


if __name__ == "__main__":
    main()
