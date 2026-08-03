"""
pytest 公共配置

通过 httpx ASGITransport 直接在进程内挂载 FastAPI app，无需手动启动后端。

全部测试离线运行（CI 无需 API Key）：
- 聊天相关测试：chat_router 用 FakeAgent 替身，不调 LLM
- 知识库测试：FakeEmbeddings 替代 DashScope，向量库落到临时目录（不碰 data/chroma_db）
- 会话存储：临时 SQLite（不污染 data/sessions.db）
- API 鉴权默认关闭（鉴权测试自行开启）
"""

import importlib
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# 保证项目根目录在 sys.path（`python -m pytest` 下自动存在，直接 `pytest` 时兜底）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app
from backend.config import settings
from backend.agent import session_store as session_store_mod
from backend.rag.knowledge_base import knowledge_base

from tests.fakes import FakeAgent, FakeEmbeddings

# 注意：backend.api.chat_router 在 __init__.py 里被重导出为 APIRouter 对象，
# 必须 importlib 拿真正的模块才能 monkeypatch 模块属性
chat_router_module = importlib.import_module("backend.api.chat_router")


@pytest.fixture(autouse=True)
def _offline_env(tmp_path, monkeypatch):
    """全测试离线环境：假 embedding + 隔离 chroma/SQLite 目录 + 关鉴权"""
    # 1) 知识库：假 embedding + 独立向量库目录（不碰 data/chroma_db）
    fake_emb = FakeEmbeddings()
    monkeypatch.setattr(knowledge_base, "embeddings", fake_emb)
    monkeypatch.setattr(knowledge_base.vector_store, "embeddings", fake_emb)
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    knowledge_base.vector_store._store = None
    knowledge_base._initialized = False

    # 2) 会话存储：独立 SQLite（不污染 data/sessions.db）
    monkeypatch.setattr(session_store_mod, "DB_PATH", tmp_path / "sessions.db")
    session_store_mod._local.conn = None
    # 重置初始化标志：否则跳过建表，新库会报 no such table
    session_store_mod.session_store._initialized = False

    # 3) 鉴权默认关闭（鉴权测试自行开启）
    monkeypatch.setattr(settings, "API_TOKEN", "")


@pytest.fixture(autouse=True)
def _fake_agent(monkeypatch):
    """聊天路由用 FakeAgent 替身，不调真实 LLM"""
    fake = FakeAgent(session_store_mod.session_store)
    monkeypatch.setattr(chat_router_module, "flower_agent", fake)


@pytest.fixture
async def client():
    """进程内 ASGI 测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
