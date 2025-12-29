"""
游戏逻辑模块

实现游戏核心逻辑，包括回合控制、分数计算、状态管理等。
"""


class GameRoom:
    """游戏房间类"""
    
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players = []
        self.is_active = True
    
    def add_player(self, player):
        """添加玩家"""
        if player not in self.players:
            self.players.append(player)
    
    def remove_player(self, player):
        """移除玩家"""
        if player in self.players:
            self.players.remove(player)

