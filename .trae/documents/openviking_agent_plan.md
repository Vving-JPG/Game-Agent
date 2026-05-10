# OpenViking 智能体开发计划

## 项目概述

基于火山引擎 OpenViking 上下文数据库开发一个具备长期记忆能力的智能体，支持多轮对话、记忆管理和工具调用。

## 当前状态分析

- 工作目录为空，需要从零搭建项目
- 需要安装 OpenViking 及相关依赖
- 需要配置模型服务（VLM + Embedding）

## 实施步骤

### 步骤 1: 环境准备

**目标**: 安装 OpenViking 和必要依赖

**操作**:
1. 创建项目目录结构
2. 创建 requirements.txt 文件
3. 安装 Python 依赖

**文件变更**:
- 新建 `requirements.txt` - 定义项目依赖
- 新建 `config/ov.conf` - OpenViking 配置文件模板

**配置说明**:
- 默认使用火山引擎 (Volcengine) 作为模型提供商
- 支持通过环境变量注入 API Key
- 工作空间设置为 `./openviking_workspace`

### 步骤 2: 核心模块开发

**目标**: 实现智能体核心功能

**操作**:
1. 创建智能体主类
2. 封装 OpenViking 记忆管理
3. 实现对话接口

**文件变更**:
- 新建 `src/__init__.py` - 包初始化
- 新建 `src/agent.py` - 智能体核心类
  - `Agent` 类: 主入口
  - `chat()` 方法: 处理用户输入
  - `remember()` 方法: 存储重要信息到长期记忆
  - `recall()` 方法: 从记忆检索相关信息
- 新建 `src/memory_manager.py` - 记忆管理封装
  - 封装 OpenViking 的文件系统操作
  - 提供记忆存储、检索、更新接口
- 新建 `src/tools.py` - 工具函数
  - 基础工具定义
  - 工具调用执行逻辑

**代码规范**:
- 使用类型注解
- 添加 docstring 文档
- 异常处理完善

### 步骤 3: 技能定义

**目标**: 定义智能体可使用的技能

**操作**:
1. 创建技能目录结构
2. 编写示例技能定义

**文件变更**:
- 新建 `skills/example_skill.yaml` - 示例技能定义
  - 技能名称、描述
  - 输入参数定义
  - 执行逻辑说明

### 步骤 4: 入口程序

**目标**: 创建可运行的入口文件

**操作**:
1. 实现命令行交互界面
2. 集成所有模块

**文件变更**:
- 新建 `main.py` - 程序入口
  - 命令行参数解析
  - 交互式对话循环
  - 优雅退出处理

### 步骤 5: 文档和配置

**目标**: 完善项目文档

**操作**:
1. 编写 README 文档
2. 添加使用示例

**文件变更**:
- 新建 `README.md` - 项目说明文档
  - 项目介绍
  - 安装步骤
  - 配置说明
  - 使用示例

## 技术细节

### OpenViking 配置

```json
{
  "storage": {
    "workspace": "./openviking_workspace"
  },
  "embedding": {
    "dense": {
      "provider": "volcengine",
      "model": "doubao-embedding-vision-251215",
      "dimension": 1024
    }
  },
  "vlm": {
    "provider": "volcengine",
    "model": "doubao-seed-2-0-pro-260215"
  }
}
```

### 记忆存储结构

```
openviking_workspace/
├── memories/
│   ├── conversations/     # 对话历史
│   ├── facts/            # 提取的事实
│   └── preferences/      # 用户偏好
├── resources/
│   └── documents/        # 文档资源
└── skills/
    └── definitions/      # 技能定义
```

### 核心类设计

```python
class Agent:
    def __init__(self, config_path: str)
    def chat(self, message: str) -> str
    def remember(self, content: str, category: str)
    def recall(self, query: str, limit: int = 5) -> List[Memory]
```

## 依赖列表

```
openviking>=0.1.0
python-dotenv>=1.0.0
```

## 验证步骤

1. 运行 `pip install -r requirements.txt` 安装依赖
2. 配置 API Key 到环境变量
3. 运行 `python main.py` 启动智能体
4. 测试对话功能
5. 测试记忆功能（询问之前对话的内容）

## 后续扩展方向

- 添加 Web 界面（Gradio/Streamlit）
- 集成更多工具（搜索、代码执行等）
- 支持多模态输入（图片、文件）
- 实现技能自动学习

## 注意事项

1. API Key 通过环境变量注入，不要硬编码
2. 工作空间目录需要写入权限
3. 首次运行会自动下载模型（如使用本地模型）
