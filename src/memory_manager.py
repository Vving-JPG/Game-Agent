"""
记忆管理模块

封装 OpenViking 的文件系统操作，提供记忆存储、检索、更新接口
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class Memory:
    """记忆条目"""
    
    def __init__(self, content: str, category: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.category = category
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        import hashlib
        data = f"{self.content}{self.created_at}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """从字典创建"""
        memory = cls(data["content"], data["category"], data.get("metadata", {}))
        memory.id = data["id"]
        memory.created_at = data["created_at"]
        return memory


class MemoryManager:
    """
    记忆管理器
    
    基于文件系统的记忆存储和管理，支持分类存储和语义检索
    """
    
    def __init__(self, workspace_path: str):
        """
        初始化记忆管理器
        
        Args:
            workspace_path: OpenViking 工作空间路径
        """
        self.workspace = Path(workspace_path)
        self.memories_dir = self.workspace / "memories"
        
        # 创建记忆目录结构
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保目录结构存在"""
        categories = ["conversations", "facts", "preferences", "general"]
        for category in categories:
            (self.memories_dir / category).mkdir(parents=True, exist_ok=True)
    
    def store(self, content: str, category: str = "general", 
              metadata: Dict[str, Any] = None) -> Memory:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            category: 记忆类别 (conversations/facts/preferences/general)
            metadata: 附加元数据
            
        Returns:
            Memory: 创建的记忆对象
        """
        memory = Memory(content, category, metadata)
        
        # 保存到文件
        category_dir = self.memories_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = category_dir / f"{memory.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)
        
        return memory
    
    def retrieve(self, query: str, category: Optional[str] = None, 
                 limit: int = 5) -> List[Memory]:
        """
        检索记忆
        
        Args:
            query: 查询关键词
            category: 指定类别检索，None则检索所有类别
            limit: 返回结果数量限制
            
        Returns:
            List[Memory]: 匹配的记忆列表
        """
        memories = []
        
        # 确定搜索目录
        if category:
            search_dirs = [self.memories_dir / category]
        else:
            search_dirs = [d for d in self.memories_dir.iterdir() if d.is_dir()]
        
        # 遍历所有记忆文件
        for dir_path in search_dirs:
            if not dir_path.exists():
                continue
                
            for file_path in dir_path.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        memory = Memory.from_dict(data)
                        
                        # 简单关键词匹配（实际项目中可使用语义检索）
                        if query.lower() in memory.content.lower():
                            memories.append(memory)
                except Exception as e:
                    print(f"读取记忆文件失败 {file_path}: {e}")
        
        # 按时间排序并限制数量
        memories.sort(key=lambda x: x.created_at, reverse=True)
        return memories[:limit]
    
    def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """
        根据ID获取记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            Optional[Memory]: 记忆对象，未找到返回None
        """
        for category_dir in self.memories_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            file_path = category_dir / f"{memory_id}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return Memory.from_dict(data)
                except Exception as e:
                    print(f"读取记忆文件失败 {file_path}: {e}")
        
        return None
    
    def delete(self, memory_id: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            bool: 是否成功删除
        """
        for category_dir in self.memories_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            file_path = category_dir / f"{memory_id}.json"
            if file_path.exists():
                try:
                    file_path.unlink()
                    return True
                except Exception as e:
                    print(f"删除记忆文件失败 {file_path}: {e}")
                    return False
        
        return False
    
    def list_categories(self) -> List[str]:
        """
        列出所有记忆类别
        
        Returns:
            List[str]: 类别名称列表
        """
        categories = []
        for item in self.memories_dir.iterdir():
            if item.is_dir():
                categories.append(item.name)
        return categories
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取记忆统计信息
        
        Returns:
            Dict[str, int]: 各类别记忆数量统计
        """
        stats = {}
        for category in self.list_categories():
            category_dir = self.memories_dir / category
            count = len(list(category_dir.glob("*.json")))
            stats[category] = count
        return stats
