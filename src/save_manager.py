"""
存档管理器 — JSON 持久化存档，支持多槽位保存/加载/列表/删除。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from src.game_world import GameWorld


class SaveManager:
    """持久化存档管理"""

    def __init__(self, save_dir: str = "saves"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _slot_path(self, slot: str) -> Path:
        return self.save_dir / f"{slot}.json"

    def save_game(self, game_world: GameWorld, slot: str = "auto") -> bool:
        try:
            save_data = {
                "version": 1,
                "timestamp": datetime.now().isoformat(),
                "slot": slot,
                "world": game_world.to_dict(),
            }
            self._slot_path(slot).write_text(
                json.dumps(save_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except (IOError, OSError) as e:
            print(f"[SaveManager] 保存失败: {e}")
            return False

    def load_game(self, slot: str = "auto") -> Optional[GameWorld]:
        path = self._slot_path(slot)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            world_data = data.get("world", {})
            return GameWorld.from_dict(world_data, save_dir=str(self.save_dir))
        except (json.JSONDecodeError, IOError, KeyError) as e:
            print(f"[SaveManager] 加载失败: {e}")
            return None

    def list_saves(self) -> List[Dict]:
        saves = []
        for p in sorted(
            self.save_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        ):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                world = data.get("world", {})
                player = world.get("player", {})
                scenes = world.get("scenes", {})
                cid = player.get("current_scene_id", "")
                cs = scenes.get(cid, {})
                saves.append({
                    "slot": data.get("slot", p.stem),
                    "timestamp": data.get("timestamp", ""),
                    "player_name": player.get("name", "?"),
                    "player_level": player.get("level", 1),
                    "scene_name": cs.get("name", "?"),
                    "game_day": player.get("game_day", 1),
                    "file": str(p),
                })
            except (json.JSONDecodeError, IOError):
                pass
        return saves

    def delete_save(self, slot: str) -> bool:
        path = self._slot_path(slot)
        if path.exists():
            try:
                path.unlink()
                return True
            except OSError:
                pass
        return False

    def get_latest_save(self) -> Optional[Dict]:
        saves = self.list_saves()
        return saves[0] if saves else None

    def has_save(self, slot: str) -> bool:
        return self._slot_path(slot).exists()
