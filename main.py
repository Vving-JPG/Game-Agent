#!/usr/bin/env python3
"""
RPG 游戏内容生成器

基于 OpenViking 的 RPG 游戏道具、NPC、任务生成工具
"""

import sys
import argparse
import json
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.rpg_generator import RPGGenerator
from src.text_renderer import renderer


def print_banner():
    """打印欢迎信息"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                   RPG 游戏内容生成器                          ║
║              基于 OpenViking 的智能生成工具                   ║
╚══════════════════════════════════════════════════════════════╝
    """
    renderer.show_instant(banner)


def interactive_mode(generator: RPGGenerator):
    """交互式生成模式"""
    print_banner()
    renderer.show("生成器已启动！输入 /help 查看可用命令，输入 exit 退出。\n")
    
    while True:
        try:
            # 获取用户输入
            user_input = input("你 > ").strip()
            
            # 空输入跳过
            if not user_input:
                continue
            
            # 退出命令
            if user_input.lower() in ["exit", "quit", "退出"]:
                renderer.show("\n感谢使用，再见！")
                break
            
            # 帮助命令
            if user_input.lower() in ["/help", "帮助"]:
                help_text = """
可用命令:
  /item <等级> <稀有度> [类型]     - 生成道具
  /npc <地点> <角色定位> [重要程度] - 生成NPC
  /quest <类型> <难度> <等级> <地点> - 生成任务
  /search <关键词>                  - 搜索记忆库
  /help                            - 显示帮助
  exit/quit/退出                    - 退出程序

示例:
  /item 5 稀有 武器
  /npc 边境小镇 商人 次要
  /quest 支线 普通 5 森林
  /search 火焰
"""
                renderer.show_instant(help_text)
                continue
            
            # 生成道具
            if user_input.startswith("/item"):
                parts = user_input.split(maxsplit=3)
                if len(parts) < 3:
                    renderer.show("用法: /item <等级> <稀有度> [类型]")
                    continue
                level = int(parts[1])
                rarity = parts[2]
                item_type = parts[3] if len(parts) > 3 else "武器"
                result = generator.generate_item(level, rarity, item_type)
                renderer.show_instant(f"\n🎁 生成道具:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n")
                continue
            
            # 生成NPC
            if user_input.startswith("/npc"):
                parts = user_input.split(maxsplit=3)
                if len(parts) < 3:
                    renderer.show("用法: /npc <地点> <角色定位> [重要程度]")
                    continue
                location = parts[1]
                role = parts[2]
                importance = parts[3] if len(parts) > 3 else "次要"
                result = generator.generate_npc(location, role, importance)
                renderer.show_instant(f"\n👤 生成NPC:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n")
                continue
            
            # 生成任务
            if user_input.startswith("/quest"):
                parts = user_input.split(maxsplit=4)
                if len(parts) < 4:
                    renderer.show("用法: /quest <类型> <难度> <玩家等级> <地点>")
                    continue
                quest_type = parts[1]
                difficulty = parts[2]
                level = int(parts[3])
                location = parts[4] if len(parts) > 4 else "森林"
                result = generator.generate_quest(quest_type, difficulty, level, location)
                renderer.show_instant(f"\n📜 生成任务:\n{json.dumps(result, ensure_ascii=False, indent=2)}\n")
                continue
            
            # 搜索记忆
            if user_input.startswith("/search"):
                keyword = user_input[7:].strip()
                if not keyword:
                    renderer.show("用法: /search <关键词>")
                    continue
                results = generator.search_memories(keyword)
                renderer.show_instant(f"\n🔍 搜索结果:\n{json.dumps(results, ensure_ascii=False, indent=2)}\n")
                continue
            
            # 默认：智能生成
            response = generator.chat(user_input)
            renderer.show(f"\n🤖 {response}\n")
            
        except KeyboardInterrupt:
            renderer.show("\n\n检测到中断，正在退出...")
            break
        except Exception as e:
            renderer.show(f"\n❌ 错误: {e}\n")


def print_help():
    """打印帮助信息"""
    help_text = """
可用命令:
  /item <等级> <稀有度> [类型]     - 生成道具
  /npc <地点> <角色定位> [重要程度] - 生成NPC
  /quest <类型> <难度> <等级> <地点> - 生成任务
  /search <关键词>                  - 搜索记忆库
  /help                            - 显示帮助
  exit/quit/退出                    - 退出程序

示例:
  /item 5 稀有 武器
  /npc 边境小镇 商人 次要
  /quest 支线 普通 5 森林
  /search 火焰
"""
    print(help_text)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="RPG 游戏内容生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                    # 启动交互式模式
  python main.py -i 5 稀有 武器      # 生成道具
  python main.py -n 边境小镇 商人    # 生成NPC
  python main.py -q 支线 普通 5 森林 # 生成任务
        """
    )
    
    parser.add_argument(
        "-c", "--config",
        default="openviking_workspace/ov.conf",
        help="OpenViking 配置文件路径"
    )
    
    parser.add_argument(
        "-i", "--item",
        nargs="*",
        help="生成道具: <等级> <稀有度> [类型]"
    )
    
    parser.add_argument(
        "-n", "--npc",
        nargs="*",
        help="生成NPC: <地点> <角色定位> [重要程度]"
    )
    
    parser.add_argument(
        "-q", "--quest",
        nargs="*",
        help="生成任务: <类型> <难度> <等级> <地点>"
    )
    
    args = parser.parse_args()
    
    try:
        # 初始化生成器
        generator = RPGGenerator(config_path=args.config)
        
        # 生成道具模式
        if args.item:
            level = int(args.item[0]) if len(args.item) > 0 else 1
            rarity = args.item[1] if len(args.item) > 1 else "普通"
            item_type = args.item[2] if len(args.item) > 2 else "武器"
            result = generator.generate_item(level, rarity, item_type)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        
        # 生成NPC模式
        if args.npc:
            location = args.npc[0] if len(args.npc) > 0 else "村庄"
            role = args.npc[1] if len(args.npc) > 1 else "村民"
            importance = args.npc[2] if len(args.npc) > 2 else "次要"
            result = generator.generate_npc(location, role, importance)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        
        # 生成任务模式
        if args.quest:
            quest_type = args.quest[0] if len(args.quest) > 0 else "支线"
            difficulty = args.quest[1] if len(args.quest) > 1 else "普通"
            level = int(args.quest[2]) if len(args.quest) > 2 else 1
            location = args.quest[3] if len(args.quest) > 3 else "森林"
            result = generator.generate_quest(quest_type, difficulty, level, location)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        
        # 交互式模式
        interactive_mode(generator)
        
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
