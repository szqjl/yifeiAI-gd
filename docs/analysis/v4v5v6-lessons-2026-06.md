# V4 / V5 / V6 历史教训汇总（2026-06）

> **背景**：V7 升格改造前，从 m-dev 历史 commit + 已删文档（`git show` 复原）中系统性梳理 V 系列失败教训，避免 V7 重走老路。
> **作者**：Hermes（跨分支历史调研）
> **创建**：2026-06-06
> **适用**：v7-dev 推进 GUA-037a/b/038/039a/b/045/V5+-04 时的设计参考
> **真源对照**：`docs/governance/M-V-Series-治理方案.md`（V 系列定位） · `docs/versions/MATRIX.md`（V4/V5_stage5 已 deprecated） · `docs/guandan-brain/ISSUES.md` GUA-009/045

---

## 0. 核心结论（先看这条）

**V 系列从未认真跑过对战 KPI**。

- V4/V5 时代所有训练报告聚焦**训练侧指标**（loss、准确率、收敛速度）
- 全历史文档（`历次训练效果汇总.md` 1806 行 + `方向评估与完整提升方案.md` 948 行 + `阶段5-高级策略学习.md` 1395 行 + `阶段8-强化学习整合.md` 530 行）从未出现过"对 lalala 胜率 X%"
- V5 强化学习部分明确写"**评估次数=0，无法判断胜率**"（`历次训练效果汇总.md` 行 306/330）
- 阶段 5 完全匹配准确率优化到 **41.20%**——但这是"500 样本测试集"准确率，**不是实战对战胜率**
- 阶段 5 性能提升表（行 362-378）声称"策略理解率 50%→70-80%、决策速度<50ms"——全部是**离线指标**
- **V5 早期甚至跑不起来**——`YF_V5_ANALYSIS.md` 直指根因：lalala 路径 `D:\NYGD\lalala` 根本不存在；YFAdapter 导入失败 → 决策流程中断

**这才是 V7 升格硬约束（§1.2：禁止 import M3）的根本动因**——V 系列再这样"训练好看但没打过"会无限循环。

### 0.1 关键复原数据（2026-06-07 自 git 复原）

| 指标 | 数值 | 来源 | 是否对战胜率 |
|------|------|------|------------|
| BC 完全匹配准确率 | 59.67% → 阶段 5 后 **41.20%** | 历次训练效果汇总 §9 + 阶段5 §"完全匹配准确率优化" | ❌ 测试集准确率 |
| BC 卡牌级别准确率 | 99.84% → 阶段 5 后 98.61% | 同上 | ❌ |
| 强化学习奖励（第三次） | +1316.35 改进 | 历次训练效果汇总 §1.2 | ⚠️ 训练奖励，**不是胜率** |
| 强化学习评估次数 | **0** | 历次训练效果汇总 行 306/313/330 | ❌ 完全没评 |
| V5 决策速度 | <50ms | 阶段5 §"性能提升" | ❌ 性能指标 |
| 阶段 5 内存占用 | <500MB | 同上 | ❌ |
| **V5 实战对 lalala 胜率** | **❌ 文档中无任何数据** | grep 全 5 文件 | — |
| V5 早期可用性 | **跑不起来**（lalala 路径错） | YF_V5_ANALYSIS §1 | ❌ 直接 crash |

### 0.2 用户口述修正（2026-06-07）

**用户（CEO Phil）口述**：V4/V5 当初**手动跑过对战训练**（"v4 v5我当初肯定跑过对战训练"）；V6 时期已不记得。

**含义**：
- 历史文档记录的"评估次数=0"指**自动评估器次数=0**，**不**代表从未手动跑过对战
- 用户口述的"跑过对战"可能未系统化记录，所以**5 个文档里找不到对战 KPI**
- 这恰恰印证了"未系统化记录对战 KPI"——手动跑过但**没沉淀数据** = 等于没跑
- **V6 不记得**也是教训本身：失败的项目连"我做没做过"都记不清

**对 V7 的启示**：
- **手动对战不计入 KPI**——必须有可重现的批跑脚本 + 落盘数据
- 每次对战**必须写入** `v7-win-rate-history.md`（即使只跑 3 局）
- 跑过 ≠ 记录过 ≠ 可分析过；三步缺一不可

---

## 1. V4：规则 + 适配（2025-12 ～ 2026-02）

### 1.1 架构

4 层 fallback 架构（`src/v/learn/hybrid_decision_engine_v4.py`，1069 行）：

```
Layer 1: YF Strategy（原 M1 规则适配，依赖 lalala_adapter_v4）
Layer 2: DecisionEngine（evaluation-based）
Layer 3: Knowledge Enhanced（44 条 YAML 规则）
Layer 4: Random（兜底）
```

### 1.2 关键代码现状

- 文件：`src/v/learn/hybrid_decision_engine_v4.py`（仍在 m-dev）
- 客户端：`src/communication/yf1_v4.py` / `yf2_v4.py`（**2026-05-29 deprecated 标记**）
- 决策引擎依赖 lalala_adapter_v4 → lalala 路径

### 1.3 V4 失败教训（核心 3 条）

| 教训 | 证据 | V7 应对 |
|------|------|--------|
| **依赖外部 lalala 路径** | `YF_V5_ANALYSIS.md` 显示 `D:\NYGD\lalala` 不存在，V5 早期直接跑挂 | V7 升格约束 §1.2：M3 game_records 仅离线单向读，禁止实时调用 lalala 代码 |
| **4 层 fallback 链太深** | Layer 1→2→3→4，每层都是 if-then 短路 | GUA-045 把 V7 改造成**前置 filter + 模型 + 后校验**（非"链式 fallback"） |
| **RL 仅部分集成未启用** | GUA-009 open：V4 RL "部分集成但未作为默认路径" | V7 直接以 NN 决策为主路径，不再"集成但不开" |

---

## 2. V5：混合决策 + 阶段训练（2026-02 ～ 2026-05）

### 2.1 架构

3 层 fallback（去 RL，简化自 V4）：

```
Layer 1: Rule-Based Engine
Layer 2: Knowledge Enhanced
Layer 3: Random
```

V5 stage5 进一步集成 torch + 模式识别 + 对手建模 + 动态策略调整。

### 2.2 关键代码现状

- `src/v/learn/hybrid_decision_engine_v5.py`（1131 行，仍在 m-dev）
- `src/v/learn/yf_v5_stage5_decision_engine.py`（516 行，集成 torch+RL+pattern+opponent）
- 客户端：`src/communication/yf1_v5.py` / `yf2_v5.py` / `yf1_v5_stage5.py` / `yf2_v5_stage5.py`
  - V5_stage5 已 deprecated（2026-05-29）

### 2.3 V5 训练历史硬数据（从 `历次训练效果汇总.md` 复原）

**BC 预训练（10 样本 → 13409 样本 → 阶段 5 优化）**：

| 阶段 | 数据量 | 完全匹配准确率 | 卡牌级准确率 | 备注 |
|------|--------|--------------|------------|------|
| 1（过拟合） | 10 样本 | 59.41% | — | 数据极小，无泛化 |
| 2（中期） | 252 样本 | 23.81% | — | 预测过少 76.2% |
| 3（13409 样本） | 13409 样本 | 1.53% → 59.67% | 99.84% | 50 epoch + 加权 BCE |
| **阶段 5 优化** | 10000 样本 | **41.20%**（500 样本测试） | 98.61% | **仍是测试集准确率** |
| 阶段 5 策略分类 | — | 100.00% | — | 离线指标 |
| 阶段 5 策略理解率 | — | **0.85%**（从 0.00%） | — | **新突破但接近 0** |

**重要注**：阶段 5 文档声称"策略理解率 50% → 70-80%"（性能提升表行 367），但同文档另一处说"策略理解率 0.85%"——**两处数据矛盾**。**实际可达的策略理解率约 0.85%**，远低于"70-80% 预期"。

**强化学习（自对弈，3 次）**：

| 训练 | 时间 | 关键参数 | 改进趋势 | 评估次数 |
|------|------|---------|---------|---------|
| 第一次 | 2025-12-07 21:27:05 | 50 episode, LR=0.0003, 无随机种子 | +241.33 | **0** |
| 第二次 | 2025-12-07 21:36:46 | 50 episode, LR=0.0003, 无随机种子 | **-378.95**（退化） | **0** |
| 第三次 | 2025-12-07 23:22:42 | 50 episode, LR=0.0001, seed=42, 早停=20 | **+1316.35** | **0** |

**3 次强化学习评估次数全为 0**。文档明确写"无法判断胜率"。

**V5 stage5 性能指标（全部离线）**：
- 决策速度 <50ms
- 内存占用 <500MB
- 稳定性 >99%
- 组件导入测试/客户端测试/决策功能测试全 pass

**V5 阶段 5 测试**（行 332-358）：声称"全面测试通过"，但**5 个测试全是组件级/集成级**（YFAdapter 初始化、客户端初始化、决策功能），**没有对战 KPI 测试**。

### 2.4 V5 失败教训（核心 6 条）

| 教训 | 证据 | V7 应对 |
|------|------|--------|
| **从未测过对战胜率** | 历次报告全聚焦 loss/准确率；**RL 部分评估次数=0**（行 306/330）；阶段 5 测试无对战 KPI | V7-007 队胜率硬指标；GUA-039b 30 局 vs lalala 评估 |
| **训练指标好 ≠ 实战胜率高** | 阶段 5 完全匹配率 41.20% vs 胜率未知（很可能 < 30%）；策略理解率"70-80% 预期" vs 实际 0.85% 矛盾 | V7 升格后 GUA-045 显式 guard；不准以"模型自信度高"为优化目标 |
| **性能指标与战 KPI 混淆** | 阶段 5 文档声称"决策速度<50ms、内存<500MB"是"质的飞跃"——但这些只是性能，**不是质量** | V7 升格：每条 GUA 完工定义**只问队胜率**，不问决策速度 |
| **阶段训练 0~8 全在优化训练侧** | 阶段 5/6/7 全部聚焦"策略理解率 X%"、"对手建模准确率 X%" | V7 升格后，**KPI 锁死 V7-007 队胜率**；训练指标作辅助 |
| **1312 真实数据训练不收敛** | 用户口述 + 阶段 0~8 阶段报告未给对战结论 | GUA-038 优先 M3 game_records（已筛选 victoryNum[0]>=2）；1312 留作可选补充 |
| **组件堆砌失控** | V5 stage5 = pattern+opponent+dynamic+RL 四件套集成（行 248-330） | V7 升格：V7 自有空间单一路径；禁止 import M1/M2 训练代码 |

### 2.5 V5 stage5 的"幸存价值"

虽然 stage5 客户端已 deprecated，但以下范本被 m-dev 采纳：
- `src/decision/cooperation.py` 队友保护策略模式（ABC + 4 个具体 Rule）
- `src/decision/multi_factor_evaluator.py` 动态优先级系统（ContextAdjuster 模式）
- 详见 GUA-036 已落地的 CTRL/WIND/TEAM guard

**V7 可借鉴**：策略模式（Rule ABC）+ 动态 Context 调整；但**不**直接 import 这两个文件（升格约束 §1.2 禁止 import M 系内部），V7 要 V7-native 复刻。

### 2.6 V5 跑不起来的根因（YF_V5_ANALYSIS 详细复原）

`YF_V5_ANALYSIS.md`（2025-12-04）直指 V5 早期可用性问题的根因——**外部依赖路径错误**：

**症状链**：
1. `lalala_adapter_v4.py` 第 26-28 行：`LALALA_PATH = r"D:\NYGD\lalala"`
2. 运行时：`from state import State` / `from action import Action` → ImportError
3. YFAdapter 抛 `ImportError("Failed to import base modules from {LALALA_PATH}")`
4. `HybridDecisionEngineV4._try_yf` 收到异常 → 返回空列表
5. 决策流程退到 Rule-based / Random 兜底
6. **V5 实际跑的是兜底决策，不是 V5 策略**

**次要问题**（同文档列出）：
- 决策权重分配：`rl_weight=0.2, knowledge_weight=0.3, rule_weight=0.5`（看似合理，但都依赖已失败的 lalala）
- 错误日志不明显：失败静默退到兜底，**没人知道 V5 没用上**
- 多版本共存：`lalala_adapter.py` + `lalala_adapter_v4.py` + `yf1_v5.py` + `yf2_v5.py` 互相纠缠

**文档作者开的解决方案**：
- 方案 A：lalala 模块集成进项目（`LALALA_PATH = os.path.join(__file__)`）— ✅ 后来 V5 stage5 实际走了这条路
- 方案 B：修正外部路径（仍依赖 D:\ 盘）— ❌ 治标不治本

**对 V7 的启示**：
- V7 升格约束 §1.2 严禁 import M3，正是 V5 这个根因的"免疫方案"
- V7 自有空间 `src/v/nn/` 独立，**不依赖任何外部路径**
- pytest 必跑 `test_v7_paths.py`（GUA-041 已关单 6 passed）— 路径错误要立即可见
- 任何决策回退（fallback）必须**有可见日志**，**不静默**——否则"明明失败但日志显示正常"

---

## 3. V6：MOE 实验（2026-05 短期）

### 3.1 架构

Mixture of Experts（专家混合）：多个子策略 + 路由器
- 主入口：`src/decision/cooperation.py`（cherry-pick 900 行）+ `multi_factor_evaluator.py`（879 行）
- **唯一 v6-dev 产物被采纳进 m-dev**

### 3.2 V6 失败教训

| 教训 | 证据 | V7 应对 |
|------|------|--------|
| **MOE 路由学习不收敛** | v6-dev 整体归档（无单独报告，但 cherry-pick 显式标注 `from v6-dev archive`） | V7 用单一 NN 决策 + P0 guard，不引入 MOE |
| **专家间无清晰边界** | cherry-pick 后在 m-dev 跑通过，但路径与原 V6 决策耦合不清 | V7 升格后，V7-native 重写所有 guard |
| **同样缺对战 KPI** | ITERATIONS 无 V6 vs lalala 批跑记录 | 沿用 V7-007 KPI |

### 3.3 V6 的文档缺失（与 V4-V5 对比）

`方向评估与完整提升方案.md`（2025-12-07）评估的 5 种业界方法（AlphaZero/Opponent Modeling/Evolutionary/Multi-Task/Curriculum Learning）**没列 MOE**——V6 是**外部实验**而非主流路线。最终 cherry-pick 900 行进 m-dev，但**没单独报告**。

V6 留下来的**实际有价值的部分**：
- `CooperationStrategy`（5 原则：上家出单我方跟天然单/牌力不够直接压制/中后期任何一方直接炸/防守责任原则/助攻角色原则）
- `TeammateProtectionRule`（4 个具体 Rule 抽象：HighValue/LowCardCount/CriticalStage/Bomb）
- `DynamicPrioritySystem`（4 个 ContextAdjuster：NextPlayer/PassCount/Endgame/Teammate）

——这些**已被 m-dev M3 采纳**（GUA-031 PASS-P02~P04、GUA-034 END-M01~M04），**V7 不再需要 import**（升格约束），V7-native 复刻即可。

---

## 4. V4-V5-V6 共同教训（V7 必避）

### 4.1 训练侧 vs 对战侧脱节

| 时代 | 训练侧投入 | 对战侧投入 |
|------|----------|----------|
| V4 | 阶段 0~4 BC + RL | 0 局 |
| V5 | 阶段 0~8 + stage5 高级模块 | 0 局（评估次数=0） |
| V6 | MOE 路由学习 | 0 局 |

**结论**：训练侧做了大量工作，**对战侧从未认真验证**。V7 必须打破这个循环。

**V7 应对**：
- GUA-039b 30 局 vs lalala 评估**不是装饰**，必须跑
- V7-007 队胜率 ≥50% 是**硬门槛**（V 冒烟 ON 触发条件）
- 每条 GUA 实施时**先想**："这条能不能让 lalala 胜率上升？"

### 4.2 fallback 链设计惯性

V4 = 4 层、V5 = 3 层、V7 当前也是 `_model_decision → _rule_based_decision` 两层 fallback。

**问题**：链式 fallback → 上一层出错就退下一层，**整条决策不稳定**，且"上层自信但错"时无法纠正。

**V7 应对**（GUA-045）：
```
V7 决策 = 前置 filter（V7-R01~R06 guard 壳）
       + 模型推理（4 头 NN）
       + 后校验（action_value 动态调整）
```
不再是"链式 fallback"，而是"过滤+推理+校验"。

### 4.3 组件堆砌 + 调参失控

V5 stage5 = 模式识别 + 对手建模 + 动态调整 + RL 四件套；每个组件各自训练、调参、版本管理，**没人能解释整体怎么 work**。

**V7 应对**：
- 单一 NN 决策（4 头网络）
- V7 自有空间 `src/v/nn/` 独立，不 import M1/M2 训练代码
- 模型权重走 GUA-040 COS manifest，不散落 `models/stage*_*.pth`

### 4.4 录牌链路耦合

V5 stage5 没独立录牌，复用 M1 录牌链路 → 改 M1 录牌易影响 V5。

**V7 应对**（GUA-038）：
- V7-internal 录牌（`src/v/nn/recorder/v7_recorder.py`）
- 仅离线单向读 M3 game_records 作 BC teacher，不写 M3 录牌

### 4.5 特征工程靠零填充

V5 时代特征工程也是"没牌面就填 0"——这正是 GUA-037a 当前要修的。

**V7 应对**（GUA-037a/b）：
- 静态 124 维（手牌 108 + 级牌/红心配 9 + 阶段 6 + hand count 1）
- 动态 64 维 LSTM 历史
- 总维度 188（< 200 阈值）

### 4.6 性能指标 vs 战 KPI 混淆

V5 stage5 文档（行 362-378）把以下指标当作"性能提升"：
- 决策速度 <50ms
- 内存占用 <500MB
- 稳定性 >99%

**这些只是性能指标（performance），不是质量指标（quality）**。"决策快 50ms" 不代表"决策对 50% 局"。**训练侧指标不能当作战 KPI**。

**V7 应对**：
- 每条 GUA 完工定义**只问队胜率**，**只**写"净盘 N 局 vs lalala，队胜率 ≥X%"
- 决策速度/内存/稳定性作辅助参考，但**不进完工定义**
- 完工定义模板：见 `v7-win-rate-history.md`

### 4.7 路径依赖的隐性失败（V5 跑不起来）

V5 早期**代码看起来都在**，但因 lalala 路径错，**实际跑的是兜底决策**。失败是**静默的**——错误处理吃掉异常，没人发现。

**V7 应对**：
- 任何外部依赖必须**有 fallback 失败检测**（不是静默退到兜底）
- GUA-041 路径债清理（6 passed）已关单，pytest 验证路径
- 日志策略：**fallback 必须打 WARNING**，让操作者立即发现"实际跑的是兜底"
- 决策链路加 `assert` 关键依赖（如 V7 升格约束 §1.2 校验：`assert_v_integration_gate`）

---

## 5. V7 升格硬约束（不重蹈覆辙的根本）

`V7-实施方案.md` §1.2 升格硬约束——**禁止**：

| 维度 | 禁止 |
|------|------|
| 代码 import | `from src.m.m3 import ...`（任何 M3 内部模块） |
| 实时数据 | 实时调用 M3 引擎生成 BC 标签 |
| 协议 | 改 v1006 协议以迁就 M3 |
| 录牌 | 调 M3 录牌链路（`game_recorder`） |
| 架构定性 | 把 M3 当 V7 底座（M3 = V7 底座 ❌） |

**关键**：M3 数据允许读（offline、单向 BC teacher），M3 代码不可 import。这条约束是 V 系列没 KPI 教训的直接产出。

---

## 6. V7 实施路径上 V 系列教训的对应检查点

| 阶段 | GUA | 必查"V 系列教训" |
|------|-----|-----------------|
| Phase 0 | GUA-041 | 路径债清理（V5 早期 `D:\NYGD\lalala` 教训） |
| Phase 0 | GUA-045 | P0 Guard 壳（替代 V4-V5 链式 fallback） |
| Phase 1 | GUA-037a/b | 静态+动态特征（替代 V5 零填充） |
| Phase 1 | GUA-040 | COS manifest（替代 V5 散落权重） |
| Phase 2 | GUA-038 | V7-internal 录牌（替代 V5 复用 M1 录牌） |
| Phase 3 | GUA-039a | 单 Actor + DMC（不引入 V6 MOE 路由学习） |
| Phase 3 | GUA-039b | 30 局 vs lalala 评估（**V 系列从未做过的事**） |

**红线**：每条 GUA 实施前问一次"这会让 V7-007 队胜率上升吗？"—— 答否就重新设计。

---

## 7. 参考文档（git 复原路径）

| 文档 | 复原 commit | 行数 | 关键内容 |
|------|------------|------|---------|
| `docs/training/历次训练效果汇总.md` | `6fd7b2b` | 1806 | V4/V5 训练参数 + 准确率演变；**RL 评估次数=0**（行 306/313/330） |
| `docs/training/方向评估与完整提升方案.md` | `6fd7b2b` | 948 | 阶段 0~8 实施计划；潜在问题分析；业界方法对比（5 种，未列 MOE） |
| `docs/training/阶段5-高级策略学习.md` | `6fd7b2b` | 1395 | V5 stage5 设计（pattern+opponent+dynamic）；**完全匹配率 41.20%（测试集）**；策略理解率 0.85% |
| `docs/training/阶段8-强化学习整合.md` | `6fd7b2b` | 530 | 强化学习框架搭建；"从监督到自主发现"——**但未给对战胜率** |
| `YF_V5_ANALYSIS.md`（根目录） | `590531d` | 212 | **V5 跑不起来根因：lalala 路径 `D:\NYGD\lalala` 错误**；附改进方案 |
| `docs/versions/MATRIX.md` | 现存 | 104 | V4/V5_stage5 deprecated 状态 |
| `docs/governance/M-V-Series-治理方案.md` | 现存 | 513 | V 系列定位 + 升格约束 |
| `docs/analysis/v4v5v6-lessons-2026-06.md` | 现存 | 357 | **本文件**——V4-V5-V6 教训汇总（2026-06-07 增） |
| `docs/analysis/v7-win-rate-history.md` | 现存 | — | V7 队胜率硬 KPI 日志（2026-06-07 新建） |

**复原命令**（任何 Agent 后续可验证）：
```bash
git show 6fd7b2b:docs/training/历次训练效果汇总.md
git show 6fd7b2b:docs/training/方向评估与完整提升方案.md
git show 6fd7b2b:docs/training/阶段5-高级策略学习.md
git show 6fd7b2b:docs/training/阶段8-强化学习整合.md
git show 590531d:YF_V5_ANALYSIS.md
```

**5 文件归档**（只读）：`docs/archive/v4v5/`（2026-06-07 复原，附 `README.md` 索引）

---

## 8. 一句话总结

**V 系列用 6 个月证明了一件事**：训练侧再漂亮，没对战 KPI 都是零。

V7 升格（禁止 M3 import + V7-007 队胜率硬指标 + GUA-045 P0 guard + GUA-039b 30 局评估）就是要把这个循环切断。

每条 V7 GUA 实施前重读 §4.1（共同教训）和 §6（检查点），确保不重蹈 V4-V5-V6 的覆辙。

### 8.1 三个最致命教训（红字）

1. **训练指标 ≠ 战 KPI**：阶段 5 完全匹配率 41.20% 是**测试集准确率**——V5 实际对 lalala 胜率**完全无数据**
2. **失败是静默的**：V5 因 lalala 路径错**静默退到兜底**——代码都在，决策是兜底，没人发现
3. **跑过 ≠ 记录过 ≠ 可分析过**：手动对战不沉淀 = 等于没跑；V6 不记得做过什么 = 教训本身丢失

### 8.2 V7 三道护栏（每条都对应一个 V 系列失败模式）

| 护栏 | 失败模式来源 | 文件 |
|------|------------|------|
| V7-007 队胜率 ≥30% 硬门槛 | V 系列从未量化战 KPI | `v7-win-rate-history.md` |
| GUA-045 P0 guard 壳 | V4-V5 链式 fallback 惯性 | `m3_decision_engine` 内 |
| 升格约束 §1.2 禁 import M3 | V5 lalala 路径错静默失败 | `V7-实施方案.md` §1.2 |
