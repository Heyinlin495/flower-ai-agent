"""
花卉识别 AI Agent - API 测试脚本

用于测试后端 API 接口
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_root():
    """测试根路径"""
    print("\n1. 测试根路径...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_health():
    """测试健康检查"""
    print("\n2. 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_chat():
    """测试聊天接口"""
    print("\n3. 测试聊天接口...")
    try:
        payload = {
            "message": "你好，请介绍一下你自己",
            "session_id": "test_session"
        }
        response = requests.post(
            f"{BASE_URL}/api/chat/send",
            json=payload,
            timeout=30
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_agent():
    """测试 Agent"""
    print("\n4. 测试 Agent...")
    try:
        response = requests.post(f"{BASE_URL}/api/chat/test", timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_knowledge_search():
    """测试知识库搜索"""
    print("\n5. 测试知识库搜索...")
    try:
        params = {
            "query": "玫瑰养护",
            "top_k": 3
        }
        response = requests.get(
            f"{BASE_URL}/api/flower/knowledge/search",
            params=params,
            timeout=30
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("🌸 花卉识别 AI Agent - API 测试")
    print("=" * 50)

    results = {
        "根路径": test_root(),
        "健康检查": test_health(),
        "聊天接口": test_chat(),
        "Agent测试": test_agent(),
        "知识库搜索": test_knowledge_search()
    }

    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️ 部分测试失败，请检查服务是否正常运行")


if __name__ == "__main__":
    run_all_tests()
