"""
渐进式披露提示词管理模块

核心思想：
1. 分层展示信息：核心层 -> 上下文层 -> 扩展层
2. 按需加载：根据对话复杂度动态调整信息披露程度
3. Token 优化：控制提示词长度，避免信息过载
"""

import json
from typing import Dict, List, Any, Optional
from enum import Enum


class DisclosureLevel(Enum):
    """披露层级"""
    CORE = 0        # 核心层：最基本的角色和能力
    CONTEXT = 1     # 上下文层：当前对话相关信息
    EXTENDED = 2    # 扩展层：可选的高级功能
    DETAILED = 3    # 详细层：完整的工具说明和元数据


class TokenBudget:
    """Token 预算管理器"""
    
    DEFAULT_BUDGET = 4000
    CORE_BUDGET = 500
    CONTEXT_BUDGET = 1500
    EXTENDED_BUDGET = 2000
    
    def __init__(self, total_budget: int = DEFAULT_BUDGET):
        self.total_budget = total_budget
        self.used_tokens = 0
    
    def allocate(self, level: DisclosureLevel, content_length: int) -> bool:
        """
        分配 token 预算
        
        Args:
            level: 披露层级
            content_length: 内容长度（字符数）
            
        Returns:
            bool: 是否成功分配
        """
        estimated_tokens = content_length // 4
        level_budgets = {
            DisclosureLevel.CORE: self.CORE_BUDGET,
            DisclosureLevel.CONTEXT: self.CONTEXT_BUDGET,
            DisclosureLevel.EXTENDED: self.EXTENDED_BUDGET,
            DisclosureLevel.DETAILED: self.total_budget
        }
        
        budget = level_budgets.get(level, self.total_budget)
        remaining = self.total_budget - self.used_tokens
        
        if estimated_tokens <= remaining and estimated_tokens <= budget:
            self.used_tokens += estimated_tokens
            return True
        return False
    
    def can_include(self, content_length: int, min_required: int = 100) -> bool:
        """检查是否还能包含更多内容"""
        estimated_tokens = max(content_length // 4, min_required // 4)
        return (self.total_budget - self.used_tokens) >= estimated_tokens
    
    def get_remaining(self) -> int:
        """获取剩余 token 预算"""
        return self.total_budget - self.used_tokens
    
    def reset(self):
        """重置预算"""
        self.used_tokens = 0


class ProgressivePromptBuilder:
    """
    渐进式披露提示词构建器
    
    根据对话上下文和 Token 预算，动态构建最优的提示词
    """
    
    def __init__(self, base_system_prompt: str = ""):
        self.base_system_prompt = base_system_prompt
        self.token_budget = TokenBudget()
        
        self._layers = {
            DisclosureLevel.CORE: {
                "name": "核心角色",
                "priority": 0,
                "always_include": True
            },
            DisclosureLevel.CONTEXT: {
                "name": "上下文信息",
                "priority": 1,
                "always_include": True
            },
            DisclosureLevel.EXTENDED: {
                "name": "扩展功能",
                "priority": 2,
                "always_include": False
            },
            DisclosureLevel.DETAILED: {
                "name": "详细信息",
                "priority": 3,
                "always_include": False
            }
        }
    
    def build(self, 
              context: Dict[str, Any],
              disclosure_level: DisclosureLevel = DisclosureLevel.CONTEXT,
              max_tokens: int = 4000) -> str:
        """
        构建渐进式披露提示词
        
        Args:
            context: 上下文信息字典
            disclosure_level: 披露层级
            max_tokens: 最大 token 数
            
        Returns:
            str: 构建好的提示词
        """
        self.token_budget = TokenBudget(max_tokens)
        
        parts = []
        
        parts.append(self._build_core_layer(context))
        
        if self.token_budget.can_include(100):
            parts.append(self._build_context_layer(context))
        
        if disclosure_level.value >= DisclosureLevel.EXTENDED.value:
            if self.token_budget.can_include(200):
                parts.append(self._build_extended_layer(context))
        
        if disclosure_level.value >= DisclosureLevel.DETAILED.value:
            if self.token_budget.can_include(500):
                parts.append(self._build_detailed_layer(context))
        
        return "\n\n".join([p for p in parts if p])
    
    def _build_core_layer(self, context: Dict[str, Any]) -> str:
        """构建核心层 - 始终包含的基本角色定义"""
        role = context.get("role", "智能助手")
        personality = context.get("personality", "专业、友好")
        
        core = f"""你是一个{role}。
性格特点：{personality}

核心能力：
- 理解和回答用户问题
- 使用可用工具完成任务
- 记住重要的用户偏好"""
        
        return core
    
    def _build_context_layer(self, context: Dict[str, Any]) -> str:
        """构建上下文层 - 当前对话相关信息"""
        parts = []
        
        if context.get("entities"):
            entities_str = self._format_entities(context["entities"])
            if entities_str and self.token_budget.can_include(len(entities_str)):
                parts.append(f"已知信息：\n{entities_str}")
        
        if context.get("recent_memories"):
            memories = self._format_memories(context["recent_memories"])
            if memories and self.token_budget.can_include(len(memories)):
                parts.append(f"相关记忆：\n{memories}")
        
        if context.get("conversation_stage"):
            stage = context["conversation_stage"]
            if stage == "initial":
                parts.append("当前是初次对话阶段，简洁回应即可。")
            elif stage == "ongoing":
                parts.append("继续之前的对话，保持上下文连贯。")
            elif stage == "complex":
                parts.append("这是一个复杂任务，仔细分析后回答。")
        
        return "\n".join(parts) if parts else ""
    
    def _build_extended_layer(self, context: Dict[str, Any]) -> str:
        """构建扩展层 - 可选的高级功能说明"""
        parts = []
        
        if context.get("available_tools"):
            tools_summary = self._summarize_tools(context["available_tools"])
            if tools_summary and self.token_budget.can_include(len(tools_summary)):
                parts.append(f"可用工具：\n{tools_summary}")
        
        if context.get("user_level"):
            level = context["user_level"]
            if level == "advanced":
                parts.append("用户是高级用户，可以使用专业术语。")
            elif level == "beginner":
                parts.append("用户是初学者，请用通俗易懂的语言解释。")
        
        return "\n".join(parts) if parts else ""
    
    def _build_detailed_layer(self, context: Dict[str, Any]) -> str:
        """构建详细层 - 完整的工具说明和元数据"""
        parts = []
        
        if context.get("full_tools_description"):
            tools = context["full_tools_description"]
            if tools and self.token_budget.can_include(len(tools)):
                parts.append(f"完整工具说明：\n{tools}")
        
        if context.get("reminders"):
            reminders = "\n".join([f"- {r}" for r in context["reminders"]])
            if reminders and self.token_budget.can_include(len(reminders)):
                parts.append(f"提醒：\n{reminders}")
        
        if context.get("constraints"):
            constraints = "\n".join([f"- {c}" for c in context["constraints"]])
            if constraints and self.token_budget.can_include(len(constraints)):
                parts.append(f"约束条件：\n{constraints}")
        
        return "\n".join(parts) if parts else ""
    
    def _format_entities(self, entities: Dict[str, Any]) -> str:
        """格式化实体信息"""
        if not entities:
            return ""
        
        lines = []
        for key, value in entities.items():
            if isinstance(value, list):
                lines.append(f"- {key}: {', '.join(str(v) for v in value)}")
            else:
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines[:5])
    
    def _format_memories(self, memories: List[Any]) -> str:
        """格式化记忆"""
        if not memories:
            return ""
        
        lines = []
        for mem in memories[:3]:
            content = getattr(mem, 'content', str(mem))
            category = getattr(mem, 'category', 'general')
            if len(content) > 100:
                content = content[:100] + "..."
            lines.append(f"- [{category}] {content}")
        
        return "\n".join(lines)
    
    def _summarize_tools(self, tools: List[Dict[str, Any]]) -> str:
        """总结工具列表"""
        if not tools:
            return ""
        
        summaries = []
        for tool in tools[:5]:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "")[:50]
            summaries.append(f"- {name}: {desc}...")
        
        return "\n".join(summaries)
    
    def build_minimal(self, role: str = "助手") -> str:
        """
        构建最小化提示词（用于简单对话）
        
        Args:
            role: 角色名称
            
        Returns:
            str: 最小化提示词
        """
        return f"你是{role}，简洁回答。"
    
    def build_adaptive(self, context: Dict[str, Any]) -> str:
        """
        自适应构建提示词
        
        根据对话复杂度自动选择披露层级
        
        Args:
            context: 上下文信息
            
        Returns:
            str: 自适应提示词
        """
        complexity = self._assess_complexity(context)
        
        if complexity == "simple":
            return self.build_minimal(context.get("role", "助手"))
        elif complexity == "moderate":
            return self.build(context, DisclosureLevel.CONTEXT, 3000)
        elif complexity == "complex":
            return self.build(context, DisclosureLevel.EXTENDED, 4000)
        else:
            return self.build(context, DisclosureLevel.DETAILED, 5000)
    
    def _assess_complexity(self, context: Dict[str, Any]) -> str:
        """评估对话复杂度"""
        score = 0
        
        if context.get("entities"):
            score += len(context["entities"]) * 0.5
        
        if context.get("recent_memories"):
            score += len(context["recent_memories"]) * 0.3
        
        if context.get("conversation_length", 0) > 10:
            score += 2
        
        if context.get("requires_tools", False):
            score += 3
        
        if context.get("task_type") in ["coding", "analysis", "research"]:
            score += 2
        
        if score < 2:
            return "simple"
        elif score < 5:
            return "moderate"
        elif score < 8:
            return "complex"
        else:
            return "very_complex"


class DisclosureController:
    """
    披露控制器
    
    管理提示词的渐进式披露策略
    """
    
    def __init__(self):
        self.current_level = DisclosureLevel.CONTEXT
        self.strategies = {
            "initial": DisclosureLevel.CORE,
            "simple": DisclosureLevel.CONTEXT,
            "complex": DisclosureLevel.EXTENDED,
            "detailed": DisclosureLevel.DETAILED
        }
    
    def get_level_for_task(self, task_type: str) -> DisclosureLevel:
        """
        根据任务类型获取披露层级
        
        Args:
            task_type: 任务类型
            
        Returns:
            DisclosureLevel: 披露层级
        """
        level_map = {
            "greeting": DisclosureLevel.CORE,
            "simple_qa": DisclosureLevel.CONTEXT,
            "explanation": DisclosureLevel.CONTEXT,
            "coding": DisclosureLevel.EXTENDED,
            "analysis": DisclosureLevel.EXTENDED,
            "creative": DisclosureLevel.EXTENDED,
            "research": DisclosureLevel.DETAILED,
            "debugging": DisclosureLevel.DETAILED
        }
        
        return level_map.get(task_type, DisclosureLevel.CONTEXT)
    
    def adjust_level(self, feedback: str):
        """
        根据反馈调整披露层级
        
        Args:
            feedback: 用户反馈
        """
        if "太简单" in feedback or "不够详细" in feedback:
            if self.current_level.value < DisclosureLevel.DETAILED.value:
                self.current_level = DisclosureLevel(
                    self.current_level.value + 1
                )
        elif "太复杂" in feedback or "太多了" in feedback:
            if self.current_level.value > DisclosureLevel.CORE.value:
                self.current_level = DisclosureLevel(
                    self.current_level.value - 1
                )
    
    def should_include_tools(self, context: Dict[str, Any]) -> bool:
        """判断是否应该包含工具说明"""
        if not context.get("available_tools"):
            return False
        
        task = context.get("task_type", "")
        if task in ["coding", "analysis", "research"]:
            return self.current_level.value >= DisclosureLevel.CONTEXT.value
        
        return self.current_level.value >= DisclosureLevel.EXTENDED.value
    
    def should_include_history(self, context: Dict[str, Any]) -> bool:
        """判断是否应该包含对话历史"""
        history_length = context.get("conversation_length", 0)
        
        if history_length == 0:
            return False
        
        if self.current_level == DisclosureLevel.CORE:
            return False
        
        if history_length <= 2:
            return self.current_level.value >= DisclosureLevel.CONTEXT.value
        
        return self.current_level.value >= DisclosureLevel.EXTENDED.value
    
    def truncate_history(self, history: List[Dict[str, str]], 
                        max_turns: int = None) -> List[Dict[str, str]]:
        """
        智能截断对话历史
        
        Args:
            history: 对话历史
            max_turns: 最大轮数
            
        Returns:
            List[Dict[str, str]]: 截断后的历史
        """
        if not history:
            return []
        
        if max_turns is None:
            if self.current_level == DisclosureLevel.CORE:
                max_turns = 0
            elif self.current_level == DisclosureLevel.CONTEXT:
                max_turns = 2
            elif self.current_level == DisclosureLevel.EXTENDED:
                max_turns = 5
            else:
                max_turns = 10
        
        if len(history) <= max_turns * 2:
            return history
        
        recent = history[-max_turns * 2:]
        
        summary_turns = max_turns // 2
        if summary_turns > 0 and len(history) > max_turns * 2:
            summary = {
                "role": "system",
                "content": f"[省略了 {len(history) - max_turns * 2} 轮对话]"
            }
            return [summary] + recent
        
        return recent


def create_progressive_prompt(user_message: str,
                             entities: Dict[str, Any] = None,
                             memories: List[Any] = None,
                             tools: List[Dict[str, Any]] = None,
                             history: List[Dict[str, str]] = None,
                             task_type: str = "simple_qa") -> str:
    """
    便捷函数：创建渐进式披露提示词
    
    Args:
        user_message: 用户消息
        entities: 实体信息
        memories: 相关记忆
        tools: 可用工具
        history: 对话历史
        task_type: 任务类型
        
    Returns:
        str: 构建好的提示词
    """
    controller = DisclosureController()
    disclosure_level = controller.get_level_for_task(task_type)
    
    builder = ProgressivePromptBuilder()
    
    truncated_history = controller.truncate_history(history or [])
    
    context = {
        "role": "智能助手",
        "personality": "专业、友好、简洁",
        "entities": entities or {},
        "recent_memories": memories or [],
        "available_tools": tools or [],
        "conversation_history": truncated_history,
        "conversation_length": len(truncated_history) // 2,
        "task_type": task_type,
        "requires_tools": bool(tools)
    }
    
    return builder.build(context, disclosure_level)
