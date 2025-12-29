import random
from typing import Dict, List, Optional, Tuple


class GameRoom:
    """
    游戏房间类，管理玩家、游戏状态和回合逻辑。
    """

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: Dict[str, Dict[str, any]] = {}  # player_id -> {name, score, is_drawer}
        self.owner_id: Optional[str] = None
        self.status = "waiting"  # waiting, playing, ended
        self.current_word: Optional[str] = None
        self.drawer_id: Optional[str] = None
        self.round_number = 0
        self.max_rounds = 5
        self.round_start_time = 0
        self.round_duration = 60  # seconds
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
                    self.next_round()

    def get_public_state(self, for_drawer: bool = False) -> dict:
        """获取房间的公开状态（用于广播给所有玩家）
        
        Args:
            for_drawer: 如果为True，包含当前词语；否则隐藏词语（只有绘者看得到）
        """
        return {
            "room_id": self.room_id,
            "owner_id": self.owner_id,
            "status": self.status,
            "players": self.players,
            "drawer_id": self.drawer_id,
            "round_number": self.round_number,
            "max_rounds": self.max_rounds,
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
        
        # 从预生成的顺序中获取当前绘者
        if self.current_drawer_index < len(self.drawer_order):
            self.drawer_id = self.drawer_order[self.current_drawer_index]
            self.current_drawer_index += 1
        else:
            self.end_game()
            return False
        
        for pid, p in self.players.items():
            p["is_drawer"] = (pid == self.drawer_id)

        # 随机选词（这里简化处理，实际应从词库加载）
        words = ["苹果", "香蕉", "电脑", "汽车", "飞机", "西瓜", "兔子", "太阳"]
        self.current_word = random.choice(words)
        
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
