# Memory Architecture

> Created: 2026-05-13

## Chosen Approach
Progressive disclosure Markdown file system. Layered by access frequency.

## Structure
```
memory/
├── INDEX.md          # L0: Global index, read every session
├── agents/           # L1: Per-agent summaries (~2KB each)
│   ├── game-dev.md
│   ├── accounting.md
│   └── tools.md
├── topics/           # L2: Deep-dive per topic (~5-20KB each)
│   ├── hex-star-map.md
│   ├── dialogue-system.md
│   └── godot-remote-executor.md
├── journal/          # L3: Daily logs (append-only, rotate after 30d)
│   └── 2026-05-13.md
└── MEMORY.md         # Curated long-term facts (updated in place)
```

## Access Protocol
1. Session start → read INDEX.md only
2. Topic relevance detected → read L1 agent summary
3. Need detail → read L2 topic file
4. Historical context → read journal files

## Evaluated Alternatives
- **OpenViking** (dropped): Windows Native Engine missing PersistStore, both local and HTTP server modes broken
- **ChromaDB**: Viable but adds dependency, MD is sufficient for current scale
- **PostgreSQL + pgvector**: Strong option for future scale-up, PG no longer installed
- **MemGPT/Letta**: Overkill for current needs
