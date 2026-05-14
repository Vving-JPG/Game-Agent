#!/usr/bin/env python3
"""
渐进式披露记忆系统 (Progressive Disclosure Memory)
v2: TF-IDF 增强检索 + 纯关键词回退

分层架构：
  L0 INDEX.md    — 全局索引，每次启动加载 (~1KB)
  L1 agents/*.md — 主题摘要，关键词匹配后展开 (~2KB each)
  L2 topics/*.md — 专题详情，按需深入 (~5-20KB each)
  L3 journal/    — 每日日志，append-only
  MEMORY.md      — 长期事实，就地更新

零外部依赖，纯 Markdown 文件存储。
"""

import os
import glob as globmod
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from memory_store.skills.tfidf_index import TfidfIndex


class ProgressiveMemory:
    """分层渐进式记忆系统（v2: TF-IDF 增强检索）"""

    def __init__(self, memory_dir: str = None):
        self.memory_dir = memory_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "memory_store"
        )
        self.agents_dir = os.path.join(self.memory_dir, "agents")
        self.topics_dir = os.path.join(self.memory_dir, "topics")
        self.journal_dir = os.path.join(self.memory_dir, "journal")
        self.kb_dir = os.path.join(self.memory_dir, "knowledge_base")
        self.index_path = os.path.join(self.memory_dir, "INDEX.md")
        self.memory_path = os.path.join(self.memory_dir, "MEMORY.md")
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录结构存在"""
        for d in [self.agents_dir, self.topics_dir, self.journal_dir, self.kb_dir]:
            os.makedirs(d, exist_ok=True)

    # ──────────────── L0: Index ────────────────

    def load_index(self) -> str:
        """加载全局索引 (L0)。启动时调用一次。"""
        if os.path.exists(self.index_path):
            with open(self.index_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return "# Memory Index\n\n(No entries yet)"

    def _read_all_md(self, directory: str) -> List[Dict]:
        """读取目录下所有 .md 文件的第一个非标题行作为摘要"""
        items = []
        for fpath in sorted(globmod.glob(os.path.join(directory, "*.md"))):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    lines = f.read().strip().split("\n")
                name = os.path.splitext(os.path.basename(fpath))[0]
                # 跳过标题行 (#)、元数据行 (>) 和分隔符 (---)
                summary = ""
                for line in lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or stripped.startswith(">") or stripped.startswith("---"):
                        continue
                    summary = stripped[:80]
                    break
                items.append({"name": name, "summary": summary, "path": fpath})
            except Exception:
                continue
        return items

    def rebuild_index(self):
        """扫描所有文件，重建 INDEX.md"""
        agents = self._read_all_md(self.agents_dir)
        topics = self._read_all_md(self.topics_dir)
        journals = self._read_all_md(self.journal_dir)

        lines = ["# Memory Index", "", f"> Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]

        # Agents
        if agents:
            lines.append("## Active Agents")
            lines.append("")
            lines.append("| Agent | One-liner |")
            lines.append("|-------|-----------|")
            for a in agents:
                rel = os.path.relpath(a["path"], self.memory_dir)
                lines.append(f"| [{a['name']}]({rel}) | {a['summary']} |")
            lines.append("")

        # Topics
        if topics:
            lines.append("## Topics")
            lines.append("")
            lines.append("| Topic | Summary | Ref |")
            lines.append("|-------|---------|-----|")
            for t in topics:
                rel = os.path.relpath(t["path"], self.memory_dir)
                lines.append(f"| {t['name']} | {t['summary']} | [{t['name']}]({rel}) |")
            lines.append("")

        # Journal (最近 7 天)
        if journals:
            lines.append("## Recent Journal")
            lines.append("")
            lines.append("| Date | Summary |")
            lines.append("|------|---------|")
            for j in journals[-7:]:
                lines.append(f"| {j['name']} | {j['summary']} |")
            lines.append("")

        content = "\n".join(lines)
        with open(self.index_path, "w", encoding="utf-8") as f:
            f.write(content)
        return content

    # ──────────────── L1/L2: 渐进检索 (v2: TF-IDF) ────────────────

    def retrieve(self, query: str) -> str:
        """
        渐进式检索：TF-IDF 关键词匹配 → 展开相关 L1 → 按需展开 L2
        返回组装好的上下文字符串，注入到 prompt 中。
        """
        if not query:
            return ""

        # TF-IDF 增强匹配（回退到字符匹配当 TF-IDF 不可用时）
        matched_agents = self._match_files_tfidf(self.agents_dir, query)
        matched_topics = self._match_files_tfidf(self.topics_dir, query)

        if not matched_agents and not matched_topics:
            return ""

        # 加载匹配的 L1 agents（摘要级）
        context_parts = []
        if matched_agents:
            for info in matched_agents[:2]:
                content = self._read_file(info["path"])
                if content:
                    context_parts.append(f"### Agent: {info['name']}\n{content[:1000]}")

        # 加载匹配的 L2 topics（详情级）
        if matched_topics:
            for info in matched_topics[:3]:
                content = self._read_file(info["path"])
                if content:
                    context_parts.append(f"### Topic: {info['name']}\n{content[:2000]}")

        if not context_parts:
            return ""

        return "【相关记忆】\n\n" + "\n\n---\n\n".join(context_parts)

    def _match_files_tfidf(self, directory: str, query: str) -> List[Dict]:
        """
        TF-IDF 增强匹配：对目录内所有 .md 文件建索引，用查询搜索。
        回退到字符匹配当索引构建失败或结果不足时。
        """
        try:
            index = TfidfIndex()
            file_map = {}
            for fpath in globmod.glob(os.path.join(directory, "*.md")):
                try:
                    content = self._read_file(fpath)
                    name = os.path.splitext(os.path.basename(fpath))[0]
                    index.add_document(name, content)
                    file_map[name] = fpath
                except Exception:
                    continue
            if len(index) == 0:
                return []
            index.build()
            results = index.search(query, top_k=5)
            return [
                {"name": doc_id, "path": file_map[doc_id], "score": score}
                for doc_id, score in results
                if doc_id in file_map and score > 0.01
            ]
        except Exception:
            pass

        # 回退：纯字符匹配
        query_tokens = set(query.lower().split())
        query_chars = set(query.lower())
        return self._match_files_keyword(directory, query_tokens, query_chars)

    def _match_files_keyword(self, directory: str, query_tokens: set, query_chars: set) -> List[Dict]:
        """关键词匹配目录中的 MD 文件（回退方案）"""
        results = []
        for fpath in globmod.glob(os.path.join(directory, "*.md")):
            try:
                content = self._read_file(fpath).lower()
                name = os.path.splitext(os.path.basename(fpath))[0]

                name_score = sum(1 for c in query_chars if c in name.lower()) / max(len(query_chars), 1)
                content_words = set(content.split())
                word_hits = len(query_tokens & content_words) if query_tokens else 0
                word_score = word_hits / max(len(query_tokens), 1)
                char_hits = sum(1 for c in query_chars if c in content)
                char_score = char_hits / max(len(query_chars), 1)

                score = name_score * 0.5 + word_score * 0.3 + char_score * 0.2
                if score > 0.05:
                    results.append({"name": name, "path": fpath, "score": score})
            except Exception:
                continue

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    # ──────────────── L3: Journal ────────────────

    def save_journal(self, title: str, body: str, tags: List[str] = None):
        """追加一条日志到当日 journal"""
        today = datetime.now().strftime("%Y-%m-%d")
        journal_path = os.path.join(self.journal_dir, f"{today}.md")

        entry = f"\n## {title}\n"
        if tags:
            entry += f"**Tags**: {', '.join(tags)}\n"
        entry += f"\n{body}\n"

        if os.path.exists(journal_path):
            with open(journal_path, "r", encoding="utf-8") as f:
                existing = f.read()
            with open(journal_path, "w", encoding="utf-8") as f:
                f.write(existing + entry)
        else:
            header = f"# {today}\n"
            with open(journal_path, "w", encoding="utf-8") as f:
                f.write(header + entry)

    def get_recent_journal(self, days: int = 7) -> List[Dict]:
        """获取最近 N 天的日志"""
        results = []
        cutoff = datetime.now() - timedelta(days=days)
        for fpath in globmod.glob(os.path.join(self.journal_dir, "*.md")):
            try:
                name = os.path.splitext(os.path.basename(fpath))[0]
                dt = datetime.strptime(name, "%Y-%m-%d")
                if dt >= cutoff:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    results.append({"date": name, "content": content, "path": fpath})
            except Exception:
                continue
        results.sort(key=lambda x: x["date"], reverse=True)
        return results

    # ──────────────── MEMORY.md: 长期事实 ────────────────

    def load_memory(self) -> str:
        """加载长期记忆"""
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def update_memory(self, section: str, content: str):
        """
        更新 MEMORY.md 中的某个 section。
        如果 section 不存在则追加，存在则替换。
        """
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                existing = f.read()
        else:
            existing = "# Long-term Memory\n\n"

        marker = f"## {section}"
        if marker in existing:
            # 替换已有 section
            parts = existing.split(marker, 1)
            before = parts[0]
            rest = parts[1]
            # 找到下一个 ## 或文件结尾
            next_section = rest.find("\n## ")
            if next_section != -1:
                after = rest[next_section:]
            else:
                after = ""
            new_content = f"{before}{marker}\n\n{content.strip()}\n\n{after}"
        else:
            new_content = existing.rstrip() + f"\n\n{marker}\n\n{content.strip()}\n"

        with open(self.memory_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    # ──────────────── Topic / Agent 注册 ────────────────

    def register_agent(self, name: str, summary: str, status: str = "active", extra: str = ""):
        """创建或更新一个 agent 摘要文件 (L1)"""
        content = f"# {name}\n\n"
        content += f"> Status: {status}\n"
        content += f"> Updated: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        content += f"{summary}\n"
        if extra:
            content += f"\n{extra}\n"

        path = os.path.join(self.agents_dir, f"{name}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.rebuild_index()

    def register_topic(self, name: str, content: str):
        """创建或更新一个 topic 文件 (L2)"""
        header = f"# {name}\n\n"
        header += f"> Created: {datetime.now().strftime('%Y-%m-%d')}\n\n"

        # 如果已有文件，保留旧内容，追加新内容
        path = os.path.join(self.topics_dir, f"{name}.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = f.read()
            # 在文件末尾追加，带分隔
            with open(path, "w", encoding="utf-8") as f:
                f.write(existing.rstrip() + f"\n\n---\n\n## Update {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}\n")
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + content + "\n")
        self.rebuild_index()

    # ──────────────── 状态查询 ────────────────

    def get_status(self) -> Dict:
        """获取记忆系统状态概览"""
        agents = globmod.glob(os.path.join(self.agents_dir, "*.md"))
        topics = globmod.glob(os.path.join(self.topics_dir, "*.md"))
        journals = globmod.glob(os.path.join(self.journal_dir, "*.md"))
        kb = globmod.glob(os.path.join(self.kb_dir, "*.txt"))

        return {
            "index_exists": os.path.exists(self.index_path),
            "memory_exists": os.path.exists(self.memory_path),
            "agents_count": len(agents),
            "topics_count": len(topics),
            "journal_days": len(journals),
            "kb_docs": len(kb),
            "memory_dir": self.memory_dir,
        }

    # ──────────────── 工具方法 ────────────────

    @staticmethod
    def _read_file(path: str) -> str:
        """安全读取文件"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
