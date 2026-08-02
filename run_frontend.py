"""
花卉识别 AI Agent - 前端启动脚本

用于启动 Streamlit 前端应用
"""

import subprocess
import sys


def main():
    """启动前端应用"""
    print("=" * 50)
    print("🌸 花卉识别 AI Agent - 前端应用")
    print("=" * 50)
    print("正在启动 Streamlit...")
    print("访问地址: http://localhost:8501")
    print("=" * 50)

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "frontend/app.py",
        "--server.port", "8501",
        "--server.address", "localhost"
    ])


if __name__ == "__main__":
    main()
