#!/usr/bin/env python3
"""使用正确的模型名称测试 OpenViking 语义检索"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_semantic_with_correct_model():
    """使用正确的模型名称测试语义检索"""
    print("使用 deepseek-v4-flash 模型测试 OpenViking 语义检索\n")
    print("="*60)

    os.environ['DEEPSEEK_API_KEY'] = 'sk-fea502e13b1247b188308dd404dcc8e1'

    from src.memory_manager import MemoryManager, OpenVikingClient

    workspace = "./semantic_test_workspace"

    print("1. 初始化 OpenViking 客户端...")
    client = OpenVikingClient(workspace_path=workspace)
    is_available = client.is_available()
    print(f"   OpenViking 可用状态: {is_available}")

    if not is_available:
        print("   ❌ OpenViking 初始化失败")
        return False

    print("\n2. 初始化记忆管理器...")
    manager = MemoryManager(workspace, use_openviking=True)

    print("\n3. 存储测试记忆...")
    test_memories = [
        ("我喜欢吃苹果和香蕉，特别喜欢红富士苹果", "preferences", "水果偏好"),
        ("我正在学习Python和JavaScript编程", "facts", "学习计划"),
        ("我的名字是张三，在北京工作", "preferences", "个人信息"),
        ("今天天气晴朗，适合户外运动", "general", "天气记录"),
        ("我讨厌阴雨天气的潮湿感", "preferences", "天气偏好"),
    ]

    for content, category, desc in test_memories:
        memory = manager.store(content, category, metadata={"type": desc})
        print(f"   ✅ 存储: {content[:40]}...")

    print("\n4. 等待语义处理...")
    import time
    print("   等待 10 秒让后台处理完成...")
    time.sleep(10)

    print("\n5. 测试语义检索...")
    queries = [
        ("水果", "查找水果相关"),
        ("编程", "查找编程相关"),
        ("名字", "查找姓名信息"),
        ("天气", "查找天气记录"),
        ("不喜欢", "查找不喜欢的事物"),
    ]

    success_count = 0
    for query, description in queries:
        print(f"\n   【查询】'{query}' - {description}")
        results = manager.retrieve(query, use_semantic=True, limit=3)

        if results:
            success_count += 1
            print(f"   ✅ 找到 {len(results)} 条相关记忆:")
            for mem in results:
                print(f"      📝 [{mem.category}] {mem.content}")
                print(f"         相关度: {mem.score:.3f}")
        else:
            print(f"   ⚠️  未找到相关记忆")

    print("\n6. 获取统计...")
    stats = manager.get_stats()
    print(f"   总记忆数: {stats['total']}")
    print(f"   OpenViking 语义检索: {'已启用' if stats['openviking_enabled'] else '未启用'}")

    print("\n7. 测试对话功能...")
    from src.agent import Agent
    agent = Agent(config_path="config/ov.conf", use_openviking=True)

    print("   测试: 告诉它我的名字")
    response1 = agent.chat("我叫李四")
    print(f"   响应: {response1[:80]}...")

    print("\n   测试: 询问我的名字")
    response2 = agent.chat("我是谁？")
    print(f"   响应: {response2[:80]}...")

    print("\n   测试: 记忆查询")
    response3 = agent.chat("我叫什么名字？")
    print(f"   响应: {response3[:80]}...")

    agent.close()

    print("\n8. 清理...")
    client.close()
    manager.close()

    import shutil
    shutil.rmtree(workspace, ignore_errors=True)

    print("\n" + "="*60)
    print(f"测试结果: {success_count}/{len(queries)} 次语义检索成功")
    print("="*60)

    return success_count > 0

if __name__ == "__main__":
    try:
        success = test_semantic_with_correct_model()
        if success:
            print("\n🎉 OpenViking 语义检索功能测试成功！")
        else:
            print("\n⚠️  语义检索功能仍有问题")
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
