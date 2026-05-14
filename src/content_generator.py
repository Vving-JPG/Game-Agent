"""
LLM 内容生成器 — 封装 DeepSeek API 调用，实现场景/道具/NPC/任务/战斗生成。

依赖项目已有的 OpenAI client 和 config 模块。
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv

# 复用现有项目模块
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
from config import Config

# 游戏世界模型
from src.game_world import (
    Scene, SceneSkeleton, NPC, Item, SceneEvent, Player, WorldCard,
)

load_dotenv(os.path.join(_project_root, "key.env"))


class ContentGenerator:
    """LLM 驱动的内容生成器 — 光锥驱动"""

    def __init__(
        self,
        config: Optional[Config] = None,
        templates_dir: Optional[str] = None,
    ):
        self.config = config or Config()
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.model = self.config.model if config else "deepseek-v4-flash"
        self.templates_dir = templates_dir or os.path.join(_project_root, "prompts")
        self._templates: Dict[str, dict] = {}
        self._load_templates()

    # ── 模板管理 ──

    def _load_templates(self):
        gaming_path = os.path.join(self.templates_dir, "gaming_templates.json")
        if os.path.exists(gaming_path):
            try:
                with open(gaming_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for t in data.get("templates", []):
                    self._templates[t["name"]] = t
            except (json.JSONDecodeError, IOError):
                pass

    def get_template(self, name: str) -> Optional[dict]:
        return self._templates.get(name)

    def render_template(self, name: str, **kwargs) -> str:
        tpl = self._templates.get(name)
        if not tpl:
            return ""
        content = tpl["content"]
        for key, value in kwargs.items():
            content = content.replace("{" + key + "}", str(value))
        return content

    def update_template(self, name: str, content: str):
        """更新/添加模板（供 template_editor 使用）"""
        self._templates[name] = {"name": name, "content": content}
        self._save_templates()

    def _save_templates(self):
        gaming_path = os.path.join(self.templates_dir, "gaming_templates.json")
        os.makedirs(os.path.dirname(gaming_path), exist_ok=True)
        data = {"templates": list(self._templates.values())}
        with open(gaming_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── LLM 调用 ──

    def _call_llm(self, system_prompt: str, user_prompt: str = "请生成。",
                  expect_json: bool = True, temperature: float = 0.8,
                  max_tokens: int = 2048) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            print(f"[ContentGenerator] LLM 调用失败: {e}")
            return "{}"

    def _parse_json_response(self, text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            nl = text.find("\n")
            text = text[nl + 1:] if nl > 0 else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except json.JSONDecodeError:
                    pass
            return {}

    # ═══════════════════════════════════════════════════════════
    # 场景生成
    # ═══════════════════════════════════════════════════════════

    def generate_full_scene(
        self, scene_id: str, world_context: str,
        neighbors: Dict[str, str], player_state: dict,
    ) -> Optional[Scene]:
        sys_prompt = self.render_template(
            "scene_full",
            world_context=world_context,
            scene_id=scene_id,
            neighbors=json.dumps(neighbors, ensure_ascii=False),
            player=json.dumps(player_state, ensure_ascii=False),
        )
        if not sys_prompt:
            sys_prompt = self._default_full_scene_prompt(
                scene_id, world_context, neighbors, player_state
            )
        response = self._call_llm(sys_prompt)
        data = self._parse_json_response(response)
        return self._dict_to_scene(data, scene_id) if data else None

    def _default_full_scene_prompt(
        self, scene_id, world_context, neighbors, player
    ) -> str:
        return f"""你是一个RPG游戏内容生成器。根据世界设定生成一个完整的游戏场景。

世界设定:
{world_context}

场景ID: {scene_id}
相邻场景: {json.dumps(neighbors, ensure_ascii=False)}
玩家状态: {json.dumps(player, ensure_ascii=False)}

请严格按照以下JSON格式输出（不要包含markdown代码块标记）:
{{
    "name": "场景名称",
    "description": "场景详细描述（50-100字）",
    "atmosphere": "氛围",
    "exits": {{"north": "scene_id", "south": "scene_id"}},
    "npcs": [
        {{"name": "NPC名称", "role": "角色定位", "personality": "性格",
          "dialogue": "初始对话", "is_hostile": false, "hp": 100, "quests": []}}
    ],
    "items": [
        {{"name": "道具名", "description": "描述", "type": "武器/防具/消耗品/任务物品",
          "rarity": "普通/稀有/史诗", "value": 10, "stats": {{}}}}
    ],
    "events": [
        {{"trigger": "触发条件", "description": "事件描述", "resolved": false}}
    ]
}}"""

    def generate_scene_skeleton(
        self, scene_id: str, world_context: str
    ) -> Optional[SceneSkeleton]:
        sys_prompt = self.render_template(
            "scene_skeleton", world_context=world_context, scene_id=scene_id,
        )
        if not sys_prompt:
            sys_prompt = f"""根据世界设定生成邻居场景骨架。

世界设定:
{world_context}
场景ID: {scene_id}

输出JSON（只输出JSON）:
{{"name":"场景名称","description":"简短描述（20字内）","exits":["north","east"]}}"""

        response = self._call_llm(sys_prompt)
        data = self._parse_json_response(response)
        if data:
            return SceneSkeleton(
                name=data.get("name", scene_id),
                description=data.get("description", ""),
                exits=data.get("exits", []),
            )
        return None

    def _dict_to_scene(self, data: dict, scene_id: str) -> Scene:
        npcs = [NPC(
            name=nd.get("name", "无名NPC"), role=nd.get("role", "路人"),
            personality=nd.get("personality", ""), dialogue=nd.get("dialogue", ""),
            is_hostile=nd.get("is_hostile", False), hp=nd.get("hp", 100),
            quests=nd.get("quests", []),
        ) for nd in data.get("npcs", [])]

        items = [Item(
            name=id_.get("name", "无名道具"), description=id_.get("description", ""),
            type=id_.get("type", "杂项"), rarity=id_.get("rarity", "普通"),
            value=id_.get("value", 0), stats=id_.get("stats", {}),
        ) for id_ in data.get("items", [])]

        events = [SceneEvent(
            trigger=ed.get("trigger", ""), description=ed.get("description", ""),
            resolved=ed.get("resolved", False),
        ) for ed in data.get("events", [])]

        return Scene(
            name=data.get("name", scene_id),
            description=data.get("description", "普通的场景。"),
            atmosphere=data.get("atmosphere", ""),
            exits=data.get("exits", {}),
            npcs=npcs, items=items, events=events,
        )

    # ═══════════════════════════════════════════════════════════
    # NPC 对话
    # ═══════════════════════════════════════════════════════════

    def generate_npc_dialogue(
        self, npc: NPC, player_action: str, context: str
    ) -> str:
        npc_profile = json.dumps({
            "name": npc.name, "role": npc.role,
            "personality": npc.personality, "mood": npc.mood,
        }, ensure_ascii=False)

        prompt = f"""你是RPG游戏中的NPC {npc.name}。根据角色设定生成对话回复。

角色信息: {npc_profile}
玩家行为: {player_action}
场景上下文: {context}

以角色身份回复，保持人设一致，2-5句话。"""
        return self._call_llm(prompt, expect_json=False, temperature=0.9)

    # ═══════════════════════════════════════════════════════════
    # 世界初始化
    # ═══════════════════════════════════════════════════════════

    def generate_world(self, world_concept: str) -> dict:
        prompt = f"""根据用户的世界概念，生成完整的RPG世界设定。

世界概念: {world_concept}

输出JSON（只输出JSON）:
{{
    "name": "世界名称",
    "theme": "中古奇幻/修仙/科幻/末日/…",
    "era": "时代背景",
    "geography": "地理概况",
    "factions": ["势力1", "势力2"],
    "magic_system": "力量体系",
    "starting_scene": {{
        "name": "起始场景名",
        "description": "起始场景描述（50-100字）",
        "atmosphere": "氛围"
    }}
}}"""
        response = self._call_llm(prompt, max_tokens=1024)
        return self._parse_json_response(response)

    # ═══════════════════════════════════════════════════════════
    # 战斗叙述
    # ═══════════════════════════════════════════════════════════

    def generate_combat_narration(
        self, player: dict, enemies: list, action: str, result: dict
    ) -> str:
        prompt = f"""你是RPG战斗叙述者。生动描述战斗过程。

玩家: {json.dumps(player, ensure_ascii=False)}
敌人: {json.dumps(enemies, ensure_ascii=False)}
行动: {action}
结果: {json.dumps(result, ensure_ascii=False)}

用2-3句话生动描述这个战斗瞬间。"""
        return self._call_llm(prompt, expect_json=False, temperature=0.9)

    # ═══════════════════════════════════════════════════════════
    # 任务生成
    # ═══════════════════════════════════════════════════════════

    def generate_quest(self, context: dict) -> dict:
        prompt = f"""根据游戏上下文，生成一个支线任务。

上下文: {json.dumps(context, ensure_ascii=False)}

输出JSON:
{{
    "name": "任务名称",
    "description": "任务描述",
    "objectives": ["目标1", "目标2"],
    "rewards": {{"exp": 100, "gold": 50, "items": []}},
    "giver": "发布者NPC名称"
}}"""
        response = self._call_llm(prompt, max_tokens=512)
        return self._parse_json_response(response)

    # ═══════════════════════════════════════════════════════════
    # 道具生成
    # ═══════════════════════════════════════════════════════════

    def generate_item(self, context: str) -> Optional[Item]:
        prompt = f"""根据上下文，生成一个RPG游戏道具。

上下文: {context}

输出JSON:
{{
    "name": "道具名称",
    "description": "道具描述",
    "type": "武器/防具/消耗品/任务物品/材料",
    "rarity": "普通/稀有/史诗/传说",
    "value": 10,
    "stats": {{"atk": 5}}
}}"""
        response = self._call_llm(prompt, max_tokens=256)
        data = self._parse_json_response(response)
        if data:
            return Item(
                name=data.get("name", "无名道具"),
                description=data.get("description", ""),
                type=data.get("type", "杂项"),
                rarity=data.get("rarity", "普通"),
                value=data.get("value", 0),
                stats=data.get("stats", {}),
            )
        return None
