"""
花卉识别 AI Agent - OSS 图片管理工具

管理用户上传的花卉图片
"""

import json
import logging
from typing import Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..oss.oss_manager import oss_manager

logger = logging.getLogger(__name__)


class OSSImageUploadInput(BaseModel):
    """OSS图片上传工具输入"""
    image_data: str = Field(
        description="图片的Base64编码数据"
    )
    filename: Optional[str] = Field(
        default=None,
        description="文件名（可选）"
    )


class OSSImageListInput(BaseModel):
    """OSS图片列表工具输入"""
    prefix: Optional[str] = Field(
        default="flower-images/",
        description="文件前缀"
    )
    max_count: Optional[int] = Field(
        default=20,
        description="最大返回数量"
    )


class OSSImageManagerTool(BaseTool):
    """
    OSS 图片管理工具

    功能：
    - 上传图片到阿里云 OSS
    - 列出已上传的图片
    - 获取图片访问 URL
    """

    name: str = "oss_image_manager"
    description: str = """
    用于管理花卉图片的工具。
    可以上传图片到云端存储，也可以列出已上传的图片。
    当需要保存用户上传的图片时使用此工具。
    """
    args_schema: type = OSSImageUploadInput

    def _run(
        self,
        image_data: Optional[str] = None,
        filename: Optional[str] = None,
        action: str = "upload",
        prefix: Optional[str] = None,
        max_count: int = 20
    ) -> str:
        """
        执行 OSS 图片管理操作

        Args:
            image_data: Base64 编码的图片数据（上传时使用）
            filename: 文件名
            action: 操作类型 (upload/list)
            prefix: 文件前缀（列出时使用）
            max_count: 最大返回数量

        Returns:
            str: 操作结果的JSON字符串
        """
        try:
            if action == "upload":
                return self._upload_image(image_data, filename)
            elif action == "list":
                return self._list_images(prefix, max_count)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"不支持的操作: {action}"
                }, ensure_ascii=False)

        except Exception as e:
            error_msg = f"OSS 操作异常: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg
            }, ensure_ascii=False)

    def _upload_image(self, image_data: str, filename: Optional[str] = None) -> str:
        """
        上传图片到 OSS

        Args:
            image_data: Base64 编码的图片数据
            filename: 文件名

        Returns:
            str: 上传结果
        """
        import base64

        try:
            # 解码 Base64 数据
            if "," in image_data:
                # 处理 data:image/xxx;base64,... 格式
                image_data = image_data.split(",")[1]

            image_bytes = base64.b64decode(image_data)

            # 上传到 OSS
            result = oss_manager.upload_image(
                image_data=image_bytes,
                filename=filename
            )

            if result["success"]:
                return json.dumps({
                    "success": True,
                    "url": result["url"],
                    "key": result["key"],
                    "message": "图片上传成功"
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "error": result.get("error", "上传失败")
                }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"图片上传失败: {str(e)}"
            }, ensure_ascii=False)

    def _list_images(
        self,
        prefix: Optional[str] = None,
        max_count: int = 20
    ) -> str:
        """
        列出 OSS 中的图片

        Args:
            prefix: 文件前缀
            max_count: 最大返回数量

        Returns:
            str: 图片列表
        """
        try:
            if prefix is None:
                prefix = "flower-images/"

            result = oss_manager.list_files(
                prefix=prefix,
                max_keys=max_count
            )

            if result["success"]:
                return json.dumps({
                    "success": True,
                    "files": result["files"],
                    "total": result["total"]
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "success": False,
                    "error": result.get("error", "列出文件失败")
                }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"列出图片失败: {str(e)}"
            }, ensure_ascii=False)

    async def _arun(self, **kwargs) -> str:
        """异步执行（暂时使用同步实现）"""
        return self._run(**kwargs)


# 创建工具实例
oss_image_manager_tool = OSSImageManagerTool()
