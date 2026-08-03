"""
花卉识别 AI Agent - 知识库搜索工具

使用 RAG 技术检索花卉知识库
"""

import json
import logging
from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..rag.knowledge_base import knowledge_base

logger = logging.getLogger(__name__)


class KnowledgeSearchInput(BaseModel):
    """知识库搜索工具输入"""
    query: str = Field(
        description="搜索查询内容，可以是花卉名称或相关问题"
    )
    flower_name: Optional[str] = Field(
        default=None,
        description="花卉名称（可选，用于精确查询）"
    )


class KnowledgeSearchTool(BaseTool):
    """
    知识库搜索工具

    功能：从花卉知识库中检索相关信息
    用途：回答花卉养护、花语、特征等问题
    """

    name: str = "knowledge_search"
    description: str = """
    用于搜索花卉知识库的工具。
    当用户询问花卉相关信息时使用此工具。
    可以查询花卉的养护方法、花语、特征、病虫害等信息。
    输入应该是搜索查询内容。
    """
    args_schema: type = KnowledgeSearchInput

    def _run(self, query: str, flower_name: Optional[str] = None) -> str:
        """
        执行知识库搜索

        Args:
            query: 搜索查询
            flower_name: 花卉名称（可选）

        Returns:
            str: 搜索结果的JSON字符串
        """
        try:
            # 执行搜索
            results = knowledge_base.search(
                query=query,
                top_k=3,
                flower_name=flower_name
            )

            if not results:
                return json.dumps({
                    "success": True,
                    "results": [],
                    "message": "未找到相关花卉信息"
                }, ensure_ascii=False)

            # 格式化结果
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "content": result["content"],
                    "flower_name": result["metadata"].get("flower_name", "未知"),
                    "score": result["score"]
                })

            logger.info(f"知识库搜索完成，查询: {query[:50]}..., 结果数: {len(formatted_results)}")

            return json.dumps({
                "success": True,
                "results": formatted_results,
                "total": len(formatted_results)
            }, ensure_ascii=False)

        except Exception as e:
            error_msg = f"知识库搜索异常: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg
            }, ensure_ascii=False)

    async def _arun(self, query: str, flower_name: Optional[str] = None) -> str:
        """异步执行（同步实现放到线程池，避免阻塞 event loop）"""
        import asyncio
        return await asyncio.to_thread(self._run, query, flower_name)


# 创建工具实例
knowledge_search_tool = KnowledgeSearchTool()
