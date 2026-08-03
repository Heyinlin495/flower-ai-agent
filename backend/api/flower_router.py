"""
花卉识别 AI Agent - 花卉识别 API 路由

提供花卉图片上传和识别的 API 接口
"""

import logging
import base64
import json
import traceback
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from typing import Optional

from ..models.flower import FlowerRecognitionResult, FlowerInfo
from ..tools.flower_recognition import flower_recognition_tool
from ..oss.oss_manager import oss_manager
from ..rag.knowledge_base import knowledge_base
from ..config import settings
from ..image_utils import compress_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flower", tags=["花卉识别"])

# 图片格式魔数（文件头，不信任客户端声明的 content_type）
_IMAGE_SIGNATURES = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # WEBP 头为 RIFF....WEBP（偏移 8 处是 "WEBP"）
]


def _verify_image_format(data: bytes, content_type: str) -> bool:
    """按文件头魔数校验图片真实格式，并确认与声明的 content_type 一致"""
    if not content_type or not content_type.startswith("image/"):
        return False
    for sig, fmt in _IMAGE_SIGNATURES:
        if data.startswith(sig):
            if fmt == "image/webp":
                return data[8:12] == b"WEBP" and content_type == "image/webp"
            return fmt == content_type
    return False


@router.post("/recognize")
async def recognize_flower(
    image: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    question: Optional[str] = Form(None)
):
    """
    识别花卉图片

    接收用户上传的花卉图片，进行识别并返回结果

    Args:
        image: 上传的图片文件
        session_id: 会话ID（可选）
        question: 用户附带的问题（可选，识别时一并回答）

    Returns:
        FlowerRecognitionResult: 识别结果
    """
    try:
        # 验证文件类型
        if not image.content_type or not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="请上传图片文件（仅支持 JPG/PNG/WebP/GIF）"
            )

        # 读取图片数据（限制大小，防止超大文件打满内存）
        max_size = settings.MAX_UPLOAD_SIZE
        image_data = await image.read(max_size + 1)
        if len(image_data) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"图片过大，最大支持 {max_size // (1024 * 1024)}MB",
            )

        # 魔数校验真实格式（不信任客户端 content_type）
        if not _verify_image_format(image_data, image.content_type):
            raise HTTPException(
                status_code=400,
                detail="图片文件格式无效"
            )

        # 压缩为 JPEG（最长边 1568px）：省 OSS 存储/带宽，且 base64 兜底路径
        # 不再触达模型对 data URL 的尺寸上限。压缩失败时返回原图，流程不中断。
        image_data = await run_in_threadpool(compress_image, image_data)
        content_type = "image/jpeg"

        # 上传到 OSS（阻塞调用，移出 event loop）
        oss_result = await run_in_threadpool(
            oss_manager.upload_image,
            image_data,
            image.filename,
            content_type,
        )

        if not oss_result["success"]:
            logger.warning(f"OSS 上传失败: {oss_result.get('error')}，使用 base64 模式")
            # 如果 OSS 失败，使用 base64 编码（压缩后体积小，可安全走 data URL）
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            image_url = f"data:{content_type};base64,{image_base64}"
        else:
            image_url = oss_result["url"]

        # 调用识别工具（阻塞调用，移出 event loop；question 一并交给视觉模型回答）
        recognition_result = await run_in_threadpool(
            flower_recognition_tool._run, image_url, question
        )

        # 解析结果
        result_data = json.loads(recognition_result)

        return FlowerRecognitionResult(
            success=result_data.get("success", False),
            image_url=image_url,
            flowers=result_data.get("flowers", []),
            message=result_data.get("message", ""),
            error=result_data.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        # 完整堆栈只进日志，响应给简短消息（不暴露内部细节）
        logger.error(f"花卉识别异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="花卉识别失败，请稍后重试")



@router.get("/knowledge/search")
async def search_flower_knowledge(
    query: str,
    flower_name: Optional[str] = None,
    top_k: int = 3
):
    """
    搜索花卉知识库

    Args:
        query: 搜索查询
        flower_name: 花卉名称（可选）
        top_k: 返回结果数量

    Returns:
        dict: 搜索结果
    """
    try:
        results = knowledge_base.search(
            query=query,
            top_k=top_k,
            flower_name=flower_name
        )

        return {
            "success": True,
            "query": query,
            "results": results,
            "total": len(results)
        }

    except Exception as e:
        logger.error(f"知识库搜索异常: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": "知识库搜索失败，请稍后重试",
            "results": [],
            "total": 0,
        }


@router.post("/knowledge/add")
async def add_flower_knowledge(flower_data: dict):
    """
    添加花卉知识

    Args:
        flower_data: 花卉数据（内部用 FlowerInfo 校验，name 必填）

    Returns:
        dict: 添加结果
    """
    try:
        validated = FlowerInfo.model_validate(flower_data)
    except ValidationError as e:
        logger.warning(f"花卉数据校验失败: {e}")
        raise HTTPException(status_code=400, detail="花卉数据不合法，name 为必填字段")

    try:
        # 去掉空字段，避免知识库写入空值
        flower_dict = validated.model_dump(exclude_none=True)
        success = knowledge_base.add_flower_knowledge(flower_dict)

        return {
            "success": success,
            "message": "花卉知识添加成功" if success else "添加失败"
        }

    except Exception as e:
        logger.error(f"添加花卉知识异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="添加花卉知识失败，请稍后重试")


@router.get("/knowledge/list")
async def list_flower_knowledge():
    """
    列出知识库中已有的花卉名称

    Returns:
        dict: 花卉名称列表
    """
    try:
        names = knowledge_base.list_flower_names()
        return {
            "success": True,
            "flowers": names,
            "total": len(names)
        }

    except Exception as e:
        logger.error(f"列出花卉知识异常: {e}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": "列出知识库失败，请稍后重试",
            "flowers": [],
            "total": 0,
        }


@router.delete("/knowledge/delete/{flower_name}")
async def delete_flower_knowledge(flower_name: str):
    """
    删除指定花卉的知识库条目

    Args:
        flower_name: 花卉名称

    Returns:
        dict: 删除结果
    """
    try:
        deleted = knowledge_base.delete_flower_knowledge(flower_name)

        if deleted < 0:
            return {
                "success": False,
                "message": f"删除「{flower_name}」失败",
                "error": "删除失败，请稍后重试",
                "deleted": 0,
            }
        if deleted == 0:
            return {
                "success": True,
                "message": f"「{flower_name}」不存在或已删除",
                "deleted": 0,
            }
        return {
            "success": True,
            "message": f"已删除「{flower_name}」的 {deleted} 条知识",
            "deleted": deleted,
        }

    except Exception as e:
        logger.error(f"删除花卉知识异常: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="删除花卉知识失败，请稍后重试")
