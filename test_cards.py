#!/usr/bin/env python3
"""
卡片系统测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.cards import CardManager, CardType, WorldCard, CharacterCard, SettingCard


def test_card_manager():
    """测试卡片管理器"""
    print("=" * 60)
    print("测试卡片管理器")
    print("=" * 60)
    
    manager = CardManager()
    
    # 获取统计
    stats = manager.get_stats()
    print(f"\n卡片统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 列出所有卡片
    print("\n所有卡片:")
    for card in manager.list_cards():
        print(f"  [{card.card_type.value}] {card.name}")
    
    # 获取特定卡片
    world = manager.get_card("幻想王国")
    if world:
        print(f"\n世界卡 '幻想王国':")
        print(world.to_prompt()[:300] + "...")
    
    char = manager.get_card("亚瑟")
    if char:
        print(f"\n角色卡 '亚瑟' (简洁模式):")
        print(char.to_prompt(mode="short"))
    
    setting = manager.get_card("战斗规则")
    if setting:
        print(f"\n设定卡 '战斗规则':")
        print(setting.to_prompt()[:300] + "...")


def test_scene_builder():
    """测试场景构建器"""
    print("\n" + "=" * 60)
    print("测试场景构建器")
    print("=" * 60)
    
    manager = CardManager()
    
    scene_prompt = manager.build_scene_prompt(
        world_name="幻想王国",
        character_names=["亚瑟"],
        setting_names=["战斗规则"]
    )
    
    print("\n构建的场景提示词:")
    print(scene_prompt[:800] + "..." if len(scene_prompt) > 800 else scene_prompt)


def test_create_new_card():
    """测试创建新卡片"""
    print("\n" + "=" * 60)
    print("测试创建新卡片")
    print("=" * 60)
    
    manager = CardManager()
    
    # 创建新角色
    new_char = CharacterCard(
        name="测试法师",
        description="一个测试用的法师角色",
        role="配角",
        personality={"聪明": "智商很高", "冷静": "遇事不慌"},
        abilities=[{"name": "火球术", "description": "发射火球"}]
    )
    
    manager.save_card(new_char)
    print(f"✅ 已创建角色卡: {new_char.name}")
    
    # 验证
    loaded = manager.get_card("测试法师")
    if loaded:
        print(f"✅ 成功加载角色卡: {loaded.name}")
        print(f"   角色定位: {loaded.role}")


def main():
    """主函数"""
    print("\n🚀 卡片系统测试\n")
    
    test_card_manager()
    test_scene_builder()
    test_create_new_card()
    
    print("\n✅ 所有测试完成！\n")


if __name__ == "__main__":
    main()
