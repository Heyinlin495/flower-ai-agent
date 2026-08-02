"""
智能聊天页面

统一聊天窗口，支持文字 + 图片输入
文字聊天使用 SSE 流式输出，逐 token 显示
"""

import streamlit as st
import requests
import httpx
import json
import base64

from config import API_BASE_URL


# ── 工具函数 ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _upload_image_cached(image_data: bytes) -> dict:
    """按图片内容缓存识别结果（同图 1 小时内不重复调用视觉模型，省钱）"""
    try:
        files = {"image": ("upload.jpg", image_data, "image/jpeg")}
        resp = requests.post(f"{API_BASE_URL}/api/flower/recognize", files=files, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return {"success": False, "error": f"识别失败: {detail}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def upload_image(image_data: bytes, filename: str) -> dict:
    """上传图片识别（结果按内容缓存）"""
    return _upload_image_cached(image_data)


@st.cache_data(ttl=3600, show_spinner=False)
def _recognize_url_cached(image_url: str) -> dict:
    """按 URL 缓存识别结果"""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/flower/recognize-url",
            data={"image_url": image_url},
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json()
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        return {"success": False, "error": f"识别失败: {detail}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def recognize_image_url(image_url: str) -> dict:
    """通过图片 URL 识别（结果按 URL 缓存）"""
    return _recognize_url_cached(image_url)


def transcribe_audio(audio_bytes: bytes) -> str:
    """把录音 WAV 转文字（DashScope Paraformer，失败返回空串）"""
    import os
    import tempfile

    try:
        from dashscope.audio.asr import Recognition

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            rec = Recognition(
                model="paraformer-realtime-v2",
                format="wav",
                sample_rate=16000,
            )
            result = rec.call(tmp_path)
            if result and getattr(result, "status_code", 500) == 200:
                sentences = result.get_sentence() or []
                return "".join(s.get("text", "") for s in sentences)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except Exception:
        pass
    return ""


def render_flower_table(flower: dict) -> str:
    """渲染花卉识别结果表格"""
    rows = [
        ("花名", flower.get("name", "未知")),
        ("科属", f"{flower.get('family', '未知')} / {flower.get('genus', '未知')}"),
        ("特征", flower.get("characteristics", "暂无")),
        ("花期", flower.get("flowering_period", "暂无")),
        ("花语", flower.get("language", "暂无")),
        ("原产地", flower.get("origin", "暂无")),
    ]
    lines = ["| 项目 | 信息 |", "|------|------|"]
    for k, v in rows:
        lines.append(f"| **{k}** | {v} |")
    return "\n".join(lines)


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
    if not flowers:
        return result.get("message", "识别完成，但未能确定花卉种类")
    parts = []
    for i, f in enumerate(flowers, 1):
        header = f"#### 识别结果 {i}" if len(flowers) > 1 else "#### 🌺 识别结果"
        parts.append(f"{header}\n\n{render_flower_card(f)}")
    parts.append("💡 想了解更多？问我关于这种花的养护知识吧！")
    return "\n\n".join(parts)


def handle_image_recognition(image_data: bytes, filename: str, user_text: str = ""):
    """处理单张图片识别（上传文件）"""
    image_b64 = base64.b64encode(image_data).decode()
    image_display = f"data:image/jpeg;base64,{image_b64}"
    user_content = user_text if user_text else "请识别这张图片中的花卉"

    with st.chat_message("user", avatar=":material/person:"):
        st.image(image_display, width=220)
        if user_text:
            st.markdown(user_text)

    st.session_state.messages.append({
        "role": "user",
        "content": user_content,
        "image_url": image_display,
    })

    with st.chat_message("assistant", avatar=":material/eco:"):
        with st.spinner("正在识别花卉…"):
            result = upload_image(image_data, filename)

        response = _render_recognition_result(result)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


def handle_image_recognition_multi(files, user_text: str = ""):
    """处理多张图片识别（循环识别每张）"""
    uploaded_images = []
    for f in files:
        image_data = f.getvalue()
        image_b64 = base64.b64encode(image_data).decode()
        uploaded_images.append({
            "data": image_data,
            "name": f.name,
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
        responses = []
        for i, img in enumerate(uploaded_images, 1):
            with st.spinner(f"正在识别第 {i}/{len(uploaded_images)} 张…"):
                result = upload_image(img["data"], img["name"])
            responses.append(f"#### 📷 图片 {i}\n\n{_render_recognition_result(result)}")
        response = "\n\n".join(responses)

        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


def handle_image_url_recognition(image_url: str, user_text: str = ""):
    """处理图片 URL 识别"""
    user_content = user_text if user_text else f"请识别这张图片中的花卉（{image_url}）"
    with st.chat_message("user", avatar=":material/person:"):
        if user_text:
            st.markdown(user_text)
        st.markdown(f"🔗 [{image_url}]({image_url})")

    st.session_state.messages.append({
        "role": "user",
        "content": user_content,
        "image_url": image_url,
    })

    with st.chat_message("assistant", avatar=":material/eco:"):
        with st.spinner("正在识别图片…"):
            result = recognize_image_url(image_url)

        response = _render_recognition_result(result)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


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


# ── 页面渲染 ─────────────────────────────────────────────────────────────────

# 顶部标题区
with st.container(horizontal_alignment="center"):
    st.title("🌸 花卉识别 AI 助手", text_alignment="center")
    st.caption("上传花卉图片或输入问题，AI 为您提供专业识别和养护建议", text_alignment="center")

# 空对话：欢迎页
if not st.session_state.messages:
    st.space("medium")

    # 功能卡片（三列等高）
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

    st.space("medium")

    # 建议问题（点击即提问）
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

# 输入区操作栏
count = len(st.session_state.messages)
with st.container(horizontal=True, horizontal_alignment="right", gap="small"):
    if count:
        st.caption(f"共 {count} 条消息")
    if st.button("清除聊天", icon=":material/delete:", disabled=not count):
        st.session_state.messages = []
        st.rerun()

# 图片 URL 识别弹窗（@st.dialog 装饰器模式）
@st.dialog("通过图片链接识别")
def url_recognition_dialog():
    st.caption("粘贴图片 URL，AI 将识别其中的花卉")
    url_input = st.text_input(
        "图片链接",
        placeholder="https://example.com/flower.jpg",
        label_visibility="collapsed",
    )
    col_url1, col_url2 = st.columns(2)
    with col_url1:
        if st.button("识别", type="primary", width="stretch"):
            if url_input:
                # 先存入 session_state，重跑后统一处理（避免 rerun 丢失识别结果）
                st.session_state._pending_url_recognition = url_input
                st.rerun()
            else:
                st.warning("请先输入图片链接")
    with col_url2:
        if st.button("取消", width="stretch"):
            st.rerun()


# 输入区操作栏：图片 URL 识别入口
with st.container(horizontal=True, horizontal_alignment="right", gap="small"):
    if st.button("识别图片链接", icon=":material/link:", help="通过图片 URL 直接识别"):
        url_recognition_dialog()

# 聊天输入框（支持文字 / 图片 / 语音；生成中按钮变为"停止"）
chat_input = st.chat_input(
    "输入消息、上传图片或按住🎤录音…",
    accept_file=True,
    file_type=["jpg", "jpeg", "png", "webp"],
    accept_audio=True,
    submit_mode="stop",
    key="chat_input_key",
)

if chat_input:
    user_text = chat_input.text if chat_input.text else ""
    uploaded_files = chat_input.files if chat_input.files else []
    audio_file = getattr(chat_input, "audio", None)

    # 语音优先处理：转文字后填回输入框，用户确认发送
    if audio_file:
        with st.spinner("正在识别语音…"):
            transcript = transcribe_audio(audio_file.getvalue())
        if transcript:
            st.session_state.chat_input_key = transcript
            st.toast("语音已识别，点击发送 🎤", icon=":material/record_voice_over:")
            st.rerun()
        else:
            st.warning("语音识别失败，请手动输入或重试")

    elif uploaded_files:
        if len(uploaded_files) > 1:
            handle_image_recognition_multi(uploaded_files, user_text)
        else:
            image_data = uploaded_files[0].getvalue()
            handle_image_recognition(image_data, uploaded_files[0].name, user_text)
        st.rerun()
    elif user_text:
        handle_text_chat(user_text)
        st.rerun()

# 处理待识别的图片 URL（弹窗里存入）
if st.session_state.get("_pending_url_recognition"):
    pending_url = st.session_state._pending_url_recognition
    del st.session_state["_pending_url_recognition"]
    handle_image_url_recognition(pending_url)
    st.rerun()
