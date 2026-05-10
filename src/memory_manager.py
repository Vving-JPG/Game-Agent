"""
记忆管理模块

封装 OpenViking 的文件系统操作，提供记忆存储、检索、更新接口
支持语义检索和自动记忆提取
"""

import os
import json
import hashlib
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
        self.score = 0.0
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        data = f"{self.content}{self.created_at}"
        return hashlib.md5(data.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "score": self.score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """从字典创建"""
        memory = cls(data["content"], data["category"], data.get("metadata", {}))
        memory.id = data["id"]
        memory.created_at = data["created_at"]
        memory.score = data.get("score", 0.0)
        return memory


class OpenVikingClient:
    """
    OpenViking 客户端封装
    
    提供语义检索和资源管理功能
    """
    
    def __init__(self, workspace_path: str = None, config_path: str = None):
        """
        初始化 OpenViking 客户端
        
        Args:
            workspace_path: 工作空间路径
            config_path: 配置文件路径
        """
        self.workspace_path = workspace_path or "./openviking_workspace"
        self.config_path = config_path
        self._client = None
        self._initialized = False
    
    def _get_client(self):
        """获取或创建 OpenViking 客户端"""
        if self._client is None:
            try:
                import openviking as ov
                self._client = ov.OpenViking(path=self.workspace_path)
                self._client.initialize()
                self._initialized = True
            except ImportError:
                print("OpenViking 未安装，使用基础文件存储模式")
                self._client = None
            except Exception as e:
                print(f"OpenViking 初始化失败: {e}")
                self._client = None
        return self._client
    
    def is_available(self) -> bool:
        """检查 OpenViking 是否可用"""
        return self._get_client() is not None
    
    def semantic_search(self, query: str, uri: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        语义检索
        
        Args:
            query: 查询文本
            uri: 搜索范围 URI
            limit: 返回结果数量
            
        Returns:
            List[Dict]: 检索结果列表
        """
        client = self._get_client()
        if client is None:
            return []
        
        try:
            target_uri = uri or f"viking://memories/"
            results = client.find(query, target_uri=target_uri)
            
            memories = []
            if hasattr(results, 'resources'):
                for r in results.resources[:limit]:
                    memories.append({
                        "uri": r.uri,
                        "content": getattr(r, 'content', ''),
                        "score": getattr(r, 'score', 0.0)
                    })
            return memories
        except Exception as e:
            print(f"语义检索失败: {e}")
            return []
    
    def add_memory_resource(self, content: str, category: str, memory_id: str) -> bool:
        """
        添加记忆资源到 OpenViking
        
        Args:
            content: 记忆内容
            category: 记忆类别
            memory_id: 记忆ID
            
        Returns:
            bool: 是否成功
        """
        client = self._get_client()
        if client is None:
            return False
        
        try:
            memory_path = Path(self.workspace_path) / "memories" / category / f"{memory_id}.txt"
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(memory_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            client.add_resource(path=str(memory_path))
            return True
        except Exception as e:
            print(f"添加记忆资源失败: {e}")
            return False
    
    def wait_processed(self, timeout: int = 30):
        """等待语义处理完成"""
        client = self._get_client()
        if client is None:
            return
        
        try:
            client.wait_processed(timeout=timeout)
        except Exception:
            pass
    
    def close(self):
        """关闭客户端"""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


class MemoryManager:
    """
    增强版记忆管理器
    
    支持文件存储和 OpenViking 语义检索
    实现分层记忆结构 (L0/L1/L2)
    """
    
    MEMORY_LAYERS = {
        "L0": {"name": "工作记忆", "ttl": 3600, "description": "当前对话上下文"},
        "L1": {"name": "短期记忆", "ttl": 86400, "description": "最近对话历史"},
        "L2": {"name": "长期记忆", "ttl": -1, "description": "持久化记忆"}
    }
    
    def __init__(self, workspace_path: str, use_openviking: bool = True):
        """
        初始化记忆管理器
        
        Args:
            workspace_path: OpenViking 工作空间路径
            use_openviking: 是否启用 OpenViking 语义检索
        """
        self.workspace = Path(workspace_path)
        self.memories_dir = self.workspace / "memories"
        
        self._ensure_directories()
        
        self.ov_client = None
        if use_openviking:
            self.ov_client = OpenVikingClient(workspace_path)
    
    def _ensure_directories(self):
        """确保目录结构存在"""
        categories = ["conversations", "facts", "preferences", "general", "entities"]
        for category in categories:
            (self.memories_dir / category).mkdir(parents=True, exist_ok=True)
    
    def store(self, content: str, category: str = "general", 
              metadata: Dict[str, Any] = None, layer: str = "L2") -> Memory:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            category: 记忆类别 (conversations/facts/preferences/general/entities)
            metadata: 附加元数据
            layer: 记忆层级 (L0/L1/L2)
            
        Returns:
            Memory: 创建的记忆对象
        """
        memory = Memory(content, category, metadata)
        
        if metadata is None:
            metadata = {}
        metadata["layer"] = layer
        memory.metadata = metadata
        
        category_dir = self.memories_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = category_dir / f"{memory.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(memory.to_dict(), f, ensure_ascii=False, indent=2)
        
        if self.ov_client and self.ov_client.is_available():
            self.ov_client.add_memory_resource(content, category, memory.id)
        
        return memory
    
    def retrieve(self, query: str, category: Optional[str] = None, 
                 limit: int = 5, use_semantic: bool = True) -> List[Memory]:
        """
        检索记忆
        
        Args:
            query: 查询关键词或语义查询
            category: 指定类别检索，None则检索所有类别
            limit: 返回结果数量限制
            use_semantic: 是否使用语义检索
            
        Returns:
            List[Memory]: 匹配的记忆列表
        """
        if use_semantic and self.ov_client and self.ov_client.is_available():
            return self._semantic_retrieve(query, category, limit)
        else:
            return self._keyword_retrieve(query, category, limit)
    
    def _semantic_retrieve(self, query: str, category: Optional[str], 
                           limit: int) -> List[Memory]:
        """语义检索"""
        uri = f"viking://memories/{category}/" if category else "viking://memories/"
        results = self.ov_client.semantic_search(query, uri=uri, limit=limit)
        
        memories = []
        for r in results:
            memory_id = Path(r.get("uri", "")).stem
            memory = self.get_by_id(memory_id)
            if memory:
                memory.score = r.get("score", 0.0)
                memories.append(memory)
        
        return memories
    
    def _keyword_retrieve(self, query: str, category: Optional[str], 
                          limit: int) -> List[Memory]:
        """关键词检索"""
        memories = []
        
        if category:
            search_dirs = [self.memories_dir / category]
        else:
            search_dirs = [d for d in self.memories_dir.iterdir() if d.is_dir()]
        
        for dir_path in search_dirs:
            if not dir_path.exists():
                continue
                
            for file_path in dir_path.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        memory = Memory.from_dict(data)
                        
                        if query.lower() in memory.content.lower():
                            memories.append(memory)
                except Exception as e:
                    print(f"读取记忆文件失败 {file_path}: {e}")
        
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
    
    def extract_and_store(self, text: str, source: str = "conversation") -> List[Memory]:
        """
        从文本中自动提取并存储重要信息
        
        Args:
            text: 输入文本
            source: 来源类型
            
        Returns:
            List[Memory]: 提取的记忆列表
        """
        extracted = []
        
        entity_patterns = [
            (r"我叫(\w+)", "preferences", "用户姓名"),
            (r"我的名字是(\w+)", "preferences", "用户姓名"),
            (r"我喜欢(\S+)", "preferences", "用户偏好"),
            (r"我不喜欢(\S+)", "preferences", "用户偏好"),
            (r"记住[：:]?\s*(.+)", "facts", "用户要求记住"),
            (r"别忘了[：:]?\s*(.+)", "facts", "用户要求记住"),
        ]
        
        import re
        for pattern, category, desc in entity_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                content = match if isinstance(match, str) else match[0]
                if content and len(content) > 1:
                    memory = self.store(
                        content=content,
                        category=category,
                        metadata={"source": source, "type": desc}
                    )
                    extracted.append(memory)
        
        return extracted
    
    def compress_conversation(self, messages: List[Dict[str, str]]) -> Memory:
        """
        压缩对话历史为摘要记忆
        
        Args:
            messages: 对话消息列表
            
        Returns:
            Memory: 压缩后的记忆
        """
        if not messages:
            return None
        
        key_points = []
        for msg in messages[-10:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if len(content) > 50:
                key_points.append(f"[{role}]: {content[:100]}...")
            else:
                key_points.append(f"[{role}]: {content}")
        
        summary = "\n".join(key_points)
        
        return self.store(
            content=summary,
            category="conversations",
            metadata={"type": "compressed", "message_count": len(messages)}
        )
    
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
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            "categories": {},
            "total": 0,
            "openviking_enabled": self.ov_client is not None and self.ov_client.is_available()
        }
        
        for category in self.list_categories():
            category_dir = self.memories_dir / category
            count = len(list(category_dir.glob("*.json")))
            stats["categories"][category] = count
            stats["total"] += count
        
        return stats
    
    def close(self):
        """关闭资源"""
        if self.ov_client:
            self.ov_client.close()
