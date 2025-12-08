# 开发指南

## 环境配置

### 1. 克隆仓库
```bash
git clone <repository-url>
cd draw-and-guess
```

### 2. 创建虚拟环境
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 安装依赖
```bash
# 安装运行时依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements/dev.txt
```

### 4. 配置 pre-commit
```bash
pre-commit install
```

## 开发流程

### 1. 创建分支
```bash
git checkout -b feature/your-feature-name
```

### 2. 编写代码
- 遵循 PEP 8 代码规范
- 添加必要的注释和文档字符串
- 编写单元测试

### 3. 运行测试
```bash
pytest
```

### 4. 代码检查
```bash
# 自动格式化
black src/

# 检查代码风格
flake8 src/

# 排序 imports
isort src/
```

### 5. 提交代码
```bash
git add .
git commit -m "feat: 添加新功能"
git push origin feature/your-feature-name
```

## 项目结构

```
draw-and-guess/
├── src/                    # 源代码
│   ├── server/            # 服务器端
│   │   ├── network/       # 网络通信
│   │   ├── game/          # 游戏逻辑
│   │   └── models/        # 数据模型
│   ├── client/            # 客户端
│   │   ├── ui/            # 用户界面
│   │   └── game/          # 游戏逻辑
│   └── shared/            # 共享代码
│       ├── constants.py   # 常量定义
│       └── protocols.py   # 协议定义
├── test/                  # 测试代码
├── assets/                # 资源文件
├── data/                  # 数据文件
└── docs/                  # 文档
```

## 代码规范

### 命名规范
- 类名：大驼峰命名法 `GameServer`
- 函数/方法：小写+下划线 `handle_message`
- 常量：全大写+下划线 `MAX_PLAYERS`
- 私有成员：前缀下划线 `_private_method`

### 注释规范
```python
def function_name(param1: str, param2: int) -> bool:
    """
    函数简短描述。

    详细描述（可选）。

    Args:
        param1: 参数1描述
        param2: 参数2描述

    Returns:
        返回值描述

    Raises:
        ValueError: 异常描述
    """
    pass
```

### 提交信息规范
```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具链更新
```

## 测试指南

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定文件
pytest test/unit/test_server/test_server_basic.py

# 显示详细输出
pytest -v

# 显示代码覆盖率
pytest --cov=src
```

### 编写测试
```python
import pytest

def test_example():
    """测试示例"""
    assert 1 + 1 == 2

@pytest.fixture
def sample_data():
    """测试数据fixture"""
    return {"key": "value"}

def test_with_fixture(sample_data):
    """使用fixture的测试"""
    assert sample_data["key"] == "value"
```

## 调试技巧

### 1. 使用日志
```python
import logging

logger = logging.getLogger(__name__)
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 2. 使用断点
```python
import pdb; pdb.set_trace()  # 设置断点
```

### 3. VS Code 调试配置
在 `.vscode/launch.json` 中配置：
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Server",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/server/main.py",
            "console": "integratedTerminal"
        }
    ]
}
```

## 常见问题

### Q: pygame 安装失败？
A: 确保安装了合适的编译工具。Windows 用户可能需要安装 Visual C++ Build Tools。

### Q: 测试失败？
A: 检查是否正确设置了 PYTHONPATH，或者使用 `pytest` 而不是 `python -m pytest`。

### Q: pre-commit hooks 失败？
A: 运行 `pre-commit run --all-files` 查看详细错误信息。

## 参考资源

- [Python 官方文档](https://docs.python.org/3/)
- [Pygame 文档](https://www.pygame.org/docs/)
- [Socket 编程指南](https://docs.python.org/3/library/socket.html)
- [pytest 文档](https://docs.pytest.org/)
