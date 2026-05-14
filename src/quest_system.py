"""
任务系统 — 任务数据模型、追踪、完成判定、奖励发放。

任务存储在 GameWorld.global_state["quests"] 中，Player 持有 active_quests / completed_quests。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any

from src.game_world import Player, Item


class QuestStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QuestObjective:
    """任务目标"""
    description: str                    # 目标描述
    type: str = "generic"               # kill/talk/collect/reach/…
    target: str = ""                    # 目标 ID/NPC名/物品名
    required: int = 1                   # 需要的数量
    current: int = 0                    # 当前进度

    def is_complete(self) -> bool:
        return self.current >= self.required

    def progress(self, amount: int = 1):
        self.current = min(self.required, self.current + amount)

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "type": self.type,
            "target": self.target,
            "required": self.required,
            "current": self.current,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuestObjective":
        return cls(
            description=d.get("description", ""),
            type=d.get("type", "generic"),
            target=d.get("target", ""),
            required=d.get("required", 1),
            current=d.get("current", 0),
        )


@dataclass
class QuestReward:
    """任务奖励"""
    exp: int = 0
    gold: int = 0
    items: List[dict] = field(default_factory=list)  # [{name, type, rarity, stats}]

    def to_dict(self) -> dict:
        return {"exp": self.exp, "gold": self.gold, "items": self.items}

    @classmethod
    def from_dict(cls, d: dict) -> "QuestReward":
        return cls(
            exp=d.get("exp", 0),
            gold=d.get("gold", 0),
            items=d.get("items", []),
        )


@dataclass
class Quest:
    """任务"""
    quest_id: str
    name: str
    description: str
    giver: str = ""                     # 发布者 NPC 名称
    status: QuestStatus = QuestStatus.NOT_STARTED
    objectives: List[QuestObjective] = field(default_factory=list)
    rewards: QuestReward = field(default_factory=QuestReward)

    def is_complete(self) -> bool:
        return all(o.is_complete() for o in self.objectives)

    def to_dict(self) -> dict:
        return {
            "quest_id": self.quest_id,
            "name": self.name,
            "description": self.description,
            "giver": self.giver,
            "status": self.status.value,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": self.rewards.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Quest":
        return cls(
            quest_id=d.get("quest_id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            giver=d.get("giver", ""),
            status=QuestStatus(d.get("status", "not_started")),
            objectives=[QuestObjective.from_dict(o) for o in d.get("objectives", [])],
            rewards=QuestReward.from_dict(d.get("rewards", {})),
        )


# ═══════════════════════════════════════════════════════════════
# 任务系统
# ═══════════════════════════════════════════════════════════════

class QuestSystem:
    """任务追踪与管理"""

    def __init__(self):
        self._quests: Dict[str, Quest] = {}

    def load_from_world(self, quests_dict: Dict[str, dict]):
        """从世界状态加载任务"""
        self._quests = {
            qid: Quest.from_dict(qd) for qid, qd in quests_dict.items()
        }

    def to_dict(self) -> dict:
        return {qid: q.to_dict() for qid, q in self._quests.items()}

    def add_quest(self, quest: Quest):
        self._quests[quest.quest_id] = quest

    def create_quest(self, name: str, description: str,
                     objectives: List[dict], rewards: dict,
                     giver: str = "") -> Quest:
        """从原始数据创建任务"""
        qid = f"quest_{uuid.uuid4().hex[:8]}"
        quest = Quest(
            quest_id=qid,
            name=name,
            description=description,
            giver=giver,
            objectives=[QuestObjective(**o) for o in objectives],
            rewards=QuestReward(**rewards) if isinstance(rewards, dict) else rewards,
        )
        self._quests[qid] = quest
        return quest

    def accept_quest(self, player: Player, quest_id: str) -> bool:
        """玩家接取任务"""
        quest = self._quests.get(quest_id)
        if not quest or quest.status != QuestStatus.NOT_STARTED:
            return False
        if quest_id in player.active_quests:
            return False
        quest.status = QuestStatus.IN_PROGRESS
        player.active_quests.append(quest_id)
        return True

    def complete_quest(self, player: Player, quest_id: str) -> Optional[str]:
        """完成任务并发奖励，返回消息"""
        quest = self._quests.get(quest_id)
        if not quest or quest.status != QuestStatus.IN_PROGRESS:
            return None
        if not quest.is_complete():
            return None

        quest.status = QuestStatus.COMPLETED
        player.active_quests.remove(quest_id)
        player.completed_quests.append(quest_id)

        # 发奖励
        msgs = [f"✅ 任务完成: {quest.name}"]
        if quest.rewards.exp:
            player.add_exp(quest.rewards.exp)
            msgs.append(f"  +{quest.rewards.exp} 经验")
        if quest.rewards.gold:
            player.gold += quest.rewards.gold
            msgs.append(f"  +{quest.rewards.gold} 金币")
        for item_data in quest.rewards.items:
            item = Item(**item_data)
            player.add_item(item)
            msgs.append(f"  获得: [{item.name}]")

        return "\n".join(msgs)

    def get_active_quests(self, player: Player) -> List[Quest]:
        return [self._quests[qid] for qid in player.active_quests
                if qid in self._quests]

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        return self._quests.get(quest_id)

    def update_progress(self, quest_id: str, objective_index: int,
                        amount: int = 1):
        """更新任务目标进度"""
        quest = self._quests.get(quest_id)
        if not quest or objective_index >= len(quest.objectives):
            return
        quest.objectives[objective_index].progress(amount)

    def update_progress_by_type(self, quest_id: str, obj_type: str,
                                target: str = "", amount: int = 1):
        """按类型匹配更新进度"""
        quest = self._quests.get(quest_id)
        if not quest or quest.status != QuestStatus.IN_PROGRESS:
            return
        for obj in quest.objectives:
            if obj.type == obj_type:
                if not target or obj.target == target:
                    obj.progress(amount)

    def progress_kill(self, enemy_name: str, player: Player):
        """击杀敌人时推进 kill 类型目标"""
        for qid in player.active_quests:
            self.update_progress_by_type(qid, "kill", enemy_name)

    def progress_talk(self, npc_name: str, player: Player):
        """与 NPC 对话时推进 talk 类型目标"""
        for qid in player.active_quests:
            self.update_progress_by_type(qid, "talk", npc_name)

    def progress_collect(self, item_name: str, player: Player, amount: int = 1):
        """收集物品时推进 collect 类型目标"""
        for qid in player.active_quests:
            self.update_progress_by_type(qid, "collect", item_name, amount)

    def progress_reach(self, scene_id: str, player: Player):
        """到达场景时推进 reach 类型目标"""
        for qid in player.active_quests:
            self.update_progress_by_type(qid, "reach", scene_id)

    def get_quest_summary(self, quest: Quest) -> str:
        """任务摘要文本"""
        lines = [f"📋 {quest.name} [{quest.status.value}]"]
        lines.append(f"   {quest.description}")
        if quest.giver:
            lines.append(f"   发布者: {quest.giver}")
        lines.append("   目标:")
        for obj in quest.objectives:
            prog = f"{obj.current}/{obj.required}"
            done = "✅" if obj.is_complete() else "⬜"
            lines.append(f"     {done} {obj.description} ({prog})")
        if quest.rewards.exp or quest.rewards.gold:
            reward_parts = []
            if quest.rewards.exp:
                reward_parts.append(f"{quest.rewards.exp}经验")
            if quest.rewards.gold:
                reward_parts.append(f"{quest.rewards.gold}金币")
            lines.append(f"   奖励: {', '.join(reward_parts)}")
        return "\n".join(lines)
