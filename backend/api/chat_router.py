"""
花卉识别 AI Agent - 聊天 API 路由

提供聊天相关的 API 接口，支持普通响应和 SSE 流式响应
"""

import asyncio
import base64
import json
import logging
import tempfile
import traceback
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
from pydantic import BaseModel, Field

from ..models.chat import ChatRequest, ChatResponse
from ..agent.flower_agent import flower_agent
from ..agent.session_store import session_store
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["聊天"])


def _error_detail(msg: str, max_len: int = 200) -> str:
    """错误响应统一格式：截断的简短消息（完整堆栈只进日志）"""
    return msg[:max_len] if msg else "处理失败，请稍后重试"


# ── 消息持久化（前端图片识别回合不走 Agent，需单独落盘） ─────────────────

class PersistMessage(BaseModel):
    """待持久化的单条消息"""
    role: str = Field(description="消息角色: user / assistant")
    content: str = Field(default="", description="消息文本内容")
    image_url: Optional[str] = Field(default=None, description="图片 URL（如有）")


class PersistMessagesRequest(BaseModel):
    """批量持久化消息请求"""
    session_id: str = Field(description="会话 ID")
    messages: List[PersistMessage] = Field(description="消息列表")


@router.post("/messages")
async def persist_messages(request: PersistMessagesRequest):
    """
    批量持久化会话消息（前端图片识别回合调用，刷新后历史不丢）

    Returns:
        dict: 操作结果
    """
    try:
        msgs = [
            {"role": m.role, "content": m.content, "image_url": m.image_url}
            for m in request.messages
            if m.role in ("user", "assistant")
        ]
        if not msgs:
            raise HTTPException(status_code=400, detail="消息列表为空或角色不合法")
        session_store.add_messages(request.session_id, msgs)
        return {"success": True, "message": f"已持久化 {len(msgs)} 条消息"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"持久化消息异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="持久化消息失败，请稍后重试")


# ── 语音识别（DashScope Paraformer，移出前端进程避免阻塞 UI） ─────────────

class TranscribeRequest(BaseModel):
    """语音识别请求"""
    audio: str = Field(description="音频数据（base64 编码）")
    format: str = Field(default="wav", description="音频格式")
    sample_rate: int = Field(default=16000, description="采样率")


class TranscribeResponse(BaseModel):
    """语音识别响应"""
    success: bool
    text: str = Field(default="", description="识别文本")
    error: str = Field(default="", description="失败原因（成功时为空）")


def _transcribe_sync(audio_b64: str, audio_format: str, sample_rate: int) -> dict:
    """同步语音识别（dashscope 阻塞调用，放进线程池执行）"""
    if not settings.DASHSCOPE_API_KEY:
        return {"success": False, "text": "", "error": "缺少 DashScope API Key（.env 中 DASHSCOPE_API_KEY）"}
    try:
        from dashscope.audio.asr import Recognition
        from dashscope.audio.asr.recognition import RecognitionCallback

        audio_bytes = base64.b64decode(audio_b64)
        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            # Recognition 构造必须传 callback（实时流式接口），
            # 离线文件识别用空 callback 即可（call() 处理完整文件后一次性返回）
            rec = Recognition(
                model="paraformer-realtime-v2",
                format=audio_format,
                sample_rate=sample_rate,
                callback=RecognitionCallback(),
                api_key=settings.DASHSCOPE_API_KEY,
            )
            result = rec.call(tmp_path)
            if result and getattr(result, "status_code", 500) == 200:
                sentences = result.get_sentence() or []
                text = "".join(s.get("text", "") for s in sentences)
                if text:
                    return {"success": True, "text": text, "error": ""}
                return {"success": False, "text": "", "error": "未能识别到语音内容，请重新录音"}
            code = getattr(result, "code", "") or ""
            msg = getattr(result, "message", "") or ""
            logger.warning(f"语音识别失败: code={code}, message={msg}")
            return {"success": False, "text": "", "error": msg or "语音识别失败"}
        finally:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"语音识别异常: {e}")
        return {"success": False, "text": "", "error": f"语音识别服务异常：{e}"}


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: TranscribeRequest):
    """
    语音转文字（DashScope Paraformer）

    前端录音文件以 base64 上传，阻塞调用在线程池执行，不卡 event loop。

    Args:
        request: base64 音频 + 格式参数

    Returns:
        TranscribeResponse: 识别文本或错误原因
    """
    try:
        result = await asyncio.to_thread(
            _transcribe_sync, request.audio, request.format, request.sample_rate
        )
        return TranscribeResponse(**result)
    except Exception as e:
        logger.error(f"语音识别路由异常: {e}\n{traceback.format_exc()}")
        return TranscribeResponse(success=False, text="", error="语音识别服务异常，请稍后重试")


@router.post("/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送聊天消息

    接收用户消息和可选的图片URL，调用 Agent 处理并返回回复

    Args:
        request: 聊天请求

    Returns:
        ChatResponse: 聊天响应
    """
    try:
        logger.info(f"收到聊天消息: {request.message[:50]}...")

        # 调用 Agent 处理消息（异步版，避免阻塞 event loop）
        result = await flower_agent.achat(
            message=request.message,
            session_id=request.session_id,
            image_url=request.image_url
        )

        if result["success"]:
            return ChatResponse(
                success=True,
                message=result["message"],
                session_id=result["session_id"],
                image_url=result.get("image_url"),
                timestamp=result["timestamp"]
            )
        # 业务失败 → 200 + success:false（与知识库接口风格一致，协议错误才用 4xx/5xx）
        logger.error(f"聊天处理失败: {result.get('error')}")
        return ChatResponse(
            success=False,
            message=_error_detail(result.get("error", "处理消息失败")),
            session_id=request.session_id or "",
            timestamp=result.get("timestamp"),
        )

    except Exception as e:
        logger.error(f"聊天消息处理异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="聊天处理失败，请稍后重试")


@router.post("/stream")
async def stream_message(request: ChatRequest):
    """
    流式聊天接口（SSE）

    返回 Server-Sent Events 流，逐 token 推送 AI 回复。

    事件格式：
        event: message
        data: {"type": "token", "content": "你"}

        event: message
        data: {"type": "status", "content": "正在搜索知识库…"}

        event: message
        data: {"type": "done", "message": "完整回复", "session_id": "..."}

        event: message
        data: {"type": "error", "content": "错误信息"}
    """
    try:
        logger.info(f"收到流式聊天消息: {request.message[:50]}...")

        async def event_generator():
            async for item in flower_agent.stream_chat(
                message=request.message,
                session_id=request.session_id,
                image_url=request.image_url,
            ):
                data_json = json.dumps(item, ensure_ascii=False)
                yield f"event: message\ndata: {data_json}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"流式聊天异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="流式聊天启动失败，请稍后重试")


@router.get("/sessions")
async def list_chat_sessions():
    """
    列出所有会话

    Returns:
        dict: 会话列表（含标题、消息数、更新时间）
    """
    try:
        sessions = flower_agent.list_sessions()
        return {
            "success": True,
            "sessions": sessions,
            "total": len(sessions)
        }
    except Exception as e:
        logger.error(f"列出会话异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="列出会话失败，请稍后重试")


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    """
    获取聊天历史

    Args:
        session_id: 会话ID

    Returns:
        dict: 聊天历史
    """
    try:
        history = flower_agent.get_session_history(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "messages": history,
            "total": len(history)
        }
    except Exception as e:
        logger.error(f"获取聊天历史异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="获取聊天历史失败，请稍后重试")


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str):
    """
    清除聊天历史

    Args:
        session_id: 会话ID

    Returns:
        dict: 操作结果
    """
    try:
        success = flower_agent.clear_session(session_id)
        return {
            "success": success,
            "message": "聊天历史已清除" if success else "会话不存在"
        }
    except Exception as e:
        logger.error(f"清除聊天历史异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="清除聊天历史失败，请稍后重试")
