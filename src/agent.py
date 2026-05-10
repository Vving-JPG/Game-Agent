"""
智能体核心模块

基于 OpenViking 的智能体主类，集成记忆管理和工具调用
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from .memory_manager import MemoryManager, Memory
from .tools import create_default_tools, ToolRegistry


class Agent:
    """
    OpenViking 智能体
    
    具备长期记忆、工具调用和多轮对话能力的智能体
    """
    
    def __init__(self, config_path: str = "config/ov.conf"):
        """
        初始化智能体
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 初始化工作空间
        self.workspace = Path(self.config.get("storage", {}).get("workspace", "./openviking_workspace"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # 初始化记忆管理器
        self.memory_manager = MemoryManager(self.workspace)
        
        # 初始化工具注册表
        self.tools = create_default_tools(self.memory_manager)
        
        # 对话历史
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history = 10
        
        # 系统提示词
        self.system_prompt = self._create_system_prompt()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            return {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 替换环境变量
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
        
        return f"""你是一个智能助手，具备长期记忆能力和工具调用能力。

可用工具:
{tools_desc}

使用说明:
1. 你可以使用工具来帮助用户解决问题
2. 重要信息会自动存储到长期记忆中
3. 在回答时会自动检索相关记忆

请友好、专业地回答用户的问题。"""
    
    def chat(self, message: str) -> str:
        """
        处理用户输入并返回回复
        
        Args:
            message: 用户消息
            
        Returns:
            str: 智能体回复
        """
        # 存储用户消息到对话历史
        self.conversation_history.append({"role": "user", "content": message})
        
        # 检索相关记忆
        relevant_memories = self.memory_manager.retrieve(message, limit=3)
        memory_context = self._format_memories(relevant_memories)
        
        # 处理特殊命令
        if message.startswith("/"):
            response = self._handle_command(message)
        else:
            # 生成回复（简化版，实际应调用 VLM）
            response = self._generate_response(message, memory_context)
        
        # 存储助手回复到对话历史
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # 限制历史长度
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
        
        # 存储对话到记忆
        self._store_conversation(message, response)
        
        return response
    
    def _format_memories(self, memories: List[Memory]) -> str:
        """格式化记忆为上下文"""
        if not memories:
            return ""
        
        parts = ["相关记忆:"]
        for mem in memories:
            parts.append(f"- [{mem.category}] {mem.content}")
        return "\n".join(parts)
    
    def _generate_response(self, message: str, memory_context: str) -> str:
        """
        生成回复（简化实现）
        
        实际项目中应调用 VLM API
        """
        # 检查是否需要使用工具
        if "时间" in message or "几点" in message:
            return self.tools.execute("get_current_time")
        
        if any(keyword in message for keyword in ["计算", "等于", "+", "-", "*", "/"]):
            # 尝试提取数学表达式
            import re
            expr_match = re.search(r'[\d\+\-\*\/\(\)\.\s]+', message)
            if expr_match:
                expr = expr_match.group().strip()
                if expr:
                    return self.tools.execute("calculator", expression=expr)
        
        # 记忆相关命令
        if "记住" in message or "存储" in message:
            content = message.replace("记住", "").replace("存储", "").strip()
            if content:
                return self.tools.execute("store_memory", content=content, category="facts")
        
        if "回忆" in message or "记得" in message:
            query = message.replace("回忆", "").replace("记得", "").strip()
            if query:
                return self.tools.execute("retrieve_memory", query=query)
        
        # 默认回复
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
/history - 显示对话历史
/clear - 清空对话历史

自然语言指令:
- "记住 xxx" - 存储重要信息
- "回忆 xxx" - 检索相关记忆
- "计算 xxx" - 执行数学计算
- "现在几点" - 获取当前时间
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
            total = 0
            for category, count in stats.items():
                parts.append(f"  {category}: {count}")
                total += count
            parts.append(f"总计: {total}")
            return "\n".join(parts)
        
        elif cmd == "/history":
            if not self.conversation_history:
                return "对话历史为空"
            
            parts = ["对话历史:"]
            for i, msg in enumerate(self.conversation_history[-10:], 1):
                role = "用户" if msg["role"] == "user" else "助手"
                parts.append(f"{i}. [{role}] {msg['content'][:50]}...")
            return "\n".join(parts)
        
        elif cmd == "/clear":
            self.conversation_history.clear()
            return "对话历史已清空"
        
        else:
            return f"未知命令: {command}\n输入 /help 查看可用命令"
    
    def _store_conversation(self, user_msg: str, assistant_msg: str):
        """存储对话到记忆"""
        # 只存储重要对话（简化逻辑）
        if len(user_msg) > 20 or "记住" in user_msg:
            content = f"用户: {user_msg}\n助手: {assistant_msg}"
            self.memory_manager.store(content, category="conversations")
    
    def remember(self, content: str, category: str = "general") -> Memory:
        """
        存储重要信息到长期记忆
        
        Args:
            content: 记忆内容
            category: 记忆类别
            
        Returns:
            Memory: 创建的记忆对象
        """
        return self.memory_manager.store(content, category)
    
    def recall(self, query: str, limit: int = 5) -> List[Memory]:
        """
        从长期记忆中检索相关信息
        
        Args:
            query: 查询关键词
            limit: 返回结果数量
            
        Returns:
            List[Memory]: 匹配的记忆列表
        """
        return self.memory_manager.retrieve(query, limit=limit)
    
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
            "tools_count": len(self.tools.list_tools())
        }
