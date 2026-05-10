"""
OpenViking Agent Package

基于火山引擎 OpenViking 开发的智能体框架
"""

__version__ = "0.1.0"
__author__ = "Game-Agent Team"

from .agent import Agent
from .memory_manager import MemoryManager

__all__ = ["Agent", "MemoryManager"]
