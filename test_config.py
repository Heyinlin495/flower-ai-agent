"""
花卉识别 AI Agent - 配置测试脚本

测试环境变量配置是否正确
"""

import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_config():
    """测试配置"""
    print("=" * 50)
    print("花卉识别 AI Agent - 配置测试")
    print("=" * 50)

    # 检查必要的配置
    checks = {
        "DASHSCOPE_API_KEY": os.getenv("DASHSCOPE_API_KEY"),
        "DASHSCOPE_BASE_URL": os.getenv("DASHSCOPE_BASE_URL"),
        "OSS_ACCESS_KEY_ID": os.getenv("OSS_ACCESS_KEY_ID"),
        "OSS_ACCESS_KEY_SECRET": os.getenv("OSS_ACCESS_KEY_SECRET"),
        "OSS_BUCKET_NAME": os.getenv("OSS_BUCKET_NAME"),
    }

    print("\n配置检查:")
    print("-" * 50)

    all_ok = True
    for key, value in checks.items():
        if value:
            # 隐藏敏感信息
            if "KEY" in key or "SECRET" in key:
                display_value = value[:10] + "..." if len(value) > 10 else value
            else:
                display_value = value
            print(f"[OK] {key}: {display_value}")
        else:
            print(f"[MISSING] {key}: 未设置")
            all_ok = False

    print("-" * 50)

    if all_ok:
        print("\n[SUCCESS] 所有配置检查通过!")
        print("\n可以启动项目了!")
        print("\n运行以下命令启动：")
        print("  1. python init_knowledge.py  (初始化知识库)")
        print("  2. python run_backend.py     (启动后端)")
        print("  3. python run_frontend.py    (启动前端)")
    else:
        print("\n[ERROR] 部分配置缺失，请检查 .env 文件")

    return all_ok


if __name__ == "__main__":
    test_config()
