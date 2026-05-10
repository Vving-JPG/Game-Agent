#!/usr/bin/env python3
"""OpenViking Agent 验证测试脚本"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """测试模块导入"""
    print("1. 测试模块导入...")
    try:
        from src.agent import Agent
        from src.memory_manager import MemoryManager, OpenVikingClient
        from src.tools import create_default_tools, ToolRegistry
        from src.prompts import PromptManager
        print("   ✅ 所有核心模块导入成功")
        return True
    except Exception as e:
        print(f"   ❌ 模块导入失败: {e}")
        return False

def test_memory_manager():
    """测试记忆管理器"""
    print("\n2. 测试记忆管理器...")
    try:
        from src.memory_manager import MemoryManager
        
        manager = MemoryManager("./test_workspace", use_openviking=True)
        
        memory = manager.store("测试记忆内容", category="general")
        print(f"   ✅ 存储记忆成功 [ID: {memory.id}]")
        
        memories = manager.retrieve("测试", use_semantic=False)
        print(f"   ✅ 检索记忆成功 (找到 {len(memories)} 条)")
        
        stats = manager.get_stats()
        print(f"   ✅ 获取统计成功: 总计 {stats['total']} 条记忆")
        
        manager.close()
        return True
    except Exception as e:
        print(f"   ❌ 记忆管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_openviking_client():
    """测试 OpenViking 客户端"""
    print("\n3. 测试 OpenViking 客户端...")
    try:
        from src.memory_manager import OpenVikingClient
        
        client = OpenVikingClient()
        is_available = client.is_available()
        
        if is_available:
            print("   ✅ OpenViking 客户端可用")
        else:
            print("   ⚠️  OpenViking 客户端不可用 (缺少 API Key 或配置错误)")
            print("      这不影响基础功能，但语义检索功能将不可用")
        
        client.close()
        return True
    except Exception as e:
        print(f"   ❌ OpenViking 客户端测试失败: {e}")
        return False

def test_tools():
    """测试工具系统"""
    print("\n4. 测试工具系统...")
    try:
        from src.memory_manager import MemoryManager
        from src.tools import create_default_tools, ToolRegistry
        
        manager = MemoryManager("./test_workspace", use_openviking=False)
        tools = create_default_tools(manager)
        
        tool_list = tools.list_tools()
        print(f"   ✅ 工具注册成功，共 {len(tool_list)} 个工具:")
        for tool in tool_list:
            print(f"      - {tool['name']}: {tool['description']}")
        
        time_result = tools.execute("get_current_time")
        print(f"   ✅ get_current_time 执行成功: {time_result[:50]}...")
        
        calc_result = tools.execute("calculator", expression="123 + 456")
        print(f"   ✅ calculator 执行成功: {calc_result}")
        
        manager.close()
        return True
    except Exception as e:
        print(f"   ❌ 工具系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_basic():
    """测试智能体基本功能"""
    print("\n5. 测试智能体基本功能...")
    try:
        from src.agent import Agent
        
        agent = Agent(config_path="config/ov.conf", use_openviking=False)
        
        response = agent.chat("你好")
        print(f"   ✅ 智能体响应: {response[:100]}...")
        
        stats = agent.get_stats()
        print(f"   ✅ 智能体统计:")
        print(f"      - 工作空间: {stats['workspace']}")
        print(f"      - 对话轮数: {stats['conversation_turns']}")
        print(f"      - 工具数量: {stats['tools_count']}")
        print(f"      - 记忆统计: {stats['memory_stats']}")
        
        agent.close()
        return True
    except Exception as e:
        print(f"   ❌ 智能体测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_extraction():
    """测试记忆提取功能"""
    print("\n6. 测试记忆提取功能...")
    try:
        from src.memory_manager import MemoryManager
        
        manager = MemoryManager("./test_workspace", use_openviking=False)
        
        test_texts = [
            "我叫张三",
            "我喜欢编程",
            "记住明天的会议"
        ]
        
        for text in test_texts:
            extracted = manager.extract_and_store(text)
            if extracted:
                for mem in extracted:
                    print(f"   ✅ 提取成功: [{mem.category}] {mem.content}")
            else:
                print(f"   ⚠️  未从 '{text}' 提取到记忆")
        
        manager.close()
        return True
    except Exception as e:
        print(f"   ❌ 记忆提取测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup():
    """清理测试工作空间"""
    import shutil
    test_dir = Path("./test_workspace")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("\n测试工作空间已清理")

def main():
    """主测试流程"""
    print("="*60)
    print("OpenViking Agent 功能验证测试")
    print("="*60)
    
    tests = [
        ("模块导入", test_imports),
        ("记忆管理器", test_memory_manager),
        ("OpenViking 客户端", test_openviking_client),
        ("工具系统", test_tools),
        ("智能体基本功能", test_agent_basic),
        ("记忆提取", test_memory_extraction),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 异常退出: {e}")
            results.append((name, False))
    
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有核心功能测试通过！")
        print("\n注意事项:")
        print("- OpenViking 语义检索功能需要配置 API Key")
        print("- 请设置环境变量 DEEPSEEK_API_KEY 或修改 config/ov.conf")
    else:
        print("\n⚠️  部分测试未通过，请检查上述错误信息")
    
    cleanup()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
