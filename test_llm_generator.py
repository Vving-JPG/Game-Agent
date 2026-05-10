#!/usr/bin/env python3
"""
LLM 自动生成功能测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.llm_auto_generator import (
    PromptGenerator,
    SkillGenerator,
    LLMAutoGenerator,
    create_llm_generation_prompt
)


def test_prompt_generator():
    """测试提示词生成器"""
    print("=" * 60)
    print("测试提示词生成器")
    print("=" * 60)
    
    generator = PromptGenerator()
    
    result = generator.generate(
        task_type="coding",
        user_requirement="帮我创建一个代码审查助手",
        context_info="用户是一个 Python 开发者，需要审查代码质量和风格"
    )
    
    print(f"\n任务类型: {result['hints']}")
    print(f"\n生成的提示词:\n{result['generated_prompt']}")
    print()


def test_skill_generator():
    """测试技能生成器"""
    print("=" * 60)
    print("测试技能生成器")
    print("=" * 60)
    
    generator = SkillGenerator()
    
    result = generator.generate(
        skill_requirement="创建一个网页搜索工具，能够根据关键词搜索网页内容",
        use_case="用户需要快速获取网页信息"
    )
    
    print(f"\n需求: {result['requirement']}")
    print(f"\n生成的技能生成提示词:\n{result['generated_prompt']}")
    print()


def test_implementation_template():
    """测试实现模板生成"""
    print("=" * 60)
    print("测试实现模板生成")
    print("=" * 60)
    
    generator = SkillGenerator()
    
    params = {
        "query": {
            "type": "string",
            "description": "搜索关键词"
        },
        "limit": {
            "type": "int",
            "description": "返回结果数量",
            "default": 10
        }
    }
    
    template = generator.generate_implementation_template("web_search", params)
    print(f"\n生成的实现模板:\n{template[:800]}...")
    print()


def test_auto_generator():
    """测试自动生成器"""
    print("=" * 60)
    print("测试 LLM 自动生成器")
    print("=" * 60)
    
    generator = LLMAutoGenerator()
    
    print("\n--- 创建提示词 ---")
    result = generator.create_prompt_for_task(
        task_description="一个数据分析助手，可以处理 CSV 文件并生成可视化报表",
        task_type="analysis",
        context="用户是数据分析师，需要处理日常数据"
    )
    print(f"类型: {result['type']}")
    print(f"LLM 输入长度: {len(result['llm_input'])} 字符")
    
    print("\n--- 创建技能 ---")
    result = generator.create_skill_for_task(
        skill_description="CSV 数据处理技能，能够读取、清洗、转换 CSV 数据",
        use_case="日常数据处理任务"
    )
    print(f"类型: {result['type']}")
    print(f"LLM 输入长度: {len(result['llm_input'])} 字符")
    
    print("\n--- 生成历史 ---")
    history = generator.get_generation_history()
    print(f"已生成提示词: {len(history['prompts'])} 个")
    print(f"已生成技能: {len(history['skills'])} 个")


def test_convenience_function():
    """测试便捷函数"""
    print("=" * 60)
    print("测试便捷函数")
    print("=" * 60)
    
    print("\n--- 仅生成提示词 ---")
    prompt = create_llm_generation_prompt(
        task="帮我创建一个游戏攻略助手",
        generation_type="prompt"
    )
    print(f"提示词长度: {len(prompt)} 字符")
    
    print("\n--- 仅生成技能 ---")
    prompt = create_llm_generation_prompt(
        task="帮我创建一个天气查询工具",
        generation_type="skill"
    )
    print(f"提示词长度: {len(prompt)} 字符")
    
    print("\n--- 同时生成 ---")
    prompt = create_llm_generation_prompt(
        task="帮我创建一个翻译助手",
        generation_type="both"
    )
    print(f"提示词长度: {len(prompt)} 字符")


def main():
    """主函数"""
    print("\n🚀 LLM 自动生成功能测试\n")
    
    test_prompt_generator()
    test_skill_generator()
    test_implementation_template()
    test_auto_generator()
    test_convenience_function()
    
    print("\n✅ 所有测试完成！\n")
    print("📝 使用说明:")
    print("1. 使用 generate_prompt 或 generate_skill 工具")
    print("2. 获取 LLM 生成提示词")
    print("3. 将提示词发送给 LLM（如 GPT-4）")
    print("4. LLM 会返回 JSON/YAML 格式的定义")
    print("5. 保存并注册使用")


if __name__ == "__main__":
    main()
