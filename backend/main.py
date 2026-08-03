"""
花卉识别 AI Agent - FastAPI 主程序

启动 FastAPI 服务，提供花卉识别和聊天 API

Author: 何胤霖 (Yinlin He)
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api.chat_router import router as chat_router
from .api.flower_router import router as flower_router
from .rag.knowledge_base import knowledge_base

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    在应用启动时初始化知识库
    """
    # 启动时执行
    logger.info("正在初始化花卉识别 AI Agent...")

    try:
        # 初始化知识库
        knowledge_base.initialize()
        logger.info("知识库初始化完成")
    except Exception as e:
        logger.error(f"知识库初始化失败: {e}")
        # 不阻止应用启动，允许后续重试

    logger.info("花卉识别 AI Agent 启动完成")

    yield

    # 关闭时执行
    logger.info("花卉识别 AI Agent 正在关闭...")


def verify_api_token(request: Request):
    """
    API 访问鉴权（依赖注入到所有 /api/* 路由）。

    未配置 API_TOKEN 时跳过校验（本地开发）；
    配置后要求请求头 Authorization: Bearer <token>，否则 401。
    """
    if not settings.API_TOKEN:
        return
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {settings.API_TOKEN}":
        raise HTTPException(status_code=401, detail="未授权访问")


# 创建 FastAPI 应用
app = FastAPI(
    title="花卉识别 AI Agent",
    description="基于 LangChain 和 RAG 的花卉识别智能聊天系统",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# 配置 CORS（来源来自配置项，.env 的 CORS_ALLOW_ORIGINS 可覆盖）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_origins_list != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（全部挂鉴权依赖；/health、/docs 等非 /api 路径不受影响）
app.include_router(chat_router, dependencies=[Depends(verify_api_token)])
app.include_router(flower_router, dependencies=[Depends(verify_api_token)])


@app.get("/")
async def root():
    """
    根路径

    Returns:
        dict: 欢迎信息
    """
    return {
        "message": "欢迎使用花卉识别 AI Agent",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat/send",
            "recognize": "/api/flower/recognize",
            "knowledge_search": "/api/flower/knowledge/search"
        }
    }


@app.get("/health")
async def health_check():
    """
    健康检查

    Returns:
        dict: 健康状态
    """
    return {
        "status": "healthy",
        "service": "flower-ai-agent"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
