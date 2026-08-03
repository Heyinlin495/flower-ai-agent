"""
智能聊天页面

统一聊天窗口，支持文字 + 图片输入
文字聊天使用 SSE 流式输出，逐 token 显示
"""

import streamlit as st
import httpx
import json
import base64
import io
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from config import API_BASE_URL
from api import api_post, api_post_files

logger = logging.getLogger(__name__)

# 消息内展示/缓存的缩略图最长边（原始大图只存在后端 OSS，前端不存原图）
_DISPLAY_MAX_EDGE = 900


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _compress_for_display(image_data: bytes, max_edge: int = _DISPLAY_MAX_EDGE) -> bytes:
    """压缩图片为 JPEG 缩略图：消息展示与缓存用，避免全量原图撑爆内存/传输。

    识别上传也走缩略图（900px 对视觉模型完全够用），失败时退回原图。
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(image_data)) as img:
            img = img.convert("RGB")
            img.thumbnail((max_edge, max_edge), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            return buf.getvalue()
    except Exception:
        return image_data


@st.cache_data(ttl=3600, max_entries=20, show_spinner=False)
def _upload_image_cached(image_data: bytes) -> dict:
    """按图片内容缓存识别结果（同图 1 小时内不重复调用视觉模型，省钱）。

    max_entries=20：限制缓存条目数，防止大量不同图片把进程内存撑爆。
    """
    files = {"image": ("upload.jpg", image_data, "image/jpeg")}
    # 直接透传后端结果（success:false 时 error 可能为 None，前端 _render_recognition_result 有兜底）
    return api_post_files("/api/flower/recognize", files=files)


def upload_image(image_data: bytes, filename: str) -> dict:
    """上传图片识别（结果按内容缓存，图片先压成缩略图再上传）"""
    return _upload_image_cached(_compress_for_display(image_data))


def transcribe_audio(audio_bytes: bytes) -> tuple[str, str]:
    """把录音 WAV 转文字（后端 DashScope Paraformer，前端不持 API Key）。

    Returns:
        (transcript, error): transcript 为识别文本（失败为空串），
        error 为失败原因（成功为空串）。
    """
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    result = api_post(
        "/api/chat/transcribe",
        json={"audio": audio_b64, "format": "wav", "sample_rate": 16000},
        timeout=60,
    )
    if result.get("success"):
        return result.get("text", ""), ""
    return "", result.get("error", "语音识别失败")


def render_flower_card(flower: dict) -> str:
    """渲染花卉识别结果为信息卡片（st.metric 三列 + 文本行）"""
    name = flower.get("name", "未知")
    family = flower.get("family", "未知")
    genus = flower.get("genus", "未知")
    flowering_period = flower.get("flowering_period", "暂无")
    language = flower.get("language", "暂无")
    origin = flower.get("origin", "暂无")
    characteristics = flower.get("characteristics", "暂无")

    lines = [f"**{name}** · {family} / {genus}", ""]
    lines.append(f"**:material/calendar_month: 花期**　{flowering_period}")
    lines.append(f"**:material/favorite: 花语**　{language}")
    lines.append(f"**:material/public: 原产地**　{origin}")
    lines.append("")
    lines.append(f"**:material/description: 特征**　{characteristics}")
    return "\n".join(lines)


def stream_chat_generator(message: str):
    """
    SSE 流式消费生成器，供 st.write_stream 使用。
    连接后端 /api/chat/stream 接口，逐 token 产出 AI 回复。
    """
    payload = {
        "message": message,
        "session_id": st.session_state.session_id,
    }

    try:
        with httpx.stream(
            "POST",
            f"{API_BASE_URL}/api/chat/stream",
            json=payload,
            timeout=120,
        ) as resp:
            if resp.status_code != 200:
                msg = resp.read().decode(errors="ignore")[:300]
                yield f"❌ 错误：HTTP {resp.status_code}\n\n`{msg}`"
                return

            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                mt = data.get("type")
                if mt == "token":
                    yield data.get("content", "")
                elif mt == "status":
                    st.toast(data.get("content", ""), icon="💬")
                elif mt == "error":
                    yield f"❌ {data.get('content', '未知错误')}"
                elif mt == "done":
                    break

    except httpx.ConnectError:
        yield "❌ 无法连接到后端服务，请确保后端已启动"
    except Exception as e:
        yield f"❌ {str(e)}"


def _render_recognition_result(result: dict) -> str:
    """把识别结果字典渲染为回复文本"""
    if not result.get("success"):
        return f"识别失败：{result.get('error') or '未知错误'}"
    flowers = result.get("flowers", [])
    message = result.get("message") or ""
    if not flowers:
        return message or "识别完成，但未能确定花卉种类"
    parts = []
    for i, f in enumerate(flowers, 1):
        header = f"#### 识别结果 {i}" if len(flowers) > 1 else "#### 🌺 识别结果"
        parts.append(f"{header}\n\n{render_flower_card(f)}")
    if message:
        # 模型对用户附带问题的回答（如"怎么养护"）
        parts.append(message)
    parts.append("💡 想了解更多？问我关于这种花的养护知识吧！")
    return "\n\n".join(parts)


def _persist_messages_to_backend(messages: list[dict]):
    """把一轮图片识别消息（含 image_url）异步同步到后端，刷新后历史不丢。

    后台线程执行，失败静默（下次进入该会话时本地缓存仍可兜底）。
    """
    sid = st.session_state.session_id

    def _do():
        api_post(
            "/api/chat/messages",
            json={"session_id": sid, "messages": messages},
            timeout=5,
        )

    threading.Thread(target=_do, daemon=True).start()


def handle_image_recognition_multi(files, user_text: str = ""):
    """处理多张图片识别（并行识别每张，总耗时 ≈ 单张）。

    图片附带的问题（user_text）不在视觉模型里回答（视觉模型只做结构化识别，
    让它同时输出"识别说明+回答"它默认只会给识别说明），识别完成后
    交给文字 LLM 流式回答，见末尾 _ask_followup_question。

    files 兼容两种输入：
    - UploadedFile 对象（输入框 📎 旧调用）
    - (name, bytes) 元组（"+"菜单 JS 文件选择器回传的 base64 解码结果）
    """
    uploaded_images = []
    for f in files:
        if isinstance(f, tuple):
            name, image_data = f
        else:
            image_data = f.getvalue()
            name = f.name
        # 统一压成 JPEG 缩略图：消息展示、缓存、上传识别都用它（省内存/带宽/存储）
        image_data = _compress_for_display(image_data)
        image_b64 = base64.b64encode(image_data).decode()
        uploaded_images.append({
            "data": image_data,
            "name": name,
            "display": f"data:image/jpeg;base64,{image_b64}",
        })

    user_content = user_text if user_text else f"请识别这 {len(uploaded_images)} 张图片中的花卉"
    with st.chat_message("user", avatar=":material/person:"):
        for img in uploaded_images:
            st.image(img["display"], width=220)
        if user_text:
            st.markdown(user_text)

    st.session_state.messages.append({
        "role": "user",
        "content": user_content,
        "image_url": uploaded_images[0]["display"],
    })

    with st.chat_message("assistant", avatar=":material/eco:"):
        with st.spinner(f"正在识别 {len(uploaded_images)} 张图片…"):
            # 并行识别（单张 5-30s，串行会 N 倍时长；4 并发封顶防打爆连接）
            results: list[dict | None] = [None] * len(uploaded_images)
            max_workers = min(len(uploaded_images), 4)
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(upload_image, img["data"], img["name"]): i
                    for i, img in enumerate(uploaded_images)
                }
                for fut, i in futures.items():
                    results[i] = fut.result()

        responses = [
            f"#### 📷 图片 {i}\n\n{_render_recognition_result(r)}"
            for i, r in enumerate(results, 1)
        ]
        response = "\n\n".join(responses)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

    # 同步到后端（用户消息带 image_url，刷新/切会话后图片历史可恢复）
    _persist_messages_to_backend([
        {"role": "user", "content": user_content, "image_url": uploaded_images[0]["display"]},
        {"role": "assistant", "content": response},
    ])

    # 图片附带的问题：识别完成后交给文字 LLM 流式回答
    if user_text:
        _ask_followup_question(results, user_text)


def _ask_followup_question(results: list[dict | None], user_text: str):
    """把识别结果摘要 + 用户问题交给文字 LLM（qwen-plus）流式回答。

    视觉模型负责结构化识别，问答是文字模型强项；两者分离后
    图片下附带的问题（"怎么养护"等）才能得到真正回答。
    """
    all_names = []
    for r in results:
        if r and r.get("success"):
            all_names.extend(f.get("name", "") for f in r.get("flowers", []))
    names_str = "、".join(n for n in all_names if n) or "多种花卉"
    followup = f"我上传了一张花卉图片，识别结果是：{names_str}。请针对我的问题回答：{user_text}"
    handle_text_chat(followup)


def handle_text_chat(user_message: str):
    """处理文字聊天（流式输出）"""
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})

    with st.chat_message("assistant", avatar=":material/eco:"):
        response = st.write_stream(stream_chat_generator(user_message))

    st.session_state.messages.append({"role": "assistant", "content": response})


# ── 初始化 ──────────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "_pending_images" not in st.session_state:
    st.session_state._pending_images = []


# ── 页面渲染 ─────────────────────────────────────────────────────────────────

# 顶部标题区
with st.container(horizontal_alignment="center"):
    st.title("🌸 花卉识别 AI 助手", text_alignment="center")
    st.caption("上传花卉图片或输入问题，AI 为您提供专业识别和养护建议", text_alignment="center")

# 消息计数（清除聊天已移至左侧栏）
count = len(st.session_state.messages)

with st.container(horizontal=True, horizontal_alignment="right", gap="small"):
    if count:
        st.caption(f"共 {count} 条消息")

# 空对话：欢迎页（紧凑，输入框首屏可见）
if not st.session_state.messages:
    st.space("small")

    # 功能卡片收进可展开区，避免空态撑满两屏
    with st.expander("了解功能", icon=":material/lightbulb:", expanded=False):
        c1, c2, c3 = st.columns(3)
        feature_cards = [
            (
                c1,
                ":material/image_search:",
                "识别花卉",
                "上传花卉图片\nAI 自动识别花名、科属、\n特征、花期、花语",
            ),
            (
                c2,
                ":material/chat_bubble:",
                "智能问答",
                "输入花卉相关问题\n获取养护建议、种植技巧\n病虫害防治",
            ),
            (
                c3,
                ":material/library_books:",
                "知识检索",
                "直达知识库\n搜索花卉养护资料\n查看相关度评分",
            ),
        ]
        for col, icon, title, desc in feature_cards:
            with col.container(border=True, height="stretch"):
                st.markdown(icon)
                st.markdown(f"**{title}**")
                st.caption(desc)

    st.space("small")

    # 建议问题（点击即提问，常驻在输入框上方）
    suggestions = [
        "🌹 玫瑰怎么养护？",
        "🌻 向日葵的花语是什么？",
        "🌷 郁金香适合什么温度？",
    ]
    picked = st.pills(
        "试试这些问题",
        suggestions,
        label_visibility="collapsed",
        key="welcome_pills",
    )
    if picked:
        handle_text_chat(picked)
        st.rerun()


# 聊天历史
for msg in st.session_state.messages:
    role = msg["role"]
    avatar_kw = (
        {"avatar": ":material/person:"} if role == "user" else {"avatar": ":material/eco:"}
    )
    with st.chat_message(role, **avatar_kw):
        img = msg.get("image_url")
        if img:
            st.image(img, width=220)
        if msg.get("content"):
            st.markdown(msg["content"])

# 聊天输入框（支持文字 / 图片 / 语音；图片用输入框原生 📎 上传，
# 和文字一起点发送键发送，完全一体）
chat_input = st.chat_input(
    "输入消息，或点 📎 上传图片后发送…",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "webp"],
    accept_audio=True,
    submit_mode="stop",
    key="chat_input_key",
)

if chat_input:
    user_text = chat_input.text if chat_input.text else ""
    audio_file = getattr(chat_input, "audio", None)
    uploaded_files = getattr(chat_input, "files", None) or []

    # 语音识别：成功直接发送（streamlit widget key 不能回填，且符合主流 App 松手即发）
    if audio_file:
        with st.spinner("正在识别语音…"):
            transcript, err = transcribe_audio(audio_file.getvalue())
        if transcript:
            handle_text_chat(transcript)
            st.rerun()
        else:
            st.warning(f"语音识别失败：{err or '请手动输入或重试'}")

    # 有图片（输入框 📎 上传）：文字（可选）+ 图片一起发送识别
    elif uploaded_files:
        all_files = [(f.name, f.getvalue()) for f in uploaded_files]
        handle_image_recognition_multi(all_files, user_text)
        st.rerun()

    elif user_text:
        handle_text_chat(user_text)
        st.rerun()

