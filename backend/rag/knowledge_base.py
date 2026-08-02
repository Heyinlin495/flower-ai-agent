"""
花卉识别 AI Agent - 知识库管理

整合文档加载、文本分割、向量化和检索功能
"""

import logging
from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .document_loader import DocumentLoader
from .vector_store import VectorStoreManager
from .dashscope_embeddings import DashScopeEmbeddings
from ..config import settings

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    花卉知识库

    功能：
    - 加载花卉知识文档
    - 文本分割
    - 向量化存储
    - 相似度检索
    """

    def __init__(self):
        """初始化知识库"""
        # 文档加载器
        self.document_loader = DocumentLoader()

        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", "。", "；", "，", " "]
        )

        # Embedding 模型 - 直接使用 DashScope SDK
        self.embeddings = DashScopeEmbeddings(
            model=settings.EMBEDDING_MODEL_NAME,
            api_key=settings.DASHSCOPE_API_KEY
        )

        # 向量存储管理器
        self.vector_store = VectorStoreManager(self.embeddings)

        # 初始化状态
        self._initialized = False

    def initialize(self) -> None:
        """
        初始化知识库

        加载文档、分割、向量化并存储
        """
        try:
            logger.info("开始初始化知识库...")

            # 初始化向量存储
            self.vector_store.initialize()

            # 加载文档
            knowledge_dir = settings.KNOWLEDGE_DIR / "processed"
            documents = self.document_loader.load_documents(str(knowledge_dir))

            if not documents:
                logger.warning("没有找到知识库文档")
                self._initialized = True
                return

            # 分割文档
            split_docs = self.text_splitter.split_documents(documents)
            logger.info(f"文档分割完成，共 {len(split_docs)} 个片段")

            # 添加到向量存储
            self.vector_store.add_documents(split_docs)

            self._initialized = True
            logger.info("知识库初始化完成")

        except Exception as e:
            logger.error(f"知识库初始化失败: {e}")
            raise

    def ensure_initialized(self) -> None:
        """确保知识库已初始化"""
        if not self._initialized:
            self.initialize()

    def search(
        self,
        query: str,
        top_k: int = 3,
        flower_name: Optional[str] = None
    ) -> List[dict]:
        """
        搜索知识库

        Args:
            query: 查询文本
            top_k: 返回结果数量
            flower_name: 花卉名称（用于精确过滤）

        Returns:
            List[dict]: 搜索结果列表
        """
        try:
            self.ensure_initialized()
        except Exception as e:
            logger.warning(f"知识库未初始化，跳过搜索: {e}")
            return []

        try:
            filter_dict = None
            if flower_name:
                filter_dict = {"flower_name": flower_name}

            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=filter_dict
            )

            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })

            logger.info(f"知识库搜索完成，查询: {query[:50]}..., 结果数: {len(formatted_results)}")
            return formatted_results

        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []

    def get_retriever(self, top_k: int = 3):
        """
        获取检索器（用于 LangChain 链）

        Args:
            top_k: 返回结果数量

        Returns:
            Retriever: 检索器实例
        """
        self.ensure_initialized()
        return self.vector_store.get_retriever(search_kwargs={"k": top_k})

    def add_flower_knowledge(self, flower_data: dict) -> bool:
        """
        添加花卉知识

        Args:
            flower_data: 花卉数据字典

        Returns:
            bool: 是否添加成功
        """
        try:
            # 创建文档
            doc = self.document_loader.load_single_flower(flower_data)

            # 分割文档
            split_docs = self.text_splitter.split_documents([doc])

            # 添加到向量存储
            self.vector_store.add_documents(split_docs)

            logger.info(f"成功添加花卉知识: {flower_data.get('name', '未知')}")
            return True

        except Exception as e:
            logger.error(f"添加花卉知识失败: {e}")
            return False

    def list_flower_names(self) -> List[str]:
        """
        列出知识库中已有的花卉名称（去重）

        Returns:
            List[str]: 花卉名称列表
        """
        try:
            self.ensure_initialized()

            store = self.vector_store.store
            # Chroma 支持 get() 读取全部文档元数据
            getter = getattr(store, "get", None)
            if getter is None:
                return []

            data = getter(include=["metadatas"])
            metadatas = data.get("metadatas", []) if isinstance(data, dict) else []
            names = set()
            for m in metadatas:
                if isinstance(m, dict) and m.get("flower_name"):
                    names.add(m["flower_name"])
            return sorted(names)

        except Exception as e:
            logger.error(f"列出花卉名称失败: {e}")
            return []

    def delete_flower_knowledge(self, flower_name: str) -> int:
        """
        按花卉名称删除知识库条目

        Args:
            flower_name: 花卉名称

        Returns:
            int: 删除的文档数量（-1 表示失败）
        """
        try:
            self.ensure_initialized()

            store = self.vector_store.store
            getter = getattr(store, "get", None)
            if getter is None:
                return -1

            data = getter(where={"flower_name": flower_name}, include=["metadatas"])
            ids = data.get("ids", []) if isinstance(data, dict) else []
            if not ids:
                return 0

            self.vector_store.delete(ids)
            logger.info(f"删除花卉知识: {flower_name}，共 {len(ids)} 条")
            return len(ids)

        except Exception as e:
            logger.error(f"删除花卉知识失败: {e}")
            return -1

    def add_documents_from_directory(self, directory: str) -> int:
        """
        从目录批量添加文档

        Args:
            directory: 文档目录路径

        Returns:
            int: 添加的文档数量
        """
        try:
            # 加载文档
            documents = self.document_loader.load_documents(directory)

            if not documents:
                logger.warning(f"目录 {directory} 中没有找到文档")
                return 0

            # 分割文档
            split_docs = self.text_splitter.split_documents(documents)

            # 添加到向量存储
            self.vector_store.add_documents(split_docs)

            logger.info(f"成功添加 {len(split_docs)} 个文档片段")
            return len(split_docs)

        except Exception as e:
            logger.error(f"批量添加文档失败: {e}")
            return 0


# 全局知识库实例
knowledge_base = KnowledgeBase()
