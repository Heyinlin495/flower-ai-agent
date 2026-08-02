"""
花卉识别 AI Agent - DashScope Embedding 封装

直接使用 DashScope SDK 进行 embedding，避免 OpenAI SDK 兼容性问题。
"""

import logging
from typing import List
from langchain_core.embeddings import Embeddings
from dashscope import TextEmbedding

from ..config import settings

logger = logging.getLogger(__name__)


class DashScopeEmbeddings(Embeddings):
    """
    DashScope Embedding 模型封装

    直接调用阿里云 DashScope API，兼容 langchain_core.embeddings.Embeddings 接口
    """

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        text_type: str = "document"
    ):
        """
        初始化 DashScope Embeddings

        Args:
            model: Embedding 模型名称，默认使用配置中的 EMBEDDING_MODEL_NAME
            api_key: DashScope API Key，默认使用配置中的 DASHSCOPE_API_KEY
            text_type: 文本类型，"document" 或 "query"
        """
        self.model = model or settings.EMBEDDING_MODEL_NAME
        self.api_key = api_key or settings.DASHSCOPE_API_KEY
        self.text_type = text_type

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        批量 embedding 文档

        Args:
            texts: 文档文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        embeddings = []

        for i, text in enumerate(texts):
            try:
                resp = TextEmbedding.call(
                    model=self.model,
                    input=text,
                    api_key=self.api_key,
                    text_type="document"  # 文档类型
                )

                if resp.status_code == 200:
                    embeddings.append(resp.output["embeddings"][0]["embedding"])
                    if (i + 1) % 10 == 0:
                        logger.debug(f"Embedding 进度: {i + 1}/{len(texts)}")
                else:
                    logger.error(
                        f"Embedding 文档失败 [{i}/{len(texts)}]: "
                        f"status={resp.status_code}, code={resp.code}, message={resp.message}"
                    )
                    raise RuntimeError(
                        f"DashScope Embedding 失败: [{resp.code}] {resp.message}"
                    )

            except Exception as e:
                logger.error(f"Embedding 文档异常 [{i}/{len(texts)}]: {e}")
                raise

        logger.info(f"成功 embedding {len(embeddings)} 个文档片段")
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embedding 单条查询文本

        Args:
            text: 查询文本

        Returns:
            List[float]: 向量
        """
        try:
            resp = TextEmbedding.call(
                model=self.model,
                input=text,
                api_key=self.api_key,
                text_type="query"  # 查询类型，DashScope 对 query 有优化
            )

            if resp.status_code == 200:
                embedding = resp.output["embeddings"][0]["embedding"]
                logger.debug(f"Embedding 查询成功，维度: {len(embedding)}")
                return embedding
            else:
                logger.error(
                    f"Embedding 查询失败: "
                    f"status={resp.status_code}, code={resp.code}, message={resp.message}"
                )
                raise RuntimeError(
                    f"DashScope Embedding 失败: [{resp.code}] {resp.message}"
                )

        except Exception as e:
            logger.error(f"Embedding 查询异常: {e}")
            raise
