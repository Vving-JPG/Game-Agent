"""
物品/背包/装备系统 — 物品注册、背包管理、装备槽、消耗品使用。

Player 的基础背包操作已在 game_world.py 中实现，本模块提供：
- 物品使用逻辑（消耗品效果）
- 装备属性加成汇总
- 背包容量管理
- 物品生成辅助
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from src.game_world import Item, Player


# ═══════════════════════════════════════════════════════════════
# 消耗品效果定义
# ═══════════════════════════════════════════════════════════════

CONSUMABLE_EFFECTS: Dict[str, dict] = {
    "生命药水": {"hp_restore": 30},
    "大生命药水": {"hp_restore": 80},
    "魔法药水": {"mp_restore": 20},
    "大魔法药水": {"mp_restore": 60},
    "解毒剂": {"cure_poison": True},
    "力量卷轴": {"temp_atk": 10, "duration": 3},
    "防御卷轴": {"temp_def": 8, "duration": 3},
}

# 可通过关键词匹配的消耗品效果
CONSUMABLE_KEYWORDS = {
    "生命": {"hp_restore": 30},
    "治疗": {"hp_restore": 30},
    "回复": {"hp_restore": 20},
    "药水": {"hp_restore": 20},
    "魔法": {"mp_restore": 20},
    "法力": {"mp_restore": 20},
    "解毒": {"cure_poison": True},
    "绷带": {"hp_restore": 15},
    "食物": {"hp_restore": 10},
    "烤肉": {"hp_restore": 25},
    "面包": {"hp_restore": 15},
}


# ═══════════════════════════════════════════════════════════════
# 物品系统
# ═══════════════════════════════════════════════════════════════

class ItemSystem:
    """物品/背包/装备管理"""

    def __init__(self, max_inventory: int = 20):
        self.max_inventory = max_inventory

    # ── 背包 ──

    def can_pickup(self, player: Player) -> bool:
        return len(player.inventory) < self.max_inventory

    def pickup_item(self, player: Player, item: Item) -> Tuple[bool, str]:
        """拾取物品，返回 (成功, 消息)"""
        if not self.can_pickup(player):
            return False, "背包已满！"
        player.add_item(item)
        return True, f"获得 [{item.name}]"

    def list_inventory(self, player: Player) -> List[Dict]:
        """列出背包物品（带索引）"""
        result = []
        for i, item in enumerate(player.inventory):
            result.append({
                "index": i + 1,
                "name": item.name,
                "type": item.type,
                "rarity": item.rarity,
                "description": item.description,
                "value": item.value,
            })
        return result

    # ── 消耗品使用 ──

    def use_item(self, player: Player, item_index: int) -> Tuple[bool, str]:
        """使用背包中指定索引的消耗品"""
        if item_index < 0 or item_index >= len(player.inventory):
            return False, "无效的物品索引。"
        item = player.inventory[item_index]

        if item.type not in ("消耗品", "材料"):
            return False, f"[{item.name}] 不是消耗品，无法使用。"

        effect = self._get_effect(item)
        if not effect:
            return False, f"[{item.name}] 没有可用效果。"

        # 应用效果
        messages = []
        if "hp_restore" in effect:
            amount = effect["hp_restore"]
            old_hp = player.hp
            player.heal(amount)
            healed = player.hp - old_hp
            messages.append(f"恢复了 {healed} 点生命")

        if "mp_restore" in effect:
            amount = effect["mp_restore"]
            old_mp = player.mp
            player.mp = min(player.max_mp, player.mp + amount)
            restored = player.mp - old_mp
            messages.append(f"恢复了 {restored} 点法力")

        if effect.get("cure_poison"):
            messages.append("解毒成功！")

        # 消耗物品
        player.inventory.pop(item_index)
        msg = f"使用 [{item.name}]：" + "，".join(messages) if messages else f"使用 [{item.name}]，但没有明显效果。"
        return True, msg

    def _get_effect(self, item: Item) -> dict:
        """根据物品名/描述推断消耗品效果"""
        # 1. 精确匹配
        if item.name in CONSUMABLE_EFFECTS:
            return CONSUMABLE_EFFECTS[item.name]
        # 2. 关键词匹配
        for keyword, effect in CONSUMABLE_KEYWORDS.items():
            if keyword in item.name or keyword in item.description:
                return effect
        # 3. 有 stats 视为战斗消耗品
        if item.stats:
            if "hp_restore" in item.stats:
                return {"hp_restore": item.stats["hp_restore"]}
            if "mp_restore" in item.stats:
                return {"mp_restore": item.stats["mp_restore"]}
        return {}

    # ── 装备 ──

    def equip_item(self, player: Player, item_index: int) -> Tuple[bool, str]:
        """装备背包中指定索引的物品"""
        if item_index < 0 or item_index >= len(player.inventory):
            return False, "无效的物品索引。"
        item = player.inventory[item_index]

        if item.type not in ("武器", "防具", "饰品"):
            return False, f"[{item.name}] 类型为 {item.type}，无法装备。"

        # 从背包移除
        player.inventory.pop(item_index)
        if player.equip(item):
            return True, f"装备了 [{item.name}]"
        # 装备失败，放回背包
        player.inventory.append(item)
        return False, f"无法装备 [{item.name}]。"

    def unequip_item(self, player: Player, slot: str) -> Tuple[bool, str]:
        """卸下指定装备槽"""
        slot_cn = {"weapon": "武器", "armor": "防具", "accessory": "饰品"}
        if slot not in player.equipment:
            return False, "无效的装备槽。"
        item = player.equipment[slot]
        if item is None:
            return False, f"{slot_cn.get(slot, slot)}槽位没有装备。"
        if not self.can_pickup(player):
            return False, "背包已满，无法卸下装备。"
        player.inventory.append(item)
        player.equipment[slot] = None
        return True, f"卸下了 [{item.name}]"

    def get_equipment_summary(self, player: Player) -> Dict:
        """装备摘要"""
        result = {}
        slot_cn = {"weapon": "武器", "armor": "防具", "accessory": "饰品"}
        for slot, item in player.equipment.items():
            if item:
                result[slot] = {
                    "name": item.name,
                    "type": item.type,
                    "rarity": item.rarity,
                    "stats": item.stats,
                }
            else:
                result[slot] = None
        result["attack"] = player.effective_attack
        result["defense"] = player.effective_defense
        result["base_attack"] = player.attack
        result["base_defense"] = player.defense
        return result

    # ── 物品丢弃 ──

    def drop_item(self, player: Player, item_index: int) -> Tuple[bool, str]:
        """丢弃背包中的物品"""
        if item_index < 0 or item_index >= len(player.inventory):
            return False, "无效的物品索引。"
        item = player.inventory.pop(item_index)
        return True, f"丢弃了 [{item.name}]"
