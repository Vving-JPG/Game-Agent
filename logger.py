#!/usr/bin/env python3
"""
Game-Agent 日志系统 — 控制台 + 文件双通道，带轮转。
错误信息统一走 logger，不再裸 print 到 stderr。
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOGGER = None


def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/agent.log",
    max_bytes: int = 1_048_576,
    backup_count: int = 3,
) -> logging.Logger:
    """初始化日志系统，幂等调用。"""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    _LOGGER = logging.getLogger("game_agent")
    _LOGGER.setLevel(getattr(logging, level.upper(), logging.DEBUG))
    _LOGGER.propagate = False

    # 控制台 —— 只显示 WARNING 及以上
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    _LOGGER.addHandler(console)

    # 文件 —— 记录 DEBUG 及以上，带轮转
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)-5s] %(name)s: %(message)s")
        )
        _LOGGER.addHandler(fh)

    return _LOGGER


def get_logger() -> logging.Logger:
    """获取日志器，未初始化时自动使用默认配置。"""
    global _LOGGER
    if _LOGGER is None:
        return setup_logging()
    return _LOGGER
