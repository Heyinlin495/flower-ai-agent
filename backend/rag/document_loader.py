"""
花卉识别 AI Agent - 文档加载器

支持加载多种格式的花卉知识文档：JSON, TXT, PDF
"""

import json
import logging
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentLoader:
    """
    文档加载器

    支持格式：
    - JSON: 花卉知识库 JSON 文件
    - TXT: 纯文本文件
    - PDF: PDF 文档
    """

    def __init__(self):
        """初始化文档加载器"""
        self.supported_formats = [".json", ".txt", ".pdf"]

    def load_documents(self, directory: str) -> List[Document]:
        """
        加载目录下的所有文档

        Args:
            directory: 文档目录路径

        Returns:
            List[Document]: 文档列表
        """
        documents = []
        dir_path = Path(directory)

        if not dir_path.exists():
            logger.warning(f"目录不存在: {directory}")
            return documents

        # 遍历目录下的所有文件
        for file_path in dir_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in self.supported_formats:
                try:
                    docs = self._load_file(file_path)
                    documents.extend(docs)
                    logger.info(f"成功加载文件: {file_path.name}, 文档数: {len(docs)}")
                except Exception as e:
                    logger.error(f"加载文件失败 {file_path.name}: {e}")

        logger.info(f"总共加载文档数: {len(documents)}")
        return documents

    def _load_file(self, file_path: Path) -> List[Document]:
        """
        加载单个文件

        Args:
            file_path: 文件路径

        Returns:
            List[Document]: 文档列表
        """
        suffix = file_path.suffix.lower()

        if suffix == ".json":
            return self._load_json(file_path)
        elif suffix == ".txt":
            return self._load_txt(file_path)
        elif suffix == ".pdf":
            return self._load_pdf(file_path)
        else:
            logger.warning(f"不支持的文件格式: {suffix}")
            return []

    def _load_json(self, file_path: Path) -> List[Document]:
        """
        加载 JSON 格式的花卉知识库

        JSON 格式示例:
        {
            "flowers": [
                {
                    "name": "玫瑰",
                    "family": "蔷薇科",
                    "description": "...",
                    ...
                }
            ]
        }

        或者直接是数组:
        [
            {
                "name": "玫瑰",
                ...
            }
        ]
        """
        documents = []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 支持两种格式：对象包含 flowers 数组，或者直接是数组
        flowers = data if isinstance(data, list) else data.get("flowers", [])

        for flower in flowers:
            # 构建文档内容
            content = self._format_flower_content(flower)

            # 构建元数据
            metadata = {
                "source": str(file_path),
                "flower_name": flower.get("name", "未知"),
                "type": "flower_knowledge"
            }

            documents.append(Document(
                page_content=content,
                metadata=metadata
            ))

        return documents

    def _load_txt(self, file_path: Path) -> List[Document]:
        """加载 TXT 格式文件"""
        documents = []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 按空行分割成多个段落
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        for i, para in enumerate(paragraphs):
            metadata = {
                "source": str(file_path),
                "paragraph_index": i,
                "type": "text_document"
            }
            documents.append(Document(
                page_content=para,
                metadata=metadata
            ))

        return documents

    def _load_pdf(self, file_path: Path) -> List[Document]:
        """加载 PDF 格式文件"""
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(str(file_path))
            documents = loader.load()

            # 添加元数据
            for doc in documents:
                doc.metadata["source"] = str(file_path)
                doc.metadata["type"] = "pdf_document"

            return documents
        except ImportError:
            logger.error("PDF 加载需要安装 pypdf: pip install pypdf")
            return []

    def _format_flower_content(self, flower: dict) -> str:
        """
        格式化花卉信息为文本内容

        Args:
            flower: 花卉信息字典

        Returns:
            str: 格式化后的文本
        """
        parts = []

        # 基本信息
        if "name" in flower:
            parts.append(f"花卉名称：{flower['name']}")
        if "family" in flower:
            parts.append(f"科：{flower['family']}")
        if "genus" in flower:
            parts.append(f"属：{flower['genus']}")
        if "alias" in flower:
            parts.append(f"别名：{flower['alias']}")

        # 描述信息
        if "description" in flower:
            parts.append(f"描述：{flower['description']}")
        if "characteristics" in flower:
            parts.append(f"形态特征：{flower['characteristics']}")

        # 生长信息
        if "habitat" in flower:
            parts.append(f"生长环境：{flower['habitat']}")
        if "origin" in flower:
            parts.append(f"原产地：{flower['origin']}")
        if "flowering_period" in flower:
            parts.append(f"花期：{flower['flowering_period']}")

        # 养护信息
        if "light_requirement" in flower:
            parts.append(f"光照需求：{flower['light_requirement']}")
        if "temperature" in flower:
            parts.append(f"适宜温度：{flower['temperature']}")
        if "watering" in flower:
            parts.append(f"浇水要求：{flower['watering']}")
        if "soil" in flower:
            parts.append(f"土壤要求：{flower['soil']}")
        if "fertilizer" in flower:
            parts.append(f"施肥要求：{flower['fertilizer']}")

        # 其他信息
        if "language" in flower:
            parts.append(f"花语：{flower['language']}")
        if "pests_diseases" in flower:
            parts.append(f"常见病虫害：{flower['pests_diseases']}")
        if "care_tips" in flower:
            parts.append(f"养护建议：{flower['care_tips']}")

        return "\n".join(parts)

    def load_single_flower(self, flower_data: dict) -> Document:
        """
        加载单个花卉数据为文档

        Args:
            flower_data: 花卉数据字典

        Returns:
            Document: 文档对象
        """
        content = self._format_flower_content(flower_data)
        metadata = {
            "flower_name": flower_data.get("name", "未知"),
            "type": "flower_knowledge"
        }
        return Document(page_content=content, metadata=metadata)
