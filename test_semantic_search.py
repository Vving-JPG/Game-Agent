#!/usr/bin/env python3
"""测试 OpenViking 语义检索功能"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_semantic_search():
    """测试语义检索功能"""
    print("测试 OpenViking 语义检索功能\n")
    print("="*60)
    
    from src.memory_manager import MemoryManager, OpenVikingClient
    
    workspace = "./semantic_test_workspace"
    
    print("1. 初始化记忆管理器...")
    manager = MemoryManager(workspace, use_openviking=True)
    print(f"   OpenViking 可用: {manager.ov_client is not None and manager.ov_client.is_available()}")
    
    print("\n2. 存储测试记忆...")
    test_memories = [
        ("我喜欢吃苹果和香蕉", "preferences", "水果偏好"),
        ("我正在学习Python编程", "facts", "学习计划"),
        ("我的名字是张三", "preferences", "姓名信息"),
        ("今天天气很好", "general", "日常记录"),
    ]
    
    for content, category, desc in test_memories:
        memory = manager.store(content, category, metadata={"type": desc})
        print(f"   ✅ 存储: {content} [ID: {memory.id}]")
    
    print("\n3. 等待语义处理...")
    import time
    time.sleep(2)
    
    print("\n4. 测试语义检索...")
    queries = [
        "水果",
        "编程语言",
        "人名",
        "天气",
    ]
    
    for query in queries:
        print(f"\n   查询: '{query}'")
        results = manager.retrieve(query, use_semantic=True, limit=3)
        
        if results:
            print(f"   ✅ 找到 {len(results)} 条相关记忆:")
            for mem in results:
                print(f"      - [{mem.category}] {mem.content} (相关度: {mem.score:.3f})")
        else:
            print(f"   ⚠️  未找到相关记忆（可能还在处理中）")
    
    print("\n5. 测试关键词检索作为对比...")
    for query in queries:
        print(f"\n   查询: '{query}'")
        results = manager.retrieve(query, use_semantic=False, limit=3)
        
        if results:
            print(f"   ✅ 找到 {len(results)} 条记忆:")
            for mem in results:
                print(f"      - [{mem.category}] {mem.content}")
        else:
            print(f"   ⚠️  未找到相关记忆")
    
    print("\n6. 清理测试工作空间...")
    import shutil
    shutil.rmtree(workspace, ignore_errors=True)
    print("   ✅ 清理完成")
    
    print("\n" + "="*60)
    print("语义检索测试完成！")
    print("="*60)

if __name__ == "__main__":
    test_semantic_search()
