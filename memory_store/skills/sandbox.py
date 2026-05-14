#!/usr/bin/env python3
"""
Sandbox — 文件 I/O 安全沙箱
限制所有文件操作在允许的目录范围内。
v2: 新增 shell_enabled / max_file_size 配置。
"""

import os


class Sandbox:
    """安全沙箱——限制所有文件 I/O 操作在允许的目录范围内。"""

    def __init__(self, base_path: str):
        self.base_path = os.path.abspath(base_path)
        self.allowed_dirs = [os.path.abspath(base_path)]
        self.readonly = False       # True 时拒绝所有写入操作
        self.shell_enabled = False  # True 时允许 shell_exec 工具
        self.max_file_size = 50000  # 单次读取最大字符数

    def resolve_path(self, user_path: str) -> str:
        """解析用户提供的路径，确保在沙箱范围内。越界则抛出 PermissionError。"""
        if not os.path.isabs(user_path):
            user_path = os.path.join(self.base_path, user_path)
        real = os.path.abspath(user_path)
        for allowed in self.allowed_dirs:
            allowed_abs = os.path.abspath(allowed)
            if real == allowed_abs or real.startswith(allowed_abs + os.sep):
                return real
        raise PermissionError(
            f"访问被拒绝: '{user_path}' 不在沙箱范围内。"
            f" 允许的目录: {', '.join(self.allowed_dirs)}"
        )

    def add_allowed_dir(self, extra_path: str):
        """添加额外允许的目录（可覆盖多个）。"""
        real = os.path.abspath(extra_path)
        if real not in self.allowed_dirs:
            self.allowed_dirs.append(real)

    def __repr__(self) -> str:
        return (
            f"Sandbox(base={self.base_path}, "
            f"readonly={self.readonly}, "
            f"shell={self.shell_enabled}, "
            f"max_file_size={self.max_file_size}, "
            f"allowed_dirs={len(self.allowed_dirs)})"
        )
