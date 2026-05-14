# 记忆索引

> 全局入口 L0 — 看一眼就知道有什么，需要时再深入。
> 更新: 2026-05-13 23:10

---

## 活跃代理

| 代理 | 一句话 | 详情 |
|------|--------|------|
| default | 通用助手，能读写文件、有分层记忆 | [→](agents/default.md) |

## 长期记忆速览

| 类别 | 要点 |
|------|------|
| 记忆系统 | 渐进式披露 MD，L0→L1→L2→L3 逐层深入 |
| 基础设施 | PostgreSQL 已卸载；OpenViking 放弃（Windows 不兼容） |
| 项目 | Game-Agent，沙箱文件工具集 |
| 技能 | Python 文件 I/O 沙箱（Sandbox + FileToolSet） |

> 完整内容 → [MEMORY.md](MEMORY.md)

## 知识库

| 主题 | 说明 |
|------|------|
| — | 暂无，使用中自动积累 |

> 主题文件在 [topics/](topics/)

## 最近日志

| 日期 | 摘要 |
|------|------|
| 2026-05-13 | 多轮对话；记忆系统两次优化 |

> 按日日志在 [journal/](journal/)

---

## 目录结构

```
INDEX.md            ← 你在这里（L0，门厅）
MEMORY.md           ← 长期记忆详情（L1）
agents/             ← 代理定义（L1）
topics/             ← 主题知识（L2）
journal/            ← 按日日志（L3）
knowledge_base/     ← 外部知识 / RAG 源
chat_history/       ← 原始聊天存档
skills/             ← 工具代码（非记忆，仅存放）
```
