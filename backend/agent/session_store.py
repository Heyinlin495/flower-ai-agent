"""
花卉识别 AI Agent - 会话持久化存储

使用 SQLite 将会话与消息落盘，后端重启后聊天历史不丢失。

Author: 何胤霖 (Yinlin He)
"""

import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent / "data" / "sessions.db"

# SQLite 连接按线程隔离
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """获取当前线程的 SQLite 连接（延迟创建 + WAL 模式）"""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        # 多 worker 多进程并发写时，等待锁而非立刻报 "database is locked"
        conn.execute("PRAGMA busy_timeout=5000")
        _local.conn = conn
    return conn


def _init_db():
    """建表"""
    conn = _get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新会话',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            image_url TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """
    )
    conn.commit()


class SessionStore:
    """会话与消息的 SQLite 存储"""

    def __init__(self):
        self._init_lock = threading.Lock()
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            with self._init_lock:
                if not self._initialized:
                    _init_db()
                    self._initialized = True

    # ── 会话 ─────────────────────────────────────────────────────

    def list_sessions(self) -> List[dict]:
        """列出所有会话（按更新时间倒序），含消息数"""
        self._ensure_init()
        conn = _get_conn()
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    # ── 消息 ─────────────────────────────────────────────────────

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        image_url: Optional[str] = None,
    ) -> None:
        """添加消息（自动创建会话 + 推导标题 + 更新时间戳）"""
        self._ensure_init()
        conn = _get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at) VALUES (?, '新会话', ?, ?)",
            (session_id, now, now),
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content, image_url, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, image_url, now),
        )
        # 首条 user 文本消息自动推导标题
        if role == "user" and not image_url and content:
            conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ? AND title = '新会话'",
                (content[:30], session_id),
            )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        conn.commit()

    def add_messages(self, session_id: str, messages: List[dict]) -> None:
        """
        批量添加消息（单事务）。

        用于前端图片识别等不走 Agent 的回合：用户消息（含 image_url）
        与助手回复一次落盘，刷新后历史不丢。

        Args:
            session_id: 会话 ID
            messages: [{"role": ..., "content": ..., "image_url": ...}]
        """
        if not messages:
            return
        self._ensure_init()
        conn = _get_conn()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, title, created_at, updated_at) VALUES (?, '新会话', ?, ?)",
            (session_id, now, now),
        )
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            image_url = m.get("image_url")
            conn.execute(
                "INSERT INTO messages (session_id, role, content, image_url, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, image_url, now),
            )
            # 首条 user 文本消息自动推导标题（与 add_message 逻辑一致）
            if role == "user" and not image_url and content:
                conn.execute(
                    "UPDATE sessions SET title = ? WHERE id = ? AND title = '新会话'",
                    (content[:30], session_id),
                )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        conn.commit()

    def get_messages(self, session_id: str) -> List[dict]:
        """获取会话消息（按时间正序）"""
        self._ensure_init()
        conn = _get_conn()
        rows = conn.execute(
            "SELECT role, content, image_url, created_at FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        """删除会话及其消息"""
        self._ensure_init()
        conn = _get_conn()
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0


# 全局实例
session_store = SessionStore()
