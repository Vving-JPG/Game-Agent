"""
回合制战斗系统 — 玩家行动、敌人 AI、伤害计算、战斗叙述。

依赖 ContentGenerator 生成战斗叙述文本。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, TYPE_CHECKING

from src.game_world import Player, NPC, Item

if TYPE_CHECKING:
    from src.content_generator import ContentGenerator


# ═══════════════════════════════════════════════════════════════
# 战斗状态
# ═══════════════════════════════════════════════════════════════

class CombatAction(str, Enum):
    ATTACK = "attack"
    SKILL = "skill"
    ITEM = "item"
    DEFEND = "defend"
    FLEE = "flee"


class CombatResult(str, Enum):
    ONGOING = "ongoing"         # 战斗继续
    PLAYER_WIN = "player_win"
    PLAYER_DEAD = "player_dead"
    PLAYER_FLED = "player_fled"


@dataclass
class CombatEnemy:
    """战斗中敌人状态"""
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    exp_reward: int = 50
    gold_reward: int = 20
    loot: List[Item] = field(default_factory=list)
    is_defending: bool = False

    def take_damage(self, amount: int) -> int:
        actual = max(1, amount - self.defense // 2)
        if self.is_defending:
            actual = actual // 2
        self.hp = max(0, self.hp - actual)
        return actual

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class CombatState:
    """战斗回合状态"""
    player: Player
    enemies: List[CombatEnemy]
    turn: int = 0
    log: List[str] = field(default_factory=list)
    player_defending: bool = False
    result: CombatResult = CombatResult.ONGOING


# ═══════════════════════════════════════════════════════════════
# 战斗系统
# ═══════════════════════════════════════════════════════════════

class CombatSystem:
    """回合制战斗系统"""

    def __init__(self, content_generator: Optional["ContentGenerator"] = None):
        self.generator = content_generator

    def start_combat(self, player: Player, npcs: List[NPC]) -> CombatState:
        """从 NPC 列表初始化战斗"""
        enemies = []
        for npc in npcs:
            enemy = CombatEnemy(
                name=npc.name,
                hp=npc.hp,
                max_hp=npc.hp,
                attack=max(5, player.level * 3),
                defense=max(2, player.level),
                exp_reward=30 + player.level * 20,
                gold_reward=10 + player.level * 5,
            )
            enemies.append(enemy)

        state = CombatState(player=player, enemies=enemies)
        state.log.append(f"⚔️ 战斗开始！遭遇了 {', '.join(e.name for e in enemies)}")
        return state

    # ── 玩家行动 ──

    def player_attack(self, state: CombatState, target_index: int = 0) -> CombatState:
        """玩家普通攻击"""
        if target_index < 0 or target_index >= len(state.enemies):
            state.log.append("无效的目标。")
            return state

        alive_enemies = [e for e in state.enemies if e.is_alive()]
        if target_index >= len(alive_enemies):
            state.log.append("目标已死亡。")
            return state

        target = alive_enemies[target_index]
        damage = state.player.effective_attack + random.randint(-2, 2)
        actual = target.take_damage(damage)
        state.log.append(f"你对 {target.name} 造成 {actual} 点伤害" +
                         (f"（{target.name} 已倒下）" if not target.is_alive() else ""))

        return self._after_player_action(state)

    def player_defend(self, state: CombatState) -> CombatState:
        """玩家防御"""
        state.player_defending = True
        state.log.append("你摆出防御姿态，本回合受到的伤害减半。")
        return self._after_player_action(state)

    def player_use_item(self, state: CombatState, item_index: int,
                        item_system=None) -> CombatState:
        """玩家使用物品"""
        if item_system is None:
            from src.item_system import ItemSystem
            item_system = ItemSystem()

        success, msg = item_system.use_item(state.player, item_index)
        state.log.append(msg)
        if success:
            return self._after_player_action(state)
        # 使用失败，不消耗回合
        return state

    def player_flee(self, state: CombatState) -> CombatState:
        """玩家逃跑"""
        flee_chance = 0.6
        if random.random() < flee_chance:
            state.result = CombatResult.PLAYER_FLED
            state.log.append("🏃 你成功逃离了战斗！")
        else:
            state.log.append("逃跑失败！")
            state = self._after_player_action(state)
        return state

    def _after_player_action(self, state: CombatState) -> CombatState:
        """玩家行动后，执行敌人回合 + 检查胜负"""
        state = self._enemy_turn(state)
        state.turn += 1
        state.player_defending = False
        state = self._check_result(state)
        return state

    # ── 敌人 AI ──

    def _enemy_turn(self, state: CombatState) -> CombatState:
        """所有存活的敌人依次行动"""
        for enemy in state.enemies:
            if not enemy.is_alive():
                continue
            enemy.is_defending = False

            # 简单 AI：随机攻击或防御
            action_roll = random.random()
            if action_roll < 0.15:
                # 防御
                enemy.is_defending = True
                state.log.append(f"{enemy.name} 摆出防御姿态。")
            else:
                # 攻击
                damage = enemy.attack + random.randint(-1, 3)
                actual = state.player.take_damage(damage)
                state.log.append(f"{enemy.name} 对你造成 {actual} 点伤害")

                if not state.player.is_alive():
                    state.result = CombatResult.PLAYER_DEAD
                    state.log.append("💀 你被击败了...")
                    return state

        return state

    def _check_result(self, state: CombatState) -> CombatState:
        """检查战斗结果"""
        if not state.player.is_alive():
            state.result = CombatResult.PLAYER_DEAD
            return state

        if all(not e.is_alive() for e in state.enemies):
            state.result = CombatResult.PLAYER_WIN
            total_exp = sum(e.exp_reward for e in state.enemies)
            total_gold = sum(e.gold_reward for e in state.enemies)
            state.player.gold += total_gold

            state.log.append(f"🎉 战斗胜利！")
            state.log.append(f"获得 {total_exp} 经验值，{total_gold} 金币")

            leveled_up = state.player.add_exp(total_exp)
            if leveled_up:
                state.log.append(f"⬆️ 升级！当前等级 {state.player.level}")

            # 掉落物品
            for enemy in state.enemies:
                for item in enemy.loot:
                    state.player.add_item(item)
                    state.log.append(f"获得掉落物品: [{item.name}]")

        return state

    # ── 叙述生成 ──

    def generate_narration(self, state: CombatState, last_action: str = "") -> str:
        """生成当前战斗回合的叙述文本"""
        if not self.generator:
            return "\n".join(state.log[-4:])

        player_dict = {
            "name": state.player.name,
            "hp": state.player.hp,
            "max_hp": state.player.max_hp,
            "attack": state.player.effective_attack,
            "defense": state.player.effective_defense,
        }
        enemies_dict = [
            {"name": e.name, "hp": e.hp, "max_hp": e.max_hp}
            for e in state.enemies if e.is_alive()
        ]
        result_dict = {
            "turn": state.turn,
            "player_hp": state.player.hp,
            "enemies": enemies_dict,
        }
        return self.generator.generate_combat_narration(
            player_dict, enemies_dict, last_action, result_dict
        )

    # ── 状态展示 ──

    def get_status_lines(self, state: CombatState) -> List[str]:
        """获取战斗状态文本（供 TUI 展示）"""
        lines = []
        lines.append(f"⚔️ 第 {state.turn} 回合")
        lines.append(f"🦸 {state.player.name}  HP: {state.player.hp}/{state.player.max_hp}  MP: {state.player.mp}/{state.player.max_mp}")
        for i, enemy in enumerate(state.enemies):
            if enemy.is_alive():
                status = "🛡️防御中" if enemy.is_defending else ""
                lines.append(f"👹 [{i+1}] {enemy.name}  HP: {enemy.hp}/{enemy.max_hp} {status}")
        return lines

    def get_alive_enemies(self, state: CombatState) -> List[CombatEnemy]:
        return [e for e in state.enemies if e.is_alive()]
