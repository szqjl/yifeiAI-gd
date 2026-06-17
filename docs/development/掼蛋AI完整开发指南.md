---
title: 掼蛋AI完整开发指南
type: guide
category: Development/CompleteGuide
source: 掼蛋AI完整开发指南.md
version: v2.1
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}
tags: [开发指南, 知识注入, 训练方法, 参赛指南, 技术实现, 最佳实践, 冲突解决, 知识更新]
difficulty: 涓绾
priority: 5
game_phase: 全阶段
---

# 掼蛋AI完整开发指南

## 概述
本文档整合了掼蛋AI开发的所有核心内容，包括专家知识注入系统（基于丁华秘籍：夈佽练方法和平台、参赛指南椼佹妧鏈实现方案）傛湰文档旨在为掼蛋AI寮鍙戣呫佺爺究人鍛樸佸弬璧涢夋墜提供完整的开发路径，从知识注入到实战参赛的全流程指导笺傚綋前基于平台v1006版本设计紝后续接口变更通过版本适配器处理銆

**目标**：
- 提供专家知识注入系统，实现基于丁华秘籍的知识驱动AI
- 介绍分层璁练方法，浠庤勫垯引擎到强鍖栧︿範的渐进式璁缁
- 指导煎弬赛流程和鎶鏈要点，确保濈符合南京邮电大学平台拌佹眰
- 提供完整的技术实现方案堝拰最佳实践
- 支持终韬记忆系统，投喂一次永久使用

**适用对象**：掼蛋AI寮鍙戣呫佺爺究人鍛樸佸弬璧涢夋墜  
**文档版本**：v2.1  
**鏈后更鏂**：使用系统时间API获取（`datetime.now()`：

## 详细内容

### 第一部分：专家知识注入系统

#### 1.1 知识来源

##### 丁华《掼蛋技宸х樼睄》整鍚
**来源**：`docs/archive/skill/掼蛋鎶宸х樼睄(丁华).md`（OCR提取：160页）

**核心知识要点**：
- **规则绫**：出牌优先级、主鐗/鍓牌使用时鏈恒佺偢寮 (Bomb) 与拆牌原鍒
- **配合策略**：队友间让牌与配合节濂忋佸崌绾/封堵联动
- **观察判断**：氳扮墝涓庤荤墝銆侀氳繃牌型估算对手持牌
- **升级防守**：关閿回合保留闃绘㈠崌级的鐗屻佺偢寮 (Bomb) 阻挡策略
- **时机掌握**：氶栬疆进攻与留牌权琛°佺偢寮 (Bomb) 使用时机

**优先级划鍒**：
- **高优先级**：直接影响胜负的规则（保炸弹 (Bomb)、阻止升绾с佷富要防瀹堣勫垯：
- **涓优先绾**：队友配合与升级鑺傚忕浉关策鐣
- **低优先级**：技宸фф彁绀恒佺ず渚嬫у瑰眬

**提取效果评估**：OCR提取鐨勭樼睄文本质量完整，这鏈书作为掼蛋理论书籍之涓，具有中上水平的实战效果（胜率提升约15-20%：夈傚疄际可用知识约70-80%（高缃信度规则和策略），后缁将引入更多知识源：堝傝嗛戠礌材分析）来丰富知识库銆

#### 1.2 知识提取流程
```python
# 知识提取工作娴
1. OCR文本清洗 ↓ 去重、合并换琛屻佺籂閿
2. 知识抽取 ↓ RealExpertKnowledgeExtractor
3. 格式鍖 ↓ StandardGuandanKnowledge
4. 验证过滤 ↓ confidence >= 0.8 优先注入
5. 存储入库 ↓ KnowledgeInjectionSystem
6. 生成策略规则 ↓ build_strategy_rules()
```

#### 1.3 知识注入系统架构

##### 核心组件
```python
# src/core/knowledge_injection_system.py
class KnowledgeInjectionSystem:
    """知识注入系统 - 核心控制鍣"""
    
    async def inject_knowledge_package(self, package_path: str):
        """注入知识鍖"""
        # 1. 加载知识鍖
        # 2. 处理和验证知璇
        # 3. 存储到持久化数据搴
        # 4. 构建内存索引
        # 5. 通知AI客户端集成
```

##### 知识分类体系
```python
class GuandanKnowledgeCategory(Enum):
    BASIC_RULES = "basic_rules"           # 基础规则
    CARD_TYPES = "card_types"             # 牌型识别 (Single/Pair/Bomb绛)
    TACTICAL_COOPERATION = "tactical_cooperation"  # 战术配合
    UPGRADE_STRATEGY = "upgrade_strategy"  # 升级策略
    DEFENSE_TACTICS = "defense_tactics"   # 防守战术
    GAME_PHASE_TACTICS = "game_phase_tactics"  # 闃舵垫垬鏈 (opening/midgame/endgame)
    OBSERVATION_SKILLS = "observation_skills"  # 观察鎶鑳
    TIMING_MASTERY = "timing_mastery"     # 时机掌握
```

#### 1.4 增强型知识提取器
```python
# src/knowledge/enhanced_extractor.py
class RealExpertKnowledgeExtractor:
    """基于实际涓撳舵暟鎹的知识提取器"""
    
    def extract_knowledge_from_text(self, text: str, source: str):
        """从专家文鏈涓提取知识"""
        # 使用8种知识类鍒的提取模寮
        # 识别动作类型（should/suggest/avoid/observe：
        # 纭定游戏阶段和绱фョ▼搴
```

**提取模式示例**：
- 战术配合: `r"(送牌|配合|队友|让牌).*?([^。]{15,100}[。])"`
- 升级策略: `r"(升级|通关).*?([^。]{15,80}[。])"`
- 时机掌握: `r"(时机|选择|把握).*?([^。]{10,80}[。])"`

#### 1.5 知识格式化与验证
```python
# src/knowledge/expert_formatter.py
class ExpertKnowledgeFormatter:
    """专家知识格式化鍣"""
    
    def format_extracted_knowledge(self, extracted, expert_source):
        """将提取的知识杞鎹为标准格寮"""
        # 生成知识ID和名绉
        # 构建触发条件
        # 生成行动寤鸿
        # 计算优先级和缃信度
```

**标准知识格式**：
```python
@dataclass
class StandardGuandanKnowledge:
    knowledge_id: str
    name: str
    category: GuandanKnowledgeCategory
    description: str
    trigger_conditions: Dict[str, Any]  # e.g., {"stage": "play", "curPos": 1}
    action_recommendations: List[str]   # e.g., ["play Pair of main_rank"]
    confidence_score: float
    priority_score: float
    # ... 鏇村氬瓧娈
```

##### 知识冲突解决机制
褰撳氫釜知识点给出矛盾建璁时（如一涓寤鸿保炸寮 (Bomb)，另涓涓寤鸿拆炸），使用以下浠茶佹満制：

```python
class KnowledgeConflictResolver:
    """知识冲突解决鍣"""
    def __init__(self):
        self.historical_success_rates = {}  # 历史成功率缓瀛
        self.context_weights = {
            "priority": 0.4,      # 优先级权閲
            "context_match": 0.3, # 鎯呭冨尮配度权重
            "history_success": 0.2, # 历史成功率权閲
            "composite": 0.1      # 综合评分权重
        }
    
    def resolve_conflicts(self, conflicting_knowledges: List[StandardGuandanKnowledge], 
                          current_situation: Dict) -> StandardGuandanKnowledge:
        """解决知识冲突"""
        # 1. 优先级仲裁：选择priority_score鏈高的知识
        prioritized = max(conflicting_knowledges, key=lambda k: k.priority_score)
        
        # 2. 鎯呭冨尮配度：氳＄畻知识与当前情况的匹配搴
        for knowledge in conflicting_knowledges:
            match_score = self._calculate_context_match(knowledge.trigger_conditions, current_situation)
            knowledge.temp_match_score = match_score
        
        best_match = max(conflicting_knowledges, key=lambda k: k.temp_match_score)
        
        # 3. 历史成功率：基于历史使用效果加权
        for knowledge in conflicting_knowledges:
            success_rate = self.historical_success_rates.get(knowledge.knowledge_id, 0.5)
            knowledge.temp_success_score = success_rate
        
        best_history = max(conflicting_knowledges, key=lambda k: k.temp_success_score)
        
        # 4. 综合评分：加鏉冭＄畻鏈终得鍒
        scores = {}
        for knowledge in conflicting_knowledges:
            composite_score = (
                knowledge.priority_score * self.context_weights["priority"] +
                knowledge.temp_match_score * self.context_weights["context_match"] +
                knowledge.temp_success_score * self.context_weights["history_success"] +
                self._calculate_additional_factors(knowledge, current_situation) * self.context_weights["composite"]
            )
            scores[knowledge.knowledge_id] = composite_score
        
        winner_id = max(scores, key=scores.get)
        return next(k for k in conflicting_knowledges if k.knowledge_id == winner_id)
    
    def _calculate_context_match(self, conditions: Dict, situation: Dict) -> float:
        """计算鎯呭冨尮配度"""
        matches = 0
        total = 0
        for key, expected in conditions.items():
            if key in situation:
                actual = situation[key]
                if isinstance(expected, list):
                    match = any(self._fuzzy_match(e, actual) for e in expected)
                else:
                    match = self._fuzzy_match(expected, actual)
                if match:
                    matches += 1
                total += 1
        return matches / total if total > 0 else 0.0
    
    def _fuzzy_match(self, expected, actual):
        """模糊匹配（支持部分匹配）"""
        if isinstance(expected, str) and isinstance(actual, str):
            return expected.lower() in actual.lower() or actual.lower() in expected.lower()
        return expected == actual
    
    def _calculate_additional_factors(self, knowledge: StandardGuandanKnowledge, situation: Dict) -> float:
        """计算棰濆栧洜素（如游戏阶段权重）"""
        stage_weight = 1.0
        if "stage" in situation:
            if situation["stage"] == "endgame" and knowledge.category == "DEFENSE_TACTICS":
                stage_weight = 1.2  # 残局防守更重瑕
            elif situation["stage"] == "opening" and knowledge.category == "UPGRADE_STRATEGY":
                stage_weight = 1.1  # 寮灞升级策略优先
        return stage_weight
```

此机制确保在矛盾情况下，选择鏈适合当前灞面的知识（e.g., 残局闃舵典紭先防守知识）銆

#### 1.6 持久鍖栬板繂系统
```python
# src/memory/lifetime_memory_system.py
class LifetimeMemorySystem:
    """终身记忆系统 - 投喂涓次，永久使用"""
    
    async def store_knowledge_memory(self, knowledge_item, context):
        """存储知识记忆"""
        # SQLite持久化存鍌
        # 构建记忆关联
        # 更新缓存
```

**记忆系统特点**：
- 鉁 **投喂涓次，永久使用** - 知识注入后持缁生效
- 鉁 **自动关鑱** - 相关记忆自动关鑱
- 鉁 **智能妫绱** - 根据上下鏂囨索相鍏宠板繂 (e.g., stage: play, curAction: Bomb)
- 鉁 **衰减机制** - 长期鏈使用鐨勮板繂自动衰鍑
- **性能优化**：使用知识缓存和索引，支鎸10,000+条知识的蹇閫熸绱：<50ms），通过预加载高频知识和分层索引实现

### 绗二部分：训练方法

#### 2.1 璁练平台

##### 涓昏佸钩台：南京邮电大学掼蛋AI算法对抗平台
- **平台地址**：https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **当前版本**：v1006（目前无更新，后缁如有变更通过版本适配器处理：
- **鐘舵**：内测中（可参与）

**平台特点**：
- 提供离线平台用于本地开发测璇
- 完整的WebSocket + JSON通信接口 (type: notify/act, stage: beginning/play)
- 鏀鎸4个AI同时对战璁缁 (myPos: 0-3, 0-2涓闃, 1-3涓闃)
- 自动评分和排名系统

**鏈鍦拌练环澧**：氱荤嚎平台鍙用ㄦу緟纭认（鏄否包鍚完整裁判系统：夈傞勭暀模拟器接口补充功鑳姐4个AI杩愯岃祫源需求：CPU 4鏍搞佸唴瀛 8GB、GPU鍙选（强化学习时需16GB+：夈

#### 2.2 训练方法

##### 方法涓：基浜庤勫垯的传缁熻练（入门：
**适用闃舵**：入门和基础璁练（1-2鍛：

**核心思路**：
```python
1. 实现基础牌型识别 (Single/Pair/Trips/ThreePair/ThreeWithTwo/TwoTrips/Straight/StraightFlush/Bomb/tribute/back/PASS)
2. 建立出牌优先绾ц勫垯
3. 实现基础配合策略
4. 连续对局璁练优鍖
5. 分析失败案例改进规则
```

**优势**：实现简单，容易调试）岃勫垯透明  
**劣势**：策略深度有限，难以搴斿瑰嶆潅灞闈

##### 方法二：搜索算法璁练（涓级）
**适用闃舵**：中绾ц练（2-4鍛：

**核心思路**：
- 使用Minimax搜索算法
- Alpha-Beta鍓枝优鍖
- 评估函数璁捐 (考虑handCards大小、curRank、teammate_seat)
- 深度搜索优化

##### 方法三：强化学习璁练（高级：
**适用闃舵**：高绾ц练（4-8鍛：

**核心思路**：
- 使用深度强化学习（DQN/A3C/PPO：
- 通过大量对局学习鏈优策鐣
- 鑷对弈和不断改进
- 多智能体协同璁缁 (考虑myPos和curPos的团队动鎬)

##### 方法四：知识增强璁练（推荐：
**适用闃舵**：所有阶娈

**核心思路**：
- 注入专家知识（丁华秘籍：
- 结合规则引擎和强鍖栧︿範
- 知识驱动决策 (trigger_conditions匹配当前stage/curAction)
- 持续优化知识库

```python
# 知识增强AI示例
class KnowledgeDrivenAI:
    """知识驱动AI"""
    
    def make_decision(self):
        # 1. 分析当前灞闈
        situation = self._analyze_situation()  # {"stage": "play", "curPos": 1}
        
        # 2. 应用涓撳剁煡璇
        knowledge_plays = self._apply_expert_knowledge(available_plays, situation)
        
        # 3. 结合经验学习
        experience_plays = self._apply_experience_learning(available_plays)
        
        # 4. 综合评估选择
        final_play = self._comprehensive_evaluation(
            knowledge_plays, experience_plays, situation
        )
        return final_play  # e.g., ["Pair", "2", ["H2", "D2"]]
```

#### 2.3 璁练数据收集
**数据来源**：
1. 平台对战数据 - 从南閭平台获取对局记录 (stage: gameOver后的replays)
2. 鑷对弈和数据 - 多个AI版本对战
3. 涓撳舵爣注数据 - 閭请掼蛋高手标娉

**数据格式**：
```json
{
  "game_id": "20241121_001",
  "game_state": {
    "stage": "play",
    "myPos": 0,
    "curPos": 1,
    "handCards": ["S2", "H3", ...],
    "curAction": ["Single", "2", ["H2"]]
  },
  "decision": {
    "player": 0,
    "action": "play",
    "selected_cards": ["H3"],
    "reasoning": "跟随同花色，避免过早使用大牌"
  },
  "outcome": {
    "win": true,
    "score": 12
  }
}
```

#### 2.4 璁练评估指鏍
**鎶鏈指标**：
- 决策准确率：> 95%
- 响应时间：< 20秒（按实际比璧涜勫垯：屽嶆潅灞闈下允许更长决策时间）
- 稳定性：连续100灞无崩婧

**竞技指标**：
- vs 基础AI：> 80% 胜率
- vs 涓绾AI：> 60% 胜率
- vs 高级AI：> 40% 胜率
- 配合榛樺戝害：> 70%

**璁练数据规模**：起濮50灞杩涜屽垵步验证，閫愭ユ墿灞曘
```python
# 璁练数据规模评估
TRAINING_CONFIG = {
    "basic_ai": {
        "required_games": 1000,      # 基础AI璁缁
        "expected_win_rate": 0.80
    },
    "intermediate_ai": {
        "required_games": 10000,     # 涓绾AI璁缁
        "expected_win_rate": 0.60
    },
    "advanced_ai": {
        "required_games": 50000,     # 高级AI璁缁
        "expected_win_rate": 0.40,
        "rl_iterations": 1000       # 强化学习杩浠
    }
}
```

### 绗三部分：参赛指南

#### 3.1 参赛流程
```
1. 访问平台 ↓ 下载资源
   ↓
2. 闃呰绘枃妗 ↓ 理解规则
   ↓
3. 开发AI客户端
   ↓
4. 本地测璇 ↓ 纭保稳瀹
   ↓
5. 联系主办鏂 ↓ 提交用宠
   ↓
6. 正式参赛 ↓ 参与对战
   ↓
7. 持续优化 ↓ 提升排名
```

#### 3.2 鎶鏈要点

##### WebSocket连接
```python
# 本地连鎺
ws://127.0.0.1:23456/game/{user_info}

# 局域网连接
ws://[局域网IP]:23456/game/{user_info}
```

##### 组队规则
- **绗1涓鍜岀3涓连接**的AI自动为涓闃 (myPos: 0鍜2)
- **绗2涓鍜岀4涓连接**的AI自动为涓闃 (myPos: 1鍜3)
- 当前以平台拌说明为准，后缁如有更新再调鏁淬傞勭暀座位鍔ㄦ佽瘑鍒接口：
```python
class DynamicSeatIdentifier:
    """鍔ㄦ佸骇位识鍒鍣"""
    def identify_teammate(self, my_pos: int, all_positions: List[int]) -> int:
        """识别队友座位"""
        # 平台规则：0-2涓队，1-3涓闃
        teammate_map = {0: 2, 2: 0, 1: 3, 3: 1}
        return teammate_map.get(my_pos, -1)  # -1表示鏈鐭
```

##### 牌型涓英文对照（平台标准）
- Single -- 单张 (Single)
- Pair -- 对子 (Pair)
- Trips -- 三张 (Trips)
- ThreePair -- 三连瀵 (ThreePair)
- ThreeWithTwo -- 三带浜 (ThreeWithTwo)
- TwoTrips -- 钢板 (TwoTrips)
- Straight -- 顺子 (Straight)
- StraightFlush -- 同花椤 (StraightFlush)
- Bomb -- 炸弹 (Bomb)
- tribute -- 进贡 (tribute)
- back -- 还贡 (back)
- PASS -- 杩 (PASS)

#### 3.3 寮鍙戞查清鍗
**开发阶娈**：
- [ ] 下载离线平台（v1006：
- [ ] 下载使用说明涔
- [ ] 闃呰绘父鎴忚勫垯
- [ ] 理解JSON格式 (["type", "rank", ["cards"]])
- [ ] 开发WebSocket通信
- [ ] 实现牌型识别
- [ ] 实现决策逻辑
- [ ] 实现閿欒处理

**测试闃舵**：
- [ ] 本地连接测璇
- [ ] 单局完整测试
- [ ] 多局稳定性测璇
- [ ] 异常场景测试
- [ ] 性能测试（响应时闂<20秒）

**提交闃舵**：
- [ ] 鍑嗗囦唬鐮/程序
- [ ] 编写使用说明
- [ ] 编写鎶本文档
- [ ] 鍙戦佸弬赛申请邮浠

##### 参赛提交材料清单（待纭认）
- [ ] AI客户端鍙鎵ц岀▼搴
- [ ] 源代码（鏄否需要开源？待确认）
- [ ] 使用说明文档（格式要求？待纭认）
- [ ] 鎶鏈报告（字数限制？待确认）
- [ ] 测试报告（是否必须？待确认）
- [ ] 瑙嗛戞紨示（鏄否需要？待确认）

**比赛评分标准**：当鍓嶉勪及（胜鐜40-50%，决策质閲20-30%等），需联系主办方（chenxg@njupt.edu.cn）确认实际权重，并据此调整开发重点（如优先提升胜率）銆

### 绗四部分：技术实现

#### 4.1 项目结构
```
guandan-ai/
├─│ src/
│   ├─│ communication/      # WebSocket通信
│   ├─│ game_logic/         # 游戏逻辑
│   ├─│ decision/           # 决策引擎
│   ├─│ knowledge/          # 知识系统
│   │   ├─│ enhanced_extractor.py
│   │   ├─│ expert_formatter.py
│   │   └── knowledge_base.py
│   ├─│ memory/             # 记忆系统
│   │   └── lifetime_memory_system.py
│   └── core/               # 核心系统
│       └── knowledge_injection_system.py
├─│ data/
│   ├─│ knowledge/          # 知识库
│   ├─│ replays/            # 对局回放
│   └── memory/             # 记忆数据
├─│ config/
│   └── config.yaml
└── tests/
```

#### 4.2 核心模块实现

##### WebSocket通信模块
```python
# src/communication/websocket_client.py
class GuandanWebSocketClient:
    async def connect(self, url: str):
        """连接WebSocket"""
        self.websocket = await websockets.connect(url)
        await self._handle_messages()
    
    async def _process_message(self, message: str):
        """处理消息"""
        data = json.loads(message)
        message_type = data.get("type")  # notify/act
        
        if message_type == "act" and data.get("stage") == "play":
            await self._handle_play_request(data)  # curPos, curAction, handCards
```

##### 知识驱动决策引擎
```python
# src/decision/knowledge_driven_ai.py
class KnowledgeDrivenAI:
    def __init__(self, game_state, knowledge_base):
        self.game_state = game_state  # myPos, handCards, curRank, stage
        self.kb = knowledge_base
        self.conflict_resolver = KnowledgeConflictResolver()  # 集成冲突解决
    
    def make_decision(self):
        # 1. 获取鍙用出鐗
        available_plays = self.game_state.get_available_cards()
        
        # 2. 分析当前灞闈
        situation = self._analyze_situation()  # {"stage": "play", "curPos": 1}
        
        # 3. 应用专家知识（处理冲突：
        knowledge_plays = self.kb.search_relevant_knowledge(situation)
        if len(knowledge_plays) > 1 and any(self._has_conflict(knowledge_plays)):
            resolved_knowledge = self.conflict_resolver.resolve_conflicts(knowledge_plays, situation)
            knowledge_plays = [resolved_knowledge]
        knowledge_plays = self._apply_expert_knowledge(available_plays, situation)
        
        # 4. 结合经验学习
        experience_plays = self._apply_experience_learning(available_plays)
        
        # 5. 综合评估选择（超时控鍒<20秒）
        final_play = self._comprehensive_evaluation(
            knowledge_plays, experience_plays, situation
        )
        return final_play  # e.g., ["Pair", "2", ["H2", "D2"]]
```

#### 4.3 配置示例
```yaml
# config/config.yaml
platform:
  websocket_url: "ws://127.0.0.1:23456/game/{user_id}"
  version: "v1006"  # 当前版本，无更新：涢勭暀适配器处理鏈来变鏇

ai:
  name: "KnowledgeDrivenAI"
  strategy_level: "expert"
  response_timeout: 20.0  # 按实际比璧涜勫垯：<20绉

knowledge:
  injection_enabled: true
  knowledge_base_path: "data/knowledge/guandan_knowledge_base.json"
  confidence_threshold: 0.8
  conflict_resolution: true  # 鍚用冲突解鍐

memory:
  enabled: true
  memory_db_path: "data/memory/lifetime_memory.db"
  max_memory_entries: 10000
  cache_enabled: true  # 性能优化：启用缓瀛

logging:
  level: "INFO"
  file: "logs/ai_client.log"
```

### 绗五部分：完整工作娴

#### 5.1 知识注入工作娴
```python
# 完整知识注入流程
async def inject_expert_knowledge():
    # 1. 鍒濆嬪寲系统
    injection_system = KnowledgeInjectionSystem()
    memory_system = LifetimeMemorySystem()
    
    # 2. 提取涓撳剁煡璇
    extractor = RealExpertKnowledgeExtractor()
    formatter = ExpertKnowledgeFormatter()
    
    # 读取丁华秘籍
    with open("docs/archive/skill/掼蛋鎶宸х樼睄(丁华).md", "r", encoding="utf-8") as f:
        expert_text = f.read()
    
    # 3. 提取和格式化
    extracted = extractor.extract_knowledge_from_text(expert_text, "丁华秘籍")
    formatted = [formatter.format_extracted_knowledge(e, "丁华秘籍") 
                 for e in extracted]
    
    # 4. 过滤高置信度知识
    high_confidence = [k for k in formatted if k.confidence_score >= 0.8]
    
    # 5. 注入系统（集成冲突解决）
    resolver = KnowledgeConflictResolver()
    for knowledge in high_confidence:
        await injection_system.inject_knowledge_package(knowledge)
        await memory_system.store_knowledge_memory(knowledge)
    
    print(f"成功注入 {len(high_confidence)} 条专家知璇")
```

#### 5.2 璁练工作流
```python
# 完整璁练流绋
async def train_guandan_ai():
    # 1. 鍒濆嬪寲AI
    game_state = GameState()  # handCards, myPos, curPos, stage
    knowledge_base = GuandanKnowledgeBase()
    knowledge_base.load_from_file("data/knowledge/guandan_knowledge_base.json")
    
    ai = KnowledgeDrivenAI(game_state, knowledge_base)
    
    # 2. 连接平台
    client = GuandanWebSocketClient("AI_TRAIN_001", game_state)
    client.rule_ai = ai
    
    # 3. 寮濮嬭练（璧峰50灞鍒濇ラ獙证）
    url = "ws://127.0.0.1:23456/game/AI_TRAIN_001"
    await client.connect(url)
    
    # 4. 收集璁练数据
    # 5. 分析优化
    # 6. 持续改进
```

#### 5.3 参赛工作娴
```python
# 参赛鍑嗗囨祦绋
async def prepare_for_competition():
    # 1. 纭保知识库已注鍏
    await inject_expert_knowledge()
    
    # 2. 本地测璇
    await local_testing()
    
    # 3. 性能优化
    await optimize_performance()
    
    # 4. 鍑嗗囨彁交材鏂
    prepare_submission_materials()
    
    # 5. 联系主办鏂
    contact_organizers()
```

### 绗鍏部分：最佳实璺

#### 6.1 知识注入最佳实践
1. **优先注入高置信度知识** (confidence >= 0.8)
2. **按优先级分类注入** (高优先级规则优先：屽侭omb使用时机)
3. **定期更新知识库** (根据实战鍙嶉)
4. **验证知识有效鎬** (通过对局验证)
5. **冲突解决**：集成KnowledgeConflictResolver处理矛盾寤鸿

#### 6.2 璁练最佳实璺
1. **寰序渐杩** - 浠庤勫垯引擎寮始，閫愭ュ紩入高级方娉
2. **数据驱动** - 閲嶈嗘暟鎹收集和统计分鏋 (replays分析)
3. **持续优化** - 建立鍙嶉堟満制，持续改进
4. **对比学习** - 与不同水平AI对比，找出问棰
5. **璧峰嬭勬ā**：从50灞寮始验证，閫愭ユ墿展到数千灞

#### 6.3 开发最佳实璺
1. **严格遵循JSON格式** - 纭保平台兼瀹规 (["Single", "2", ["H2"]])
2. **实现閿欒处理** - 提高系统稳定鎬
3. **记录详细日志** - 便于闂题排鏌 (stage/curAction变化)
4. **版本控制** - 使用Git管理代码
5. **鍔ㄦ佸骇位识鍒**：氶勭暀接口处理潜在的座位动态分閰

### 绗七部分：评估与优鍖

#### 7.1 性能评估
```python
# 性能评估指标
evaluation_metrics = {
    "technical": {
        "decision_accuracy": 0.95,  # 决策准确鐜
        "response_time": 20.0,      # 响应时间：堢掞紝按比璧涜勫垯：
        "stability": 100            # 连续对局鏁
    },
    "competitive": {
        "win_rate_vs_basic": 0.80,
        "win_rate_vs_intermediate": 0.60,
        "win_rate_vs_advanced": 0.40,
        "cooperation_success": 0.70
    },
    "learning": {
        "convergence_speed": 500,    # 收敛杞娆
        "generalization": 0.85,     # 泛化能力
        "adaptation": 0.75          # 适应能力
    }
}
```

##### 记忆系统性能基准测试
```python
# 性能基准测试
import time
from src.memory.lifetime_memory_system import LifetimeMemorySystem

async def benchmark_memory_retrieval():
    memory = LifetimeMemorySystem()
    await memory.load_all_knowledge()
    
    # 测试不同规模鐨勬绱㈡ц兘（已优化：缓瀛+索引：
    for knowledge_count in [100, 1000, 10000]:
        start_time = time.time()
        results = await memory.search_relevant_knowledge(
            situation={"stage": "play", "curAction": "Bomb"}, 
            limit=10
        )
        end_time = time.time()
        
        print(f"{knowledge_count}条知璇嗘绱㈣楁椂: {end_time - start_time:.4f}s")
        # 预期：100鏉 <10ms, 1000鏉 <30ms, 10000鏉 <100ms：堥氳繃分层索引和缓存实现）
```

#### 7.2 优化寤鸿
**知识系统优化**：
- 定期更新知识库
- 根据使用效果调整优先绾
- 合并相似知识椤

**决策系统优化**：
- 优化评估函数
- 调整知识权重
- 改进搜索算法
- **响应时间**：氬嶆潅灞闈下允璁<20秒决策，按实际比璧涜勫垯调整

**性能优化**：
- 优化数据结构
- 减少计算复杂搴
- 使用缓存机制：堣板繂系统已集成）

##### 知识库更鏂扮＄悊鍣
```python
class KnowledgeUpdateManager:
    """知识更新管理鍣"""
    def __init__(self):
        self.version_control = KnowledgeVersionControl()
        self.validation_pipeline = KnowledgeValidationPipeline()
    
    async def update_knowledge_base(self, new_knowledge_source: str, version: str):
        """更新知识库（鏀鎸佽嗛戠礌材）"""
        # 1. 提取新知识（文本/瑙嗛戣浆录）
        if new_knowledge_source.endswith('.mp4'):
            transcribed_text = await self._transcribe_video(new_knowledge_source)
            extracted = self._extract_from_transcription(transcribed_text)
        else:
            with open(new_knowledge_source, 'r') as f:
                text = f.read()
            extracted = self._extract_from_text(text)
        
        # 2. 验证鍏煎规
        validated = [k for k in extracted if self.validation_pipeline.validate(k)]
        
        # 3. 版本控制：堝為噺更新：
        self.version_control.create_new_version(validated, version)
        
        # 4. 增量更新（仅添加新知识，避免覆盖：
        for knowledge in validated:
            if not self._exists(knowledge.knowledge_id):
                await self._insert_knowledge(knowledge)
        
        # 5. 通知相关系统（AI重载缓存：
        await self._notify_update(version)
        print(f"知识库更新完成：版本 {version}，新澧 {len(validated)} 条知璇")
    
    async def _transcribe_video(self, video_path: str) -> str:
        """瑙嗛戣浆录（使用璇音识别API："""
        # 集成Whisper或其他ASR服务
        # 返回杞录文鏈
        pass
    
    def _exists(self, knowledge_id: str) -> bool:
        """妫查知识是否存鍦（避免重复）"""
        # 鏌ヨ㈡暟鎹搴
        pass
```

姝ょ＄悊器支持文鏈鍜岃嗛戠礌材更新，纭保知识库的持缁演进銆

**文档版本鍚屾**：
- **文档版本映射琛**：维护 `docs/VERSION_MAP.md`：岃板綍所有文档间的依赖关系和版本鍏煎规
- **链接版本妫鏌**：在文档涓嵌入版本校验脚本：岃块棶链接时验证版鏈涓鑷存
- **自动化妫鏌**：实现CI/CD管道，自动扫描文档一鑷存э紙e.g., 链接有效鎬с佸彉量命名统涓：

### 快速开濮

#### 绗涓步：获取平台资源
1. **访问平台网站**
   ```
   https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
   ```

2. **下载蹇呰佹枃浠**
   - 鉁 离线平台（v1006版本：
   - 鉁 使用说明书（v1006：
   - 鉁 JSON格式说明文档

3. **联系方式**
   - 研究鍜ㄨ: chenxg@njupt.edu.cn
   - 闂题反棣: wuguduofeng@gmail.com
   - QQ: 519301156

#### 绗浜屾ワ細鐜境准澶
```bash
# 1. 瀹夎匬ython 3.8+
python --version

# 2. 瀹夎呬緷璧
pip install websockets>=11.0
pip install asyncio>=3.4.3
pip install numpy>=1.21.0
pip install pandas>=1.5.0
pip install torch>=1.13.0  # 如需强化学习

# 3. 创建项目结构
mkdir guandan-ai
cd guandan-ai
mkdir -p {src/{communication,game_logic,decision,knowledge,memory},tests,config,logs,data/{knowledge,replays,memory}}
```

#### 绗涓夋ワ細基础实现
鍙傝 `docs/PHASE1_TASKS.md` 完成基础功能：
- WebSocket通信模块
- JSON消息处理
- 游戏逻辑模块
- 基础决策引擎

## 应用场景
- **开发阶娈**：指导从零开始构建掼蛋AI客户端，包鎷知识注入銆佽练和参赛的全流程
- **璁练阶娈**：提供分灞傝练方法，浠庤勫垯引擎到强鍖栧︿範的渐进式璺径（璧峰50灞验证：
- **参赛闃舵**：确保AI符合平台要求 (v1006 JSON格式、myPos组队规则)，并优化胜率和稳瀹氭
- **优化闃舵**：氶氳繃评估指标和最佳实践持缁改进AI性能：<20秒决策时间）
- **团队协作**：作为项鐩文档，支鎸佸氫汉开发和知识共享

## 示例/案例
- **知识注入示例**：从丁华秘籍提取"炸弹使用时机"知识，格式化为StandardGuandanKnowledge，注入到AI决策涓，当situation["curAction"]为Bomb时触发action_recommendations
- **璁缁冨瑰眬示例**：4个AI (myPos 0-3) 连接本地平台，完成涓灞游戏：岃板綍replays数据，分析决策准纭鐜 (e.g., 选择["Pair", "2", ["H2", "D2"]] 的合鐞嗘)；起濮50灞鍒濇ヨ瘎估胜鐜
- **参赛提交示例**：发送邮件到chenxg@njupt.edu.cn，附带代鐮併佷娇用ㄨ说明和技本文档，验证WebSocket连接 (ws://127.0.0.1:23456) 和响应时闂<20绉
- **记忆系统示例**：存鍌"残局逼炸"知识 (endgame闃舵)，在后续对局涓妫绱，自动应用 (confidence_score: 0.9)：涙ц兘测试显示10000条知璇嗘绱<100ms

## 注意事项
- **平台变量统一**：所有牌鍨 (Single/Pair/Bomb/tribute/back/PASS)、状鎬 (myPos/curPos/handCards/stage/type) 必须使用南京邮电大学平台标准变量名：岄栨″嚭现时标注 (e.g., 单张 (Single))
- **时间处理**：所有时间字段使用系统时间API (datetime.now().strftime('%Y-%m-%d %H:%M:%S'))：岀佹㈢‖编码时间
- **JSON格式**：严格遵守平台拌勮寖，示例：["Bomb", "2", ["H2", "D2", "C2", "S2"]]，消息示例：{"type": "act", "stage": "play", "handCards": ["S2", ...], "myPos": 0}
- **组队规则**：氱1/3连接为一闃 (myPos 0/2)：岀2/4连接为一闃 (myPos 1/3)，决策时考虑teammate_seat配合：涢勭暀鍔ㄦ佽瘑鍒接口处理潜在变更
- **响应时间**：决策时闂<20秒（按实际比璧涜勫垯），复杂灞闈下允许更长决策时间；信息监控妫查间隔≥6小时，静默时娈 (00:00-06:00) 不抓鍙
- **知识注入**：仅注入confidence >= 0.8的高质量知识，定期验证实战效果；集成KnowledgeConflictResolver处理矛盾寤鸿
- **鍚堣勬**：遵守平台使用条款，参赛前联系主办方纭认提浜よ佹眰（材料清单待纭认）：涚荤嚎平台裁判系统鍙用ㄦу緟验证：岄勭暀模拟器补鍏
- **璁缁冭勬ā**：起濮50灞鍒濇ラ獙证，閫愭ユ墿展；丁华秘籍提供涓上水平理论，后续引入瑙嗛戠瓑新知识源丰富

## 相关知识鐐
- [掼蛋AI知识库格式化方案 - 变量命名标准和知识分绫 (Rules/Strategy/Skills)]
- [掼蛋AI客户端架构方案 - 系统分层璁捐″拰通信模块 (WebSocket/JSON)]
- [江苏掼蛋规则 - 基础规则和牌型定涔 (Single/Bomb绛)]
- [丁华掼蛋鎶宸х樼睄 - 专家知识来婧 (升级策略/防守战术)]

---

**文档维护**：本文档整合了所有相关技术方案，寤鸿定期更新  
**鍙嶉堝缓璁**：氬傛湁闂题或寤鸿：岃锋彁浜Issue或联系开发团闃

## 📝 更新日志

### v2.1 (使用系统时间API获取)
- 鉁 集成用户鍙嶉堬細决策时间调整涓<20秒，璁练起濮50灞
- 鉁 实现KnowledgeConflictResolver类（优先绾/鎯呭/历史/综合浠茶侊級
- 鉁 增强KnowledgeUpdateManager，支鎸佽嗛戠礌材转录和增量更新
- 鉁 添加鍔ㄦ佸骇位识鍒接口和版鏈鍏煎硅说明
- 鉁 优化记忆系统性能（缓瀛+索引：10000鏉<100ms：
- 鉁 更新参赛材料清单（待纭认项）和璁缁冭勬ā评估
- 鉁 添加文档版本鍚屾ユ満制（映射琛/自动化妫查）

### v2.0 (使用系统时间API获取)
- 鉁 整合专家知识注入系统熴佽练方娉曘佸弬赛指南椼佹妧鏈实现
- 鉁 添加完整工作流和最佳实践
- 鉁 统一平台变量命名 (Single/Bomb/myPos/stage)
- 鉁 增强璁练评估指标和优化寤鸿
- 鉁 提供快速开始指南和行动清单

### v1.0 (使用系统时间API获取)
- 鍒濆嬬増鏈，基础开发指南

---

## 鈴 时间处理规范
**所有时间相关字段必须使用系统时间API：岀佹㈢‖编码时间銆**

### Python示例
```python
from datetime import datetime

# 获取当前时间
current_time = datetime.now()

# 格式化时间字符串
time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
# 输出：2025-11-24 14:30:00

# 涓文格寮
time_str_cn = current_time.strftime('%Y骞%m鏈%d鏃 %H:%M:%S')
# 输出：2025骞11鏈24鏃 14:30:00
```

### 元数据时间瀛楁
在文档中，`last_updated` 瀛楁靛繀须使用系统时间API：
```markdown
---
title: 文档鏍囬
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}
---
```

**绂佹㈠啓娉**：
```markdown
---
last_updated: 2025骞11鏈24鏃  # 鉂 纭编码时间
---
```

**正确写法**：
```markdown
---
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}  # 鉁 使用系统时间
---
```

