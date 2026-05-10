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
    
    # 注册 LLM 生成工具
    registry.register(GeneratePromptTool(None))
    registry.register(GenerateSkillTool(None))
    registry.register(AutoCreatePromptAndSkillTool())
    
    return registry


class GeneratePromptTool(Tool):
    """LLM 生成提示词工具"""
    
    def __init__(self, generator):
        super().__init__(
            name="generate_prompt",
            description="根据任务描述生成提示词模板",
            parameters={
                "task_description": {
                    "type": "string",
                    "description": "任务描述，例如：'帮我写一个代码审查助手'"
                },
                "task_type": {
                    "type": "string",
                    "description": "任务类型：conversation/coding/writing/analysis/gaming/teaching/creative",
                    "default": "conversation"
                },
                "context": {
                    "type": "string",
                    "description": "额外上下文信息",
                    "default": ""
                }
            }
        )
        self.generator = generator
    
    def execute(self, task_description: str, task_type: str = "conversation", 
                context: str = "") -> str:
        """生成提示词"""
        try:
            from .llm_auto_generator import PromptGenerator
            
            generator = PromptGenerator()
            result = generator.generate(
                task_type=task_type,
                user_requirement=task_description,
                context_info=context
            )
            
            output = []
            output.append(f"✅ 已生成提示词\n")
            output.append(f"任务类型: {result['hints']}")
            output.append(f"\n请使用以下提示词让 LLM 生成模板:\n")
            output.append(result['generated_prompt'])
            
            return "\n".join(output)
        except Exception as e:
            return f"生成提示词失败: {str(e)}"


class GenerateSkillTool(Tool):
    """LLM 生成技能工具"""
    
    def __init__(self, generator):
        super().__init__(
            name="generate_skill",
            description="根据需求描述生成技能定义和实现代码",
            parameters={
                "skill_description": {
                    "type": "string",
                    "description": "技能需求描述，例如：'帮我创建一个网页搜索工具'"
                },
                "use_case": {
                    "type": "string",
                    "description": "使用场景",
                    "default": ""
                }
            }
        )
        self.generator = generator
    
    def execute(self, skill_description: str, use_case: str = "") -> str:
        """生成技能"""
        try:
            from .llm_auto_generator import SkillGenerator
            
            generator = SkillGenerator()
            result = generator.generate(
                skill_requirement=skill_description,
                use_case=use_case
            )
            
            output = []
            output.append(f"✅ 已生成技能生成请求\n")
            output.append(f"\n请使用以下提示词让 LLM 生成技能定义:\n")
            output.append(result['generated_prompt'])
            
            output.append(f"\n\n💡 生成技能后，你可以:")
            output.append(f"1. 将技能定义保存到 skills/ 目录")
            output.append(f"2. 实现技能处理函数")
            output.append(f"3. 注册到工具系统")
            
            return "\n".join(output)
        except Exception as e:
            return f"生成技能失败: {str(e)}"


class AutoCreatePromptAndSkillTool(Tool):
    """自动创建提示词和技能工具"""
    
    def __init__(self):
        super().__init__(
            name="auto_create",
            description="同时创建提示词和技能，适合复杂任务",
            parameters={
                "task": {
                    "type": "string",
                    "description": "任务描述"
                },
                "generation_type": {
                    "type": "string",
                    "description": "生成类型: prompt/skill/both",
                    "default": "both"
                }
            }
        )
    
    def execute(self, task: str, generation_type: str = "both") -> str:
        """自动创建"""
        try:
            from .llm_auto_generator import create_llm_generation_prompt
            
            result = create_llm_generation_prompt(task, generation_type)
            
            output = []
            output.append(f"✅ 已生成 {'提示词和技能' if generation_type == 'both' else generation_type} 创建提示词\n")
            
            if generation_type in ["prompt", "both"]:
                output.append("\n【提示词生成部分】")
            if generation_type in ["skill", "both"]:
                output.append("\n【技能生成部分】")
            
            output.append(result)
            
            output.append(f"\n\n📝 使用说明:")
            output.append(f"1. 将以上提示词发送给 LLM")
            output.append(f"2. LLM 会返回 JSON/YAML 格式的定义")
            output.append(f"3. 保存到相应文件并注册使用")
            
            return "\n".join(output)
        except Exception as e:
            return f"自动创建失败: {str(e)}"