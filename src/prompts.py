"""
提示词管理模块

提供结构化的提示词模板管理和动态生成功能
支持多角色、多场景的提示词定制
"""

import json
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from enum import Enum


class PromptRole(Enum):
    """提示词角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    CONTEXT = "context"


class PromptTemplate:
    """提示词模板"""
    
    def __init__(self, name: str, role: PromptRole, content: str, 
                 description: str = "", variables: List[str] = None):
        self.name = name
        self.role = role
        self.content = content
        self.description = description
        self.variables = variables or []
    
    def render(self, **kwargs) -> str:
        """
        渲染提示词模板
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            str: 渲染后的提示词
        """
        content = self.content
        for var in self.variables:
            value = kwargs.get(var, f"{{{var}}}")
            placeholder = f"{{{var}}}"
            content = content.replace(placeholder, str(value))
        return content
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "role": self.role.value,
            "content": self.content,
            "description": self.description,
            "variables": self.variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """从字典创建"""
        return cls(
            name=data["name"],
            role=PromptRole(data["role"]),
            content=data["content"],
            description=data.get("description", ""),
            variables=data.get("variables", [])
        )


class PromptManager:
    """
    提示词管理器
    
    管理所有提示词模板，支持模板组合和动态生成
    """
    
    def __init__(self, template_dir: str = "prompts"):
        """
        初始化提示词管理器
        
        Args:
            template_dir: 提示词模板目录
        """
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, PromptTemplate] = {}
        self._system_prompts: List[PromptTemplate] = []
        
        self._init_default_templates()
    
    def _init_default_templates(self):
        """初始化默认提示词模板"""
        system_templates = [
            PromptTemplate(
                name="base_system",
                role=PromptRole.SYSTEM,
                description="基础系统提示词",
                content="""你是一个智能助手，具备长期记忆能力和工具调用能力。

记忆系统:
- L0 工作记忆: 当前对话上下文
- L1 短期记忆: 最近对话历史  
- L2 长期记忆: 持久化记忆（用户偏好、重要事实等）

{available_tools}

使用说明:
1. 你可以使用工具来帮助用户解决问题
2. 重要信息会自动提取并存储到长期记忆中
3. 在回答时会自动检索相关记忆
4. 支持语义检索，可以理解查询意图

请友好、专业地回答用户的问题。""",
                variables=["available_tools"]
            ),
            PromptTemplate(
                name="memory_context",
                role=PromptRole.CONTEXT,
                description="记忆上下文提示词",
                content="""相关记忆:
{memories}

实体信息:
{entities}""",
                variables=["memories", "entities"]
            ),
            PromptTemplate(
                name="conversation_history",
                role=PromptRole.CONTEXT,
                description="对话历史提示词",
                content="""对话历史:
{history}""",
                variables=["history"]
            ),
            PromptTemplate(
                name="user_profile",
                role=PromptRole.CONTEXT,
                description="用户画像提示词",
                content="""用户信息:
- 姓名: {name}
- 偏好: {preferences}
- 最近关注: {recent_interests}""",
                variables=["name", "preferences", "recent_interests"]
            ),
            PromptTemplate(
                name="task_instruction",
                role=PromptRole.USER,
                description="任务指令提示词",
                content="""{task_description}

要求:
{requirements}

开始执行。""",
                variables=["task_description", "requirements"]
            ),
            PromptTemplate(
                name="reminder",
                role=PromptRole.CONTEXT,
                description="提醒提示词",
                content="""重要提醒:
{reminders}""",
                variables=["reminders"]
            )
        ]
        
        for template in system_templates:
            self.register(template)
            if template.role == PromptRole.SYSTEM:
                self._system_prompts.append(template)
    
    def register(self, template: PromptTemplate):
        """
        注册提示词模板
        
        Args:
            template: 提示词模板
        """
        self.templates[template.name] = template
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """
        获取提示词模板
        
        Args:
            name: 模板名称
            
        Returns:
            Optional[PromptTemplate]: 模板对象
        """
        return self.templates.get(name)
    
    def render(self, name: str, **kwargs) -> str:
        """
        渲染提示词模板
        
        Args:
            name: 模板名称
            **kwargs: 模板变量
            
        Returns:
            str: 渲染后的提示词
        """
        template = self.get(name)
        if template is None:
            return f"[模板不存在: {name}]"
        return template.render(**kwargs)
    
    def build_system_prompt(self, tools: str = "", memories: str = "", 
                           entities: str = "") -> str:
        """
        构建完整的系统提示词
        
        Args:
            tools: 可用工具描述
            memories: 相关记忆
            entities: 实体信息
            
        Returns:
            str: 完整的系统提示词
        """
        base = self.render("base_system", available_tools=tools)
        
        if memories or entities:
            context_parts = []
            if memories:
                context_parts.append(f"相关记忆:\n{memories}")
            if entities:
                context_parts.append(f"实体信息:\n{entities}")
            context = "\n\n".join(context_parts)
            base = f"{base}\n\n{context}"
        
        return base
    
    def build_conversation_context(self, history: List[Dict[str, str]], 
                                  max_turns: int = 10) -> str:
        """
        构建对话历史上下文
        
        Args:
            history: 对话历史
            max_turns: 最大轮数
            
        Returns:
            str: 对话历史字符串
        """
        if not history:
            return ""
        
        recent = history[-max_turns * 2:] if len(history) > max_turns * 2 else history
        
        lines = []
        for i, msg in enumerate(recent):
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"{i+1}. [{role}] {content}")
        
        return "\n".join(lines)
    
    def build_user_profile(self, entity_cache: Dict[str, Any]) -> str:
        """
        构建用户画像
        
        Args:
            entity_cache: 实体缓存
            
        Returns:
            str: 用户画像字符串
        """
        if not entity_cache:
            return ""
        
        parts = []
        if "用户姓名" in entity_cache:
            parts.append(f"姓名: {entity_cache['用户姓名']}")
        
        prefs = [v for k, v in entity_cache.items() if "偏好" in k]
        if prefs:
            parts.append(f"偏好: {', '.join(prefs)}")
        
        return "\n".join(parts) if parts else ""
    
    def create_skill_prompt(self, skill_name: str, skill_data: Dict[str, Any]) -> str:
        """
        为技能创建专用提示词
        
        Args:
            skill_name: 技能名称
            skill_data: 技能数据
            
        Returns:
            str: 技能提示词
        """
        description = skill_data.get("description", "")
        parameters = skill_data.get("parameters", {})
        examples = skill_data.get("examples", [])
        
        prompt = f"技能: {skill_name}\n"
        prompt += f"描述: {description}\n\n"
        
        if parameters:
            prompt += "参数:\n"
            for param_name, param_info in parameters.items():
                param_type = param_info.get("type", "string")
                required = param_info.get("required", False)
                desc = param_info.get("description", "")
                prompt += f"  - {param_name} ({param_type})"
                if required:
                    prompt += " [必需]"
                prompt += f": {desc}\n"
        
        if examples:
            prompt += "\n示例:\n"
            for ex in examples[:3]:
                prompt += f"  输入: {ex.get('input', '')}\n"
                prompt += f"  输出: {ex.get('expected_output', '')}\n"
        
        return prompt
    
    def create_task_prompt(self, task: str, context: Dict[str, Any] = None) -> str:
        """
        创建任务提示词
        
        Args:
            task: 任务描述
            context: 上下文信息
            
        Returns:
            str: 任务提示词
        """
        prompt = f"任务: {task}\n\n"
        
        if context:
            if "constraints" in context:
                prompt += "约束条件:\n"
                for c in context["constraints"]:
                    prompt += f"  - {c}\n"
                prompt += "\n"
            
            if "goal" in context:
                prompt += f"目标: {context['goal']}\n\n"
            
            if "output_format" in context:
                prompt += f"输出格式: {context['output_format']}\n\n"
        
        return prompt
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        列出所有模板
        
        Returns:
            List[Dict[str, Any]]: 模板列表
        """
        return [t.to_dict() for t in self.templates.values()]
    
    def load_from_file(self, file_path: str):
        """
        从文件加载模板
        
        Args:
            file_path: 文件路径
        """
        path = Path(file_path)
        if not path.exists():
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    template = PromptTemplate.from_dict(item)
                    self.register(template)
            elif isinstance(data, dict) and "templates" in data:
                for item in data["templates"]:
                    template = PromptTemplate.from_dict(item)
                    self.register(template)
        except Exception as e:
            print(f"加载提示词模板失败 {file_path}: {e}")
    
    def save_to_file(self, file_path: str):
        """
        保存模板到文件
        
        Args:
            file_path: 文件路径
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        templates_data = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "templates": [t.to_dict() for t in self.templates.values()]
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=2)


class DynamicPromptBuilder:
    """
    动态提示词构建器
    
    根据上下文动态组合提示词
    """
    
    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
    
    def build_context_prompt(self, query: str, memories: List[Any] = None,
                            entity_cache: Dict[str, Any] = None,
                            conversation_history: List[Dict[str, str]] = None) -> str:
        """
        构建完整的上下文提示词
        
        Args:
            query: 用户查询
            memories: 相关记忆
            entity_cache: 实体缓存
            conversation_history: 对话历史
            
        Returns:
            str: 完整的提示词
        """
        parts = []
        
        if conversation_history:
            history = self.prompt_manager.build_conversation_context(conversation_history)
            if history:
                parts.append(history)
        
        if memories:
            memory_lines = []
            for mem in memories:
                cat = getattr(mem, 'category', 'general')
                cont = getattr(mem, 'content', str(mem))
                score = getattr(mem, 'score', 0.0)
                memory_lines.append(f"- [{cat}] {cont} (相关度: {score:.2f})")
            parts.append("相关记忆:\n" + "\n".join(memory_lines))
        
        if entity_cache:
            profile = self.prompt_manager.build_user_profile(entity_cache)
            if profile:
                parts.append("用户信息:\n" + profile)
        
        if parts:
            parts.insert(0, f"用户问题: {query}\n")
            return "\n\n".join(parts)
        
        return query
    
    def build_skill_invocation_prompt(self, skill_name: str, skill_data: Dict[str, Any],
                                     parameters: Dict[str, Any]) -> str:
        """
        构建技能调用提示词
        
        Args:
            skill_name: 技能名称
            skill_data: 技能数据
            parameters: 调用参数
            
        Returns:
            str: 技能调用提示词
        """
        skill_prompt = self.prompt_manager.create_skill_prompt(skill_name, skill_data)
        
        parts = [skill_prompt]
        parts.append("\n当前参数:")
        for key, value in parameters.items():
            parts.append(f"  {key}: {value}")
        
        return "\n".join(parts)
    
    def build_reflection_prompt(self, task: str, result: str, 
                               context: str = "") -> str:
        """
        构建反思提示词
        
        Args:
            task: 原始任务
            result: 执行结果
            context: 上下文
            
        Returns:
            str: 反思提示词
        """
        prompt = f"任务: {task}\n\n"
        prompt += f"结果: {result}\n\n"
        
        if context:
            prompt += f"上下文: {context}\n\n"
        
        prompt += """请反思:
1. 这个结果是否正确解决了用户的问题？
2. 有哪些可以改进的地方？
3. 是否需要记忆任何重要信息？
4. 是否有遗漏的关键点？"""
        
        return prompt
