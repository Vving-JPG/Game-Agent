"""
工具模块

定义智能体可使用的工具和执行逻辑
"""

import json
from typing import Dict, Any, Callable, List
from datetime import datetime


class Tool:
    """工具基类"""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    def execute(self, **kwargs) -> Any:
        """执行工具"""
        raise NotImplementedError
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class GetCurrentTimeTool(Tool):
    """获取当前时间工具"""
    
    def __init__(self):
        super().__init__(
            name="get_current_time",
            description="获取当前日期和时间",
            parameters={
                "format": {
                    "type": "string",
                    "description": "时间格式，如 '%Y-%m-%d %H:%M:%S'",
                    "default": "%Y-%m-%d %H:%M:%S"
                }
            }
        )
    
    def execute(self, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        return datetime.now().strftime(format)


class CalculatorTool(Tool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行基础数学计算",
            parameters={
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '1 + 2 * 3'"
                }
            }
        )
    
    def execute(self, expression: str) -> str:
        try:
            # 安全计算：只允许基本运算符
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                return "错误：表达式包含非法字符"
            
            result = eval(expression)
            return f"{expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"


class MemoryStoreTool(Tool):
    """记忆存储工具"""
    
    def __init__(self, memory_manager):
        super().__init__(
            name="store_memory",
            description="存储重要信息到长期记忆",
            parameters={
                "content": {
                    "type": "string",
                    "description": "要存储的内容"
                },
                "category": {
                    "type": "string",
                    "description": "记忆类别: facts(事实)/preferences(偏好)/general(一般)",
                    "default": "general"
                }
            }
        )
        self.memory_manager = memory_manager
    
    def execute(self, content: str, category: str = "general") -> str:
        try:
            memory = self.memory_manager.store(content, category)
            return f"记忆已存储 [ID: {memory.id}]"
        except Exception as e:
            return f"存储失败: {str(e)}"


class MemoryRetrieveTool(Tool):
    """记忆检索工具"""
    
    def __init__(self, memory_manager):
        super().__init__(
            name="retrieve_memory",
            description="从长期记忆中检索相关信息",
            parameters={
                "query": {
                    "type": "string",
                    "description": "查询关键词"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量",
                    "default": 3
                }
            }
        )
        self.memory_manager = memory_manager
    
    def execute(self, query: str, limit: int = 3) -> str:
        try:
            memories = self.memory_manager.retrieve(query, limit=limit)
            if not memories:
                return "未找到相关记忆"
            
            results = []
            for mem in memories:
                results.append(f"- [{mem.category}] {mem.content}")
            
            return "找到以下记忆:\n" + "\n".join(results)
        except Exception as e:
            return f"检索失败: {str(e)}"


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Tool:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return [tool.to_dict() for tool in self._tools.values()]
    
    def execute(self, tool_name: str, **kwargs) -> Any:
        """执行工具"""
        tool = self.get(tool_name)
        if not tool:
            return f"未知工具: {tool_name}"
        return tool.execute(**kwargs)


def create_default_tools(memory_manager=None) -> ToolRegistry:
    """
    创建默认工具集
    
    Args:
        memory_manager: 记忆管理器实例（可选）
        
    Returns:
        ToolRegistry: 工具注册表
    """
    registry = ToolRegistry()
    
    # 注册基础工具
    registry.register(GetCurrentTimeTool())
    registry.register(CalculatorTool())
    
    # 注册记忆工具（如果提供了 memory_manager）
    if memory_manager:
        registry.register(MemoryStoreTool(memory_manager))
        registry.register(MemoryRetrieveTool(memory_manager))
    
    return registry
