---
created: 2026-08-24
updated: 2026-08-24
status: 活跃
tags: [调研, FableDan, DMC, 自学习, V8]
related_gua: [GUA-039a, GUA-039b]
related_iter: []
next_review: 2026-09-24
---

# FableDan `train_demo` 样本观测记录

> **目的**：跑通 FableDan 最小 DMC 自对弈管道（选项 a），记录单条样本长什么样、回报如何贴标签，为后续 **V8 自学习** 设计提供对照真源。  
> **代码位置**：`external/FableDan/`（本仓库 vendor，非交付线）。  
> **关联**：[`掼蛋AI自我进化-随机应变套路.md`](../guandan-brain/掼蛋AI自我进化-随机应变套路.md)、ISSUES `GUA-039a/039b`（V7 自对弈基础设施，未关单）。

---

## 1. 执行记录（本机 2026-08-24）

### 1.1 命令

```bash
cd external/FableDan
mkdir -p ckpts
python -m fabledan.train_demo --episodes 500 --eval-every 250 --eval-games 30 --seed 42 --out ckpts/demo_mlp.npz
```

### 1.2 结果摘要

| 指标 | ep 250 | ep 500 |
|------|--------|--------|
| MSE loss（近 200 step 均值） | 0.2711 | 0.2826 |
| vs RandomAgent | 73% | 73% |
| vs RuleAgent | 13% | 13% |
| 墙钟 | ~14s | ~27s |

**解读**：

- 500 副自对弈 + 167 维 MLP 能在 **~30s** 内明显超过随机，但 **远低于规则基线**（符合 README：demo 仅验证管道，非严肃训练）。
- 严肃训练需 `python -m fabledan.train_fast`（Transformer + 多 Actor + GPU 推理服务）。

### 1.3 产物

- `external/FableDan/ckpts/demo_mlp.npz` — NumPy MLP 权重（可喂 `evaluate` / Botzone 弱 bot 测试）。

---

## 2. DMC 自学习闭环（`train_demo` 版）

```mermaid
flowchart LR
  A[play_round 四席同一 MLPAgent] --> B[每步 encode_flat 得 X]
  B --> C[ε-greedy 选 legal index]
  C --> D[副末 engine 算队分 rewards]
  D --> E["z = rewards[player] / 3"]
  E --> F[FIFO bufX/bufZ]
  F --> G[MSE: Q(X) ≈ z]
  G --> A
```

| 环节 | 实现 |
|------|------|
| 仿真 | `fabledan.engine.GuandanRound` + `play_round` |
| 策略 | `MLPAgent`：对 `obs["legal"]` 每条着法 `encode_flat` → `NumpyMLP.forward` → argmax（ε=0.10 探索） |
| 标签 | 整副 MC 回报，**同玩家本副每一步共享同一个 z** |
| 损失 | `mean((Q - z)²)`，Adam lr=3e-4 |
| 缓冲 | 默认 60000 条 FIFO；`n >= 4*batch` 后每副训练 2×batch=512 |

**重要细节**：仅当 `len(legal) >= 2` 时才会调用 `agent.act()`，因此 **唯一合法着（自动 PASS 等）不进训练集**。实测单副约 **59–72** 条样本（随机策略）。

---

## 3. 回报与 z 取值

`engine._rewards(ranking)`：按头游 + 队友名次给队分，败方对称取负。

| 队友名次 | 胜方每人 | z = reward/3 |
|----------|----------|----------------|
| 二游 | +3 | **+1.0** |
| 三游 | +2 | **+0.667** |
| 末游 | +1 | **+0.333** |
| 败方 | 负对称 | **-1.0 / -0.667 / -0.333** |

示例（ep1，RandomAgent，seed 衍生）：

- `rewards = [3, -3, 3, -3]`，`ranking = [0, 2, 1, 3]` → 队 (0,2) 胜、队友二游 → z∈{+1.0, -1.0}
- `rewards = [2, -2, 2, -2]`，队友三游 → z∈{+0.667, -0.667}

---

## 4. 单条样本结构

### 4.1 `train_demo` 路径（扁平特征）

每条样本 = `(X, player)` 入库时配上 `z`：

| 字段 | 形状/类型 | 含义 |
|------|-----------|------|
| `X` | `float32[167]` | `encode_flat(obs, chosen_move)` |
| `z` | `float32` 标量 | `rewards[player] / 3.0` |
| `player` | 0..3 | 决策席（训练时不入模，仅分 z） |

**`FLAT_DIM = 167` 构成**（`encode.py`）：

```
167 = FEAT_DIM(80) + 历史出牌聚合(60) + 上一手类型/点数/张数(27)
```

- **前 80 维** `hand_action_features`：手牌点数计数、逢人配、剩牌、完牌 flag、级牌 one-hot、**候选着**类型/claim/lead 等（与 PyTorch 路径共享）。
- **+60 维**：本局已出牌，按相对座位×点数累计。
- **+27 维**：历史最后一手非 PASS 着法的类型 one-hot + 首 claim 点数 + size。

### 4.2 `train_fast` 路径（正式训练）

每条样本（`ring.py::pop_episodes`）：

| 字段 | 形状 | 含义 |
|------|------|------|
| `toks` | `int16[*]`，≤512 | 因果历史 token 流（词表 48） |
| `feat` | `float32[80]` | **已选**候选着的 hand/action 特征 |
| `z` | `float32` | 同上 MC 目标 |
| `belief` | `float32[45]` | 训练专用：三家的隐藏手牌点数分布（oracle） |

网络：`Transformer(历史) → ctx` + `MLP(feat)` → Q；辅助 NTP + Belief（推理时丢弃）。

### 4.3 决策点 `obs` 字典（引擎产出）

| 键 | 说明 |
|----|------|
| `player` | 当前行动者 0..3 |
| `level` | 级牌 rank index 0..12 |
| `hand` | 当前手牌 int 0..107 |
| `legal` | `Move` 列表（含 PASS） |
| `lead` | 本圈需压的 `Move` 或 None（领出） |
| `left` | 四家剩牌数 |
| `done` | 四家是否已出完 |
| `events` | 本副公开事件流（供 tokenize） |

### 4.4 实测样例（首步领出，level=12/A）

```
player=3, n_legal=61, chosen=SINGLE
tokens: [BOS, LV12, P0, TRIBUTE, j, P1, RETURN, 2]  # 先进贡还贡
feat_shape: [61, 80]   # 61 个候选各 80 维
flat_nonzero: 23/167
```

跟牌样例（需压 FULL）：

```
player=2, n_legal=4, chosen=PASS
tokens_tail: ... P3 FULL J J J Q Q
left: [22, 22, 27, 27]
```

Token 词表要点：`P0..P3` 为相对视角座位；牌型 token 对应 `combos.TYPE_NAMES`（`FULL`=三带二，`SFLUSH`=同花顺等）。

---

## 5. 与 V8 规则引擎对照（自学习相关）

| 能力 | FableDan | V8（当前） |
|------|----------|------------|
| 离线整副仿真 | ✅ `engine.py` 自包含 | ❌ 依赖 OpenGuanDan / Botzone 对局 |
| 合法着枚举 | `combos.gen_moves` | `ActionListGenerator`（Botzone）；OpenGuanDan 用平台 `actionList` |
| 比牌裁判 | `combos.beats` | `botzone_adapter._beats`（细）；`trick_state.action_beats`（粗） |
| 训练样本编码 | `encode_*` 167/80 维 + token | 无统一训练编码；决策用组牌 + 残局规则 + 可选 NN 特征 |
| 自对弈训练环 | ✅ DMC 完整 | ❌ 无；GUA-039a 仅 V7 Actor/Learner 脚手架 |

**可复用度判断**：

1. **仿真器**：FableDan `engine` 与 V8 `botzone_adapter` 规则已对照过（炸弹阶梯、牌型名映射），但 **编码体系不同**（int 0–107 vs `H2`/`SB` 字符串）。
2. **最小可行 V8 自学习**：不必先上 Transformer；可学 `train_demo` 用 **扁平特征 + MLP + MC 回报**，但需 **V8 侧仿真或牌谱回放** 产 `(state, action, z)`。
3. **长期**：对齐 `train_fast` 需 V8 产出 token 化 `events` 或复用 FableDan `encode_decision`（要统一动作/历史格式）。

---

## 6. V8 自学习 — 后续研究 checklist

按优先级排列（本文件为 step-a 产出，供 step-b/c 接续）：

- [x] **step-b 对照实验**：`scripts/analysis/fabledan_v8_sim_compare.py`（结果见 §9）
- [x] **step-c 桥接 PoC**：`src/v/nn/training/fabledan_v8_bridge.py` + `scripts/analysis/fabledan_v8_selfplay_poc.py`（结果见 §10）
- [ ] **仿真源定型**：训练默认 FableDan `engine`；部署/监督信号走 V8 `actionList`（桥接层已通）
- [ ] **动作空间**：V8 平台名 `ThreeWithTwo` ↔ FableDan `FULL`；导出训练样本时 **强制 PascalCase**（见 `guandan-context.mdc`）。
- [ ] **状态编码**：短期 `encode_flat` 167 维或 V7 已有特征；长期 token 流 + Belief（与 FableDan/DanLM 对齐）。
- [ ] **回报**：沿用队分 MC（±3/±2/±1）或副级 only；**局 ⊃ 副** 口径勿混（训练可按「副」为单位，与 Botzone 一致）。
- [ ] **基础设施**：复用/扩展 `src/v/nn/training/`（GUA-039a：`actor.py`、`learner.py`、`replay_buffer.py`）。
- [ ] **评估**：vs `RuleAgent` 饱和后加 **frozen snapshot**（FableDan `train_fast` 做法）。
- [ ] **算力预期**：demo 500 副 ≈ 3 万样本 / 30s CPU；严肃训练 = GPU 天级（见 FableDan `DESIGN.md`）。

---

## 7. 复现命令速查

```bash
# 管道测试（本记录所用）
cd external/FableDan && python -m fabledan.train_demo --episodes 500 --eval-every 250 --seed 42

# 评估 demo 权重
python -m fabledan.evaluate --a ckpts/demo_mlp.npz --b rule --games 100

# 严肃训练（需 PyTorch + GPU）
python -m fabledan.train_fast --out ckpts/fast1 --actors 16
```

---

## 9. step-b 对照实验（2026-08-24）

### 9.1 脚本

```bash
# 仓库根目录
python scripts/analysis/fabledan_v8_sim_compare.py --episodes 15 --seed 42 \
    --json-out tmp/fabledan_v8_compare.json
```

**做法**：FableDan `play_round` + `RandomAgent` 采样真实决策点（`len(legal)>=2`）；同一 `obs` 上并行调用：

- FableDan：`obs["legal"]`（`gen_moves` 产物）
- V8：`ActionListGenerator.generate_lead_actions` / `generate_follow_actions`

对比三项：合法着 **数量**、抽象 **签名集合**（平台牌型 + 张数 + 比较键）、**beats** 语义（`fabledan.combos.beats` vs `botzone_adapter` 裁判逻辑）。

### 9.2 本机首轮结果（15 副，996 决策点，seed=42）

| 指标 | 结果 | 解读 |
|------|------|------|
| 合法着 **数量**一致 | 521/996（52.3%） | V8 常 **枚举更多**（同 rank 全组合、配子补炸等）；领出例 n_fd=151 vs n_v8=593 |
| **签名集合**完全一致 | 160/996（16.1%） | 预期偏低：比较键编码不同（FD `move.key` vs V8 `_rank_to_order`），且 V8 多枚举变体 |
| **beats** 不一致 | **6 / 2147**（0.28%） | **裁判语义高度一致**，可作自对弈仿真主判据 |

典型签名差（非 beats 错误）：

```
fd_only: Bomb|4|10   v8_only: Bomb|4|11   # 级牌序/比较键偏移
fd_only: StraightFlush|5|6  v8_only: StraightFlush|5|8
```

### 9.3 对 V8 自学习的含义

1. **仿真器选型**：若目标是 DMC 自对弈，**FableDan `engine` 更轻**（整副闭环 + 与训练样本同源）；V8 `ActionListGenerator` 适合 **对齐 Botzone/OpenGuanDan 部署**，但枚举更肥。
2. **训练样本来源**：可先用 FableDan 产 `(encode_*, z)`，再用本脚本 spot-check 与 V8 枚举/beats 偏差；beats 偏差 <1% 时风险可控。
3. **下一步（step-c）**：在 FableDan 引擎上挂 V8 字符串牌转换层，或反向用 `botzone_adapter` 驱动单副 judge 跑自对弈，对比 **样本吞吐** 与 **实现成本**。

---

## 10. step-c 桥接 PoC（2026-08-24）

### 10.1 新增代码

| 路径 | 作用 |
|------|------|
| `src/v/nn/training/fabledan_v8_bridge.py` | FableDan `obs` ↔ V8 手牌/`actionList`/着法 index 桥接 |
| `scripts/analysis/fabledan_v8_selfplay_poc.py` | 双路径自对弈吞吐对比 |
| `tests/test_fabledan_v8_bridge.py` | 桥接单测（4 项） |

### 10.2 架构（推荐训练管线）

```
FableDan GuandanRound（仿真 + MC 回报 z）
        │
        ├─► fd_native：encode_flat(167) + z          ← DMC 最快路径
        │
        └─► fd_v8_bridge：obs_to_v8_context
                 → ActionListGenerator（平台 actionList）
                 → V8TrainingSample + z
                 → v8_action_to_fd_index → 引擎执行
```

**不采用**「纯 V8 无引擎自对弈」：V8 无整副仿真，必须依赖 FableDan `engine` 或平台 judge。

### 10.3 命令

```bash
python -m pytest tests/test_fabledan_v8_bridge.py -q

python scripts/analysis/fabledan_v8_selfplay_poc.py --episodes 25 --json-out tmp/step_c.json
```

### 10.4 本机结果（25 副，seed 42/43）

| 路径 | 样本数 | 吞吐 | 副/秒 |
|------|--------|------|-------|
| **fd_native**（FableDan flat） | 1734 | ~4200 samples/s | ~60 |
| **fd_v8_bridge**（+V8 actionList，仅可映射着法） | 1712 | ~300 samples/s | ~4.4 |
| 吞吐比 | | **~0.07×** | V8 枚举 + 映射扫描开销大 |

**V8→FD 映射**：PoC 仅从「可映射到 FableDan legal」的 V8 着法中采样 → **100%** 合法执行。若随机抽全量 V8 列表，约 **82%** 可映射（其余为 V8 多枚举变体，FD 无对应）。

**瓶颈**：每步对 `len(actionList)`（领出可达数百）做 multiset 匹配；训练管线可缓存或按签名索引优化。

**V8 样本字段示例**：

```json
{
  "player": 3,
  "cur_rank": "8",
  "n_v8_legal": 23,
  "n_fd_legal": 18,
  "chosen_type": "Bomb",
  "chosen_v8_index": 14,
  "chosen_fd_index": 17,
  "z_mc": -0.667
}
```

### 10.5 结论（V8 自学习落地建议）

1. **仿真**：固定用 FableDan `engine`（轻、与 DMC 样本同源）。
2. **动作空间**：若要学「与 Botzone 一致的 actionList」，用 `fabledan_v8_bridge` 产 `V8TrainingSample`；执行仍走 FD index。
3. **特征**：短期可并行保留 `encode_flat`（167 维）与 `actionList` 索引；长期对齐 `train_fast` token 流。
4. **基础设施**：~~下一步接 GUA-039a `replay_buffer` + 简易 learner~~ → **已落地** `DMCLearner` + `run_fd_dmc_selfplay.py`（§11）；ZMQ / v1006 Actor 仍占位。

---

## 11. GUA-039a fd_native DMC 跑通（2026-08-24）

### 11.1 模块

| 路径 | 作用 |
|------|------|
| `src/v/nn/training/replay_buffer.py` | FIFO `(feature, z_mc)` |
| `src/v/nn/training/dmc_mlp.py` | NumPy MLP，167 维 `encode_flat` |
| `src/v/nn/training/actor.py` | FableDan 四席自对弈采样 |
| `src/v/nn/training/learner.py` | `DMCLearner` cycle：collect → train |
| `src/v/nn/training/zmq_bridge.py` | ZMQ 占位（默认关闭） |
| `scripts/v7/run_fd_dmc_selfplay.py` | CLI |
| `tests/test_v7_selfplay_039a.py` | 5 项 pytest |

### 11.2 命令

```bash
python -m pytest tests/test_v7_selfplay_039a.py -q

python scripts/v7/run_fd_dmc_selfplay.py --cycles 10 --episodes-per-cycle 50 \
    --eval-every 5 --out models/dmc_fd_native.npz

# V8 actionList 采样（同一 DMCLearner / 同一 167 维特征）
python scripts/v7/run_fd_dmc_selfplay.py --sample-route fd_v8_bridge \
    --cycles 5 --episodes-per-cycle 20 --out models/dmc_v8_bridge.npz

# 混合采样
python scripts/v7/run_fd_dmc_selfplay.py --sample-route mixed --cycles 8
```

### 11.3 本机冒烟（8 cycle × 40 ep）

- 24742 samples，~1446 samples/s
- loss ~0.67–0.72；eval vs RuleAgent 0%→10%（样本仍少，属预期）
- 权重：`models/dmc_fd_native.npz`（Layer 2，勿 commit）

### 11.4 GUA-039a 剩余（未关单）

- ZMQ 分布式 Actor-Learner
- v1006 平台 Actor + ONNX 推理
- mock 联调 / 推理延迟基线

### 11.5 fd_v8_bridge 接入同一 DMCLearner（2026-08-24）

- `LearnerConfig.sample_route`：`fd_native` | `fd_v8_bridge` | `mixed`
- V8 路径：枚举 `ActionListGenerator` → 仅从可映射着法采样 → `V8TrainingSample`（含 `action_list` / `chosen_v8_index`）+ `encode_mc_feature`（167 维，与 fd_native 同 MLP）
- `learner.last_v8_samples` 保留最近 cycle 的 V8 元数据供导出/调试
- CLI：`--sample-route fd_v8_bridge`
- 导出：`learner.export_v8_samples(path)` 或 CLI `--export-v8-jsonl tmp/v8_samples.jsonl`（每 cycle 追加，含完整 `action_list` / `chosen_action` / `hand_v8` / `z_mc`）

---

## 8. 参考文件索引

| 文件 | 作用 |
|------|------|
| `external/FableDan/fabledan/train_demo.py` | NumPy MLP + DMC 最小环 |
| `external/FableDan/fabledan/train_fast.py` | 多进程 Actor + GPU 推理 + Learner |
| `external/FableDan/fabledan/ring.py` | 并发多副 + `(toks, feat, z, belief)` |
| `external/FableDan/fabledan/encode.py` | `FEAT_DIM=80`, `FLAT_DIM=167`, tokenize |
| `external/FableDan/fabledan/engine.py` | 单副仿真与 `_rewards` |
| `external/FableDan/DESIGN.md` | Belief / TD-λ / 对手池路线图 |
| `src/communication/botzone_adapter.py` | V8 Botzone 合法着与 `_beats` |
| `src/v/nn/training/fabledan_v8_bridge.py` | step-c：FableDan obs ↔ V8 actionList 桥接 |
