"""
网络通信模块

处理 Socket 连接、消息收发、协议解析等网络功能。
"""

from __future__ import annotations

import logging
import socket
import threading
import json
import traceback
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

from src.shared.constants import (
	DEFAULT_HOST,
	DEFAULT_PORT,
	BUFFER_SIZE,
	MSG_CONNECT,
	MSG_DISCONNECT,
	MSG_JOIN_ROOM,
	MSG_CREATE_ROOM,
	MSG_LIST_ROOMS,
	MSG_LEAVE_ROOM,
	MSG_KICK_PLAYER,
	MSG_ROOM_UPDATE,
	MSG_DRAW,
	MSG_GUESS,
	MSG_CHAT,
	MSG_START_GAME,
	MSG_END_GAME,
	MSG_NEXT_ROUND,
	MSG_SET_GAME_CONFIG,
	MSG_ERROR,
)
from src.shared.protocols import Message
from src.server.game import GameRoom


class ClientSession:
	"""客户端会话，封装连接与玩家信息"""

	def __init__(self, conn: socket.socket, addr: Tuple[str, int]):
		self.conn = conn
		self.addr = addr
		self.player_id: Optional[str] = None
		self.player_name: Optional[str] = None
		self.room_id: Optional[str] = None
		self._recv_buffer = bytearray()

	def fileno(self) -> int:
		return self.conn.fileno()

	def close(self) -> None:
		try:
			self.conn.close()
		except Exception:
			pass


class NetworkServer:
	"""网络服务器，负责会话管理与消息路由"""

	def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
		self.host = host
		self.port = port
		self._sock: Optional[socket.socket] = None
		self._accept_thread: Optional[threading.Thread] = None
		self._running = threading.Event()
		self.sessions: Dict[int, ClientSession] = {}
		self.rooms: Dict[str, GameRoom] = {}

	def _rooms_snapshot(self) -> list:
		"""构建当前房间的简要列表快照。"""
		rooms = []
		for rid, r in self.rooms.items():
			rooms.append({
				"room_id": rid,
				"player_count": len(r.players),
				"status": r.status
			})
		return rooms

	def broadcast_rooms_update(self) -> None:
		"""向所有连接广播房间列表更新。"""
		payload = {"rooms": self._rooms_snapshot()}
		for s in list(self.sessions.values()):
			self._send(s, Message("rooms_update", payload))

	# 服务器生命周期
	def start(self) -> None:
		"""启动服务器并进入 Accept 循环"""
		self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		# // 允许快速重启服务
		self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._sock.bind((self.host, self.port))
		self._sock.listen(32)
		self._running.set()
		self._accept_thread = threading.Thread(target=self._accept_loop, name="accept-loop", daemon=True)
		self._accept_thread.start()

	def stop(self) -> None:
		"""停止服务器并关闭所有会话"""
		self._running.clear()
		try:
			if self._sock:
				# // 触发 accept 退出
				try:
					self._sock.shutdown(socket.SHUT_RDWR)
				except Exception:
					pass
				self._sock.close()
		finally:
			self._sock = None
		# // 关闭所有客户端连接
		for sess in list(self.sessions.values()):
			sess.close()
		self.sessions.clear()

	# 接入与会话线程
	def _accept_loop(self) -> None:
		"""Accept 新连接并为其创建会话线程"""
		while self._running.is_set():
			try:
				conn, addr = self._sock.accept()  # type: ignore[arg-type]
			except OSError:
				# // 套接字已关闭或出错，退出循环
				break
			sess = ClientSession(conn, addr)
			self.sessions[conn.fileno()] = sess
			t = threading.Thread(target=self._session_loop, args=(sess,), daemon=True)
			t.start()

	def _session_loop(self, sess: ClientSession) -> None:
		"""单会话收发循环：按行（\n）读取 JSON 消息并路由"""
		conn = sess.conn
		try:
			while self._running.is_set():
				data = conn.recv(BUFFER_SIZE)
				if not data:
					break
				sess._recv_buffer.extend(data)
				# // 简单分包：按换行符划分消息
				while True:
					try:
						idx = sess._recv_buffer.index(ord("\n"))
					except ValueError:
						break
					raw = sess._recv_buffer[:idx]
					del sess._recv_buffer[: idx + 1]
					self._handle_raw_message(sess, raw)
		except ConnectionResetError:
			pass
		except Exception:
			traceback.print_exc()
		finally:
			self._on_disconnect(sess)

	# 消息处理
	def _handle_raw_message(self, sess: ClientSession, raw: bytes) -> None:
		"""原始字节消息 -> JSON -> Message 并路由"""
		try:
			text = raw.decode("utf-8", errors="replace")
			msg = Message.from_json(text)
		except Exception:
			# // 非法消息，忽略
			return
		self._route_message(sess, msg)

	def _route_message(self, sess: ClientSession, msg: Message) -> None:
		"""根据消息类型路由到对应处理函数"""
		t = msg.type
		data = msg.data
		logger.info(f"收到消息: type={t}, from={sess.player_name or sess.addr}")

		if t == MSG_CONNECT:
			# // 注册玩家，要求 data: {player_id, name}
			sess.player_id = str(data.get("player_id") or sess.addr[0])
			sess.player_name = str(data.get("name") or f"Player-{sess.addr[1]}")
			self._send(sess, Message("ack", {"ok": True, "event": MSG_CONNECT}))

		elif t == MSG_CREATE_ROOM:
			# 创建房间
			room_id = str(len(self.rooms) + 1)
			new_room = GameRoom(room_id)
			self.rooms[room_id] = new_room
			
			# 自动加入
			if sess.player_id and sess.player_name:
				new_room.add_player(sess.player_id, sess.player_name)
				sess.room_id = room_id
				
				self._send(sess, Message("ack", {"ok": True, "event": MSG_CREATE_ROOM, "room_id": room_id}))
			self.broadcast_room_state(room_id)
			# 广播房间列表更新，便于其他客户端立刻看到新房间
			self.broadcast_rooms_update()
		elif t == MSG_LIST_ROOMS:
			# 获取房间列表
			room_list = []
			for rid, r in self.rooms.items():
				room_list.append({
					"room_id": rid,
					"player_count": len(r.players),
					"status": r.status
				})
			self._send(sess, Message("ack", {"ok": True, "event": MSG_LIST_ROOMS, "rooms": room_list}))

		elif t == MSG_JOIN_ROOM:
			# 加入房间
			target_room_id = str(data.get("room_id"))
			if target_room_id in self.rooms:
				room = self.rooms[target_room_id]
				if sess.player_id and sess.player_name:
					if room.add_player(sess.player_id, sess.player_name):
						sess.room_id = target_room_id
						# 容错：若房主缺失，指定为已有的第一个玩家
						if room.owner_id is None:
							try:
								room.owner_id = next(iter(room.players))
							except Exception:
								room.owner_id = sess.player_id
						self._send(sess, Message("ack", {"ok": True, "event": MSG_JOIN_ROOM, "room_id": target_room_id}))
						self.broadcast_room_state(target_room_id)
						# 广播房间列表更新（人数变化）
						self.broadcast_rooms_update()
					else:
						self._send(sess, Message("error", {"msg": "Could not join room"}))
			else:
				self._send(sess, Message("error", {"msg": "Room not found"}))
		elif t == MSG_SET_GAME_CONFIG:
			# 房主更新游戏参数
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				# 若尚未设定房主，则将当前请求者设为房主（容错）
				if room.owner_id is None and sess.player_id:
					room.owner_id = sess.player_id
				if room.owner_id == sess.player_id:
					try:
						max_rounds = data.get("max_rounds")
						round_time = data.get("round_time")
						rest_time = data.get("rest_time")
						if isinstance(max_rounds, int) and max_rounds > 0:
							room.max_rounds = max_rounds
						if isinstance(round_time, int) and round_time > 0:
							# 模块化服务器使用 round_duration
							room.round_duration = round_time
						# rest_time 暂未在此实现，忽略或未来支持
						self._send(sess, Message("ack", {"ok": True, "event": MSG_SET_GAME_CONFIG}))
						self.broadcast_room_state(sess.room_id)
					except Exception:
						self._send(sess, Message("error", {"msg": "Invalid config"}))
				else:
					self._send(sess, Message("error", {"msg": "Permission denied"}))

		elif t == MSG_LEAVE_ROOM:
			# 离开房间
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				if sess.player_id:
					room.remove_player(sess.player_id)
				self.broadcast_room_state(sess.room_id)
				# 广播房间列表更新（人数变化或房间清理）
				self.broadcast_rooms_update()
				if not room.players:
					del self.rooms[sess.room_id]
			
			sess.room_id = None
			self._send(sess, Message("ack", {"ok": True, "event": MSG_LEAVE_ROOM}))

		elif t == MSG_KICK_PLAYER:
			# 踢出玩家
			target_player_id = str(data.get("player_id"))
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				# 检查权限
				if room.owner_id == sess.player_id:
					if target_player_id in room.players:
						room.remove_player(target_player_id)
					self.broadcast_room_state(sess.room_id)
					self.broadcast_rooms_update()
					for s in self.sessions.values():
						if s.player_id == target_player_id:
							s.room_id = None
							self._send(s, Message("event", {"type": MSG_KICK_PLAYER, "room_id": room.room_id}))
							break
				else:
					self._send(sess, Message("error", {"msg": "Permission denied"}))

		elif t == MSG_START_GAME:
			# 启动游戏 - 生成随机绘画顺序
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				# 若尚未设定房主，则将当前请求者设为房主（容错）
				if room.owner_id is None and sess.player_id:
					room.owner_id = sess.player_id
				if room.owner_id == sess.player_id:
					# 调用 start_game 生成随机顺序并进入第一轮
					ok = room.start_game()
					if ok:
						# 广播游戏开始和房间状态更新（词语隐藏）
						self.broadcast_room_state(sess.room_id)
						# 发送特定的游戏开始事件，包含绘画顺序信息
						self.broadcast_room(sess.room_id, Message("event", {
							"type": MSG_START_GAME,
							"ok": True,
							"drawer_order": room.drawer_order,
							"drawer_id": room.drawer_id,
							"round_number": room.round_number
						}))
					else:
						self._send(sess, Message("error", {"msg": "Cannot start game with no players"}))
				else:
					self._send(sess, Message("error", {"msg": "Permission denied"}))
			else:
				self._send(sess, Message("error", {"msg": "Room not found"}))

		elif t == MSG_NEXT_ROUND:
			# 进入下一回合
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				ok = room.next_round()
				if ok:
					# 广播房间状态更新（词语隐藏）
					self.broadcast_room_state(sess.room_id)
					# 发送轮次开始事件
					self.broadcast_room(sess.room_id, Message("event", {
						"type": MSG_NEXT_ROUND,
						"ok": True,
						"drawer_id": room.drawer_id,
						"round_number": room.round_number
					}))
				else:
					# 游戏结束
					self.broadcast_room(sess.room_id, Message("event", {"type": MSG_END_GAME, "ok": True}))
					self.broadcast_room_state(sess.room_id)
		elif t == MSG_END_GAME:
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				# room.end_game()
				room.status = "ended"
				self.broadcast_room_state(sess.room_id)
				self.broadcast_room(sess.room_id, Message("event", {"type": MSG_END_GAME, "ok": True}))

		elif t == MSG_GUESS:
			# 猜词
			guess_text = str(data.get("text") or "")
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				if sess.player_id:
					# ok, score = room.submit_guess(sess.player_id, guess_text)
					# 简化
					ok, score = False, 0
					self._send(sess, Message("guess_result", {"ok": ok, "score": score}))
				self.broadcast_room_state(sess.room_id)
		elif t == MSG_CHAT:
			# 聊天
			if sess.room_id:
				payload = {
					"by": sess.player_id,
					"by_name": sess.player_name,
					"text": str(data.get("text") or ""),
				}
				self.broadcast_room(sess.room_id, Message("chat", payload))

		elif t == MSG_DISCONNECT:
			self._on_disconnect(sess)
		else:
			self._send(sess, Message("error", {"msg": f"unknown type: {t}"}))

	# 发送/广播
	def _send(self, sess: ClientSession, msg: Message) -> None:
		try:
			text = msg.to_json() + "\n"
			sess.conn.sendall(text.encode("utf-8"))
		except Exception:
			self._on_disconnect(sess)

	def broadcast_room(self, room_id: str, msg: Message, exclude: Optional[ClientSession] = None) -> None:
		"""向特定房间广播消息"""
		for s in list(self.sessions.values()):
			if s.room_id == room_id:
				if exclude and s is exclude:
					continue
				self._send(s, msg)

	def broadcast_room_state(self, room_id: str) -> None:
		"""向房间广播房间状态，但对非绘者隐藏当前词语"""
		if room_id not in self.rooms:
			return
		room = self.rooms[room_id]
		
		for s in list(self.sessions.values()):
			if s.room_id == room_id:
				# 如果该玩家是绘者，发送包含词语的状态；否则隐藏词语
				is_drawer = (s.player_id == room.drawer_id)
				state = room.get_public_state(for_drawer=is_drawer)
				self._send(s, Message(MSG_ROOM_UPDATE, state))

	def broadcast(self, msg: Message, exclude: Optional[ClientSession] = None) -> None:
		"""向所有连接广播 (慎用)"""
		for s in list(self.sessions.values()):
			if exclude and s is exclude:
				continue
			self._send(s, msg)

	# 断开清理
	def _on_disconnect(self, sess: ClientSession) -> None:
		try:
			if sess.room_id and sess.room_id in self.rooms:
				room = self.rooms[sess.room_id]
				if sess.player_id:
					room.remove_player(sess.player_id)
					self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
					if not room.players:
						del self.rooms[sess.room_id]
			sess.close()
		finally:
			self.sessions.pop(sess.fileno(), None)


__all__ = [
	"ClientSession",
	"NetworkServer",
]

