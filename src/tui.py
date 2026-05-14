"""
TUI 界面渲染 — 基于 rich 库的终端 RPG 界面。

提供两种模式：
- TUI 模式：使用 rich.Layout 渲染面板式界面
- 纯文本模式：回退到 print 输出（无 rich 依赖时）
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from src.game_world import Player, Scene, DIRECTION_CN
from src.combat_system import CombatState, CombatResult

if TYPE_CHECKING:
    from src.game_engine import GameEngine

RICH_AVAILABLE = False
Console = None
Layout = None
Panel = None
Live = None

try:
    from rich.console import Console as RichConsole
    from rich.layout import Layout as RichLayout
    from rich.panel import Panel as RichPanel
    from rich.live import Live as RichLive
    from rich.table import Table
    from rich.text import Text
    from rich import box
    Console = RichConsole
    Layout = RichLayout
    Panel = RichPanel
    Live = RichLive
    RICH_AVAILABLE = True
except ImportError:
    pass


class TUIRenderer:
    """TUI 界面渲染器"""

    def __init__(self, use_rich: bool = True):
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()
        self._last_output: List[str] = []

    def render(self, engine: "GameEngine", logs: List[str]) -> str:
        """渲染界面，返回字符串（TUI 模式直接输出到终端）"""
        if self.use_rich:
            return self._render_rich(engine, logs)
        else:
            return self._render_text(engine, logs)

    def render_welcome(self) -> List[str]:
        """渲染欢迎界面"""
        lines = [
            "╔══════════════════════════════════════════╗",
            "║         🗡️  RPG Game Agent              ║",
            "║     光锥驱动 · LLM 实时生成 · TUI       ║",
            "╠══════════════════════════════════════════╣",
            "║  输入世界概念开始冒险，例如:             ║",
            "║    「一个被龙族统治的中古奇幻世界」       ║",
            "║    「灵气复苏的现代都市」                ║",
            "║    「崩塌纪元的末日废土」                ║",
            "╠══════════════════════════════════════════╣",
            "║  特殊命令:                               ║",
            "║    :wq  保存并退出                       ║",
            "║    :q   直接退出                         ║",
            "║    :tpl 进入模板编辑模式                 ║",
            "╚══════════════════════════════════════════╝",
        ]
        return lines

    def render_goodbye(self) -> List[str]:
        return ["👋 冒险暂告一段落，后会有期。"]

    # ═══════════════════════════════════════════════════════════
    # Rich TUI
    # ═══════════════════════════════════════════════════════════

    def _render_rich(self, engine: "GameEngine", logs: List[str]) -> str:
        """使用 rich 渲染面板式界面"""
        player = engine.world.player
        scene = engine.world.get_current_scene()
        combat = engine.combat_state
        in_combat = combat is not None and combat.result == CombatResult.ONGOING

        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        layout["body"].split_row(
            Layout(name="main", ratio=2),
            Layout(name="sidebar", ratio=1),
        )

        # Header
        layout["header"].update(self._rich_header(player))

        # Main
        if in_combat:
            layout["main"].update(self._rich_combat(combat))
        elif scene:
            layout["main"].update(self._rich_scene(scene, engine))
        else:
            layout["main"].update(Panel("等待世界初始化...", title="🌍"))

        # Sidebar
        layout["sidebar"].update(self._rich_sidebar(player, engine))

        # Footer
        output_text = "\n".join(logs[-8:]) if logs else "输入命令开始冒险..."
        layout["footer"].update(Panel(output_text, title="📜 日志"))

        return layout  # 返回 layout 对象供 Live display

    def _rich_header(self, player: Player) -> Panel:
        """顶部状态栏"""
        hp_pct = player.hp / max(player.max_hp, 1)
        mp_pct = player.mp / max(player.max_mp, 1)
        hp_bar = self._bar(hp_pct, 10)
        mp_bar = self._bar(mp_pct, 8)

        text = (
            f"🦸 {player.name}  Lv.{player.level} | "
            f"❤️ HP: {player.hp}/{player.max_hp} {hp_bar} | "
            f"💎 MP: {player.mp}/{player.max_mp} {mp_bar} | "
            f"💰 {player.gold}G | "
            f"⚔️ {player.effective_attack} | "
            f"🛡️ {player.effective_defense} | "
            f"📅 第{player.game_day}天"
        )
        return Panel(text, title=f"🗡️ {engine.world.world_card.name}")

    def _rich_scene(self, scene: Scene, engine: "GameEngine") -> Panel:
        """场景面板"""
        lines = []
        lines.append(f"[bold cyan]{scene.name}[/bold cyan]")
        lines.append(f"  {scene.description}")
        if scene.atmosphere:
            lines.append(f"  [dim]🌫 {scene.atmosphere}[/dim]")
        lines.append("")

        # NPC
        for npc in scene.npcs:
            icon = "⚔️" if npc.is_hostile else "👤"
            lines.append(f"  {icon} [yellow]{npc.name}[/yellow] [{npc.role}]")

        # Items
        for item in scene.items:
            lines.append(f"  💎 [green]{item.name}[/green] - {item.description[:30]}")

        # Exits
        if scene.exits:
            exits = []
            for d, nid in scene.exits.items():
                cn = DIRECTION_CN.get(d, d)
                neighbor = engine.world.get_scene(nid)
                label = neighbor.name if neighbor else nid
                exits.append(f"[bold]{cn}[/bold]({label})")
            lines.append(f"  🚪 {' | '.join(exits)}")

        return Panel("\n".join(lines), title="📍 当前场景")

    def _rich_combat(self, combat: CombatState) -> Panel:
        """战斗面板"""
        lines = [f"[bold red]⚔️ 第 {combat.turn} 回合[/bold red]", ""]
        lines.append(f"[cyan]🦸 {combat.player.name}[/cyan]  "
                    f"HP: {combat.player.hp}/{combat.player.max_hp}")
        for i, enemy in enumerate(combat.enemies):
            if enemy.is_alive():
                status = "[yellow]🛡️防御[/yellow]" if enemy.is_defending else ""
                lines.append(f"[red]👹 [{i+1}] {enemy.name}[/red]  "
                           f"HP: {enemy.hp}/{enemy.max_hp} {status}")
        lines.append("")
        lines.append("攻击1 / 防御 / 物品 / 逃跑")
        return Panel("\n".join(lines), title="⚔️ 战斗")

    def _rich_sidebar(self, player: Player, engine: "GameEngine") -> Panel:
        """侧边栏"""
        lines = [f"[bold]背包 ({len(player.inventory)})[/bold]"]
        for i, item in enumerate(player.inventory[-6:]):
            lines.append(f"  [{i+1}] {item.name}")

        lines.append("")
        lines.append("[bold]装备[/bold]")
        slots = {"weapon": "武器", "armor": "防具", "accessory": "饰品"}
        for slot, cn in slots.items():
            eq = player.equipment.get(slot)
            lines.append(f"  {cn}: {eq.name if eq else '-'}")

        lines.append("")
        active_quests = engine.quests.get_active_quests(player)
        if active_quests:
            lines.append(f"[bold]任务 ({len(active_quests)})[/bold]")
            for q in active_quests[:3]:
                lines.append(f"  📋 {q.name}")

        return Panel("\n".join(lines), title="📊 状态")

    def _bar(self, pct: float, width: int) -> str:
        filled = int(pct * width)
        empty = width - filled
        color = "green" if pct > 0.5 else "yellow" if pct > 0.25 else "red"
        return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"

    # ═══════════════════════════════════════════════════════════
    # 纯文本渲染
    # ═══════════════════════════════════════════════════════════

    def _render_text(self, engine: "GameEngine", logs: List[str]) -> str:
        """纯文本渲染，返回字符串"""
        player = engine.world.player
        scene = engine.world.get_current_scene()
        combat = engine.combat_state
        in_combat = combat is not None and combat.result == CombatResult.ONGOING

        lines = []

        # Header
        lines.append(f"╔══ {engine.world.world_card.name} ══╗")
        hp_pct = player.hp / max(player.max_hp, 1)
        hp_bar = "█" * int(hp_pct * 10) + "░" * (10 - int(hp_pct * 10))
        lines.append(f"║ Lv.{player.level} {player.name}  "
                    f"HP:[{hp_bar}] {player.hp}/{player.max_hp}  "
                    f"💰{player.gold}G  ⚔{player.effective_attack}  "
                    f"🛡{player.effective_defense}  📅第{player.game_day}天")
        lines.append("╠" + "═" * 40)

        # Body
        if in_combat:
            lines.append(f"⚔️ 第{combat.turn}回合")
            lines.append(f"  🦸 {combat.player.name} HP:{combat.player.hp}")
            for i, e in enumerate(combat.enemies):
                if e.is_alive():
                    lines.append(f"  👹 [{i+1}] {e.name} HP:{e.hp}")
            lines.append("")
            lines.append("  攻击1 / 防御 / 物品 / 逃跑")
        elif scene:
            lines.append(f"📍 {scene.name}")
            lines.append(f"   {scene.description}")
            if scene.atmosphere:
                lines.append(f"   🌫 {scene.atmosphere}")
            for npc in scene.npcs:
                icon = "⚔️" if npc.is_hostile else "👤"
                lines.append(f"  {icon} {npc.name} [{npc.role}]")
            for item in scene.items:
                lines.append(f"  💎 {item.name}")
            if scene.exits:
                exits = []
                for d, nid in scene.exits.items():
                    cn = DIRECTION_CN.get(d, d)
                    n = engine.world.get_scene(nid)
                    exits.append(f"{cn}({n.name if n else nid})")
                lines.append(f"  🚪 {' | '.join(exits)}")

        # Footer
        lines.append("╠" + "═" * 40)
        for log in logs[-6:]:
            lines.append(f"  {log}")
        lines.append("╚" + "═" * 40)

        return "\n".join(lines)


class SimpleRenderer:
    """最简渲染器 — 无 rich 依赖，直接 print"""

    @staticmethod
    def render(lines: List[str]):
        for line in lines:
            print(line)
        print()
