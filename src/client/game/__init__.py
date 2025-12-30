"""
客户端游戏逻辑模块

负责客户端本地的游戏状态管理与网络交互封装：
- 维护房间公开/私密视图（不泄露谜底）
- 与服务器进行行分隔 JSON 消息通信
- 提供绘图/聊天/猜词等动作接口

该模块尽量无 UI 依赖，便于被界面层调用。
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Any, Callable, Dict, Optional

from src.shared.constants import (
	DEFAULT_HOST,
	DEFAULT_PORT,
	BUFFER_SIZE,
	MSG_CONNECT,
	MSG_JOIN_ROOM,
	MSG_LEAVE_ROOM,
	MSG_START_GAME,
	MSG_END_GAME,
	MSG_NEXT_ROUND,
	MSG_GUESS,
	MSG_DRAW,
	MSG_CHAT,
)
from src.shared.protocols import Message


class ClientNetwork:
	"""客户端网络接口（行分隔 JSON）"""

	def __init__(self):
		self._sock: Optional[socket.socket] = None
		self._recv_thread: Optional[threading.Thread] = None
		self._running = threading.Event()
		self._buffer = bytearray()
		self._lock = threading.RLock()
		# // 事件回调注册表：event_type -> callback(msg: Message)
		self._handlers: Dict[str, Callable[[Message], None]] = {}

	# 连接/关闭
	def connect(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 5.0) -> bool:
		"""连接到服务器并启动接收线程"""
		with self._lock:
			if self._sock:
				return True
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.settimeout(timeout)
			s.connect((host, port))
			s.settimeout(None)
			self._sock = s
			self._running.set()
			self._recv_thread = threading.Thread(target=self._recv_loop, name="client-recv", daemon=True)
			self._recv_thread.start()
			return True

	def close(self) -> None:
		"""关闭连接并停止接收线程"""
		with self._lock:
			self._running.clear()
			try:
				if self._sock:
					try:
						self._sock.shutdown(socket.SHUT_RDWR)
					except Exception:
						pass
					self._sock.close()
			finally:
				self._sock = None

	# 发送/接收
	def send(self, msg: Message) -> None:
		"""发送一条消息（自动添加换行）"""
		with self._lock:
			if not self._sock:
				raise RuntimeError("not connected")
			data = (msg.to_json() + "\n").encode("utf-8")
			self._sock.sendall(data)

	def _recv_loop(self) -> None:
		"""接收线程：按行分割并回调处理"""
		assert self._sock is not None
		sock = self._sock
		while self._running.is_set():
			try:
				chunk = sock.recv(BUFFER_SIZE)
				if not chunk:
					break
				self._buffer.extend(chunk)
				# // 行分割
				while True:
					try:
						idx = self._buffer.index(ord("\n"))
					except ValueError:
						break
					raw = self._buffer[:idx]
					del self._buffer[: idx + 1]
					self._handle_raw(raw)
			except Exception:
				break
		# // 清理
		self.close()

	def _handle_raw(self, raw: bytes) -> None:
		try:
			text = raw.decode("utf-8", errors="replace")
			msg = Message.from_json(text)
		except Exception:
			return
		# // 分发到对应处理器
		cb = self._handlers.get(msg.type)
		if cb:
			try:
				cb(msg)
			except Exception:
				pass

	# 回调注册
	def on(self, event_type: str, handler: Callable[[Message], None]) -> None:
		self._handlers[event_type] = handler


class ClientGame:
	"""客户端游戏状态管理与动作封装"""

	def __init__(self, network: Optional[ClientNetwork] = None):
		self.net = network or ClientNetwork()
		self.player_id: Optional[str] = None
		self.player_name: Optional[str] = None
		# // 公开房间状态（由服务器广播）
		self.room_public: Dict[str, Any] = {}
		# // 私密视图（本地根据 drawer 身份请求或缓存）
		self.round_private: Dict[str, Any] = {}
		self._lock = threading.RLock()
		# // 事件钩子供 UI 层订阅：类型 -> 回调
		self._ui_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}

		# // 绑定网络事件
		self._bind_network_handlers()

	def _bind_network_handlers(self) -> None:
		# // 房间状态广播
		self.net.on("room_state", lambda m: self._update_room(m.data))
		# // 聊天与绘图同步
		self.net.on("chat", lambda m: self._emit_ui("chat", m.data))
		self.net.on("draw_sync", lambda m: self._emit_ui("draw_sync", m.data))
		# // 通用事件与结果
		self.net.on("event", lambda m: self._emit_ui("event", m.data))
		self.net.on("guess_result", lambda m: self._emit_ui("guess_result", m.data))
		self.net.on("error", lambda m: self._emit_ui("error", m.data))
		# // 心跳
		self.net.on("ping", lambda m: self.net.send(Message("pong", {"ts": m.data.get("ts")})))

	# 事件派发到 UI 层
	def on_ui(self, event: str, handler: Callable[[Dict[str, Any]], None]) -> None:
		self._ui_handlers[event] = handler

	def _emit_ui(self, event: str, payload: Dict[str, Any]) -> None:
		cb = self._ui_handlers.get(event)
		if cb:
			try:
				cb(payload)
			except Exception:
				pass

	def _update_room(self, data: Dict[str, Any]) -> None:
		with self._lock:
			self.room_public = data
		self._emit_ui("room_state", data)

	# 连接/登录/房间
	def connect(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
		ok = self.net.connect(host, port)
		return ok

	def login(self, player_id: str, name: str) -> None:
		# // 记录本地身份并发送注册
		with self._lock:
			self.player_id = player_id
			self.player_name = name
		self.net.send(Message(MSG_CONNECT, {"player_id": player_id, "name": name}))

	def join_room(self, room_id: str = "default") -> None:
		self.net.send(Message(MSG_JOIN_ROOM, {"room_id": room_id}))

	def leave_room(self) -> None:
		self.net.send(Message(MSG_LEAVE_ROOM, {}))

	# 游戏控制
	def start_game(self) -> None:
		self.net.send(Message(MSG_START_GAME, {}))

	def end_game(self) -> None:
		self.net.send(Message(MSG_END_GAME, {}))

	def next_round(self) -> None:
		self.net.send(Message(MSG_NEXT_ROUND, {}))

	# 行为动作
	def submit_guess(self, text: str) -> None:
		self.net.send(Message(MSG_GUESS, {"text": text}))

	def send_chat(self, text: str) -> None:
		self.net.send(Message(MSG_CHAT, {"text": text}))

	def send_draw(self, payload: Dict[str, Any]) -> None:
		# // payload 可包含 kind/color/size/point 等，由 UI 层构建
		self.net.send(Message(MSG_DRAW, payload))


__all__ = [
	"ClientNetwork",
	"ClientGame",
]

