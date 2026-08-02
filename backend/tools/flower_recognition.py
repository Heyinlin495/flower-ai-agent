"""
花卉识别 AI Agent - 花卉识别工具

使用通义千问视觉模型识别花卉图片
"""

import json
import logging
from typing import Optional
import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..config import settings

logger = logging.getLogger(__name__)


class FlowerRecognitionInput(BaseModel):
    """花卉识别工具输入"""
    image_url: str = Field(
        description="花卉图片的URL地址"
    )


class FlowerRecognitionTool(BaseTool):
    """
    花卉识别工具

    功能：调用通义千问视觉模型识别花卉图片
    返回：花卉名称、科属、特征等信息
    """

    name: str = "flower_recognition"
    description: str = """
    用于识别花卉图片的工具。
    当用户上传花卉图片时，使用此工具识别花卉。
    输入应该是图片的URL地址。
    返回花卉的名称、科属、特征、花期等信息。
    """
    args_schema: type = FlowerRecognitionInput

    def _run(self, image_url: str) -> str:
        """
        执行花卉识别

        Args:
            image_url: 图片URL (支持 http/https URL 或 data: base64 URL)

        Returns:
            str: 识别结果的JSON字符串
        """
        try:
            # 构建提示词
            prompt = """请仔细观察这张图片，识别其中的花卉。

请按照以下JSON格式返回识别结果：
{
    "success": true,
    "flowers": [
        {
            "name": "花卉名称",
            "probability": 0.95,
            "family": "科名",
            "genus": "属名",
            "characteristics": "形态特征描述",
            "habitat": "生长环境",
            "flowering_period": "花期",
            "language": "花语",
            "origin": "原产地"
        }
    ],
    "message": "识别结果说明"
}

注意：
1. 如果图片中有多种花卉，请全部列出
2. probability 是置信度，范围 0-1
3. 如果无法确定，请在 message 中说明可能的结果
4. 所有内容请用中文回答"""

            # 使用 httpx 调用 OpenAI 兼容接口（DashScope）
            headers = {
                "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                "Content-Type": "application/json",
            }

            # 根据图片URL类型构建 image_url 字段
            if image_url.startswith("data:"):
                # Base64 数据 URL，直接传给 OpenAI 兼容接口
                image_url_field = image_url
            else:
                # 普通 URL，也直接传
                image_url_field = image_url

            # 构建请求体 - OpenAI 兼容多模态格式
            payload = {
                "model": settings.VISION_MODEL_NAME,
                "max_tokens": 2048,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url_field},
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            }

            # 调用 DashScope OpenAI 兼容端点
            api_url = f"{settings.DASHSCOPE_BASE_URL}/chat/completions"
            logger.info(f"调用视觉模型: {api_url}")
            response = httpx.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=120.0,
            )

            if response.status_code == 200:
                api_response = response.json()
                # OpenAI 兼容格式响应
                choices = api_response.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                else:
                    content = api_response.get("message", "")
                logger.info(f"花卉识别成功: {content[:100]}...")

                # 尝试解析JSON
                try:
                    # 提取JSON部分
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    if json_start != -1 and json_end != -1:
                        json_str = content[json_start:json_end]
                        result = json.loads(json_str)
                        return json.dumps(result, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass

                # 如果JSON解析失败，返回原始文本
                return json.dumps({
                    "success": True,
                    "flowers": [],
                    "message": content
                }, ensure_ascii=False)
            else:
                error_msg = f"视觉模型调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return json.dumps({
                    "success": False,
                    "error": error_msg
                }, ensure_ascii=False)

        except Exception as e:
            error_msg = f"花卉识别异常: {str(e)}"
            logger.error(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg
            }, ensure_ascii=False)

    async def _arun(self, image_url: str) -> str:
        """异步执行（暂时使用同步实现）"""
        return self._run(image_url)


# 创建工具实例
flower_recognition_tool = FlowerRecognitionTool()
