"""
花卉识别 AI Agent - API 集成测试

使用 httpx ASGITransport 在进程内挂载 FastAPI app，无需手动启动后端。
运行方式：pytest tests/ -v
"""

import json
import uuid

import pytest
from httpx import AsyncClient


# ── 基础 ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health(client: AsyncClient):
    """健康检查"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


@pytest.mark.anyio
async def test_root(client: AsyncClient):
    """根路径"""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


# ── 知识库 ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_knowledge_search(client: AsyncClient):
    """知识库搜索"""
    resp = await client.get(
        "/api/flower/knowledge/search",
        params={"query": "玫瑰养护", "top_k": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["results"]) > 0
    # 结果必须带 metadata.flower_name（前端依赖此字段）
    for r in data["results"]:
        assert r["metadata"]["flower_name"], "结果缺少 flower_name 元数据"


@pytest.mark.anyio
async def test_knowledge_search_filter(client: AsyncClient):
    """知识库搜索 + 花卉名过滤"""
    resp = await client.get(
        "/api/flower/knowledge/search",
        params={"query": "怎么养护", "flower_name": "玫瑰", "top_k": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    for r in data["results"]:
        assert r["metadata"]["flower_name"] == "玫瑰"


@pytest.mark.anyio
async def test_knowledge_list(client: AsyncClient):
    """知识库花卉列表"""
    resp = await client.get("/api/flower/knowledge/list")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["flowers"], list)
    assert data["total"] == len(data["flowers"])


@pytest.mark.anyio
async def test_knowledge_add_and_delete(client: AsyncClient):
    """知识添加 + 删除（用唯一名称避免污染知识库）"""
    flower_name = f"测试花_{uuid.uuid4().hex[:6]}"
    flower_data = {
        "name": flower_name,
        "family": "测试科",
        "genus": "测试属",
        "origin": "测试产地",
        "flowering_period": "全年",
        "language": "测试",
        "habitat": "测试环境",
        "characteristics": "测试特征",
        "care_content": "测试养护",
    }

    # 添加
    resp = await client.post("/api/flower/knowledge/add", json=flower_data)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 列表应包含新花
    resp = await client.get("/api/flower/knowledge/list")
    assert flower_name in resp.json()["flowers"]

    # 删除
    resp = await client.delete(f"/api/flower/knowledge/delete/{flower_name}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 列表应已移除
    resp = await client.get("/api/flower/knowledge/list")
    assert flower_name not in resp.json()["flowers"]


# ── 聊天 ─────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_chat_send(client: AsyncClient):
    """聊天发送（普通接口）"""
    session_id = f"pytest_send_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        "/api/chat/send",
        json={"message": "你好", "session_id": session_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["message"]
    # 清理测试会话，避免污染持久化数据
    await client.delete(f"/api/chat/history/{session_id}")


@pytest.mark.anyio
async def test_chat_stream(client: AsyncClient):
    """聊天流式接口（SSE）"""
    session_id = f"pytest_stream_{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        "/api/chat/stream",
        json={"message": "向日葵的花语是什么？", "session_id": session_id},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    got_token = False
    got_done = False
    async for line in resp.aiter_lines():
        if not line.startswith("data: "):
            continue
        try:
            item = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if item.get("type") == "token" and item.get("content"):
            got_token = True
        if item.get("type") == "done":
            got_done = True
            break
    assert got_token, "流式响应未产出 token"
    assert got_done, "流式响应未收到 done 事件"
    # 清理测试会话
    await client.delete(f"/api/chat/history/{session_id}")


# ── 会话历史 ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_sessions_list(client: AsyncClient):
    """会话列表接口"""
    resp = await client.get("/api/chat/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["sessions"], list)
    assert data["total"] == len(data["sessions"])


@pytest.mark.anyio
async def test_chat_history_roundtrip(client: AsyncClient):
    """会话历史：发送后可用 history 拉取，可删除"""
    session_id = f"pytest_history_{uuid.uuid4().hex[:6]}"

    # 发送一条消息
    resp = await client.post(
        "/api/chat/send",
        json={"message": "你好", "session_id": session_id},
    )
    assert resp.status_code == 200

    # 拉取历史，应有 user + assistant 两条
    resp = await client.get(f"/api/chat/history/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    roles = [m["role"] for m in data["messages"]]
    assert roles == ["user", "assistant"], f"历史消息角色异常: {roles}"

    # 会话列表应包含该会话
    resp = await client.get("/api/chat/sessions")
    sids = [s["id"] for s in resp.json()["sessions"]]
    assert session_id in sids

    # 删除历史
    resp = await client.delete(f"/api/chat/history/{session_id}")
    assert resp.status_code == 200
    resp = await client.get(f"/api/chat/history/{session_id}")
    assert resp.json()["total"] == 0
