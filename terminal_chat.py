#!/usr/bin/env python3
"""
终端对话程序 — DeepSeek API + 渐进式记忆 + RAG 文档知识库 + 技能系统
v2: 配置系统 / 日志 / TF-IDF 检索 / 技能加载 / 会话持久化 / 扩展工具集

记忆架构：
  L0 INDEX.md    — 全局索引，每次启动加载 (~1KB)
  L1 agents/*.md — 主题摘要，关键词匹配后展开
  L2 topics/*.md — 专题详情，按需深入
  L3 journal/    — 每日日志，append-only
  MEMORY.md      — 长期事实，就地更新

技能模块（memory_store/skills/）：
  sandbox.py      — 文件 I/O 安全沙箱
  file_tools.py   — 文件操作工具定义 + 沙箱保护的执行器（9 个工具）
  tfidf_index.py  — TF-IDF 检索引擎
  rag.py          — RAG 文档知识库
  skill_loader.py — JSON 技能加载器
"""

import os
import sys
import json
import glob as globmod
from datetime import datetime
from typing import List, Dict, Optional

from openai import OpenAI
from dotenv import load_dotenv

from config import Config
from logger import setup_logging, get_logger
from progressive_memory import ProgressiveMemory
from memory_store.skills.sandbox import Sandbox
from memory_store.skills.file_tools import FileToolSet
from memory_store.skills.skill_loader import SkillLoader
from memory_store.skills.rag import RagKnowledgeBase

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "key.env"))


class TerminalChatAgent:
    """带渐进式记忆、RAG、技能系统的终端聊天 Agent (v2)"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        config: Config,
    ):
        self.config = config
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = config.model
        self.messages: List[Dict] = []
        self.use_memory = config.use_memory
        self._log = get_logger()

        # ── 沙箱 + 文件工具 ──
        project_root = os.path.dirname(os.path.abspath(__file__))
        self.sandbox = Sandbox(project_root)
        self.sandbox.max_file_size = config.get("sandbox", "max_file_size", default=50000)
        for extra_dir in config.get("sandbox", "allowed_dirs", default=[]):
            abs_dir = os.path.abspath(os.path.join(project_root, extra_dir))
            if os.path.isdir(abs_dir):
                self.sandbox.add_allowed_dir(abs_dir)
        self.file_tools = FileToolSet(self.sandbox)

        # ── 技能系统 ──
        self.skill_loader = None
        self._skills_tools: List[Dict] = []
        self._skills_prompts: List[str] = []
        if config.get("skills", "enabled", default=True):
            skills_dir = config.get("skills", "dir", default="memory_store/skills")
            skills_abs = os.path.join(project_root, skills_dir)
            self.skill_loader = SkillLoader(skills_abs)
            loaded = self.skill_loader.load_all()
            if loaded:
                self._skills_tools = self.skill_loader.get_tool_definitions()
                self._skills_prompts = self.skill_loader.get_system_prompts()
                self._log.info("技能系统: 加载了 %d 个技能", loaded)

        # ── 渐进式记忆 ──
        self.memory = None
        self.kb_ready = False
        if self.use_memory:
            try:
                self.memory = ProgressiveMemory(
                    memory_dir=os.path.join(project_root, config.get("memory", "dir", default="memory_store"))
                )
                self.kb_ready = any(
                    globmod.glob(os.path.join(self.memory.kb_dir, "*.txt"))
                )
                self._log.info("记忆系统已启用")
                print("🧠 渐进式记忆系统已启用")
                print(f"   L0 INDEX: {'✓' if os.path.exists(self.memory.index_path) else '空'}")
                print(f"   L1 Agents: {len(globmod.glob(os.path.join(self.memory.agents_dir, '*.md')))} 个")
                print(f"   L2 Topics: {len(globmod.glob(os.path.join(self.memory.topics_dir, '*.md')))} 个")
                print(f"   L3 Journal: {len(globmod.glob(os.path.join(self.memory.journal_dir, '*.md')))} 天")
                if self.kb_ready:
                    kb_count = len(globmod.glob(os.path.join(self.memory.kb_dir, "*.txt")))
                    print(f"   📚 RAG 知识库: {kb_count} 个文档")
            except Exception as e:
                self._log.warning("无法初始化记忆系统: %s", e)
                print(f"⚠️ 无法初始化记忆系统: {e}")
                self.use_memory = False

        # ── RAG 知识库 ──
        self.rag = None
        if self.use_memory and self.memory:
            try:
                self.rag = RagKnowledgeBase(
                    kb_dir=self.memory.kb_dir,
                    chunk_size=config.get("rag", "chunk_size", default=500),
                    chunk_overlap=config.get("rag", "chunk_overlap", default=50),
                )
                if self.kb_ready:
                    self.rag.load()
                    self._log.info("RAG 知识库: 已加载 %d 个文档", self.kb_ready)
            except Exception as e:
                self._log.warning("RAG 知识库初始化失败: %s", e)

        # ── 会话持久化 ──
        self.history_dir = None
        self.session_id = None
        if config.get("chat", "save_history", default=True):
            hist_rel = config.get("chat", "history_dir", default="memory_store/chat_history")
            self.history_dir = os.path.join(project_root, hist_rel)
            os.makedirs(self.history_dir, exist_ok=True)
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ── 提示词文件（可直接编辑 memory_store/ 下同名文件） ──
        self.prompt_file = config.get("chat", "prompt_file", default="SYSTEM_PROMPT.md")

        self._build_system_message()

    # ──────────────── 系统提示构建 ────────────────

    def _build_system_message(self):
        """从 memory_store/SYSTEM_PROMPT.md 加载提示词模板，替换占位符。"""
        template = self._load_prompt_template(self.prompt_file)

        # 准备替换值
        index_text = ""
        memory_text = ""
        skills_text = ""
        if self.use_memory and self.memory:
            index_text = self.memory.load_index() or ""
            mem = self.memory.load_memory()
            if mem and len(mem) > 50:
                memory_text = f"【长期记忆】\n{mem[:500]}"
        if self._skills_prompts:
            skills_text = "【已加载技能】\n" + "\n".join(self._skills_prompts)

        # 占位符替换
        replacements = {
            "{{INDEX}}": index_text,
            "{{MEMORY}}": memory_text,
            "{{SKILLS}}": skills_text,
            "{{DATE}}": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        for placeholder, value in replacements.items():
            template = template.replace(placeholder, value)

        # RAG 规则追加
        if self.rag and self.rag.ready:
            template += (
                "\n\n当提供知识库文档片段时，请仅基于这些片段回答。"
                "如果无法从片段中找到答案，请明确说明'未在文档中找到相关信息'，不要编造。"
            )

        self.messages.append({"role": "system", "content": template.strip()})

    def _load_prompt_template(self, filename: str) -> str:
        """从 memory_store/ 加载提示词模板文件"""
        project_root = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(project_root, "memory_store", filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        # 回退：内置最小模板
        return (
            "你是一个AI助手。用中文回答，简洁自然。\n\n"
            "{{INDEX}}\n\n{{MEMORY}}\n\n{{SKILLS}}"
        )

    def switch_prompt(self, filename: str):
        """切换到另一个提示词文件，重建 system message"""
        project_root = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(project_root, "memory_store", filename)
        if not os.path.exists(path):
            print(f"❌ 提示词文件不存在: memory_store/{filename}")
            return False
        self.prompt_file = filename
        self.messages = []
        self._build_system_message()
        print(f"✅ 已切换到提示词: memory_store/{filename}")
        self._log.info("切换到提示词: %s", filename)
        return True

    # ──────────────── 会话持久化 ────────────────

    def _save_chat_history(self, user_input: str, response: str):
        """保存当前会话到文件"""
        if not self.history_dir or not self.session_id:
            return
        try:
            fpath = os.path.join(self.history_dir, f"{self.session_id}.json")
            record = {
                "session_id": self.session_id,
                "model": self.model,
                "created": datetime.now().isoformat(),
                "messages": self.messages,
            }
            record["messages"].append({
                "role": "user", "content": user_input, "timestamp": datetime.now().isoformat()
            })
            record["messages"].append({
                "role": "assistant", "content": response, "timestamp": datetime.now().isoformat()
            })
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            self._cleanup_old_histories()
        except Exception as e:
            self._log.debug("保存会话历史失败: %s", e)

    def _cleanup_old_histories(self):
        """清理旧会话文件，保留最近 N 个"""
        max_files = self.config.get("chat", "max_history_files", default=50)
        files = sorted(
            globmod.glob(os.path.join(self.history_dir, "*.json")),
            key=os.path.getmtime,
            reverse=True,
        )
        for f in files[max_files:]:
            try:
                os.remove(f)
            except Exception:
                pass

    def load_session(self, session_id: str) -> bool:
        """加载指定会话的历史消息"""
        if not self.history_dir:
            print("⚠️ 会话持久化未启用")
            return False
        fpath = os.path.join(self.history_dir, f"{session_id}.json")
        if not os.path.exists(fpath):
            print(f"❌ 会话不存在: {session_id}")
            return False
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                record = json.load(f)
            self.messages = record.get("messages", [])
            self.session_id = session_id
            print(f"✅ 已加载会话 {session_id} ({len(self.messages)} 条消息)")
            return True
        except Exception as e:
            print(f"❌ 加载会话失败: {e}")
            return False

    def list_sessions(self) -> List[str]:
        """列出所有会话 ID"""
        if not self.history_dir:
            return []
        files = sorted(
            globmod.glob(os.path.join(self.history_dir, "*.json")),
            key=os.path.getmtime,
            reverse=True,
        )
        return [os.path.splitext(os.path.basename(f))[0] for f in files]

    # ──────────────── 日志 / 记忆辅助 ────────────────

    def _save_journal(self, user_input: str, response: str):
        """记录对话到当日日志 (L3)"""
        if not self.use_memory or not self.memory:
            return
        try:
            self.memory.save_journal(
                title=f"对话: {user_input[:40]}{'...' if len(user_input) > 40 else ''}",
                body=f"**用户**: {user_input}\n\n**AI**: {response[:200]}{'...' if len(response) > 200 else ''}",
                tags=["chat"],
            )
        except Exception as e:
            self._log.debug("记录日志失败: %s", e)

    def _retrieve_memories(self, query: str) -> str:
        """渐进式检索记忆（L0 → L1 → L2 逐层展开，v2: TF-IDF）"""
        if not self.use_memory or not self.memory:
            return ""
        try:
            return self.memory.retrieve(query)
        except Exception as e:
            self._log.warning("检索记忆失败: %s", e)
            return ""

    def _retrieve_documents(self, query: str) -> str:
        """从 RAG 知识库检索相关文档片段（v2: TF-IDF 分块）"""
        if not self.rag or not self.rag.ready:
            return ""
        try:
            return self.rag.search_as_context(
                query,
                top_k=self.config.get("rag", "top_k", default=3),
            )
        except Exception as e:
            self._log.warning("RAG 检索失败: %s", e)
            return ""

    # ──────────────── 工具定义聚合 ────────────────

    def _get_all_tool_definitions(self) -> List[Dict]:
        """聚合所有工具定义：文件工具 + 技能工具"""
        tools = list(self.file_tools.get_definitions())
        tools.extend(self._skills_tools)
        return tools

    # ──────────────── 两阶段对话 ────────────────

    def _print_debug_prompt(self, messages: List[Dict]):
        """打印完整 prompt 用于调试。"""
        print("\n" + "=" * 80)
        print("📤 发送给 LLM 的完整 Prompt：")
        print("=" * 80)
        for msg in messages:
            role = msg.get("role", "?").upper()
            content = msg.get("content", "") or ""
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    content += (
                        f"\n[tool_call: {fn.get('name', '?')}"
                        f"({fn.get('arguments', '')[:200]})]"
                    )
            print(f"\n【{role}】\n{content}")
        print("=" * 80)

    def _resolve_with_tools(self, user_content: str, debug: bool) -> tuple:
        """
        Phase 1: 非流式工具解析。
        返回 (final_content, reasoning, message_history)。
        """
        messages = self.messages.copy()
        messages.append({"role": "user", "content": user_content})

        if debug:
            self._print_debug_prompt(messages)

        max_rounds = self.config.get("chat", "max_tool_rounds", default=10)
        for round_idx in range(max_rounds):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._get_all_tool_definitions(),
                stream=False,
            )
            choice = response.choices[0]
            msg = choice.message

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                if debug:
                    print(f"\n[Tool Call Round {round_idx + 1}]")
                assistant_msg = {
                    "role": "assistant",
                    "content": msg.content or "",
                    "reasoning_content": getattr(msg, "reasoning_content", None) or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tc in msg.tool_calls:
                    result = self._execute_tool(tc)
                    if debug:
                        print(
                            f"  -> {tc.function.name}(...) 返回 {len(result)} 字符"
                        )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        }
                    )
            else:
                reasoning = getattr(msg, "reasoning_content", None) or ""
                content = msg.content or ""
                messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "reasoning_content": reasoning,
                    }
                )
                return content, reasoning, messages

        error_msg = f"Error: 工具调用超过最大轮数({max_rounds})，请简化请求。"
        self._log.warning(error_msg)
        return error_msg, "", messages

    def _execute_tool(self, tool_call) -> str:
        """执行工具调用：文件工具 → 技能工具 → 通用回退"""
        name = tool_call.function.name

        # 文件工具（9 个核心工具）
        if name in {"read_file", "write_file", "list_directory",
                    "get_working_directory", "append_file", "grep_files",
                    "delete_file", "move_file", "shell_exec"}:
            return self.file_tools.execute(tool_call)

        # 技能工具：review_code / find_imports
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return f"Error: 无效的 JSON 参数: {e}"

        if name == "review_code":
            return self._handle_review_code(args.get("path", ""))
        if name == "find_imports":
            return self._handle_find_imports(args.get("path", ""))

        return f"Error: 工具 '{name}' 未注册执行器。可用: " + ", ".join(
            [t["function"]["name"] for t in self._get_all_tool_definitions()]
        )

    def _stream_response(
        self, messages: List[Dict], original_user_input: str, debug: bool
    ):
        """
        Phase 2: 流式展示（带 reasoning_content 思考过程）。
        """
        if debug:
            print("\n" + "=" * 80)
            print("[Phase 2: Streaming display]")
            print("=" * 80)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
            )

            reasoning_buffer = ""
            answer_buffer = ""
            is_reasoning = True

            print("🤖 AI: ", end="", flush=True)

            for chunk in response:
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None) or ""
                content = getattr(delta, "content", None) or ""

                if reasoning:
                    if not is_reasoning:
                        print("\n" + "=" * 40 + " 思考续 " + "=" * 40)
                        is_reasoning = True
                    print(f"\033[33m{reasoning}\033[0m", end="", flush=True)
                    reasoning_buffer += reasoning

                if content and is_reasoning:
                    print("\n" + "=" * 40 + " 正式回答 " + "=" * 40)
                    is_reasoning = False

                if content:
                    print(content, end="", flush=True)
                    answer_buffer += content

            print()

            assistant_response = answer_buffer
            self.messages.append({"role": "user", "content": original_user_input})
            self.messages.append(
                {"role": "assistant", "content": assistant_response}
            )

            self._save_journal(original_user_input, assistant_response)

            # 会话持久化
            if self.history_dir:
                self._save_chat_history(original_user_input, assistant_response)

        except Exception as e:
            self._log.error("API 流式调用失败: %s", e)
            print(f"\n❌ API 调用失败: {e}")

    def chat(self, user_input: str, debug: bool = False) -> str:
        """
        发送消息，支持两阶段模式：
          Phase 1：非流式工具解析（始终携带 tool 定义，AI 按需调用）
          Phase 2：流式展示思考过程 + 最终回答
        """
        # 1. 渐进检索记忆 + RAG
        memory_context = self._retrieve_memories(user_input)
        doc_context = self._retrieve_documents(user_input)
        context_parts = []
        if memory_context:
            context_parts.append(memory_context)
        if doc_context:
            context_parts.append(doc_context)
        context_block = "\n\n".join(context_parts) if context_parts else ""

        if context_block:
            final_user_content = (
                f"{context_block}\n\n现在请基于以上信息回答：{user_input}"
            )
        else:
            final_user_content = user_input

        # --- Phase 1：非流式工具解析 ---
        final_content, reasoning, tool_resolved_messages = (
            self._resolve_with_tools(final_user_content, debug)
        )

        # --- Phase 2：流式展示 ---
        self._stream_response(tool_resolved_messages, user_input, debug)

        return self.messages[-1]["content"] if self.messages else ""

    # ──────────────── 管理命令 ────────────────

    def clear_history(self):
        """清空当前会话历史（不影响长期记忆）"""
        self.messages = []
        self._build_system_message()
        print("✅ 当前会话历史已清空")

    def show_memory_status(self):
        """显示记忆系统状态"""
        if not self.memory:
            print("⚠️ 记忆系统未启用")
            return
        status = self.memory.get_status()
        print("\n" + "=" * 50)
        print("🧠 渐进式记忆系统状态")
        print("=" * 50)
        print(f"  INDEX.md:    {'✓' if status['index_exists'] else '空'}")
        print(f"  MEMORY.md:   {'✓' if status['memory_exists'] else '空'}")
        print(f"  Agents:      {status['agents_count']} 个")
        print(f"  Topics:      {status['topics_count']} 个")
        print(f"  Journal:     {status['journal_days']} 天")
        print(f"  知识库文档:  {status['kb_docs']} 个")

        print(f"\n📋 Agents:")
        for f in sorted(
            globmod.glob(os.path.join(self.memory.agents_dir, "*.md"))
        ):
            print(f"   - {os.path.splitext(os.path.basename(f))[0]}")
        print(f"📋 Topics:")
        for f in sorted(
            globmod.glob(os.path.join(self.memory.topics_dir, "*.md"))
        ):
            print(f"   - {os.path.splitext(os.path.basename(f))[0]}")
        if self.skill_loader:
            print(f"\n🔧 已加载技能: {', '.join(self.skill_loader.list_skills())}")
        print("=" * 50)

    def register_topic(self, name: str):
        """注册一个新的 topic"""
        if not self.memory:
            print("⚠️ 记忆系统未启用")
            return
        print(
            f"📝 输入 topic '{name}' 的内容"
            "（输入 CANCEL 取消，输入 END 结束）:"
        )
        lines = []
        try:
            while True:
                line = input()
                if line.strip().upper() == "END":
                    break
                if line.strip().upper() == "CANCEL":
                    print("↩ 已取消")
                    return
                lines.append(line)
        except EOFError:
            pass
        if lines:
            content = "\n".join(lines)
            self.memory.register_topic(name, content)
            print(f"✅ Topic '{name}' 已注册，INDEX 已更新")
        else:
            print("↩ 已取消")

    def rebuild_index(self):
        """手动重建索引"""
        if not self.memory:
            print("⚠️ 记忆系统未启用")
            return
        self.memory.rebuild_index()
        print("✅ INDEX.md 已重建")
        self.messages = []
        self._build_system_message()
        print("✅ System prompt 已更新")

    def reload_rag(self):
        """重新加载 RAG 知识库"""
        if not self.rag:
            print("⚠️ RAG 知识库未启用")
            return
        count = self.rag.reload()
        print(f"✅ RAG 知识库已重载 ({count} 个文档)")

    # ──────────────── 技能工具实现 ────────────────

    def _handle_review_code(self, path: str) -> str:
        """技能工具：对 Python 文件进行基础代码审查"""
        resolved = self.sandbox.resolve_path(path)
        if not os.path.isfile(resolved):
            return f"Error: 文件不存在: {resolved}"
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error: 无法读取文件: {e}"

        issues = []
        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()
            # PEP 8: 行长度
            if len(stripped) > 120:
                issues.append(f"  L{i}: 行过长 ({len(stripped)} 字符 > 120)")
            # 裸 except
            if "except:" in stripped and "Exception" not in stripped:
                issues.append(f"  L{i}: 裸 except，建议指定异常类型")
            # print 调试残留
            if "print(" in stripped and "def " not in stripped:
                if "main" not in path.lower():
                    issues.append(f"  L{i}: 存在 print() 调用，建议使用 logger")

        if not issues:
            return f"✅ 代码审查 '{os.path.basename(resolved)}' ({len(lines)} 行): 未发现明显问题。"
        return (
            f"📋 代码审查 '{os.path.basename(resolved)}' ({len(lines)} 行):\n"
            + "\n".join(issues[:20])
        )

    def _handle_find_imports(self, path: str) -> str:
        """技能工具：查找 Python 文件中的 import 语句"""
        resolved = self.sandbox.resolve_path(path)
        if not os.path.isfile(resolved):
            return f"Error: 文件不存在: {resolved}"
        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            return f"Error: 无法读取文件: {e}"

        imports = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append(f"  L{i}: {stripped}")

        if not imports:
            return f"📦 '{os.path.basename(resolved)}': 未找到 import 语句。"
        return (
            f"📦 '{os.path.basename(resolved)}' 的导入 ({len(imports)} 条):\n"
            + "\n".join(imports[:30])
        )


# ──────────────── 主入口 ────────────────

def main():
    cfg = Config()

    # 初始化日志
    setup_logging(
        level=cfg.get("logging", "level", default="INFO"),
        log_file=os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            cfg.get("logging", "file", default="logs/agent.log"),
        ),
        max_bytes=cfg.get("logging", "max_bytes", default=1_048_576),
        backup_count=cfg.get("logging", "backup_count", default=3),
    )
    log = get_logger()
    log.info("Game-Agent v2 启动")

    api_key = os.getenv(
        cfg.get("api", "key_env", default="DEEPSEEK_API_KEY")
    )
    base_url = os.getenv(
        cfg.get("api", "base_url_env", default="DEEPSEEK_BASE_URL"),
        cfg.get("api", "base_url_default", default="https://api.deepseek.com"),
    )
    if not api_key:
        print(f"❌ 请在 key.env 中设置 {cfg.get('api', 'key_env', default='DEEPSEEK_API_KEY')}")
        sys.exit(1)

    print("=" * 56)
    print("🤖 DeepSeek 终端对话 v2 (渐进式记忆 + RAG + 技能 + 扩展工具)")
    print("=" * 56)
    print("\n可用模型:")
    models = cfg.get("models_available", default=["deepseek-v4-flash"])
    for i, m in enumerate(models, 1):
        marker = " (当前)" if m == cfg.model else ""
        print(f"  {i}) {m}{marker}")
    choice = input(f"请选择 (默认 {models.index(cfg.model) + 1 if cfg.model in models else 1}): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(models):
            cfg.set("model", value=models[idx])
    except ValueError:
        pass

    agent = TerminalChatAgent(
        api_key=api_key,
        base_url=base_url,
        config=cfg,
    )

    print("\n💬 命令（输入数字或文本）:")
    print("  1/quit   退出        5/topic    专题记忆")
    print("  2/clear   清空历史    6/index    重建索引")
    print("  3/debug   调试模式    7/sandbox  沙箱配置")
    print("  4/memory  记忆状态    8/readonly 只读切换")
    print("  9/shell   启用Shell   10/skills  列出技能")
    print("  11/rag    重载 RAG    12/session 会话管理")
    print("  13/config 配置状态    14/load    加载会话")
    print("  15/gm     GM模式     16/prompt  当前提示词")
    print("  (或直接聊天)")
    debug_mode = False

    while True:
        try:
            raw = input("\n👤 你: ").strip()
            if not raw:
                continue

            cmd = raw.lower()

            # ── 数字命令 ──
            if raw == "1" or cmd in ("quit", "exit", "q"):
                print("👋 再见！")
                log.info("Game-Agent v2 退出")
                break
            if raw == "2" or cmd == "clear":
                agent.clear_history()
                continue
            if raw == "3" or cmd == "debug":
                debug_mode = not debug_mode
                print(f"🔧 调试模式已{'开启' if debug_mode else '关闭'}")
                continue
            if raw == "4" or cmd == "memory":
                agent.show_memory_status()
                continue
            if raw == "5" or cmd.startswith("topic "):
                name = raw[6:].strip() if raw.startswith("5") else raw[6:].strip()
                if not name and raw != "5":
                    name = raw[6:].strip()
                if raw == "5":
                    name = input("  专题名称 (留空取消): ").strip()
                if name:
                    agent.register_topic(name)
                else:
                    print("↩ 已取消")
                continue
            if raw == "6" or cmd == "index":
                agent.rebuild_index()
                continue
            if raw == "7" or cmd == "sandbox":
                sb = agent.sandbox
                print(f"📂 沙箱根目录: {sb.base_path}")
                if len(sb.allowed_dirs) > 1:
                    print(f"   额外允许目录: {sb.allowed_dirs[1:]}")
                print(f"🔒 只读模式: {'开启' if sb.readonly else '关闭'}")
                print(f"🐚 Shell执行: {'启用' if sb.shell_enabled else '禁用'}")
                print(f"📏 最大文件读取: {sb.max_file_size:,} 字符")
                continue
            if raw == "8" or cmd == "readonly":
                agent.sandbox.readonly = not agent.sandbox.readonly
                print(
                    f"🔒 只读模式已{'开启' if agent.sandbox.readonly else '关闭'}"
                )
                continue
            if raw == "9" or cmd == "shell":
                agent.sandbox.shell_enabled = not agent.sandbox.shell_enabled
                print(
                    f"🐚 Shell执行已{'启用' if agent.sandbox.shell_enabled else '禁用'}"
                )
                continue
            if raw == "10" or cmd == "skills":
                if agent.skill_loader:
                    names = agent.skill_loader.list_skills()
                    if names:
                        print(f"🔧 已加载技能 ({len(names)}):")
                        for n in names:
                            skill = agent.skill_loader.get_skill(n)
                            print(f"   - {n}: {skill.description}")
                    else:
                        print("🔧 无已加载技能（将 skills/*.json 放入 skills/ 目录即可）")
                else:
                    print("⚠️ 技能系统未启用")
                continue
            if raw == "11" or cmd == "rag":
                agent.reload_rag()
                continue
            if raw == "12" or cmd == "session":
                sessions = agent.list_sessions()
                if sessions:
                    print(f"📁 会话列表 ({len(sessions)}):")
                    for s in sessions[:10]:
                        fpath = os.path.join(agent.history_dir, f"{s}.json")
                        mtime = datetime.fromtimestamp(
                            os.path.getmtime(fpath)
                        ).strftime("%Y-%m-%d %H:%M")
                        print(f"   {s}  ({mtime})")
                else:
                    print("📁 无已保存会话")
                continue
            if raw == "13" or cmd == "config":
                print("⚙️ 当前配置:")
                print(f"   模型: {cfg.model}")
                print(f"   记忆系统: {'启用' if cfg.use_memory else '禁用'}")
                print(f"   会话持久化: {'启用' if cfg.get('chat', 'save_history') else '禁用'}")
                print(f"   技能系统: {'启用' if cfg.get('skills', 'enabled') else '禁用'}")
                print(f"   RAG分块: {cfg.get('rag', 'chunk_size')} 字符")
                continue
            if raw == "14" or cmd.startswith("load "):
                sid = raw[5:].strip() if cmd.startswith("load ") else ""
                if not sid:
                    sid = input("  会话ID: ").strip()
                if sid:
                    agent.load_session(sid)
                continue
            if raw == "15" or cmd == "gm":
                agent.switch_prompt("GM_PROMPT.md")
                continue
            if raw == "16" or cmd == "prompt":
                print(f"📄 当前提示词: memory_store/{agent.prompt_file}")
                print("   可用: SYSTEM_PROMPT.md, GM_PROMPT.md")
                print("   切换: 输入 15/gm 或 prompt <文件名>")
                continue
            if cmd.startswith("prompt "):
                fname = raw[7:].strip()
                if fname:
                    agent.switch_prompt(fname)
                continue
            if cmd == "sandbox_dir" or cmd.startswith("allowpath "):
                new_path = raw[len("allowpath "):].strip() if cmd.startswith("allowpath ") else input("  允许目录路径: ").strip()
                if new_path:
                    abs_path = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), new_path)
                    )
                    if not os.path.isdir(abs_path):
                        print(f"❌ 目录不存在: {abs_path}")
                    else:
                        agent.sandbox.add_allowed_dir(abs_path)
                        print(f"✅ 已添加允许目录: {abs_path}")
                continue

            # ── 正常聊天 ──
            agent.chat(raw, debug=debug_mode)

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            log.info("Game-Agent v2 退出 (Ctrl+C)")
            break
        except Exception as e:
            log.error("运行错误: %s", e, exc_info=True)
            print(f"\n❌ 运行错误: {e}")


if __name__ == "__main__":
    main()
