"""
智能体核心模块

基于 OpenViking 的智能体主类，集成记忆管理和工具调用
支持分层记忆、自动提取和语义检索
支持结构化的提示词管理和动态生成
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from .memory_manager import MemoryManager, Memory
from .tools import create_default_tools, ToolRegistry
from .prompts import PromptManager, DynamicPromptBuilder
from .progressive_prompts import ProgressivePromptBuilder, DisclosureController, DisclosureLevel


class Agent:
    """
    OpenViking 智能体
    
    具备长期记忆、工具调用和多轮对话能力的智能体
    支持分层记忆结构 (L0/L1/L2) 和自动记忆提取
    支持结构化的提示词管理和动态生成
    """
    
    def __init__(self, config_path: str = "config/ov.conf", use_openviking: bool = True,
                 prompt_template: str = "base"):
        """
        初始化智能体
        
        Args:
            config_path: 配置文件路径
            use_openviking: 是否启用 OpenViking 语义检索
            prompt_template: 提示词模板类型 (base/gaming/code)
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        self.workspace = Path(self.config.get("storage", {}).get("workspace", "./openviking_workspace"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        self.memory_manager = MemoryManager(self.workspace, use_openviking=use_openviking)
        
        self.tools = create_default_tools(self.memory_manager)
        
        self.prompt_manager = PromptManager()
        self._load_prompt_templates(prompt_template)
        self.prompt_builder = DynamicPromptBuilder(self.prompt_manager)
        
        self.progressive_builder = ProgressivePromptBuilder()
        self.disclosure_controller = DisclosureController()
        self.disclosure_level = DisclosureLevel.CONTEXT
        
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 20
        
        self._working_memory: List[Dict[str, Any]] = []
        self._entity_cache: Dict[str, Any] = {}
        
        self.system_prompt = self._create_system_prompt()
    
    def _load_prompt_templates(self, template_type: str):
        """加载提示词模板"""
        if template_type == "gaming":
            self.prompt_manager.load_from_file("prompts/gaming_templates.json")
        elif template_type == "code":
            self.prompt_manager.load_from_file("prompts/code_templates.json")
        else:
            self.prompt_manager.load_from_file("prompts/default_templates.json")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            for key, value in os.environ.items():
                placeholder = f"${{{key}}}"
                if placeholder in content:
                    content = content.replace(placeholder, value)
            
            return json.loads(content)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    
    def _create_system_prompt(self) -> str:
        """创建系统提示词"""
        tools_desc = json.dumps(self.tools.list_tools(), ensure_ascii=False, indent=2)
        
        return self.prompt_manager.build_system_prompt(
            tools=tools_desc,
            memories="",
            entities=""
        )
    
    def build_full_prompt(self, query: str, include_history: bool = True) -> Dict[str, str]:
        """
        构建完整的提示词上下文
        
        Args:
            query: 用户查询
            include_history: 是否包含对话历史
            
        Returns:
            Dict[str, str]: 包含 system 和 user 提示词的字典
        """
        user_parts = []
        
        if include_history and self.conversation_history:
            history = self.prompt_builder.prompt_manager.build_conversation_context(
                self.conversation_history
            )
            if history:
                user_parts.append(history)
        
        memories = self.memory_manager.retrieve(query, limit=3, use_semantic=False)
        if memories:
            memory_lines = []
            for mem in memories:
                memory_lines.append(f"- [{mem.category}] {mem.content}")
            user_parts.append("相关记忆:\n" + "\n".join(memory_lines))
        
        if self._entity_cache:
            profile = self.prompt_builder.prompt_manager.build_user_profile(self._entity_cache)
            if profile:
                user_parts.append("用户信息:\n" + profile)
        
        user_parts.append(query)
        
        return {
            "system": self.system_prompt,
            "user": "\n\n".join(user_parts)
        }
    
    def chat(self, message: str) -> str:
        """
        处理用户输入并返回回复
        
        Args:
            message: 用户消息
            
        Returns:
            str: 智能体回复
        """
        self.conversation_history.append({"role": "user", "content": message})
        
        self._update_working_memory(message)
        
        extracted = self.memory_manager.extract_and_store(message, source="conversation")
        for mem in extracted:
            self._update_entity_cache(mem)
        
        relevant_memories = self._retrieve_relevant_memories(message)
        memory_context = self._format_memories(relevant_memories)
        
        if message.startswith("/"):
            response = self._handle_command(message)
        else:
            response = self._generate_response(message, memory_context)
        
        self.conversation_history.append({"role": "assistant", "content": response})
        
        if len(self.conversation_history) > self.max_history * 2:
            self._compress_old_history()
        
        self._store_conversation(message, response)
        
        return response
    
    def _update_working_memory(self, message: str):
        """更新工作记忆"""
        self._working_memory.append({
            "content": message,
            "timestamp": self._get_timestamp()
        })
        
        if len(self._working_memory) > 10:
            self._working_memory = self._working_memory[-10:]
    
    def _update_entity_cache(self, memory: Memory):
        """更新实体缓存"""
        entity_type = memory.metadata.get("type", "unknown")
        self._entity_cache[entity_type] = memory.content
    
    def _retrieve_relevant_memories(self, query: str) -> List[Memory]:
        """检索相关记忆"""
        memories = []
        
        for key, value in self._entity_cache.items():
            if key.lower() in query.lower() or any(kw in query.lower() for kw in key.lower().split()):
                mem = Memory(value, "preferences", {"type": key})
                mem.score = 1.0
                memories.append(mem)
        
        semantic_memories = self.memory_manager.retrieve(
            query, 
            limit=5, 
            use_semantic=True
        )
        
        existing_ids = {m.id for m in memories}
        for mem in semantic_memories:
            if mem.id not in existing_ids:
                memories.append(mem)
        
        memories.sort(key=lambda x: x.score, reverse=True)
        return memories[:5]
    
    def _format_memories(self, memories: List[Memory]) -> str:
        """格式化记忆为上下文"""
        if not memories:
            return ""
        
        parts = ["相关记忆:"]
        for mem in memories:
            score_str = f" (相关度: {mem.score:.2f})" if mem.score > 0 else ""
            parts.append(f"- [{mem.category}] {mem.content}{score_str}")
        return "\n".join(parts)
    
    def _generate_response(self, message: str, memory_context: str) -> str:
        """生成回复"""
        if "时间" in message or "几点" in message:
            return self.tools.execute("get_current_time")
        
        if any(keyword in message for keyword in ["计算", "等于", "+", "-", "*", "/"]):
            import re
            expr_match = re.search(r'[\d\+\-\*\/\(\)\.\s]+', message)
            if expr_match:
                expr = expr_match.group().strip()
                if expr:
                    return self.tools.execute("calculator", expression=expr)
        
        if "记住" in message or "存储" in message:
            content = message.replace("记住", "").replace("存储", "").strip()
            if content:
                return self.tools.execute("store_memory", content=content, category="facts")
        
        if "回忆" in message or "记得" in message or "查找" in message:
            query = message.replace("回忆", "").replace("记得", "").replace("查找", "").strip()
            if query:
                return self.tools.execute("retrieve_memory", query=query)
        
        if "我是谁" in message or "我的名字" in message:
            if "用户姓名" in self._entity_cache:
                return f"根据我的记忆，你的名字是 {self._entity_cache['用户姓名']}"
            return "我还没有记住你的名字，你可以告诉我你的名字。"
        
        if "我喜欢" in message or "我不喜欢" in message:
            return "我已经记住了你的偏好！"
        
        response_parts = []
        
        if memory_context:
            response_parts.append(memory_context)
            response_parts.append("")
        
        response_parts.append(f"我收到了你的消息: {message}")
        response_parts.append("")
        response_parts.append("可用命令:")
        response_parts.append("- 输入 '/help' 查看帮助")
        response_parts.append("- 输入 '/tools' 查看可用工具")
        response_parts.append("- 输入 '/memory' 查看记忆统计")
        response_parts.append("- 输入 '/entities' 查看已记住的实体")
        response_parts.append("- 输入 '/prompts' 查看提示词模板")
        response_parts.append("- 输入 '记住 xxx' 存储记忆")
        response_parts.append("- 输入 '回忆 xxx' 检索记忆")
        
        return "\n".join(response_parts)
    
    def _handle_command(self, command: str) -> str:
        """处理特殊命令"""
        cmd = command.lower().strip()
        
        if cmd == "/help":
            return """可用命令:
/help - 显示帮助信息
/tools - 显示可用工具
/memory - 显示记忆统计
/entities - 显示已记住的实体
/history - 显示对话历史
/prompts - 显示提示词模板
/clear - 清空对话历史
/compress - 压缩对话历史

自然语言指令:
- "记住 xxx" - 存储重要信息
- "回忆 xxx" - 检索相关记忆
- "我叫xxx" - 告诉我你的名字
- "我喜欢xxx" - 记住你的偏好
- "计算 xxx" - 执行数学计算
- "现在几点" - 获取当前时间
- "我是谁" - 询问你的身份信息
"""
        
        elif cmd == "/tools":
            tools = self.tools.list_tools()
            parts = ["可用工具:"]
            for tool in tools:
                parts.append(f"\n{tool['name']}:")
                parts.append(f"  描述: {tool['description']}")
                parts.append(f"  参数: {json.dumps(tool['parameters'], ensure_ascii=False)}")
            return "\n".join(parts)
        
        elif cmd == "/memory":
            stats = self.memory_manager.get_stats()
            parts = ["记忆统计:"]
            parts.append(f"  OpenViking 语义检索: {'已启用' if stats.get('openviking_enabled') else '未启用'}")
            parts.append(f"  总记忆数: {stats.get('total', 0)}")
            parts.append("  分类统计:")
            for category, count in stats.get("categories", {}).items():
                parts.append(f"    {category}: {count}")
            return "\n".join(parts)
        
        elif cmd == "/entities":
            if not self._entity_cache:
                return "还没有记住任何实体信息"
            
            parts = ["已记住的实体:"]
            for entity_type, value in self._entity_cache.items():
                parts.append(f"  {entity_type}: {value}")
            return "\n".join(parts)
        
        elif cmd == "/prompts":
            templates = self.prompt_manager.list_templates()
            parts = ["可用提示词模板:"]
            for t in templates:
                parts.append(f"\n  {t['name']} [{t['role']}]:")
                parts.append(f"    {t['description']}")
            return "\n".join(parts)
        
        elif cmd == "/history":
            if not self.conversation_history:
                return "对话历史为空"
            
            parts = ["对话历史:"]
            for i, msg in enumerate(self.conversation_history[-10:], 1):
                role = "用户" if msg["role"] == "user" else "助手"
                content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
                parts.append(f"{i}. [{role}] {content}")
            return "\n".join(parts)
        
        elif cmd == "/clear":
            self.conversation_history.clear()
            self._working_memory.clear()
            return "对话历史已清空"
        
        elif cmd == "/compress":
            if len(self.conversation_history) < 4:
                return "对话历史太短，无需压缩"
            
            memory = self.memory_manager.compress_conversation(self.conversation_history)
            self.conversation_history = self.conversation_history[-4:]
            return f"对话历史已压缩并存储 [ID: {memory.id}]"
        
        else:
            return f"未知命令: {command}\n输入 /help 查看可用命令"
    
    def _store_conversation(self, user_msg: str, assistant_msg: str):
        """存储对话到记忆"""
        if len(user_msg) > 20 or "记住" in user_msg or "我叫" in user_msg:
            content = f"用户: {user_msg}\n助手: {assistant_msg}"
            self.memory_manager.store(
                content, 
                category="conversations",
                metadata={"type": "conversation_turn"}
            )
    
    def _compress_old_history(self):
        """压缩旧历史"""
        old_history = self.conversation_history[:-self.max_history]
        if old_history:
            self.memory_manager.compress_conversation(old_history)
        self.conversation_history = self.conversation_history[-self.max_history:]
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def remember(self, content: str, category: str = "general", layer: str = "L2") -> Memory:
        """
        存储重要信息到长期记忆
        
        Args:
            content: 记忆内容
            category: 记忆类别
            layer: 记忆层级
            
        Returns:
            Memory: 创建的记忆对象
        """
        return self.memory_manager.store(content, category, layer=layer)
    
    def recall(self, query: str, limit: int = 5, use_semantic: bool = True) -> List[Memory]:
        """
        从长期记忆中检索相关信息
        
        Args:
            query: 查询关键词
            limit: 返回结果数量
            use_semantic: 是否使用语义检索
            
        Returns:
            List[Memory]: 匹配的记忆列表
        """
        return self.memory_manager.retrieve(query, limit=limit, use_semantic=use_semantic)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取智能体统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            "workspace": str(self.workspace),
            "memory_stats": self.memory_manager.get_stats(),
            "conversation_turns": len(self.conversation_history) // 2,
            "working_memory_size": len(self._working_memory),
            "entities_count": len(self._entity_cache),
            "tools_count": len(self.tools.list_tools()),
            "prompt_templates_count": len(self.prompt_manager.list_templates())
        }
    
    def set_prompt_template(self, template_type: str):
        """
        切换提示词模板
        
        Args:
            template_type: 模板类型 (base/gaming/code)
        """
        self._load_prompt_templates(template_type)
        self.system_prompt = self._create_system_prompt()
    
    def add_custom_prompt(self, name: str, role: str, content: str, 
                          variables: List[str] = None):
        """
        添加自定义提示词模板
        
        Args:
            name: 模板名称
            role: 角色 (system/user/assistant/context)
            content: 模板内容
            variables: 变量列表
        """
        from .prompts import PromptRole, PromptTemplate
        
        template = PromptTemplate(
            name=name,
            role=PromptRole(role),
            content=content,
            variables=variables or []
        )
        self.prompt_manager.register(template)
    
    def close(self):
        """关闭资源"""
        self.memory_manager.close()
