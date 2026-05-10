"""
LLM 自动生成模块

让 LLM 能够根据上下文动态生成：
1. 提示词模板
2. 技能定义
3. 角色配置
"""

import json
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime


class PromptGenerator:
    """
    提示词生成器
    
    根据对话上下文和目标，自动生成最优提示词
    """
    
    SYSTEM_TEMPLATE = """你是一个专业的提示词工程师。根据以下信息，生成最优的提示词模板。

【任务类型】
{task_type}

【用户需求】
{user_requirement}

【上下文信息】
{context_info}

【约束条件】
{constraints}

请生成符合以下 JSON 格式的提示词模板：
{{
    "name": "模板名称（英文）",
    "role": "system/user/assistant/context",
    "description": "模板描述",
    "content": "提示词内容（使用 {{变量名}} 占位）",
    "variables": ["变量1", "变量2", ...]
}}

要求：
1. 简洁，专业、易于维护
2. 变量名使用有意义的英文命名
3. 内容要具体、可操作
4. 符合渐进式披露原则"""

    TASK_TYPE_HINTS = {
        "conversation": "对话助手、聊天机器人",
        "coding": "代码编写、调试、优化",
        "writing": "文章撰写、内容创作",
        "analysis": "数据分析、问题诊断",
        "gaming": "游戏攻略、角色扮演",
        "teaching": "教育培训、知识讲解",
        "creative": "创意设计、头脑风暴"
    }
    
    def __init__(self):
        self.generated_templates: List[Dict[str, Any]] = []
    
    def generate(self, 
                 task_type: str,
                 user_requirement: str,
                 context_info: str = "",
                 constraints: str = "") -> Dict[str, Any]:
        """
        生成提示词模板
        
        Args:
            task_type: 任务类型
            user_requirement: 用户需求
            context_info: 上下文信息
            constraints: 约束条件
            
        Returns:
            Dict: 生成的提示词模板
        """
        prompt = self.SYSTEM_TEMPLATE.format(
            task_type=f"{task_type} - {self.TASK_TYPE_HINTS.get(task_type, '')}",
            user_requirement=user_requirement,
            context_info=context_info or "无",
            constraints=constraints or "无特殊约束"
        )
        
        return {
            "generated_prompt": prompt,
            "task_type": task_type,
            "hints": self.TASK_TYPE_HINTS.get(task_type, '')
        }
    
    def parse_template_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 响应中解析模板
        
        Args:
            response: LLM 响应文本
            
        Returns:
            Optional[Dict]: 解析出的模板
        """
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                template = json.loads(json_match.group())
                if self._validate_template(template):
                    self.generated_templates.append(template)
                    return template
            except json.JSONDecodeError:
                pass
        
        return self._parse_fallback(response)
    
    def _validate_template(self, template: Dict[str, Any]) -> bool:
        """验证模板格式"""
        required_fields = ["name", "role", "content"]
        return all(field in template for field in required_fields)
    
    def _parse_fallback(self, response: str) -> Optional[Dict[str, Any]]:
        """备用解析方法"""
        name_match = re.search(r'name[:\s]+["\']?([\w_]+)["\']?', response, re.I)
        role_match = re.search(r'role[:\s]+["\']?(system|user|assistant|context)["\']?', response, re.I)
        content_match = re.search(r'content[:\s]+["\']([\s\S]+?)["\']', response)
        
        if name_match and content_match:
            return {
                "name": name_match.group(1),
                "role": role_match.group(1) if role_match else "system",
                "description": "LLM 自动生成",
                "content": content_match.group(1).strip(),
                "variables": self._extract_variables(content_match.group(1))
            }
        
        return None
    
    def _extract_variables(self, content: str) -> List[str]:
        """提取变量名"""
        variables = re.findall(r'\{(\w+)\}', content)
        return list(set(variables))
    
    def save_to_file(self, template: Dict[str, Any], file_path: str):
        """保存模板到文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = []
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    existing = data.get("templates", [])
            except:
                pass
        
        existing.append(template)
        
        data = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "templates": existing
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class SkillGenerator:
    """
    技能生成器
    
    根据需求描述，自动生成技能定义文件
    """
    
    SYSTEM_TEMPLATE = """你是一个专业的技能工程师。根据以下信息，生成完整的技能定义。

【技能需求】
{skill_requirement}

【使用场景】
{use_case}

【已有工具参考】
{available_tools}

请生成符合以下 YAML 格式的技能定义：

name: skill_name
description: 技能描述
version: "1.0.0"

parameters:
  input_param:
    type: string
    description: 参数描述
    required: true/false
    default: 默认值

execution:
  type: python_function
  module: src.generated_skills
  function: skill_name_handler

examples:
  - input:
      param: value
    expected_output: "预期输出"

metadata:
  author: "LLM Generated"
  tags: [tag1, tag2]
  created_at: "{timestamp}"
"""

    SKILL_TYPE_HINTS = {
        "tool": "实用工具、执行特定操作",
        "analysis": "数据分析、报告生成",
        "automation": "流程自动化、批量处理",
        "integration": "外部系统集成、API调用",
        "utility": "辅助工具、格式转换"
    }
    
    def __init__(self):
        self.generated_skills: List[Dict[str, Any]] = []
    
    def generate(self,
                 skill_requirement: str,
                 use_case: str = "",
                 available_tools: str = "") -> Dict[str, Any]:
        """
        生成技能定义
        
        Args:
            skill_requirement: 技能需求
            use_case: 使用场景
            available_tools: 可用工具参考
            
        Returns:
            Dict: 生成的技能信息
        """
        prompt = self.SYSTEM_TEMPLATE.format(
            skill_requirement=skill_requirement,
            use_case=use_case or "通用场景",
            available_tools=available_tools or "无",
            timestamp=datetime.now().strftime("%Y-%m-%d")
        )
        
        return {
            "generated_prompt": prompt,
            "requirement": skill_requirement,
            "hints": self._generate_hints(skill_requirement)
        }
    
    def _generate_hints(self, requirement: str) -> Dict[str, str]:
        """生成提示信息"""
        hints = {
            "skill_type": "请根据功能确定技能类型",
            "parameters": "列出必要的输入参数",
            "implementation": "提供 Python 实现代码框架"
        }
        
        return hints
    
    def parse_skill_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 响应中解析技能定义
        
        Args:
            response: LLM 响应文本
            
        Returns:
            Optional[Dict]: 解析出的技能定义
        """
        yaml_match = re.search(r'name:.*?(?=\n\n|\Z)', response, re.DOTALL)
        if yaml_match:
            skill = self._parse_yaml_style(yaml_match.group())
            if skill:
                self.generated_skills.append(skill)
                return skill
        
        return None
    
    def _parse_yaml_style(self, yaml_text: str) -> Optional[Dict[str, Any]]:
        """解析 YAML 风格文本"""
        skill = {}
        
        name_match = re.search(r'name:\s*"?(\w+)"?', yaml_text)
        desc_match = re.search(r'description:\s*"?([^"\n]+)"?', yaml_text)
        version_match = re.search(r'version:\s*"?([\d.]+)"?', yaml_text)
        
        if name_match:
            skill["name"] = name_match.group(1)
            skill["description"] = desc_match.group(1).strip() if desc_match else ""
            skill["version"] = version_match.group(1) if version_match else "1.0.0"
            
            skill["parameters"] = self._extract_parameters(yaml_text)
            skill["metadata"] = {
                "author": "LLM Generated",
                "tags": ["generated"],
                "created_at": datetime.now().isoformat()
            }
            
            return skill
        
        return None
    
    def _extract_parameters(self, yaml_text: str) -> Dict[str, Any]:
        """提取参数定义"""
        params = {}
        
        param_blocks = re.findall(
            r'(\w+):\s*\n\s*type:\s*(\w+)\s*\n\s*description:\s*([^\n]+)',
            yaml_text
        )
        
        for param_name, param_type, description in param_blocks:
            params[param_name] = {
                "type": param_type,
                "description": description.strip()
            }
        
        return params
    
    def save_to_file(self, skill: Dict[str, Any], file_path: str):
        """保存技能到文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        import yaml
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(skill, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    def generate_implementation_template(self, skill_name: str, parameters: Dict[str, Any]) -> str:
        """
        生成技能实现代码模板
        
        Args:
            skill_name: 技能名称
            parameters: 参数定义
            
        Returns:
            str: Python 代码模板
        """
        func_name = f"{skill_name}_handler"
        
        param_list = []
        param_defaults = []
        for name, info in parameters.items():
            param_type = info.get("type", "str")
            default = info.get("default", "None")
            param_list.append(f"{name}: {param_type}")
            if default != "None":
                param_defaults.append(f"{name}={default}")
        
        params_str = ", ".join(param_list) if param_list else ""
        defaults_str = f"\n    def {func_name}({params_str}) -> str:\n" if param_list else f"\n    def {func_name}() -> str:\n"
        
        template = f'''"""
{skill_name} 技能实现

自动生成的技能实现代码
"""

from typing import Dict, Any


def {func_name}({params_str}) -> str:
    """
    {skill_name} 技能处理函数
    
    Args:
{chr(10).join([f"        {name}: {info.get('description', '')}" for name, info in parameters.items()])}
    
    Returns:
        str: 处理结果
    """
    # TODO: 实现技能逻辑
    
    return f"{skill_name} 处理完成"


# 如果需要导出为工具类，可以这样使用:
class {skill_name.title().replace('_', '')}Tool:
    """{skill_name} 工具类"""
    
    def __init__(self):
        self.name = "{skill_name}"
        self.description = "{parameters.get('input', {}).get('description', '自动生成的工具') if parameters else '自动生成的工具'}"
        self.parameters = {json.dumps(parameters, ensure_ascii=False, indent=8)}
    
    def execute(self, **kwargs) -> str:
        """执行技能"""
        return {func_name}(**kwargs)
'''
        
        return template


class LLMAutoGenerator:
    """
    LLM 自动生成器
    
    整合提示词和技能生成能力
    """
    
    def __init__(self, output_dir: str = "prompts/generated"):
        self.prompt_generator = PromptGenerator()
        self.skill_generator = SkillGenerator()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_prompt_for_task(self,
                              task_description: str,
                              task_type: str = "conversation",
                              context: str = "") -> Dict[str, Any]:
        """
        为任务创建提示词
        
        Args:
            task_description: 任务描述
            task_type: 任务类型
            context: 上下文信息
            
        Returns:
            Dict: 包含生成提示词的信息
        """
        result = self.prompt_generator.generate(
            task_type=task_type,
            user_requirement=task_description,
            context_info=context
        )
        
        return {
            "type": "prompt",
            "llm_input": result["generated_prompt"],
            "task_type": task_type,
            "hints": result["hints"]
        }
    
    def create_skill_for_task(self,
                             skill_description: str,
                             use_case: str = "",
                             existing_tools: List[str] = None) -> Dict[str, Any]:
        """
        为任务创建技能
        
        Args:
            skill_description: 技能描述
            use_case: 使用场景
            existing_tools: 已有工具列表
            
        Returns:
            Dict: 包含生成技能的信息
        """
        tools_str = "\n".join([f"- {t}" for t in (existing_tools or [])])
        
        result = self.skill_generator.generate(
            skill_requirement=skill_description,
            use_case=use_case,
            available_tools=tools_str
        )
        
        return {
            "type": "skill",
            "llm_input": result["generated_prompt"],
            "requirement": skill_description,
            "hints": result["hints"]
        }
    
    def save_generated_template(self, template: Dict[str, Any]):
        """保存生成的提示词模板"""
        file_path = self.output_dir / "generated_templates.json"
        self.prompt_generator.save_to_template_file(template, file_path)
    
    def save_generated_skill(self, skill: Dict[str, Any]):
        """保存生成的技能定义"""
        skill_name = skill.get("name", "generated_skill")
        file_path = self.output_dir / "skills" / f"{skill_name}.yaml"
        self.skill_generator.save_to_file(skill, file_path)
        
        impl_path = self.output_dir / "implementations" / f"{skill_name}.py"
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        
        impl_template = self.skill_generator.generate_implementation_template(
            skill_name,
            skill.get("parameters", {})
        )
        
        with open(impl_path, "w", encoding="utf-8") as f:
            f.write(impl_template)
    
    def get_generation_history(self) -> Dict[str, List]:
        """获取生成历史"""
        return {
            "prompts": self.prompt_generator.generated_templates,
            "skills": self.skill_generator.generated_skills
        }


def create_llm_generation_prompt(task: str, generation_type: str = "prompt") -> str:
    """
    创建 LLM 生成提示词
    
    Args:
        task: 任务描述
        generation_type: 生成类型 (prompt/skill/both)
        
    Returns:
        str: 组合后的提示词
    """
    if generation_type == "prompt":
        generator = PromptGenerator()
        result = generator.generate(
            task_type="general",
            user_requirement=task
        )
        return result["generated_prompt"]
    
    elif generation_type == "skill":
        generator = SkillGenerator()
        result = generator.generate(
            skill_requirement=task
        )
        return result["generated_prompt"]
    
    else:
        prompt_gen = PromptGenerator()
        skill_gen = SkillGenerator()
        
        prompt_result = prompt_gen.generate(
            task_type="general",
            user_requirement=task
        )
        skill_result = skill_gen.generate(
            skill_requirement=task
        )
        
        return f"""{prompt_result['generated_prompt']}

---

{skill_result['generated_prompt']}
"""
