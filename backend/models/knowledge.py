"""
花卉识别 AI Agent - 知识库文档模型

定义知识库文档的数据结构
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
    """
    知识库文档模型
    """
    id: Optional[str] = Field(
        default=None,
        description="文档ID"
    )
    flower_name: str = Field(
        description="花卉名称"
    )
    content: str = Field(
        description="文档内容"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="元数据"
    )
    source: Optional[str] = Field(
        default=None,
        description="来源"
    )


class KnowledgeQuery(BaseModel):
    """
    知识库查询模型
    """
    query: str = Field(
        description="查询内容"
    )
    flower_name: Optional[str] = Field(
        default=None,
        description="花卉名称（可选，用于精确查询）"
    )
    top_k: int = Field(
        default=3,
        description="返回结果数量"
    )


class KnowledgeSearchResult(BaseModel):
    """
    知识库搜索结果
    """
    success: bool = Field(
        description="搜索是否成功"
    )
    results: List[dict] = Field(
        default_factory=list,
        description="搜索结果列表"
    )
    query: str = Field(
        description="原始查询"
    )
    total: int = Field(
        default=0,
        description="结果总数"
    )
