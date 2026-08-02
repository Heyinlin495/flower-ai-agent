"""
花卉识别 AI Agent - 前端公共配置

统一管理后端 API 地址，供所有页面共享。
"""

import os

# 后端服务地址（可通过环境变量 FLOWER_API_BASE_URL 覆盖，默认本地开发）
API_BASE_URL = os.environ.get("FLOWER_API_BASE_URL", "http://localhost:8000")
