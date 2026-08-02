"""
花卉识别 AI Agent - Streamlit 前端应用

多页面布局：聊天、知识搜索、知识管理、关于
侧边栏包含会话历史、系统状态和操作按钮

Author: 何胤霖 (Yinlin He)
"""

import streamlit as st
import requests
import time
from datetime import datetime

from config import API_BASE_URL

# 页面配置
st.set_page_config(
    page_title="花卉识别 AI 助手",
    page_icon="🌸",
    layout="centered",
)

# ── 会话历史管理 ─────────────────────────────────────────────────────────────

MAX_SESSIONS = 20  # 最多保留 20 个历史会话

if "_sessions" not in st.session_state:
    st.session_state._sessions = {}  # {sid: {"title": str, "messages": list, "ts": str}}
if "session_id" not in st.session_state:
    sid = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state.session_id = sid
    st.session_state._sessions[sid] = {"title": "新会话", "messages": [], "ts": datetime.now().isoformat()}
if "messages" not in st.session_state:
    st.session_state.messages = []


def _save_session():
    """保存当前消息到会话存储，并自动提取标题"""
    sid = st.session_state.session_id
    msgs = st.session_state.messages
    title = "新会话"
    for m in msgs:
        if m["role"] == "user" and not m.get("image_url"):
            title = m["content"][:30]
            break
    st.session_state._sessions[sid] = {
        "title": title,
        "messages": list(msgs),
        "ts": datetime.now().isoformat(),
    }


def load_session(sid: str):
    """切换到指定会话"""
    if sid == st.session_state.session_id:
        return
    _save_session()
    data = st.session_state._sessions[sid]
    st.session_state.session_id = sid
    # 优先从后端拉取该会话历史；拉不到时退回本地缓存
    backend_msgs = fetch_backend_history(sid)
    st.session_state.messages = backend_msgs if backend_msgs else list(data["messages"])


def new_session():
    """创建新会话并保存当前会话"""
    _save_session()
    sid = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state._sessions[sid] = {"title": "新会话", "messages": [], "ts": datetime.now().isoformat()}
    st.session_state.session_id = sid
    st.session_state.messages = []

    # 清理过多的旧会话
    sessions = st.session_state._sessions
    if len(sessions) > MAX_SESSIONS:
        sorted_sids = sorted(sessions.keys(), key=lambda k: sessions[k]["ts"], reverse=True)
        for old_sid in sorted_sids[MAX_SESSIONS:]:
            del sessions[old_sid]


def delete_session(sid: str):
    """删除指定会话（同时清除后端历史）"""
    sessions = st.session_state._sessions
    if sid in sessions:
        del sessions[sid]
    # 同步删除后端会话历史
    clear_backend_history(sid)
    # 如果删除的是当前会话，切换到最新的
    if sid == st.session_state.session_id and sessions:
        latest = max(sessions.keys(), key=lambda k: sessions[k]["ts"])
        load_session(latest)
    elif not sessions:
        new_session()


def clear_current_messages():
    """清空当前会话消息（不删除会话）"""
    st.session_state.messages = []


# ── API 工具 ──────────────────────────────────────────────────────────────────

_HEALTH_CACHE_TTL = 30


def check_backend_health() -> bool:
    """检查后端服务是否在线（结果缓存 30 秒）"""
    now = time.time()
    cache = st.session_state.get("_health_cache")
    if cache and (now - cache["ts"] < _HEALTH_CACHE_TTL):
        return cache["ok"]
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=1)
        ok = resp.status_code == 200
    except Exception:
        ok = False
    st.session_state["_health_cache"] = {"ts": now, "ok": ok}
    return ok


def fetch_backend_history(session_id: str) -> list:
    """从后端拉取会话历史（失败返回空列表，不阻塞页面）"""
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/chat/history/{session_id}",
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("messages", [])
    except Exception:
        pass
    return []


def restore_sessions_from_backend():
    """把后端持久化的会话合并进本地 _sessions（保留本地已存在项）"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/chat/sessions", timeout=5)
        if resp.status_code != 200:
            return
        for s in resp.json().get("sessions", []):
            sid = s["id"]
            if sid not in st.session_state._sessions:
                st.session_state._sessions[sid] = {
                    "title": s["title"] or "新会话",
                    "messages": [],
                    "ts": s["updated_at"] or s["created_at"],
                }
    except Exception:
        pass


def clear_backend_history(session_id: str):
    """删除后端会话历史（失败静默）"""
    try:
        requests.delete(
            f"{API_BASE_URL}/api/chat/history/{session_id}",
            timeout=5,
        )
    except Exception:
        pass


# ── 侧边栏（温馨风格） ─────────────────────────────────────────────────────

def _format_relative_time(ts_iso: str) -> str:
    """把 ISO 时间戳格式化为相对时间（刚刚 / N 分钟前 / 今天 HH:MM …）"""
    try:
        dt = datetime.fromisoformat(ts_iso)
    except ValueError:
        return ""
    diff = datetime.now() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{int(seconds // 60)} 分钟前"
    if diff.days < 1:
        return f"今天 {dt.strftime('%H:%M')}"
    if diff.days < 2:
        return f"昨天 {dt.strftime('%H:%M')}"
    return dt.strftime("%m-%d %H:%M")


with st.sidebar:
    # ── 从后端恢复会话列表（仅首次，刷新页面后历史不丢） ──────────────

    if not st.session_state.get("_sessions_restored"):
        restore_sessions_from_backend()
        st.session_state._sessions_restored = True

    # ── 品牌区 ────────────────────────────────────────────────────────────

    st.markdown("### 🌸 花卉助手")
    st.caption("你的 AI 花卉顾问")

    # 新建会话（主操作，置顶）
    if st.button(
        "✨ 新建会话",
        icon=":material/add:",
        width="stretch",
        type="primary",
    ):
        new_session()
        st.rerun()

    st.space("small")

    # ── 系统状态（紧凑一行） ─────────────────────────────────────────────

    if check_backend_health():
        st.badge("后端在线", icon=":material/check_circle:", color="green")
    else:
        st.badge("后端离线，请启动后端", icon=":material/warning:", color="orange")

    st.space("small")

    # ── 会话历史列表 ──────────────────────────────────────────────────────

    sorted_sessions = sorted(
        st.session_state._sessions.items(),
        key=lambda kv: kv[1]["ts"],
        reverse=True,
    )
    current_sid = st.session_state.session_id

    st.markdown(f"**历史会话** · {len(sorted_sessions)}")
    st.caption("点击会话切换，✕ 删除")

    for sid, data in sorted_sessions:
        is_active = sid == current_sid
        title = data["title"]
        ts = _format_relative_time(data.get("ts", ""))

        with st.container(horizontal=True, gap="small", border=is_active):
            if st.button(
                title,
                key=f"hist_{sid}",
                type="primary" if is_active else "secondary",
                help=ts,
            ):
                load_session(sid)
                st.rerun()
            if st.button(
                ":material/close:",
                key=f"del_{sid}",
                help=f"删除「{title}」",
            ):
                delete_session(sid)
                st.rerun()

    st.space("medium")

    # 底部版本与作者信息
    st.caption("花卉识别 AI Agent · v1.1")
    st.caption("👨‍💻 何胤霖")

# ── 页面导航 ──────────────────────────────────────────────────────────────────

page = st.navigation(
    {
        "": [
            st.Page("app_pages/chat.py", title="智能聊天", icon=":material/chat:", default=True),
            st.Page("app_pages/knowledge.py", title="知识搜索", icon=":material/search:"),
            st.Page("app_pages/manage.py", title="知识管理", icon=":material/library_books:"),
            st.Page("app_pages/about.py", title="关于", icon=":material/info:"),
        ],
    },
    position="sidebar",
)

page.run()

# ── 自动保存 ──────────────────────────────────────────────────────────────────
# 每次渲染后，如果消息数量变化了，自动保存到会话存储
sessions = st.session_state._sessions
sid = st.session_state.session_id
msgs = st.session_state.messages
if sid in sessions and len(msgs) != len(sessions[sid].get("messages", [])):
    _save_session()
