#!/usr/bin/env python3
"""
技能加载器 — 从 skills/ 目录加载 JSON 技能定义，
将 tool definitions 和 system prompt 注入 Agent。
"""

import json
import os
import glob as globmod
from typing import List, Dict


class Skill:
    """单个技能定义。"""

    def __init__(self, name: str, data: dict):
        self.name = name
        self.description = data.get("description", "")
        self.system_prompt = data.get("system_prompt", "")
        self.tools: List[Dict] = data.get("tools", [])
        self.examples: List[str] = data.get("examples", [])
        self.created_at = data.get("created_at", "")
        self.enabled = data.get("enabled", True)

    def __repr__(self):
        return f"Skill({self.name}, tools={len(self.tools)})"


class SkillLoader:
    """扫描 skills/ 目录，加载所有 JSON 技能文件。"""

    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}

    def load_all(self) -> int:
        """加载目录下所有 .json 技能文件。返回加载数。"""
        self.skills.clear()
        if not os.path.isdir(self.skills_dir):
            return 0
        for fpath in sorted(globmod.glob(os.path.join(self.skills_dir, "*.json"))):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue
            name = data.get("name", os.path.splitext(os.path.basename(fpath))[0])
            skill = Skill(name, data)
            if skill.enabled:
                self.skills[name] = skill
        return len(self.skills)

    def get_tool_definitions(self) -> List[Dict]:
        """汇总所有已加载技能的 tool 定义。"""
        tools = []
        for skill in self.skills.values():
            tools.extend(skill.tools)
        return tools

    def get_system_prompts(self) -> List[str]:
        """汇总所有已加载技能的 system prompt 片段。"""
        prompts = []
        for skill in self.skills.values():
            if skill.system_prompt:
                prompts.append(f"【技能: {skill.name}】\n{skill.system_prompt}")
        return prompts

    def get_skill(self, name: str) -> Skill:
        """按名称获取单个技能。"""
        return self.skills.get(name)

    def list_skills(self) -> List[str]:
        """列出所有已加载技能名称。"""
        return list(self.skills.keys())
