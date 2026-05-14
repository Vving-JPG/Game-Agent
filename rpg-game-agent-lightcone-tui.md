# RPG Game Agent - 光锥驱动 TUI 游戏智能体

## 一、任务理解

### 目标
在现有 Game-Agent 项目基础上，构建一个**终端 TUI RPG 游戏**，核心由 Agent 驱动。Agent 通过 LLM 实时生成剧情、道具、NPC、任务等内容，采用**光锥机制**（当前场景 + 邻居预生成），支持**持久化存档**。

### 关键特性
- **光锥机制**：玩家所在场景实时生成，邻居场景预生成，远离区域保持"未观测"状态
- **人机协作模板优化**：用户编写提示词/输出规范/模板 → 体验游戏 → 反馈给 AI → AI 修改模板
- **持久化存档**：所有生成内容持久存储，支持加载继续
- **完整游戏系统**：探索交互、战斗、物品、任务四大核心玩法
- **CLI/TUI 交互**：终端命令行界面

### 约束
- 基于现有 Game-Agent 项目扩展，复用 `agent.py`、`memory_manager.py`、`tools.py`、`prompts.py`、`cards.py`、`config_manager.py`、`text_renderer.py` 等模块
- 云端 API（DeepSeek/OpenAI）
- Python >= 3.10

---

## 二、现有代码分析

### 可复用模块
| 模块 | 复用价值 | 需要改动 |
|------|----------|----------|
| `memory_manager.py` | 记忆存储/检索/语义搜索 | 高 - 需扩展为游戏世界状态存储 |
| `cards.py` | 世界卡/角色卡/设定卡系统 | 中 - 已有完善的数据模型 |
| `prompts.py` | 提示词模板管理 | 中 - 需增加游戏专用模板 |
| `config_manager.py` | 配置管理 | 低 - 基本可用 |
| `text_renderer.py` | 打字机效果输出 | 低 - 直接复用 |
| `tools.py` | 工具注册表 | 中 - 需增加游戏工具 |
| `progressive_prompts.py` | 渐进式提示词 | 低 - Token预算管理可复用 |

### 需要新建的模块
| 模块 | 用途 |
|------|------|
| `src/game_world.py` | 游戏世界状态管理（地图、场景图、光锥） |
| `src/game_engine.py` | 游戏引擎（主循环、战斗、物品、任务） |
| `src/tui.py` | TUI 界面渲染 |
| `src/template_editor.py` | 提示词/模板编辑与人机协作优化 |
| `src/content_generator.py` | LLM 内容生成器（剧情/道具/NPC/任务） |
| `src/combat_system.py` | 战斗系统 |
| `src/quest_system.py` | 任务系统 |
| `src/item_system.py` | 物品/背包系统 |
| `src/save_manager.py` | 存档管理 |

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      main.py (入口)                       │
│                  启动游戏 / 编辑模板 / 管理存档              │
└───────────────┬─────────────────────┬───────────────────┘
                │                     │
    ┌───────────▼──────────┐  ┌──────▼──────────────┐
    │   GameEngine        │  │  TemplateEditor     │
    │   游戏主循环         │  │  模板编辑/人机协作    │
    └───┬────┬────┬────┬──┘  └──────┬──────────────┘
        │    │    │    │            │
   ┌────▼┐┌──▼──┐┌▼───┐┌▼───┐  ┌──▼──────────────┐
   │Combat││Item││Quest││World│  │ PromptManager  │
   │System││Sys ││Sys  ││Map  │  │ + LLM反馈循环   │
   └──────┘└────┘└─────┘└──┬──┘  └────────────────┘
                          │
              ┌───────────▼───────────┐
              │   ContentGenerator    │
              │  LLM内容生成（光锥驱动） │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │    GameWorld          │
              │  世界状态 + 场景图      │
              │  + LightCone光锥管理   │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │  MemoryManager        │
              │  持久化存储 + 语义检索  │
              └───────────────────────┘
```

---

## 四、核心设计

### 4.1 光锥机制 (LightCone)

```python
# src/game_world.py

class SceneState(Enum):
    UNOBSERVED = "unobserved"    # 未观测 - 不生成内容
    PRE_GENERATED = "pre_gen"    # 预生成 - 邻居场景，骨架数据
    OBSERVED = "observed"        # 已观测 - 完整生成
    VISITED = "visited"          # 已访问 - 完整内容 + 玩家交互记录

class LightCone:
    """光锥管理器"""
    def __init__(self, game_world):
        self.world = game_world
        self.current_scene = None
        self.observation_range = 1  # 邻居深度

    def move_to(self, scene_id: str):
        """玩家移动到新场景，触发光锥更新"""
        old_scene = self.current_scene
        self.current_scene = scene_id

        # 1. 当前场景 → OBSERVED（完整生成）
        self.world.generate_scene(scene_id, full=True)

        # 2. 邻居场景 → PRE_GENERATED（骨架生成）
        neighbors = self.world.get_neighbors(scene_id)
        for neighbor_id in neighbors:
            if self.world.get_scene_state(neighbor_id) == SceneState.UNOBSERVED:
                self.world.generate_scene(neighbor_id, full=False)

        # 3. 离开旧场景 → 保持 VISITED 状态
        if old_scene:
            self.world.set_scene_state(old_scene, SceneState.VISITED)
```

**光锥生成策略**：
- **OBSERVED（当前场景）**：调用 LLM 生成完整场景描述、NPC 对话、可交互对象、事件
- **PRE_GENERATED（邻居场景）**：只生成场景名称、简短描述、出口方向（骨架数据）
- **UNOBSERVED（未观测）**：不生成任何内容，只记录场景 ID 和连接关系

### 4.2 游戏世界状态 (GameWorld)

```python
# src/game_world.py

class GameWorld:
    """游戏世界 - 管理所有场景和世界状态"""

    def __init__(self, save_dir: str):
        self.scenes: Dict[str, Scene] = {}       # scene_id → Scene
        self.scene_graph: Dict[str, List[str]] = {}  # 场景连接图
        self.player: Player = None
        self.world_card: WorldCard = None         # 世界设定卡
        self.global_state: Dict[str, Any] = {}    # 全局状态（任务进度等）

    def generate_scene(self, scene_id: str, full: bool = True):
        """生成场景内容"""
        if full:
            # 调用 ContentGenerator 完整生成
            content = self.content_generator.generate_full_scene(
                scene_id=scene_id,
                world_context=self.world_card.to_prompt(),
                neighbors=self.get_neighbor_names(scene_id),
                player_state=self.player.to_dict()
            )
        else:
            # 只生成骨架
            content = self.content_generator.generate_scene_skeleton(
                scene_id=scene_id,
                world_context=self.world_card.to_prompt()
            )
```

### 4.3 内容生成器 (ContentGenerator)

```python
# src/content_generator.py

class ContentGenerator:
    """LLM 内容生成器 - 光锥驱动"""

    def __init__(self, llm_client, prompt_manager):
        self.llm = llm_client
        self.prompts = prompt_manager

    def generate_full_scene(self, scene_id, world_context, neighbors, player_state) -> Scene:
        """完整生成当前场景"""
        prompt = self.prompts.render("scene_full", **{
            "world_context": world_context,
            "scene_id": scene_id,
            "neighbors": neighbors,
            "player": player_state,
            "output_schema": self.prompts.render("schema_scene")
        })
        response = self.llm.chat(prompt)
        return Scene.from_llm_response(response)

    def generate_scene_skeleton(self, scene_id, world_context) -> SceneSkeleton:
        """骨架生成邻居场景"""
        prompt = self.prompts.render("scene_skeleton", **{
            "world_context": world_context,
            "scene_id": scene_id,
            "output_schema": self.prompts.render("schema_scene_skeleton")
        })
        response = self.llm.chat(prompt)
        return SceneSkeleton.from_llm_response(response)

    def generate_npc_dialogue(self, npc, player_action, context) -> str:
        """生成 NPC 对话"""
        ...

    def generate_item(self, context) -> dict:
        """生成道具"""
        ...

    def generate_quest(self, context) -> dict:
        """生成任务"""
        ...

    def generate_combat_encounter(self, scene, player) -> dict:
        """生成战斗遭遇"""
        ...
```

### 4.4 模板编辑与人机协作 (TemplateEditor)

```python
# src/template_editor.py

class TemplateEditor:
    """提示词/模板编辑器 - 人机协作优化"""

    def __init__(self, prompt_manager, llm_client):
        self.prompts = prompt_manager
        self.llm = llm_client

    def edit_template(self, template_name: str):
        """交互式编辑模板"""
        template = self.prompts.get(template_name)
        print(f"当前模板 [{template_name}]:")
        print(template.content)
        print("\n输入新内容（空行结束）:")

        new_content = self._read_multiline_input()
        self.prompts.update_template(template_name, content=new_content)

    def test_template(self, template_name: str, test_input: str) -> str:
        """测试模板效果"""
        rendered = self.prompts.render(template_name, **json.loads(test_input))
        response = self.llm.chat(rendered)
        return response

    def ai_optimize(self, template_name: str, feedback: str):
        """根据用户反馈让 AI 优化模板"""
        current = self.prompts.get(template_name)

        optimize_prompt = f"""用户对以下提示词模板有反馈，请优化：

当前模板:
{current.content}

用户反馈:
{feedback}

请输出优化后的模板内容（只输出模板内容，不要其他解释）："""

        new_content = self.llm.chat(optimize_prompt)
        self.prompts.update_template(template_name, content=new_content)

    def start_collab_loop(self):
        """启动人机协作循环：编写 → 体验 → 反馈 → AI修改"""
        while True:
            print("\n=== 模板协作模式 ===")
            print("1. 编辑模板")
            print("2. 测试模板")
            print("3. 启动游戏体验")
            print("4. 提交反馈（AI优化）")
            print("5. 查看所有模板")
            print("0. 退出")
            # ...
```

### 4.5 战斗系统 (CombatSystem)

```python
# src/combat_system.py

class CombatSystem:
    """回合制战斗系统"""

    def __init__(self, content_generator):
        self.generator = content_generator

    def start_combat(self, player, enemies, context) -> CombatResult:
        """开始战斗"""
        # LLM 生成战斗描述和敌人行为
        ...

    def player_action(self, action: str, combat_state) -> CombatState:
        """处理玩家行动"""
        ...

    def enemy_turn(self, combat_state) -> CombatState:
        """敌人回合"""
        ...
```

### 4.6 存档系统 (SaveManager)

```python
# src/save_manager.py

class SaveManager:
    """持久化存档管理"""

    def save_game(self, game_world: GameWorld, slot: str = "auto"):
        """保存游戏"""
        save_data = {
            "timestamp": datetime.now().isoformat(),
            "player": game_world.player.to_dict(),
            "scenes": {sid: s.to_dict() for sid, s in game_world.scenes.items()},
            "scene_graph": game_world.scene_graph,
            "scene_states": game_world.scene_states,
            "global_state": game_world.global_state,
            "world_card": game_world.world_card.to_dict()
        }
        save_path = Path("saves") / f"{slot}.json"
        save_path.write_text(json.dumps(save_data, ensure_ascii=False, indent=2))

    def load_game(self, slot: str = "auto") -> GameWorld:
        """加载游戏"""
        ...

    def list_saves(self) -> List[Dict]:
        """列出所有存档"""
        ...
```

---

## 五、提示词模板体系

### 游戏专用模板（新增到 `prompts/gaming_templates.json`）

```json
{
  "templates": [
    {
      "name": "scene_full",
      "role": "system",
      "description": "完整场景生成模板",
      "variables": ["world_context", "scene_id", "neighbors", "player", "output_schema"],
      "content": "你是一个RPG游戏内容生成器。根据世界设定生成一个完整的游戏场景。\n\n世界设定:\n{world_context}\n\n场景ID: {scene_id}\n相邻场景: {neighbors}\n玩家状态: {player}\n\n请严格按照以下JSON Schema输出:\n{output_schema}"
    },
    {
      "name": "scene_skeleton",
      "role": "system",
      "description": "骨架场景生成模板（光锥预生成）",
      "variables": ["world_context", "scene_id", "output_schema"],
      "content": "根据世界设定，为邻居场景生成骨架信息（只需名称、简短描述、出口方向）。\n\n世界设定:\n{world_context}\n场景ID: {scene_id}\n\n输出Schema:\n{output_schema}"
    },
    {
      "name": "schema_scene",
      "role": "context",
      "description": "完整场景输出Schema",
      "content": "{\"name\":\"场景名称\",\"description\":\"场景详细描述（50-100字）\",\"atmosphere\":\"氛围\",\"exits\":{\"north\":\"场景ID\",\"east\":\"场景ID\"},\"npcs\":[{\"name\":\"NPC名\",\"role\":\"角色定位\",\"dialogue\":\"初始对话\"}],\"items\":[{\"name\":\"道具名\",\"description\":\"描述\",\"type\":\"武器/消耗品/任务物品\"}],\"events\":[{\"trigger\":\"触发条件\",\"description\":\"事件描述\"}]}"
    },
    {
      "name": "schema_scene_skeleton",
      "role": "context",
      "description": "骨架场景输出Schema",
      "content": "{\"name\":\"场景名称\",\"description\":\"简短描述（20字内）\",\"exits\":[\"north\",\"east\"]}"
    },
    {
      "name": "npc_dialogue",
      "role": "system",
      "description": "NPC对话生成",
      "variables": ["npc_profile", "player_action", "context", "dialogue_style"],
      "content": "你是RPG游戏中的NPC。根据角色设定生成对话回复。\n\n角色信息:\n{npc_profile}\n\n玩家行为: {player_action}\n场景上下文: {context}\n对话风格: {dialogue_style}\n\n请以角色身份回复，保持人设一致。"
    },
    {
      "name": "combat_narrate",
      "role": "system",
      "description": "战斗叙述生成",
      "variables": ["player", "enemies", "action", "result"],
      "content": "你是RPG战斗叙述者。生动描述战斗过程。\n\n玩家: {player}\n敌人: {enemies}\n行动: {action}\n结果: {result}\n\n用2-3句话生动描述这个战斗瞬间。"
    },
    {
      "name": "world_init",
      "role": "system",
      "description": "世界初始化生成",
      "variables": ["world_concept", "output_schema"],
      "content": "根据用户的世界概念，生成完整的RPG世界设定。\n\n世界概念: {world_concept}\n\n输出Schema:\n{output_schema}"
    }
  ]
}
```

---

## 六、TUI 界面设计

```
╔══════════════════════════════════════════════════════════════╗
║  🗡️ 灰烬大陆 - 第3天 | HP: 45/60 | MP: 12/20 | 金币: 130  ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  你站在一座古老的石桥上，桥下是干涸的河床。远处，            ║
║  一座被藤蔓覆盖的塔楼在薄雾中若隐若现。                      ║
║                                                              ║
║  桥的另一端，一个披着灰色斗篷的老者靠在栏杆上，               ║
║  似乎在等待什么人。                                          ║
║                                                              ║
║  [NPC] 灰袍老者 正在看着你                                   ║
║  [物品] 地上有一把生锈的匕首                                  ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  出口: 北(塔楼) | 南(村庄) | 东(森林小径)                    ║
╠══════════════════════════════════════════════════════════════╣
║  > 与老者对话                                                ║
║  > 捡起匕首                                                  ║
║  > 前往北                                                    ║
║  > 查看背包                                                  ║
║  > /save  /load  /template  /help                            ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 七、项目结构（扩展后）

```
Game-Agent/
├── config/
│   ├── ov.conf                    # OpenViking 配置
│   └── keys.conf                  # API Key 配置
├── src/
│   ├── __init__.py
│   ├── agent.py                   # [复用] 智能体核心
│   ├── memory_manager.py          # [复用] 记忆管理
│   ├── prompts.py                 # [复用] 提示词管理
│   ├── tools.py                   # [复用] 工具注册
│   ├── cards.py                   # [复用] 卡片系统
│   ├── config_manager.py          # [复用] 配置管理
│   ├── text_renderer.py           # [复用] 文本渲染
│   ├── progressive_prompts.py     # [复用] 渐进式提示词
│   ├── llm_auto_generator.py      # [复用] LLM自动生成
│   ├── game_world.py              # [新建] 游戏世界状态 + 光锥
│   ├── game_engine.py             # [新建] 游戏引擎主循环
│   ├── tui.py                     # [新建] TUI界面渲染
│   ├── content_generator.py       # [新建] LLM内容生成器
│   ├── combat_system.py           # [新建] 战斗系统
│   ├── quest_system.py            # [新建] 任务系统
│   ├── item_system.py             # [新建] 物品系统
│   ├── save_manager.py            # [新建] 存档管理
│   └── template_editor.py         # [新建] 模板编辑器
├── prompts/
│   ├── default_templates.json     # 默认模板
│   ├── gaming_templates.json      # [扩展] 游戏专用模板
│   └── code_templates.json        # 代码模板
├── saves/                         # [新建] 存档目录
├── main.py                        # [改造] 入口（支持游戏/编辑模式）
├── requirements.txt               # [更新] 新增依赖
└── README.md
```

---

## 八、实施步骤

### Phase 1: 基础框架
1. **新建 `src/game_world.py`** - Scene/SceneSkeleton/GameWorld/LightCone 数据模型
2. **新建 `src/content_generator.py`** - 封装 LLM 调用，实现场景/道具/NPC/任务生成
3. **扩展 `prompts/gaming_templates.json`** - 添加所有游戏专用模板
4. **新建 `src/save_manager.py`** - 存档/读档/列表

### Phase 2: 游戏系统
5. **新建 `src/item_system.py`** - 物品/背包/装备
6. **新建 `src/combat_system.py`** - 回合制战斗
7. **新建 `src/quest_system.py`** - 任务追踪/完成/奖励
8. **新建 `src/game_engine.py`** - 游戏主循环，串联所有系统

### Phase 3: 界面与交互
9. **新建 `src/tui.py`** - TUI 界面渲染（状态栏/场景描述/操作区）
10. **改造 `main.py`** - 支持游戏模式/模板编辑模式/存档管理

### Phase 4: 人机协作
11. **新建 `src/template_editor.py`** - 模板编辑 + AI 优化循环
12. **集成测试** - 完整游戏流程测试

---

## 九、验证方式

1. **光锥验证**：移动到新场景时，确认当前场景完整生成、邻居骨架生成、远处未生成
2. **存档验证**：保存后重启，加载存档能恢复完整游戏状态
3. **模板协作验证**：编辑模板 → 启动游戏 → 体验 → 反馈 → AI 修改 → 再次体验，确认生成内容变化
4. **战斗验证**：进入战斗 → 选择行动 → 确认伤害计算和叙述生成
5. **任务验证**：接取任务 → 完成条件 → 确认奖励发放

---

## 十、依赖更新

```
# requirements.txt 新增
rich>=13.0.0          # TUI 渲染
```

> 注：使用 `rich` 库实现 TUI，而非 `curses`，因为 rich 跨平台兼容性更好，且支持富文本渲染。
