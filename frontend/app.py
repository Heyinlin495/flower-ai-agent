"""
花卉识别 AI Agent - Streamlit 前端应用

多页面布局：聊天、知识搜索、知识管理、关于
侧边栏包含会话历史、系统状态和操作按钮

Author: 何胤霖 (Yinlin He)
"""

import streamlit as st
import requests
import time
import json
from datetime import datetime
from pathlib import Path

from config import API_BASE_URL, APP_VERSION
from api import auth_headers

# 侧边栏会话列表组件资产（ChatGPT 风格，JS 渲染）
_SESSION_CSS = (Path(__file__).parent / "assets" / "session_sidebar.css").read_text(encoding="utf-8")
_SESSION_HTML = (Path(__file__).parent / "assets" / "session_sidebar.html").read_text(encoding="utf-8")
_SESSION_JS = (Path(__file__).parent / "assets" / "session_sidebar.js").read_text(encoding="utf-8")

# CCv2 组件：isolate_styles=True 时 HTML/CSS/JS 都在组件 shadow root 内，
# CSS 作用于组件内部元素（#sessionSidebarRoot .session-*），不会污染全局。
_session_list = st.components.v2.component(
    "session_sidebar_list",
    html=_SESSION_HTML,
    css=_SESSION_CSS,
    js=_SESSION_JS,
    isolate_styles=True,
)

# 页面配置
st.set_page_config(
    page_title="花卉识别 AI 助手",
    page_icon="🌸",
    layout="centered",
)

# ── 会话历史管理 ─────────────────────────────────────────────────────────────

MAX_SESSIONS = 20  # 最多保留 20 个历史会话

# 后台预取缓存：{sid: messages}。后台线程拉取、主线程合并进 _sessions，
# 避免跨线程写 st.session_state（SessionState 非线程安全）。
_prefetch_cache: dict[str, list] = {}


def _make_session_id() -> str:
    """生成唯一会话 ID（时间戳 + 随机后缀，避免同一秒内重复）"""
    import uuid
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


if "_sessions" not in st.session_state:
    st.session_state._sessions = {}  # {sid: {"title": str, "messages": list, "ts": str}}
if "session_id" not in st.session_state:
    sid = _make_session_id()
    st.session_state.session_id = sid
    st.session_state._sessions[sid] = {"title": "新会话", "messages": [], "ts": datetime.now().isoformat()}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "_pending_images" not in st.session_state:
    st.session_state._pending_images = []  # 输入框上方"待发送"图片预览（由 chat.py 维护）


def _save_session(touch: bool = True):
    """保存当前消息到会话存储，并自动提取标题。

    touch=False 时只保存消息内容、不刷新 ts：切换/新建会话时调用，
    避免"只是被保存"就让会话跳到列表顶部（用户没在该会话发消息，
    不该算最新活跃）。只有真正产生新消息（auto-save / 发消息缓存）
    才刷新 ts，会话才会跳顶。
    """
    sid = st.session_state.session_id
    msgs = st.session_state.messages
    title = "新会话"
    for m in msgs:
        if m["role"] == "user" and not m.get("image_url"):
            title = m["content"][:30]
            break
    old_ts = st.session_state._sessions.get(sid, {}).get("ts")
    st.session_state._sessions[sid] = {
        "title": title,
        "messages": list(msgs),
        "ts": datetime.now().isoformat() if touch else (old_ts or datetime.now().isoformat()),
    }


def load_session(sid: str):
    """切换到指定会话。

    本地缓存有消息就直接秒开（刚聊过的会话缓存就是最新的），
    只有缓存为空（刷新后恢复的会话）才同步拉后端，并把结果写回缓存，
    保证下次切换不再卡在网络请求上。
    """
    if sid == st.session_state.session_id:
        return
    data = st.session_state._sessions.get(sid)
    if data is None:
        # 防御：目标会话不存在（可能刚被删除，触发值残留）→ 忽略
        return
    # 当前会话有消息才保存（避免空会话产生多余记录）；
    # touch=False：切换只是保存内容，不刷新 ts，会话顺序不因切换而变
    if st.session_state.messages:
        _save_session(touch=False)
    st.session_state.session_id = sid
    cached = list(data.get("messages") or [])
    if cached:
        # 本地缓存是最新的：直接秒开，不发网络请求
        st.session_state.messages = cached
        return
    # 缓存为空：从后端拉一次（失败时退回空，避免显示别的会话内容）
    backend_msgs = fetch_backend_history(sid)
    st.session_state.messages = list(backend_msgs) if backend_msgs else []
    if backend_msgs:
        data["messages"] = list(backend_msgs)


def new_session():
    """创建新会话（不保存当前空会话，避免产生多余的"新会话"记录）"""
    # 当前会话有消息才保存（避免空会话也落盘成一条记录）；
    # touch=False：新建只是保存内容，不刷新 ts，旧会话不因"新建"而跳顶
    if st.session_state.messages:
        _save_session(touch=False)
    sid = _make_session_id()
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
    """删除指定会话（同时清除后端历史，不切会话避免网络等待卡顿）"""
    sessions = st.session_state._sessions
    if sid in sessions:
        del sessions[sid]
    # 同步删除后端会话历史（静默，不阻塞 UI）
    clear_backend_history(sid)
    # 如果删除的是当前会话：重置为全新空会话（无网络请求，秒开）
    # 不复用 load_session（内部 fetch_backend_history 同步请求会卡顿）
    # 全删光时：直接重置当前会话为空，不再 new_session（避免"新建两个"）
    if sid == st.session_state.session_id:
        if sessions:
            # 有剩余会话：直接切到最新的；缓存有消息就秒开，
            # 缓存为空（刷新恢复的会话）才拉后端，避免删除后显示空聊天
            latest = max(sessions.keys(), key=lambda k: sessions[k]["ts"])
            st.session_state.session_id = latest
            cached = list(sessions[latest].get("messages") or [])
            st.session_state.messages = cached if cached else fetch_backend_history(latest)
        else:
            # 全删光了：当前会话重置为全新空会话
            st.session_state.session_id = _make_session_id()
            st.session_state.messages = []


def clear_current_messages():
    """清空当前会话消息（不删除会话）"""
    st.session_state.messages = []
    st.session_state._pending_images = []


# ── API 工具 ──────────────────────────────────────────────────────────────────

_HEALTH_CACHE_TTL = 30


def check_backend_health() -> bool:
    """检查后端服务是否在线（结果缓存 30 秒）"""
    now = time.time()
    cache = st.session_state.get("_health_cache")
    if cache and (now - cache["ts"] < _HEALTH_CACHE_TTL):
        return cache["ok"]
    try:
        resp = requests.get(f"{API_BASE_URL}/health", headers=auth_headers(), timeout=1)
        ok = resp.status_code == 200
    except Exception:
        ok = False
    st.session_state["_health_cache"] = {"ts": now, "ok": ok}
    return ok


def fetch_backend_history(session_id: str) -> list:
    """从后端拉取会话历史（失败返回空列表；只在缓存为空时调用，
    超时放宽到 5s 避免慢网络下丢失历史，不影响正常切换速度）"""
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/chat/history/{session_id}",
            headers=auth_headers(),
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("messages", [])
    except Exception:
        pass
    return []


def _prefetch_sessions_async():
    """首屏后后台预取所有会话历史，填充本地缓存。

    刷新页面后恢复的会话缓存是空的，若不预取，用户第一次点击该会话
    时要同步等网络（即使已修复 localhost 回退也还有几十毫秒）。
    这里把拉取放到后台线程，结果存 _prefetch_cache，由主线程在下次
    rerun 时合并进 _sessions，点击时即缓存命中、秒开。
    """
    import threading

    def _do():
        sids = list(st.session_state._sessions.keys())
        for sid in sids:
            if sid in _prefetch_cache:
                continue
            msgs = fetch_backend_history(sid)
            if msgs:
                _prefetch_cache[sid] = msgs

    threading.Thread(target=_do, daemon=True).start()


def _merge_prefetch_cache():
    """主线程把已完成的预取结果合并进 _sessions（只补空缓存）"""
    for sid, msgs in list(_prefetch_cache.items()):
        data = st.session_state._sessions.get(sid)
        if data is not None and not data.get("messages") and msgs:
            data["messages"] = list(msgs)


def restore_sessions_from_backend():
    """把后端持久化的会话合并进本地 _sessions（保留本地已存在项，合并空"新会话"）"""
    try:
        resp = requests.get(f"{API_BASE_URL}/api/chat/sessions", headers=auth_headers(), timeout=5)
        if resp.status_code != 200:
            return
        # 本地已有的空"新会话"：后端恢复时不再重复添加
        local_has_empty_new = any(
            v["title"] == "新会话" and not v["messages"]
            for v in st.session_state._sessions.values()
        )
        for s in resp.json().get("sessions", []):
            sid = s["id"]
            if sid in st.session_state._sessions:
                continue
            title = s["title"] or "新会话"
            # 后端也是空"新会话"，且本地已有空新会话 → 跳过（避免重复）
            if title == "新会话" and local_has_empty_new:
                continue
            st.session_state._sessions[sid] = {
                "title": title,
                "messages": [],
                "ts": s["updated_at"] or s["created_at"],
            }
    except Exception:
        pass


def clear_backend_history(session_id: str):
    """删除后端会话历史（后台线程执行，不阻塞 UI；失败静默）"""
    import threading

    def _do_delete():
        try:
            requests.delete(
                f"{API_BASE_URL}/api/chat/history/{session_id}",
                headers=auth_headers(),
                timeout=2,
            )
        except Exception:
            pass

    threading.Thread(target=_do_delete, daemon=True).start()


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


# ── 侧边栏（品牌 + 会话管理） ───────────────────────────────────────────

# 会话列表可滚动（限制高度，避免长列表撑爆侧栏）
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
        max-height: 320px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: rgba(0,0,0,0.15) transparent;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    # ── 从后端恢复会话列表（仅首次，刷新页面后历史不丢） ──────────────

    if not st.session_state.get("_sessions_restored"):
        restore_sessions_from_backend()
        st.session_state._sessions_restored = True
        _prefetch_sessions_async()
    else:
        _merge_prefetch_cache()

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

    # 清空当前会话消息（不删除会话）
    if st.button(
        "清除聊天",
        icon=":material/delete:",
        width="stretch",
        disabled=not st.session_state.messages,
    ):
        clear_current_messages()
        st.rerun()

    st.divider()

    # ── 系统状态（紧凑一行） ─────────────────────────────────────────────

    if check_backend_health():
        st.badge("后端在线", icon=":material/check_circle:", color="green")
    else:
        st.badge("后端离线，请启动后端", icon=":material/warning:", color="orange")

    st.space("small")

    # ── 会话历史列表（ChatGPT 风格，JS 渲染 + 回传） ─────────────────────

    sorted_sessions = sorted(
        st.session_state._sessions.items(),
        key=lambda kv: kv[1]["ts"],
        reverse=True,
    )
    current_sid = st.session_state.session_id

    st.markdown("**历史会话**")

    # 注入会话数据给 JS 组件
    _session_data = [
        {
            "id": sid,
            "title": data.get("title", "新会话"),
            "ts": _format_relative_time(data.get("ts", "")),
        }
        for sid, data in sorted_sessions
    ]
    # CCv2 触发值（select/delete）在触发后的下一次 rerun 仍会保留一次
    # （不会立即清除），若每次 rerun 都处理会"连坐"重复删除。
    # 这里用 session_state 记录已消费的触发 sid，同一 sid 只处理一次。
    if "_consumed_trigger" not in st.session_state:
        st.session_state._consumed_trigger = {"select": None, "delete": None}

    _session_result = _session_list(
        key="session_sidebar_v1",
        data={"sessions": _session_data, "current_sid": current_sid},
        on_select_change=lambda: None,
        on_delete_change=lambda: None,
    )
    _sel = _session_result.select
    _del = _session_result.delete

    # 消费触发值（去重：同一 sid 不重复处理）
    _sel_value = _sel.get("value") if isinstance(_sel, dict) else None
    if _sel_value and _sel_value != st.session_state._consumed_trigger["select"]:
        st.session_state._consumed_trigger["select"] = _sel_value
        load_session(_sel_value)
        st.rerun()

    _del_value = _del.get("value") if isinstance(_del, dict) else None
    if _del_value and _del_value != st.session_state._consumed_trigger["delete"]:
        st.session_state._consumed_trigger["delete"] = _del_value
        delete_session(_del_value)
        st.rerun()

    st.space("medium")

    # 底部版本与作者信息
    st.caption(f"花卉识别 AI Agent · {APP_VERSION}")
    st.caption("👨‍💻 何胤霖 ❤️ 👧 淋淋大王")

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
