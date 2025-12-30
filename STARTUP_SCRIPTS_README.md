# 启动脚本使用说明 (Startup Scripts Usage)

## 问题说明 (Problem)

Windows 批处理文件 (`.bat`) 对中文编码支持不完美，可能导致中文字符乱码。

## 解决方案 (Solutions)

我们提供了三种启动方式，推荐使用 **PowerShell 脚本**（最稳定）：

### 1️⃣ **PowerShell 脚本** (推荐 - Recommended) ⭐

```bash
# 在 PowerShell 中直接运行：
.\start.ps1
```

**优点：**
- ✅ 完全支持中文和 Unicode
- ✅ 错误处理更完善
- ✅ 跨平台兼容

**首次运行可能需要设置执行策略：**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2️⃣ **批处理脚本** (Batch Script)

两个版本可选：

**选项 A: 英文版本** (推荐 - 最稳定)
```cmd
start.bat
```

**选项 B: 中文版本**
```cmd
start_cn.bat
```

**说明：**
- `start.bat` - 使用英文菜单，避免编码问题
- `start_cn.bat` - 包含中文说明注释

### 3️⃣ **手动启动** (Manual Start)

如果脚本有问题，可以手动启动：

```bash
# 1. 创建虚拟环境（首次）
python -m venv venv

# 2. 激活虚拟环境
venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 选择启动方式
# 启动服务器
python src\server\main.py

# 或启动客户端
python src\client\main.py

# 或同时启动（需要两个终端）
# 终端1: python src\server\main.py
# 终端2: python src\client\main.py
```

## 菜单选项说明 (Menu Options)

无论使用哪个脚本，菜单选项都是：

| 选项 | 说明 | English |
|------|------|---------|
| 1 | 仅启动服务器 | Start server only |
| 2 | 仅启动客户端 | Start client only |
| 3 | 同时启动服务器和客户端 | Start both server and client |
| 4 | 运行测试 | Run tests |

## 故障排除 (Troubleshooting)

### PowerShell 脚本执行权限错误

如果看到 `cannot be loaded because running scripts is disabled`：

```powershell
# 临时允许当前会话执行脚本
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 然后再次运行
.\start.ps1
```

### 批处理脚本中文乱码

- 使用 `start.bat`（英文版本）代替
- 或升级到 PowerShell 脚本

### 端口 5555 已被占用

脚本会自动尝试释放端口。如果仍有问题：

```cmd
REM 查看占用端口的进程
netstat -ano | findstr :5555

REM 手动关闭进程（替换 PID）
taskkill /PID <PID> /F
```

### Python 不在 PATH 中

确保 Python 已正确安装并添加到系统 PATH：

```bash
python --version
```

如果命令无法识别，需要重新安装 Python 并勾选"Add Python to PATH"选项。

## 推荐使用顺序

1. **首先尝试：** `.\start.ps1` (PowerShell)
2. **其次尝试：** `start.bat` (英文批处理)
3. **最后手动：** 按照"手动启动"部分逐步操作

## 文件说明

| 文件 | 说明 |
|------|------|
| `start.ps1` | PowerShell 脚本（推荐） |
| `start.bat` | 英文版批处理脚本 |
| `start_cn.bat` | 中英混合批处理脚本 |
| `start_fixed.bat` | 备用的英文版本 |

---

**最后，如果以上方案都不行，请直接在 PowerShell 或 CMD 中手动执行 Python 命令。**
