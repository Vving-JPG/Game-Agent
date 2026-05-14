#!/usr/bin/env python3
"""
文件操作工具集 — OpenAI 兼容的工具定义 + 沙箱保护的执行器。
v2: 扩展了 grep / delete / move / shell 工具。
"""

import json
import os
import re
import subprocess
from datetime import datetime
from typing import List, Dict

from .sandbox import Sandbox


class FileToolSet:
    """文件操作工具集——定义 + 沙箱保护的执行器"""

    def __init__(self, sandbox: Sandbox):
        self.sandbox = sandbox

    # ──────────────── 工具定义 ────────────────

    def get_definitions(self) -> List[Dict]:
        """返回 OpenAI 兼容的 tool 定义列表。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取指定文本文件的内容。用于查看代码、配置、笔记等文本文件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "文件路径（相对沙箱根目录或绝对路径）",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "将内容写入文件。文件不存在则创建。若文件已存在且 overwrite 为 false 则发出警告。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "要写入的内容"},
                            "overwrite": {
                                "type": "boolean",
                                "description": "是否覆盖已有文件（默认 false）",
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "列出指定目录下的文件和子目录，显示文件大小和最后修改时间。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "目录路径"}
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_working_directory",
                    "description": "返回当前沙箱工作目录的根路径。",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "append_file",
                    "description": "追加文本内容到已有文件末尾。如果文件不存在则报错。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "要追加的内容"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            # ── v2 新增工具 ──
            {
                "type": "function",
                "function": {
                    "name": "grep_files",
                    "description": "在指定目录的文本文件中搜索正则表达式。返回匹配的行及其文件来源。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "搜索的目录路径（递归搜索子目录）",
                            },
                            "pattern": {
                                "type": "string",
                                "description": "正则表达式搜索模式",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "最大返回结果数（默认 20）",
                            },
                        },
                        "required": ["path", "pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "删除指定文件。操作不可逆，请谨慎使用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "要删除的文件路径"}
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "move_file",
                    "description": "移动或重命名文件/目录。源和目标必须在沙箱范围内。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "源文件/目录路径",
                            },
                            "destination": {
                                "type": "string",
                                "description": "目标路径",
                            },
                        },
                        "required": ["source", "destination"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "shell_exec",
                    "description": (
                        "在沙箱根目录下执行一个 shell 命令。"
                        "有超时保护（默认 30 秒），输出限制 10000 字符。"
                        "仅当沙箱 shell_enabled=True 时可用；默认禁用以确保安全。"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的 shell 命令",
                            },
                            "timeout_secs": {
                                "type": "integer",
                                "description": "超时秒数（默认 30，最大 120）",
                            },
                        },
                        "required": ["command"],
                    },
                },
            },
        ]

    # ──────────────── 工具执行器 ────────────────

    def execute(self, tool_call) -> str:
        """调度单个 tool call，返回执行结果字符串。"""
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON arguments for {name}: {e}"
        try:
            if name == "read_file":
                return self._read(args["path"])
            elif name == "write_file":
                return self._write(
                    args["path"], args["content"], args.get("overwrite", False)
                )
            elif name == "list_directory":
                return self._list(args["path"])
            elif name == "get_working_directory":
                return self._get_cwd()
            elif name == "append_file":
                return self._append(args["path"], args["content"])
            elif name == "grep_files":
                return self._grep(
                    args["path"], args["pattern"], args.get("max_results", 20)
                )
            elif name == "delete_file":
                return self._delete(args["path"])
            elif name == "move_file":
                return self._move(args["source"], args["destination"])
            elif name == "shell_exec":
                return self._shell(
                    args["command"], args.get("timeout_secs", 30)
                )
            else:
                return f"Error: Unknown tool '{name}'"
        except PermissionError as e:
            return f"沙箱安全拒绝: {e}"
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    # ──────────────── 基础工具实现 ────────────────

    def _read(self, path: str) -> str:
        """读取文本文件内容（沙箱保护）。"""
        resolved = self.sandbox.resolve_path(path)
        if not os.path.isfile(resolved):
            return f"Error: File not found: {resolved}"
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        max_size = self.sandbox.max_file_size
        if len(content) > max_size:
            content = (
                content[:max_size]
                + f"\n\n... [文件过长，已截断至 {max_size} 字符]"
            )
        return content

    def _write(self, path: str, content: str, overwrite: bool = False) -> str:
        """写入文件（沙箱保护 + 只读检查 + 防意外覆盖）。"""
        if self.sandbox.readonly:
            return "Error: 系统处于只读模式，写入已禁用。"
        resolved = self.sandbox.resolve_path(path)
        if os.path.exists(resolved) and not overwrite:
            return (
                f"Warning: 文件已存在 '{resolved}'。"
                f" 如需覆盖请设置 overwrite=true，或使用 append_file 追加。"
            )
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: 已将 {len(content)} 字符写入 '{resolved}'"

    def _list(self, path: str) -> str:
        """列出目录内容（沙箱保护）。"""
        resolved = self.sandbox.resolve_path(path)
        if not os.path.isdir(resolved):
            return f"Error: Directory not found: {resolved}"
        entries = []
        for item in sorted(os.listdir(resolved)):
            full = os.path.join(resolved, item)
            if os.path.isfile(full):
                size = os.path.getsize(full)
                mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime(
                    "%Y-%m-%d %H:%M"
                )
                entries.append(f"  [FILE] {item}  ({size:,} bytes, {mtime})")
            elif os.path.isdir(full):
                entries.append(f"  [DIR]  {item}/")
        if not entries:
            return f"(empty directory)"
        return f"Contents of '{resolved}':\n" + "\n".join(entries)

    def _get_cwd(self) -> str:
        """返回当前沙箱根目录。"""
        return f"Working directory: {self.sandbox.base_path}"

    def _append(self, path: str, content: str) -> str:
        """追加文本内容到已有文件末尾。"""
        if self.sandbox.readonly:
            return "Error: 系统处于只读模式，写入已禁用。"
        resolved = self.sandbox.resolve_path(path)
        if not os.path.isfile(resolved):
            return f"Error: File not found (append 仅支持已有文件): {resolved}"
        with open(resolved, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Success: 已将 {len(content)} 字符追加到 '{resolved}'"

    # ──────────────── v2 新增工具实现 ────────────────

    def _grep(self, path: str, pattern: str, max_results: int = 20) -> str:
        """在目录中递归搜索正则表达式（沙箱保护）。"""
        resolved = self.sandbox.resolve_path(path)
        if not os.path.isdir(resolved):
            return f"Error: Directory not found: {resolved}"

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return f"Error: 无效的正则表达式 '{pattern}': {e}"

        results = []
        # 支持的文件扩展名
        text_exts = {".txt", ".md", ".py", ".json", ".env", ".cfg",
                     ".toml", ".yaml", ".yml", ".xml", ".html", ".css",
                     ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp",
                     ".h", ".hpp", ".csv", ".log", ".ini", ".conf", ".sh",
                     ".bat", ".ps1", ".sql", ".r", ".rb", ".php", ".swift",
                     ".kt", ".scala", ".lua", ".vim", ".tex", ".rst"}

        for root, dirs, files in os.walk(resolved):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if len(results) >= max_results:
                    break
                ext = os.path.splitext(fname)[1].lower()
                if ext not in text_exts and fname not in (
                    "Makefile", "Dockerfile", "LICENSE", "README"
                ):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for lineno, line in enumerate(f, 1):
                            if len(results) >= max_results:
                                break
                            if regex.search(line):
                                rel = os.path.relpath(fpath, resolved)
                                results.append(
                                    f"{rel}:{lineno}: {line.rstrip()[:200]}"
                                )
                except Exception:
                    continue

        if not results:
            return f"在 '{resolved}' 中未找到匹配 '{pattern}' 的结果。"
        return (
            f"在 '{resolved}' 中找到 {len(results)} 处匹配：\n"
            + "\n".join(results)
        )

    def _delete(self, path: str) -> str:
        """删除文件（沙箱保护 + 只读检查）。"""
        if self.sandbox.readonly:
            return "Error: 系统处于只读模式，删除已禁用。"
        resolved = self.sandbox.resolve_path(path)
        if not os.path.exists(resolved):
            return f"Error: 文件/目录不存在: {resolved}"
        try:
            if os.path.isfile(resolved):
                os.remove(resolved)
                return f"Success: 已删除文件 '{resolved}'"
            elif os.path.isdir(resolved):
                import shutil
                shutil.rmtree(resolved)
                return f"Success: 已删除目录 '{resolved}'"
            else:
                return f"Error: 不是常规文件或目录: {resolved}"
        except Exception as e:
            return f"Error: 删除失败 '{resolved}': {e}"

    def _move(self, source: str, destination: str) -> str:
        """移动/重命名文件或目录（沙箱保护 + 只读检查）。"""
        if self.sandbox.readonly:
            return "Error: 系统处于只读模式，移动已禁用。"
        src = self.sandbox.resolve_path(source)
        dst = self.sandbox.resolve_path(destination)
        if not os.path.exists(src):
            return f"Error: 源文件/目录不存在: {src}"
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            import shutil
            shutil.move(src, dst)
            return f"Success: 已将 '{src}' 移动到 '{dst}'"
        except Exception as e:
            return f"Error: 移动失败 '{src}' -> '{dst}': {e}"

    def _shell(self, command: str, timeout_secs: int = 30) -> str:
        """在沙箱根目录下执行 shell 命令（需手动启用）。"""
        if not self.sandbox.shell_enabled:
            return (
                "Error: Shell 执行未启用。"
                " 请在沙箱设置中开启 shell_enabled=True，或使用其他工具完成操作。"
            )
        timeout = min(max(timeout_secs, 5), 120)  # 限制 5-120 秒
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.sandbox.base_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                env={},  # 清空环境变量，隔离执行
            )
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            if len(output) > 10000:
                output = output[:10000] + "\n\n... [输出过长，已截断至 10000 字符]"
            return (
                f"Shell 命令: {command}\n"
                f"退出码: {result.returncode}\n"
                f"输出:\n{output if output else '(无输出)'}"
            )
        except subprocess.TimeoutExpired:
            return f"Error: Shell 命令超时 ({timeout}秒): {command}"
        except Exception as e:
            return f"Error: Shell 执行失败: {e}"
