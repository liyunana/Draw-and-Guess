"""
Draw & Guess 游戏服务器 - 独立部署版本
"""

import json
import logging
import os
import socket
import threading
import time
from typing import Any, Dict, Optional, Tuple

# ============== 配置 ==============
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5555
BUFFER_SIZE = 4096

# 消息类型
MSG_CONNECT = "connect"
MSG_DISCONNECT = "disconnect"
MSG_JOIN_ROOM = "join_room"
MSG_CREATE_ROOM = "create_room"
MSG_LIST_ROOMS = "list_rooms"
MSG_LEAVE_ROOM = "leave_room"
MSG_KICK_PLAYER = "kick_player"
MSG_ROOM_UPDATE = "room_update"
MSG_DRAW = "draw"
MSG_GUESS = "guess"
MSG_CHAT = "chat"
MSG_START_GAME = "start_game"
MSG_END_GAME = "end_game"
MSG_NEXT_ROUND = "next_round"
MSG_SET_GAME_CONFIG = "set_game_config"
MSG_GIVE_SCORE = "give_score"
MSG_ROUND_END = "round_end"
MSG_GAME_RESULT = "game_result"
MSG_ERROR = "error"

# ============== 日志配置 ==============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("server.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ============== 消息类 ==============
class Message:
    def __init__(self, msg_type: str, data: Dict[str, Any] = None):
        self.type = msg_type
        self.data = data or {}

    def to_json(self) -> str:
        return json.dumps({"type": self.type, "data": self.data})

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        obj = json.loads(json_str)
        return cls(obj["type"], obj.get("data", {}))


# ============== 游戏房间 ==============
class GameRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: Dict[str, Dict[str, Any]] = {}
        self.owner_id: Optional[str] = None
        self.status = "waiting"
        self.drawer_id: Optional[str] = None
        self.current_word: Optional[str] = None
        self.round_number = 0
        self.max_rounds = 3  # 总轮数
        self.round_time = 60  # 每轮时间（秒）
        self.rest_time = 10  # 休息时间（秒）
        self.round_start_time: Optional[float] = None
        self.words_list = []  # 词库
        self.used_words = set()  # 已使用的词
        self._load_words()

    def add_player(self, player_id: str, player_name: str) -> bool:
        if player_id in self.players:
            return True
        self.players[player_id] = {
            "name": player_name,
            "score": 0,
            "is_drawer": False
        }
        if self.owner_id is None:
            self.owner_id = player_id
        return True

    def remove_player(self, player_id: str):
        if player_id in self.players:
            del self.players[player_id]
            if self.owner_id == player_id:
                self.owner_id = next(iter(self.players), None)
            if self.drawer_id == player_id:
                self.drawer_id = None

    def _load_words(self):
        """加载词库"""
        try:
            words_file = os.path.join(os.path.dirname(__file__), "words.txt")
            if not os.path.exists(words_file):
                # 尝试从项目根目录加载
                words_file = os.path.join(os.path.dirname(__file__), "..", "data", "words.txt")
            if os.path.exists(words_file):
                with open(words_file, "r", encoding="utf-8") as f:
                    self.words_list = [w.strip() for w in f if w.strip()]
            else:
                # 默认词库
                self.words_list = ["苹果", "香蕉", "汽车", "飞机", "房子", "太阳", "月亮", "星星", "猫", "狗"]
        except Exception:
            self.words_list = ["苹果", "香蕉", "汽车", "飞机", "房子"]

    def set_game_config(self, max_rounds: int = None, round_time: int = None, rest_time: int = None):
        """设置游戏参数"""
        if max_rounds is not None and max_rounds > 0:
            self.max_rounds = max_rounds
        if round_time is not None and round_time > 0:
            self.round_time = round_time
        if rest_time is not None and rest_time > 0:
            self.rest_time = rest_time

    def get_next_word(self) -> str:
        """获取下一个词语"""
        import random
        available = [w for w in self.words_list if w not in self.used_words]
        if not available:
            self.used_words.clear()  # 重置已使用词库
            available = self.words_list
        if available:
            word = random.choice(available)
            self.used_words.add(word)
            return word
        return "画画"

    def get_public_state(self) -> dict:
        return {
            "room_id": self.room_id,
            "owner_id": self.owner_id,
            "status": self.status,
            "players": self.players,
            "drawer_id": self.drawer_id,
            "round_number": self.round_number,
            "max_rounds": self.max_rounds,
            "round_time": self.round_time,
            "rest_time": self.rest_time,
            "current_word": self.current_word,
        }


# ============== 客户端会话 ==============
class ClientSession:
    def __init__(self, sock: socket.socket, addr: Tuple[str, int]):
        self.sock = sock
        self.addr = addr
        self.player_id: Optional[str] = None
        self.player_name: Optional[str] = None
        self.room_id: Optional[str] = None


# ============== 网络服务器 ==============
class NetworkServer:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._running = threading.Event()
        self.sessions: Dict[Tuple[str, int], ClientSession] = {}
        self.rooms: Dict[str, GameRoom] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(32)
        self._running.set()
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def stop(self) -> None:
        self._running.clear()
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def _accept_loop(self) -> None:
        while self._running.is_set():
            try:
                client_sock, addr = self.sock.accept()
                sess = ClientSession(client_sock, addr)
                with self._lock:
                    self.sessions[addr] = sess
                threading.Thread(target=self._session_loop, args=(sess,), daemon=True).start()
                logger.info(f"客户端连接: {addr}")
            except Exception:
                if self._running.is_set():
                    pass

    def _session_loop(self, sess: ClientSession) -> None:
        buf = bytearray()
        try:
            while self._running.is_set():
                data = sess.sock.recv(BUFFER_SIZE)
                if not data:
                    break
                buf.extend(data)
                while b"\n" in buf:
                    idx = buf.index(b"\n")
                    raw = bytes(buf[:idx])
                    buf = buf[idx + 1:]
                    self._handle_raw_message(sess, raw)
        except Exception:
            pass
        finally:
            self._cleanup_session(sess)

    def _cleanup_session(self, sess: ClientSession) -> None:
        with self._lock:
            if sess.addr in self.sessions:
                del self.sessions[sess.addr]
            if sess.room_id and sess.room_id in self.rooms:
                room = self.rooms[sess.room_id]
                if sess.player_id:
                    room.remove_player(sess.player_id)
                    self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                    if not room.players:
                        del self.rooms[sess.room_id]
        try:
            sess.sock.close()
        except Exception:
            pass
        logger.info(f"客户端断开: {sess.addr}")

    def _handle_raw_message(self, sess: ClientSession, raw: bytes) -> None:
        try:
            text = raw.decode("utf-8", errors="ignore")
            msg = Message.from_json(text)
        except Exception:
            return
        self._route_message(sess, msg)

    def _route_message(self, sess: ClientSession, msg: Message) -> None:
        t = msg.type
        data = msg.data
        logger.info(f"收到消息: type={t}, from={sess.player_name or sess.addr}")

        if t == MSG_CONNECT:
            sess.player_id = str(data.get("player_id") or sess.addr[0])
            sess.player_name = str(data.get("name") or f"Player-{sess.addr[1]}")
            self._send(sess, Message("ack", {"ok": True, "event": MSG_CONNECT}))

        elif t == MSG_CREATE_ROOM:
            room_id = str(len(self.rooms) + 1)
            new_room = GameRoom(room_id)
            self.rooms[room_id] = new_room
            if sess.player_id and sess.player_name:
                new_room.add_player(sess.player_id, sess.player_name)
                sess.room_id = room_id
                self._send(sess, Message("ack", {"ok": True, "event": MSG_CREATE_ROOM, "room_id": room_id}))
                self.broadcast_room(room_id, Message(MSG_ROOM_UPDATE, new_room.get_public_state()))

        elif t == MSG_LIST_ROOMS:
            room_list = []
            for rid, r in self.rooms.items():
                room_list.append({
                    "room_id": rid,
                    "player_count": len(r.players),
                    "status": r.status
                })
            self._send(sess, Message("ack", {"ok": True, "event": MSG_LIST_ROOMS, "rooms": room_list}))

        elif t == MSG_JOIN_ROOM:
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
                        self.broadcast_room(target_room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                    else:
                        self._send(sess, Message("error", {"msg": "Could not join room"}))
            else:
                self._send(sess, Message("error", {"msg": "Room not found"}))

        elif t == MSG_LEAVE_ROOM:
            if sess.room_id and sess.room_id in self.rooms:
                room = self.rooms[sess.room_id]
                if sess.player_id:
                    room.remove_player(sess.player_id)
                    self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                    if not room.players:
                        del self.rooms[sess.room_id]
            sess.room_id = None
            self._send(sess, Message("ack", {"ok": True, "event": MSG_LEAVE_ROOM}))

        elif t == MSG_KICK_PLAYER:
            target_player_id = str(data.get("player_id"))
            if sess.room_id and sess.room_id in self.rooms:
                room = self.rooms[sess.room_id]
                if room.owner_id == sess.player_id:
                    if target_player_id in room.players:
                        room.remove_player(target_player_id)
                        self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                        for s in self.sessions.values():
                            if s.player_id == target_player_id:
                                s.room_id = None
                                self._send(s, Message("event", {"type": MSG_KICK_PLAYER, "room_id": room.room_id}))
                                break
                else:
                    self._send(sess, Message("error", {"msg": "Permission denied"}))

        elif t == MSG_SET_GAME_CONFIG:
            if sess.room_id and sess.room_id in self.rooms:
                room = self.rooms[sess.room_id]
                # 若尚未设定房主，则将当前请求者设为房主（容错）
                if room.owner_id is None and sess.player_id:
                    room.owner_id = sess.player_id
                if room.owner_id == sess.player_id:
                    max_rounds = data.get("max_rounds")
                    round_time = data.get("round_time")
                    rest_time = data.get("rest_time")
                    room.set_game_config(max_rounds, round_time, rest_time)
                    self._send(sess, Message("ack", {"ok": True, "event": MSG_SET_GAME_CONFIG}))
                    self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                else:
                    self._send(sess, Message("error", {"msg": "Permission denied"}))

        elif t == MSG_START_GAME:
            if sess.room_id and sess.room_id in self.rooms:
                room = self.rooms[sess.room_id]
                # 若尚未设定房主，则将当前请求者设为房主（容错）
                if room.owner_id is None and sess.player_id:
                    room.owner_id = sess.player_id
                if room.owner_id == sess.player_id:
                    room.status = "playing"
                    room.round_number = 1
                    # 选择第一个绘画者
                    import random
                    room.drawer_id = random.choice(list(room.players.keys()))
                    # 选择词语
                    room.current_word = room.get_next_word()
                    room.round_start_time = time.time()
                    # 重置所有玩家分数
                    for pid in room.players:
                        room.players[pid]["score"] = 0
                    self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                    # 全局播报：游戏开始，XXX是绘画者
                    drawer_name = room.players[room.drawer_id]["name"]
                    self.broadcast_room(sess.room_id, Message("event", {
                        "type": MSG_START_GAME, 
                        "ok": True,
                        "drawer_id": room.drawer_id,
                        "drawer_name": drawer_name,
                        "round": room.round_number,
                        "max_rounds": room.max_rounds
                    }))
                else:
                    self._send(sess, Message("error", {"msg": "Permission denied"}))

        elif t == MSG_GIVE_SCORE:
            # 绘画者给某玩家打分
            if sess.room_id and sess.room_id in self.rooms:
                room = self.rooms[sess.room_id]
                if room.drawer_id == sess.player_id:
                    target_player_id = str(data.get("player_id"))
                    score = int(data.get("score", 0))
                    if target_player_id in room.players:
                        room.players[target_player_id]["score"] += score
                        self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                        self.broadcast_room(sess.room_id, Message("event", {
                            "type": MSG_GIVE_SCORE,
                            "player_id": target_player_id,
                            "player_name": room.players[target_player_id]["name"],
                            "score": score
                        }))

        elif t == MSG_NEXT_ROUND:
            # 开始下一轮
            if sess.room_id and sess.room_id in self.rooms:
                room = self.rooms[sess.room_id]
                if room.owner_id == sess.player_id or room.drawer_id == sess.player_id:
                    room.round_number += 1
                    if room.round_number > room.max_rounds:
                        # 游戏结束
                        room.status = "finished"
                        # 计算排名
                        ranking = sorted(room.players.items(), key=lambda x: x[1]["score"], reverse=True)
                        result = [{"player_id": pid, "name": p["name"], "score": p["score"]} for pid, p in ranking]
                        self.broadcast_room(sess.room_id, Message(MSG_GAME_RESULT, {"ranking": result}))
                        room.status = "waiting"
                        room.round_number = 0
                        self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                    else:
                        # 继续下一轮
                        import random
                        # 轮换绘画者
                        player_ids = list(room.players.keys())
                        current_index = player_ids.index(room.drawer_id) if room.drawer_id in player_ids else -1
                        next_index = (current_index + 1) % len(player_ids)
                        room.drawer_id = player_ids[next_index]
                        room.current_word = room.get_next_word()
                        room.round_start_time = time.time()
                        
                        self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                        drawer_name = room.players[room.drawer_id]["name"]
                        self.broadcast_room(sess.room_id, Message("event", {
                            "type": MSG_NEXT_ROUND,
                            "drawer_id": room.drawer_id,
                            "drawer_name": drawer_name,
                            "round": room.round_number,
                            "max_rounds": room.max_rounds
                        }))

        elif t == MSG_DRAW:
            if sess.room_id:
                payload = {"by": sess.player_id, "data": data}
                self.broadcast_room(sess.room_id, Message("draw_sync", payload), exclude=sess)

        elif t == MSG_CHAT:
            if sess.room_id:
                room = self.rooms.get(sess.room_id)
                text = str(data.get("text") or "")
                
                # 如果在游戏中，检查是否猜对
                if room and room.status == "playing" and room.current_word:
                    # 不是绘画者才可以猜
                    if sess.player_id != room.drawer_id:
                        # 完全匹配：自动加分
                        if text.strip() == room.current_word:
                            room.players[sess.player_id]["score"] += 10
                            self.broadcast_room(sess.room_id, Message(MSG_ROOM_UPDATE, room.get_public_state()))
                            # 播报猜对消息
                            self.broadcast_room(sess.room_id, Message("event", {
                                "type": "guess_correct",
                                "player_id": sess.player_id,
                                "player_name": sess.player_name,
                                "word": room.current_word
                            }))
                            # 不发送猜对的消息到聊天框（避免泄露答案）
                            return
                
                # 正常聊天消息
                payload = {
                    "by": sess.player_id,
                    "by_name": sess.player_name,
                    "text": text,
                }
                self.broadcast_room(sess.room_id, Message("chat", payload))

    def _send(self, sess: ClientSession, msg: Message) -> None:
        try:
            payload = msg.to_json() + "\n"
            sess.sock.sendall(payload.encode("utf-8"))
        except Exception:
            pass

    def broadcast_room(self, room_id: str, msg: Message, exclude: Optional[ClientSession] = None) -> None:
        with self._lock:
            for sess in list(self.sessions.values()):
                if sess.room_id == room_id and sess != exclude:
                    self._send(sess, msg)


# ============== 主函数 ==============
def main():
    host = os.environ.get("HOST", DEFAULT_HOST)
    try:
        port = int(os.environ.get("PORT", DEFAULT_PORT))
    except Exception:
        port = DEFAULT_PORT

    logger.info("=" * 50)
    logger.info("Draw & Guess 游戏服务器启动中...")
    logger.info(f"监听地址: {host}:{port}")
    logger.info("=" * 50)

    server = NetworkServer(host, port)
    server.start()

    logger.info("服务器运行中，按 Ctrl+C 停止")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n服务器正在关闭...")
        server.stop()
    finally:
        logger.info("服务器已停止")


if __name__ == "__main__":
    main()
