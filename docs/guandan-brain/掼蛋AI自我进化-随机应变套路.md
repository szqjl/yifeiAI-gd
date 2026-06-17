# 掼蛋 AI 自我学习进化：随机应变套路

> 创建时间：2026-06-11
> 状态：进行中
> 对应问题：神经网络 RL 三轮迭代输给硬编码，核心原因是模型无法处理"随机应变"
---

## 核心诊断结论

**神经网络吃亏的本质**：掼蛋的决策依赖**动态贝叶斯局面判断**，而标准 RL 学到的是"input 下的平均最优 action"——这是一个没有条件依赖的条件概率。

> 人类打牌：当前局面 → 更新信念 → 基于信念决策
> 标准 RL：手牌特征 → 输出动作（没有局面信念这个中间变量）

---

## 套路一：局面信念建模（最关键）

### 什么是"局面信念"
每出一手牌，人类会推断：
- 对手为什么出这个牌型（逼我？送对家？打信号）
- 各家手里大概有什么牌（概率分布）
- 当前谁占优，谁该冲，谁该保

### 如何教模型学"局面判断"

把决策分成两步：

```
Step 1：局面分类
├─ 输入：手牌 + 出牌历史 + 级牌状态 + 进贡状态
├─ 输出：当前属于哪种局面类型
│        ├─ 进攻型：我手牌强，该冲
│        ├─ 防守型：我手牌弱，该送对家
│        ├─ 观望型：局势不明，等待信号
│        └─ 保对家型：对家快走完了，我掩护
└─ 这是一个 **多分类问题**，比直接学动作更容易收敛

Step 2：动作选择（条件于局面类型）
├─ 输入：手牌 + 局面类型 + 各模块评估
├─ 输出：该局面下的最优动作概率
└─ 同一手牌，不同局面类型 → 不同动作
```

### 技术实现

```python
# 局面信念向量
state_belief = {
    'my_strength': float,           # 自己的牌力 0~1
    'partner_strength': float,       # 对家牌力 0~1
    'opponent_pressure': float,     # 对手压迫程度 0~1
    'level_progress': int,          # 级牌进度（打几）
    'trump_ready': bool,            # 我是否有级牌
    'bomb_count': int,              # 我方剩余炸弹数
    'opponent_bomb_risk': float,    # 推断对手有炸弹的概率
    'last_card_meaning': str,       # 上家出的牌传达什么信号
}
```

---

## 套路二：多模块 specialized 评估

不是训练一个通用 policy，而是拆成多个专业化模块：

| 模块 | 输入 | 输出 | 作用 |
|------|------|------|------|
| 级牌判断 | 级牌状态+手牌 | 该冲还是该等 | 控制级牌节奏 |
| 炸弹评估 | 手牌炸弹数+局面对手炸弹信号 | 现在亮弹还是留弹 | 级牌控制 |
| 对家配合 | 对家明牌+出牌历史 | 我该冲还是保 | 配合决策 |
| 局面风险 | 各家出牌+手牌 | 我冲会不会被炸 | 风险评估 |
| 贡牌判断 | 进贡/还贡状态 | 贡牌质量如何 | 信用评估 |

最终决策 = 各模块评分的加权组合

```python
weight 由 RL 或模仿学习得到
```

---

## 套路三：Memory / 长程情境记忆

掼蛋需要看"前几轮发生了什么"：

```
标准 RL input：当前手牌 + 本局开始时的状态
改进后 input：当前手牌 + 前 N 轮出牌历史（序列）

模型结构：Transformer Self-Attention
├─ 每张牌是 one-hot 向量
├─ 出牌历史是序列
├─ 通过 attention 建模"这张牌在那手下有意义"
└─ 输出：考虑了情境的动作概率
```

---

## 套路四：稠密 Reward 信号

纯输赢 reward 太稀疏，加中间信号：

| Reward 信号 | 触发条件 | 分值 |
|------------|----------|------|
| 出牌成功 | 出的牌型赢得这一墩 | +0.05 |
| 接风成功 | 接住了对家的风 | +0.1 |
| 掼蛋成功 | 打出级牌组合 | +0.3 |
| 级牌控制 | 打出当前级牌 | +0.2 |
| 配合成功 | 对家接住我出的牌型 | +0.1 |
| 送对家成功 | 对家因此走了一张 | +0.15 |
| 炸蛋得失 | 放炸弹赢/被炸输 | ±0.5 |
| 本方升级 | 完成升级 | +2.0 |
| 对方升级 | 对方完成升级 | -1.0 |

**关键**：用 TD(λ) 或 advantage estimation 做信用分配，而不是蒙特卡洛平均。

---

## 套路五：对手多样性（破解 self-play 陷阱）

```
问题：所有 RL 对手都是同一版本 → 策略多样性崩溃

破解：
1. 保留历史 checkpoint 对手池
2. 每次 self-play 从对手池随机选
3. 用硬编码 bot 当固定训练对手
4. 训练后期：让人类玩家对战，把反馈 signal 回训练
```

---

## 套路七：模块化分阶段训练（V7 新方向）

### 核心思路

**像人类一样学习**：先单训各个模块，训练达标一个，再训练新的模块，最后整合。

> 端到端训练（V2-V7 失败路线）：手牌特征 → 模型 → 动作（跳过了组牌、记牌、策略）
> 模块化训练（新路线）：组牌 → 记牌 → 策略 → 动作（每个模块独立验证）

### 为什么端到端训练失败？

| 问题 | V2-V7 端到端训练 | 模块化训练 |
|------|-----------------|-----------|
| **任务复杂度** | 同时学习组牌+记牌+策略+动作 | 每个模块只学一个子任务 |
| **可诊断性** | val_acc=35% 不知道哪里错 | 哪个模块差就调哪个 |
| **表示学习** | 缺少中间表示（局面信念） | 组牌/记牌/策略就是中间表示 |
| **数据效率** | 需要大量数据才能收敛 | 每个模块用针对性数据 |
| **人类对照** | 不像人类学习方式 | 完全符合人类学习路径 |

### 训练路线图

```
Week 1: 组牌模块（监督学习）
├─ 输入：手牌 one-hot (108 维)
├─ 输出：炸弹数、手数、牌力分数、角色定位
├─ 训练数据：M3 规则引擎生成（366 局胜局）
├─ 目标：
│   ├─ bomb_count 准确率 > 95%
│   ├─ hand_count 准确率 > 90%
│   ├─ power_score MAE < 1.0
│   └─ role 准确率 > 85%
└─ 验证：独立测试集，不达标不进入下一步

Week 2: 记牌模块（序列学习）
├─ 输入：出牌历史序列
├─ 输出：各家剩余牌分布概率 (4 × 54 维)
├─ 训练数据：完整对局记录（game_records）
├─ 目标：推断准确率 > 80%
└─ 验证：对比真实剩余牌（restCards）

Week 3: 策略模块（分类学习）
├─ 输入：组牌结果 + 记牌结果
├─ 输出：进攻/防守/观望/保对家 (4 分类)
├─ 训练数据：M3 胜局策略标注
├─ 目标：分类准确率 > 85%
└─ 验证：M3 策略一致性检查

Week 4: 动作模块（条件学习）
├─ 输入：手牌 + 组牌 + 记牌 + 策略
├─ 输出：动作概率分布 (2048 维)
├─ 训练数据：M3 胜局动作
├─ 目标：动作匹配率 > 70%
└─ 验证：批跑 12 局 vs lalala，胜率 > 30%

Week 5: 整合与微调（可选）
├─ 冻结组牌/记牌/策略模块
├─ 端到端微调动作模块
├─ 批跑 36 局 vs lalala
└─ 目标：V7 胜率 > 40%
```

### 技术实现

```python
# Step 1: 组牌模块
class CardGroupingNetwork(nn.Module):
    """手牌 → 组牌结果"""
    def forward(self, hand_cards):
        # 输入：手牌 one-hot (108 维)
        # 输出：bomb_count, hand_count, power_score, role
        x = self.encoder(hand_cards)
        return self.bomb_head(x), self.hand_head(x), \
               self.power_head(x), self.role_head(x)

# Step 2: 记牌模块
class CardCountingNetwork(nn.Module):
    """出牌历史 → 各家剩余牌分布"""
    def forward(self, history_sequence):
        # 输入：出牌历史序列
        # 输出：4 × 54 维概率分布
        x = self.lstm(history_sequence)
        return self.decoder(x)

# Step 3: 策略模块
class StrategyNetwork(nn.Module):
    """组牌+记牌 → 策略分类"""
    def forward(self, grouping, counting):
        # 输入：组牌结果 + 记牌结果
        # 输出：进攻/防守/观望/保对家
        x = torch.cat([grouping, counting], dim=1)
        return self.classifier(x)

# Step 4: 动作模块
class ActionNetwork(nn.Module):
    """手牌+组牌+记牌+策略 → 动作概率"""
    def forward(self, hand_cards, grouping, counting, strategy):
        # 输入：所有模块输出
        # 输出：动作概率分布 (2048 维)
        x = torch.cat([hand_cards, grouping, counting, strategy], dim=1)
        return self.decoder(x)

# 整合
class V7ModularEngine(nn.Module):
    def __init__(self):
        self.card_grouping = CardGroupingNetwork()
        self.card_counting = CardCountingNetwork()
        self.strategy = StrategyNetwork()
        self.action = ActionNetwork()
    
    def forward(self, message):
        # 串联所有模块
        grouping = self.card_grouping(message.handCards)
        counting = self.card_counting(message.history)
        strategy = self.strategy(grouping, counting)
        return self.action(message.handCards, grouping, counting, strategy)
```

### 关键优势

1. ✅ **每个模块可独立验证**（不达标就不进入下一步）
2. ✅ **问题可定位**（组牌差就调组牌，动作差就调动作）
3. ✅ **数据可复用**（组牌模块数据可用于其他任务）
4. ✅ **可解释性强**（能看到每个模块的输出）
5. ✅ **符合人类学习方式**（先学基本功，再学综合）
6. ✅ **与套路一完美契合**（组牌/记牌=局面信念建模）

### 与现有套路的关系

| 套路 | 对应模块 | 关系 |
|------|---------|------|
| 套路一：局面信念建模 | 组牌+记牌+策略 | 组牌/记牌输出就是局面信念 |
| 套路二：多模块评估 | 组牌+记牌+策略+动作 | 每个模块就是一个 specialized 评估 |
| 套路三：Memory | 记牌模块 | LSTM/Transformer 建模历史 |
| 套路六：模仿学习 | 动作模块 | 用 M3 胜局做 BC 训练 |
| **套路七：模块化训练** | **全部** | **训练方法论，贯穿所有套路** |

---

## 套路六：从模仿学习起步

直接 RL 的问题：探索空间太大，没有有效引导。

```
阶段 1（2-4周）：模仿学习
├─ 爬取线上平台高段位玩家牌谱
├─ 训 Policy Network 模仿强手动作
└─ 得到一个"有基础牌感"的 baseline

阶段 2（2-4周）：RL 精修
├─ AlphaZero 风格 self-play
├─ 用模仿学习模型做 MCTS rollout 的 baseline
└─ 逐步超越模仿学习的水平

阶段 3（ongoing）：对战 + 持续进化
├─ 开放窗口收集真实玩家反馈
└─ 对手池 + 持续 self-play
```