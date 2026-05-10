# OpenViking Agent

基于火山引擎 [OpenViking](https://github.com/volcengine/OpenViking) 开发的智能体框架，具备长期记忆、工具调用和多轮对话能力。

## 特性

- **长期记忆**: 基于文件系统的记忆存储，支持分类管理和检索
- **工具调用**: 可扩展的工具系统，内置时间、计算、记忆等工具
- **多轮对话**: 维护对话历史，支持上下文理解
- **技能定义**: YAML 格式的技能配置文件
- **配置灵活**: 支持环境变量注入，适配多种模型提供商

## 项目结构

```
Game-Agent/
├── config/
│   └── ov.conf              # OpenViking 配置文件
├── src/
│   ├── __init__.py          # 包初始化
│   ├── agent.py             # 智能体核心类
│   ├── memory_manager.py    # 记忆管理模块
│   └── tools.py             # 工具定义和注册
├── skills/
│   └── example_skill.yaml   # 技能定义示例
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

## 使用指南

### 可用命令

在交互式模式下，输入以下命令:

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/tools` | 显示可用工具 |
| `/memory` | 显示记忆统计 |
| `/history` | 显示对话历史 |
| `/clear` | 清空对话历史 |
| `exit` | 退出程序 |

### 自然语言指令

- **记住信息**: "记住我的名字叫张三"
- **回忆信息**: "回忆我的名字"
- **计算**: "计算 123 + 456"
- **查询时间**: "现在几点"

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

## 注意事项

1. **API Key 安全**: 使用环境变量注入 API Key，不要硬编码到代码中
2. **工作空间**: 默认工作空间为 `./openviking_workspace`，需要写入权限
3. **模型服务**: 确保网络连接正常，能够访问模型服务 API

## 依赖项

- Python >= 3.10
- openviking >= 0.1.0
- python-dotenv >= 1.0.0

## 许可证

MIT License

## 相关链接

- [OpenViking GitHub](https://github.com/volcengine/OpenViking)
- [火山引擎](https://www.volcengine.com/)
