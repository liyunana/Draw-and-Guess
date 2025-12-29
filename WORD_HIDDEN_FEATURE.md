# 词语隐藏功能实现说明

## 功能概述
在联机游戏中，只有正在作画的玩家（绘者）能看到当前的词语提示，其他玩家则无法看到词语，增加了猜词的难度和趣味性。

## 实现原理

### 1. 服务器端 (`src/server/game/room.py`)

**修改 `get_public_state()` 方法**
```python
def get_public_state(self, for_drawer: bool = False) -> dict:
    """获取房间的公开状态
    
    Args:
        for_drawer: 如果为True，包含当前词语；否则隐藏词语
    """
    return {
        # ...其他字段...
        "current_word": self.current_word if (self.status == "playing" and for_drawer) else None,
    }
```

**关键机制：**
- 添加 `for_drawer` 参数来控制词语的可见性
- 只有当 `for_drawer=True` 且游戏进行中时，才包含 `current_word`
- 否则 `current_word` 设置为 `None`

### 2. 网络层 (`src/server/network/__init__.py`)

**新增 `broadcast_room_state()` 方法**
```python
def broadcast_room_state(self, room_id: str) -> None:
    """向房间广播房间状态，但对非绘者隐藏当前词语"""
    if room_id not in self.rooms:
        return
    room = self.rooms[room_id]
    
    for s in list(self.sessions.values()):
        if s.room_id == room_id:
            # 判断该玩家是否是绘者
            is_drawer = (s.player_id == room.drawer_id)
            # 根据身份发送不同的房间状态
            state = room.get_public_state(for_drawer=is_drawer)
            self._send(s, Message(MSG_ROOM_UPDATE, state))
```

**工作流程：**
1. 遍历房间内的所有玩家
2. 对每个玩家检查是否是当前绘者 (`player_id == room.drawer_id`)
3. 根据身份调用 `get_public_state(for_drawer=True/False)`
4. 发送定制化的房间状态消息

### 3. 客户端主程序 (`src/client/main.py`)

**处理房间状态更新**
```python
if msg.type == MSG_ROOM_UPDATE or msg.type == "room_state":
    APP_STATE["current_room"] = data
    
    # 更新 HUD 中的词语和绘者状态
    if APP_STATE["screen"] == "play" and ui and "hud" in ui:
        hud = ui["hud"]
        player_id = APP_STATE["settings"].get("player_id")
        drawer_id = data.get("drawer_id")
        
        # 判断当前玩家是否是绘者
        hud["is_drawer"] = (player_id == drawer_id)
        
        # 只有绘者才能看到词语
        if hud["is_drawer"]:
            hud["current_word"] = data.get("current_word")
        else:
            hud["current_word"] = None  # 隐藏词语
```

**词语显示逻辑**
```python
is_drawer = hud.get("is_drawer", False)
if is_drawer:
    word = hud.get("current_word") or "(未选择)"
    word_display = f"当前词: {word}"
else:
    word_display = "当前词: (隐藏)"  # 非绘者看不到词语
word_txt = font.render(word_display, True, (60, 60, 60))
```

## 数据流

```
游戏进行中：
┌─────────────────────────────────┐
│  客户端A（绘者）                 │
│  - is_drawer = True              │
│  - current_word = "苹果"         │
│  - 显示: "当前词: 苹果"          │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  客户端B（猜词）                 │
│  - is_drawer = False             │
│  - current_word = None           │
│  - 显示: "当前词: (隐藏)"        │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  客户端C（猜词）                 │
│  - is_drawer = False             │
│  - current_word = None           │
│  - 显示: "当前词: (隐藏)"        │
└─────────────────────────────────┘
```

## 关键流程

### 游戏开始流程
1. 房主点击"开始游戏"
2. 服务器调用 `room.start_game()` 生成随机顺序
3. 调用 `broadcast_room_state()` 发送初始房间状态
4. 绘者收到包含词语的消息：`{"current_word": "苹果", ...}`
5. 其他玩家收到隐藏词语的消息：`{"current_word": None, ...}`

### 轮次切换流程
1. 一轮结束，发送 `MSG_NEXT_ROUND`
2. 服务器调用 `room.next_round()` 切换绘者
3. 调用 `broadcast_room_state()` 发送更新状态
4. **新的绘者**能看到新的词语
5. **之前的绘者**现在只能看到"(隐藏)"

## 安全性考虑

✅ **服务器控制**：词语隐藏完全由服务器控制，客户端无法绕过
✅ **动态判断**：基于 `player_id` 和 `drawer_id` 的动态比对
✅ **消息层安全**：即使客户端尝试篡改本地数据，服务器也会不断发送正确的状态
✅ **网络传输安全**：非绘者永远不会从网络接收到词语数据

## 兼容性

- ✅ 支持任意数量的玩家
- ✅ 支持多轮游戏（词语隐藏在每一轮都有效）
- ✅ 支持玩家中途加入（新加入的玩家会立即收到正确的隐藏状态）
- ✅ 向后兼容老客户端（如果客户端不处理隐藏逻辑，也不会收到词语数据）

## 测试建议

1. **单玩家测试**
   - 启动游戏，作为绘者应该看到词语
   - 确认词语正确显示

2. **多玩家测试**
   - 启动2个客户端
   - 绘者看到完整词语
   - 非绘者看到"(隐藏)"

3. **轮次切换测试**
   - 进行多轮游戏
   - 每轮切换绘者时，验证词语的可见性正确切换

4. **网络延迟测试**
   - 模拟网络延迟（使用浏览器开发者工具）
   - 验证在高延迟情况下词语仍然正确隐藏
