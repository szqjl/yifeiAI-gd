---
created: 2026-06-02
updated: 2026-06-02
reviewed: 2026-06-02
status: 活跃
tags: [调研, GitHub, 技术]
related_gua: []
related_iter: []
next_review: 2026-09-02
---

# 掼蛋 AI GitHub 技术调研报告

基于 GitHub 搜索和论文分析，整理了掼蛋 AI 的成熟技术方案。

---

## 一、主要开源项目汇总

| 项目名称 | 作者/机构 | GitHub 地址 | 技术方案 | 状态 | 核心特性 |
|---------|----------|------------|---------|------|---------|
| **Danzero** | 中科大（赵鉴团队） | https://github.com/AltmanD/guandan_mcc | Deep Monte Carlo (DMC) + value-based | ✅ 已开源 | 首个掼蛋 AI benchmark，K=2 动作过滤最优 |
| **Danzero+** | 同上 | https://github.com/submit-paper/Danzero_plus | DMC + PPO + top-K 动作筛选 | ✅ 已开源 | 解决 10^6 动作空间问题，性能更优 |
| **OpenGuanDan** | 南京邮电大学 | https://github.com/GameAI-NJUPT/OpenGuanDan | 基准平台 + DMC | ✅ 已开源 | 大规模基准平台，支持人类-AI 交互，RL 算法评估 |
| **AltmanD/Guandan** | AltmanD | https://github.com/AltmanD/Guandan | 游戏引擎（无 AI） | ✅ 已开源 | 完整掼蛋规则实现，可作为基础引擎参考 |
| **LSTM-Kirigaya/NUAA-guandan** | 南京航空航天大学 | https://github.com/LSTM-Kirigaya/NUAA-guandan | 模仿学习 + 深度 RL | ✅ 已开源 | 学生项目，训练入口完整 |
| **LLM4CardGame** | 清华 THUDM | https://github.com/THUDM/LLM4CardGame | 大语言模型微调 | ✅ 已开源 | GLM 微调后在 8 种卡牌游戏中表现优秀，掼蛋能力第一 |

---

## 二、技术架构对比

### 1. Danzero 系列（中科大）

**Danzero（原版）**
- **算法**：Deep Monte Carlo (DMC) + value-based
- **架构**：分布式训练框架（Actor-Learner 分离）
- **状态编码**：513 维状态向量
- **动作处理**：输入 (state, action) 输出 Q 值，O(1) 复杂度
- **训练资源**：160 个 CPU + 1 个 GPU，训练 30 天
- **表现**：优于 8 个规则 AI，达到人类水平

**Danzero+（改进版）**
- **算法**：DMC + PPO 融合
- **创新点**：
  - 用预训练 DMC 模型筛选 top-K 动作（K=2 最优）
  - 只在 K 个候选动作上训练策略网络
  - 解决 10^6 动作空间对 PPO 的挑战
- **架构**：
  ```
  两阶段训练：
  Phase 1：训练 value-based teacher（Danzero 原版）
  Phase 2：用 teacher 筛 top-K 动作，喂 policy net（PPO）训练
  ```
- **表现**：性能更优，是目前最成熟的开源方案之一

---

### 2. OpenGuanDan（南京邮电大学）

**定位**：大规模基准平台，而非单一算法
- **功能**：
  - 高效的掼蛋模拟器
  - 内置多种 Agent（学习型 + 规则型）
  - 独立的 API（每个玩家独立接口）
  - 支持人类-AI 交互
  - 支持与大语言模型集成
- **推荐算法**：Deep Monte Carlo (DMC)
- **特性**：
  - 多人组队游戏（2v2）
  - 多回合决策（长 horizon）
  - 不完美信息（只看到自己手牌）
  - 动态团队配合
- **实验结论**：学习型 Agent 显著优于规则型，但尚未达到超人表现

---

### 3. SDMC（南京大学）

**论文**：基于软深度蒙特卡洛的掼蛋扑克博弈求解
- **算法**：Soft Deep Monte Carlo (SDMC)
- **创新点**：
  - **软启动**：融合专家知识加速训练收敛
  - **软动作采样**：实时游戏中用采样策略迷惑对手
  - 防止对手利用固定策略
- **成就**：第二届中国人工智能博弈算法比赛冠军
- **遗憾**：未开源

---

### 4. 大模型方案（清华 THUDM）

**项目**：LLM4CardGame
- **方案**：用高质量游戏数据微调大语言模型
- **模型**：GLM4-9B-Chat-mix（微调后表现最佳）
- **表现**：
  - 在掼蛋、斗地主等 8 种游戏中均表现优秀
  - 掼蛋能力超过欢乐掼蛋（规则 AI）
  - 配合能力优于纯强化学习方案
- **挑战**：推理延迟高，难以实时部署
- **对比**：
  | 维度 | 大模型微调 | 强化学习（Danzero+） |
  |-----|----------|---------------------|
  | 数据需求 | 100 万轨迹 | 自对弈生成 |
  | 配合能力 | 较好（有语义理解） | 弱 |
  | 拟人化 | 天然好 | 难 |
  | 推理延迟 | 高 | 低 |

---

## 三、技术成熟度分析

### 最成熟的技术方案

| 方案 | 成熟度 | 推荐度 | 原因 |
|-----|-------|-------|------|
| **Danzero+** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 完全开源，性能最优秀，社区验证充分 |
| **OpenGuanDan** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 基准平台，支持多种算法评估 |
| **规则 AI** | ⭐⭐⭐⭐ | ⭐⭐⭐ | 实现简单，适合入门，但上限低 |
| **大模型微调** | ⭐⭐⭐ | ⭐⭐ | 配合能力强，但延迟高，成本高 |

---

## 四、技术选型建议

### 方案 A：快速原型（推荐）

基于 **Danzero+** + **OpenGuanDan**
- **优点**：
  - 完全开源，直接可用
  - 性能优秀，已验证
  - 社区支持好
  - 上手快
- **缺点**：配合能力有待提升
- **适用场景**：快速出原型，短期验证

---

### 方案 B：进阶优化（推荐）

基于 **Danzero+** 基础，重点攻克 **配合策略**
- **改进方向**：
  - 队友意图理解
  - 团队协作建模
  - 信号传递机制
- **参考**：
  - Danzero 用共享 LSTM 编码器 + 独立决策头
  - 可尝试反绎学习（ABL）融合逻辑规则
- **适用场景**：追求更高性能，技术攻坚

---

### 方案 C：探索性（不推荐）

基于 **大模型微调**
- **优点**：配合能力、拟人化天然好
- **缺点**：
  - 推理延迟高，难以实时部署
  - 训练成本高
  - 可解释性低
- **适用场景**：研究探索，产品化需等待技术成熟

---

## 五、GitHub 项目使用指南

### 1. 使用 OpenGuanDan 进行评估

```bash
git clone https://github.com/GameAI-NJUPT/OpenGuanDan
cd OpenGuanDan
# 按照项目文档进行配置和运行
```

**用途**：
- 作为训练和评估平台
- 对比不同算法性能
- 进行人类-AI 对战测试

---

### 2. 使用 Danzero+ 作为基线

```bash
git clone https://github.com/submit-paper/Danzero_plus
cd Danzero_plus
# 按照项目文档配置
```

**用途**：
- 作为算法 baseline
- 研究动作空间压缩方法
- 参考分布式训练框架

---

## 六、关键技术要点

### 1. 动作空间压缩

| 方案 | 实现 | 推荐度 |
|-----|------|-------|
| **Danzero** | value-based，网络输入 (state, action) 输出 Q 值 | ⭐⭐⭐⭐ |
| **Danzero+** | top-K 动作筛选（K=2 最优），然后 PPO | ⭐⭐⭐⭐⭐ |
| **SDMC** | 软动作采样，结合领域知识剪枝 | ⭐⭐⭐⭐（未开源） |

---

### 2. 状态编码

- **卡牌编码**：54 维向量（每张牌 3 种可能：0/1/2 张）
- **状态向量**：513 维（手牌、剩余牌、历史出牌、玩家信息等）
- **参考**：Danzero 的编码方案已验证有效

---

### 3. 训练框架

- **架构**：Actor-Learner 分离（Actor 负责采样，Learner 负责更新）
- **通信**：ZMQ（分布式环境）
- **框架**：TensorFlow 或 PyTorch

---

## 七、下一步行动建议

1. **立即**：克隆 OpenGuanDan 和 Danzero+ 项目，跑通 demo
2. **短期**：基于 Danzero+ 实现基础对战能力，验证可行性
3. **中期**：重点攻关配合策略，提升 2v2 协作能力
4. **长期**：探索拟人化出牌风格（可选）

---

## 八、参考资源汇总

### 论文
| 论文 | arXiv | 会议 |
|-----|-------|------|
| DanZero: Mastering GuanDan Game with Reinforcement Learning | 2210.17087 | COG 2023 |
| DanZero+: Dominating the GuanDan Game through Reinforcement Learning | 2312.02561 | - |
| OpenGuanDan: A Large-Scale Imperfect Information Game Benchmark | 2602.00676 | ICML 2026？ |
| Solving GuanDan Poker Games with Deep Reinforcement Learning（SDMC） | - | 计算机研究与发展 2024 |

### GitHub 项目
- https://github.com/AltmanD/guandan_mcc
- https://github.com/submit-paper/Danzero_plus
- https://github.com/GameAI-NJUPT/OpenGuanDan
- https://github.com/THUDM/LLM4CardGame

---

**最后更新**：2026-06-02
**调研工具**：GitHub 搜索 + arXiv 论文分析
