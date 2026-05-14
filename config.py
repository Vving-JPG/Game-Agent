#!/usr/bin/env python3
"""
Game-Agent 配置管理 — JSON 配置文件 + 环境变量回退。
所有可调参数集中管理，支持运行时读写。
"""

import json
import os


DEFAULT_CONFIG = {
    "model": "deepseek-v4-flash",
    "models_available": ["deepseek-v4-flash", "deepseek-v4-pro"],
    "api": {
        "key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com",
    },
    "memory": {
        "enabled": True,
        "dir": "memory_store",
    },
    "sandbox": {
        "readonly_default": False,
        "max_file_size": 50000,
        "allowed_dirs": [],
    },
    "logging": {
        "level": "INFO",
        "file": "logs/agent.log",
        "max_bytes": 1_048_576,
        "backup_count": 3,
    },
    "chat": {
        "save_history": True,
        "history_dir": "memory_store/chat_history",
        "max_history_files": 50,
        "max_tool_rounds": 10,
        "prompt_file": "SYSTEM_PROMPT.md",
    },
    "rag": {
        "chunk_size": 500,
        "chunk_overlap": 50,
        "top_k": 3,
    },
    "skills": {
        "enabled": True,
        "dir": "memory_store/skills",
    },
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.json")


class Config:
    """统一配置访问器，JSON 文件 > 默认值。"""

    def __init__(self, config_path: str = None):
        self.path = config_path or CONFIG_PATH
        self.data = self._deep_copy(DEFAULT_CONFIG)
        self.load()

    # ── 读写 ──

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._deep_update(self.data, loaded)
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ── 访问 ──

    def get(self, *keys, default=None):
        d = self.data
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return default
        return d if d is not None else default

    def set(self, *keys, value):
        d = self.data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    @property
    def model(self):
        return self.get("model")

    @property
    def use_memory(self):
        return self.get("memory", "enabled")

    # ── 工具方法 ──

    @staticmethod
    def _deep_copy(d):
        if isinstance(d, dict):
            return {k: Config._deep_copy(v) for k, v in d.items()}
        if isinstance(d, list):
            return [Config._deep_copy(v) for v in d]
        return d

    @staticmethod
    def _deep_update(base, update):
        for k, v in update.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                Config._deep_update(base[k], v)
            else:
                base[k] = v


# 模块级快捷方式
def load_config(path: str = None) -> Config:
    return Config(path)
