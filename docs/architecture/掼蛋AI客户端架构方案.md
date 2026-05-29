---
title: 掼蛋AI客户端基础架构方案
type: architecture
category: System/Architecture
source: 掼蛋AI客户端架构方案.md
version: v2.7
last_updated: 2026-05-29
tags: [架构, 客户端, WebSocket, 决策引擎, 信息监控, 知识库, 动作空间优化, 特征编码, 知识应用框架]
difficulty: 高级
priority: 5
game_phase: 全阶段
---

# 掼蛋AI客户端基础架构方案

> 本文档为 UTF-8 编码。若再次出现乱码，请用编辑器「以 UTF-8 重新打开/保存」，或运行 `python scripts/tools/fix_doc_encoding.py`。

## 概述
本文档提出掼蛋AI客户端的基础架构方案，旨在开发符合南京邮电大学掼蛋AI平台的客户端，实现 AI 自动出牌决策，支持自我对弈和数据收集，提供可扩展的架构设计。

**目标**：
- 开发符合南京邮电大学掼蛋AI平台的客户端
- 实现 AI 自动出牌决策
- 支持自我对弈和数据收集
- 可扩展的架构设计

## M/V 系列物理目录与契约（m-dev，2026-05-29）

自 [M-V 系列治理方案](../governance/M-V-Series-治理方案.md) 落地后，代码按 **M 底座 / V 智能体 / 契约** 三层组织；与本文「逻辑分层」（通信、决策、知识等）正交——逻辑层实现可分布在 `src/m/`、`src/v/` 与兼容 shim 中。

### 目录对照

| 路径 | 层级 | 说明 |
|------|------|------|
| [`src/contracts/`](../../src/contracts/README.md) | 契约 | `IDecisionProvider` **v1.0**（`DECISION_PROVIDER_CONTRACT_VERSION`）；V 挂接门禁 `V_INTEGRATION_GATE_ENABLED=True` |
| [`src/m/platform/`](../../src/m/README.md) | M · 平台 | 通信、记录、WebSocket、常量等（re-export 既有 `communication` / `game_logic` 能力） |
| [`src/m/m1/`](../../src/m/README.md) | M · m1 | 阶段路由、规则引擎 M1、阶段处理器（**当前对战 lalala 主迭代**） |
| [`src/m/m2/`](../../src/m/README.md) | M · m2 | M2 引擎与阶段处理器（依赖 `m.m1.stage_router`） |
| [`src/m/m3/`](../../src/m/README.md) | M · m3 | M3 / lalala 移植、`M3DecisionProvider` |
| [`src/v/learn/`](../../src/v/README.md) | V · 自学 | V4 / V5 / Stage5 混合决策引擎 |
| [`src/v/nn/`](../../src/v/README.md) | V · 神经网络 | V7 胜率引擎等 |
| [`src/decision/`](../../src/decision/) | 兼容 | 迁移期 **shim**，指向 `m.m1.*` / `v.learn.*` / `v.nn.*`；新代码勿再依赖 |

客户端入口仍可使用历史文件名（如 `yf1_m1.py`、`yf1_v5.py`），内部 import 应逐步改为 `m.*` / `v.*` / `contracts.*`。

### 依赖规则（摘要）

- **V 允许依赖**：`contracts.*`、`m.platform.*`、`v.learn.*`、`v.nn.*`
- **V 禁止**：直达 `decision.rule_based_decision_engine_m1` 等 M 实现；禁止新增对 `src/decision/` shim 的依赖
- **M 不被 V 破坏**：平台 JSON、`actIndex` 响应、记牌与状态契约保持稳定

### 测试与版本矩阵

```bash
pytest tests/test_m3_contracts_layout.py tests/test_v_integration_gate.py
```

分支、冒烟与 deprecated 客户端见 [docs/versions/MATRIX.md](../versions/MATRIX.md)。改契约前须在 `docs/guandan-brain/ITERATIONS.md` 登记。

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
- **4 个 AI 同时参与**：第 1、3 号连接为一队，第 2、4 号连接为另一队
- **支持 Windows / Linux 环境**

### 二、系统架构设计

#### 2.1 整体架构（分层设计）

```
├──││││││││││││││││││││││││││││││││││││
│        应用层 (Application)         │
│  - 主程序入口                       │
│  - 配置管理                         │
│  - 日志管理                         │
└──││││││││││││││││││││││││││││││││││││
          ↓
├──││││││││││││││││││││││││││││││││││││
│    信息监控层 (Info Monitor)        │
│  - 平台动态抓取                     │
│  - 比赛消息监控                     │
│  - 信息通知                         │
└──││││││││││││││││││││││││││││││││││││
          ↓
├──││││││││││││││││││││││││││││││││││││
│      决策层 (Decision Engine)        │
│  - 策略评估                         │
│  - 出牌决策                         │
│  - 配合策略                         │
│  - 知识库查询                       │
└──││││││││││││││││││││││││││││││││││││
          ↓
├──││││││││││││││││││││││││││││││││││││
│      知识库层 (Knowledge Base)       │
│  - 规则库（硬编码）                 │
│  - 策略库（内存加载）               │
│  - 技巧库（按需查询）               │
│  - 知识检索与缓存                   │
└──││││││││││││││││││││││││││││││││││││
          ↓
├──││││││││││││││││││││││││││││││││││││
│      逻辑层 (Game Logic)             │
│  - 游戏规则                         │
│  - 牌型识别                         │
│  - 牌型比较                         │
│  - 状态管理                         │
└──││││││││││││││││││││││││││││││││││││
          ↓
├──││││││││││││││││││││││││││││││││││││
│      通信层 (Communication)         │
│  - WebSocket连接                    │
│  - JSON解析/构建                    │
│  - 消息路由                         │
└──││││││││││││││││││││││││││││││││││││
          ↓
├──││││││││││││││││││││││││││││││││││││
│      数据层 (Data Layer)             │
│  - 对局记录                         │
│  - 数据存储                         │
│  - 统计分析                         │
│  - 平台信息存储                     │
└──││││││││││││││││││││││││││││││││││││
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
  - `{user_info}` 为用户信鎭标识

- **接口璁捐**:
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
  - 解析平台鍙戦佺殑JSON消息
  - 构建鍙戦佺粰平台的JSON消息
  - 消息格式验证
  - 消息类型璺用

- **消息类型**:
  - 游戏寮始消息
  - 发牌消息
  - 出牌请求消息
  - 游戏鐘舵佹洿新消息
  - 游戏结束消息

#### 3.2 游戏逻辑模块 (Game Logic Module)

##### 3.2.1 牌型识别鍣 (CardTypeRecognizer)
- **功能**:
  - 识别所有掼蛋牌鍨
  - 严格按照平台JSON格式要求
  - 支持主牌识鍒

- **牌型涓英文对照**（平台标准）:
  - **Single** -- 单张 (Single)
  - **Pair** -- 对子 (Pair)
  - **Trips** -- 三张 (Trips)
  - **ThreePair** -- 三连瀵 (ThreePair)
  - **ThreeWithTwo** -- 三带浜 (ThreeWithTwo)
  - **TwoTrips** -- 钢板（两涓三张： (TwoTrips)
  - **Straight** -- 顺子 (Straight)
  - **StraightFlush** -- 同花顺（特殊顺子： (StraightFlush)
  - **Bomb** -- 炸弹 (Bomb)

- **特殊规则**:
  - v1006版本调整了抗璐¤勫垯，与比赛鐗堣勫垯涓鑷
  - 注意手牌的表示方娉
  - 接口与v1003版本保持涓鑷

##### 3.2.2 牌型比较鍣 (CardTypeComparator)
- **功能**:
  - 比较牌型大小
  - 判断鏄否可以压鍒
  - 判断牌型合法鎬

##### 3.2.3 增强游戏状态管理器 (EnhancedGameStateManager)
- **功能**:
  - 维护完整的游戏状态信鎭
  - 集成记牌模块
  - 提供鐘舵佹煡询接鍙
  - 支持状态快照和鎭㈠
  - **识别队友关系**（重要）

- **组队规则**（平台拌勫垯：:
  - **绗1涓鍜岀3涓连接**的AI自动为涓闃 (myPos: 0鍜2)
  - **绗2涓鍜岀4涓连接**的AI自动为涓闃 (myPos: 1鍜3)
  - 队友识别鍏寮: `teammate_pos = (myPos + 2) % 4`（参考获奖代码）

- **出牌顺序**（平台实际实现）:
  - 根据平台使用说明：`order` 瀛楁佃〃示完鐗屾″簭：堝 `[0, 1, 2, 3]`），代表出牌顺序
  - 根据一等奖代码实现：`numofnext = (myPos+1)%4`（下家），`numofpre = (myPos-1)%4`（上家）
  - **平台实际出牌顺序**：**0 ↓ 1 ↓ 2 ↓ 3 ↓ 0...**（顺时针：
  - **位置关系计算鍏寮**：
    - 涓嬪朵綅缃：`(myPos + 1) % 4`
    - 涓婂朵綅缃：`(myPos - 1) % 4`
    - 瀵瑰朵綅缃：`(myPos + 2) % 4`（队友）
  - **閲嶈佽说明**：虽然江苏掼蛋规则绗240鏉¤"出牌浠ラ嗘椂针为搴"，但平台实际实现为顺时针顺序。应以平台实现为鍑嗐

- **鐘舵佷俊鎭**:
  - 当前手牌列表 (handCards)
  - 已出牌历鍙
  - 当前出牌鐜╁ (curPos)
  - 当前牌型 (curAction)
  - 游戏闃舵 (stage)
  - 队友座位鍙
  - 对手座位鍙
  - 主牌级别 (curRank)
  
- **增强功能**:
  - 鐜╁跺巻鍙茶板綍（history：: 每个鐜╁舵墦出的牌和剩余牌数
  - 牌库鐘舵侊紙remain_cards：: 按花色和点数分类的剩余牌
  - 游戏进度鐘舵: 连续PASS次数（pass_num, my_pass_num：
  - 配合鐘舵: 队友位置识别、队友出牌意图分鏋
  
- **鐘舵佹煡询接鍙**:
  - `is_passive_play()`: 判断鏄鍚﹁动出鐗
  - `is_active_play()`: 判断鏄否主动出鐗
  - `is_teammate_action()`: 判断鏄否是队友出的鐗
  - `get_player_remain_cards()`: 获取鐜╁跺剩余牌鏁
  - `get_teammate_remain_cards()`: 获取队友剩余牌数
  - `get_opponent_remain_cards()`: 获取对手剩余牌数
  - `get_pass_count()`: 获取PASS次数
  - `get_state_summary()`: 获取鐘舵佹憳瑕

#### 3.3 决策引擎模块 (Decision Engine Module)

##### 3.3.1 多因素评估系统 (MultiFactorEvaluator)
- **功能**:
  - 综合评估多个因素
  - 计算动作的综合评鍒
  - 支持权重调鏁
  
- **评估因素**：6涓因素，权重可调）:
  1. **剩余牌数因素** (25%): 考虑鑷宸便侀槦鍙嬨佸规墜的剩余牌鏁
  2. **牌型大小因素** (20%): 评估牌型大小和压制能鍔
  3. **配合因素** (20%): 评估配合机会和配合效鏋
  4. **风险因素** (15%): 评估出牌风险
  5. **时机因素** (10%): 评估游戏闃舵靛拰时机
  6. **手牌结构因素** (10%): 评估对手牌结构的影响

- **接口璁捐**:
  ```python
  class MultiFactorEvaluator:
      def evaluate_action(self, action, action_index, cur_action, action_list) -> float
      def evaluate_all_actions(self, action_list, cur_action) -> List[Tuple[int, float]]
      def get_best_action(self, action_list, cur_action) -> int
      def update_weights(self, weights: Dict[str, float])
  ```

##### 3.3.2 策略评估鍣 (StrategyEvaluator)
- **功能**:
  - 评估当前灞闈
  - 评估手牌浠峰
  - 评估出牌风险
  - 评估配合机会

##### 3.3.3 出牌决策鍣 (PlayDecisionMaker)
- **功能**:
  - 生成鍊欓夊嚭牌方妗
  - 评估每个方案堢殑浠峰
  - 选择鏈优出鐗
  - 决定鏄否过鐗 (PASS)
  - **主动/琚动决策分绂**:
    - `active_decision()`: 主动出牌决策（率先出牌或鎺ラ庯級
    - `passive_decision()`: 琚动出牌决策（闇要压制）

##### 3.3.4 配合策略鍣 (CooperationStrategy)
- **功能**:
  - 识别队友意图
  - 判断鏄否需要配鍚
  - 制定配合策略
  - 评估配合效果
  
- **详细实现**:
  - `should_support_teammate()`: 判断鏄否应该配合队友（PASS让队友继缁：
  - `should_take_over()`: 判断鏄否应该接替队鍙
  - `evaluate_cooperation_opportunity()`: 评估配合机会
  - `get_cooperation_strategy()`: 获取配合策略寤鸿
  
- **配合策略参数**（可配置：:
  - `support_threshold`: 队友牌型值阈值（榛樿15：
  - `danger_threshold`: 对手剩余牌数危险闃堝硷紙榛樿4：
  - `max_val_threshold`: 鏈大牌值阈值（榛樿14：

##### 3.3.5 决策时间控制鍣 (DecisionTimer) / 鑷适应决策时间控制鍣 (AdaptiveDecisionTimer)
- **功能**:
  - 设置鏈大决策时间（榛樿0.8秒）
  - 超时妫测和保护机制
  - 渐进式决策支鎸
  - 装饰器支持（`@with_timeout`：
  - **鑷适应时间分配**（新增）:
    - 根据动作空间大小鍔ㄦ佽皟整评估深搴
    - 大动作空间：鏇村氭椂间用于快速筛閫
    - 小动作空间：鏇村氭椂间用于精细评浼

- **接口璁捐**:
  ```python
  class AdaptiveDecisionTimer:
      def get_time_budget(self, action_count: int) -> Dict[str, float]
      def start(self)
      def check_timeout(self) -> bool
      def get_remaining_time(self) -> float
  ```

##### 3.3.6 动作空间优化鍣 (ActionSpaceOptimizer)
- **功能**:
  - 根据动作空间大小鍔ㄦ佺瓫閫夊欓夊姩浣
  - 大动作空间（>100）：快速筛选Top-K鍊欓
  - 小动作空间（鈮100）：精细评估所有动浣
  - 提升决策效率，避免在大动作空间下评估鎵鏈夊欓

- **璁捐℃濊矾**：堝熼壌DanZero+论文：:
  - 掼蛋游戏鍒濆嬬姸态可鑳>5000合法动作，后期可鑳<50
  - 大动作空间需要快速筛选，小动作空间可以精细评浼
  - 使用鍚发式规则快速评估，保留Top-K鍊欓

- **接口璁捐**:
  ```python
  class ActionSpaceOptimizer:
      def filter_actions(self, action_list: List, game_state: GameState) -> List
      def _fast_filter(self, action_list: List, game_state: GameState) -> List
      def _quick_evaluate(self, action: List, game_state: GameState) -> float
  ```

- **配置参数**:
  - `large_space_threshold`: 大动作空间阈值（榛樿100：
  - `candidate_ratio`: 鍊欓夊姩作比例（榛樿0.1，即10%：
  - `min_candidates`: 鏈灏忓欓夋暟量（榛樿10：

##### 3.3.7 动作特征编码鍣 (ActionFeatureEncoder)
- **功能**:
  - 将动作编码为特征向量
  - 提取动作的关閿特征（牌鍨嬨佸ぇ灏忋佷富鐗屻佺櫨鎼牌等：
  - 支持快速评估和相似搴﹁＄畻
  - 为未来强鍖栧︿範集成做准澶

- **璁捐℃濊矾**：堝熼壌DanZero+论文的DMC方法：:
  - DMC方法利用动作特征杩涜屾棤偏估璁
  - 结构化特征表示提升评估效鐜
  - 考虑掼蛋特色（花色重瑕佹с佺櫨鎼鐗屻佺骇牌）

- **特征维度**:
  1. **牌型类型特征**（One-hot编码：: Single/Pair/Trips/ThreePair/ThreeWithTwo/TwoTrips/Straight/StraightFlush/Bomb
  2. **牌型大小特征**: 归一化的牌型大小鍊
  3. **主牌数量特征**: 使用的主牌（级牌）数閲
  4. **百搭牌数量特寰**: 使用的百鎼牌（红心级牌）数閲
  5. **手牌结构影响特征**: 出牌后手牌结构变鍖
  6. **压制能力特征**: 对当前牌型的压制能力

- **接口璁捐**:
  ```python
  class ActionFeatureEncoder:
      def encode_action(self, action: List, game_state: GameState) -> np.ndarray
      def _encode_card_type(self, card_type: str) -> List[float]
      def _encode_rank(self, rank: str, cur_rank: str) -> float
      def _encode_special_cards(self, cards: List[str], game_state: GameState) -> List[float]
      def _encode_hand_structure_impact(self, action: List, game_state: GameState) -> List[float]
  ```

##### 3.3.8 状态特征编码器 (StateFeatureEncoder)
- **功能**:
  - 将游戏状态编码为特征向量
  - 提取鐘舵佺殑关键信息（手鐗屻佸巻鍙层佺帺家状态等：
  - 支持状态相似度计算和模式识鍒
  - 为未来强鍖栧︿範集成做准澶

- **璁捐℃濊矾**：堝熼壌DanZero+论文的特征编码技术：:
  - 使用特征编码鎶鏈处理鐘舵佸拰动作
  - 考虑花色閲嶈佹э紙掼蛋特色：
  - 处理百搭牌和级牌的特娈婃
  - 结构化状态表绀

- **特征维度**:
  1. **手牌特征**：27维）: 每张牌的存在性（考虑花色和点数）
  2. **已出牌历史特寰**: 各玩家出牌历史统璁
  3. **鐜╁跺剩余牌数特寰**：4维）: 每个鐜╁剁殑剩余牌数
  4. **当前牌型特征**: 当前闇要压制的牌型信息
  5. **游戏闃舵电壒寰**: 游戏闃舵碉紙beginning/play/tribute/back等）
  6. **级牌和百鎼牌特寰**: 当前级牌和百鎼牌信鎭
  7. **配合鐘舵佺壒寰**: 队友鐘舵併侀厤合机会等

- **接口璁捐**:
  ```python
  class StateFeatureEncoder:
      def encode_state(self, game_state: GameState) -> np.ndarray
      def _encode_hand_cards(self, hand_cards: List[str], cur_rank: str) -> List[float]
      def _encode_play_history(self, history: Dict) -> List[float]
      def _encode_player_states(self, game_state: GameState) -> List[float]
      def _encode_current_action(self, cur_action: List) -> List[float]
      def _encode_game_phase(self, stage: str) -> List[float]
      def _encode_special_cards(self, game_state: GameState) -> List[float]
  ```

##### 3.3.9 牌型专门处理鍣 (CardTypeHandlers)
- **功能**:
  - 为每种牌型创建专门的处理绫
  - 实现閽堝规х殑决策逻辑
  - 支持主动和琚动两种出牌模寮
  
- **已实现的处理鍣**:
  - `SingleHandler`: 单张专门处理
  - `PairHandler`: 对子专门处理
  - `TripsHandler`: 三张专门处理
  - `BombHandler`: 炸弹专门处理
  - `StraightHandler`: 顺子专门处理
  
- **璁捐℃ā寮**:
  - 使用抽象基类 `BaseCardTypeHandler` 定义统一接口
  - 通过工厂模式 `CardTypeHandlerFactory` 获取处理鍣

#### 3.4 知识库模鍧 (Knowledge Base Module)

**与知识库格式化方妗堝归綈**：
- 鉁 鏈模块设计笌《知识库格式化方妗.md》完鍏ㄥ归綈
- 鉁 知识分类体系对应格式化方案的涓级分类（规则/基础/策略/鎶宸/心理：
- 鉁 鐩录结鏋勫瑰簲格式化方案的`docs/knowledge/`目录曡捐
- 鉁 变量命名统一使用平台标准变量名（Single/Pair/Bomb等）
- 鉁 知识检索方寮忓瑰簲格式化方案的鏌ヨ㈡帴鍙ｈ捐

##### 3.4.1 知识库架构设计捐

**分层记忆策略**（基浜庢ц兘和使用ㄩ戠巼：屽瑰簲知识库格式化方案級：

1. **纭编码层（Hardcoded Rules：**
   - **鍐呭**：基础规则（牌型定涔夈佸帇鐗岃勫垯、大小关系等：
   - **实现方式**：直接写在代码中，作为函鏁/类方娉
   - **访问方式**：O(1)直接调用
   - **更新方式**：代码修鏀
   - **示例**：
     ```python
     class GameRules:
         CARD_TYPES = ['Single', 'Pair', 'Trips', ...]
         def can_beat(self, card1, card2): ...
         def is_valid_type(self, cards): ...
     ```

2. **内存加载层（In-Memory Knowledge：**
   - **鍐呭**：常用策略和鎶巧（组牌鎶宸с侀厤鐏原则、常见策略模式）
   - **实现方式**：程序启动时加载到内存（字典/对象：
   - **访问方式**：O(1)内存访问
   - **更新方式**：重鍚程序或热更新
   - **示例**：
     ```python
     class KnowledgeBase:
         def __init__(self):
             self.grouping_priorities = self.load_grouping_rules()
             self.strategy_patterns = self.load_strategies()
     ```

3. **按需鏌ヨ㈠眰（On-Demand Query：**
   - **鍐呭**：高级技巧和特殊情况：堝嶆潅策略、边缂樻堜緥：
   - **实现方式**：需要时鏌ヨ㈢煡识库文件，结果缓瀛
   - **访问方式**：氶栨O(n)鏌ヨ，后续O(1)缓存访问
   - **更新方式**：知识库文件更新，缓存失鏁
   - **示例**：
     ```python
     class KnowledgeQuery:
         def __init__(self):
             self.cache = {}
         def query_advanced_skill(self, situation): ...
     ```

**知识库目录结鏋**：堝归綈知识库格式化方案級：
```
docs/knowledge/
├─│ rules/              # 规则知识（硬编码层）- 对应规则库（鏈高准则）
│   ├─│ 01_basic_rules/      # 基础规则（整合了原basics鐩录的鍐呭癸級
│   │   ├─│ 01_card_types.md          # 牌型定义
│   │   ├─│ 01_card_types_guide.md    # 牌型指南
│   │   ├─│ 02_card_distribution.md    # 牌张分配
│   │   ├─│ 03_game_flow.md            # 游戏流程
│   │   ├─│ 04_upgrade_rules.md        # 升级规则
│   │   ├─│ 05_game_introduction.md    # 游戏介绍
│   │   ├─│ 06_basic_concepts.md       # 基本概念
│   │   ├─│ 07_quick_start.md          # 快速入闂
│   │   ├─│ 08_basic_strategy.md       # 基础策略
│   │   └── 09_practice_tips.md        # 练习寤鸿
│   ├─│ 02_competition_rules/ # 比赛规则
│   └── 03_advanced_rules/    # 进贡报牌规则
└── skills/              # 鎶巧知识（按需鏌ヨ㈠眰：- 对应技巧库
    ├─│ 01_foundation/        # 基础鎶宸
    ├─│ 02_main_attack/       # 主攻鎶宸
    ├─│ 03_assist_attack/     # 助攻鎶宸
    ├─│ 04_common_skills/     # 通用鎶宸
    ├─│ 05_psychology/        # 心理知识
    ├─│ 06_advanced/          # 高级鎶宸
    ├─│ 07_opening/          # 寮灞鎶宸
    └── 08_endgame/          # 残局鎶宸
```

**说明**：
- `rules/` 对应"规则搴 (Rules Library)"，实现为纭编码层，鏄规则知识的最高准鍒
- 鍘 `basics/` 鐩录已整合鍒 `rules/01_basic_rules/` 鐩录中，不再单鐙存在
- `skills/` 对应"技巧库 (Skills Library)"，实现为按需鏌ヨ㈠眰
- 策略知识（Strategy：夊瑰簲"策略搴 (Strategy Library)"，实现为内存加载层，通常不存储在文件系统涓：岃屾槸程序鍚动时从配缃或代码中加载

##### 3.4.2 规则搴 (Rules Library)

**功能**：
- 牌型定义和识鍒规则（`Single`, `Pair`, `Trips`, `ThreePair`, `ThreeWithTwo`, `TwoTrips`, `Straight`, `StraightFlush`, `Bomb`：
- 压牌规则和大小关系（同牌型比杈冦佺偢弹压鐗屻佸悓花顺压牌：
- 进贡规则和升绾ц勫垯：堟ｅ父进贡、双下进璐°佸崌级条件）
- 游戏流程规则（局、场、轮的定义）

**实现方式**：硬编码到`GameRules`类中

**接口璁捐**：
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

##### 3.4.3 策略搴 (Strategy Library)

**功能**：
- 组牌鎶巧和优先级（同花椤 > 炸弹 > 顺子/三带二）
- 常用策略模式（主攻策鐣ャ佸姪攻策略）
- 寮灞、中灞、残灞策略
- 配火原则（四头火、宜配中小不配大：

**实现方式**：启动时加载到内瀛

**接口璁捐**：
```python
class StrategyLibrary:
    def __init__(self):
        # 鍚动时加载
        self.grouping_priorities = self.load_grouping_priorities()
        self.strategy_patterns = self.load_strategy_patterns()
    
    # 组牌优先绾
    def get_grouping_priority(self) -> Dict[str, int]
    
    # 配火原则
    def get_bomb_grouping_rules(self) -> Dict
    
    # 策略模式匹配
    def match_strategy_pattern(self, situation: Dict) -> List[str]
```

**加载鍐呭**：
- 组牌优先绾ц勫垯（同花顺 > 炸弹 > 顺子/三带二）
- 配火原则（四头火、宜配中小不配大、破二炸弹不能搭：
- 百搭使用原则：堥勭暀3涓配百鎼、百鎼閰3放后压）
- 去单化原则（鏃犺哄皬与大，坚持去单化：

##### 3.4.4 技巧库 (Skills Library)

**功能**：
- 高级鎶巧文章（寮灞鎶宸с佹畫灞鎶宸с佸嶆潅策略：
- 特殊情况处理（边缂樻堜緥銆佸嶆潅灞闈：
- 复杂策略分析：堝氬洜素决策）
- 按需鏌ヨ㈠拰缓存

**实现方式**：按闇鏌ヨ㈢煡识库文件，结果缓瀛

**对应知识库格式化方案**：
- 对应格式化方案的"鎶巧知璇 (Skills)"鍜"心理知识 (Psychology)"
- 知识库文件存储在`docs/knowledge/skills/`鐩录下
- 文件格式遵循格式化方案的Markdown模板（含YAML元数据：
- 支持按游戏闃舵碉紙opening/midgame/endgame）过滤查璇

**接口璁捐**：
```python
class SkillsLibrary:
    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path
        self.cache = {}
        self.index = self.build_index()  # 建立索引
    
    # 鏌ヨ㈡妧宸
    def query_skill(self, situation: str, game_phase: str) -> Dict
    
    # 璇义搜绱
    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]
    
    # 缓存管理
    def get_cached(self, key: str) -> Optional[Dict]
    def cache_result(self, key: str, result: Dict)
```

**鏌ヨ㈢瓥鐣**：
- 根据游戏闃舵碉紙opening/midgame/endgame）过婊
- 根据鏍囩撅紙tags）匹閰
- 根据优先级（priority）排搴
- 结果缓存，避免重复查璇

##### 3.4.5 知识检索器 (Knowledge Retriever)

**功能**：
- 知识库文件解析（Markdown格式，YAML元数据：
- 璇义搜索和匹配（关閿璇嶃佹爣绛俱侀樁段匹配）
- 结果缓存管理（LRU缓存，避免重复查璇：
- 知识关联鏌ヨ（前缃知识、后缁知识、相关知识点：

**对应知识库格式化方案**：
- 解析格式化方案定义的Markdown文档（含YAML元数据：
- 支持按格式化方案的分类体系鏌ヨ（Rules/Basics/Skills/Psychology：
- 支持按格式化方案的鏍囩撅紙tags）和游戏闃舵碉紙game_phase）过婊
- 支持按格式化方案的优先级（priority）和难度（difficulty）排搴

**接口璁捐**：
```python
class KnowledgeRetriever:
    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path
        self.cache = LRUCache(maxsize=100)
        self.index = self.build_index()
    
    # 解析知识库文浠
    def parse_knowledge_file(self, file_path: str) -> Dict
    
    # 建立索引
    def build_index(self) -> Dict
    
    # 璇义搜绱
    def search(self, query: str, filters: Dict = None) -> List[Dict]
    
    # 按标签查璇
    def query_by_tags(self, tags: List[str]) -> List[Dict]
    
    # 按阶段查璇
    def query_by_phase(self, phase: str) -> List[Dict]
    
    # 关联鏌ヨ
    def get_related_knowledge(self, knowledge_id: str) -> Dict
```

**性能优化**：
- 鍚动时建立索引（避免每次查询都鎵描文件）
- LRU缓存（最近使用的知识优先：
- 寮傛ユ煡璇（不闃诲炲喅策流程）
- 批量加载（常用知璇嗛勫姞载）

##### 3.4.6 知识应用框架 (Knowledge Application Framework)

**闂题背鏅**：
我们已经整理浜17涓知识文件，包鍚绾850涓知识点（核心原则50鏉°佺瓥鐣ヨ勫垯200鏉°佹妧宸ц佺偣500鏉°佹堜緥示例100涓：夈傝繖些知璇嗗傛灉熟练运用，可以打璐85%以上鐨勫规墜。但闂题是：**这么多知识，掼蛋AI怎么熟练掌握鍛：**

**知识规模缁熻**：
- **已格式化知识文件**：17涓
  - 基础类：2涓（原鍒欍佹垬略）
  - 主攻类：1涓（炸弹技巧）
  - 助攻类：1涓（传牌技巧）
  - 通用鎶巧类：11涓：堝瑰瓙、牌璇、相生相鍏嬨佺畻鐗屻佽扮墝、红桃配、钢鏉裤侀『瀛愩佷笁杩炲广佷笁带二、三张）
  - 寮灞类：2涓：堥栧彂瑙ｈ汇佺粍牌技巧）
- **知识点数閲**：约850涓
  - 核心原则：约50鏉
  - 策略规则：约200鏉
  - 鎶宸ц佺偣：约500鏉
  - 案例示例：约100涓

**知识灞傛＄粨鏋**：堝瑰簲分层记忆策略）：

```
知识灞傛
├─│ L1: 纭编码规则（必须遵守）- 对应纭编码灞
│   ├─│ 游戏规则（出鐗岃勫垯、牌型定义）
│   ├─│ 平台接口规范
│   └── 基础约束：堝"鐏不打鍥"銆"进贡慎出鍗"：
│
├─│ L2: 核心策略（高频使用：- 对应内存加载灞
│   ├─│ 组牌原则（炸弹越多越好，单牌越少越好：
│   ├─│ 角色定位（主鏀/助攻判断：
│   └── 牌力评估：8分以上主攻，2-4分助攻）
│
├─│ L3: 场景策略（按闇匹配：- 对应按需鏌ヨ㈠眰
│   ├─│ 寮灞策略：堥栧彂瑙ｈ汇佺粍牌技巧）
│   ├─│ 涓灞策略（相生相鍏嬨佺畻鐗岃扮墝：
│   └── 残局策略（传牌技宸с佸嚭炸技巧）
│
└── L4: 高级鎶巧（深度应用：- 对应按需鏌ヨ㈠眰
    ├─│ 鐗岃瑙ｈ伙紙判断对手牌力：
    ├─│ 相生相克（反打策略）
    └── 心理战术：堣遍獥、守鏍待兔：
```

**知识应用方案細分层决策系统**

**核心思想**：将知识分层，不同层次采用不同的应用方式銆

**1. 纭编码层（L1规则：**

**实现方式**：直接写在代码中，作为基础约束銆

```python
# src/core/game_rules.py
class GameRules:
    """纭编码的游鎴忚勫垯"""
    
    # 基础规则
    MAX_HAND_CARDS = 27
    MIN_STRAIGHT_LENGTH = 5
    MIN_BOMB_COUNT = 4
    
    # 高压绾胯勫垯（必须遵守）
    def check_high_voltage_rules(self, action, game_state):
        """妫查五条高压线"""
        # 1. 进贡慎出鍗
        if game_state.stage == "tribute" and action.type == "Single":
            return False, "进贡慎出鍗"
        
        # 2. 鐏不打鍥
        if opponent_remain == 4 and action.type == "Bomb":
            return False, "鐏不打鍥"
        
        # 3. 尽量避免涓打二
        # 4. 不打赌气鐗
        # 5. 顺子鎱庡嬪彂
        return True, None
```

**特点**：
- 鉁 鎵ц屾晥率最高（O(1)：
- 鉁 100%准确，不会出閿
- 鉁 作为所有决策的基础约束

**2. 策略引擎层（L2核心策略：**

**实现方式**：启动时加载到内存，构建决策鏍戙

```python
# src/core/strategy_engine.py
class StrategyEngine:
    """策略引擎 - 核心策略决策"""
    
    def __init__(self):
        # 鍚动时加载核心策略
        self.card_grouping_rules = self._load_card_grouping_rules()
        self.role_determination = self._load_role_determination()
        self.bomb_strategy = self._load_bomb_strategy()
    
    def determine_role(self, handcards, game_state):
        """角色定位：主鏀/助攻"""
        score = self._calculate_power_score(handcards)
        
        if score >= 8:
            return "主攻"
        elif score >= 5:
            return "攻守鍏煎"
        elif score >= 2:
            return "助攻"
        else:
            return "鏈娓"
    
    def group_cards(self, handcards, role):
        """组牌决策"""
        # 应用"炸弹瓒婂氳秺好，单牌越少越好"原则
        # 应用"杞次优鍏"原则
        # 根据角色调整策略
        pass
```

**特点**：
- 鉁 鍚动时加载，内瀛樿块棶（O(1)：
- 鉁 支持热更新
- 鉁 核心策略快速决策

**3. 知识检索层（L3场景策略：**

**实现方式**：按闇鏌ヨ㈢煡识库，结果缓瀛樸

```python
# src/core/knowledge_retriever.py
class KnowledgeRetriever:
    """知识检索器 - 按需鏌ヨ㈢煡识库"""
    
    def __init__(self):
        self.cache = {}  # 鏌ヨ㈢粨果缓瀛
        self.knowledge_index = self._build_index()
    
    def get_relevant_knowledge(self, situation):
        """根据当前灞闈㈡索相关知璇"""
        # 1. 构建鏌ヨ㈠叧閿璇
        keywords = self._extract_keywords(situation)
        # 关键词示例：["残局", "瀵瑰跺墿5寮", "三带浜"]
        
        # 2. 妫索知识库
        knowledge = self._search_knowledge(keywords)
        
        # 3. 缓存结果
        cache_key = self._build_cache_key(situation)
        self.cache[cache_key] = knowledge
        
        return knowledge
    
    def _search_knowledge(self, keywords):
        """搜索知识库"""
        # 使用璇义搜索或关键词匹閰
        # 返回相关的知识片娈
        results = []
        
        # 示例：搜绱"残局传牌"相关知识
        if "残局" in keywords and "传牌" in keywords:
            results.append(self._load_knowledge("skills/03_assist_attack/01_passing_skills.md"))
        
        return results
```

**特点**：
- 鉁 按需加载，节省内瀛
- 鉁 鏀鎸佽义搜绱
- 鉁 结果缓存，提高效鐜

**4. 推理应用层（L4高级鎶巧）**

**实现方式**：结合局面分析，应用高级鎶宸с

```python
# src/core/advanced_reasoning.py
class AdvancedReasoning:
    """高级推理 - 应用高级鎶宸"""
    
    def analyze_card_language(self, opponent_actions):
        """鐗岃分析"""
        # 分析对手出牌，判鏂牌力
        if opponent_actions[0].type == "Single" and opponent_actions[0].rank < "T":
            return {
                "card_power": "寮",
                "intent": "想当上游",
                "suggestion": "配合让队友争头游"
            }
    
    def apply_interaction_rules(self, my_cards, opponent_cards):
        """应用相生相克规则"""
        # 判断牌型相生相克关系
        if self._has_many_straight(my_cards):
            # 顺子多，鍒3+2鍙能少
            return "对手鍙能没有三带二"
        
        if self._has_many_three_with_two(my_cards):
            # 3+2多，则顺子可能少
            return "对手鍙能没有顺瀛"
```

**特点**：
- 鉁 深度分析，灵活应用
- 鉁 结合灞面动态推鐞
- 鉁 鏀鎸佸嶆潅策略组合

**知识应用流程**：

```python
# src/core/ai_decision_maker.py
class AIDecisionMaker:
    """AI决策鍣 - 整合所有知璇"""
    
    def make_decision(self, game_state):
        """完整决策流程"""
        
        # 1. 纭编码规则妫查（L1：
        valid_actions = self.game_rules.filter_valid_actions(
            game_state.available_actions
        )
        
        # 2. 核心策略决策（L2：
        role = self.strategy_engine.determine_role(
            game_state.handcards, game_state
        )
        grouped_cards = self.strategy_engine.group_cards(
            game_state.handcards, role
        )
        
        # 3. 场景策略匹配（L3：
        situation = self._analyze_situation(game_state)
        relevant_knowledge = self.knowledge_retriever.get_relevant_knowledge(
            situation
        )
        
        # 4. 高级鎶巧应用（L4：
        if situation["phase"] == "endgame":
            # 应用残局鎶宸
            advanced_strategy = self.advanced_reasoning.analyze_endgame(
                game_state
            )
        
        # 5. 综合决策
        best_action = self._evaluate_actions(
            valid_actions,
            role,
            relevant_knowledge,
            advanced_strategy
        )
        
        return best_action
```

**知识应用示例**：

**示例1：开灞组牌决策**
```python
def group_cards_decision(handcards, game_state):
    """组牌决策示例"""
    
    # 1. 纭编码规则：氭查牌型合娉曟
    if not is_valid_card_combination(handcards):
        return None
    
    # 2. 核心策略：氳＄畻牌力，确瀹氳掕壊
    power_score = calculate_power_score(handcards)
    role = "主攻" if power_score >= 8 else "助攻"
    
    # 3. 应用组牌原则
    # "炸弹瓒婂氳秺好，单牌越少越好"
    grouped = optimize_card_grouping(
        handcards,
        principle="bomb_max_single_min"
    )
    
    # 4. 妫索相关知璇
    knowledge = knowledge_retriever.get_knowledge(
        keywords=["组牌", "寮灞", role]
    )
    
    # 5. 应用知识
    # "组顺生两单，鑲定没眼光"
    if will_create_two_singles(grouped):
        grouped = avoid_creating_singles(grouped)
    
    return grouped
```

**示例2：残灞传牌决策**
```python
def endgame_passing_decision(game_state):
    """残局传牌决策示例"""
    
    # 1. 判断场景
    if game_state.partner_remain == 5:
        # 2. 妫索相关知璇
        knowledge = knowledge_retriever.get_knowledge(
            keywords=["残局", "传牌", "瀵瑰跺墿5寮"]
        )
        
        # 3. 应用知识
        # "瀵瑰跺墿五张，明显是3+2"
        if is_likely_three_with_two(game_state.partner_history):
            # "送三带二"
            return find_three_with_two_to_pass(game_state.handcards)
        elif is_likely_straight(game_state.partner_history):
            # "送顺瀛"
            return find_straight_to_pass(game_state.handcards)
    
    return None
```

**知识妫绱优化**：

**1. 索引构建**
```python
# 构建知识索引，提楂樻索效鐜
knowledge_index = {
    "关键璇": ["知识文件璺寰"],
    "残局": ["skills/03_assist_attack/01_passing_skills.md", ...],
    "传牌": ["skills/03_assist_attack/01_passing_skills.md", ...],
    "瀵瑰跺墿5寮": ["skills/03_assist_attack/01_passing_skills.md", ...]
}
```

**2. 缓存策略**
```python
# 缓存常用知识，避免重复查璇
cache = {
    "残局_瀵瑰跺墿5张_三带浜": {
        "knowledge": "...",
        "timestamp": "...",
        "hit_count": 10
    }
}
```

**3. 优先级排搴**
```python
# 根据知识优先级排搴
def sort_knowledge_by_priority(knowledge_list):
    """按优先级排序"""
    priority_map = {
        "高压绾胯勫垯": 10,  # 鏈高优先级
        "核心策略": 8,
        "场景策略": 6,
        "高级鎶宸": 4
    }
    return sorted(knowledge_list, key=lambda k: priority_map.get(k.priority, 0))
```

**知识掌握程度评估**：

**1. 知识覆盖鐜**
```python
def calculate_knowledge_coverage(ai_actions, knowledge_base):
    """计算知识覆盖鐜"""
    applied_knowledge = set()
    total_knowledge = len(knowledge_base)
    
    for action in ai_actions:
        # 妫查应用了鍝些知璇
        knowledge_used = identify_applied_knowledge(action)
        applied_knowledge.update(knowledge_used)
    
    coverage = len(applied_knowledge) / total_knowledge
    return coverage
```

**2. 决策准确鐜**
```python
def evaluate_decision_accuracy(ai_decisions, expert_decisions):
    """评估决策准确鐜"""
    correct = 0
    total = len(ai_decisions)
    
    for ai_decision, expert_decision in zip(ai_decisions, expert_decisions):
        if ai_decision == expert_decision:
            correct += 1
    
    accuracy = correct / total
    return accuracy
```

**3. 胜率提升**
```python
def measure_win_rate_improvement(baseline_ai, knowledge_ai):
    """测量胜率提升"""
    baseline_win_rate = test_ai(baseline_ai, num_games=1000)
    knowledge_win_rate = test_ai(knowledge_ai, num_games=1000)
    
    improvement = knowledge_win_rate - baseline_win_rate
    return improvement
```

**预期效果**：
- **闃舵典竴**（基础规则引擎）：胜率 40-50%
- **闃舵典簩**（加入知璇嗘绱）：胜率 55-65%
- **闃舵典笁**（加入高级推理）：胜鐜 70-80%
- **闃舵靛洓**（持缁优化）：胜率 85%+

**关键成功因素**：
1. 鉁 知识结构化（已完成）
2. 鉁 知识索引构建（待实现：
3. 鉁 决策系统设计紙待实现）
4. 鉁 知识应用流程（待实现：
5. 鉁 持续优化机制（待实现：

**AI掌握知识的核心方娉**：
1. **分层应用**：不同层次的知识采用不同的应用方寮
   - 纭编码层：直接写在代码涓
   - 策略引擎层：鍚动时加载到内瀛
   - 知识检索层：按闇鏌ヨ，结果缓瀛
   - 推理应用层：深度分析，灵活应用
2. **蹇閫熸绱**：构建知识索引，支持关閿词和璇义搜绱
3. **智能匹配**：根鎹当前灞闈，自动匹配相关知璇
4. **优先绾х＄悊**：知识有优先级，高优先级知识优先应用
5. **持续优化**：氶氳繃对局数据分析，不鏂优化知识应用

通过这个框架，AI鍙以系统化地掌握和应用杩850+涓知识点，閫愭ユ彁升到鑳藉熸墦璐85%以上对手的水骞炽

#### 3.5 数据收集模块 (Data Collection Module)

##### 3.4.1 对局记录鍣 (GameRecorder)
- **功能**:
  - 记录完整对局过程
  - 保存JSON格式数据
  - 记录决策过程
  - 记录胜负结果

##### 3.4.2 数据存储 (DataStorage)
- **功能**:
  - 保存对局文件
  - 数据格式标准鍖
  - 数据索引管理
  - 数据统计分析

#### 3.6 信息监控模块 (Info Monitor Module)

##### 3.5.1 平台信息抓取鍣 (PlatformInfoFetcher)
- **功能**:
  - 定期访问平台网站
  - 抓取平台鍔ㄦ佷俊鎭
  - 抓取比赛相关消息
  - 妫测平台版鏈更新
  - 妫测文档更鏂

- **抓取鍐呭**:
  - 平台鍏告和通知
  - 比赛信息（报名时闂淬佹瘮赛时间等：
  - 平台版本更新
  - 文档更新（使用ㄨ说明书等：
  - 閲嶈侀氱煡鍜岃勫垯变更

- **技术实现**:
  - HTTP请求获取网页鍐呭
  - HTML解析提取关键信息
  - 鍐呭瑰彉鍖栨娴
  - 定时任务调度

- **接口璁捐**:
  ```python
  class PlatformInfoFetcher:
      - fetch_platform_info() -> dict
      - check_updates() -> List[UpdateInfo]
      - get_competition_info() -> dict
      - get_announcements() -> List[Announcement]
      - is_quiet_hours() -> bool  # 妫查是否在静默鏃舵
      - start_monitoring(interval: int, quiet_hours: dict)
      - stop_monitoring()
      - schedule_next_check() -> datetime  # 计算涓嬫℃查时间（避开静默鏃舵碉級
  ```

##### 3.5.2 信息解析鍣 (InfoParser)
- **功能**:
  - 解析HTML鍐呭
  - 提取关键信息
  - 识别信息类型（公鍛/比赛/更新等）
  - 格式化信鎭鍐呭

- **解析策略**:
  - 基于HTML鏍囩剧粨构解鏋
  - 关键词匹配识鍒閲嶈佷俊鎭
  - 时间信息提取
  - 链接和附件提鍙

##### 3.5.3 信息存储 (InfoStorage)
- **功能**:
  - 存储抓取的信鎭
  - 记录信息时间鎴
  - 去重处理
  - 信息历史记录

- **数据结构**:
  - 信息ID
  - 信息类型
  - 鏍囬樺拰鍐呭
  - 发布时间
  - 抓取时间
  - 鏄否已璇

##### 3.5.4 通知管理鍣 (NotificationManager)
- **功能**:
  - 妫测新信息
  - 鍙戦侀氱煡提醒
  - 鏀鎸佸氱嶉氱煡方式
  - 通知优先绾х＄悊

- **通知方式**:
  - 控制台输鍑
  - 日志记录
  - 桌面通知（可选）
  - 邮件堕氱煡（可选）
  - 文件保存

- **通知鍐呭**:
  - 新公鍛
  - 比赛信息
  - 平台更新
  - 閲嶈佽勫垯变更

### 鍥涖佹暟鎹结构璁捐

#### 4.1 卡牌表示
```python
Card:
    - suit: str  # 花色 (S/H/D/C/R/B) - 平台标准
    - rank: str  # 点数 (A/2-9/T/J/Q/K/B/R) - 平台标准
    - is_main: bool  # 鏄否为主牌 (curRank)
```

#### 4.2 牌型表示
```python
CardType:
    - type: str  # 牌型类型 (Single/Pair/Trips/ThreePair/ThreeWithTwo/TwoTrips/Straight/StraightFlush/Bomb/tribute/back/PASS) - 平台标准
    - cards: List[Card]  # 牌列琛 (handCards格式)
    - main_rank: str  # 主牌级别 (curRank)
```

#### 4.3 游戏鐘舵
```python
GameState:
    - my_hand: List[Card]  # 我的手牌 (handCards)
    - played_cards: List[CardType]  # 已出鐗 (actionList)
    - current_player: int  # 当前鐜╁ (curPos, 0-3)
    - current_card_type: CardType  # 当前牌型 (curAction)
    - teammate_seat: int  # 队友座位 (myPos对应: 0-2, 1-3)
    - game_phase: str  # 游戏闃舵 (stage: beginning/play/tribute/back/episodeOver/gameOver)
```

#### 4.4 平台信息
```python
PlatformInfo:
    - id: str  # 信息ID
    - type: str  # 信息类型（announcement/competition/update：
    - title: str  # 鏍囬
    - content: str  # 鍐呭
    - publish_time: datetime  # 发布时间
    - fetch_time: datetime  # 抓取时间
    - url: str  # 原文链接
    - is_read: bool  # 鏄否已璇
    - priority: int  # 优先绾

UpdateInfo:
    - version: str  # 版本鍙 (e.g., v1006)
    - update_time: datetime  # 更新时间
    - changelog: str  # 更新日志
    - download_url: str  # 下载链接

CompetitionInfo:
    - name: str  # 比赛名称
    - registration_start: datetime  # 报名寮始时闂
    - registration_end: datetime  # 报名结束时间
    - competition_start: datetime  # 比赛寮始时闂
    - competition_end: datetime  # 比赛结束时间
    - description: str  # 比赛描述
    - requirements: str  # 参赛要求
```

### 浜斻佹秷鎭流程璁捐

#### 5.1 连接流程
```
1. 建立WebSocket连接
   - 本地：ws://127.0.0.1:23456/game/{user_info}
   - 局域网：ws://[IP]:23456/game/{user_info}
2. 鍙戦佺敤户信鎭 (type: notify)
3. 等待游戏寮始消息 (stage: beginning)
4. 识别队友（根鎹连接顺序：1-3涓闃 (myPos 0-2)：2-4涓闃 (myPos 1-3)：
5. 进入游戏寰鐜 (stage: play)
```

#### 5.2 游戏流程
```
1. 接收发牌消息 ↓ 更新手牌 (handCards)
2. 接收出牌请求 ↓ 决策出牌 ↓ 鍙戦佸嚭牌消息 (type: act, curAction)
3. 接收其他鐜╁跺嚭鐗 ↓ 更新游戏鐘舵 (actionList)
4. 接收游戏结束消息 ↓ 保存对局数据 (stage: gameOver)
```

#### 5.3 完整数据娴佽捐

**数据流图**:
```
WebSocket消息接收
    ↓
消息解析 (JSON)
    ↓
鐘舵佹洿鏂 (EnhancedGameStateManager.update_from_message)
    ├─> 更新基础鐘舵 (myPos, handCards, curPos, etc.)
    ├─> 更新记牌信息 (CardTracker.update_from_play)
    │   ├─> 更新鐜╁跺巻鍙
    │   ├─> 更新剩余牌库
    │   └─> 更新PASS次数
    └─> 更新鍏共信鎭 (publicInfo)
    ↓
决策引擎 (DecisionEngine.decide)
    ├─> 寮濮嬭℃椂 (AdaptiveDecisionTimer.start)
    ├─> 编码游戏鐘舵 (StateFeatureEncoder.encode_state)
    │   ├─> 编码手牌特征
    │   ├─> 编码出牌历史特征
    │   ├─> 编码鐜╁剁姸态特寰
    │   └─> 编码游戏闃舵电壒寰
    ├─> 判断主动/琚鍔 (EnhancedGameStateManager.is_passive_play)
    │
    ├─> [琚动出牌分支]
    │   ├─> 评估配合机会 (CooperationStrategy.get_cooperation_strategy)
    │   │   └─> 鏌ヨ㈢姸态信鎭 (EnhancedGameStateManager)
    │   │       └─> 鏌ヨ㈣扮墝信息 (CardTracker)
    │   │
    │   ├─> 使用牌型专门处理鍣 (CardTypeHandlerFactory.get_handler)
    │   │   ├─> 分析手牌结构 (HandCombiner.combine_handcards)
    │   │   └─> 处理琚动出鐗 (Handler.handle_passive)
    │   │
    │   ├─> 生成鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
    │   │
    │   ├─> 动作空间优化 (ActionSpaceOptimizer.filter_actions)
    │   │   ├─> 判断动作空间大小
    │   │   ├─> [大动作空间] 快速筛选Top-K鍊欓
    │   │   │   ├─> 编码动作特征 (ActionFeatureEncoder.encode_action)
    │   │   │   └─> 快速评估并排序
    │   │   └─> [小动作空间] 保留鎵鏈夊欓
    │   │
    │   └─> 多因素评浼 (MultiFactorEvaluator.evaluate_all_actions)
    │       ├─> 编码动作特征 (ActionFeatureEncoder.encode_action) - 鍙閫
    │       ├─> 评估剩余牌数因素 (鏌ヨ CardTracker)
    │       ├─> 评估牌型大小因素
    │       ├─> 评估配合因素 (鏌ヨ CooperationStrategy)
    │       ├─> 评估风险因素
    │       ├─> 评估时机因素
    │       └─> 评估手牌结构因素 (鏌ヨ HandCombiner)
    │
    └─> [主动出牌分支]
        ├─> 生成鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
        ├─> 动作空间优化 (ActionSpaceOptimizer.filter_actions)
        │   └─> (同上)
        └─> 多因素评浼 (MultiFactorEvaluator.evaluate_all_actions)
            └─> (同上)
    ↓
妫查超鏃 (AdaptiveDecisionTimer.check_timeout)
    ├─> 根据动作空间大小鍔ㄦ佽皟整时闂撮勭畻
    └─> 超时保护机制
    ↓
选择鏈佳动浣
    ↓
构建响应消息 ({"actIndex": X})
    ↓
WebSocket消息鍙戦
```

#### 5.4 决策流程：堣︾粏：
```
1. 接收出牌请求 (type: act, stage: play)
2. 寮濮嬭℃椂 (AdaptiveDecisionTimer.start)
3. 编码游戏鐘舵 (StateFeatureEncoder.encode_state)
4. 判断主动/琚鍔 (EnhancedGameStateManager.is_passive_play)
5. [琚动出牌]:
   - 评估配合机会 (CooperationStrategy)
   - 使用牌型专门处理鍣 (CardTypeHandlerFactory)
   - 生成鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
   - 动作空间优化 (ActionSpaceOptimizer.filter_actions)
     - 判断动作空间大小
     - [大动作空间] 快速筛选Top-K鍊欓夛紙使用ActionFeatureEncoder：
     - [小动作空间] 保留鎵鏈夊欓
   - 多因素评浼 (MultiFactorEvaluator.evaluate_all_actions)
6. [主动出牌]:
   - 生成鍊欓夊姩浣 (PlayDecisionMaker.generate_candidates)
   - 动作空间优化 (ActionSpaceOptimizer.filter_actions)
   - 多因素评浼 (MultiFactorEvaluator.evaluate_all_actions)
7. 妫查超鏃 (AdaptiveDecisionTimer.check_timeout)
   - 根据动作空间大小鍔ㄦ佽皟整时闂撮勭畻
8. 选择鏈优方妗
9. 鍙戦佸喅策结鏋 (type: act, {"actIndex": X})
```

#### 5.5 模块依赖关系

**依赖关系鍥**:
```
DecisionEngine (决策引擎)
├─│ AdaptiveDecisionTimer (鑷适应时间控制)
│   └── (无依璧)
├─│ StateFeatureEncoder (鐘舵佺壒征编鐮)
│   └── EnhancedGameStateManager (状态管理)
│       └── CardTracker (记牌模块)
│           └── (无依璧)
├─│ ActionSpaceOptimizer (动作空间优化)
│   ├─│ EnhancedGameStateManager (状态管理)
│   └── ActionFeatureEncoder (动作特征编码)
│       └── EnhancedGameStateManager (状态管理)
├─│ ActionFeatureEncoder (动作特征编码)
│   └── EnhancedGameStateManager (状态管理)
│       └── CardTracker (记牌模块)
├─│ CooperationStrategy (配合策略)
│   └── EnhancedGameStateManager (状态管理)
│       └── CardTracker (记牌模块)
├─│ MultiFactorEvaluator (多因素评浼)
│   ├─│ EnhancedGameStateManager (状态管理)
│   │   └── CardTracker (记牌模块)
│   ├─│ HandCombiner (手牌组合)
│   │   └── (无依璧)
│   ├─│ CooperationStrategy (配合策略)
│   └── ActionFeatureEncoder (动作特征编码) - 鍙閫
└── CardTypeHandlerFactory (牌型处理器工鍘)
    ├─│ EnhancedGameStateManager (状态管理)
    │   └── CardTracker (记牌模块)
    └── HandCombiner (手牌组合)
        └── (无依璧)
```

**依赖说明**:
- **决策引擎 ↓ 状态管理 ↓ 记牌模块**: `DecisionEngine` 通过 `EnhancedGameStateManager` 访问游戏鐘舵侊紝`EnhancedGameStateManager` 内部使用 `CardTracker` 维护记牌信息
- **决策引擎 ↓ 鐘舵佺壒征编鐮 ↓ 状态管理**: `DecisionEngine` 使用 `StateFeatureEncoder` 编码游戏鐘舵侊紝`StateFeatureEncoder` 通过 `EnhancedGameStateManager` 获取鐘舵佷俊鎭
- **决策引擎 ↓ 动作空间优化 ↓ 动作特征编码**: `DecisionEngine` 使用 `ActionSpaceOptimizer` 优化动作空间，`ActionSpaceOptimizer` 使用 `ActionFeatureEncoder` 杩涜屽揩速评浼
- **决策引擎 ↓ 配合策略 ↓ 状态管理**: `DecisionEngine` 调用 `CooperationStrategy` 评估配合机会，`CooperationStrategy` 通过 `EnhancedGameStateManager` 获取鐘舵佷俊鎭
- **决策引擎 ↓ 手牌组合 ↓ 游戏规则**: `DecisionEngine` 使用 `HandCombiner` 分析手牌结构，`HandCombiner` 基于游戏规则识别牌型

#### 5.4 信息监控流程
```
1. 鍚动定时任务（后台杩愯岋級
   ↓
2. 妫查当前时间是否在静默鏃舵碉紙0:00-6:00： (quiet_hours)
   - 如果在静默时段，跳过鏈娆℃查，等待涓嬫
   ↓
3. 定期访问平台网站（每6小时，≥6小时： (check_interval: 21600s)
   ↓
4. 抓取网页鍐呭 (requests/httpx)
   ↓
5. 解析HTML提取信息 (BeautifulSoup)
   ↓
6. 与历史信鎭对比：屾测新鍐呭 (鍐呭瑰搱希或时间鎴)
   ↓
7. 如有新信鎭：
   - 保存到数据搴 (data/platform_info)
   - 鍙戦侀氱煡 (console/log/desktop/email)
   - 记录日志
   ↓
8. 等待妫查间隔（6小时）后继续寰鐜
   - 注意：氬傛灉涓嬫℃查时间落在静默时段，自动延后到静默鏃舵电粨鏉 (schedule_next_check)
```

### 鍏、配缃管理

#### 6.1 配置文件结构
```yaml
# config.yaml
platform:
  name: "南京邮电大学掼蛋AI平台"
  version: "v1006"
  url: "https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html"

websocket:
  # 本地连鎺
  local_url: "ws://127.0.0.1:23456/game/{user_info}"
  # 局域网连接（需要时替换IP：
  network_url: "ws://[局域网IP]:23456/game/{user_info}"
  reconnect_interval: 5
  heartbeat_interval: 30
  timeout: 10  # 连接超时时间：堢掞級

decision:
  # 鏈大决策时间（秒）
  max_decision_time: 0.8
  # 鍚用ㄨ扮墝功能
  enable_card_tracking: true
  # 鍚用推理功鑳
  enable_inference: true
  # 鍚用配合策鐣
  enable_cooperation: true
  # 决策缓存大小
  cache_size: 1000
  # 鍚用动作空间优鍖
  enable_action_space_optimization: true
  # 鍚用特征编鐮
  enable_feature_encoding: true

# 动作空间优化配置
action_space_optimizer:
  # 大动作空间阈值（超过姝ゅ间娇用快速筛选）
  large_space_threshold: 100
  # 鍊欓夊姩作比例（大动作空间时保留的比例）
  candidate_ratio: 0.1
  # 鏈灏忓欓夋暟量（即使比例很小也至少保留的数量：
  min_candidates: 10
  # 快速评估模式（true: 使用特征编码快速评浼, false: 使用完整评估：
  fast_evaluation_mode: true

# 特征编码配置
feature_encoding:
  # 鍚用状态特征编鐮
  enable_state_encoding: true
  # 鍚用动作特征编鐮
  enable_action_encoding: true
  # 鐘舵佺壒征维度（鑷鍔ㄨ＄畻：屾ゅ勪负鍙傝冿級
  state_feature_dim: 200
  # 动作特征维度（自鍔ㄨ＄畻：屾ゅ勪负鍙傝冿級
  action_feature_dim: 50
  # 特征缓存大小
  feature_cache_size: 1000

# 记牌模块配置
card_tracking:
  # 跟踪历史
  track_history: true
  # 跟踪剩余鐗
  track_remaining: true
  # 鍚用ㄦ傜巼计算
  enable_probability: true

# 多因素评估权重配缃
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
  # 队友牌型值阈值（大于姝ゅ煎簲璇PASS配合：
  support_threshold: 15
  # 对手剩余牌数危险闃堝硷紙小于姝ゅ煎簲该配合）
  danger_threshold: 4
  # 鏈大牌值阈鍊
  max_val_threshold: 14

# 手牌组合配置
hand_combiner:
  # 组牌优先级（鏁板艰秺大优先级越高：
  priorities:
    StraightFlush: 100  # 同花椤
    Bomb: 80            # 炸弹
    Straight: 60        # 顺子
    ThreeWithTwo: 50    # 三带浜
    TwoTrips: 45        # 钢板
    ThreePair: 40       # 三连瀵
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
  console: true  # 鏄否输出到控制鍙

contact:
  research: "chenxg@njupt.edu.cn"
  feedback: "wuguduofeng@gmail.com"
  qq: "519301156"

info_monitor:
  enabled: true  # 鏄否启用信鎭监控
  check_interval: 21600  # 妫查间隔（秒），默璁6小时（≥6小时：
  quiet_hours:  # 静默鏃舵碉紝不进琛屾鏌
    enabled: true  # 鏄否启用静默时娈
    start: "00:00"  # 静默寮始时间（24小时制）
    end: "06:00"    # 静默结束时间：24小时制）
  platforms:
    - name: "南京邮电大学掼蛋AI平台"
      url: "https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html"
      check_version: true  # 鏄鍚︽查版鏈更新
      check_announcements: true  # 鏄鍚︽查公鍛
      check_competitions: true  # 鏄鍚︽查比赛信鎭
  notification:
    console: true  # 控制鍙伴氱煡
    log: true  # 日志记录
    desktop: false  # 桌面通知（需瑕侀濆栧簱：
    email: false  # 邮件堕氱煡（需要配缃：
    email_config:
      smtp_server: ""
      smtp_port: 587
      username: ""
      password: ""
      to_email: ""
  storage:
    path: "./data/platform_info"  # 信息存储璺寰
    format: "json"  # 存储格式
    keep_history: true  # 保留历史记录
    max_history_days: 90  # 历史记录保留天数
```

### 涓冦侀敊璇处理

#### 7.1 连接閿欒
- WebSocket连接失败
- 连接涓鏂
- 重连机制

#### 7.2 数据閿欒
- JSON解析閿欒
- 消息格式閿欒
- 数据验证失败

#### 7.3 逻辑閿欒
- 牌型识别閿欒
- 决策异常
- 鐘舵佷笉涓鑷

### 鍏、日志和调试

#### 8.1 日志级别
- DEBUG: 详细调试信息
- INFO: 涓鑸信息
- WARNING: 警告信息
- ERROR: 閿欒信息

#### 8.2 日志鍐呭
- 连接鐘舵
- 接收/鍙戦佺殑消息 (type/stage/handCards/curPos/curAction)
- 决策过程
- 閿欒信息

### 涔濄佹祴试策鐣

#### 9.1 单元测试
- 牌型识别测试 (Single/Pair/Bomb绛)
- 牌型比较测试
- 决策逻辑测试

#### 9.2 集成测试
- **WebSocket通信测试**
  - 本地连接测璇 (ws://127.0.0.1:23456)
  - 局域网连接测试
  - 连接重连测试
  - 消息收发测试 (notify/act)

- **完整对局测试**
  - 鍚鍔4个AI客户端
  - 完成涓灞完整游戏 (stage: beginning -> play -> gameOver)
  - 验证组队关系：1-3涓闃 (myPos 0-2)：2-4涓闃 (myPos 1-3)：
  - 妫查牌型识鍒准确鎬
  - 妫查决策合鐞嗘
  - 验证记牌模块准确鎬
  - 验证配合策略有效鎬

- **模块集成测试**
  - 测试状态管理 ↓ 记牌模块的集鎴
  - 测试决策引擎 ↓ 多因素评估的集成
  - 测试决策引擎 ↓ 配合策略的集鎴
  - 测试决策引擎 ↓ 牌型处理器的集成
  - 测试完整决策流程

- **多局稳定性测璇**
  - 连续多局对战
  - 内存泄漏妫鏌
  - 长时间运行稳瀹氭
  - 鐘舵侀噸缃测试

- **异常场景测试**
  - 网络涓鏂鎭㈠
  - 消息格式閿欒处理
  - 超时处理
  - 异常閫出恢复
  - 决策超时保护测试

#### 9.3 性能测试
- **决策响应时间**
  - 鐩标：< 0.8秒（榛樿ら厤缃：
  - 平均响应时间
  - 鏈大响应时闂
  - 超时情况缁熻
  - 时间控制机制验证

- **内存使用**
  - 单局内存占用
  - 多局杩愯屽唴瀛樺為暱
  - 内存泄漏妫娴
  - 记牌模块内存占用

- **并发处理能力**
  - 同时处理多个消息
  - 寮傛ュ勭悊性能
  - 连接并发鏁

#### 9.4 策略测试
- **多因素评估测璇**
  - 测试不同权重配置的效鏋
  - 测试各因素评分的准确鎬
  - 测试鏈佳动作选择鐨勬ｇ‘鎬

- **配合策略测试**
  - 测试配合判断的准纭鎬
  - 测试不同参数配置的效鏋
  - 测试接替判断鐨勯昏緫

- **牌型处理器测璇**
  - 测试姣忕嶇墝鍨嬪勭悊器的逻辑
  - 测试主动/琚动出牌的正确鎬
  - 测试手牌结构分析的准纭鎬

### 鍗併佹墿灞曟ц捐

#### 10.1 策略插件鍖
- 鏀鎸佸氱嶇瓥略算娉
- 策略鍙插拔
- 策略鍔ㄦ佸垏鎹

#### 10.2 机器学习集成
- 预留ML模型接口
- 支持模型推鐞
- 支持在绾垮︿範

#### 10.3 多AI鏀鎸
- 支持同时运琛屽氫釜AI实例
- 支持不同策略的AI对战
- 支持AI水平评估

### 十一、项鐩鐩录结鏋

```
guandan_ai_client/
├─│ main.py                 # 主程序入口
├─│ config.yaml             # 配置文件
├─│ requirements.txt        # 依赖鍖
├─│ README.md              # 说明文档
│
├─│ src/
│   ├─│ communication/      # 通信模块
│   │   ├─│ __init__.py
│   │   ├─│ websocket_client.py
│   │   └── message_handler.py
│   │
│   ├─│ game_logic/         # 游戏逻辑模块
│   │   ├─│ __init__.py
│   │   ├─│ card.py
│   │   ├─│ card_type.py
│   │   ├─│ recognizer.py
│   │   ├─│ comparator.py
│   │   └── state_manager.py
│   │
│   ├─│ decision/           # 决策引擎模块
│   │   ├─│ __init__.py
│   │   ├─│ evaluator.py
│   │   ├─│ decision_maker.py
│   │   ├─│ cooperation.py
│   │   ├─│ action_space_optimizer.py  # 动作空间优化鍣
│   │   ├─│ action_feature_encoder.py  # 动作特征编码鍣
│   │   ├─│ state_feature_encoder.py    # 状态特征编码器
│   │   └── adaptive_timer.py          # 鑷适应决策时间控制鍣
│   │
│   ├─│ data/               # 数据收集模块
│   │   ├─│ __init__.py
│   │   ├─│ recorder.py
│   │   └── storage.py
│   │
│   ├─│ monitor/            # 信息监控模块
│   │   ├─│ __init__.py
│   │   ├─│ fetcher.py      # 信息抓取鍣
│   │   ├─│ parser.py       # 信息解析鍣
│   │   ├─│ storage.py      # 信息存储
│   │   └── notification.py # 通知管理鍣
│   │
│   └── utils/              # 工具模块
│       ├─│ __init__.py
│       ├─│ logger.py
│       └── config.py
│
├─│ tests/                  # 测试代码
│   ├─│ test_card_type.py
│   ├─│ test_decision.py
│   └── test_communication.py
│
├─│ data/                   # 数据目录
│   ├─│ replays/           # 回放文件
│   └── platform_info/     # 平台信息存储
│       ├─│ announcements.json  # 鍏告信鎭
│       ├─│ competitions.json   # 比赛信息
│       ├─│ updates.json        # 更新信息
│       └── history/            # 历史记录
│
└── logs/                   # 日志目录
    └── ai_client.log
```

### 十二、开鍙戣″垝

#### 闃舵典竴：基础框架：1-2鍛：
- [ ] 鎼建项鐩结构
- [ ] 实现WebSocket通信
- [ ] 实现JSON消息处理
- [ ] 实现基础日志系统

#### 闃舵典簩：游鎴忛昏緫：2-3鍛：
- [ ] 实现卡牌和牌型数据结构
- [ ] 实现牌型识别鍣
- [ ] 实现牌型比较鍣
- [ ] 实现游戏状态管理

#### 闃舵典笁：决策引擎（3-4鍛：
- [ ] 实现基础决策逻辑
- [ ] 实现策略评估
- [ ] 实现配合策略
- [ ] 优化决策算法
- [ ] 实现动作空间优化鍣（ActionSpaceOptimizer：
- [ ] 实现动作特征编码鍣（ActionFeatureEncoder：
- [ ] 实现状态特征编码器（StateFeatureEncoder：
- [ ] 实现鑷适应决策时间控制鍣（AdaptiveDecisionTimer：

#### 闃舵靛洓：数据收集：1鍛：
- [ ] 实现对局记录
- [ ] 实现数据存储
- [ ] 实现统计分析

#### 闃舵典簲：信鎭监控：1鍛：
- [ ] 实现平台信息抓取鍣
- [ ] 实现信息解析鍣
- [ ] 实现信息存储
- [ ] 实现通知管理鍣
- [ ] 实现定时任务调度
- [ ] 测试信息抓取鍜岄氱煡功能

#### 闃舵靛叚：测试优化（持续：
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化
- [ ] 策略优化
- [ ] 信息监控测试

### 十三、关閿鎶鏈鐐

#### 13.1 WebSocket寮傛ュ勭悊
- 使用寮傛IO提高性能
- 处理并发消息
- 避免闃诲

#### 13.2 决策算法
- 规则引擎（初期）
- 搜索算法（中期）
- 机器学习（后期）
- **多因素评估系统**: 综合评估6涓因素（剩余牌鏁般佺墝型大灏忋侀厤鍚）侀庨櫓、时鏈恒佹墜牌结构）：岃＄畻动作评分
- **主动/琚动决策分绂**: 区分主动出牌鍜岃动出牌，采用不同策略
- **牌型专门处理**: 为每种牌型（Single、Pair、Trips、Bomb、Straight等）创建专门鐨勫勭悊逻辑
- **动作空间优化**：堝熼壌DanZero+论文：:
  - 根据动作空间大小鍔ㄦ佺瓫閫夊欓夊姩浣
  - 大动作空间（>100）：快速筛选Top-K鍊欓夛紝使用鍚发式规则快速评浼
  - 小动作空间（鈮100）：精细评估鎵鏈夊欓夊姩浣
  - 解决掼蛋游戏鍒濆嬬姸态可鑳>5000合法动作的挑鎴
- **特征编码鎶鏈**：堝熼壌DanZero+论文的DMC方法：:
  - **鐘舵佺壒征编鐮**: 将游戏状态编码为结构化特征向量（手牌、历鍙层佺帺家状态等：
  - **动作特征编码**: 将动作编码为特征向量（牌鍨嬨佸ぇ灏忋佷富鐗屻佺櫨鎼牌等：
  - 提升评估效率，为鏈来强鍖栧︿範集成做准澶
  - 考虑掼蛋特色（花色重瑕佹с佺櫨鎼鐗屻佺骇牌）

#### 13.3 鐘舵佸悓姝
- 纭保状态一鑷存
- 处理消息乱序
- 鐘舵佹仮复机鍒
- **增强状态管理**: 集成记牌模块，提供完整状态查询接鍙
- **队友识别**: 使用鍏寮 `teammate_pos = (myPos + 2) % 4` 自动识鍒队友（参考获奖代码）

#### 13.4 模块依赖关系璁捐
- **依赖注入**: 所有模鍧楅氳繃依赖注入方式连接，避免硬编码依赖
- **依赖关系**:
  - 决策引擎 ↓ 状态管理 ↓ 记牌模块
  - 决策引擎 ↓ 鐘舵佺壒征编鐮 ↓ 状态管理
  - 决策引擎 ↓ 动作空间优化 ↓ 动作特征编码 ↓ 状态管理
  - 决策引擎 ↓ 配合策略 ↓ 状态管理
  - 决策引擎 ↓ 手牌组合 ↓ 游戏规则
  - 决策引擎 ↓ 多因素评浼 ↓ 动作特征编码（可选）
- **鍒濆嬪寲顺序**: 从底层到顶层，确保依赖关绯绘ｇ‘

#### 13.5 数据娴佽捐
- **完整数据娴**: WebSocket消息 ↓ 消息解析 ↓ 鐘舵佹洿鏂 ↓ 决策引擎 ↓ 动作选择 ↓ 消息鍙戦
- **关键节点**:
  - 鐘舵佹洿新时自动更鏂拌扮墝模块
  - 鐘舵佺壒征编码（StateFeatureEncoder：: 编码游戏鐘舵佷负特征向量
  - 动作空间优化（ActionSpaceOptimizer：: 根据动作空间大小鍔ㄦ佺瓫閫夊欓
  - 动作特征编码（ActionFeatureEncoder：: 编码动作为特征向量（大动作空间快速评估）
  - 决策引擎调用配合策略评估
  - 决策引擎调用多因素评浼
  - 鑷适应时间控制（AdaptiveDecisionTimer：: 根据动作空间大小鍔ㄦ佽皟整时闂撮勭畻
  - 超时保护机制
- **详细说明**: 鍙傝"浜斻佹秷鎭流程璁捐"章节鐨"5.3 完整数据娴佽捐"

#### 13.6 鍙傝冭幏奖代码的关键璁捐
- **队友识别鍏寮**: `teammate_pos = (myPos + 2) % 4`（参考获奖代码）
- **鐘舵佹暟鎹结构**: 鍙傝冭幏奖代码的 `history` 鍜 `remain_cards` 结构
  - `history`: `{'0': {'send': [], 'remain': 27}, ...}` 记录每个鐜╁剁殑出牌历史和剩余牌鏁
  - `remain_cards`: 按花色和点数分类的剩余牌搴
- **决策函数鍒嗙**: 鍙傝冭幏奖代码的 `active()` 鍜 `passive()` 鍒嗙
  - `active_decision()`: 主动出牌决策（率先出牌或鎺ラ庯級
  - `passive_decision()`: 琚动出牌决策（闇要压制）
- **手牌组合算法**: 鍙傝冭幏奖代码的 `combine_handcards()` 完整实现
  - 识别单张銆佸瑰瓙、三寮犮佺偢寮
  - 识别顺子：堣冭檻单张銆佸瑰瓙、三张分布）
  - 识别同花椤

#### 13.7 信息抓取鎶鏈
- **HTTP请求**: 使用requests/httpx鍙戦丠TTP请求
- **HTML解析**: 使用BeautifulSoup解析网页鍐呭
- **定时任务**: 使用schedule/APScheduler实现定时抓取
- **鍐呭瑰规瘮**: 通过鍐呭瑰搱希或时间鎴虫测更鏂
- **异常处理**: 处理网络閿欒、解析错璇绛
- **反爬铏搴斿**: 设置合理鐨勮锋眰间隔和User-Agent

### 十四、参考资料与资源

#### 14.1 官方资源
- **平台网站**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **平台版本**: v1006（当前版鏈：
- **离线平台**: 闇从平台网站下杞
- **使用说明涔**: 对应版本v1006，包鍚：
  - 使用说明
  - JSON数据格式说明 (type/stage/handCards/myPos/curPos/curAction/actionList)
  - JSON示例说明

#### 14.2 游戏规则
- **江苏省体育局掼蛋竞赛绠鏄撹勫垯**
- **特殊规则注意**:
  - v1006版本调整了抗璐¤勫垯，与比赛鐗堣勫垯涓鑷 (tribute/back)
  - 注意手牌的表示方娉 (handCards: ["S2", "H2", ...])
  - 接口与v1003版本保持涓鑷

#### 14.3 联系方式
- **研究兴趣鍜ㄨ**: chenxg@njupt.edu.cn
- **闂题反棣**: wuguduofeng@gmail.com
- **QQ**: 519301156

#### 14.4 鎶鏈鍙傝
- WebSocket鍗忚文档
- JSON格式规范
- Python WebSocket库文档（websockets / websocket-client：

### 十五、比赛参璧涜佹眰与评浼

#### 15.1 比赛参赛资格纭璁

鉁 **当前架构满足比赛要求**：

##### 鎶鏈鍚堣勬
- 鉁 WebSocket通信：已实现
- 鉁 JSON数据格式：已鏀鎸 (平台标准变量)
- 鉁 4个AI参与：已璁捐 (myPos 0-3组队)
- 鉁 Windows/Linux支持：Python跨平台
- 鉁 实时响应：异姝ュ勭悊机制

##### 功能完整鎬
- 鉁 游戏规则实现：牌型识鍒和比杈 (Single/Bomb绛)
- 鉁 决策能力：策略评估和出牌决策
- 鉁 配合能力：队友配合策鐣 (teammate_seat)
- 鉁 閿欒处理：异甯稿勭悊和恢复
- 鉁 稳定性：重连和状态同姝

#### 15.2 比赛评分标准：堥勪及：
根据AI算法对抗平台的常见评分方式：

##### 评分维度
1. **胜率** (40-50%)
   - 与其他AI对战的胜鐜
   - 闇要优化决策算娉

2. **决策质量** (20-30%)
   - 出牌合理鎬
   - 配合榛樺戝害
   - 策略深度

3. **稳定鎬** (15-20%)
   - 无异甯搁鍑
   - 响应时间稳定
   - 閿欒处理能力

4. **代码质量** (10-15%)
   - 代码规范鎬
   - 鍙维护鎬
   - 文档完整鎬

#### 15.3 比赛前必须完成的功能

##### 核心功能（必须）
- [x] WebSocket连接鍜岄氫俊
- [x] JSON消息解析和构寤
- [x] 所有牌型识鍒
- [x] 牌型比较和压制判鏂
- [x] 基础出牌决策
- [x] 游戏状态管理 (stage/myPos/curPos)
- [x] 閿欒处理和重杩

##### 进阶功能（建璁：
- [ ] 配合策略优化
- [ ] 记牌和推鐞
- [ ] 多策略融鍚
- [ ] 性能优化（响应时闂<1秒）
- [ ] 详细日志记录

##### 比赛鍑嗗囷紙閲嶈侊級
- [ ] 本地测试：涓庣荤嚎平台完整测试
- [ ] 压力测试：长时间杩愯岀ǔ瀹氭
- [ ] 对战测试：与其他AI对战
- [ ] 性能测试：响应时间优鍖
- [ ] 文档鍑嗗囷細提交说明文档

#### 15.4 比赛策略寤鸿

##### 鐭期策略（快速参赛）
```
鐩标：鑳藉熸ｅ父参赛，不鐘低级閿欒
时间：2-3涓鏈
重点：
  - 完善基础功能
  - 实现基本策略
  - 纭保稳瀹氭
```

##### 涓期策略（提升排名：
```
鐩标：达到涓上水骞
时间：3-6涓鏈
重点：
  - 优化决策算法
  - 加强配合策略
  - 提升胜率
```

##### 长期策略（冲击冠军）
```
鐩标：达到顶尖水平
时间：6-12涓鏈
重点：
  - 引入机器学习
  - 深度策略优化
  - 大量对战璁缁
```

#### 15.5 比赛注意事项

##### 鎶鏈注意事项
1. **响应时间限制**
   - 纭保决策时间在合理范围内（寤鸿<1秒）
   - 避免超时导致判负

2. **连接稳定鎬**
   - 实现完善的重连机鍒
   - 处理网络波动

3. **数据格式严格鎬**
   - 严格按照平台JSON格式要求 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
   - 验证所有消息格式

4. **规则准确鎬**
   - 严格按照江苏省体育局规则
   - 特别注意抗贡等特娈婅勫垯 (tribute/back)

##### 提交要求（根鎹参赛指南：
- **AI客户端代码**（或鍙鎵ц岀▼序）
- **源代鐮**：堝傞渶要，闇联系主办方确认）
- **使用说明文档**
  - 如何杩愯岀▼搴
  - 配置说明
  - 使用姝ラ
- **鎶本文档**（架鏋勮说明：
  - 技术选型
  - 架构璁捐
  - 核心算法说明
- **测试报告**（可选）
  - 测试结果
  - 性能数据
- **联系方式**
  - 閭绠
  - 电话
  - QQ

##### 提交流程
1. **鍑嗗囨彁交材鏂**：堣佷笂述清单）
2. **鍙戦佸弬赛申请邮浠**
   - 涓婚橈細掼蛋AI算法对抗 - 参赛用宠
   - 收件人：chenxg@njupt.edu.cn（研究兴趣）鎴 wuguduofeng@gmail.com（问题反馈）
   - 鍐呭癸細介绍已完成工浣溿丄I特点、希望了解的闂棰
3. **等待主办方回澶**
   - 获取参赛纭璁
   - 了解具体比赛安排
   - 获取提交方式
4. **正式提交作品**
   - 根据主办鏂硅佹眰提交材料
5. **参与对战**
   - 平台自动匹閰嶅规垬
   - 系统自动评鍒
   - 查看排名和结鏋

#### 15.6 比赛流程（根鎹参赛指南：

```
1. 访问平台网站
   ↓
2. 下载离线平台（v1006）和使用说明涔
   ↓
3. 闃呰诲拰理解文档
   - 游戏规则
   - JSON格式
   - 鎶本文档
   ↓
4. 开发AI客户端
   - WebSocket通信
   - 牌型识别
   - 决策逻辑
   ↓
5. 本地测璇
   - 连接测试
   - 完整对局测试
   - 多局稳定性测璇
   ↓
6. 联系主办鏂
   - 鍙戦佸弬赛申请邮浠
   - 等待鍥炲
   ↓
7. 正式提交作品
   - 根据要求提交材料
   ↓
8. 参与对战
   - 平台自动匹閰
   - 系统自动评鍒
   ↓
9. 查看排名和结鏋
   ↓
10. 持续优化提升
```

#### 15.7 当前架构的参赛准备度评估

| 模块 | 完成搴 | 比赛就绪搴 | 备注 |
|------|--------|-----------|------|
| 通信模块 | 鉁 100% | 鉁 就绪 | 核心功能完整 |
| 游戏逻辑 | 鉁 100% | 鉁 就绪 | 闇要实际测试验璇 |
| 决策引擎 | ⚠️ 70% | ⚠️ 闇优化 | 策略闇要实战优鍖 |
| 数据收集 | 鉁 100% | 鉁 就绪 | 可选功鑳 |
| 信息监控 | 鉁 100% | 鉁 就绪 | 鏂板炲姛能，推荐鍚用 |
| 閿欒处理 | 鉁 90% | 鉁 就绪 | 闇要完善边界情鍐 |
| 测试覆盖 | ⚠️ 50% | ⚠️ 闇加强 | 闇要更多集成测璇 |

**总体评估**：✅ **鍙以参璧**，但寤鸿在决策引擎和测试方面继续优化銆

### 十六、参璧涙查清鍗

#### 16.1 开发阶娈垫查清鍗
- [ ] 下载离线平台（v1006：
- [ ] 下载使用说明书（v1006版本：
- [ ] 闃呰绘父鎴忚勫垯（江苏省体育灞规则：
- [ ] 理解JSON格式（严格按照平台格式）
- [ ] 开发WebSocket通信模块
- [ ] 实现所有牌型识鍒（Single/Pair/Trips等）
- [ ] 实现牌型比较和压制判鏂
- [ ] 实现决策逻辑
- [ ] 实现队友识别：1-3涓闃 (myPos 0-2)：2-4涓闃 (myPos 1-3)：
- [ ] 实现配合策略
- [ ] 实现閿欒处理和重连机鍒
- [ ] 实现日志系统
- [ ] 实现平台信息监控模块（可选但推荐：
  - [ ] 信息抓取鍣
  - [ ] 信息解析鍣
  - [ ] 信息存储
  - [ ] 通知管理鍣

#### 16.2 测试闃舵垫查清鍗
- [ ] 本地连接测试（ws://127.0.0.1:23456：
- [ ] 局域网连接测试：堝傞渶要）
- [ ] 单局完整测试：4个AI完整对局：
- [ ] 多局稳定性测试（连续多局：
- [ ] 异常场景测试（网络中鏂、消息閿欒等）
- [ ] 性能测试（响应时闂<1秒）
- [ ] 组队关系验证：1-3涓队，2-4涓队）
- [ ] 牌型识别准确性验璇
- [ ] 决策合理性验璇

#### 16.3 提交闃舵垫查清鍗
- [ ] 鍑嗗嘇I客户端代码/程序
- [ ] 编写使用说明文档
- [ ] 编写鎶本文档（架鏋勮说明：
- [ ] 鍑嗗囨祴试报告（可选）
- [ ] 鍑嗗囪仈系方式信鎭
- [ ] 鍙戦佸弬赛申请邮浠
  - [ ] 閭件主题：掼蛋AI算法对抗 - 参赛用宠
  - [ ] 收件人：chenxg@njupt.edu.cn 鎴 wuguduofeng@gmail.com
  - [ ] 鍐呭瑰寘鍚：已完成工作、AI特点、希望了解的闂棰
- [ ] 等待主办方回澶
- [ ] 根据要求正式提交作品

#### 16.4 鎶鏈要点妫鏌
- [ ] WebSocket连接地址正确（本鍦/局域网：
- [ ] JSON消息格式严格符合平台要求 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
- [ ] 所有牌型都鑳芥ｇ‘识别
- [ ] 组队关系正确识别：1-3涓队，2-4涓队）
- [ ] 抗贡规则正确处理（v1006版本，tribute/back：
- [ ] 响应时间控制在合理范围（<1秒）
- [ ] 閿欒处理和重连机制完鍠
- [ ] 日志记录完整
- [ ] 信息监控功能测试：堝傚凡实现：
  - [ ] 信息抓取准确鎬
  - [ ] 通知功能正常
  - [ ] 信息存储正确

### 十七、后缁优化方向

#### 17.1 算法优化
1. **强化学习集成**: 使用收集的数据璁练RL模型
2. **深度学习**: 使用神经网络杩涜屽喅绛
3. **多策略融鍚**: 结合澶氱嶇瓥略算娉
4. **实时学习**: 在线学习鍜岄傚簲
5. **配合策略优化**: 提升队友配合榛樺戝害
6. **记牌和推鐞**: 实现记牌功能鍜屽规墜牌推鐞

#### 17.2 性能优化
1. **决策速度**: 提升决策速度，确保<1秒响搴
2. **内存优化**: 减少内存占用，避免内存泄婕
3. **并发处理**: 优化寮傛ュ勭悊性能
4. **代码优化**: 提升代码鎵ц屾晥鐜

#### 17.3 比赛优化
1. **閽堝硅瘎分标准优鍖**: 根据比赛评分维度优化策略
2. **胜率提升**: 通过大量对战璁练提升胜鐜
3. **稳定性提鍗**: 纭保长时间杩愯屾棤异常
4. **策略深度**: 提升决策策略的深度和广度

#### 17.4 鍙傝冨︿範方向
1. **南京澶у﹂珮阳团闃**: 研究SDMC方法：堢二届涓国人工智能博弈算法大赛掼蛋项鐩冠军：
2. **清华澶у﹀攼杰团闃**: 研究大型璇瑷模型在掼蛋等棋牌游戏涓的应用
3. **Botzone平台**: 鍙傝冩枟地主AI的实现方娉
4. **学术论文**: 关注相关AI博弈算法研究

### 十八、快速开始指南

#### 18.1 立即行动（今天）
1. 鉁 访问平台网站：https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
2. 鉁 下载离线平台（v1006）和使用说明涔
3. 鉁 寮始阅读文档，理解游戏规则和JSON格式

#### 18.2 鏈周完鎴
1. 鉁 理解游戏规则（江苏省体育灞规则：
2. 鉁 理解JSON格式和消息类型 (type: notify/act, stage: beginning/play)
3. 鉁 鎼建开发环境（Python + WebSocket库）
4. 鉁 实现基础WebSocket通信

#### 18.3 鏈月完鎴
1. 鉁 实现所有牌型识鍒
2. 鉁 实现牌型比较和压制判鏂
3. 鉁 实现基础决策逻辑
4. 鉁 完成本地测试（连接和单灞测试：

#### 18.4 下月完成
1. 鉁 实现配合策略
2. 鉁 优化决策算法
3. 鉁 完成多局稳定性测璇
4. 鉁 鍑嗗囨彁交材鏂

### 十九、重要提閱

#### 19.1 鎶鏈要点
- ⚠️ **严格按照JSON格式**：平台板笿SON格式要求严格，必须完鍏ㄧ符合 (["Bomb", "2", ["H2", "D2", "C2", "S2"]])
- ⚠️ **组队规则**：第 1、3 号连接为另一队 (myPos 0-2)：岀2銆4涓连接为另一队 (myPos 1-3)，必椤绘ｇ‘识别
- ⚠️ **响应时间**：建璁决策时间<1秒，避免超时
- ⚠️ **版本鍏煎**：当前使用v1006版本，注意抗璐¤勫垯调整 (tribute/back)
- ⚠️ **信息监控**：建璁鍚用信鎭监控功能，及时了解平台动态和比赛信息
- ⚠️ **抓取频率**：信鎭抓取搴旇剧疆合理间隔：堟查间隔≥6小时），且每鏃0:00-6:00为静默时段不杩涜屾查，避免过于频繁请求

#### 19.2 开发建璁
- 鉁 **先实现基础功能**：确保能正常连接鍜岄氫俊
- 鉁 **閫愭ヤ紭鍖**：先实现基本策略，再閫愭ヤ紭鍖
- 鉁 **充分测试**：本地完整测试后再提浜
- 鉁 **保持联系**：遇到问题及时联系主办方

#### 19.3 参赛寤鸿
- 📧 **提前联系**：开发完成后提前联系主办方了解提浜よ佹眰
- 📝 **鍑嗗囨枃妗**：准备好使用说明和技本文档
- 🧪 **充分测试**：确保稳瀹氭у拰正确鎬
- 🚀 **持续优化**：参赛后根据对战结果持续优化

### 二十、信鎭监控功能说明

#### 20.1 功能概述
信息监控模块用于自动抓取南浜邮电大学掼蛋AI平台的动态信鎭，帮助用户及时了解：
- 平台鍏告和通知
- 比赛信息和时间安鎺
- 平台版本更新
- 文档更新
- 閲嶈佽勫垯变更

#### 20.2 使用方式

##### 鍚用信鎭监控
在配缃文件涓设置：
```yaml
info_monitor:
  enabled: true  # 鍚用信鎭监控
  check_interval: 21600  # 妫查间隔（秒），默璁6小时（≥6小时：
  quiet_hours:  # 静默鏃舵碉紝不进琛屾鏌
    enabled: true  # 鏄否启用静默时娈
    start: "00:00"  # 静默寮始时间（24小时制）
    end: "06:00"    # 静默结束时间：24小时制）
```

##### 查看信息
- 控制台输出：新信鎭会自动在控制台显绀
- 日志文件：信鎭浼氳板綍到日志文浠
- 数据文件：信鎭保存鍦 `data/platform_info/` 目录

##### 手动妫鏌
鍙浠ラ氳繃API或命浠よ屾墜动触鍙戞查：
```python
from src.monitor.fetcher import PlatformInfoFetcher
fetcher = PlatformInfoFetcher()
updates = fetcher.check_updates()
```

#### 20.3 技术实现要点

##### 网页抓取
- 使用 `requests` 鎴 `httpx` 鍙戦丠TTP请求
- 设置合理的User-Agent鍜岃锋眰澶
- 处理网络超时和重试机鍒
- 遵守robots.txt规则：堝傛湁：

##### HTML解析
- 使用 `BeautifulSoup` 解析HTML鍐呭
- 根据网站结构提取关键信息
- 处理鍔ㄦ佸唴容（如需要，鍙使用Selenium：

##### 鍐呭规娴
- 通过鍐呭瑰搱希或时间鎴虫测更鏂
- 去重处理，避免重澶嶉氱煡
- 记录历史信息，支持查璇

##### 通知机制
- 控制鍙伴氱煡：实时显示新信息
- 日志记录：氳板綍所有抓取的信息
- 可选扩展：桌面通知、邮浠堕氱煡绛

##### 静默鏃舵靛勭悊
- 妫查当前时间是否在静默鏃舵碉紙0:00-6:00：
- 如果在静默时段，跳过鏈娆℃鏌
- 计算涓嬫℃查时间时：屽傛灉落在静默鏃舵碉紝自动延后到静默鏃舵电粨鏉
- 实现示例：
  ```python
  def is_quiet_hours(self, current_time: datetime) -> bool:
      hour = current_time.hour
      return 0 <= hour < 6
  
  def schedule_next_check(self, current_time: datetime, interval: int) -> datetime:
      next_check = current_time + timedelta(seconds=interval)
      if self.is_quiet_hours(next_check):
          # 延后到静默时段结束（6:00：
          next_check = next_check.replace(hour=6, minute=0, second=0)
      return next_check
  ```

#### 20.4 注意事项

##### 鍚堣勬
- 遵守网站使用鏉℃
- 设置合理的抓鍙栭戠巼：堟查间隔≥6小时：
- 静默鏃舵碉紙0:00-6:00）不杩涜屾查，减少对服务器的影鍝
- 涓嶈佸规湇务器造成压力
- 尊重网站的反鐖铏机制

##### 稳定鎬
- 处理网络閿欒和超鏃
- 处理HTML结构变化
- 实现閿欒鎭㈠嶆満鍒
- 记录抓取失败日志

##### 鍙维护鎬
- 网站结构鍙能变化，闇要及时更新解鏋愰昏緫
- 寤鸿定期妫查抓取功能是鍚︽ｅ父
- 保持代码的可扩展鎬

#### 20.5 扩展功能（可选）

##### 邮件堕氱煡
配置閭件服务，閲嶈佷俊鎭自动发送邮件：
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
使用系统通知功能（需瑕侀濆栧簱）：
```python
# 闇要安瑁: plyer 鎴 win10toast (Windows)
from plyer import notification
notification.notify(
    title="平台更新",
    message="发现新的比赛信息",
    timeout=10
)
```

##### 多平台监鎺
鍙以扩展监控其他相关平台：
- 涓国人工智鑳藉︿細官网
- 其他掼蛋AI比赛平台
- 相关学术浼氳网站

## 应用场景
- **开发阶娈**：指导掼蛋AI客户端的架构设计″拰模块实现
- **测试闃舵**：作为测试和验证的标准参鑰
- **比赛鍑嗗**：确保参赛作鍝佺符合平台要求和技术规范
- **维护闃舵**：作为文档参考，便于后续优化和扩灞
- **信息监控**：自动获取平台动态，及时响应比赛和更新信鎭

## 示例/案例
- **完整对局示例**：4个AI客户端连接，完成一灞游戏，验证组闃 (myPos 0 vs 1-3闃)和决策 (curAction: ["Single", "2", ["H2"]])
- **信息监控示例**：氭测到新比赛公告，鑷鍔ㄩ氱煡并保存到 data/platform_info/announcements.json
- **閿欒鎭㈠嶇ず渚**：WebSocket鏂寮后自动重连，鎭㈠嶆父戏状鎬 (stage: play)

## 注意事项
- **平台变量统一**：所有牌鍨 (Single/Bomb)、花鑹 (S/H/D/C)、状鎬 (myPos/curPos/stage) 必须使用平台标准变量鍚
- **时间处理**：所有时间字段使用系统时间API (datetime.now())：岀佹㈢‖编码
- **响应时间**：决策时间控制在1秒以内，避免超时
- **组队识别**：严格按照平台拌勫垯：岀1/3连接为另一队 (myPos 0/2)
- **信息抓取鍚堣**：氭查间隔≥6小时，静默时娈 (00:00-06:00) 不抓鍙
- **JSON格式**：严格遵守平台格式，示例：["Bomb", "2", ["H2", "D2", "C2", "S2"]]
- **动作空间优化**：初始状态可鑳>5000合法动作，必须使用动作空间优化器快速筛选，避免评估鎵鏈夊欓夊艰嚧超时
- **特征编码**：状态和动作特征编码鍙提升评估效率，为鏈来强鍖栧︿範集成打下基础，建璁鍚用

## 相关知识鐐
- [掼蛋AI知识库格式化方案圿 - 知识库格式化标准，与本文档绗3.4鑺"知识库模鍧"完全对齐
- [掼蛋AI知识应用框架] - 知识应用框架设计紝说明AI如何掌握和应用850+涓知识点，已整合到本文档绗3.4.6鑺
- [江苏掼蛋规则 - 牌型定义 (Single/Pair/Bomb)]
- [平台使用说明涔 v1006 - JSON格式和消息类型]
- [DanZero+论文分析-架构借鉴寤鸿甝 - 动作空间优化和特征编码技术

---

**文档版本**: v2.5  
**创建时间**: 使用系统时间API获取（`datetime.now()`）  
**鏈后更鏂**: 使用系统时间API获取（`datetime.now()`）- 整合知识应用框架  
**维护责任**: AI开发团闃

## 📝 更新日志

### v2.6 (2025-11-26)
- 鉁 更新出牌顺序说明（平台实际实现为顺时针）
- 鉁 添加位置关系计算鍏式（涓婂躲佷笅瀹躲佸瑰讹級
- 鉁 明确平台出牌顺序：0 ↓ 1 ↓ 2 ↓ 3 ↓ 0...（顺时针：
- 鉁 说明虽然规则璇"逆时閽"，但平台实现为顺时针，应以平台为鍑

### v2.5 (2025-01-27)
- 鉁 整合《掼蛋AI知识应用框架.md》到架构方案
- 鉁 在知识库模块：3.4.6节）添加知识应用框架璁捐
- 鉁 添加知识规模缁熻★紙17涓文件，约850涓知识点）
- 鉁 添加知识灞傛＄粨构（L1纭编码灞傘丩2策略引擎灞傘丩3知识检索层、L4推理应用层）
- 鉁 添加分层决策系统实现方案
- 鉁 添加知识应用流程和示例代鐮
- 鉁 添加知识妫绱优化策略（索引构寤恒佺紦存策鐣ャ佷紭先级排序：
- 鉁 添加知识掌握程度评估方法（知璇嗚嗙洊鐜囥佸喅策准纭鐜囥佽儨率提升）
- 鉁 添加预期效果（阶段一40-50%，阶段二55-65%，阶段三70-80%，阶段四85%+：
- 鉁 更新相关知识点，添加知识应用框架引用

### v2.4 (2025-01-27)
- 鉁 对齐《知识库格式化方妗.md銆
- 鉁 更新知识库目录结构，添加`rules/`鐩录，与格式化方案堜繚持一鑷
- 鉁 在知识库模块部分添加与格式化方案堢殑对齐说明
- 鉁 明确知识分类与格式化方案堢殑对应关系
- 鉁 更新技巧库和知璇嗘索器部分，添加格式化方案堝瑰簲说明
- 鉁 更新相关知识点，添加知识库格式化方案堝紩用

### v2.3 (2025-01-27)
- 鉁 添加动作空间优化鍣（ActionSpaceOptimizer）模鍧楄捐
  - 根据动作空间大小鍔ㄦ佺瓫閫夊欓夊姩浣
  - 大动作空间快速筛选Top-K鍊欓
  - 小动作空间精细评估所有动浣
  - 借鉴DanZero+论文的动作空闂村勭悊策略
- 鉁 添加动作特征编码鍣（ActionFeatureEncoder）模鍧楄捐
  - 将动作编码为结构化特征向閲
  - 提取牌型、大灏忋佷富鐗屻佺櫨鎼牌等特征
  - 支持快速评估和相似搴﹁＄畻
- 鉁 添加状态特征编码器（StateFeatureEncoder）模鍧楄捐
  - 将游戏状态编码为特征向量
  - 提取手牌、历鍙层佺帺家状态等特征
  - 为未来强鍖栧︿範集成做准澶
- 鉁 增强决策时间控制器为鑷适应决策时间控制鍣（AdaptiveDecisionTimer：
  - 根据动作空间大小鍔ㄦ佽皟整时闂撮勭畻
  - 大动作空间：鏇村氭椂间用于快速筛閫
  - 小动作空间：鏇村氭椂间用于精细评浼
- 鉁 更新数据娴佽捐★紝集成动作空间优化和特征编码流绋
- 鉁 更新模块依赖关系，添加新模块的依璧栬说明
- 鉁 更新配置管理，添加动作空间优化和特征编码配置椤
- 鉁 更新关键鎶鏈点，说明动作空间优化和特征编码技术
- 鉁 更新项目鐩录结构，添加新模块文浠
- 鉁 更新寮鍙戣″垝，添加新模块的开发任鍔

### v2.2 (2025-11-25)
- 鉁 添加知识库模块（Knowledge Base Module：夎捐
- 鉁 更新整体架构图，增加知识库层
- 鉁 璁捐″垎灞傝板繂策略（硬编码灞傘佸唴存加载层、按闇鏌ヨ㈠眰：
- 鉁 璁捐¤勫垯搴撱佺瓥略库、技巧库、知璇嗘索器
- 鉁 明确知识库使用策略和性能优化方案
- 鉁 添加知识库目录结鏋勮说明
- 鉁 添加接口璁捐″拰实现方式
- 鉁 明确基础规则纭编码、常用策略内存加杞姐侀珮级技巧按闇鏌ヨ㈢殑策略

### v2.1 (使用系统时间API获取)
- 鉁 对齐知识库格式化方案，添加YAML元数据
- 鉁 标准化文档结鏋 (概述/详细内容/应用场景/注意事项)
- 鉁 统一使用平台变量鍚 (Single/Bomb/myPos/curPos/stage)
- 鉁 增强信息监控模块说明，包鍚静默鏃舵靛勭悊
- 鉁 更新示例代码，确保濈符合平台JSON格式
- 鉁 添加参赛妫查清单和快速开始指南

### v2.0 (使用系统时间API获取)
- 鉁 鍒濆嬫灦构方案，包含分层璁捐″拰核心模块
- 鉁 添加信息监控功能璁捐
- 鉁 完善比赛参赛要求和评浼

### v1.0 (使用系统时间API获取)
- 基础架构框架璁捐

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

