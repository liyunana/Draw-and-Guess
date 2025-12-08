# API 文档

## 通信协议

### 消息格式

所有消息使用 JSON 格式：

```json
{
  "type": "消息类型",
  "data": {
    // 消息数据
  }
}
```

### 消息类型

#### 1. 连接相关

**客户端连接 (connect)**
```json
{
  "type": "connect",
  "data": {
    "username": "玩家名称",
    "version": "0.1.0"
  }
}
```

**服务器响应**
```json
{
  "type": "connect_response",
  "data": {
    "success": true,
    "player_id": "唯一玩家ID",
    "message": "连接成功"
  }
}
```

#### 2. 房间相关

**加入房间 (join_room)**
```json
{
  "type": "join_room",
  "data": {
    "room_id": "房间ID（可选，不填则自动匹配）"
  }
}
```

**离开房间 (leave_room)**
```json
{
  "type": "leave_room",
  "data": {}
}
```

#### 3. 游戏相关

**绘图数据 (draw)**
```json
{
  "type": "draw",
  "data": {
    "action": "draw|erase|clear",
    "x": 100,
    "y": 200,
    "color": [0, 0, 0],
    "size": 5
  }
}
```

**猜词 (guess)**
```json
{
  "type": "guess",
  "data": {
    "word": "猜测的词语"
  }
}
```

**聊天 (chat)**
```json
{
  "type": "chat",
  "data": {
    "message": "聊天内容"
  }
}
```

## 服务器 API

### GameServer

游戏服务器主类。

**方法：**
- `start()` - 启动服务器
- `stop()` - 停止服务器
- `handle_client(client_socket)` - 处理客户端连接

### RoomManager

房间管理器。

**方法：**
- `create_room(room_id)` - 创建房间
- `join_room(player, room_id)` - 加入房间
- `leave_room(player)` - 离开房间

## 客户端 API

### GameClient

游戏客户端主类。

**方法：**
- `connect(host, port)` - 连接服务器
- `disconnect()` - 断开连接
- `send_message(message)` - 发送消息

### Canvas

画布组件。

**方法：**
- `draw(x, y, color, size)` - 绘制
- `erase(x, y, size)` - 擦除
- `clear()` - 清空画布

## 数据模型

### Player

玩家数据模型。

```python
{
    "id": "唯一ID",
    "name": "玩家名称",
    "score": 0,
    "is_drawer": False,
    "is_ready": False
}
```

### Room

房间数据模型。

```python
{
    "id": "房间ID",
    "players": [],  # 玩家列表
    "max_players": 8,
    "current_drawer": None,
    "current_word": None,
    "game_state": "waiting|playing|ended",
    "round": 1,
    "max_rounds": 3
}
```
