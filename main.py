#!/usr/bin/env python3
"""
RPG Game Agent — 终端 TUI RPG 游戏入口

支持三种模式：
- 游戏模式（默认）：python main.py
- 模板编辑模式：python main.py --template
- 存档管理：python main.py --saves

启动流程：欢迎界面 → 世界概念输入 → LLM 生成世界 → 游戏主循环
"""

from __future__ import annotations

import os
import sys
import argparse
from typing import List

# 确保项目根在 path 中
_project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _project_root)

from src.game_engine import GameEngine
from src.tui import TUIRenderer, SimpleRenderer, RICH_AVAILABLE
from src.save_manager import SaveManager

# 尝试导入 rich Live
Live = None
if RICH_AVAILABLE:
    try:
        from rich.live import Live as RichLive
        Live = RichLive
    except ImportError:
        pass


def run_game_mode(engine: GameEngine, renderer: TUIRenderer):
    """游戏主循环"""
    # ── 世界初始化 ──
    print()
    for line in renderer.render_welcome():
        print(line)
    print()

    world_concept = input("🌍 请输入你的世界概念（留空使用默认）: ").strip()
    if not world_concept:
        world_concept = "一个传统的中古奇幻世界，剑与魔法的时代，人类王国与兽人部落对峙"
        print(f"📝 使用默认: {world_concept}")

    logs = engine.init_world(world_concept)
    for line in logs:
        print(line)

    # ── 生成初始场景 ──
    print("\n⏳ 正在生成起始场景...")
    from src.game_world import SceneState
    start_id = engine.world.world_card.starting_scene_id
    logs = engine._travel_to(start_id)
    SimpleRenderer.render(logs)

    # ── 主循环 ──
    print("\n输入命令开始冒险（输入 /help 查看帮助）:\n")

    # Rich TUI 或纯文本循环
    if renderer.use_rich and Live:
        _run_rich_loop(engine, renderer)
    else:
        _run_text_loop(engine, renderer)


def _run_rich_loop(engine: GameEngine, renderer: TUIRenderer):
    """Rich Live 循环"""
    from rich.live import Live as RL
    layout = renderer._render_rich(engine, [])
    with RL(layout, console=renderer.console, refresh_per_second=4,
            screen=True) as live:
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input:
                continue

            # 退出命令
            if user_input in (":q", ":quit", "exit"):
                break
            if user_input in (":wq", ":x"):
                engine.saves.save_game(engine.world, "auto")
                print("💾 已自动保存。")
                break
            if user_input == ":tpl":
                print("模板编辑模式请在 --template 下启动。")
                continue

            logs = engine.process_turn(user_input)
            layout = renderer._render_rich(engine, logs)
            live.update(layout)


def _run_text_loop(engine: GameEngine, renderer: TUIRenderer):
    """纯文本循环"""
    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input in (":q", ":quit", "exit"):
            break
        if user_input in (":wq", ":x"):
            engine.saves.save_game(engine.world, "auto")
            print("💾 已自动保存。")
            break
        if user_input == ":tpl":
            print("模板编辑模式请在 --template 下启动。")
            continue

        logs = engine.process_turn(user_input)
        SimpleRenderer.render(logs)

    for line in renderer.render_goodbye():
        print(line)


def run_template_mode():
    """模板编辑模式"""
    from src.content_generator import ContentGenerator
    from src.template_editor import TemplateEditor

    gen = ContentGenerator()
    editor = TemplateEditor(gen)
    editor.start_collab_loop()


def run_saves_mode():
    """存档管理模式"""
    saves = SaveManager()
    all_saves = saves.list_saves()

    if not all_saves:
        print("📭 没有存档。")
        return

    print("📁 存档列表:\n")
    for s in all_saves:
        print(f"  [{s['slot']}] Lv{s['player_level']} {s['player_name']} "
              f"@{s['scene_name']} 第{s['game_day']}天")
        print(f"       {s['timestamp'][:19]}")
        print()

    print("输入槽位名加载，输入 d:<槽位> 删除，输入 q 退出。")
    while True:
        try:
            cmd = input("saves> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        if cmd == "q":
            break
        if cmd.startswith("d:"):
            slot = cmd[2:].strip()
            if saves.delete_save(slot):
                print(f"🗑 已删除存档 [{slot}]")
            else:
                print(f"❌ 删除失败")
            continue

        # 加载
        world = saves.load_game(cmd)
        if world:
            print(f"✅ 已加载 [{cmd}] — Lv{world.player.level} "
                  f"{world.player.name} @ {world.player.current_scene_id}")
            print("使用 python main.py --load " + cmd + " 进入游戏。")
        else:
            print(f"❌ 存档 [{cmd}] 不存在。")


def main():
    parser = argparse.ArgumentParser(description="RPG Game Agent - 光锥驱动 TUI RPG")
    parser.add_argument("--template", "-t", action="store_true",
                       help="进入模板编辑模式")
    parser.add_argument("--saves", "-s", action="store_true",
                       help="查看/管理存档")
    parser.add_argument("--load", "-l", type=str, default="",
                       help="加载指定槽位的存档进入游戏")
    parser.add_argument("--no-rich", action="store_true",
                       help="禁用 Rich TUI（使用纯文本模式）")
    args = parser.parse_args()

    # 模板模式
    if args.template:
        run_template_mode()
        return

    # 存档管理
    if args.saves:
        run_saves_mode()
        return

    # 游戏模式
    renderer = TUIRenderer(use_rich=not args.no_rich)
    engine = GameEngine()

    # 加载存档
    if args.load:
        saves = SaveManager()
        world = saves.load_game(args.load)
        if world:
            engine.world = world
            engine.lightcone.__init__(world)
            engine.quests.load_from_world(world.global_state.get("quests", {}))
            print(f"📂 已加载存档 [{args.load}]")
            scene = engine.world.get_current_scene()
            if scene:
                logs = engine._render_scene(scene)
                SimpleRenderer.render(logs)
        else:
            print(f"❌ 存档 [{args.load}] 不存在。")
            return
    else:
        run_game_mode(engine, renderer)
        return

    # 从存档继续游戏
    print("\n输入命令继续冒险:\n")
    if renderer.use_rich and Live:
        _run_rich_loop(engine, renderer)
    else:
        _run_text_loop(engine, renderer)


if __name__ == "__main__":
    main()
