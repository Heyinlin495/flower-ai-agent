"""
测试替身（Fakes）：让全部测试离线运行，不依赖真实 LLM / Embedding / API Key。

- FakeEmbeddings：确定性哈希向量，替代 DashScope TextEmbedding
- FakeAgent：模拟真实 Agent 的消息落盘/查询/删除契约，但不调 LLM
"""

import hashlib
import uuid

from langchain_core.embeddings import Embeddings


class FakeEmbeddings(Embeddings):
    """确定性假 embedding：同一文本向量恒定（哈希派生），维度固定，不调外部 API。

    向量质量与真实模型无关，仅保证 Chroma 检索链路（add/search/filter）可跑通。
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _vec(self, text: str) -> list:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        return [float(h[i % 32]) / 255.0 for i in range(self.dim)]

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeAgent:
    """替身 Agent：与 flower_agent 对外契约一致（achat / stream_chat /
    get_session_history / list_sessions / clear_session），行为上真实落盘到
    session_store，但不触发任何 LLM 调用。
    """

    def __init__(self, store):
        self._store = store

    async def achat(self, message, session_id=None, image_url=None):
        session_id = session_id or f"fake_{uuid.uuid4().hex[:8]}"
        reply = f"模拟回复：{message}"
        self._store.add_message(session_id, "user", message, image_url)
        self._store.add_message(session_id, "assistant", reply)
        return {
            "success": True,
            "message": reply,
            "session_id": session_id,
            "image_url": image_url,
            "timestamp": "2026-01-01T00:00:00",
        }

    async def stream_chat(self, message, session_id=None, image_url=None):
        session_id = session_id or f"fake_{uuid.uuid4().hex[:8]}"
        reply = f"模拟回复：{message}"
        self._store.add_message(session_id, "user", message, image_url)
        self._store.add_message(session_id, "assistant", reply)
        yield {"type": "token", "content": "模"}
        yield {"type": "token", "content": "拟"}
        yield {"type": "done", "message": reply, "session_id": session_id}

    def get_session_history(self, session_id):
        return [
            {"role": m["role"], "content": m["content"], "image_url": m.get("image_url")}
            for m in self._store.get_messages(session_id)
        ]

    def list_sessions(self):
        return self._store.list_sessions()

    def clear_session(self, session_id):
        return self._store.delete_session(session_id)
