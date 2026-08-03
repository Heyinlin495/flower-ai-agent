"""
花卉识别 AI Agent - 前端公共配置

统一管理后端 API 地址与访问令牌，供所有页面共享。
"""

import os
from pathlib import Path

# 本地开发时前端进程不读系统环境变量里的 .env，这里显式加载（Docker 内已由环境注入，不覆盖）
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# 后端服务地址（可通过环境变量 FLOWER_API_BASE_URL 覆盖，默认本地开发）
API_BASE_URL = os.environ.get("FLOWER_API_BASE_URL", "http://localhost:8000")

# API 访问令牌（与后端 API_TOKEN 对应，为空则不携带 Authorization 头）
# 兼容两种变量名：Docker 里用 FLOWER_API_TOKEN 注入，本地直接读 .env 的 API_TOKEN
API_TOKEN = os.environ.get("FLOWER_API_TOKEN") or os.environ.get("API_TOKEN") or ""

# 应用版本（关于页、侧边栏等处统一引用，升级时只改这一处）
APP_VERSION = "v1.1"
