"""
花卉识别 AI Agent - 向量存储管理器

支持 ChromaDB 和 FAISS 两种向量数据库
"""

import logging
from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from ..config import settings

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    向量存储管理器

    支持：
    - ChromaDB: 持久化存储，适合生产环境
    - FAISS: 内存存储，适合开发测试
    """

    def __init__(self, embeddings: Embeddings):
        """
        初始化向量存储管理器

        Args:
            embeddings: Embedding 模型实例
        """
        self.embeddings = embeddings
        self._store = None
        self._store_type = settings.VECTOR_DB_TYPE

    def _init_chroma(self) -> None:
        """初始化 ChromaDB"""
        try:
            from langchain_community.vectorstores import Chroma

            persist_dir = settings.CHROMA_PERSIST_DIR
            self._store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=persist_dir,
                collection_name="flower_knowledge"
            )
            logger.info(f"ChromaDB 初始化成功，持久化目录: {persist_dir}")

        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    def _init_faiss(self) -> None:
        """初始化 FAISS"""
        try:
            from langchain_community.vectorstores import FAISS

            # FAISS 需要从已有索引加载或新建
            faiss_path = settings.DATA_DIR / "faiss_index"

            if faiss_path.exists():
                self._store = FAISS.load_local(
                    str(faiss_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info(f"FAISS 索引加载成功: {faiss_path}")
            else:
                # 创建空的 FAISS 索引
                self._store = FAISS.from_texts(
                    texts=["初始化文档"],
                    embedding=self.embeddings,
                    metadatas=[{"type": "init"}]
                )
                # 保存索引
                self._store.save_local(str(faiss_path))
                logger.info(f"FAISS 索引创建成功: {faiss_path}")

        except Exception as e:
            logger.error(f"FAISS 初始化失败: {e}")
            raise

    def initialize(self) -> None:
        """初始化向量存储"""
        if self._store_type == "chroma":
            self._init_chroma()
        elif self._store_type == "faiss":
            self._init_faiss()
        else:
            raise ValueError(f"不支持的向量数据库类型: {self._store_type}")

    @property
    def store(self):
        """获取向量存储实例"""
        if self._store is None:
            self.initialize()
        return self._store

    def add_documents(self, documents: List[Document]) -> List[str]:
        """
        添加文档到向量存储

        Args:
            documents: 文档列表

        Returns:
            List[str]: 文档ID列表
        """
        try:
            if not documents:
                logger.warning("没有文档需要添加")
                return []

            # 添加文档
            ids = self.store.add_documents(documents)
            logger.info(f"成功添加 {len(documents)} 个文档到向量存储")

            # 如果是 FAISS，需要保存索引
            if self._store_type == "faiss":
                self._save_faiss_index()

            return ids

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None
    ) -> List[str]:
        """
        添加文本到向量存储

        Args:
            texts: 文本列表
            metadatas: 元数据列表

        Returns:
            List[str]: 文档ID列表
        """
        try:
            ids = self.store.add_texts(texts, metadatas)
            logger.info(f"成功添加 {len(texts)} 条文本到向量存储")

            if self._store_type == "faiss":
                self._save_faiss_index()

            return ids

        except Exception as e:
            logger.error(f"添加文本失败: {e}")
            raise

    def similarity_search(
        self,
        query: str,
        k: int = 3,
        filter: Optional[dict] = None
    ) -> List[Document]:
        """
        相似度搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter: 过滤条件

        Returns:
            List[Document]: 相似文档列表
        """
        try:
            results = self.store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            logger.info(f"相似度搜索完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            return []

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 3,
        filter: Optional[dict] = None
    ) -> List[tuple]:
        """
        带分数的相似度搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter: 过滤条件

        Returns:
            List[tuple]: (Document, score) 元组列表
        """
        try:
            results = self.store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
            logger.info(f"带分数相似度搜索完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"带分数相似度搜索失败: {e}")
            return []

    def delete(self, ids: List[str]) -> None:
        """
        删除文档

        Args:
            ids: 文档ID列表
        """
        try:
            self.store.delete(ids)
            logger.info(f"成功删除 {len(ids)} 个文档")

            if self._store_type == "faiss":
                self._save_faiss_index()

        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            raise

    def _save_faiss_index(self) -> None:
        """保存 FAISS 索引到本地"""
        try:
            if self._store_type == "faiss" and self._store:
                faiss_path = settings.DATA_DIR / "faiss_index"
                self._store.save_local(str(faiss_path))
                logger.debug("FAISS 索引已保存")

        except Exception as e:
            logger.error(f"保存 FAISS 索引失败: {e}")

    def get_retriever(self, search_kwargs: Optional[dict] = None):
        """
        获取检索器

        Args:
            search_kwargs: 搜索参数

        Returns:
            Retriever: 检索器实例
        """
        if search_kwargs is None:
            search_kwargs = {"k": 3}

        return self.store.as_retriever(search_kwargs=search_kwargs)
