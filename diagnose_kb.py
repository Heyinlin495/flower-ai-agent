"""
知识库诊断脚本 - 逐步排查搜索无结果的问题
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# 配置日志 - 输出到控制台
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("diagnose")

print("=" * 60)
print("🔍 花卉知识库诊断工具")
print("=" * 60)

# ====== 第1步: 检查配置 ======
print("\n📋 第1步: 检查配置...")
from backend.config import settings

print(f"  VECTOR_DB_TYPE: {settings.VECTOR_DB_TYPE}")
print(f"  CHROMA_PERSIST_DIR: {settings.CHROMA_PERSIST_DIR}")
print(f"  EMBEDDING_MODEL_NAME: {settings.EMBEDDING_MODEL_NAME}")
print(f"  DASHSCOPE_BASE_URL: {settings.DASHSCOPE_BASE_URL}")
print(f"  DASHSCOPE_API_KEY: {'***' + settings.DASHSCOPE_API_KEY[-8:] if settings.DASHSCOPE_API_KEY else '❌ 未设置!'}")
print(f"  KNOWLEDGE_DIR: {settings.KNOWLEDGE_DIR}")

# ====== 第2步: 检查知识库文件 ======
print("\n📁 第2步: 检查知识库文件...")
knowledge_dir = settings.KNOWLEDGE_DIR / "processed"
if knowledge_dir.exists():
    files = list(knowledge_dir.glob("*"))
    print(f"  ✅ 目录存在: {knowledge_dir}")
    print(f"  文件列表: {[f.name for f in files]}")
    for f in files:
        if f.suffix == ".json":
            import json
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            flowers = data if isinstance(data, list) else data.get("flowers", [])
            print(f"    {f.name}: 包含 {len(flowers)} 种花卉")
else:
    print(f"  ❌ 目录不存在: {knowledge_dir}")

# ====== 第3步: 检查ChromaDB数据 ======
print("\n💾 第3步: 检查ChromaDB数据...")
chroma_dir = Path(settings.CHROMA_PERSIST_DIR)
if chroma_dir.exists():
    db_file = chroma_dir / "chroma.sqlite3"
    if db_file.exists():
        import os
        size_kb = os.path.getsize(db_file) / 1024
        print(f"  ✅ ChromaDB 文件存在: {db_file} ({size_kb:.1f} KB)")

        # 直接查询 sqlite 看有多少条记录
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()

            # 查看所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"  数据库表: {[t[0] for t in tables]}")

            # 尝试查 embedding 表的记录数
            for table_name in ["embedding_fulltext_search", "embeddings", "embedding_metadata"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"  {table_name}: {count} 条记录")
                except:
                    pass

            # 查 collections 表
            try:
                cursor.execute("SELECT id, name FROM collections")
                collections = cursor.fetchall()
                for col in collections:
                    print(f"  Collection: id={col[0]}, name='{col[1]}'")
            except Exception as e:
                print(f"  查 collections 失败: {e}")

            conn.close()
        except Exception as e:
            print(f"  ⚠️ 读取数据库失败: {e}")
    else:
        print(f"  ❌ chroma.sqlite3 不存在!")
else:
    print(f"  ❌ ChromaDB 目录不存在: {chroma_dir}")

# ====== 第4步: 测试 Embedding API ======
print("\n🌐 第4步: 测试 Embedding API (DashScope SDK)...")
try:
    from backend.rag.dashscope_embeddings import DashScopeEmbeddings

    embeddings = DashScopeEmbeddings(
        model=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.DASHSCOPE_API_KEY
    )

    print(f"  正在调用 embedding API (模型: {settings.EMBEDDING_MODEL_NAME})...")
    test_result = embeddings.embed_query("测试文本")
    print(f"  ✅ Embedding API 调用成功! 向量维度: {len(test_result)}")
except Exception as e:
    print(f"  ❌ Embedding API 调用失败: {e}")
    print(f"     → 这是知识库搜索无结果的最可能原因!")
    print(f"     → 请检查: API Key 是否有效? 账户是否有配额? 模型名是否正确?")

# ====== 第5步: 测试 ChromaDB 向量搜索 ======
print("\n🔎 第5步: 测试向量搜索...")
try:
    from backend.rag.vector_store import VectorStoreManager
    from backend.rag.dashscope_embeddings import DashScopeEmbeddings

    embeddings = DashScopeEmbeddings(
        model=settings.EMBEDDING_MODEL_NAME,
        api_key=settings.DASHSCOPE_API_KEY
    )

    vsm = VectorStoreManager(embeddings)
    vsm.initialize()

    # 不带 filter 搜索
    print("  执行相似度搜索: '玫瑰怎么养护'...")
    results = vsm.similarity_search_with_score("玫瑰怎么养护", k=3)
    print(f"  返回结果数: {len(results)}")
    for i, (doc, score) in enumerate(results):
        flower = doc.metadata.get("flower_name", "未知")
        print(f"    结果{i+1}: {flower} (分数: {score:.4f})")
        print(f"      内容: {doc.page_content[:80]}...")

    if len(results) == 0:
        print("  ⚠️ 搜索返回空! 可能原因:")
        print("    1. ChromaDB 中没有数据")
        print("    2. Embedding 维度不匹配 (之前用不同模型索引的)")
        print("    3. ChromaDB 版本不兼容")

except Exception as e:
    print(f"  ❌ 向量搜索失败: {e}")
    import traceback
    traceback.print_exc()

# ====== 第6步: 总结 ======
print("\n" + "=" * 60)
print("📊 诊断总结")
print("=" * 60)
print("""
常见问题及解决方案:
1. Embedding API 失败 → 检查 API Key 和配额
2. ChromaDB 无数据 → 重新运行 init_knowledge.py
3. Embedding 维度不匹配 → 删除 data/chroma_db 重新初始化
4. 应用启动时 initialize() 静默失败 → 查看服务端日志
""")
