"""
花卉识别 AI Agent - OSS 管理器

实现阿里云 OSS 文件上传、下载和管理功能
"""

import os
import uuid
import logging
from typing import Optional
from datetime import datetime
import oss2
from ..config import settings

logger = logging.getLogger(__name__)


class OSSManager:
    """
    阿里云 OSS 管理器

    功能：
    - 上传图片到 OSS
    - 获取图片访问 URL
    - 删除 OSS 文件
    """

    def __init__(self):
        """初始化 OSS 客户端"""
        self._bucket = None
        self._init_bucket()

    def _init_bucket(self):
        """初始化 OSS Bucket 连接"""
        try:
            if not settings.OSS_ACCESS_KEY_ID or not settings.OSS_ACCESS_KEY_SECRET:
                logger.warning("OSS 配置未设置，将使用本地存储模式")
                return

            # 创建认证对象
            auth = oss2.Auth(
                settings.OSS_ACCESS_KEY_ID,
                settings.OSS_ACCESS_KEY_SECRET
            )

            # 创建 Bucket 对象
            self._bucket = oss2.Bucket(
                auth,
                settings.OSS_ENDPOINT,
                settings.OSS_BUCKET_NAME
            )

            logger.info(f"OSS Bucket 初始化成功: {settings.OSS_BUCKET_NAME}")

        except Exception as e:
            logger.error(f"OSS 初始化失败: {e}")
            self._bucket = None

    @property
    def is_available(self) -> bool:
        """检查 OSS 是否可用"""
        return self._bucket is not None

    def upload_image(
        self,
        image_data: bytes,
        filename: Optional[str] = None,
        content_type: str = "image/jpeg"
    ) -> dict:
        """
        上传图片到 OSS

        Args:
            image_data: 图片二进制数据
            filename: 文件名（可选，自动生成）
            content_type: 文件类型

        Returns:
            dict: 包含 success, url, key 的结果字典
        """
        try:
            if not self.is_available:
                return {
                    "success": False,
                    "error": "OSS 服务不可用",
                    "url": None,
                    "key": None
                }

            # 生成唯一的文件名
            if not filename:
                ext = content_type.split("/")[-1]
                filename = f"{uuid.uuid4().hex}.{ext}"

            # 生成 OSS 对象键（按日期组织目录）
            date_prefix = datetime.now().strftime("%Y/%m/%d")
            object_key = f"flower-images/{date_prefix}/{filename}"

            # 设置请求头
            headers = {
                "Content-Type": content_type,
                "x-oss-object-acl": "public-read"  # 设置为公开读
            }

            # 上传文件
            result = self._bucket.put_object(
                object_key,
                image_data,
                headers=headers
            )

            if result.status == 200:
                # 生成访问 URL
                url = self._get_public_url(object_key)
                logger.info(f"图片上传成功: {object_key}")

                return {
                    "success": True,
                    "url": url,
                    "key": object_key
                }
            else:
                return {
                    "success": False,
                    "error": f"上传失败，状态码: {result.status}",
                    "url": None,
                    "key": None
                }

        except Exception as e:
            logger.error(f"图片上传异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": None,
                "key": None
            }

    def upload_file(
        self,
        file_path: str,
        object_key: Optional[str] = None
    ) -> dict:
        """
        上传本地文件到 OSS

        Args:
            file_path: 本地文件路径
            object_key: OSS 对象键（可选）

        Returns:
            dict: 上传结果
        """
        try:
            if not self.is_available:
                return {
                    "success": False,
                    "error": "OSS 服务不可用"
                }

            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }

            # 生成对象键
            if not object_key:
                filename = os.path.basename(file_path)
                date_prefix = datetime.now().strftime("%Y/%m/%d")
                object_key = f"knowledge-files/{date_prefix}/{filename}"

            # 上传文件
            result = self._bucket.put_object_from_file(
                object_key,
                file_path
            )

            if result.status == 200:
                url = self._get_public_url(object_key)
                return {
                    "success": True,
                    "url": url,
                    "key": object_key
                }
            else:
                return {
                    "success": False,
                    "error": f"上传失败，状态码: {result.status}"
                }

        except Exception as e:
            logger.error(f"文件上传异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def delete_file(self, object_key: str) -> dict:
        """
        删除 OSS 文件

        Args:
            object_key: OSS 对象键

        Returns:
            dict: 删除结果
        """
        try:
            if not self.is_available:
                return {
                    "success": False,
                    "error": "OSS 服务不可用"
                }

            self._bucket.delete_object(object_key)
            logger.info(f"文件删除成功: {object_key}")

            return {
                "success": True,
                "message": f"文件已删除: {object_key}"
            }

        except Exception as e:
            logger.error(f"文件删除异常: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_public_url(self, object_key: str) -> str:
        """
        获取文件的公开访问 URL

        Args:
            object_key: OSS 对象键

        Returns:
            str: 公开访问 URL
        """
        return f"https://{settings.OSS_BUCKET_NAME}.{settings.OSS_ENDPOINT}/{object_key}"

    def list_files(self, prefix: str = "flower-images/", max_keys: int = 100) -> dict:
        """
        列出 OSS 文件

        Args:
            prefix: 文件前缀
            max_keys: 最大返回数量

        Returns:
            dict: 文件列表
        """
        try:
            if not self.is_available:
                return {
                    "success": False,
                    "error": "OSS 服务不可用",
                    "files": []
                }

            files = []
            for obj in oss2.ObjectIterator(self._bucket, prefix=prefix, max_keys=max_keys):
                files.append({
                    "key": obj.key,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "url": self._get_public_url(obj.key)
                })

            return {
                "success": True,
                "files": files,
                "total": len(files)
            }

        except Exception as e:
            logger.error(f"列出文件异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "files": []
            }


# 全局 OSS 管理器实例
oss_manager = OSSManager()
