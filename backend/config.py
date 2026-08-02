"""
花卉识别 AI Agent - 配置管理模块

负责加载环境变量和应用配置
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """
    应用配置类
    使用 pydantic-settings 自动从环境变量加载配置
    """

    # ==================== 阿里云 DashScope 配置 ====================
    DASHSCOPE_API_KEY: str = Field(
        default="",
        description="阿里云百炼大模型平台 API Key"
    )
    DASHSCOPE_BASE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="DashScope OpenAI 兼容接口地址 (用于主 Agent)"
    )
    DASHSCOPE_ANTHROPIC_URL: str = Field(
        default="https://dashscope.aliyuncs.com/apps/anthropic",
        description="DashScope Anthropic 兼容接口地址 (用于视觉模型)"
    )

    # ==================== 阿里云 OSS 配置 ====================
    OSS_ACCESS_KEY_ID: str = Field(
        default="",
        description="OSS Access Key ID"
    )
    OSS_ACCESS_KEY_SECRET: str = Field(
        default="",
        description="OSS Access Key Secret"
    )
    OSS_BUCKET_NAME: str = Field(
        default="",
        description="OSS Bucket 名称"
    )
    OSS_ENDPOINT: str = Field(
        default="oss-cn-hangzhou.aliyuncs.com",
        description="OSS Endpoint"
    )
    OSS_REGION: str = Field(
        default="cn-hangzhou",
        description="OSS 区域"
    )

    # ==================== 向量数据库配置 ====================
    VECTOR_DB_TYPE: str = Field(
        default="chroma",
        description="向量数据库类型: chroma 或 faiss"
    )
    CHROMA_PERSIST_DIR: str = Field(
        default="./data/chroma_db",
        description="ChromaDB 持久化目录"
    )

    # ==================== 模型配置 ====================
    LLM_MODEL_NAME: str = Field(
        default="qwen-plus",
        description="大语言模型名称"
    )
    VISION_MODEL_NAME: str = Field(
        default="qwen-vl-max",
        description="视觉模型名称"
    )
    EMBEDDING_MODEL_NAME: str = Field(
        default="text-embedding-v3",
        description="Embedding 模型名称"
    )

    # ==================== 应用配置 ====================
    APP_HOST: str = Field(
        default="0.0.0.0",
        description="应用监听地址"
    )
    APP_PORT: int = Field(
        default=8000,
        description="应用监听端口"
    )
    DEBUG: bool = Field(
        default=True,
        description="调试模式"
    )
    # CORS 允许来源（逗号分隔，.env 可覆盖；默认本地开发来源）
    CORS_ALLOW_ORIGINS: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501",
        description="允许的跨域来源，逗号分隔"
    )

    @property
    def cors_origins_list(self) -> list:
        """CORS 来源列表（解析逗号分隔字符串，* 原样保留）"""
        raw = self.CORS_ALLOW_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    # ==================== 路径配置 ====================
    BASE_DIR: Path = Path(__file__).parent.parent
    KNOWLEDGE_DIR: Path = BASE_DIR / "knowledge"
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATA_DIR: Path = BASE_DIR / "data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 全局配置实例
settings = Settings()

# 确保必要的目录存在
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """获取配置实例"""
    return settings
