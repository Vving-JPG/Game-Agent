"""
检查 OpenViking 集成状态
"""
import sys
sys.path.insert(0, "src")

print("=" * 60)
print("🔍 检查项目集成状态")
print("=" * 60)

# 1. 检查 OpenViking 安装
print("\n1. OpenViking 安装状态")
try:
    import openviking as ov
    print("   ✅ OpenViking 已安装")
    print(f"   📦 版本: {getattr(ov, '__version__', 'unknown')}")
except ImportError:
    print("   ❌ OpenViking 未安装")
    sys.exit(1)

# 2. 检查配置文件
print("\n2. OpenViking 配置")
from pathlib import Path
config_path = Path.home() / ".openviking" / "ov.conf"
if config_path.exists():
    print(f"   ✅ 配置文件存在: {config_path}")
    import json
    with open(config_path, 'r') as f:
        config = json.load(f)
    print(f"   📁 工作空间: {config.get('storage', {}).get('workspace', 'N/A')}")
    print(f"   🔤 Embedding: {config.get('embedding', {}).get('dense', {}).get('model', 'N/A')}")
    print(f"   🤖 VLM: {config.get('vlm', {}).get('model', 'N/A')}")
else:
    print(f"   ❌ 配置文件不存在")

# 3. 检查代码集成
print("\n3. 代码集成状态")
try:
    from memory_manager import MemoryManager, OpenVikingClient
    print("   ✅ memory_manager 模块可导入")
    
    # 测试客户端
    client = OpenVikingClient()
    if client.is_available():
        print("   ✅ OpenVikingClient 可用")
    else:
        print("   ⚠️ OpenVikingClient 不可用")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")

# 4. 检查智能体
print("\n4. 智能体集成")
try:
    from agent import Agent
    print("   ✅ Agent 模块可导入")
    
    # 尝试创建智能体实例
    print("   🔄 创建智能体实例...")
    agent = Agent(use_openviking=True)
    print("   ✅ 智能体创建成功")
    
    stats = agent.get_stats()
    print(f"   📊 OpenViking 启用: {stats.get('memory_stats', {}).get('openviking_enabled', False)}")
    print(f"   💾 记忆数量: {stats.get('memory_stats', {}).get('total', 0)}")
    
    agent.close()
except Exception as e:
    print(f"   ❌ 智能体创建