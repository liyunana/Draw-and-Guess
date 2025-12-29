# 随机绘画顺序功能实现说明

## 功能概述
在联机模式中，系统会在游戏开始时自动生成一个随机的绘画顺序，确保每个玩家都有机会作画，其他玩家猜词。

## 核心实现

### 1. 游戏房间模块 (`src/server/game/room.py`)

#### 新增属性
```python
self.drawer_order: List[str] = []  # 随机生成的绘画顺序（player_id列表）
self.current_drawer_index = 0      # 当前绘者在顺序中的索引
```

#### 修改的方法

**`start_game()` - 游戏开始时生成随机顺序**
```python
def start_game(self) -> bool:
    """开始游戏 - 生成随机绘画顺序"""
    # ...初始化游戏状态...
    
    # 关键：生成随机顺序
    player_ids = list(self.players.keys())
    self.drawer_order = []
    for _ in range(self.max_rounds):
        # 每轮随机打乱玩家顺序
        self.drawer_order.extend(random.sample(player_ids, len(player_ids)))
    
    return self.next_round()
```

**`next_round()` - 按顺序轮流绘画**
```python
def next_round(self) -> bool:
    """进入下一回合 - 按照预生成的顺序轮流"""
    if self.round_number >= self.max_rounds:
        self.end_game()
        return False

    self.round_number += 1
    
    # 从顺序列表中取下一个绘者
    if self.current_drawer_index < len(self.drawer_order):
        self.drawer_id = self.drawer_order[self.current_drawer_index]
        self.current_drawer_index += 1
    else:
        self.end_game()
        return False
    
    # ...更新玩家状态和选词...
    return True
```

### 2. 房间状态广播 (`get_public_state()`)

增加绘画顺序信息到房间公开状态：
```python
def get_public_state(self) -> dict:
    return {
        # ... 其他字段 ...
        "drawer_order": self.drawer_order,           # 完整的绘画顺序
        "current_drawer_index": self.current_drawer_index,  # 当前轮次索引
    }
```

### 3. 网络通信 (`src/server/network/__init__.py`)

#### MSG_START_GAME 处理
- 调用 `room.start_game()` 生成随机顺序
- 广播包含 `drawer_order` 的事件给所有房间玩家

```python
self.broadcast_room(sess.room_id, Message("event", {
    "type": MSG_START_GAME, 
    "ok": True,
    "drawer_order": room.drawer_order,    # 绘画顺序列表
    "drawer_id": room.drawer_id,           # 当前绘者
    "round_number": room.round_number      # 当前轮次
}))
```

#### MSG_NEXT_ROUND 处理
- 调用 `room.next_round()` 进入下一轮
- 广播更新当前绘者信息
- 游戏结束时发送 MSG_END_GAME 事件

### 4. 消息类型 (`src/shared/constants.py`)

新增消息类型：
```python
MSG_ROUND_START = "round_start"  # 通知轮次开始和当前绘者
```

## 工作流程

```
1. 房主点击"开始游戏"
   ↓
2. 服务器接收 MSG_START_GAME
   ↓
3. GameRoom.start_game()
   - 初始化游戏状态
   - 生成随机绘画顺序：[玩家A, 玩家B, 玩家C, 玩家A, 玩家B, ...]
   - 调用 next_round() 进入第一轮
   ↓
4. 广播 MESSAGE("event", {...drawer_order...}) 给所有玩家
   ↓
5. 所有玩家接收顺序信息，绘者开始作画，其他人猜词
   ↓
6. 一轮结束，发送 MSG_NEXT_ROUND
   ↓
7. 进入下一轮，切换绘者
   ↓
8. 重复 6-7 直到 max_rounds 完成
   ↓
9. 发送 MSG_END_GAME，游戏结束
```

## 特点

✅ **公平性**：通过随机打乱确保每个玩家轮流作画
✅ **可预测性**：顺序在游戏开始时生成，所有玩家都知道轮流顺序
✅ **灵活性**：支持任意玩家数量和回合数
✅ **同步性**：服务器统一管理顺序，确保所有客户端一致

## 示例场景

假设3个玩家：玩家A、玩家B、玩家C，max_rounds=3

**生成的 drawer_order：**
```
[B, C, A] (第一轮随机)
[A, B, C] (第二轮随机)
[C, A, B] (第三轮随机)
```

**轮流过程：**
- 第1轮：玩家B作画，玩家A和C猜词
- 第2轮：玩家C作画，玩家A和B猜词
- 第3轮：玩家A作画，玩家B和C猜词
- 第4轮：玩家A作画，玩家B和C猜词
- 第5轮：玩家B作画，玩家A和C猜词
- 第6轮：玩家C作画，玩家A和B猜词
- 游戏结束，统计分数

## 客户端集成建议

客户端应该：
1. 接收 MSG_START_GAME 事件，保存 `drawer_order`
2. 在 UI 中显示当前绘者和剩余轮次
3. 当收到 MSG_NEXT_ROUND 时更新绘者信息
4. 当 `is_drawer=True` 时显示绘画界面，否则显示猜词界面
