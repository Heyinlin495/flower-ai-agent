"""
花卉识别 AI Agent - 知识库初始化脚本

用于初始化和测试知识库
"""

import sys
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import settings
from backend.rag.knowledge_base import knowledge_base

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_knowledge_base():
    """初始化知识库"""
    print("=" * 50)
    print("🌸 花卉识别 AI Agent - 知识库初始化")
    print("=" * 50)

    try:
        # 初始化知识库
        print("\n正在初始化知识库...")
        knowledge_base.initialize()
        print("✅ 知识库初始化完成！")

        # 测试搜索
        print("\n正在测试搜索功能...")
        test_queries = [
            "玫瑰怎么养护？",
            "菊花的花语是什么？",
            "兰花需要什么样的光照？"
        ]

        for query in test_queries:
            print(f"\n查询: {query}")
            results = knowledge_base.search(query, top_k=2)
            if results:
                for i, result in enumerate(results, 1):
                    flower_name = result["metadata"].get("flower_name", "未知")
                    print(f"  结果{i}: {flower_name} (相似度: {result['score']:.2f})")
            else:
                print("  未找到相关结果")

        print("\n" + "=" * 50)
        print("✅ 知识库测试完成！")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        logger.error(f"知识库初始化失败: {e}", exc_info=True)
        return False

    return True


def add_sample_flower():
    """添加示例花卉数据"""
    print("\n正在添加示例花卉数据...")

    sample_flower = {
        "name": "水仙花",
        "alias": "凌波仙子、金盏银台",
        "family": "石蒜科",
        "genus": "水仙属",
        "description": "水仙花是中国十大名花之一，也是中国传统观赏花卉。水仙花在寒冬开花，清香扑鼻，象征着吉祥如意。",
        "characteristics": "多年生草本植物。叶扁平，带状。花茎中空，花单生或数朵排列成伞形花序，花白色，副冠黄色，芳香。",
        "habitat": "喜温暖湿润环境",
        "origin": "中国",
        "flowering_period": "1-3月",
        "language": "吉祥、团圆、思念",
        "light_requirement": "喜光，室内明亮处",
        "temperature": "10-15°C",
        "watering": "水培为主，保持水质清洁",
        "soil": "沙质土壤或水培",
        "fertilizer": "水培可不施肥，土培施薄肥",
        "pests_diseases": "基腐病、叶斑病",
        "care_tips": "1. 水培时保持水质清洁；2. 每天换水；3. 避免高温；4. 花后可继续养球"
    }

    success = knowledge_base.add_flower_knowledge(sample_flower)
    if success:
        print("✅ 示例花卉数据添加成功！")
    else:
        print("❌ 添加失败")

    return success


if __name__ == "__main__":
    # 初始化知识库
    if init_knowledge_base():
        # 添加示例数据
        add_sample_flower()

    print("\n初始化完成！现在可以启动应用了。")
    print("运行 'python run_backend.py' 启动后端")
    print("运行 'python run_frontend.py' 启动前端")
