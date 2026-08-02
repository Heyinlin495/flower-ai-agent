"""
花卉识别 AI Agent - 聊天数据模型

定义聊天请求和响应的数据结构
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """
    消息角色枚举
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """
    聊天消息模型
    """
    role: MessageRole = Field(
        description="消息角色"
    )
    content: str = Field(
        description="消息内容"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="消息时间戳"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="图片URL（如果有）"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="元数据"
    )


class ChatRequest(BaseModel):
    """
    聊天请求模型
    """
    message: str = Field(
        description="用户消息"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="会话ID"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="图片URL（如果用户上传了图片）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "这是什么花？",
                "session_id": "session_123",
                "image_url": "https://example.com/flower.jpg"
            }
        }


class ChatResponse(BaseModel):
    """
    聊天响应模型
    """
    success: bool = Field(
        description="请求是否成功"
    )
    message: str = Field(
        description="AI回复消息"
    )
    session_id: str = Field(
        description="会话ID"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="图片URL"
    )
    sources: Optional[List[str]] = Field(
        default=None,
        description="知识库来源"
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="响应时间戳"
    )
