"""
花卉识别 AI Agent - 花卉数据模型

定义花卉信息和识别结果的数据结构
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class FlowerInfo(BaseModel):
    """
    花卉详细信息模型
    """
    name: str = Field(
        description="花卉名称"
    )
    probability: Optional[float] = Field(
        default=None,
        description="识别置信度概率"
    )
    family: Optional[str] = Field(
        default=None,
        description="科"
    )
    genus: Optional[str] = Field(
        default=None,
        description="属"
    )
    characteristics: Optional[str] = Field(
        default=None,
        description="形态特征"
    )
    habitat: Optional[str] = Field(
        default=None,
        description="生长环境"
    )
    flowering_period: Optional[str] = Field(
        default=None,
        description="花期"
    )
    care_tips: Optional[str] = Field(
        default=None,
        description="养护建议"
    )
    language: Optional[str] = Field(
        default=None,
        description="花语"
    )
    origin: Optional[str] = Field(
        default=None,
        description="原产地"
    )
    light_requirement: Optional[str] = Field(
        default=None,
        description="光照需求"
    )
    temperature: Optional[str] = Field(
        default=None,
        description="适宜温度"
    )
    watering: Optional[str] = Field(
        default=None,
        description="浇水要求"
    )
    soil: Optional[str] = Field(
        default=None,
        description="土壤要求"
    )
    pests_diseases: Optional[str] = Field(
        default=None,
        description="常见病虫害"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "玫瑰",
                "probability": 0.95,
                "family": "蔷薇科",
                "genus": "蔷薇属",
                "characteristics": "落叶灌木，茎密生锐刺",
                "habitat": "温带地区",
                "flowering_period": "5-6月",
                "care_tips": "喜阳光充足，耐寒耐旱",
                "language": "爱情、美丽",
                "origin": "中国",
                "light_requirement": "全日照",
                "temperature": "15-25°C",
                "watering": "适量浇水，避免积水",
                "soil": "疏松肥沃的微酸性土壤",
                "pests_diseases": "白粉病、蚜虫"
            }
        }


class FlowerRecognitionResult(BaseModel):
    """
    花卉识别结果模型
    """
    success: bool = Field(
        description="识别是否成功"
    )
    image_url: Optional[str] = Field(
        default=None,
        description="上传的图片URL"
    )
    flowers: List[FlowerInfo] = Field(
        default_factory=list,
        description="识别出的花卉列表"
    )
    message: str = Field(
        default="",
        description="提示信息"
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息（识别失败时）"
    )
