# 掼蛋AI完整开发指南

## 📋 文档概述

本文档整合了掼蛋AI开发的所有核心内容，包括：
- 专家知识注入系统（基于丁华秘籍）
- 训练方法和平台
- 参赛指南
- 技术实现方案

**适用对象**: 掼蛋AI开发者、研究人员、参赛选手  
**文档版本**: v2.0  
**最后更新**: 使用系统时间API获取（`datetime.now()`）

---

## 🚀 快速开始

### 第一步：获取平台资源

1. **访问平台网站**
   ```
   https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
   ```

2. **下载必要文件**
   - ✅ 离线平台（v1006版本）
   - ✅ 使用说明书（v1006）
   - ✅ JSON格式说明文档

3. **联系方式**
   - 研究咨询: chenxg@njupt.edu.cn
   - 问题反馈: wuguduofeng@gmail.com
   - QQ: 519301156

### 第二步：环境准备

```bash
# 1. 安装Python 3.8+
python --version

# 2. 安装依赖
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

### 第三步：基础实现

参考 `docs/PHASE1_TASKS.md` 完成基础功能：
- WebSocket通信模块
- JSON消息处理
- 游戏逻辑模块
- 基础决策引擎

---

## 📚 第一部分：专家知识注入系统

### 1.1 知识来源

#### 丁华《掼蛋技巧秘籍》整合

**来源**: `docs/skill/掼蛋技巧秘籍(丁华).md`（OCR提取，160页）

**核心知识要点**：
- **规则类**: 出牌优先级、主牌/副牌使用时机、炸弹与拆牌原则
- **配合策略**: 队友间让牌与配合节奏、升级/封堵联动
- **观察判断**: 记牌与读牌、通过牌型估算对手持牌
- **升级防守**: 关键回合保留阻止升级的牌、炸弹阻挡策略
- **时机掌握**: 首轮进攻与留牌权衡、炸弹使用时机

**优先级划分**：
- **高优先级**: 直接影响胜负的规则（保炸弹、阻止升级、主要防守规则）
- **中优先级**: 队友配合与升级节奏相关策略
- **低优先级**: 技巧性提示、示例性对局

### 1.2 知识提取流程

```python
# 知识提取工作流
1. OCR文本清洗 → 去重、合并换行、纠错
2. 知识抽取 → RealExpertKnowledgeExtractor
3. 格式化 → StandardGuandanKnowledge
4. 验证过滤 → confidence >= 0.8 优先注入
5. 存储入库 → KnowledgeInjectionSystem
6. 生成策略规则 → build_strategy_rules()
```

### 1.3 知识注入系统架构

#### 核心组件

```python
# src/core/knowledge_injection_system.py
class KnowledgeInjectionSystem:
    """知识注入系统 - 核心控制器"""
    
    async def inject_knowledge_package(self, package_path: str):
        """注入知识包"""
        # 1. 加载知识包
        # 2. 处理和验证知识
        # 3. 存储到持久化数据库
        # 4. 构建内存索引
        # 5. 通知AI客户端集成
```

#### 知识分类体系

```python
class GuandanKnowledgeCategory(Enum):
    BASIC_RULES = "basic_rules"           # 基础规则
    CARD_TYPES = "card_types"             # 牌型识别
    TACTICAL_COOPERATION = "tactical_cooperation"  # 战术配合
    UPGRADE_STRATEGY = "upgrade_strategy"  # 升级策略
    DEFENSE_TACTICS = "defense_tactics"   # 防守战术
    GAME_PHASE_TACTICS = "game_phase_tactics"  # 阶段战术
    OBSERVATION_SKILLS = "observation_skills"  # 观察技能
    TIMING_MASTERY = "timing_mastery"     # 时机掌握
```

### 1.4 增强型知识提取器

```python
# src/knowledge/enhanced_extractor.py
class RealExpertKnowledgeExtractor:
    """基于实际专家数据的知识提取器"""
    
    def extract_knowledge_from_text(self, text: str, source: str):
        """从专家文本中提取知识"""
        # 使用8种知识类别的提取模式
        # 识别动作类型（should/suggest/avoid/observe）
        # 确定游戏阶段和紧急程度
```

**提取模式示例**：
- 战术配合: `r"(送牌|配合|队友|让牌).*?([^。]{15,100}[。])"`
- 升级策略: `r"(升级|通关).*?([^。]{15,80}[。])"`
- 时机掌握: `r"(时机|选择|把握).*?([^。]{10,80}[。])"`

### 1.5 知识格式化与验证

```python
# src/knowledge/expert_formatter.py
class ExpertKnowledgeFormatter:
    """专家知识格式化器"""
    
    def format_extracted_knowledge(self, extracted, expert_source):
        """将提取的知识转换为标准格式"""
        # 生成知识ID和名称
        # 构建触发条件
        # 生成行动建议
        # 计算优先级和置信度
```

**标准知识格式**：
```python
@dataclass
class StandardGuandanKnowledge:
    knowledge_id: str
    name: str
    category: GuandanKnowledgeCategory
    description: str
    trigger_conditions: Dict[str, Any]
    action_recommendations: List[str]
    confidence_score: float
    priority_score: float
    # ... 更多字段
```

### 1.6 持久化记忆系统

```python
# src/memory/lifetime_memory_system.py
class LifetimeMemorySystem:
    """终身记忆系统 - 投喂一次，永久使用"""
    
    async def store_knowledge_memory(self, knowledge_item, context):
        """存储知识记忆"""
        # SQLite持久化存储
        # 构建记忆关联
        # 更新缓存
```

**记忆系统特点**：
- ✅ **投喂一次，永久使用** - 知识注入后持续生效
- ✅ **自动关联** - 相关记忆自动关联
- ✅ **智能检索** - 根据上下文检索相关记忆
- ✅ **衰减机制** - 长期未使用的记忆自动衰减

---

## 🎯 第二部分：训练方法

### 2.1 训练平台

#### 主要平台：南京邮电大学掼蛋AI算法对抗平台

- **平台地址**: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **当前版本**: v1006
- **状态**: 内测中（可参与）

**平台特点**：
- 提供离线平台用于本地开发测试
- 完整的WebSocket + JSON通信接口
- 支持4个AI同时对战训练
- 自动评分和排名系统

### 2.2 训练方法

#### 方法一：基于规则的传统训练（入门）

**适用阶段**: 入门和基础训练（1-2周）

**核心思路**：
```python
1. 实现基础牌型识别 (Single/Pair/Trips等)
2. 建立出牌优先级规则
3. 实现基础配合策略
4. 连续对局训练优化
5. 分析失败案例改进规则
```

**优势**: 实现简单，容易调试，规则透明  
**劣势**: 策略深度有限，难以应对复杂局面

#### 方法二：搜索算法训练（中级）

**适用阶段**: 中级训练（2-4周）

**核心思路**：
- 使用Minimax搜索算法
- Alpha-Beta剪枝优化
- 评估函数设计
- 深度搜索优化

#### 方法三：强化学习训练（高级）

**适用阶段**: 高级训练（4-8周）

**核心思路**：
- 使用深度强化学习（DQN/A3C/PPO）
- 通过大量对局学习最优策略
- 自我对弈不断改进
- 多智能体协同训练

#### 方法四：知识增强训练（推荐）

**适用阶段**: 所有阶段

**核心思路**：
- 注入专家知识（丁华秘籍）
- 结合规则引擎和强化学习
- 知识驱动决策
- 持续优化知识库

```python
# 知识增强AI示例
class KnowledgeDrivenAI:
    """知识驱动AI"""
    
    def make_decision(self):
        # 1. 分析当前局面
        situation = self._analyze_situation()
        
        # 2. 应用专家知识
        knowledge_plays = self._apply_expert_knowledge(available_plays, situation)
        
        # 3. 结合经验学习
        experience_plays = self._apply_experience_learning(available_plays)
        
        # 4. 综合评估选择
        final_play = self._comprehensive_evaluation(
            knowledge_plays, experience_plays, situation
        )
```

### 2.3 训练数据收集

**数据来源**：
1. 平台对战数据 - 从南邮平台获取对局记录
2. 自我对弈数据 - 多个AI版本对战
3. 专家标注数据 - 邀请掼蛋高手标注

**数据格式**：
```json
{
  "game_id": "20241121_001",
  "game_state": {...},
  "decision": {
    "player": 1,
    "action": "play",
    "selected_cards": ["H-K"],
    "reasoning": "跟随同花色，避免过早使用大牌"
  },
  "outcome": {...}
}
```

### 2.4 训练评估指标

**技术指标**：
- 决策准确率: > 95%
- 响应时间: < 1秒
- 稳定性: 连续100局无崩溃

**竞技指标**：
- vs 基础AI: > 80% 胜率
- vs 中级AI: > 60% 胜率
- vs 高级AI: > 40% 胜率
- 配合默契度: > 70%

---

## 🏆 第三部分：参赛指南

### 3.1 参赛流程

```
1. 访问平台 → 下载资源
   ↓
2. 阅读文档 → 理解规则
   ↓
3. 开发AI客户端
   ↓
4. 本地测试 → 确保稳定
   ↓
5. 联系主办方 → 提交申请
   ↓
6. 正式参赛 → 参与对战
   ↓
7. 持续优化 → 提升排名
```

### 3.2 技术要点

#### WebSocket连接

```python
# 本地连接
ws://127.0.0.1:23456/game/{user_info}

# 局域网连接
ws://[局域网IP]:23456/game/{user_info}
```

#### 组队规则

- **第1个和第3个连接**的AI自动为一队
- **第2个和第4个连接**的AI自动为一队
- 需要识别队友并配合

#### 牌型中英文对照

- Single -- 单张
- Pair -- 对子
- Trips -- 三张
- ThreePair -- 三连对
- ThreeWithTwo -- 三带二
- TwoTrips -- 钢板
- Straight -- 顺子
- Bomb -- 炸弹

### 3.3 开发检查清单

**开发阶段**：
- [ ] 下载离线平台（v1006）
- [ ] 下载使用说明书
- [ ] 阅读游戏规则
- [ ] 理解JSON格式
- [ ] 开发WebSocket通信
- [ ] 实现牌型识别
- [ ] 实现决策逻辑
- [ ] 实现错误处理

**测试阶段**：
- [ ] 本地连接测试
- [ ] 单局完整测试
- [ ] 多局稳定性测试
- [ ] 异常场景测试
- [ ] 性能测试（响应时间）

**提交阶段**：
- [ ] 准备代码/程序
- [ ] 编写使用说明
- [ ] 编写技术文档
- [ ] 发送参赛申请邮件

---

## 🔧 第四部分：技术实现

### 4.1 项目结构

```
guandan-ai/
├── src/
│   ├── communication/      # WebSocket通信
│   ├── game_logic/         # 游戏逻辑
│   ├── decision/           # 决策引擎
│   ├── knowledge/          # 知识系统
│   │   ├── enhanced_extractor.py
│   │   ├── expert_formatter.py
│   │   └── knowledge_base.py
│   ├── memory/             # 记忆系统
│   │   └── lifetime_memory_system.py
│   └── core/               # 核心系统
│       └── knowledge_injection_system.py
├── data/
│   ├── knowledge/          # 知识库
│   ├── replays/            # 对局回放
│   └── memory/             # 记忆数据
├── config/
│   └── config.yaml
└── tests/
```

### 4.2 核心模块实现

#### WebSocket通信模块

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
        message_type = data.get("type")
        
        if message_type == "play_request":
            await self._handle_play_request(data)
```

#### 知识驱动决策引擎

```python
# src/decision/knowledge_driven_ai.py
class KnowledgeDrivenAI:
    def __init__(self, game_state, knowledge_base):
        self.game_state = game_state
        self.kb = knowledge_base
    
    def make_decision(self):
        # 1. 获取可用出牌
        available_plays = self.game_state.get_available_cards()
        
        # 2. 分析当前局面
        situation = self._analyze_situation()
        
        # 3. 应用专家知识
        knowledge_plays = self._apply_expert_knowledge(
            available_plays, situation
        )
        
        # 4. 综合评估选择
        return self._comprehensive_evaluation(knowledge_plays)
```

### 4.3 配置示例

```yaml
# config/config.yaml
platform:
  websocket_url: "ws://127.0.0.1:23456/game/{user_id}"
  version: "v1006"

ai:
  name: "KnowledgeDrivenAI"
  strategy_level: "expert"
  response_timeout: 1.0

knowledge:
  injection_enabled: true
  knowledge_base_path: "data/knowledge/guandan_knowledge_base.json"
  confidence_threshold: 0.8

memory:
  enabled: true
  memory_db_path: "data/memory/lifetime_memory.db"
  max_memory_entries: 10000

logging:
  level: "INFO"
  file: "logs/ai_client.log"
```

---

## 📖 第五部分：完整工作流

### 5.1 知识注入工作流

```python
# 完整知识注入流程
async def inject_expert_knowledge():
    # 1. 初始化系统
    injection_system = KnowledgeInjectionSystem()
    memory_system = LifetimeMemorySystem()
    
    # 2. 提取专家知识
    extractor = RealExpertKnowledgeExtractor()
    formatter = ExpertKnowledgeFormatter()
    
    # 读取丁华秘籍
    with open("docs/skill/掼蛋技巧秘籍(丁华).md", "r", encoding="utf-8") as f:
        expert_text = f.read()
    
    # 3. 提取和格式化
    extracted = extractor.extract_knowledge_from_text(expert_text, "丁华秘籍")
    formatted = [formatter.format_extracted_knowledge(e, "丁华秘籍") 
                 for e in extracted]
    
    # 4. 过滤高置信度知识
    high_confidence = [k for k in formatted if k.confidence_score >= 0.8]
    
    # 5. 注入系统
    for knowledge in high_confidence:
        await injection_system.inject_knowledge_package(knowledge)
        await memory_system.store_knowledge_memory(knowledge)
    
    print(f"成功注入 {len(high_confidence)} 条专家知识")
```

### 5.2 训练工作流

```python
# 完整训练流程
async def train_guandan_ai():
    # 1. 初始化AI
    game_state = GameState()
    knowledge_base = GuandanKnowledgeBase()
    knowledge_base.load_from_file("data/knowledge/guandan_knowledge_base.json")
    
    ai = KnowledgeDrivenAI(game_state, knowledge_base)
    
    # 2. 连接平台
    client = GuandanWebSocketClient("AI_TRAIN_001", game_state)
    client.rule_ai = ai
    
    # 3. 开始训练
    url = "ws://127.0.0.1:23456/game/AI_TRAIN_001"
    await client.connect(url)
    
    # 4. 收集训练数据
    # 5. 分析优化
    # 6. 持续改进
```

### 5.3 参赛工作流

```python
# 参赛准备流程
async def prepare_for_competition():
    # 1. 确保知识库已注入
    await inject_expert_knowledge()
    
    # 2. 本地测试
    await local_testing()
    
    # 3. 性能优化
    await optimize_performance()
    
    # 4. 准备提交材料
    prepare_submission_materials()
    
    # 5. 联系主办方
    contact_organizers()
```

---

## 🎓 第六部分：最佳实践

### 6.1 知识注入最佳实践

1. **优先注入高置信度知识** (confidence >= 0.8)
2. **按优先级分类注入** (高优先级规则优先)
3. **定期更新知识库** (根据实战反馈)
4. **验证知识有效性** (通过对局验证)

### 6.2 训练最佳实践

1. **循序渐进** - 从规则引擎开始，逐步引入高级方法
2. **数据驱动** - 重视数据收集和统计分析
3. **持续优化** - 建立反馈机制，持续改进
4. **对比学习** - 与不同水平AI对比，找出问题

### 6.3 开发最佳实践

1. **严格遵循JSON格式** - 确保平台兼容性
2. **实现错误处理** - 提高系统稳定性
3. **记录详细日志** - 便于问题排查
4. **版本控制** - 使用Git管理代码

---

## 📊 第七部分：评估与优化

### 7.1 性能评估

```python
# 性能评估指标
evaluation_metrics = {
    "technical": {
        "decision_accuracy": 0.95,  # 决策准确率
        "response_time": 0.8,       # 响应时间（秒）
        "stability": 100            # 连续对局数
    },
    "competitive": {
        "win_rate_vs_basic": 0.80,
        "win_rate_vs_intermediate": 0.60,
        "win_rate_vs_advanced": 0.40,
        "cooperation_success": 0.70
    },
    "learning": {
        "convergence_speed": 500,    # 收敛轮次
        "generalization": 0.85,     # 泛化能力
        "adaptation": 0.75          # 适应能力
    }
}
```

### 7.2 优化建议

**知识系统优化**：
- 定期更新知识库
- 根据使用效果调整优先级
- 合并相似知识项

**决策系统优化**：
- 优化评估函数
- 调整知识权重
- 改进搜索算法

**性能优化**：
- 优化数据结构
- 减少计算复杂度
- 使用缓存机制

---

## 🔗 相关资源

### 官方资源
- 平台网站: https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- 使用说明书（v1006）
- JSON格式说明文档

### 专家知识
- 丁华《掼蛋技巧秘籍》: `docs/skill/掼蛋技巧秘籍(丁华).md`
- 江苏掼蛋规则: `docs/gdrules/江苏掼蛋规则.md`

### 技术文档
- 开发规则: `docs/DEVELOPMENT_RULES.md`
- 阶段一任务: `docs/PHASE1_TASKS.md`
- Git设置指南: `docs/GIT_SETUP_GUIDE.md`

---

## 📝 总结

### 核心要点

1. **专家知识注入** - 基于丁华秘籍的知识系统，投喂一次永久使用
2. **分层训练方法** - 从规则引擎到强化学习的渐进式训练
3. **完整技术方案** - WebSocket通信、知识系统、记忆系统一体化
4. **实战验证** - 通过平台对战持续优化

### 快速行动清单

- [ ] 访问平台网站，下载资源
- [ ] 搭建开发环境
- [ ] 实现基础通信和游戏逻辑
- [ ] 注入专家知识（丁华秘籍）
- [ ] 实现知识驱动决策
- [ ] 本地测试训练
- [ ] 准备参赛材料

**现在就开始行动，打造强大的掼蛋AI！** 🚀

---

**文档维护**: 本文档整合了所有相关技术方案，建议定期更新  
**反馈建议**: 如有问题或建议，请提交Issue或联系开发团队

