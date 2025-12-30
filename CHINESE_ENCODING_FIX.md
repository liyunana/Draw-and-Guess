# 中文乱码修复说明

## 问题描述
在房间聊天中输入中文时，出现乱码或显示不正常的现象。

## 根本原因

### 1. JSON 转义问题
Python 的 `json.dumps()` 默认使用 `ensure_ascii=True`，会将所有非 ASCII 字符（包括中文）转义为 `\uXXXX` Unicode 转义序列。虽然这在网络传输中是正确的，但当接收端使用 `errors="ignore"` 时，可能导致某些字符被忽略。

### 2. 解码错误处理不当
使用 `decode("utf-8", errors="ignore")` 会默默忽略任何无法解码的 UTF-8 字节序列，导致：
- 不完整的多字节字符被丢弃
- 乱码消息被截断
- 错误信息没有任何提示

## 修复方案

### 1. JSON 编码优化 (`src/shared/protocols.py`)
```python
def to_json(self) -> str:
    """将消息转换为 JSON 字符串"""
    return json.dumps(
        {"type": self.type, "data": self.data}, 
        ensure_ascii=False  # ← 添加此参数
    )
```

**效果**：
- 使用 UTF-8 编码直接传输中文，而不是转义
- 减少传输数据量
- 提高易读性

### 2. 解码错误处理改善

#### 服务器端 (`src/server/network/__init__.py`)
```python
def _handle_raw_message(self, sess: ClientSession, raw: bytes) -> None:
    try:
        text = raw.decode("utf-8", errors="replace")  # 改为 replace
        msg = Message.from_json(text)
    except Exception:
        return
```

#### 客户端 (`src/client/network.py`)
```python
def _handle_raw(self, raw: bytes) -> None:
    try:
        text = raw.decode("utf-8", errors="replace")  # 改为 replace
        msg = Message.from_json(text)
        self.events.put(msg)
    except Exception:
        pass
```

#### 客户端游戏模块 (`src/client/game/__init__.py`)
```python
def _handle_raw(self, raw: bytes) -> None:
    try:
        text = raw.decode("utf-8", errors="replace")  # 改为 replace
        msg = Message.from_json(text)
    except Exception:
        return
```

**效果**：
- `errors="ignore"`：忽略错误，导致数据丢失（不推荐）
- `errors="replace"`：用 `\ufffd`（替换字符）替换错误（推荐）
- `errors="strict"`：遇到错误直接抛出异常（太严格）

## 修复前后对比

### 修复前
```
输入：你好世界
JSON: {"type":"chat","data":{"text":"\u4f60\u597d\u4e16\u754c"}}
网络传输: \u4f60\u597d\u4e16\u754c (转义形式)
解码: errors="ignore" → 可能丢失某些字符
显示: ??? 或 乱码
```

### 修复后
```
输入：你好世界
JSON: {"type":"chat","data":{"text":"你好世界"}}
网络传输: 你好世界 (UTF-8 编码)
解码: errors="replace" → 完整保留所有字符
显示: 你好世界 ✓
```

## 修改的文件清单

1. **`src/shared/protocols.py`**
   - 修改 `to_json()` 添加 `ensure_ascii=False`

2. **`src/server/network/__init__.py`**
   - 修改 `_handle_raw_message()` 的解码方式

3. **`src/client/network.py`**
   - 修改 `_handle_raw()` 的解码方式

4. **`src/client/game/__init__.py`**
   - 修改 `_handle_raw()` 的解码方式

## 技术细节

### UTF-8 编码
UTF-8 是可变长度编码：
- ASCII 字符（0-127）：1 字节
- 中文字符（0x4E00-0x9FFF）：通常 3 字节

例如 "你好" 编码为：
```
你 (U+4F60): E4 BD A0 (3 字节)
好 (U+597D): E5 A5 BD (3 字节)
```

### 为什么 `errors="ignore"` 有问题
如果传输过程中因为网络问题缺少了一个字节，例如只收到 `E4 BD`（缺少 `A0`），那么：
- `errors="ignore"`：直接丢弃这个不完整的字符
- `errors="replace"`：用 `\ufffd` 替换这个不完整的字符（更好的反馈）

## 测试建议

1. **基本中文测试**
   - 启动游戏，创建房间
   - 在聊天栏输入："你好"、"世界"、"测试"
   - 验证聊天框中正确显示中文

2. **特殊字符测试**
   - 输入 emoji：😀😁😂
   - 输入特殊符号：！@#￥%
   - 输入繁体中文：繁體测試

3. **长文本测试**
   - 输入较长的中文句子
   - 验证不会因为字符位置而乱码

4. **多人测试**
   - 启动多个客户端
   - 互相发送中文消息
   - 验证所有人都能正确接收

## 性能影响

- **正面影响**：
  - 网络传输数据量减少（中文字符不需要转义）
  - JSON 解析速度不变
  - 内存占用不变

- **无负面影响**：
  - 错误处理的性能差异可忽略不计
