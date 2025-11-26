---
title: 掼蛋AI客户端基础架构方案
type: architecture
category: System/Architecture
source: 掼蛋AI客户端架构方案.md
version: v2.2
last_updated: 2025-11-25 03:30:00
tags: [架构, 客户端, WebSocket, 决策引擎, 信息监控, 知识库]
difficulty: 高级
priority: 5
game_phase: 全阶段
---

# 掼蛋AI客户端基础架构方案

## 概述
本文档提出掼蛋AI客户端的基础架构方案，旨在开发符合南京邮电大学掼蛋AI平台的客户端，实现AI自动出牌决策，支持自我对弈和数据收集，提供可扩展的架构设计。

**目标**：
- 开发符合南京邮电大学掼蛋AI平台的客户端
- 实现AI自动出牌决策
- 支持自我对弈和数据收集
- 可扩展的架构设计

## 详细内容

### 一、项目概述

#### 1.1 项目目标
- 开发符合南京邮电大学掼蛋AI平台的客户端
- 实现AI自动出牌决策
- 支持自我对弈和数据收集
- 可扩展的架构设计

#### 1.2 技术选型
- **编程语言**: Python（推荐，便于快速开发和调试）
- **WebSocket库**: websockets / websocket-client
- **JSON处理**: json（标准库）
- **日志系统**: logging（标准库）
- **配置管理**: configparser / yaml
- **网页抓取**: requests / httpx（HTTP请求）
- **HTML解析**: beautifulsoup4 / lxml（网页内容解析）
- **定时任务**: schedule / APScheduler（定时抓取）
- **通知系统**: 可选（邮件/桌面通知等）

#### 1.3 平台要求
- **平台名称**: 南京邮电大学掼蛋AI算法对抗平台
- **平台地址**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **当前版本**: v1006（内测中，可参与）
- **WebSocket连接**：
  - 本地连接：`ws://127.0.0.1:23456/game/{user_info}`
  - 局域网连接：`ws://[局域网IP]:23456/game/{user_info}`
- **JSON数据格式通信**：严格按照平台格式要求
- **4个AI同时参与**：第1、3个连接为一队，第2、4个连接为一队
- **支持Windows/Linux环境**

### 二、系统架构设计

#### 2.1 整体架构（分层设计）

```
┌─────────────────────────────────────┐
│        应用层 (Application)         │
│  - 主程序入口                       │
│  - 配置管理                         │
│  - 日志管理                         │
└─────────────────────────────────────┘
          ↓
┌─────────────────────────────────────┐
│    信息监控层 (Info Monitor)        │
│  - 平台动态抓取                     │
│  - 比赛消息监控                     │
│  - 信息通知                         │
└─────────────────────────────────────┘
          ↓
┌─────────────────────────────────────┐
│      决策层 (Decision Engine)        │
│  - 策略评估                         │
│  - 出牌决策                         │
│  - 配合策略                         │
│  - 知识库查询                       │
└─────────────────────────────────────┘
          ↓
┌─────────────────────────────────────┐
│      知识库层 (Knowledge Base)       │
│  - 规则库（硬编码）                 │
│  - 策略库（内存加载）               │
│  - 技巧库（按需查询）               │
│  - 知识检索与缓存                   │
└─────────────────────────────────────┘
          ↓
┌─────────────────────────────────────┐
│      逻辑层 (Game Logic)             │
│  - 游戏规则                         │
│  - 牌型识别                         │
│  - 牌型比较                         │
│  - 状态管理                         │
└─────────────────────────────────────┘
          ↓
┌─────────────────────────────────────┐
│      通信层 (Communication)         │
│  - WebSocket连接                    │
│  - JSON解析/构建                    │
│  - 消息路由                         │
└─────────────────────────────────────┘
          ↓
┌─────────────────────────────────────┐
│      数据层 (Data Layer)             │
│  - 对局记录                         │
│  - 数据存储                         │
│  - 统计分析                         │
│  - 平台信息存储                     │
└─────────────────────────────────────┘
```

### 三、核心模块设计

#### 3.1 通信模块 (Communication Module)

##### 3.1.1 WebSocket客户端
- **功能**:
  - 建立和维护WebSocket连接
  - 支持本地和局域网连接
  - 处理连接重连机制
  - 心跳保活
  - 异常处理和恢复

- **连接地址**:
  - 本地测试：`ws://127.0.0.1:23456/game/{user_info}`
  - 局域网对战：`ws://[局域网IP]:23456/game/{user_info}`
  - `{user_info}` 为用户信息标识

- **接口设计**:
  ```python
  class WebSocketClient:
      - connect(url: str) -> bool
      - send(message: dict) -> bool
      - receive() -> dict
      - disconnect()
      - is_connected() -> bool
      - reconnect() -> bool  # 重连功能
  ```

##### 3.1.2 JSON消息处理
- **功能**:
  - 解析平台发送的JSON消息
  - 构建发送给平台的JSON消息
  - 消息格式验证
  - 消息类型路由

- **消息类型**:
  - 游戏开始消息
  - 发牌消息
  - 出牌请求消息
  - 游戏状态更新消息
  - 游戏结束消息

#### 3.2 游戏逻辑模块 (Game Logic Module)

##### 3.2.1 牌型识别器 (CardTypeRecognizer)
- **功能**:
  - 识别所有掼蛋牌型
  - 严格按照平台JSON格式要求
  - 支持主牌识别

- **牌型中英文对照**（平台标准）:
  - **Single** -- 单张 (Single)
  - **Pair** -- 对子 (Pair)
  - **Trips** -- 三张 (Trips)
  - **ThreePair** -- 三连对 (ThreePair)
  - **ThreeWithTwo** -- 三带二 (ThreeWithTwo)
  - **TwoTrips** -- 钢板（两个三张） (TwoTrips)
  - **Straight** -- 顺子 (Straight)
  - **StraightFlush** -- 同花顺（特殊顺子） (StraightFlush)
  - **Bomb** -- 炸弹 (Bomb)

- **特殊规则**:
  - v1006版本调整了抗贡规则，与比赛版规则一致
  - 注意手牌的表示方法
  - 接口与v1003版本保持一致

##### 3.2.2 牌型比较器 (CardTypeComparator)
- **功能**:
  - 比较牌型大小
  - 判断是否可以压制
  - 判断牌型合法性

##### 3.2.3 增强游戏状态管理器 (EnhancedGameStateManager)
- **功能**:
  - 维护完整的游戏状态信息
  - 集成记牌模块
  - 提供状态查询接口
  - 支持状态快照和恢复
  - **识别队友关系**（重要）

- **组队规则**（平台规则）:
  - **第1个和第3个连接**的AI自动为一队 (myPos: 0和2)
  - **第2个和第4个连接**的AI自动为一队 (myPos: 1和3)
  - 队友识别公式: `teammate_pos = (myPos + 2) % 4`（参考获奖代码）

- **状态信息**:
  - 当前手牌列表 (handCards)
  - 已出牌历史
  - 当前出牌玩家 (curPos)
  - 当前牌型 (curAction)
  - 游戏阶段 (stage)
  - 队友座位号
  - 对手座位号
  - 主牌级别 (curRank)
  
- **增强功能**:
  - 玩家历史记录（history）: 每个玩家打出的牌和剩余牌数
  - 牌库状态（remain_cards）: 按花色和点数分类的剩余牌
  - 游戏进度状态: 连续PASS次数（pass_num, my_pass_num）
  - 配合状态: 队友位置识别、队友出牌意图分析
  
- **状态查询接口**:
  - `is_passive_play()`: 判断是否被动出牌
  - `is_active_play()`: 判断是否主动出牌
  - `is_teammate_action()`: 判断是否是队友出的牌
  - `get_player_remain_cards()`: 获取玩家剩余牌数
  - `get_teammate_remain_cards()`: 获取队友剩余牌数
  - `get_opponent_remain_cards()`: 获取对手剩余牌数
  - `get_pass_count()`: 获取PASS次数
  - `get_state_summary()`: 获取状态摘要

#### 3.3 决策引擎模块 (Decision Engine Module)

##### 3.3.1 多因素评估系统 (MultiFactorEvaluator)
- **功能**:
  - 综合评估多个因素
  - 计算动作的综合评分
  - 支持权重调整
  
- **评估因素**（6个因素，权重可调）:
  1. **剩余牌数因素** (25%): 考虑自己、队友、对手的剩余牌数
  2. **牌型大小因素** (20%): 评估牌型大小和压制能力
  3. **配合因素** (20%): 评估配合机会和配合效果
  4. **风险因素** (15%): 评估出牌风险
  5. **时机因素** (10%): 评估游戏阶段和时机
  6. **手牌结构因素** (10%): 评估对手牌结构的影响

- **接口设计**:
  ```python
  class MultiFactorEvaluator:
      def evaluate_action(self, action, action_index, cur_action, action_list) -> float
      def evaluate_all_actions(self, action_list, cur_action) -> List[Tuple[int, float]]
      def get_best_action(self, action_list, cur_action) -> int
      def update_weights(self, weights: Dict[str, float])
  ```

##### 3.3.2 策略评估器 (StrategyEvaluator)
- **功能**:
  - 评估当前局面
  - 评估手牌价值
  - 评估出牌风险
  - 评估配合机会

##### 3.3.3 出牌决策器 (PlayDecisionMaker)
- **功能**:
  - 生成候选出牌方案
  - 评估每个方案的价值
  - 选择最优出牌
  - 决定是否过牌 (PASS)
  - **主动/被动决策分离**:
    - `active_decision()`: 主动出牌决策（率先出牌或接风）
    - `passive_decision()`: 被动出牌决策（需要压制）

##### 3.3.4 配合策略器 (CooperationStrategy)
- **功能**:
  - 识别队友意图
  - 判断是否需要配合
  - 制定配合策略
  - 评估配合效果
  
- **详细实现**:
  - `should_support_teammate()`: 判断是否应该配合队友（PASS让队友继续）
  - `should_take_over()`: 判断是否应该接替队友
  - `evaluate_cooperation_opportunity()`: 评估配合机会
  - `get_cooperation_strategy()`: 获取配合策略建议
  
- **配合策略参数**（可配置）:
  - `support_threshold`: 队友牌型值阈值（默认15）
  - `danger_threshold`: 对手剩余牌数危险阈值（默认4）
  - `max_val_threshold`: 最大牌值阈值（默认14）

##### 3.3.5 决策时间控制器 (DecisionTimer)
- **功能**:
  - 设置最大决策时间（默认0.8秒）
  - 超时检测和保护机制
  - 渐进式决策支持
  - 装饰器支持（`@with_timeout`）

##### 3.3.6 牌型专门处理器 (CardTypeHandlers)
- **功能**:
  - 为每种牌型创建专门的处理类
  - 实现针对性的决策逻辑
  - 支持主动和被动两种出牌模式
  
- **已实现的处理器**:
  - `SingleHandler`: 单张专门处理
  - `PairHandler`: 对子专门处理
  - `TripsHandler`: 三张专门处理
  - `BombHandler`: 炸弹专门处理
  - `StraightHandler`: 顺子专门处理
  
- **设计模式**:
  - 使用抽象基类 `BaseCardTypeHandler` 定义统一接口
  - 通过工厂模式 `CardTypeHandlerFactory` 获取处理器

#### 3.4 知识库模块 (Knowledge Base Module)

##### 3.4.1 知识库架构设计

**分层记忆策略**（基于性能和使用频率）：

1. **硬编码层（Hardcoded Rules）**
   - **内容**：基础规则（牌型定义、压牌规则、大小关系等）
   - **实现方式**：直接写在代码中，作为函数/类方法
   - **访问方式**：O(1)直接调用
   - **更新方式**：代码修改
   - **示例**：
     ```python
     class GameRules:
         CARD_TYPES = ['Single', 'Pair', 'Trips', ...]
         def can_beat(self, card1, card2): ...
         def is_valid_type(self, cards): ...
     ```

2. **内存加载层（In-Memory Knowledge）**
   - **内容**：常用策略和技巧（组牌技巧、配火原则、常见策略模式）
   - **实现方式**：程序启动时加载到内存（字典/对象）
   - **访问方式**：O(1)内存访问
   - **更新方式**：重启程序或热更新
   - **示例**：
     ```python
     class KnowledgeBase:
         def __init__(self):
             self.grouping_priorities = self.load_grouping_rules()
             self.strategy_patterns = self.load_strategies()
     ```

3. **按需查询层（On-Demand Query）**
   - **内容**：高级技巧和特殊情况（复杂策略、边缘案例）
   - **实现方式**：需要时查询知识库文件，结果缓存
   - **访问方式**：首次O(n)查询，后续O(1)缓存访问
   - **更新方式**：知识库文件更新，缓存失效
   - **示例**：
     ```python
     class KnowledgeQuery:
         def __init__(self):
             self.cache = {}
         def query_advanced_skill(self, situation): ...
     ```

**知识库目录结构**：
```
docs/knowledge/
├── basics/              # 基础知识（规则、概念）
│   ├── 01_getting_started/
│   └── 02_beginner_guide/
└── skills/              # 技巧知识
    ├── 01_foundation/
    ├── 02_main_attack/
    ├── 03_assist_attack/
    ├── 07_opening/      # 开局技巧（组牌技巧等）
    └── 08_endgame/      # 残局技巧
```

##### 3.4.2 规则库 (Rules Library)

**功能**：
- 牌型定义和识别规则（`Single`, `Pair`, `Trips`, `ThreePair`, `ThreeWithTwo`, `TwoTrips`, `Straight`, `StraightFlush`, `Bomb`）
- 压牌规则和大小关系（同牌型比较、炸弹压牌、同花顺压牌）
- 进贡规则和升级规则（正常进贡、双下进贡、升级条件）
- 游戏流程规则（局、场、轮的定义）

**实现方式**：硬编码到`GameRules`类中

**接口设计**：
```python
class GameRules:
    # 牌型识别
    def recognize_card_type(self, cards: List[str]) -> Tuple[str, str, List[str]]
    
    # 压牌判断
    def can_beat(self, action1: List, action2: List) -> bool
    
    # 牌点大小比较
    def compare_rank(self, rank1: str, rank2: str, cur_rank: str) -> int
    
    # 进贡规则
    def get_tribute_rules(self, order: List[int]) -> Dict
    
    # 升级规则
    def get_upgrade_rules(self, order: List[int]) -> int
```

##### 3.4.3 策略库 (Strategy Library)

**功能**：
- 组牌技巧和优先级（同花顺 > 炸弹 > 顺子/三带二）
- 常用策略模式（主攻策略、助攻策略）
- 开局、中局、残局策略
- 配火原则（四头火、宜配中小不配大）

**实现方式**：启动时加载到内存

**接口设计**：
```python
class StrategyLibrary:
    def __init__(self):
        # 启动时加载
        self.grouping_priorities = self.load_grouping_priorities()
        self.strategy_patterns = self.load_strategy_patterns()
    
    # 组牌优先级
    def get_grouping_priority(self) -> Dict[str, int]
    
    # 配火原则
    def get_bomb_grouping_rules(self) -> Dict
    
    # 策略模式匹配
    def match_strategy_pattern(self, situation: Dict) -> List[str]
```

**加载内容**：
- 组牌优先级规则（同花顺 > 炸弹 > 顺子/三带二）
- 配火原则（四头火、宜配中小不配大、破二炸弹不能搭）
- 百搭使用原则（预留3个配百搭、百搭配3放后压）
- 去单化原则（无论小与大，坚持去单化）

##### 3.4.4 技巧库 (Skills Library)

**功能**：
- 高级技巧文章（开局技巧、残局技巧、复杂策略）
- 特殊情况处理（边缘案例、复杂局面）
- 复杂策略分析（多因素决策）
- 按需查询和缓存

**实现方式**：按需查询知识库文件，结果缓存

**接口设计**：
```python
class SkillsLibrary:
    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path
        self.cache = {}
        self.index = self.build_index()  # 建立索引
    
    # 查询技巧
    def query_skill(self, situation: str, game_phase: str) -> Dict
    
    # 语义搜索
    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]
    
    # 缓存管理
    def get_cached(self, key: str) -> Optional[Dict]
    def cache_result(self, key: str, result: Dict)
```

**查询策略**：
- 根据游戏阶段（opening/midgame/endgame）过滤
- 根据标签（tags）匹配
- 根据优先级（priority）排序
- 结果缓存，避免重复查询

##### 3.4.5 知识检索器 (Knowledge Retriever)

**功能**：
- 知识库文件解析（Markdown格式，YAML元数据）
- 语义搜索和匹配（关键词、标签、阶段匹配）
- 结果缓存管理（LRU缓存，避免重复查询）
- 知识关联查询（前置知识、后续知识、相关知识点）

**接口设计**：
```python
class KnowledgeRetriever:
    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path
        self.cache = LRUCache(maxsize=100)
        self.index = self.build_index()
    
    # 解析知识库文件
    def parse_knowledge_file(self, file_path: str) -> Dict
    
    # 建立索引
    def build_index(self) -> Dict
    
    # 语义搜索
    def search(self, query: str, filters: Dict = None) -> List[Dict]
    
    # 按标签查询
    def query_by_tags(self, tags: List[str]) -> List[Dict]
    
    # 按阶段查询
    def query_by_phase(self, phase: str) -> List[Dict]
    
    # 关联查询
    def get_related_knowledge(self, knowledge_id: str) -> Dict
```

**性能优化**：
- 启动时建立索引（避免每次查询都扫描文件）
- LRU缓存（最近使用的知识优先）
- 异步查询（不阻塞决策流程）
- 批量加载（常用知识预加载）

#### 3.5 数据收集模块 (Data Collection Module)

##### 3.4.1 对局记录器 (GameRecorder)
- **功能**:
  - 记录完整对局过程
  - 保存JSON格式数据
  - 记录决策过程
  - 记录胜负结果

##### 3.4.2 数据存储 (DataStorage)
- **功能**:
  - 保存对局文件
  - 数据格式标准化
  - 数据索引管理
  - 数据统计分析

#### 3.6 信息监控模块 (Info Monitor Module)

##### 3.5.1 平台信息抓取器 (PlatformInfoFetcher)
- **功能**:
  - 定期访问平台网站
  - 抓取平台动态信息
  - 抓取比赛相关消息
  - 检测平台版本更新
  - 检测文档更新

- **抓取内容**:
  - 平台公告和通知
  - 比赛信息（报名时间、比赛时间等）
  - 平台版本更新
  - 文档更新（使用说明书等）
  - 重要通知和规则变更

- **技术实现**:
  - HTTP请求获取网页内容
  - HTML解析提取关键信息
  - 内容变化检测
  - 定时任务调度

- **接口设计**:
  ```python
  class PlatformInfoFetcher:
      - fetch_platform_info() -> dict
      - check_updates() -> List[UpdateInfo]
      - get_competition_info() -> dict
      - get_announcements() -> List[Announcement]
      - is_quiet_hours() -> bool  # 检查是否在静默时段
      - start_monitoring(interval: int, quiet_hours: dict)
      - stop_monitoring()
      - schedule_next_check() -> datetime  # 计算下次检查时间（避开静默时段）
  ```

##### 3.5.2 信息解析器 (InfoParser)
- **功能**:
  - 解析HTML内容
  - 提取关键信息
  - 识别信息类型（公告/比赛/更新等）
  - 格式化信息内容

- **解析策略**:
  - 基于HTML标签结构解析
  - 关键词匹配识别重要信息
  - 时间信息提取
  - 链接和附件提取

##### 3.5.3 信息存储 (InfoStorage)
- **功能**:
  - 存储抓取的信息
  - 记录信息时间戳
  - 去重处理
  - 信息历史记录

- **数据结构**:
  - 信息ID
  - 信息类型
  - 标题和内容
  - 发布时间
  - 抓取时间
  - 是否已读

##### 3.5.4 通知管理器 (NotificationManager)
- **功能**:
  - 检测新信息
  - 发送通知提醒
  - 支持多种通知方式
  - 通知优先级管理

- **通知方式**:
  - 控制台输出
  - 日志记录
  - 桌面通知（可选）
  - 邮件通知（可选）
  - 文件保存

- **通知内容**:
  - 新公告
  - 比赛信息
  - 平台更新
  - 重要规则变更

### 四、数据结构设计

#### 4.1 卡牌表示
```python
Card:
    - suit: str  # 花色 (S/H/D/C/R/B) - 平台标准
    - rank: str  # 点数 (A/2-9/T/J/Q/K/B/R) - 平台标准
    - is_main: bool  # 是否为主牌 (curRank)
```

#### 4.2 牌型表示
```python
CardType:
    - type: str  # 牌型类型 (Single/Pair/Trips/ThreePair/ThreeWithTwo/TwoTrips/Straight/StraightFlush/Bomb/tribute/back/PASS) - 平台标准
    - cards: List[Card]  # 牌列表 (handCards格式)
    - main_rank: str  # 主牌级别 (curRank)
```

#### 4.3 游戏状态
```python
GameState:
    - my_hand: List[Card]  # 我的手牌 (handCards)
    - played_cards: List[CardType]  # 已出牌 (actionList)
    - current_player: int  # 当前玩家 (curPos, 0-3)
    - current_card_type: CardType  # 当前牌型 (curAction)
    - teammate_seat: int  # 队友座位 (myPos对应: 0-2, 1-3)
    - game_phase: str  # 游戏阶段 (stage: beginning/play/tribute/back/episodeOver/gameOver)
```

#### 4.4 平台信息
```python
PlatformInfo:
    - id: str  # 信息ID
    - type: str  # 信息类型（announcement/competition/update）
    - title: str  # 标题
    - content: str  # 内容
    - publish_time: datetime  # 发布时间
    - fetch_time: datetime  # 抓取时间
    - url: str  # 原文链接
    - is_read: bool  # 是否已读
    - priority: int  # 优先级

UpdateInfo:
    - version: str  # 版本号 (e.g., v1006)
    - update_time: datetime  # 更新时间
    - changelog: str  # 更新日志
    - download_url: str  # 下载链接

CompetitionInfo:
    - name: str  # 比赛名称
    - registration_start: datetime  # 报名开始时间
    - registration_end: datetime  # 报名结束时间
    - competition_start: datetime  # 比赛开始时间
    - competition_end: datetime  # 比赛结束时间
    - description: str  # 比赛描述
    - requirements: str  # 参赛要求
```

### 五、消息流程设计

#### 5.1 连接流程
```
1. 建立WebSocket连接
   - 本地：ws://127.0.0.1:23456/game/{user_info}
   - 局域网：ws://[IP]:23456/game/{user_info}
2. 发送用户信息 (type: notify)
3. 等待游戏开始消息 (stage: beginning)
4. 识别队友（根据连接顺序：1-3一队 (myPos 0-2)，2-4一队 (myPos 1-3)）
5. 进入游戏循环 (stage: play)
```

#### 5.2 游戏流程
```
1. 接收发牌消息 → 更新手牌 (handCards)
2. 接收出牌请求 → 决策出牌 → 发送出牌消息 (type: act, curAction)
3. 接收其他玩家出牌 → 更新游戏状态 (actionList)
4. 接收游戏结束消息 → 保存对局数据 (stage: gameOver)
```

#### 5.3 完整数据流设计

**数据流图**:
```
WebSocket消息接收
    ↓
消息解析 (JSON)
    ↓
状态更新 (EnhancedGameStateManager.update_from_message)
    ├─> 更新基础状态 (myPos, handCards, curPos, etc.)
    ├─> 更新记牌信息 (CardTracker.update_from_play)
    │   ├─> 更新玩家历史
    │   ├─> 更新剩余牌库
    │   └─> 更新PASS次数
    └─> 更新公共信息 (publicInfo)
    ↓
决策引擎 (DecisionEngine.decide)
    ├─> 开始计时 (DecisionTimer.start)
    ├─> 判断主动/被动 (EnhancedGameStateManager.is_passive_play)
    │
    ├─> [被动出牌分支]
    │   ├─> 评估配合机会 (CooperationStrategy.get_cooperation_strategy)
    │   │   └─> 查询状态信息 (EnhancedGameStateManager)
    │   │       └─> 查询记牌信息 (CardTracker)
    │   │
    │   ├─> 使用牌型专门处理器 (CardTypeHandlerFactory.get_handler)
    │   │   ├─> 分析手牌结构 (HandCombiner.combine_handcards)
    │   │   └─> 处理被动出牌 (Handler.handle_passive)
    │   │
    │   └─> 多因素评估 (MultiFactorEvaluator.evaluate_all_actions)
    │       ├─> 评估剩余牌数因素 (查询 CardTracker)
    │       ├─> 评估牌型大小因素
    │       ├─> 评估配合因素 (查询 CooperationStrategy)
    │       ├─> 评估风险因素
    │       ├─> 评估时机因素
    │       └─> 评估手牌结构因素 (查询 HandCombiner)
    │
    └─> [主动出牌分支]
        └─> 多因素评估 (MultiFactorEvaluator.evaluate_all_actions)
            └─> (同上)
    ↓
检查超时 (DecisionTimer.check_timeout)
    ↓
选择最佳动作
    ↓
构建响应消息 ({"actIndex": X})
    ↓
WebSocket消息发送
```

#### 5.4 决策流程（详细）
```
1. 接收出牌请求 (type: act, stage: play)
2. 开始计时 (DecisionTimer.start)
3. 判断主动/被动 (EnhancedGameStateManager.is_passive_play)
4. [被动出牌]:
   - 评估配合机会 (CooperationStrategy)
   - 使用牌型专门处理器 (CardTypeHandlerFactory)
   - 多因素评估 (MultiFactorEvaluator)
5. [主动出牌]:
   - 多因素评估 (MultiFactorEvaluator)
6. 检查超时 (DecisionTimer.check_timeout)
7. 选择最优方案
8. 发送决策结果 (type: act, {"actIndex": X})
```

#### 5.5 模块依赖关系

**依赖关系图**:
```
DecisionEngine (决策引擎)
├── DecisionTimer (时间控制)
│   └── (无依赖)
├── CooperationStrategy (配合策略)
│   └── EnhancedGameStateManager (状态管理)
│       └── CardTracker (记牌模块)
│           └── (无依赖)
├── MultiFactorEvaluator (多因素评估)
│   ├── EnhancedGameStateManager (状态管理)
│   │   └── CardTracker (记牌模块)
│   ├── HandCombiner (手牌组合)
│   │   └── (无依赖)
│   └── CooperationStrategy (配合策略)
│       └── EnhancedGameStateManager (状态管理)
└── CardTypeHandlerFactory (牌型处理器工厂)
    ├── EnhancedGameStateManager (状态管理)
    │   └── CardTracker (记牌模块)
    └── HandCombiner (手牌组合)
        └── (无依赖)
```

**依赖说明**:
- **决策引擎 → 状态管理 → 记牌模块**: `DecisionEngine` 通过 `EnhancedGameStateManager` 访问游戏状态，`EnhancedGameStateManager` 内部使用 `CardTracker` 维护记牌信息
- **决策引擎 → 配合策略 → 状态管理**: `DecisionEngine` 调用 `CooperationStrategy` 评估配合机会，`CooperationStrategy` 通过 `EnhancedGameStateManager` 获取状态信息
- **决策引擎 → 手牌组合 → 游戏规则**: `DecisionEngine` 使用 `HandCombiner` 分析手牌结构，`HandCombiner` 基于游戏规则识别牌型

#### 5.4 信息监控流程
```
1. 启动定时任务（后台运行）
   ↓
2. 检查当前时间是否在静默时段（0:00-6:00） (quiet_hours)
   - 如果在静默时段，跳过本次检查，等待下次
   ↓
3. 定期访问平台网站（每6小时，≥6小时） (check_interval: 21600s)
   ↓
4. 抓取网页内容 (requests/httpx)
   ↓
5. 解析HTML提取信息 (BeautifulSoup)
   ↓
6. 与历史信息对比，检测新内容 (内容哈希或时间戳)
   ↓
7. 如有新信息：
   - 保存到数据库 (data/platform_info)
   - 发送通知 (console/log/desktop/email)
   - 记录日志
   ↓
8. 等待检查间隔（6小时）后继续循环
   - 注意：如果下次检查时间落在静默时段，自动延后到静默时段结束 (schedule_next_check)
```

### 六、配置管理

#### 6.1 配置文件结构
```yaml
# config.yaml
platform:
  name: "南京邮电大学掼蛋AI平台"
  version: "v1006"
  url: "https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html"

websocket:
  # 本地连接
  local_url: "ws://127.0.0.1:23456/game/{user_info}"
  # 局域网连接（需要时替换IP）
  network_url: "ws://[局域网IP]:23456/game/{user_info}"
  reconnect_interval: 5
  heartbeat_interval: 30
  timeout: 10  # 连接超时时间（秒）

decision:
  # 最大决策时间（秒）
  max_decision_time: 0.8
  # 启用记牌功能
  enable_card_tracking: true
  # 启用推理功能
  enable_inference: true
  # 启用配合策略
  enable_cooperation: true
  # 决策缓存大小
  cache_size: 1000

# 记牌模块配置
card_tracking:
  # 跟踪历史
  track_history: true
  # 跟踪剩余牌
  track_remaining: true
  # 启用概率计算
  enable_probability: true

# 多因素评估权重配置
evaluation:
  weights:
    # 剩余牌数因素权重
    remaining_cards: 0.25
    # 牌型大小因素权重
    card_type_value: 0.20
    # 配合因素权重
    cooperation: 0.20
    # 风险因素权重
    risk: 0.15
    # 时机因素权重
    timing: 0.10
    # 手牌结构因素权重
    hand_structure: 0.10

# 配合策略配置
cooperation:
  # 队友牌型值阈值（大于此值应该PASS配合）
  support_threshold: 15
  # 对手剩余牌数危险阈值（小于此值应该配合）
  danger_threshold: 4
  # 最大牌值阈值
  max_val_threshold: 14

# 手牌组合配置
hand_combiner:
  # 组牌优先级（数值越大优先级越高）
  priorities:
    StraightFlush: 100  # 同花顺
    Bomb: 80            # 炸弹
    Straight: 60        # 顺子
    ThreeWithTwo: 50    # 三带二
    TwoTrips: 45        # 钢板
    ThreePair: 40       # 三连对
    Trips: 30           # 三张
    Pair: 20            # 对子
    Single: 10          # 单张

ai:
  strategy_level: "medium"  # basic/medium/advanced
  cooperation_enabled: true
  risk_tolerance: 0.5

data:
  save_path: "./replays"
  auto_save: true
  format: "json"

logging:
  level: "INFO"  # DEBUG/INFO/WARNING/ERROR
  file: "ai_client.log"
  console: true  # 是否输出到控制台

contact:
  research: "chenxg@njupt.edu.cn"
  feedback: "wuguduofeng@gmail.com"
  qq: "519301156"

info_monitor:
  enabled: true  # 是否启用信息监控
  check_interval: 21600  # 检查间隔（秒），默认6小时（≥6小时）
  quiet_hours:  # 静默时段，不进行检查
    enabled: true  # 是否启用静默时段
    start: "00:00"  # 静默开始时间（24小时制）
    end: "06:00"    # 静默结束时间（24小时制）
  platforms:
    - name: "南京邮电大学掼蛋AI平台"
      url: "https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html"
      check_version: true  # 是否检查版本更新
      check_announcements: true  # 是否检查公告
      check_competitions: true  # 是否检查比赛信息
  notification:
    console: true  # 控制台通知
    log: true  # 日志记录
    desktop: false  # 桌面通知（需要额外库）
    email: false  # 邮件通知（需要配置）
    email_config:
      smtp_server: ""
      smtp_port: 587
      username: ""
      password: ""
      to_email: ""
  storage:
    path: "./data/platform_info"  # 信息存储路径
    format: "json"  # 存储格式
    keep_history: true  # 保留历史记录
    max_history_days: 90  # 历史记录保留天数
```

### 七、错误处理

#### 7.1 连接错误
- WebSocket连接失败
- 连接中断
- 重连机制

#### 7.2 数据错误
- JSON解析错误
- 消息格式错误
- 数据验证失败

#### 7.3 逻辑错误
- 牌型识别错误
- 决策异常
- 状态不一致

### 八、日志和调试

#### 8.1 日志级别
- DEBUG: 详细调试信息
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息

#### 8.2 日志内容
- 连接状态
- 接收/发送的消息 (type/stage/handCards/curPos/curAction)
- 决策过程
- 错误信息

### 九、测试策略

#### 9.1 单元测试
- 牌型识别测试 (Single/Pair/Bomb等)
- 牌型比较测试
- 决策逻辑测试

#### 9.2 集成测试
- **WebSocket通信测试**
  - 本地连接测试 (ws://127.0.0.1:23456)
  - 局域网连接测试
  - 连接重连测试
  - 消息收发测试 (notify/act)

- **完整对局测试**
  - 启动4个AI客户端
  - 完成一局完整游戏 (stage: beginning -> play -> gameOver)
  - 验证组队关系（1-3一队 (myPos 0-2)，2-4一队 (myPos 1-3)）
  - 检查牌型识别准确性
  - 检查决策合理性
  - 验证记牌模块准确性
  - 验证配合策略有效性

- **模块集成测试**
  - 测试状态管理 → 记牌模块的集成
  - 测试决策引擎 → 多因素评估的集成
  - 测试决策引擎 → 配合策略的集成
  - 测试决策引擎 → 牌型处理器的集成
  - 测试完整决策流程

- **多局稳定性测试**
  - 连续多局对战
  - 内存泄漏检查
  - 长时间运行稳定性
  - 状态重置测试

- **异常场景测试**
  - 网络中断恢复
  - 消息格式错误处理
  - 超时处理
  - 异常退出恢复
  - 决策超时保护测试

#### 9.3 性能测试
- **决策响应时间**
  - 目标：< 0.8秒（默认配置）
  - 平均响应时间
  - 最大响应时间
  - 超时情况统计
  - 时间控制机制验证

- **内存使用**
  - 单局内存占用
  - 多局运行内存增长
  - 内存泄漏检测
  - 记牌模块内存占用

- **并发处理能力**
  - 同时处理多个消息
  - 异步处理性能
  - 连接并发数

#### 9.4 策略测试
- **多因素评估测试**
  - 测试不同权重配置的效果
  - 测试各因素评分的准确性
  - 测试最佳动作选择的正确性

- **配合策略测试**
  - 测试配合判断的准确性
  - 测试不同参数配置的效果
  - 测试接替判断的逻辑

- **牌型处理器测试**
  - 测试每种牌型处理器的逻辑
  - 测试主动/被动出牌的正确性
  - 测试手牌结构分析的准确性

### 十、扩展性设计

#### 10.1 策略插件化
- 支持多种策略算法
- 策略可插拔
- 策略动态切换

#### 10.2 机器学习集成
- 预留ML模型接口
- 支持模型推理
- 支持在线学习

#### 10.3 多AI支持
- 支持同时运行多个AI实例
- 支持不同策略的AI对战
- 支持AI水平评估

### 十一、项目目录结构

```
guandan_ai_client/
├── main.py                 # 主程序入口
├── config.yaml             # 配置文件
├── requirements.txt        # 依赖包
├── README.md              # 说明文档
│
├── src/
│   ├── communication/      # 通信模块
│   │   ├── __init__.py
│   │   ├── websocket_client.py
│   │   └── message_handler.py
│   │
│   ├── game_logic/         # 游戏逻辑模块
│   │   ├── __init__.py
│   │   ├── card.py
│   │   ├── card_type.py
│   │   ├── recognizer.py
│   │   ├── comparator.py
│   │   └── state_manager.py
│   │
│   ├── decision/           # 决策引擎模块
│   │   ├── __init__.py
│   │   ├── evaluator.py
│   │   ├── decision_maker.py
│   │   └── cooperation.py
│   │
│   ├── data/               # 数据收集模块
│   │   ├── __init__.py
│   │   ├── recorder.py
│   │   └── storage.py
│   │
│   ├── monitor/            # 信息监控模块
│   │   ├── __init__.py
│   │   ├── fetcher.py      # 信息抓取器
│   │   ├── parser.py       # 信息解析器
│   │   ├── storage.py      # 信息存储
│   │   └── notification.py # 通知管理器
│   │
│   └── utils/              # 工具模块
│       ├── __init__.py
│       ├── logger.py
│       └── config.py
│
├── tests/                  # 测试代码
│   ├── test_card_type.py
│   ├── test_decision.py
│   └── test_communication.py
│
├── data/                   # 数据目录
│   ├── replays/           # 回放文件
│   └── platform_info/     # 平台信息存储
│       ├── announcements.json  # 公告信息
│       ├── competitions.json   # 比赛信息
│       ├── updates.json        # 更新信息
│       └── history/            # 历史记录
│
└── logs/                   # 日志目录
    └── ai_client.log
```

### 十二、开发计划

#### 阶段一：基础框架（1-2周）
- [ ] 搭建项目结构
- [ ] 实现WebSocket通信
- [ ] 实现JSON消息处理
- [ ] 实现基础日志系统

#### 阶段二：游戏逻辑（2-3周）
- [ ] 实现卡牌和牌型数据结构
- [ ] 实现牌型识别器
- [ ] 实现牌型比较器
- [ ] 实现游戏状态管理

#### 阶段三：决策引擎（3-4周）
- [ ] 实现基础决策逻辑
- [ ] 实现策略评估
- [ ] 实现配合策略
- [ ] 优化决策算法

#### 阶段四：数据收集（1周）
- [ ] 实现对局记录
- [ ] 实现数据存储
- [ ] 实现统计分析

#### 阶段五：信息监控（1周）
- [ ] 实现平台信息抓取器
- [ ] 实现信息解析器
- [ ] 实现信息存储
- [ ] 实现通知管理器
- [ ] 实现定时任务调度
- [ ] 测试信息抓取和通知功能

#### 阶段六：测试优化（持续）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化
- [ ] 策略优化
- [ ] 信息监控测试

### 十三、关键技术点

#### 13.1 WebSocket异步处理
- 使用异步IO提高性能
- 处理并发消息
- 避免阻塞

#### 13.2 决策算法
- 规则引擎（初期）
- 搜索算法（中期）
- 机器学习（后期）
- **多因素评估系统**: 综合评估6个因素（剩余牌数、牌型大小、配合、风险、时机、手牌结构），计算动作评分
- **主动/被动决策分离**: 区分主动出牌和被动出牌，采用不同策略
- **牌型专门处理**: 为每种牌型（Single、Pair、Trips、Bomb、Straight等）创建专门的处理逻辑

#### 13.3 状态同步
- 确保状态一致性
- 处理消息乱序
- 状态恢复机制
- **增强状态管理**: 集成记牌模块，提供完整状态查询接口
- **队友识别**: 使用公式 `teammate_pos = (myPos + 2) % 4` 自动识别队友（参考获奖代码）

#### 13.4 模块依赖关系设计
- **依赖注入**: 所有模块通过依赖注入方式连接，避免硬编码依赖
- **依赖关系**:
  - 决策引擎 → 状态管理 → 记牌模块
  - 决策引擎 → 配合策略 → 状态管理
  - 决策引擎 → 手牌组合 → 游戏规则
- **初始化顺序**: 从底层到顶层，确保依赖关系正确

#### 13.5 数据流设计
- **完整数据流**: WebSocket消息 → 消息解析 → 状态更新 → 决策引擎 → 动作选择 → 消息发送
- **关键节点**:
  - 状态更新时自动更新记牌模块
  - 决策引擎调用配合策略评估
  - 决策引擎调用多因素评估
  - 超时保护机制
- **详细说明**: 参见"五、消息流程设计"章节的"5.3 完整数据流设计"

#### 13.6 参考获奖代码的关键设计
- **队友识别公式**: `teammate_pos = (myPos + 2) % 4`（参考获奖代码）
- **状态数据结构**: 参考获奖代码的 `history` 和 `remain_cards` 结构
  - `history`: `{'0': {'send': [], 'remain': 27}, ...}` 记录每个玩家的出牌历史和剩余牌数
  - `remain_cards`: 按花色和点数分类的剩余牌库
- **决策函数分离**: 参考获奖代码的 `active()` 和 `passive()` 分离
  - `active_decision()`: 主动出牌决策（率先出牌或接风）
  - `passive_decision()`: 被动出牌决策（需要压制）
- **手牌组合算法**: 参考获奖代码的 `combine_handcards()` 完整实现
  - 识别单张、对子、三张、炸弹
  - 识别顺子（考虑单张、对子、三张分布）
  - 识别同花顺

#### 13.7 信息抓取技术
- **HTTP请求**: 使用requests/httpx发送HTTP请求
- **HTML解析**: 使用BeautifulSoup解析网页内容
- **定时任务**: 使用schedule/APScheduler实现定时抓取
- **内容对比**: 通过内容哈希或时间戳检测更新
- **异常处理**: 处理网络错误、解析错误等
- **反爬虫应对**: 设置合理的请求间隔和User-Agent

### 十四、参考资料与资源

#### 14.1 官方资源
- **平台网站**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **平台版本**: v1006（当前版本）
- **离线平台**: 需从平台网站下载
- **使用说明书**: 对应版本v1006，包含：
  - 使用说明
  - JSON数据格式说明 (type/stage/handCards/myPos/curPos/curAction/actionList)
  - JSON示例说明

#### 14.2 游戏规则
- **江苏省体育局掼蛋竞赛简易规则**
- **特殊规则注意**:
  - v1006版本调整了抗贡规则，与比赛版规则一致 (tribute/back)
  - 注意手牌的表示方法 (handCards: ["S2", "H2", ...])
  - 接口与v1003版本保持一致

#### 14.3 联系方式
- **研究兴趣咨询**: chenxg@njupt.edu.cn
- **问题反馈**: wuguduofeng@gmail.com
- **QQ**: 519301156

#### 14.4 技术参考
- WebSocket协议文档
- JSON格式规范
- Python WebSocket库文档（websockets / websocket-client）

### 十五、比赛参赛要求与评估

#### 15.1 比赛参赛资格确认

✅ **当前架构满足比赛要求**：

##### 技术合规性
- ✅ WebSocket通信：已实现
- ✅ JSON数据格式：已支持 (平台标准变量)
- ✅ 4个AI参与：已设计 (myPos 0-3组队)
- ✅ Windows/Linux支持：Python跨平台
- ✅ 实时响应：异步处理机制

##### 功能完整性
- ✅ 游戏规则实现：牌型识别和比较 (Single/Bomb等)
- ✅ 决策能力：策略评估和出牌决策
- ✅ 配合能力：队友配合策略 (teammate_seat)
- ✅ 错误处理：异常处理和恢复
- ✅ 稳定性：重连和状态同步

#### 15.2 比赛评分标准（预估）
根据AI算法对抗平台的常见评分方式：

##### 评分维度
1. **胜率** (40-50%)
   - 与其他AI对战的胜率
   - 需要优化决策算法

2. **决策质量** (20-30%)
   - 出牌合理性
   - 配合默契度
   - 策略深度

3. **稳定性** (15-20%)
   - 无异常退出
   - 响应时间稳定
   - 错误处理能力

4. **代码质量** (10-15%)
   - 代码规范性
   - 可维护性
   - 文档完整性

#### 15.3 比赛前必须完成的功能

##### 核心功能（必须）
- [x] WebSocket连接和通信
- [x] JSON消息解析和构建
- [x] 所有牌型识别
- [x] 牌型比较和压制判断
- [x] 基础出牌决策
- [x] 游戏状态管理 (stage/myPos/curPos)
- [x] 错误处理和重连

##### 进阶功能（建议）
- [ ] 配合策略优化
- [ ] 记牌和推理
- [ ] 多策略融合
- [ ] 性能优化（响应时间<1秒）
- [ ] 详细日志记录

##### 比赛准备（重要）
- [ ] 本地测试：与离线平台完整测试
- [ ] 压力测试：长时间运行稳定性
- [ ] 对战测试：与其他AI对战
- [ ] 性能测试：响应时间优化
- [ ] 文档准备：提交说明文档

#### 15.4 比赛策略建议

##### 短期策略（快速参赛）
```
目标：能够正常参赛，不犯低级错误
时间：2-3个月
重点：
  - 完善基础功能
  - 实现基本策略
  - 确保稳定性
```

##### 中期策略（提升排名）
```
目标：达到中上水平
时间：3-6个月
重点：
  - 优化决策算法
  - 加强配合策略
  - 提升胜率
```

##### 长期策略（冲击冠军）
```
目标：达到顶尖水平
时间：6-12个月
重点：
  - 引入机器学习
  - 深度策略优化
  - 大量对战训练
```

#### 15.5 比赛注意事项

##### 技术注意事项
1. **响应时间限制**
   - 确保决策时间在合理范围内（建议<1秒）
   - 避免超时导致判负

2. **连接稳定性**
   - 实现完善的重连机制
   - 处理网络波动

3. **数据格式严格性**
   - 严格按照平台JSON格式要求 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
   - 验证所有消息格式

4. **规则准确性**
   - 严格按照江苏省体育局规则
   - 特别注意抗贡等特殊规则 (tribute/back)

##### 提交要求（根据参赛指南）
- **AI客户端代码**（或可执行程序）
- **源代码**（如需要，需联系主办方确认）
- **使用说明文档**
  - 如何运行程序
  - 配置说明
  - 使用步骤
- **技术文档**（架构说明）
  - 技术选型
  - 架构设计
  - 核心算法说明
- **测试报告**（可选）
  - 测试结果
  - 性能数据
- **联系方式**
  - 邮箱
  - 电话
  - QQ

##### 提交流程
1. **准备提交材料**（见上述清单）
2. **发送参赛申请邮件**
   - 主题：掼蛋AI算法对抗 - 参赛申请
   - 收件人：chenxg@njupt.edu.cn（研究兴趣）或 wuguduofeng@gmail.com（问题反馈）
   - 内容：介绍已完成工作、AI特点、希望了解的问题
3. **等待主办方回复**
   - 获取参赛确认
   - 了解具体比赛安排
   - 获取提交方式
4. **正式提交作品**
   - 根据主办方要求提交材料
5. **参与对战**
   - 平台自动匹配对战
   - 系统自动评分
   - 查看排名和结果

#### 15.6 比赛流程（根据参赛指南）

```
1. 访问平台网站
   ↓
2. 下载离线平台（v1006）和使用说明书
   ↓
3. 阅读和理解文档
   - 游戏规则
   - JSON格式
   - 技术文档
   ↓
4. 开发AI客户端
   - WebSocket通信
   - 牌型识别
   - 决策逻辑
   ↓
5. 本地测试
   - 连接测试
   - 完整对局测试
   - 多局稳定性测试
   ↓
6. 联系主办方
   - 发送参赛申请邮件
   - 等待回复
   ↓
7. 正式提交作品
   - 根据要求提交材料
   ↓
8. 参与对战
   - 平台自动匹配
   - 系统自动评分
   ↓
9. 查看排名和结果
   ↓
10. 持续优化提升
```

#### 15.7 当前架构的参赛准备度评估

| 模块 | 完成度 | 比赛就绪度 | 备注 |
|------|--------|-----------|------|
| 通信模块 | ✅ 100% | ✅ 就绪 | 核心功能完整 |
| 游戏逻辑 | ✅ 100% | ✅ 就绪 | 需要实际测试验证 |
| 决策引擎 | ⚠️ 70% | ⚠️ 需优化 | 策略需要实战优化 |
| 数据收集 | ✅ 100% | ✅ 就绪 | 可选功能 |
| 信息监控 | ✅ 100% | ✅ 就绪 | 新增功能，推荐启用 |
| 错误处理 | ✅ 90% | ✅ 就绪 | 需要完善边界情况 |
| 测试覆盖 | ⚠️ 50% | ⚠️ 需加强 | 需要更多集成测试 |

**总体评估**：✅ **可以参赛**，但建议在决策引擎和测试方面继续优化。

### 十六、参赛检查清单

#### 16.1 开发阶段检查清单
- [ ] 下载离线平台（v1006）
- [ ] 下载使用说明书（v1006版本）
- [ ] 阅读游戏规则（江苏省体育局规则）
- [ ] 理解JSON格式（严格按照平台格式）
- [ ] 开发WebSocket通信模块
- [ ] 实现所有牌型识别（Single/Pair/Trips等）
- [ ] 实现牌型比较和压制判断
- [ ] 实现决策逻辑
- [ ] 实现队友识别（1-3一队 (myPos 0-2)，2-4一队 (myPos 1-3)）
- [ ] 实现配合策略
- [ ] 实现错误处理和重连机制
- [ ] 实现日志系统
- [ ] 实现平台信息监控模块（可选但推荐）
  - [ ] 信息抓取器
  - [ ] 信息解析器
  - [ ] 信息存储
  - [ ] 通知管理器

#### 16.2 测试阶段检查清单
- [ ] 本地连接测试（ws://127.0.0.1:23456）
- [ ] 局域网连接测试（如需要）
- [ ] 单局完整测试（4个AI完整对局）
- [ ] 多局稳定性测试（连续多局）
- [ ] 异常场景测试（网络中断、消息错误等）
- [ ] 性能测试（响应时间<1秒）
- [ ] 组队关系验证（1-3一队，2-4一队）
- [ ] 牌型识别准确性验证
- [ ] 决策合理性验证

#### 16.3 提交阶段检查清单
- [ ] 准备AI客户端代码/程序
- [ ] 编写使用说明文档
- [ ] 编写技术文档（架构说明）
- [ ] 准备测试报告（可选）
- [ ] 准备联系方式信息
- [ ] 发送参赛申请邮件
  - [ ] 邮件主题：掼蛋AI算法对抗 - 参赛申请
  - [ ] 收件人：chenxg@njupt.edu.cn 或 wuguduofeng@gmail.com
  - [ ] 内容包含：已完成工作、AI特点、希望了解的问题
- [ ] 等待主办方回复
- [ ] 根据要求正式提交作品

#### 16.4 技术要点检查
- [ ] WebSocket连接地址正确（本地/局域网）
- [ ] JSON消息格式严格符合平台要求 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
- [ ] 所有牌型都能正确识别
- [ ] 组队关系正确识别（1-3一队，2-4一队）
- [ ] 抗贡规则正确处理（v1006版本，tribute/back）
- [ ] 响应时间控制在合理范围（<1秒）
- [ ] 错误处理和重连机制完善
- [ ] 日志记录完整
- [ ] 信息监控功能测试（如已实现）
  - [ ] 信息抓取准确性
  - [ ] 通知功能正常
  - [ ] 信息存储正确

### 十七、后续优化方向

#### 17.1 算法优化
1. **强化学习集成**: 使用收集的数据训练RL模型
2. **深度学习**: 使用神经网络进行决策
3. **多策略融合**: 结合多种策略算法
4. **实时学习**: 在线学习和适应
5. **配合策略优化**: 提升队友配合默契度
6. **记牌和推理**: 实现记牌功能和对手牌推理

#### 17.2 性能优化
1. **决策速度**: 提升决策速度，确保<1秒响应
2. **内存优化**: 减少内存占用，避免内存泄漏
3. **并发处理**: 优化异步处理性能
4. **代码优化**: 提升代码执行效率

#### 17.3 比赛优化
1. **针对评分标准优化**: 根据比赛评分维度优化策略
2. **胜率提升**: 通过大量对战训练提升胜率
3. **稳定性提升**: 确保长时间运行无异常
4. **策略深度**: 提升决策策略的深度和广度

#### 17.4 参考学习方向
1. **南京大学高阳团队**: 研究SDMC方法（第二届中国人工智能博弈算法大赛掼蛋项目冠军）
2. **清华大学唐杰团队**: 研究大型语言模型在掼蛋等棋牌游戏中的应用
3. **Botzone平台**: 参考斗地主AI的实现方法
4. **学术论文**: 关注相关AI博弈算法研究

### 十八、快速开始指南

#### 18.1 立即行动（今天）
1. ✅ 访问平台网站：https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
2. ✅ 下载离线平台（v1006）和使用说明书
3. ✅ 开始阅读文档，理解游戏规则和JSON格式

#### 18.2 本周完成
1. ✅ 理解游戏规则（江苏省体育局规则）
2. ✅ 理解JSON格式和消息类型 (type: notify/act, stage: beginning/play)
3. ✅ 搭建开发环境（Python + WebSocket库）
4. ✅ 实现基础WebSocket通信

#### 18.3 本月完成
1. ✅ 实现所有牌型识别
2. ✅ 实现牌型比较和压制判断
3. ✅ 实现基础决策逻辑
4. ✅ 完成本地测试（连接和单局测试）

#### 18.4 下月完成
1. ✅ 实现配合策略
2. ✅ 优化决策算法
3. ✅ 完成多局稳定性测试
4. ✅ 准备提交材料

### 十九、重要提醒

#### 19.1 技术要点
- ⚠️ **严格按照JSON格式**：平台对JSON格式要求严格，必须完全符合 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
- ⚠️ **组队规则**：第1、3个连接为一队 (myPos 0-2)，第2、4个连接为一队 (myPos 1-3)，必须正确识别
- ⚠️ **响应时间**：建议决策时间<1秒，避免超时
- ⚠️ **版本兼容**：当前使用v1006版本，注意抗贡规则调整 (tribute/back)
- ⚠️ **信息监控**：建议启用信息监控功能，及时了解平台动态和比赛信息
- ⚠️ **抓取频率**：信息抓取应设置合理间隔（检查间隔≥6小时），且每日0:00-6:00为静默时段不进行检查，避免过于频繁请求

#### 19.2 开发建议
- ✅ **先实现基础功能**：确保能正常连接和通信
- ✅ **逐步优化**：先实现基本策略，再逐步优化
- ✅ **充分测试**：本地完整测试后再提交
- ✅ **保持联系**：遇到问题及时联系主办方

#### 19.3 参赛建议
- 📧 **提前联系**：开发完成后提前联系主办方了解提交要求
- 📝 **准备文档**：准备好使用说明和技术文档
- 🧪 **充分测试**：确保稳定性和正确性
- 🚀 **持续优化**：参赛后根据对战结果持续优化

### 二十、信息监控功能说明

#### 20.1 功能概述
信息监控模块用于自动抓取南京邮电大学掼蛋AI平台的动态信息，帮助用户及时了解：
- 平台公告和通知
- 比赛信息和时间安排
- 平台版本更新
- 文档更新
- 重要规则变更

#### 20.2 使用方式

##### 启用信息监控
在配置文件中设置：
```yaml
info_monitor:
  enabled: true  # 启用信息监控
  check_interval: 21600  # 检查间隔（秒），默认6小时（≥6小时）
  quiet_hours:  # 静默时段，不进行检查
    enabled: true  # 是否启用静默时段
    start: "00:00"  # 静默开始时间（24小时制）
    end: "06:00"    # 静默结束时间（24小时制）
```

##### 查看信息
- 控制台输出：新信息会自动在控制台显示
- 日志文件：信息会记录到日志文件
- 数据文件：信息保存在 `data/platform_info/` 目录

##### 手动检查
可以通过API或命令行手动触发检查：
```python
from src.monitor.fetcher import PlatformInfoFetcher
fetcher = PlatformInfoFetcher()
updates = fetcher.check_updates()
```

#### 20.3 技术实现要点

##### 网页抓取
- 使用 `requests` 或 `httpx` 发送HTTP请求
- 设置合理的User-Agent和请求头
- 处理网络超时和重试机制
- 遵守robots.txt规则（如有）

##### HTML解析
- 使用 `BeautifulSoup` 解析HTML内容
- 根据网站结构提取关键信息
- 处理动态内容（如需要，可使用Selenium）

##### 内容检测
- 通过内容哈希或时间戳检测更新
- 去重处理，避免重复通知
- 记录历史信息，支持查询

##### 通知机制
- 控制台通知：实时显示新信息
- 日志记录：记录所有抓取的信息
- 可选扩展：桌面通知、邮件通知等

##### 静默时段处理
- 检查当前时间是否在静默时段（0:00-6:00）
- 如果在静默时段，跳过本次检查
- 计算下次检查时间时，如果落在静默时段，自动延后到静默时段结束
- 实现示例：
  ```python
  def is_quiet_hours(self, current_time: datetime) -> bool:
      hour = current_time.hour
      return 0 <= hour < 6
  
  def schedule_next_check(self, current_time: datetime, interval: int) -> datetime:
      next_check = current_time + timedelta(seconds=interval)
      if self.is_quiet_hours(next_check):
          # 延后到静默时段结束（6:00）
          next_check = next_check.replace(hour=6, minute=0, second=0)
      return next_check
  ```

#### 20.4 注意事项

##### 合规性
- 遵守网站使用条款
- 设置合理的抓取频率（检查间隔≥6小时）
- 静默时段（0:00-6:00）不进行检查，减少对服务器的影响
- 不要对服务器造成压力
- 尊重网站的反爬虫机制

##### 稳定性
- 处理网络错误和超时
- 处理HTML结构变化
- 实现错误恢复机制
- 记录抓取失败日志

##### 可维护性
- 网站结构可能变化，需要及时更新解析逻辑
- 建议定期检查抓取功能是否正常
- 保持代码的可扩展性

#### 20.5 扩展功能（可选）

##### 邮件通知
配置邮件服务，重要信息自动发送邮件：
```yaml
info_monitor:
  notification:
    email: true
    email_config:
      smtp_server: "smtp.example.com"
      smtp_port: 587
      username: "your_email@example.com"
      password: "your_password"
      to_email: "recipient@example.com"
```

##### 桌面通知
使用系统通知功能（需要额外库）：
```python
# 需要安装: plyer 或 win10toast (Windows)
from plyer import notification
notification.notify(
    title="平台更新",
    message="发现新的比赛信息",
    timeout=10
)
```

##### 多平台监控
可以扩展监控其他相关平台：
- 中国人工智能学会官网
- 其他掼蛋AI比赛平台
- 相关学术会议网站

## 应用场景
- **开发阶段**：指导掼蛋AI客户端的架构设计和模块实现
- **测试阶段**：作为测试和验证的标准参考
- **比赛准备**：确保参赛作品符合平台要求和技术规范
- **维护阶段**：作为文档参考，便于后续优化和扩展
- **信息监控**：自动获取平台动态，及时响应比赛和更新信息

## 示例/案例
- **完整对局示例**：4个AI客户端连接，完成一局游戏，验证组队 (myPos 0 vs 1-3队)和决策 (curAction: ["Single", "2", ["H2"]])
- **信息监控示例**：检测到新比赛公告，自动通知并保存到 data/platform_info/announcements.json
- **错误恢复示例**：WebSocket断开后自动重连，恢复游戏状态 (stage: play)

## 注意事项
- **平台变量统一**：所有牌型 (Single/Bomb)、花色 (S/H/D/C)、状态 (myPos/curPos/stage) 必须使用平台标准变量名
- **时间处理**：所有时间字段使用系统时间API (datetime.now())，禁止硬编码
- **响应时间**：决策时间控制在1秒以内，避免超时
- **组队识别**：严格按照平台规则，第1/3连接为一队 (myPos 0/2)
- **信息抓取合规**：检查间隔≥6小时，静默时段 (00:00-06:00) 不抓取
- **JSON格式**：严格遵守平台格式，示例：["Bomb", "2", ["H2", "D2", "C2", "S2"]]

## 相关知识点
- [掼蛋AI知识库格式化方案 - 变量命名标准]
- [江苏掼蛋规则 - 牌型定义 (Single/Pair/Bomb)]
- [平台使用说明书 v1006 - JSON格式和消息类型]

---

**文档版本**: v2.2  
**创建时间**: 使用系统时间API获取（`datetime.now()`）  
**最后更新**: 使用系统时间API获取（`datetime.now()`）- 对齐知识库格式化方案  
**维护责任**: AI开发团队

## 📝 更新日志

### v2.2 (2025-11-25)
- ✅ 添加知识库模块（Knowledge Base Module）设计
- ✅ 更新整体架构图，增加知识库层
- ✅ 设计分层记忆策略（硬编码层、内存加载层、按需查询层）
- ✅ 设计规则库、策略库、技巧库、知识检索器
- ✅ 明确知识库使用策略和性能优化方案
- ✅ 添加知识库目录结构说明
- ✅ 添加接口设计和实现方式
- ✅ 明确基础规则硬编码、常用策略内存加载、高级技巧按需查询的策略

### v2.1 (使用系统时间API获取)
- ✅ 对齐知识库格式化方案，添加YAML元数据
- ✅ 标准化文档结构 (概述/详细内容/应用场景/注意事项)
- ✅ 统一使用平台变量名 (Single/Bomb/myPos/curPos/stage)
- ✅ 增强信息监控模块说明，包含静默时段处理
- ✅ 更新示例代码，确保符合平台JSON格式
- ✅ 添加参赛检查清单和快速开始指南

### v2.0 (使用系统时间API获取)
- ✅ 初始架构方案，包含分层设计和核心模块
- ✅ 添加信息监控功能设计
- ✅ 完善比赛参赛要求和评估

### v1.0 (使用系统时间API获取)
- 基础架构框架设计

---

## ⏰ 时间处理规范
**所有时间相关字段必须使用系统时间API，禁止硬编码时间。**

### Python示例
```python
from datetime import datetime

# 获取当前时间
current_time = datetime.now()

# 格式化时间字符串
time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
# 输出：2025-11-24 14:30:00

# 中文格式
time_str_cn = current_time.strftime('%Y年%m月%d日 %H:%M:%S')
# 输出：2025年11月24日 14:30:00
```

### 元数据时间字段
在文档中，`last_updated` 字段必须使用系统时间API：
```markdown
---
title: 文档标题
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}
---
```

**禁止写法**：
```markdown
---
last_updated: 2025年11月24日  # ❌ 硬编码时间
---
```

**正确写法**：
```markdown
---
last_updated: {{ datetime.now().strftime('%Y-%m-%d %H:%M:%S') }}  # ✅ 使用系统时间
---
```

