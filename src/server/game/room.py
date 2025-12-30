import random
import time
from typing import Dict, List, Optional, Tuple


class GameRoom:
    """
    游戏房间类，管理玩家、游戏状态和回合逻辑。
    """

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: Dict[str, Dict[str, any]] = {}  # player_id -> {name, score, is_drawer}
        self.owner_id: Optional[str] = None
        # waiting: 未开始/大厅
        # playing: 正在绘画回合
        # resting: 回合间休息
        # ended: 游戏结束
        self.status = "waiting"  # waiting, playing, resting, ended
        self.current_word: Optional[str] = None
        self.drawer_id: Optional[str] = None
        self.round_number = 0
        self.max_rounds = 5
        self.round_start_time = 0
        self.round_duration = 60  # seconds
        self.rest_time = 10  # 轮与轮之间休息时间（秒）
        self.rest_start_time = 0
        # 设置：绘画者退出时是否立刻终止本轮进入休息
        self.end_round_on_drawer_leave = True
        self.drawer_order: List[str] = []  # 随机生成的绘画顺序（player_id列表）
        self.current_drawer_index = 0  # 当前绘者在顺序中的索引

    def add_player(self, player_id: str, player_name: str) -> bool:
        """添加玩家到房间"""
        if player_id in self.players:
            return True

        # 如果是第一个玩家，设为房主
        if not self.players:
            self.owner_id = player_id

        self.players[player_id] = {
            "name": player_name,
            "score": 0,
            "is_drawer": False
        }
        return True

    def remove_player(self, player_id: str):
        """从房间移除玩家"""
        if player_id in self.players:
            del self.players[player_id]

            # 如果房主离开，移交房主权限
            if self.owner_id == player_id:
                if self.players:
                    self.owner_id = next(iter(self.players))
                else:
                    self.owner_id = None

            # 如果绘图者离开了，可能需要结束当前回合或重新分配
            if self.drawer_id == player_id:
                self.drawer_id = None
                if self.status == "playing":
                    if self.end_round_on_drawer_leave:
                        self.start_rest()
                    else:
                        self.next_round()

            if not self.players:
                # 房间空了，重置为等待状态
                self.status = "waiting"
                self.current_word = None
                self.drawer_id = None
                self.round_number = 0
                self.drawer_order = []
                self.current_drawer_index = 0
                self.round_start_time = 0
                self.rest_start_time = 0

    def get_time_left(self) -> int:
        """返回当前阶段剩余时间（秒）。

        - playing: round_duration 倒计时
        - resting: rest_time 倒计时
        - 其他: 0
        """
        now = time.time()
        if self.status == "playing" and self.round_start_time:
            try:
                elapsed = max(0.0, now - float(self.round_start_time))
            except Exception:
                elapsed = 0.0
            return max(0, int(self.round_duration - elapsed))
        if self.status == "resting" and self.rest_start_time:
            try:
                elapsed = max(0.0, now - float(self.rest_start_time))
            except Exception:
                elapsed = 0.0
            return max(0, int(self.rest_time - elapsed))
        return 0

    def start_rest(self) -> None:
        """进入回合间休息阶段。"""
        self.status = "resting"
        self.rest_start_time = time.time()
        # 清空本回合数据，避免休息阶段泄露/误用
        self.current_word = None
        self.round_start_time = 0
        # 休息阶段不指定绘者，避免客户端继续显示词语
        self.drawer_id = None
        for p in self.players.values():
            p["is_drawer"] = False

    def tick(self) -> bool:
        """服务器每秒调用一次的状态推进。

        Returns:
            True 表示房间状态发生了变化（需要广播事件/状态）。
        """
        if self.status == "playing":
            if self.get_time_left() <= 0:
                self.start_rest()
                return True
        elif self.status == "resting":
            if self.get_time_left() <= 0:
                # 休息结束：进入下一回合或结束游戏
                ok = self.next_round()
                if ok:
                    # next_round 成功，进入 playing 状态
                    self.status = "playing"
                # 无论成功与否（游戏结束时 ok=False），都表示状态变化
                return True
        return False

    def get_public_state(self, for_drawer: bool = False) -> dict:
        """获取房间的公开状态（用于广播给所有玩家）

        Args:
            for_drawer: 如果为True，包含当前词语；否则隐藏词语（只有绘者看得到）
        """
        time_left = self.get_time_left()

        return {
            "room_id": self.room_id,
            "owner_id": self.owner_id,
            "status": self.status,
            "players": self.players,
            "drawer_id": self.drawer_id,
            "round_number": self.round_number,
            "max_rounds": self.max_rounds,
            "round_duration": self.round_duration,
            "rest_time": self.rest_time,
            "time_left": time_left,
            "end_round_on_drawer_leave": bool(self.end_round_on_drawer_leave),
            "current_word": self.current_word if (self.status == "playing" and for_drawer) else None,
            "drawer_order": self.drawer_order,  # 绘画顺序列表
            "current_drawer_index": self.current_drawer_index,  # 当前轮次索引
        }

    def start_game(self) -> bool:
        """开始游戏 - 生成随机绘画顺序"""
        if len(self.players) < 1: # 调试时允许 1 人
            return False
        self.status = "playing"
        self.round_number = 0
        self.current_drawer_index = 0
        # 记录当前回合开始时间，用于统一倒计时
        self.round_start_time = time.time()

        # 生成随机绘画顺序（允许重复，使每个玩家都有机会绘画max_rounds次）
        player_ids = list(self.players.keys())
        self.drawer_order = []
        for _ in range(self.max_rounds):
            self.drawer_order.extend(random.sample(player_ids, len(player_ids)))

        for p in self.players.values():
            p["score"] = 0
        return self.next_round()

    def next_round(self) -> bool:
        """进入下一回合 - 按照预生成的顺序轮流"""
        if self.round_number >= self.max_rounds:
            self.end_game()
            return False

        self.round_number += 1

        # 从预生成的顺序中获取当前绘者；若该玩家已离开，则跳过
        self.drawer_id = None
        while self.current_drawer_index < len(self.drawer_order):
            candidate = self.drawer_order[self.current_drawer_index]
            self.current_drawer_index += 1
            if candidate in self.players:
                self.drawer_id = candidate
                break
        if not self.drawer_id:
            self.end_game()
            return False

        for pid, p in self.players.items():
            p["is_drawer"] = (pid == self.drawer_id)

        # 随机选词（这里简化处理，实际应从词库加载）
        words = ["苹果", "香蕉", "电脑", "汽车", "飞机", "西瓜", "兔子", "太阳"]
        self.current_word = random.choice(words)
        # 新一轮开始时刷新回合开始时间
        self.round_start_time = time.time()

        # 进入新回合时，清空休息计时
        self.rest_start_time = 0

        return True

    def end_game(self):
        """结束游戏"""
        self.status = "ended"
        self.drawer_id = None
        self.current_word = None

    def submit_guess(self, player_id: str, guess_text: str) -> Tuple[bool, int]:
        """提交猜词"""
        if self.status != "playing" or player_id == self.drawer_id:
            return False, 0

        if guess_text == self.current_word:
            # 猜对了，加分
            score_gain = 10
            self.players[player_id]["score"] += score_gain
            # 画手也加分
            if self.drawer_id:
                self.players[self.drawer_id]["score"] += 5

            # 简化：猜对后立即进入下一回合（实际可能需要等待计时结束）
            # self.next_round()
            return True, score_gain

        return False, 0
