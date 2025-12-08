# setup.py - 用于兼容旧版 pip 安装方式

from setuptools import setup, find_packages

# 从 pyproject.toml 读取配置（推荐使用 pyproject.toml）
# 这个文件是为了兼容性而保留

setup(
    name="draw-and-guess",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pygame>=2.0.0",
    ],
    extras_require={
        "dev": [
            "black==23.9.1",
            "flake8==6.1.0",
            "isort==5.12.0",
            "pytest==7.4.0",
            "pytest-cov==4.1.0",
            "pre-commit==3.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "draw-guess-server=src.server.main:main",
            "draw-guess-client=src.client.main:main",
        ],
    },
)
