#!/usr/bin/env python3
"""测试 OpenViking 语义检索功能 - 使用 DeepSeek API"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_with_deepseek():
    """使用 DeepSeek API 测试完整功能"""
    print("使用 DeepSeek API 测试 OpenViking 完整功能\n")
    print("="*60)
    
    os.environ['DEEPSEEK_API_KEY'] = 'sk-fea502e13b1247b188308dd404dcc8e1'
    
    from src.memory_manager import MemoryManager, OpenVikingClient
    
    workspace = "./deepseek_test_workspace"
    
    print("1. 初始化 OpenViking 客户端...")
    client = OpenVikingClient(workspace_path=workspace)
    is_available = client.is_available()
    print(f"   OpenViking 可用状态: {is_available}")
    
    if not is_available:
        print("   ❌ OpenViking 初始化失败")
        return False
    
    print("\n2. 初始化记忆管理器...")
    manager = MemoryManager(workspace, use_openviking=True)
    print(f"   记忆管理器初始化完成")
    
    print("\n3. 存储测试记忆...")
    test_memories = [
        ("我喜欢吃苹果和香蕉", "preferences", "水果偏好"),
        ("我正在学习Python编程", "facts", "学习计划"),
        ("我的名字是张三", "preferences", "姓名信息"),
        ("今天天气很好适合出去散步", "general", "日常记录"),
        ("我讨厌下雨天", "preferences", "天气偏好"),
    ]
    
    stored_ids = []
    for content, category, desc in test_memories:
        memory = manager.store(content, category, metadata={"type": desc})
        stored_ids.append(memory.id)
        print(f"   ✅ 存储: {content}")
    
    print("\n4. 等待语义处理...")
    import time
    print("   等待 5 秒让后台处理完成...")
    time.sleep(5)
    
    print("\n5. 测试语义检索...")
    queries = [
        ("水果", "查找水果相关记忆"),
        ("编程语言", "查找编程相关记忆"),
        ("人名", "查找姓名信息"),
        ("天气", "查找天气相关"),
        ("我不喜欢什么", "查找不喜欢的事物"),
    ]
    
    for query, description in queries:
        print(f"\n   查询 '{query}' ({description}):")
        results = manager.retrieve(query, use_semantic=True, limit=3)
        
        if results:
            print(f"   ✅ 找到 {len(results)} 条相关记忆:")
            for mem in results[:3]:
                print(f"      - [{mem.category}] {mem.content}")
                print(f"        (相关度: {mem.score:.3f})")
        else:
            print(f"   ⚠️  未找到相关记忆")
    
    print("\n6. 统计信息...")
    stats = manager.get_stats()
    print(f"   总记忆数: {stats['total']}")
    print(f"   OpenViking 启用: {stats['openviking_enabled']}")
    print(f"   分类统计: {stats['categories']}")
    
    print("\n7. 清理...")
    client.close()
    manager.close()
    
    import shutil
    shutil.rmtree(workspace, ignore_errors=True)
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_with_deepseek()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
