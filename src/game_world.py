"""
游戏世界状态管理 — Scene / SceneSkeleton / GameWorld / LightCone / Player

光锥机制：玩家所在场景完整生成，邻居骨架预生成，远处保持"未观测"状态。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any


# ═══════════════════════════════════════════════════════════════
# 场景状态枚举
# ═══════════════════════════════════════════════════════════════

class SceneState(str, Enum):
    UNOBSERVED = "unobserved"       # 未观测 - 不生成内容
    PRE_GENERATED = "pre_gen"       # 预生成 - 邻居场景，骨架数据
    OBSERVED = "observed"           # 已观测 - 完整生成
    VISITED = "visited"             # 已访问 - 完整内容 + 交互记录


# ═══════════════════════════════════════════════════════════════
# 方向常量
# ═══════════════════════════════════════════════════════════════

DIRECTIONS = ["north", "south", "east", "west", "up", "down"]
DIRECTION_CN = {
    "north": "北", "south": "南", "east": "东", "west": "西",
    "up": "上", "down": "下",
}
OPPOSITE = {
    "north": "south", "south": "north",
    "east": "west", "west": "east",
    "up": "down", "down": "up",
}


# ═══════════════════════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════════════════════

@dataclass
class NPC:
    """NPC 角色"""
    name: str
    role: str
    dialogue: str = ""
    personality: str = ""
    mood: str = "平静"
    inventory: List[Dict] = field(default_factory=list)
    quests: List[str] = field(default_factory=list)
    is_hostile: bool = False
    hp: int = 100
    memory: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NPC":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Item:
    """道具"""
    name: str
    description: str
    type: str                       # 武器/防具/消耗品/任务物品/材料/杂项
    rarity: str = "普通"
    value: int = 0
    stats: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SceneEvent:
    """场景事件"""
    trigger: str
    description: str
    resolved: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SceneEvent":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SceneSkeleton:
    """骨架场景 — 光锥预生成"""
    name: str
    description: str
    exits: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SceneSkeleton":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Scene:
    """完整场景"""
    name: str
    description: str
    atmosphere: str = ""
    exits: Dict[str, str] = field(default_factory=dict)
    npcs: List[NPC] = field(default_factory=list)
    items: List[Item] = field(default_factory=list)
    events: List[SceneEvent] = field(default_factory=list)
    state: SceneState = SceneState.OBSERVED
    visit_count: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["npcs"] = [n.to_dict() for n in self.npcs]
        d["items"] = [i.to_dict() for i in self.items]
        d["events"] = [e.to_dict() for e in self.events]
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Scene":
        raw = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        raw["npcs"] = [NPC.from_dict(n) for n in d.get("npcs", [])]
        raw["items"] = [Item.from_dict(i) for i in d.get("items", [])]
        raw["events"] = [SceneEvent.from_dict(e) for e in d.get("events", [])]
        if "state" in d and isinstance(d["state"], str):
            raw["state"] = SceneState(d["state"])
        return cls(**raw)

    def get_npc(self, name: str) -> Optional[NPC]:
        for npc in self.npcs:
            if npc.name == name:
                return npc
        return None

    def remove_item(self, item_name: str) -> Optional[Item]:
        for i, item in enumerate(self.items):
            if item.name == item_name:
                return self.items.pop(i)
        return None


@dataclass
class Player:
    """玩家角色"""
    name: str = "冒险者"
    title: str = ""
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    level: int = 1
    exp: int = 0
    gold: int = 0
    attack: int = 10
    defense: int = 5
    inventory: List[Item] = field(default_factory=list)
    equipment: Dict[str, Optional[Item]] = field(default_factory=lambda: {
        "weapon": None, "armor": None, "accessory": None
    })
    active_quests: List[str] = field(default_factory=list)
    completed_quests: List[str] = field(default_factory=list)
    game_day: int = 1
    current_scene_id: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["inventory"] = [i.to_dict() for i in self.inventory]
        d["equipment"] = {
            k: (v.to_dict() if v else None) for k, v in self.equipment.items()
        }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Player":
        raw = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        raw["inventory"] = [Item.from_dict(i) for i in d.get("inventory", [])]
        raw["equipment"] = {}
        for k, v in d.get("equipment", {}).items():
            raw["equipment"][k] = Item.from_dict(v) if v else None
        return cls(**raw)

    @property
    def effective_attack(self) -> int:
        atk = self.attack
        w = self.equipment.get("weapon")
        if w:
            atk += w.stats.get("atk", 0)
        return atk

    @property
    def effective_defense(self) -> int:
        df = self.defense
        a = self.equipment.get("armor")
        if a:
            df += a.stats.get("def", 0)
        return df

    def add_item(self, item: Item) -> bool:
        self.inventory.append(item)
        return True

    def remove_item(self, item_name: str) -> Optional[Item]:
        for i, item in enumerate(self.inventory):
            if item.name == item_name:
                return self.inventory.pop(i)
        return None

    def has_item(self, item_name: str) -> bool:
        return any(i.name == item_name for i in self.inventory)

    def equip(self, item: Item) -> bool:
        slot_map = {"武器": "weapon", "防具": "armor", "饰品": "accessory"}
        slot = slot_map.get(item.type)
        if not slot:
            return False
        old = self.equipment[slot]
        if old:
            self.inventory.append(old)
        self.equipment[slot] = item
        self.remove_item(item.name)
        return True

    def take_damage(self, amount: int) -> int:
        actual = max(1, amount - self.effective_defense // 2)
        self.hp = max(0, self.hp - actual)
        return actual

    def heal(self, amount: int):
        self.hp = min(self.max_hp, self.hp + amount)

    def is_alive(self) -> bool:
        return self.hp > 0

    def add_exp(self, amount: int) -> bool:
        self.exp += amount
        needed = self.level * 100
        if self.exp >= needed:
            self.exp -= needed
            self.level += 1
            self.max_hp += 20
            self.hp = self.max_hp
            self.max_mp += 10
            self.mp = self.max_mp
            self.attack += 3
            self.defense += 1
            return True
        return False


@dataclass
class WorldCard:
    """世界设定卡"""
    name: str = "未命名世界"
    theme: str = ""
    era: str = ""
    geography: str = ""
    factions: List[str] = field(default_factory=list)
    magic_system: str = ""
    starting_scene_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WorldCard":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def to_prompt(self) -> str:
        parts = [f"世界名称: {self.name}"]
        if self.theme:
            parts.append(f"主题: {self.theme}")
        if self.era:
            parts.append(f"时代: {self.era}")
        if self.geography:
            parts.append(f"地理: {self.geography}")
        if self.factions:
            parts.append(f"势力: {', '.join(self.factions)}")
        if self.magic_system:
            parts.append(f"力量体系: {self.magic_system}")
        return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# 游戏世界
# ═══════════════════════════════════════════════════════════════

class GameWorld:
    """游戏世界 — 管理所有场景和世界状态"""

    def __init__(self, save_dir: str = "saves"):
        self.scenes: Dict[str, Scene] = {}
        self.scene_states: Dict[str, SceneState] = {}
        self.scene_graph: Dict[str, Dict[str, str]] = {}
        self.player: Player = Player()
        self.world_card: WorldCard = WorldCard()
        self.global_state: Dict[str, Any] = {}
        self.save_dir = save_dir

    # ── 场景管理 ──

    def add_scene(self, scene_id: str, scene: Scene):
        self.scenes[scene_id] = scene
        self.scene_states[scene_id] = scene.state

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        return self.scenes.get(scene_id)

    def get_scene_state(self, scene_id: str) -> SceneState:
        return self.scene_states.get(scene_id, SceneState.UNOBSERVED)

    def set_scene_state(self, scene_id: str, state: SceneState):
        self.scene_states[scene_id] = state
        if scene_id in self.scenes:
            self.scenes[scene_id].state = state

    def get_neighbors(self, scene_id: str) -> Dict[str, str]:
        return self.scene_graph.get(scene_id, {})

    def get_neighbor_names(self, scene_id: str) -> Dict[str, str]:
        result = {}
        for direction, neighbor_id in self.get_neighbors(scene_id).items():
            scene = self.scenes.get(neighbor_id)
            if scene:
                result[direction] = f"{scene.name}({neighbor_id})"
            else:
                result[direction] = neighbor_id
        return result

    def connect_scenes(self, from_id: str, direction: str, to_id: str):
        self.scene_graph.setdefault(from_id, {})[direction] = to_id
        self.scene_graph.setdefault(to_id, {})[OPPOSITE[direction]] = from_id

    def get_current_scene(self) -> Optional[Scene]:
        return self.scenes.get(self.player.current_scene_id)

    def set_player_scene(self, scene_id: str):
        self.player.current_scene_id = scene_id

    def to_dict(self) -> dict:
        return {
            "player": self.player.to_dict(),
            "scenes": {sid: s.to_dict() for sid, s in self.scenes.items()},
            "scene_states": {sid: st.value for sid, st in self.scene_states.items()},
            "scene_graph": self.scene_graph,
            "world_card": self.world_card.to_dict(),
            "global_state": self.global_state,
        }

    @classmethod
    def from_dict(cls, d: dict, save_dir: str = "saves") -> "GameWorld":
        world = cls(save_dir=save_dir)
        world.player = Player.from_dict(d.get("player", {}))
        world.scenes = {
            sid: Scene.from_dict(sd) for sid, sd in d.get("scenes", {}).items()
        }
        world.scene_states = {
            sid: SceneState(st) for sid, st in d.get("scene_states", {}).items()
        }
        world.scene_graph = d.get("scene_graph", {})
        world.world_card = WorldCard.from_dict(d.get("world_card", {}))
        world.global_state = d.get("global_state", {})
        return world


# ═══════════════════════════════════════════════════════════════
# 光锥管理器
# ═══════════════════════════════════════════════════════════════

class LightCone:
    """光锥管理器 — 当前场景完整生成，邻居骨架预生成"""

    def __init__(self, game_world: GameWorld, observation_range: int = 1):
        self.world = game_world
        self.current_scene_id: Optional[str] = None
        self.observation_range = observation_range

    def move_to(self, scene_id: str):
        """
        玩家移动到新场景，触发光锥更新。
        返回 (需要完整生成的场景ID列表, 需要预生成的场景ID列表)
        """
        old_id = self.current_scene_id
        self.current_scene_id = scene_id

        # 1. 旧场景 → VISITED
        if old_id:
            self.world.set_scene_state(old_id, SceneState.VISITED)

        # 2. 当前场景 → OBSERVED
        to_gen_full: List[str] = []
        current_state = self.world.get_scene_state(scene_id)
        if current_state in (SceneState.UNOBSERVED, SceneState.PRE_GENERATED):
            to_gen_full.append(scene_id)

        # 3. BFS 收集邻居预生成
        to_gen_skeleton = self._collect_neighbors_for_pregen(scene_id)

        return to_gen_full, to_gen_skeleton

    def _collect_neighbors_for_pregen(self, center_id: str) -> List[str]:
        needs: List[str] = []
        visited = {center_id}
        queue = deque([(center_id, 0)])

        while queue:
            current, depth = queue.popleft()
            if depth >= self.observation_range:
                continue
            for _dir, neighbor_id in self.world.get_neighbors(current).items():
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                state = self.world.get_scene_state(neighbor_id)
                if state == SceneState.UNOBSERVED:
                    needs.append(neighbor_id)
                    self.world.set_scene_state(neighbor_id, SceneState.PRE_GENERATED)
                if depth + 1 < self.observation_range:
                    queue.append((neighbor_id, depth + 1))
        return needs

    def get_observable_area(self) -> Dict[str, SceneState]:
        if not self.current_scene_id:
            return {}
        return {
            sid: state
            for sid, state in self.world.scene_states.items()
            if state != SceneState.UNOBSERVED
        }
