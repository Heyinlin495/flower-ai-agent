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
    # 多 worker：多人同时访问不排队（一个请求等 LLM 回复时，其他请求由别的 worker 处理）。
    # Windows 下强制单进程（spawn 启动慢且不稳定）；DEBUG 模式下 uvicorn reload 与 workers 互斥。
    workers = settings.APP_WORKERS
    if sys.platform == "win32" or settings.DEBUG:
        workers = 1

    print("=" * 50)
    print("🌸 花卉识别 AI Agent - 后端服务")
    print("=" * 50)
    print(f"服务地址: http://{settings.APP_HOST}:{settings.APP_PORT}")
    print(f"API 文档: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    print(f"Worker 进程数: {workers}（生产环境多人访问建议 ≥2，可用 APP_WORKERS 调整）")
    print("=" * 50)

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        workers=workers,
        reload=settings.DEBUG and workers == 1
    )


if __name__ == "__main__":
    main()
