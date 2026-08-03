"""
花卉识别 AI Agent - 后端启动脚本

用于启动 FastAPI 后端服务
"""

import sys

# 强制 UTF-8 输出：中文 Windows cmd 默认 GBK，打印 emoji 会 UnicodeEncodeError 闪退
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import uvicorn
from backend.config import settings


def main():
    """启动后端服务"""
    print("=" * 50)
    print("🌸 花卉识别 AI Agent - 后端服务")
    print("=" * 50)
    print(f"服务地址: http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"API 文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    print("=" * 50)

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )


if __name__ == "__main__":
    main()
