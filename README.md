# OpenViking Agent

基于火山引擎 [OpenViking](https://github.com/volcengine/OpenViking) 开发的智能体框架，具备长期记忆、工具调用和多轮对话能力。

## 特性

- **分层记忆系统**: L0 工作记忆 / L1 短期记忆 / L2 长期记忆
- **语义检索**: 集成 OpenViking 语义搜索，理解查询意图
- **自动记忆提取**: 从对话中自动识别并存储用户偏好、姓名等信息
- **对话压缩**: 自动压缩历史对话，提取关键信息
- **提示词管理**: 结构化的提示词模板系统，支持多角色、多场景
- **工具调用**: 可扩展的工具系统，内置时间、计算、记忆等工具
- **多轮对话**: 维护对话历史，支持上下文理解
- **技能定义**: YAML 格式的技能配置文件

## 项目结构

```
Game-Agent/
├── config/
│   └── ov.conf              # OpenViking 配置文件
├── src/
│   ├── __init__.py          # 包初始化
│   ├── agent.py             # 智能体核心类
│   ├── memory_manager.py    # 记忆管理模块（支持语义检索）
│   ├── prompts.py           # 提示词管理模块
│   └── tools.py             # 工具定义和注册
├── skills/
│   └── example_skill.yaml   # 技能定义示例
├── prompts/
│   ├── default_templates.json  # 默认提示词模板
│   ├── gaming_templates.json   # 游戏助手模板
│   └── code_templates.json     # 代码助手模板
├── main.py                  # 入口程序
├── requirements.txt         # 依赖列表
└── README.md               # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

设置环境变量（推荐）:

```bash
# Windows PowerShell
$env:VOLCENGINE_API_KEY="your-api-key"

# Windows CMD
set VOLCENGINE_API_KEY=your-api-key

# Linux/Mac
export VOLCENGINE_API_KEY=your-api-key
```

或修改 `config/ov.conf` 文件，将 `${VOLCENGINE_API_KEY}` 替换为实际的 API Key。

### 3. 运行智能体

**交互式模式**:
```bash
python main.py
```

**单次对话**:
```bash
python main.py -m "你好"
```

**查看统计信息**:
```bash
python main.py --stats
```

## 记忆系统

### 分层记忆结构

| 层级 | 名称 | 说明 | TTL |
|------|------|------|-----|
| L0 | 工作记忆 | 当前对话上下文 | 1小时 |
| L1 | 短期记忆 | 最近对话历史 | 24小时 |
| L2 | 长期记忆 | 持久化记忆 | 永久 |

### 记忆类别

- `conversations` - 对话历史
- `facts` - 重要事实
- `preferences` - 用户偏好
- `entities` - 实体信息（姓名、喜好等）
- `general` - 一般记忆

### 自动记忆提取

智能体会自动从对话中提取以下信息：

- 用户姓名: "我叫张三"、"我的名字是李四"
- 用户偏好: "我喜欢编程"、"我不喜欢辣的食物"
- 重要信息: "记住明天开会"、"别忘了买牛奶"

### 语义检索

当 OpenViking 可用时，支持语义检索：

```python
# 自动使用语义检索
memories = agent.recall("用户喜欢什么")
# 返回相关度最高的记忆
```

## 使用指南

### 可用命令

在交互式模式下，输入以下命令:

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/tools` | 显示可用工具 |
| `/memory` | 显示记忆统计 |
| `/entities` | 显示已记住的实体 |
| `/history` | 显示对话历史 |
| `/clear` | 清空对话历史 |
| `/compress` | 压缩对话历史 |
| `exit` | 退出程序 |

### 自然语言指令

- **记住信息**: "记住我的名字叫张三"
- **回忆信息**: "回忆我的名字"
- **身份查询**: "我是谁"
- **偏好表达**: "我喜欢编程"
- **计算**: "计算 123 + 456"
- **查询时间**: "现在几点"

### 示例对话

```
你 > 我叫小明
助手 > 我已经记住了你的偏好！

你 > 我喜欢玩游戏
助手 > 我已经记住了你的偏好！

你 > 我是谁
助手 > 根据我的记忆，你的名字是 小明

你 > /entities
已记住的实体:
  用户姓名: 小明
  用户偏好: 玩游戏

你 > /memory
记忆统计:
  OpenViking 语义检索: 已启用
  总记忆数: 3
  分类统计:
    preferences: 2
    conversations: 1
```

### 配置文件说明

`config/ov.conf` 是 JSON 格式的配置文件:

```json
{
  "storage": {
    "workspace": "./openviking_workspace"
  },
  "embedding": {
    "dense": {
      "provider": "volcengine",
      "api_key": "${VOLCENGINE_API_KEY}",
      "model": "doubao-embedding-vision-251215"
    }
  },
  "vlm": {
    "provider": "volcengine",
    "api_key": "${VOLCENGINE_API_KEY}",
    "model": "doubao-seed-2-0-pro-260215"
  }
}
```

支持的模型提供商:
- `volcengine` - 火山引擎（豆包模型）
- `openai` - OpenAI API
- `litellm` - 统一访问多种模型
- `ollama` - 本地模型

## 扩展开发

### 添加自定义工具

在 `src/tools.py` 中继承 `Tool` 类:

```python
class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="我的工具",
            parameters={"input": {"type": "string"}}
        )
    
    def execute(self, input: str) -> str:
        return f"处理结果: {input}"
```

然后在 `create_default_tools()` 函数中注册:

```python
registry.register(MyTool())
```

### 自定义记忆提取规则

在 `memory_manager.py` 的 `extract_and_store` 方法中添加新模式：

```python
entity_patterns = [
    (r"你的正则表达式", "category", "描述"),
    # 添加更多模式...
]
```

### 定义新技能

在 `skills/` 目录下创建 YAML 文件:

```yaml
name: my_skill
description: 我的技能
parameters:
  input:
    type: string
    required: true
execution:
  type: python_function
  module: src.tools
  function: my_skill_handler
```

### 提示词模板管理

使用提示词管理器来组织和渲染提示词:

```python
from src.prompts import PromptManager, DynamicPromptBuilder

# 初始化
prompt_manager = PromptManager()

# 加载模板
prompt_manager.load_from_file("prompts/default_templates.json")

# 渲染模板
system_prompt = prompt_manager.build_system_prompt(
    tools="工具描述",
    memories="相关记忆",
    entities="实体信息"
)

# 动态构建提示词
builder = DynamicPromptBuilder(prompt_manager)
context_prompt = builder.build_context_prompt(
    query="用户查询",
    memories=[...],
    entity_cache={...}
)
```

### 切换提示词模板

```python
# 切换到游戏助手模板
agent.set_prompt_template("gaming")

# 切换到代码助手模板
agent.set_prompt_template("code")

# 添加自定义模板
agent.add_custom_prompt(
    name="my_template",
    role="system",
    content="自定义提示词内容 {variable}",
    variables=["variable"]
)
```

## API 参考

### Agent 类

```python
from src.agent import Agent

# 初始化
agent = Agent(config_path="config/ov.conf", use_openviking=True)

# 对话
response = agent.chat("你好")

# 存储记忆
memory = agent.remember("重要信息", category="facts", layer="L2")

# 检索记忆
memories = agent.recall("查询内容", limit=5, use_semantic=True)

# 获取统计
stats = agent.get_stats()

# 关闭资源
agent.close()
```

### MemoryManager 类

```python
from src.memory_manager import MemoryManager

# 初始化
manager = MemoryManager("./workspace", use_openviking=True)

# 存储记忆
memory = manager.store("内容", category="general", metadata={"key": "value"})

# 检索记忆
memories = manager.retrieve("查询", category=None, limit=5, use_semantic=True)

# 自动提取
extracted = manager.extract_and_store("我叫张三", source="conversation")

# 压缩对话
compressed = manager.compress_conversation(messages)
```

## 注意事项

1. **API Key 安全**: 使用环境变量注入 API Key，不要硬编码到代码中
2. **工作空间**: 默认工作空间为 `./openviking_workspace`，需要写入权限
3. **模型服务**: 确保网络连接正常，能够访问模型服务 API
4. **语义检索**: 需要安装 openviking 包并配置 embedding 模型

## 依赖项

- Python >= 3.10
- openviking >= 0.1.0
- python-dotenv >= 1.0.0

## 许可证

MIT License

## 相关链接

- [OpenViking GitHub](https://github.com/volcengine/OpenViking)
- [火山引擎](https://www.volcengine.com/)
- [OpenViking 文档](https://openviking.ai/)
