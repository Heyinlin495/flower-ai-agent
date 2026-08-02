"""
花卉识别 AI Agent - 花卉识别 API 路由

提供花卉图片上传和识别的 API 接口
"""

import io
import logging
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from ..models.flower import FlowerRecognitionResult
from ..tools.flower_recognition import flower_recognition_tool
from ..oss.oss_manager import oss_manager
from ..rag.knowledge_base import knowledge_base

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flower", tags=["花卉识别"])


@router.post("/recognize")
async def recognize_flower(
    image: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    """
    识别花卉图片

    接收用户上传的花卉图片，进行识别并返回结果

    Args:
        image: 上传的图片文件
        session_id: 会话ID（可选）

    Returns:
        FlowerRecognitionResult: 识别结果
    """
    try:
        # 验证文件类型
        if not image.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="请上传图片文件"
            )

        # 读取图片数据
        image_data = await image.read()

        # 上传到 OSS
        oss_result = oss_manager.upload_image(
            image_data=image_data,
            filename=image.filename
        )

        if not oss_result["success"]:
            logger.warning(f"OSS 上传失败: {oss_result.get('error')}，使用 base64 模式")
            # 如果 OSS 失败，使用 base64 编码
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            image_url = f"data:{image.content_type};base64,{image_base64}"
        else:
            image_url = oss_result["url"]

        # 调用识别工具
        recognition_result = flower_recognition_tool._run(image_url)

        # 解析结果
        import json
        result_data = json.loads(recognition_result)

        return FlowerRecognitionResult(
            success=result_data.get("success", False),
            image_url=image_url,
            flowers=result_data.get("flowers", []),
            message=result_data.get("message", ""),
            error=result_data.get("error"),
            raw_response=recognition_result
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"花卉识别异常: {e}\n{error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recognize-url")
async def recognize_flower_by_url(image_url: str = Form(...)):
    """
    通过 URL 识别花卉

    Args:
        image_url: 图片URL

    Returns:
        FlowerRecognitionResult: 识别结果
    """
    try:
        # 调用识别工具
        recognition_result = flower_recognition_tool._run(image_url)

        # 解析结果
        import json
        result_data = json.loads(recognition_result)

        return FlowerRecognitionResult(
            success=result_data.get("success", False),
            image_url=image_url,
            flowers=result_data.get("flowers", []),
            message=result_data.get("message", ""),
            error=result_data.get("error"),
            raw_response=recognition_result
        )

    except Exception as e:
        logger.error(f"花卉识别异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"知识库搜索异常: {e}")
        return {
            "success": False,
            "error": f"搜索失败：{e}",
            "results": [],
            "total": 0,
        }


@router.post("/knowledge/add")
async def add_flower_knowledge(flower_data: dict):
    """
    添加花卉知识

    Args:
        flower_data: 花卉数据

    Returns:
        dict: 添加结果
    """
    try:
        success = knowledge_base.add_flower_knowledge(flower_data)

        return {
            "success": success,
            "message": "花卉知识添加成功" if success else "添加失败"
        }

    except Exception as e:
        logger.error(f"添加花卉知识异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
        logger.error(f"列出花卉知识异常: {e}")
        return {
            "success": False,
            "error": f"列出知识库失败：{e}",
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
        logger.error(f"删除花卉知识异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))
