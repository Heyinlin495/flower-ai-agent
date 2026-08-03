"""
花卉识别 AI Agent - 前端启动脚本

用于启动 Streamlit 前端应用
"""

import subprocess
import sys

# 强制 UTF-8 输出：中文 Windows cmd 默认 GBK，打印 emoji 会 UnicodeEncodeError 闪退
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


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
        # 绑定 0.0.0.0：Docker 端口映射需要（绑定 localhost 时外部流量进不来）
        "--server.address", "0.0.0.0"
    ])


if __name__ == "__main__":
    main()
