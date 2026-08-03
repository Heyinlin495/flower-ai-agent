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

# 识别提示词（要求模型返回结构化 JSON）
_RECOGNITION_PROMPT = """请仔细观察这张图片，识别其中的花卉。

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


def _build_recognition_payload(image_url: str, question: Optional[str] = None) -> dict:
    """构建 OpenAI 兼容多模态请求体（question 非空时附加用户问题，让模型一并回答）"""
    text = _RECOGNITION_PROMPT
    if question:
        text = (
            f"{text}\n\n用户附加问题：{question}\n"
            "请识别图片中的花卉并按上述 JSON 格式返回；"
            "同时请在 message 字段中用中文回答用户的附加问题。"
        )
    return {
        "model": settings.VISION_MODEL_NAME,
        "max_tokens": 2048,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
                    {
                        "type": "text",
                        "text": text,
                    },
                ],
            }
        ],
    }


def _extract_content(api_response: dict) -> str:
    """从 OpenAI 兼容响应中提取文本内容"""
    choices = api_response.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return api_response.get("message", "")


def _parse_recognition_response(content: str) -> str:
    """把模型返回文本解析为 JSON 字符串。

    优先匹配 ```json 代码块，再退化为首个 { 到末尾 }（处理无围栏/尾注情况）。
    """
    try:
        # 1) ```json ... ``` 代码块围栏内提取（模型常见输出格式）
        fence = content.find("```")
        if fence != -1:
            start = content.find("{", fence)
            end = content.find("```", start)
            if start != -1:
                candidate = content[start:end].strip() if end != -1 else content[start:].strip()
                result = json.loads(candidate)
                return json.dumps(result, ensure_ascii=False)
        # 2) 兜底：首个 { 到最后一个 }
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start != -1 and json_end != -1:
            result = json.loads(content[json_start:json_end])
            return json.dumps(result, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    # JSON 解析失败时返回原始文本
    return json.dumps({
        "success": True,
        "flowers": [],
        "message": content
    }, ensure_ascii=False)


def _build_error_response(error_msg: str) -> str:
    """构建统一错误响应 JSON"""
    return json.dumps({
        "success": False,
        "error": error_msg
    }, ensure_ascii=False)


class FlowerRecognitionInput(BaseModel):
    """花卉识别工具输入"""
    image_url: str = Field(
        description="花卉图片的URL地址"
    )
    question: Optional[str] = Field(
        default=None,
        description="用户附带的问题（可选，识别时一并回答）"
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

    def _call_vision(self, image_url: str, question: Optional[str] = None, *, async_client: Optional[httpx.AsyncClient] = None) -> str:
        """
        调用视觉模型识别花卉图片

        Args:
            image_url: 图片URL (支持 http/https URL 或 data: base64 URL)
            question: 用户附带的问题（可选）
            async_client: 可选的异步客户端（传入则使用异步调用）

        Returns:
            str: 识别结果的JSON字符串
        """
        headers = {
            "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        }
        api_url = f"{settings.DASHSCOPE_BASE_URL}/chat/completions"
        payload = _build_recognition_payload(image_url, question)

        if async_client is not None:
            return self._call_vision_async(async_client, api_url, headers, payload)
        return self._call_vision_sync(api_url, headers, payload)

    def _call_vision_sync(self, api_url: str, headers: dict, payload: dict) -> str:
        """同步调用视觉模型"""
        try:
            logger.info(f"调用视觉模型(同步): {api_url}")
            response = httpx.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=120.0,
            )
            return self._handle_response(response)
        except Exception as e:
            error_msg = f"花卉识别异常: {str(e)}"
            logger.error(error_msg)
            return _build_error_response(error_msg)

    async def _call_vision_async(self, async_client: httpx.AsyncClient, api_url: str, headers: dict, payload: dict) -> str:
        """异步调用视觉模型"""
        try:
            logger.info(f"调用视觉模型(异步): {api_url}")
            response = await async_client.post(
                api_url,
                headers=headers,
                json=payload,
            )
            return self._handle_response(response)
        except Exception as e:
            error_msg = f"花卉识别异常: {str(e)}"
            logger.error(error_msg)
            return _build_error_response(error_msg)

    def _handle_response(self, response) -> str:
        """处理视觉模型响应"""
        if response.status_code == 200:
            api_response = response.json()
            content = _extract_content(api_response)
            logger.info(f"花卉识别成功: {content[:100]}...")
            return _parse_recognition_response(content)
        else:
            error_msg = f"视觉模型调用失败: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return _build_error_response(error_msg)

    def _run(self, image_url: str, question: Optional[str] = None) -> str:
        """
        执行花卉识别（同步）

        Args:
            image_url: 图片URL (支持 http/https URL 或 data: base64 URL)
            question: 用户附带的问题（可选）

        Returns:
            str: 识别结果的JSON字符串
        """
        return self._call_vision(image_url, question)

    async def _arun(self, image_url: str, question: Optional[str] = None) -> str:
        """
        执行花卉识别（异步，复用连接池）

        Args:
            image_url: 图片URL (支持 http/https URL 或 data: base64 URL)
            question: 用户附带的问题（可选）

        Returns:
            str: 识别结果的JSON字符串
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            return await self._call_vision(image_url, question, async_client=client)


# 创建工具实例
flower_recognition_tool = FlowerRecognitionTool()
