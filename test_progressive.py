#!/usr/bin/env python3
"""
渐进式披露功能测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.progressive_prompts import (
    ProgressivePromptBuilder,
    DisclosureController,
    DisclosureLevel,
    create_progressive_prompt,
    TokenBudget
)


def test_token_budget():
    """测试 Token 预算管理"""
    print("=" * 60)
    print("测试 Token 预算管理")
    print("=" * 60)
    
    budget = TokenBudget(total_budget=4000)
    print(f"初始预算: {budget.total_budget} tokens")
    print(f"已使用: {budget.used_tokens} tokens")
    print(f"剩余: {budget.get_remaining()} tokens")
    
    can_include = budget.can_include(1000)
    print(f"能否包含 1000 字符内容: {can_include}")
    print()


def test_disclosure_levels():
    """测试不同披露层级"""
    print("=" * 60)
    print("测试不同披露层级")
    print("=" * 60)
    
    builder = ProgressivePromptBuilder()
    
    context = {
        "role": "游戏攻略助手",
        "personality": "专业、有趣、热情",
        "entities": {
            "用户姓名": "小明",
            "游戏类型": "RPG"
        },
        "recent_memories": [],
        "available_tools": [],
        "task_type": "simple_qa"
    }
    
    levels = [
        DisclosureLevel.CORE,
        DisclosureLevel.CONTEXT,
        DisclosureLevel.EXTENDED,
        DisclosureLevel.DETAILED
    ]
    
    for level in levels:
        print(f"\n--- {level.name} 层级 ---")
        prompt = builder.build(context, level)
        print(prompt[:300] + "..." if len(prompt) > 300 else prompt)
        print()


def test_adaptive_prompt():
    """测试自适应提示词"""
    print("=" * 60)
    print("测试自适应提示词构建")
    print("=" * 60)
    
    builder = ProgressivePromptBuilder()
    
    contexts = [
        {
            "name": "简单对话",
            "context": {
                "role": "助手",
                "personality": "友好",
                "task_type": "greeting"
            }
        },
        {
            "name": "复杂任务",
            "context": {
                "role": "游戏攻略助手",
                "personality": "专业、有趣",
                "entities": {"用户姓名": "小明", "等级": "50级"},
                "recent_memories": [{"content": "上次讨论了副本攻略", "category": "conversations"}],
                "task_type": "analysis",
                "requires_tools": True
            }
        }
    ]
    
    for item in contexts:
        print(f"\n--- {item['name']} ---")
        prompt = builder.build_adaptive(item["context"])
        print(prompt[:400] + "..." if len(prompt) > 400 else prompt)


def test_disclosure_controller():
    """测试披露控制器"""
    print("=" * 60)
    print("测试披露控制器")
    print("=" * 60)
    
    controller = DisclosureController()
    
    task_types = [
        "greeting",
        "simple_qa",
        "coding",
        "research",
        "debugging"
    ]
    
    for task in task_types:
        level = controller.get_level_for_task(task)
        print(f"{task:15} -> {level.name}")
    
    print("\n历史截断测试:")
    
    history = [
        {"role": "user", "content": "第1轮用户消息"},
        {"role": "assistant", "content": "第1轮助手回复"},
        {"role": "user", "content": "第2轮用户消息"},
        {"role": "assistant", "content": "第2轮助手回复"},
        {"role": "user", "content": "第3轮用户消息"},
        {"role": "assistant", "content": "第3轮助手回复"},
        {"role": "user", "content": "第4轮用户消息"},
        {"role": "assistant", "content": "第4轮助手回复"},
        {"role": "user", "content": "第5轮用户消息"},
        {"role": "assistant", "content": "第5轮助手回复"},
    ]
    
    for level in [DisclosureLevel.CORE, DisclosureLevel.CONTEXT, DisclosureLevel.EXTENDED]:
        controller.current_level = level
        truncated = controller.truncate_history(history)
        print(f"{level.name}: {len(history)} 轮 -> {len(truncated)} 轮")


def test_convenience_function():
    """测试便捷函数"""
    print("=" * 60)
    print("测试便捷函数")
    print("=" * 60)
    
    prompt = create_progressive_prompt(
        user_message="你好，我叫小明",
        entities={"用户姓名": "小明"},
        task_type="greeting"
    )
    
    print("问候场景:")
    print(prompt)
    print()
    
    prompt = create_progressive_prompt(
        user_message="帮我分析一下这个副本",
        entities={"游戏类型": "RPG", "等级": "50级"},
        memories=[{"content": "上次讨论了副本攻略", "category": "conversations"}],
        task_type="analysis"
    )
    
    print("分析场景:")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)


def main():
    """主函数"""
    print("\n🚀 渐进式披露功能测试\n")
    
    test_token_budget()
    test_disclosure_levels()
    test_adaptive_prompt()
    test_disclosure_controller()
    test_convenience_function()
    
    print("\n✅ 所有测试完成！\n")


if __name__ == "__main__":
    main()
