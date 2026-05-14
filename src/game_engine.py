"""
游戏引擎 — 主循环，串联所有系统：光锥、场景生成、交互、战斗、任务、存档。

命令解析 → 逻辑处理 → 内容生成 → 状态更新 → 渲染输出
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List, Optional, Tuple

from src.game_world import (
    GameWorld, LightCone, Scene, SceneState, Player, Item, NPC,
    DIRECTIONS, DIRECTION_CN, OPPOSITE,
)
from src.content_generator import ContentGenerator
from src.combat_system import CombatSystem, CombatState, CombatResult
from src.quest_system import QuestSystem, Quest, QuestObjective, QuestReward
from src.item_system import ItemSystem
from src.save_manager import SaveManager


# ═══════════════════════════════════════════════════════════════
# 命令解析器
# ═══════════════════════════════════════════════════════════════

class CommandParser:
    """用户输入解析 — 自然语言 → 结构化动作"""

    # 移动关键词
    MOVE_KEYWORDS = {
        "北": "north", "north": "north", "n": "north",
        "南": "south", "south": "south", "s": "south",
        "东": "east", "east": "east", "e": "east",
        "西": "west", "west": "west", "w": "west",
        "上": "up", "up": "up", "u": "up",
        "下": "down", "down": "down", "d": "down",
    }

    GO_PATTERNS = ["前往", "去", "走向", "进入", "向", "go", "move"]

    @classmethod
    def parse(cls, raw: str, current_scene: Optional[Scene] = None) -> dict:
        """解析命令，返回 {action, params}"""
        raw = raw.strip()
        lower = raw.lower()

        # ── 系统命令 ──
        if raw.startswith("/"):
            return cls._parse_system(raw[1:])

        # ── 移动 ──
        move_result = cls._parse_move(raw, lower, current_scene)
        if move_result:
            return move_result

        # ── 交互 ──
        talk_result = cls._parse_talk(raw, lower, current_scene)
        if talk_result:
            return talk_result

        # ── 拾取/拿取 ──
        pickup_result = cls._parse_pickup(raw, lower, current_scene)
        if pickup_result:
            return pickup_result

        # ── 查看 ──
        look_result = cls._parse_look(raw, lower)
        if look_result:
            return look_result

        # ── 默认 → 自由文本 ──
        return {"action": "free_text", "text": raw}

    @classmethod
    def _parse_system(cls, cmd: str) -> dict:
        parts = cmd.split(maxsplit=1)
        name = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        return {"action": f"sys_{name}", "arg": arg}

    @classmethod
    def _parse_move(cls, raw: str, lower: str, scene: Optional[Scene]) -> Optional[dict]:
        # 方向词
        direction = cls.MOVE_KEYWORDS.get(lower)
        if direction:
            return cls._make_move(direction, scene)
        direction = cls.MOVE_KEYWORDS.get(raw)
        if direction:
            return cls._make_move(direction, scene)

        # "前往 X" 模式
        for pattern in cls.GO_PATTERNS:
            if pattern in lower:
                after = lower.split(pattern, 1)[-1].strip()
                direction = cls.MOVE_KEYWORDS.get(after)
                if direction:
                    return cls._make_move(direction, scene)
                # 尝试匹配场景名
                if scene:
                    for d, nid in scene.exits.items():
                        cn = DIRECTION_CN.get(d, d)
                        if cn in after or d in after:
                            return cls._make_move(d, scene)

        return None

    @classmethod
    def _make_move(cls, direction: str, scene: Optional[Scene]) -> dict:
        """验证方向是否有效"""
        if scene and direction not in scene.exits:
            cn = DIRECTION_CN.get(direction, direction)
            return {"action": "invalid", "reason": f"那个方向（{cn}）没有路。"}
        return {"action": "move", "direction": direction}

    @classmethod
    def _parse_talk(cls, raw: str, lower: str, scene: Optional[Scene]) -> Optional[dict]:
        if not scene:
            return None
        talk_prefixes = ["对话", "交谈", "询问", "问", "talk", "speak"]
        for prefix in talk_prefixes:
            if lower.startswith(prefix):
                npc_name = lower[len(prefix):].strip()
                if npc_name:
                    return {"action": "talk", "target": npc_name, "text": raw}
                return {"action": "talk_prompt", "text": "你想和谁对话？"}

        # "与 X 对话"
        if "与" in raw and "对话" in raw:
            parts = raw.split("与", 1)[-1].split("对话", 1)[0].strip()
            if parts:
                return {"action": "talk", "target": parts, "text": raw}

        return None

    @classmethod
    def _parse_pickup(cls, raw: str, lower: str, scene: Optional[Scene]) -> Optional[dict]:
        pickup_keys = ["捡起", "拾取", "拿起", "拿", "pick", "take", "grab"]
        for key in pickup_keys:
            if key in lower:
                item_name = lower.split(key, 1)[-1].strip()
                return {"action": "pickup", "target": item_name if item_name else None}
        return None

    @classmethod
    def _parse_look(cls, raw: str, lower: str) -> Optional[dict]:
        look_keys = ["查看", "观察", "环顾", "look", "inspect", "examine"]
        for key in look_keys:
            if lower.startswith(key) or lower == key:
                after = lower[len(key):].strip()
                return {"action": "look", "target": after if after else "scene"}
        return None


# ═══════════════════════════════════════════════════════════════
# 游戏引擎
# ═══════════════════════════════════════════════════════════════

class GameEngine:
    """RPG 游戏引擎 — 主循环"""

    def __init__(
        self,
        content_generator: Optional[ContentGenerator] = None,
        save_dir: str = "saves",
    ):
        self.world = GameWorld(save_dir=save_dir)
        self.lightcone = LightCone(self.world, observation_range=1)
        self.generator = content_generator or ContentGenerator()
        self.combat = CombatSystem(self.generator)
        self.quests = QuestSystem()
        self.items = ItemSystem()
        self.saves = SaveManager(save_dir)
        self.running = False

        # 战斗子状态
        self.combat_state: Optional[CombatState] = None

    # ═══════════════════════════════════════════════════════════
    # 世界初始化
    # ═══════════════════════════════════════════════════════════

    def init_world(self, world_concept: str) -> List[str]:
        """根据用户概念初始化世界，返回日志"""
        logs = []
        logs.append(f"🌍 正在生成世界: {world_concept}")

        data = self.generator.generate_world(world_concept)
        if not data:
            logs.append("❌ 世界生成失败，请重试。")
            return logs

        self.world.world_card.name = data.get("name", world_concept)
        self.world.world_card.theme = data.get("theme", "")
        self.world.world_card.era = data.get("era", "")
        self.world.world_card.geography = data.get("geography", "")
        self.world.world_card.factions = data.get("factions", [])
        self.world.world_card.magic_system = data.get("magic_system", "")

        starting = data.get("starting_scene", {})
        start_id = "scene_start"
        self.world.world_card.starting_scene_id = start_id

        # 创建起始场景
        start_scene = Scene(
            name=starting.get("name", "起始之地"),
            description=starting.get("description", "你的旅程从这里开始。"),
            atmosphere=starting.get("atmosphere", "平静"),
            exits={},
        )
        self.world.add_scene(start_id, start_scene)
        self.world.set_player_scene(start_id)
        self.lightcone.current_scene_id = start_id

        logs.append(f"✅ 世界「{self.world.world_card.name}」已生成")
        logs.append(f"📍 起始场景: {start_scene.name}")
        if self.world.world_card.theme:
            logs.append(f"🎭 主题: {self.world.world_card.theme}")
        if self.world.world_card.factions:
            logs.append(f"🏛 势力: {', '.join(self.world.world_card.factions)}")

        return logs

    # ═══════════════════════════════════════════════════════════
    # 命令执行
    # ═══════════════════════════════════════════════════════════

    def execute(self, raw_input: str) -> List[str]:
        """执行玩家输入，返回输出行列表"""
        if self.combat_state and self.combat_state.result == CombatResult.ONGOING:
            return self._handle_combat_input(raw_input)

        cmd = CommandParser.parse(raw_input, self.world.get_current_scene())
        action = cmd["action"]

        if action == "move":
            return self._do_move(cmd["direction"])
        elif action == "talk":
            return self._do_talk(cmd.get("target", ""), cmd.get("text", raw_input))
        elif action == "talk_prompt":
            return ["你想和谁对话？"]
        elif action == "pickup":
            return self._do_pickup(cmd.get("target", ""))
        elif action == "look":
            return self._do_look(cmd.get("target", "scene"))
        elif action == "invalid":
            return [f"⚠️ {cmd['reason']}"]
        elif action.startswith("sys_"):
            return self._handle_system(cmd["action"][4:], cmd.get("arg", ""))
        elif action == "free_text":
            return self._handle_free_text(cmd["text"])
        else:
            return [f"未知动作: {action}"]

    # ── 移动 ──

    def _do_move(self, direction: str) -> List[str]:
        scene = self.world.get_current_scene()
        if not scene:
            return ["当前没有场景。"]

        target_id = scene.exits.get(direction)
        if not target_id:
            cn = DIRECTION_CN.get(direction, direction)
            return [f"⚠️ {cn}方向没有路。"]

        return self._travel_to(target_id)

    def _travel_to(self, scene_id: str) -> List[str]:
        """移动到指定场景，触发光锥和生成"""
        logs = []

        # 光锥更新
        to_gen_full, to_gen_skeleton = self.lightcone.move_to(scene_id)
        self.world.set_player_scene(scene_id)

        # 完整生成当前场景
        if to_gen_full:
            for sid in to_gen_full:
                scene = self.generator.generate_full_scene(
                    sid,
                    self.world.world_card.to_prompt(),
                    self.world.get_neighbor_names(sid),
                    self.world.player.to_dict(),
                )
                if scene:
                    self.world.add_scene(sid, scene)
                    logs.append(f"✨ 探索了新区域: {scene.name}")

        # 骨架生成邻居
        for sid in to_gen_skeleton:
            skeleton = self.generator.generate_scene_skeleton(
                sid, self.world.world_card.to_prompt()
            )
            if skeleton:
                # 注册邻居为预生成场景
                self.world.add_scene(sid, Scene(
                    name=skeleton.name,
                    description=skeleton.description,
                    state=SceneState.PRE_GENERATED,
                ))
                logs.append(f"👁 远处隐约可见: {skeleton.name}")

        # 推进 quest reach 目标
        self.quests.progress_reach(scene_id, self.world.player)

        # 输出当前场景
        current = self.world.get_current_scene()
        if current:
            current.visit_count += 1
            logs.append("")
            logs.extend(self._render_scene(current))

        return logs

    # ── 对话 ──

    def _do_talk(self, target: str, raw_text: str) -> List[str]:
        scene = self.world.get_current_scene()
        if not scene:
            return ["当前没有可对话的对象。"]

        # 查找 NPC
        npc = None
        for n in scene.npcs:
            if target in n.name or n.name in target:
                npc = n
                break
        if not npc:
            # 模糊匹配
            for n in scene.npcs:
                if any(c in n.name for c in target):
                    npc = n
                    break
        if not npc:
            return [f"这里没有叫「{target}」的人。"]

        # 检查敌对
        if npc.is_hostile:
            return self._start_combat_from_npc(npc)

        # 生成对话
        context = f"场景: {scene.name} - {scene.description}"
        dialogue = self.generator.generate_npc_dialogue(npc, raw_text, context)
        npc.memory.append(raw_text)

        # 推进 quest talk 目标
        self.quests.progress_talk(npc.name, self.world.player)

        return [f"💬 {npc.name}: {dialogue}"]

    # ── 拾取 ──

    def _do_pickup(self, target: str) -> List[str]:
        scene = self.world.get_current_scene()
        if not scene:
            return ["当前没有可拾取的物品。"]

        if not target:
            # 列出可拾取物品
            if not scene.items:
                return ["地上没有值得注意的东西。"]
            lines = ["地上可以看到:"]
            for item in scene.items:
                lines.append(f"  · {item.name} - {item.description}")
            return lines

        # 查找物品
        found = None
        for item in scene.items:
            if target in item.name or item.name in target:
                found = item
                break
        if not found:
            return [f"这里没有「{target}」。"]

        # 拾取
        success, msg = self.items.pickup_item(self.world.player, found)
        if success:
            scene.items.remove(found)
            self.quests.progress_collect(found.name, self.world.player)

        return [msg]

    # ── 查看 ──

    def _do_look(self, target: str) -> List[str]:
        scene = self.world.get_current_scene()
        if not scene:
            return ["你什么都看不到。"]

        if target == "scene" or not target:
            return self._render_scene(scene)

        # 查看特定对象
        npc = scene.get_npc(target)
        if npc:
            return [
                f"【{npc.name}】{npc.role}",
                f"  {npc.personality}" if npc.personality else "",
                f"  HP: {npc.hp}" + (" ⚔️敌对" if npc.is_hostile else ""),
            ]

        for item in scene.items:
            if target in item.name:
                return [f"【{item.name}】{item.rarity}", f"  {item.description}"]

        return [f"你仔细看了看「{target}」，没发现什么特别的。"]

    # ── 系统命令 ──

    def _handle_system(self, cmd: str, arg: str) -> List[str]:
        if cmd == "save":
            slot = arg or "auto"
            ok = self.saves.save_game(self.world, slot)
            return [f"💾 已保存到槽位 [{slot}]" if ok else "❌ 保存失败"]

        elif cmd == "load":
            slot = arg or "auto"
            world = self.saves.load_game(slot)
            if world:
                self.world = world
                self.lightcone = LightCone(self.world)
                self.quests.load_from_world(world.global_state.get("quests", {}))
                scene = self.world.get_current_scene()
                return [f"📂 已加载存档 [{slot}]", f"📍 {scene.name if scene else '?'}"]
            return [f"❌ 存档 [{slot}] 不存在"]

        elif cmd == "saves" or cmd == "list":
            saves = self.saves.list_saves()
            if not saves:
                return ["📭 没有存档。"]
            lines = ["📁 存档列表:"]
            for s in saves:
                lines.append(f"  [{s['slot']}] Lv{s['player_level']} {s['player_name']} "
                           f"@{s['scene_name']} 第{s['game_day']}天 {s['timestamp'][:16]}")
            return lines

        elif cmd == "status":
            return self._render_status()

        elif cmd == "bag" or cmd == "inventory":
            return self._render_inventory()

        elif cmd == "equip":
            return self._render_equipment()

        elif cmd == "quests":
            return self._render_quests()

        elif cmd == "help":
            return self._render_help()

        elif cmd == "use":
            return self._handle_use_item(arg)

        elif cmd == "drop":
            return self._handle_drop_item(arg)

        elif cmd == "equip_item":
            return self._handle_equip_item(arg)

        elif cmd == "unequip":
            return self._handle_unequip(arg)

        else:
            return [f"未知命令: /{cmd}，输入 /help 查看帮助。"]

    # ── 自由文本 ──

    def _handle_free_text(self, text: str) -> List[str]:
        """未匹配到具体命令时，尝试通用交互"""
        scene = self.world.get_current_scene()
        if not scene:
            return ["你站在虚空之中。输入 /help 查看可用命令。"]

        # 尝试匹配场景中的 NPC 或物品
        for npc in scene.npcs:
            if npc.name in text:
                return self._do_talk(npc.name, text)
        for item in scene.items:
            if item.name in text:
                if any(kw in text for kw in ["捡", "拿", "拾"]):
                    return self._do_pickup(item.name)
                return self._do_look(item.name)

        return [f"💭 （你在想什么？输入 /help 查看可用命令）"]

    # ── 物品操作 ──

    def _handle_use_item(self, arg: str) -> List[str]:
        try:
            idx = int(arg) - 1
        except ValueError:
            return ["用法: /use <背包序号>"]
        success, msg = self.items.use_item(self.world.player, idx)
        return [msg]

    def _handle_drop_item(self, arg: str) -> List[str]:
        try:
            idx = int(arg) - 1
        except ValueError:
            return ["用法: /drop <背包序号>"]
        success, msg = self.items.drop_item(self.world.player, idx)
        return [msg]

    def _handle_equip_item(self, arg: str) -> List[str]:
        try:
            idx = int(arg) - 1
        except ValueError:
            return ["用法: /equip_item <背包序号>"]
        success, msg = self.items.equip_item(self.world.player, idx)
        return [msg]

    def _handle_unequip(self, arg: str) -> List[str]:
        slot_map = {"武器": "weapon", "防具": "armor", "饰品": "accessory",
                     "weapon": "weapon", "armor": "armor", "accessory": "accessory"}
        slot = slot_map.get(arg, arg)
        success, msg = self.items.unequip_item(self.world.player, slot)
        return [msg]

    # ═══════════════════════════════════════════════════════════
    # 战斗
    # ═══════════════════════════════════════════════════════════

    def _start_combat_from_npc(self, npc: NPC) -> List[str]:
        self.combat_state = self.combat.start_combat(self.world.player, [npc])
        lines = list(self.combat_state.log)
        lines.extend(self.combat.get_status_lines(self.combat_state))
        lines.append("")
        lines.append("输入行动: 攻击1 / 防御 / 物品 / 逃跑")
        return lines

    def _handle_combat_input(self, raw: str) -> List[str]:
        """处理战斗中的输入"""
        if not self.combat_state:
            return []

        lower = raw.strip().lower()

        # 攻击
        if lower.startswith("攻击") or lower.startswith("attack"):
            parts = lower.replace("攻击", "").replace("attack", "").strip()
            target = 0
            if parts.isdigit():
                target = int(parts) - 1
            self.combat_state = self.combat.player_attack(self.combat_state, target)

        # 防御
        elif lower in ("防御", "defend", "防"):
            self.combat_state = self.combat.player_defend(self.combat_state)

        # 物品
        elif lower.startswith("物品") or lower.startswith("item"):
            parts = lower.replace("物品", "").replace("item", "").strip()
            if parts.isdigit():
                self.combat_state = self.combat.player_use_item(
                    self.combat_state, int(parts) - 1, self.items
                )
            else:
                inv = self.items.list_inventory(self.world.player)
                lines = ["背包（战斗中）:"]
                for item in inv:
                    lines.append(f"  [{item['index']}] {item['name']} ({item['type']})")
                lines.append("输入「物品 序号」使用。")
                return lines

        # 逃跑
        elif lower in ("逃跑", "flee", "逃"):
            self.combat_state = self.combat.player_flee(self.combat_state)

        else:
            return [f"战斗中无法执行「{raw}」。可用: 攻击 / 防御 / 物品 / 逃跑"]

        # 检查战斗结果
        result = self.combat_state.result
        lines = list(self.combat_state.log[-6:])

        if result == CombatResult.PLAYER_WIN:
            lines.append("")
            lines.append("战斗胜利！输入任意内容继续探索。")
            self.combat_state = None
        elif result == CombatResult.PLAYER_DEAD:
            lines.append("")
            lines.append("你被击败了... 输入 /load 读取存档，或重新开始。")
            self.combat_state = None
        elif result == CombatResult.PLAYER_FLED:
            lines.append("")
            lines.append("你逃回了之前的位置。")
            self.combat_state = None
        else:
            lines.extend(self.combat.get_status_lines(self.combat_state))
            lines.append("")
            lines.append("输入行动: 攻击1 / 防御 / 物品 / 逃跑")

        return lines

    # ═══════════════════════════════════════════════════════════
    # 渲染方法（供 TUI 或纯文本模式调用）
    # ═══════════════════════════════════════════════════════════

    def _render_scene(self, scene: Scene) -> List[str]:
        """渲染当前场景"""
        lines = [
            f"📍 {scene.name}",
            f"   {scene.description}",
        ]
        if scene.atmosphere:
            lines.append(f"   🌫 氛围: {scene.atmosphere}")

        # NPC
        for npc in scene.npcs:
            mood_icon = "⚔️" if npc.is_hostile else "👤"
            lines.append(f"  {mood_icon} [{npc.role}] {npc.name}")

        # 物品
        for item in scene.items:
            lines.append(f"  💎 [{item.name}] - {item.description[:40]}")

        # 出口
        if scene.exits:
            exit_parts = []
            for d, nid in scene.exits.items():
                cn = DIRECTION_CN.get(d, d)
                neighbor = self.world.get_scene(nid)
                label = neighbor.name if neighbor else nid
                exit_parts.append(f"{cn}({label})")
            lines.append(f"  🚪 出口: {' | '.join(exit_parts)}")

        return lines

    def _render_status(self) -> List[str]:
        p = self.world.player
        return [
            f"🦸 {p.name}  Lv.{p.level}",
            f"  HP: {p.hp}/{p.max_hp}  MP: {p.mp}/{p.max_mp}",
            f"  攻击: {p.effective_attack}  防御: {p.effective_defense}",
            f"  金币: {p.gold}  经验: {p.exp}/{p.level * 100}",
            f"  第 {p.game_day} 天",
        ]

    def _render_inventory(self) -> List[str]:
        inv = self.items.list_inventory(self.world.player)
        if not inv:
            return ["🎒 背包是空的。"]
        lines = [f"🎒 背包 ({len(inv)}/{self.items.max_inventory}):"]
        for item in inv:
            lines.append(f"  [{item['index']}] {item['name']} | {item['type']} | "
                        f"{item['rarity']} | {item['description'][:30]}")
        return lines

    def _render_equipment(self) -> List[str]:
        eq = self.items.get_equipment_summary(self.world.player)
        slot_cn = {"weapon": "武器", "armor": "防具", "accessory": "饰品"}
        lines = [f"⚔️ 装备 (总攻击:{eq['attack']} 总防御:{eq['defense']})"]
        for slot, name in slot_cn.items():
            item = eq.get(slot)
            if item:
                lines.append(f"  {name}: [{item['name']}] {item['rarity']}")
            else:
                lines.append(f"  {name}: 无")
        return lines

    def _render_quests(self) -> List[str]:
        active = self.quests.get_active_quests(self.world.player)
        if not active:
            return ["📋 没有进行中的任务。"]
        lines = ["📋 任务列表:"]
        for q in active:
            lines.append(self.quests.get_quest_summary(q))
            lines.append("")
        return lines

    def _render_help(self) -> List[str]:
        return [
            "📖 命令帮助:",
            "  移动: 北/南/东/西  |  前往 <方向>",
            "  交互: 对话 <NPC>    |  查看 [对象]",
            "  拾取: 捡起 <物品>   |  拿 <物品>",
            "  系统: /status  /bag  /equip  /quests",
            "        /use <序号>  /drop <序号>",
            "        /save [槽位]  /load [槽位]  /saves",
            "        /help",
        ]

    # ═══════════════════════════════════════════════════════════
    # 主循环（供纯文本模式或 TUI 调用）
    # ═══════════════════════════════════════════════════════════

    def process_turn(self, user_input: str) -> List[str]:
        """处理一个回合（供外部 UI 循环调用）"""
        return self.execute(user_input)

    def get_state_snapshot(self) -> dict:
        """获取当前状态快照（供 TUI 渲染）"""
        scene = self.world.get_current_scene()
        return {
            "player": self.world.player,
            "scene": scene,
            "combat": self.combat_state,
            "in_combat": self.combat_state is not None
                         and self.combat_state.result == CombatResult.ONGOING,
        }
