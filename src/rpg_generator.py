"""
RPG 游戏内容生成器

集成 OpenViking 和 DeepSeek API 的 RPG 内容生成工具
支持对话式交互、文件操作和记忆保存
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class RPGGenerator:
    """RPG 游戏内容生成器"""

    def __init__(self, config_path: str = "openviking_workspace/ov.conf"):
        """初始化生成器"""
        abs_config_path = Path(config_path).absolute()
        os.environ["OPENVIKING_CONFIG_FILE"] = str(abs_config_path)

        # 项目根目录
        self.project_root = Path("d:/Game-Agent")

        # 对话记忆保存路径
        self.memory_dir = self.project_root / "openviking_workspace" / "viking" / "default" / "user" / "default" / "memories" / "conversations"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.skills = self._load_skills()
        self.api_key = "sk-fea502e13b1247b188308dd404dcc8e1"
        self.api_base = "https://api.deepseek.com/v1"

        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            self.use_ai = True
        except ImportError:
            print("警告: 未安装 openai 包，将使用模拟数据")
            self.use_ai = False

        # 当前对话记录
        self.conversation_history = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _load_skills(self) -> Dict[str, str]:
        """加载技能定义"""
        skills = {}
        skills_dir = self.project_root / "openviking_workspace/viking/default/agent/default/skills"
        if skills_dir.exists():
            for skill_file in skills_dir.glob("*.md"):
                if not skill_file.name.startswith("."):
                    skills[skill_file.stem] = skill_file.read_text(encoding="utf-8")
        return skills

    def save_conversation(self, user_msg: str, ai_msg: str):
        """保存对话到记忆 - 自动调用"""
        timestamp = datetime.now().isoformat()
        conversation_entry = {
            "timestamp": timestamp,
            "user": user_msg,
            "assistant": ai_msg
        }

        # 保存到内存
        self.conversation_history.append(conversation_entry)

        # 保存到文件
        memory_file = self.memory_dir / f"session_{self.session_id}.jsonl"
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(conversation_entry, ensure_ascii=False) + "\n")

    def load_conversation_history(self, limit: int = 10) -> List[Dict]:
        """加载历史对话"""
        history = []
        # 加载所有会话文件
        for mem_file in sorted(self.memory_dir.glob("session_*.jsonl")):
            with open(mem_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        history.append(json.loads(line))
        return history[-limit:]  # 返回最近 limit 条

    def list_files(self, path: str = ".") -> List[str]:
        """列出项目文件夹中的文件"""
        target_path = self.project_root / path
        if not target_path.exists():
            return [f"路径不存在: {path}"]

        files = []
        try:
            for item in target_path.iterdir():
                if item.is_dir():
                    files.append(f"[目录] {item.name}/")
                else:
                    files.append(f"[文件] {item.name}")
        except Exception as e:
            return [f"读取失败: {e}"]

        return files

    def read_file(self, filepath: str) -> str:
        """读取项目文件夹中的文件"""
        target_path = self.project_root / filepath
        if not target_path.exists():
            return f"文件不存在: {filepath}"

        try:
            return target_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"读取失败: {e}"

    def write_file(self, filepath: str, content: str) -> str:
        """写入文件到项目文件夹"""
        target_path = self.project_root / filepath

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return f"✅ 已保存: {filepath}"
        except Exception as e:
            return f"❌ 保存失败: {e}"

    def _call_deepseek(self, prompt: str, system_prompt: str = None) -> str:
        """调用 DeepSeek API"""
        if not self.use_ai:
            return self._mock_response(prompt)

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": "你是一个专业的 RPG 游戏内容生成器。"})

            # 添加历史对话作为上下文
            history = self.load_conversation_history(5)
            for entry in history:
                messages.append({"role": "user", "content": entry["user"]})
                messages.append({"role": "assistant", "content": entry["assistant"]})

            messages.append({"role": "user", "content": prompt})

            response = self.client.chat.completions.create(
                model="deepseek-v4-pro",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content
        except Exception as e:
            print(f"API 调用失败: {e}")
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """模拟返回"""
        if "道具" in prompt or "武器" in prompt:
            return json.dumps({
                "名称": "烈焰之刃",
                "类型": "长剑",
                "稀有度": "稀有",
                "描述": "剑身刻有火焰符文",
                "属性": {"攻击力": "+15"},
                "背景故事": "由火山黑曜石锻造"
            }, ensure_ascii=False)
        return "模拟回复"

    def chat(self, message: str) -> str:
        """
        对话模式 - 自动保存对话记录
        """
        # 构建系统提示词，包含文件操作能力
        system_prompt = """你是一个专业的 RPG 游戏内容生成器，可以帮助用户生成游戏内容并操作项目文件。

你可以使用以下工具操作项目文件夹:
- 列出文件: 当你需要查看目录内容时
- 读取文件: 当你需要查看文件内容时  
- 写入文件: 当你需要保存生成的内容时

可用命令格式:
/list_files <路径>  - 列出指定路径的文件
/read_file <文件路径> - 读取文件内容
/write_file <文件路径> <内容> - 写入文件

对话记录会自动保存到记忆中。"""

        # 检测文件操作命令
        if message.startswith("/list_files"):
            parts = message.split(maxsplit=1)
            path = parts[1] if len(parts) > 1 else "."
            result = self.list_files(path)
            response = "📁 文件列表:\n" + "\n".join(result)
            # 自动保存对话
            self.save_conversation(message, response)
            return response

        if message.startswith("/read_file"):
            parts = message.split(maxsplit=1)
            if len(parts) < 2:
                response = "用法: /read_file <文件路径>"
                self.save_conversation(message, response)
                return response
            filepath = parts[1]
            result = self.read_file(filepath)
            response = f"📄 文件内容 ({filepath}):\n{result}"
            self.save_conversation(message, response)
            return response

        if message.startswith("/write_file"):
            # 解析: /write_file <路径> <内容>
            parts = message.split(maxsplit=2)
            if len(parts) < 3:
                response = "用法: /write_file <文件路径> <内容>"
                self.save_conversation(message, response)
                return response
            filepath = parts[1]
            content = parts[2]
            result = self.write_file(filepath, content)
            response = result
            self.save_conversation(message, response)
            return response

        # 调用 AI 生成回复
        response = self._call_deepseek(message, system_prompt)

        # 自动保存对话记录
        self.save_conversation(message, response)

        return response

    def generate_item(self, level: int, rarity: str, item_type: str = "武器") -> Dict:
        """生成道具"""
        prompt = f"生成一个 RPG 游戏道具:\n"
        prompt += f"- 玩家等级: {level}\n"
        prompt += f"- 稀有度: {rarity}\n"
        prompt += f"- 类型: {item_type}\n"
        prompt += "\n请以 JSON 格式返回，包含: 名称、类型、稀有度、描述、属性、背景故事"

        response = self._call_deepseek(prompt)

        try:
            # 尝试解析 JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                item_data = json.loads(json_match.group())
            else:
                item_data = {"raw_response": response}
        except:
            item_data = {"raw_response": response}

        # 自动保存到记忆
        self.save_conversation(
            f"生成道具: 等级{level}, {rarity}, {item_type}",
            json.dumps(item_data, ensure_ascii=False)
        )

        return item_data

    def generate_npc(self, location: str, role: str, importance: str = "次要") -> Dict:
        """生成 NPC"""
        prompt = f"生成一个 RPG 游戏 NPC:\n"
        prompt += f"- 所在地点: {location}\n"
        prompt += f"- 角色定位: {role}\n"
        prompt += f"- 重要程度: {importance}\n"
        prompt += "\n请以 JSON 格式返回，包含: 姓名、年龄、职业、性格、背景故事、对话风格"

        response = self._call_deepseek(prompt)

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                npc_data = json.loads(json_match.group())
            else:
                npc_data = {"raw_response": response}
        except:
            npc_data = {"raw_response": response}

        # 自动保存到记忆
        self.save_conversation(
            f"生成NPC: {location}, {role}, {importance}",
            json.dumps(npc_data, ensure_ascii=False)
        )

        return npc_data

    def generate_quest(self, quest_type: str, difficulty: str, level: int, location: str) -> Dict:
        """生成任务"""
        prompt = f"生成一个 RPG 游戏任务:\n"
        prompt += f"- 任务类型: {quest_type}\n"
        prompt += f"- 难度: {difficulty}\n"
        prompt += f"- 推荐等级: {level}\n"
        prompt += f"- 发生地点: {location}\n"
        prompt += "\n请以 JSON 格式返回，包含: 任务名称、描述、目标、奖励、前置条件"

        response = self._call_deepseek(prompt)

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                quest_data = json.loads(json_match.group())
            else:
                quest_data = {"raw_response": response}
        except:
            quest_data = {"raw_response": response}

        # 自动保存到记忆
        self.save_conversation(
            f"生成任务: {quest_type}, {difficulty}, 等级{level}, {location}",
            json.dumps(quest_data, ensure_ascii=False)
        )

        return quest_data

    def search_memories(self, keyword: str) -> List[Dict]:
        """搜索记忆库"""
        history = self.load_conversation_history(100)
        results = []

        for entry in history:
            if keyword in entry.get("user", "") or keyword in entry.get("assistant", ""):
                results.append(entry)

        return results

    def get_conversation_summary(self) -> str:
        """获取对话摘要"""
        history = self.load_conversation_history(20)
        if not history:
            return "暂无对话记录"

        summary = f"当前会话 (ID: {self.session_id})\n"
        summary += f"历史对话数: {len(history)}\n\n"

        for i, entry in enumerate(history[-5:], 1):
            summary += f"[{i}] 用户: {entry['user'][:50]}...\n"
            summary += f"    AI: {entry['assistant'][:50]}...\n\n"

        return summary
