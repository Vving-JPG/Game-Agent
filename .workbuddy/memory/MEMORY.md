# Long-term Memory

> Updated: 2026-05-13

## User Profile
- Bilingual CN/EN, prefers Chinese
- Short指令 style, pulls back to main line after divergence
- Reviews AI output critically, flags logic contradictions
- Values accuracy over speed
- Prefers automation over manual steps
- Does milestone summaries

## Projects
- **RPG Game**: Godot 4.6.1, water-ink style, hex-star map + dialogue system. Path: `D:/RPG/`
- **Accounting Training**: Excel cost accounting templates (materials, labor, depreciation, overhead)
- **Game-Agent**: AI agent project at `D:/Game-Agent/`. Uses progressive MD memory architecture.

## Technical Decisions
- Memory: Progressive disclosure MD (not OpenViking/ChromaDB/pgvector). See topics/memory-architecture.md
- Remote execution: godot-remote-executor skill for Godot editor interaction
- IDE: Trae CN + WorkBuddy
- Cloud: Tencent Docs for collaboration
- **File I/O in terminal_chat.py**: DeepSeek Function Calling (OpenAI-compatible), two-phase pattern (non-streaming tool resolution → streaming display), sandboxed to `D:/Game-Agent/`

## Notable Opinions
- Git-style version control as a viable path to AI safety

## Infrastructure
- PostgreSQL: was at `C:\pgsql`, no longer installed (as of 2026-05-13)
- OpenViking: evaluated v0.3.16, dropped due to Windows incompatibility
- Python 3.11.9, Node 24.14.0
