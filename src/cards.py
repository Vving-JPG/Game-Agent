"""
卡片系统模块

提供世界卡、角色卡、设定卡的管理和使用
适用于游戏、角色扮演、故事创作等场景
"""

import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from enum import Enum


class CardType(Enum):
    """卡片类型"""
    WORLD = "world"           # 世界卡
    CHARACTER = "character"   # 角色卡
    SETTING = "setting"       # 设定卡


class Card:
    """卡片基类"""
    
    def __init__(self, 
                 name: str,
                 card_type: CardType,
                 description: str = "",
                 author: str = "",
                 version: str = "1.0.0",
                 tags: List[str] = None,
                 metadata: Dict[str, Any] = None):
        self.name = name
        self.card_type = card_type
        self.description = description
        self.author = author
        self.version = version
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.card_type.value,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Card":
        """从字典创建"""
        card_type = CardType(data.get("type", "setting"))
        
        if card_type == CardType.WORLD:
            return WorldCard.from_dict(data)
        elif card_type == CardType.CHARACTER:
            return CharacterCard.from_dict(data)
        else:
            return SettingCard.from_dict(data)
    
    def to_prompt(self) -> str:
        """转换为提示词"""
        return f"【{self.name}】\n{self.description}"


class WorldCard(Card):
    """
    世界卡
    
    描述游戏世界、故事背景、世界观等
    """
    
    def __init__(self, 
                 name: str,
                 description: str = "",
                 world_setting: Dict[str, Any] = None,
                 locations: List[Dict[str, Any]] = None,
                 factions: List[Dict[str, Any]] = None,
                 history: str = "",
                 rules: List[str] = None,
                 **kwargs):
        super().__init__(name, CardType.WORLD, description, **kwargs)
        
        self.world_setting = world_setting or {}
        self.locations = locations or []
        self.factions = factions or []
        self.history = history
        self.rules = rules or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = super().to_dict()
        data.update({
            "world_setting": self.world_setting,
            "locations": self.locations,
            "factions": self.factions,
            "history": self.history,
            "rules": self.rules
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldCard":
        """从字典创建"""
        card = cls(
            name=data["name"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            world_setting=data.get("world_setting", {}),
            locations=data.get("locations", []),
            factions=data.get("factions", []),
            history=data.get("history", ""),
            rules=data.get("rules", [])
        )
        card.created_at = data.get("created_at", card.created_at)
        card.updated_at = data.get("updated_at", card.updated_at)
        return card
    
    def to_prompt(self) -> str:
        """转换为提示词"""
        parts = [f"# {self.name}", ""]
        
        if self.description:
            parts.append(f"## 世界概述\n{self.description}")
        
        if self.world_setting:
            parts.append("\n## 世界设定")
            for key, value in self.world_setting.items():
                parts.append(f"- {key}: {value}")
        
        if self.history:
            parts.append(f"\n## 历史背景\n{self.history}")
        
        if self.locations:
            parts.append("\n## 重要地点")
            for loc in self.locations[:5]:
                parts.append(f"- {loc.get('name', '未知地点')}: {loc.get('description', '')}")
        
        if self.factions:
            parts.append("\n## 主要势力")
            for faction in self.factions[:5]:
                parts.append(f"- {faction.get('name', '未知势力')}: {faction.get('description', '')}")
        
        if self.rules:
            parts.append("\n## 世界规则")
            for rule in self.rules[:5]:
                parts.append(f"- {rule}")
        
        return "\n".join(parts)


class CharacterCard(Card):
    """
    角色卡
    
    描述游戏角色、NPC、人物设定等
    """
    
    def __init__(self,
                 name: str,
                 description: str = "",
                 role: str = "",           # 角色定位：主角/配角/反派等
                 personality: Dict[str, Any] = None,
                 appearance: str = "",
                 background: str = "",
                 abilities: List[Dict[str, Any]] = None,
                 relationships: List[Dict[str, Any]] = None,
                 goals: List[str] = None,
                 dialogue_style: str = "",
                 **kwargs):
        super().__init__(name, CardType.CHARACTER, description, **kwargs)
        
        self.role = role
        self.personality = personality or {}
        self.appearance = appearance
        self.background = background
        self.abilities = abilities or []
        self.relationships = relationships or []
        self.goals = goals or []
        self.dialogue_style = dialogue_style
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = super().to_dict()
        data.update({
            "role": self.role,
            "personality": self.personality,
            "appearance": self.appearance,
            "background": self.background,
            "abilities": self.abilities,
            "relationships": self.relationships,
            "goals": self.goals,
            "dialogue_style": self.dialogue_style
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterCard":
        """从字典创建"""
        card = cls(
            name=data["name"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            role=data.get("role", ""),
            personality=data.get("personality", {}),
            appearance=data.get("appearance", ""),
            background=data.get("background", ""),
            abilities=data.get("abilities", []),
            relationships=data.get("relationships", []),
            goals=data.get("goals", []),
            dialogue_style=data.get("dialogue_style", "")
        )
        card.created_at = data.get("created_at", card.created_at)
        card.updated_at = data.get("updated_at", card.updated_at)
        return card
    
    def to_prompt(self, mode: str = "full") -> str:
        """
        转换为提示词
        
        Args:
            mode: 模式 (full/short/roleplay)
        """
        if mode == "short":
            return f"{self.name} - {self.description}"
        
        parts = [f"# 角色：{self.name}", ""]
        
        if self.description:
            parts.append(f"**简介**：{self.description}")
        
        if self.role:
            parts.append(f"**定位**：{self.role}")
        
        if self.appearance:
            parts.append(f"\n**外貌**：{self.appearance}")
        
        if self.personality:
            parts.append("\n**性格**：")
            for key, value in self.personality.items():
                parts.append(f"- {key}: {value}")
        
        if self.background:
            parts.append(f"\n**背景**：{self.background}")
        
        if self.abilities:
            parts.append("\n**能力**：")
            for ability in self.abilities[:5]:
                parts.append(f"- {ability.get('name', '未知能力')}: {ability.get('description', '')}")
        
        if self.goals:
            parts.append("\n**目标**：")
            for goal in self.goals:
                parts.append(f"- {goal}")
        
        if self.dialogue_style and mode == "roleplay":
            parts.append(f"\n**对话风格**：{self.dialogue_style}")
        
        return "\n".join(parts)
    
    def to_roleplay_prompt(self) -> str:
        """转换为角色扮演提示词"""
        return self.to_prompt(mode="roleplay")


class SettingCard(Card):
    """
    设定卡
    
    描述特定场景、情境、规则设定等
    """
    
    def __init__(self,
                 name: str,
                 description: str = "",
                 category: str = "",       # 场景/规则/情境/道具
                 content: Dict[str, Any] = None,
                 constraints: List[str] = None,
                 examples: List[str] = None,
                 **kwargs):
        super().__init__(name, CardType.SETTING, description, **kwargs)
        
        self.category = category
        self.content = content or {}
        self.constraints = constraints or []
        self.examples = examples or []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = super().to_dict()
        data.update({
            "category": self.category,
            "content": self.content,
            "constraints": self.constraints,
            "examples": self.examples
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SettingCard":
        """从字典创建"""
        card = cls(
            name=data["name"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            category=data.get("category", ""),
            content=data.get("content", {}),
            constraints=data.get("constraints", []),
            examples=data.get("examples", [])
        )
        card.created_at = data.get("created_at", card.created_at)
        card.updated_at = data.get("updated_at", card.updated_at)
        return card
    
    def to_prompt(self) -> str:
        """转换为提示词"""
        parts = [f"# {self.name}"]
        
        if self.category:
            parts.append(f"**类型**：{self.category}")
        
        if self.description:
            parts.append(f"\n**描述**：{self.description}")
        
        if self.content:
            parts.append("\n**详细内容**：")
            for key, value in self.content.items():
                if isinstance(value, list):
                    parts.append(f"\n{key}：")
                    for item in value:
                        parts.append(f"  - {item}")
                else:
                    parts.append(f"- {key}: {value}")
        
        if self.constraints:
            parts.append("\n**约束条件**：")
            for constraint in self.constraints:
                parts.append(f"- {constraint}")
        
        if self.examples:
            parts.append("\n**示例**：")
            for i, example in enumerate(self.examples[:3], 1):
                parts.append(f"{i}. {example}")
        
        return "\n".join(parts)


class CardManager:
    """
    卡片管理器
    
    统一管理所有卡片的加载、保存、查询
    """
    
    def __init__(self, cards_dir: str = "cards"):
        """
        初始化卡片管理器
        
        Args:
            cards_dir: 卡片存储目录
        """
        self.cards_dir = Path(cards_dir)
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        for card_type in CardType:
            (self.cards_dir / card_type.value).mkdir(exist_ok=True)
        
        self._cards: Dict[str, Card] = {}
        self._load_all_cards()
    
    def _load_all_cards(self):
        """加载所有卡片"""
        for card_type in CardType:
            type_dir = self.cards_dir / card_type.value
            for file_path in type_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    card = Card.from_dict(data)
                    self._cards[card.name] = card
                except Exception as e:
                    print(f"加载卡片失败 {file_path}: {e}")
            
            for file_path in type_dir.glob("*.yaml"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    card = Card.from_dict(data)
                    self._cards[card.name] = card
                except Exception as e:
                    print(f"加载卡片失败 {file_path}: {e}")
    
    def save_card(self, card: Card, format: str = "json"):
        """
        保存卡片
        
        Args:
            card: 卡片对象
            format: 格式 (json/yaml)
        """
        card.updated_at = datetime.now().isoformat()
        
        type_dir = self.cards_dir / card.card_type.value
        type_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = type_dir / f"{card.name}.{format}"
        
        with open(file_path, "w", encoding="utf-8") as f:
            if format == "json":
                json.dump(card.to_dict(), f, ensure_ascii=False, indent=2)
            else:
                yaml.dump(card.to_dict(), f, allow_unicode=True, default_flow_style=False)
        
        self._cards[card.name] = card
    
    def get_card(self, name: str) -> Optional[Card]:
        """
        获取卡片
        
        Args:
            name: 卡片名称
            
        Returns:
            Optional[Card]: 卡片对象
        """
        return self._cards.get(name)
    
    def list_cards(self, card_type: CardType = None) -> List[Card]:
        """
        列出卡片
        
        Args:
            card_type: 卡片类型过滤
            
        Returns:
            List[Card]: 卡片列表
        """
        cards = list(self._cards.values())
        if card_type:
            cards = [c for c in cards if c.card_type == card_type]
        return cards
    
    def search_cards(self, query: str, card_type: CardType = None) -> List[Card]:
        """
        搜索卡片
        
        Args:
            query: 搜索关键词
            card_type: 卡片类型过滤
            
        Returns:
            List[Card]: 匹配的卡片列表
        """
        results = []
        query_lower = query.lower()
        
        for card in self._cards.values():
            if card_type and card.card_type != card_type:
                continue
            
            if (query_lower in card.name.lower() or 
                query_lower in card.description.lower() or
                any(query_lower in tag.lower() for tag in card.tags)):
                results.append(card)
        
        return results
    
    def delete_card(self, name: str) -> bool:
        """
        删除卡片
        
        Args:
            name: 卡片名称
            
        Returns:
            bool: 是否成功
        """
        card = self._cards.get(name)
        if not card:
            return False
        
        # 删除文件
        for ext in ["json", "yaml"]:
            file_path = self.cards_dir / card.card_type.value / f"{name}.{ext}"
            if file_path.exists():
                file_path.unlink()
        
        del self._cards[name]
        return True
    
    def get_cards_by_tag(self, tag: str) -> List[Card]:
        """
        按标签获取卡片
        
        Args:
            tag: 标签名
            
        Returns:
            List[Card]: 卡片列表
        """
        return [c for c in self._cards.values() if tag in c.tags]
    
    def build_scene_prompt(self, 
                         world_name: str = None,
                         character_names: List[str] = None,
                         setting_names: List[str] = None) -> str:
        """
        构建场景提示词
        
        Args:
            world_name: 世界卡名称
            character_names: 角色卡名称列表
            setting_names: 设定卡名称列表
            
        Returns:
            str: 场景提示词
        """
        parts = []
        
        if world_name:
            world = self.get_card(world_name)
            if world and isinstance(world, WorldCard):
                parts.append(world.to_prompt())
                parts.append("\n" + "="*50 + "\n")
        
        if character_names:
            parts.append("## 出场角色\n")
            for char_name in character_names:
                char = self.get_card(char_name)
                if char and isinstance(char, CharacterCard):
                    parts.append(char.to_prompt(mode="short"))
                    parts.append("")
        
        if setting_names:
            parts.append("## 当前情境\n")
            for setting_name in setting_names:
                setting = self.get_card(setting_name)
                if setting and isinstance(setting, SettingCard):
                    parts.append(setting.to_prompt())
                    parts.append("")
        
        return "\n".join(parts)
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        stats = {"total": len(self._cards)}
        for card_type in CardType:
            stats[card_type.value] = len(
                [c for c in self._cards.values() if c.card_type == card_type]
            )
        return stats
