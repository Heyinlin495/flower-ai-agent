"""
花卉识别 AI Agent - 图片处理工具

上传图片的压缩与格式归一化：
- 视觉模型对超大图会内部降采样，先压缩可省 OSS 存储与带宽，识别质量几乎无损失
- 统一转 JPEG，规避 base64 data URL 尺寸上限（OSS 失败时的兜底路径才真正可用）
"""

import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

# 视觉模型识别的合理最长边（qwen-vl-max 官方建议，超过会内部缩放）
_DEFAULT_MAX_EDGE = 1568
_DEFAULT_QUALITY = 85


def compress_image(
    image_data: bytes,
    max_edge: int = _DEFAULT_MAX_EDGE,
    quality: int = _DEFAULT_QUALITY,
) -> bytes:
    """
    压缩图片为 JPEG：最长边缩到 max_edge，质量 quality。

    Args:
        image_data: 原始图片二进制（任意常见格式，含 GIF/PNG 等）
        max_edge: 最长边像素上限
        quality: JPEG 质量（0-100）

    Returns:
        bytes: 压缩后的 JPEG 二进制（尺寸小于原图时；未缩小则转码后返回）
    """
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            # 转 RGB：丢弃 alpha 通道与 GIF 调色板（识别只关心内容，JPEG 无透明通道）
            img = img.convert("RGB")
            img.thumbnail((max_edge, max_edge), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            return buf.getvalue()
    except Exception as e:
        # 解压失败（理论上已被魔数校验拦截）或 Pillow 不支持时原样返回
        logger.warning(f"图片压缩失败，使用原图: {e}")
        return image_data
