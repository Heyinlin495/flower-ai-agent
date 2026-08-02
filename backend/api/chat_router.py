"""
花卉识别 AI Agent - 聊天 API 路由

提供聊天相关的 API 接口，支持普通响应和 SSE 流式响应
"""

import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional

from ..models.chat import ChatRequest, ChatResponse
from ..agent.flower_agent import flower_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["聊天"])


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

        # 调用 Agent 处理消息
        result = flower_agent.chat(
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
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "处理消息失败")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天消息处理异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"流式聊天异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"列出会话异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"获取聊天历史异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"清除聊天历史异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_agent():
    """
    测试 Agent 是否正常工作

    Returns:
        dict: 测试结果
    """
    try:
        result = flower_agent.chat(
            message="你好，请介绍一下你自己",
            session_id="test_session"
        )
        return {
            "success": True,
            "message": "Agent 测试成功",
            "response": result
        }
    except Exception as e:
        logger.error(f"Agent 测试失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }
