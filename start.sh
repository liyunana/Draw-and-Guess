#!/bin/bash
# 快速启动脚本 (Linux/Mac)

echo "🎨 Draw & Guess 游戏启动脚本"
echo "================================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，正在创建..."
    python3 -m venv venv
    echo "✅ 虚拟环境创建完成"
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
echo "📦 检查依赖..."
pip install -q -r requirements.txt

# 选择启动模式
echo ""
echo "请选择启动模式:"
echo "1) 启动服务器"
echo "2) 启动客户端"
echo "3) 同时启动服务器和客户端"
echo "4) 运行测试"
read -p "输入选项 (1-4): " choice

# 释放占用端口（如有残留进程）
free_port() {
    if command -v fuser >/dev/null 2>&1; then
        fuser -n tcp 5555 -k 2>/dev/null || true
    else
        # 回退方案：使用 lsof
        pid=$(lsof -ti tcp:5555 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill -9 $pid 2>/dev/null || true
        fi
    fi
}

case $choice in
    1)
        echo "🚀 启动服务器..."
        free_port
        python src/server/main.py
        ;;
    2)
        echo "🚀 启动客户端..."
        python src/client/main.py
        ;;
    3)
        echo "🚀 启动服务器和客户端..."
        free_port
        python src/server/main.py &
        server_pid=$!
        sleep 2
        python src/client/main.py
        # 客户端退出后，清理后台服务器
        if ps -p "$server_pid" >/dev/null 2>&1; then
            kill "$server_pid" 2>/dev/null || true
        fi
        ;;
    4)
        echo "🧪 运行测试..."
        pytest -v
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac
