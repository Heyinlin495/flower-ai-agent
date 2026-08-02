"""
pytest 公共配置

通过 httpx ASGITransport 直接在进程内挂载 FastAPI app，
无需手动启动后端服务，`pytest tests/` 一条命令即可独立跑通。

注意：LLM / Embedding / 语音识别等真实外部调用仍会执行（依赖 .env 中 API Key），
但健康检查、知识库增删查等链路不依赖外部网络。
"""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.fixture
async def client():
    """进程内 ASGI 测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
