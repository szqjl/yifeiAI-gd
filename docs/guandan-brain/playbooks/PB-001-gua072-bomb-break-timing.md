# PB-001：GUA-072 拆炸 — 时序押后优于改阈值

| 字段 | 内容 |
|------|------|
| **场景** | 组牌引擎多策略分支（BOMB_FIRST / ROUND_OPTIMAL）；需同时 **保牌力/保炸** 与 **去单化/结构优化** |
| **问题** | ≤10 小炸在 **Step1 SF 池** 被 GUA-072 **提前拆入普通池** → 三分支结构相同 → `BOMB_FIRST` 名存实亡 → 三炸牌 **主攻变助攻** |
| **做法** | **不改** `_safe_to_break_bomb` 阈值；把拆炸从 Step1 **押后** 到 `_make_plan_from_sf` **Step2**，由现有 `break_bombs` 门控 |
| **反例** | 在 SF 池构建时预拆小炸；为单局加 if-else 保炸；单独建 `test_gua080_*.py` 而不走组牌引擎验收 |
| **验证** | 见下文「验证」节 |
| **关联** | GUA-080、GUA-072；commit `f91f0af`（`grouping_engine.py`）；[`GUA-080-completion.md`](../issues/GUA-080-completion.md) |
| **Skill / check** | WF-05 · [`guandan-grouping-engine`](../../../.cursor/skills/guandan-grouping-engine/SKILL.md) · `check_grouping_engine.py --pre-dedup` |

---

## 背景

回放 `20260621224308510816` 第16副：`_basic_classify` 识别 **五星8 + 四T + 四Q** 三炸，修复前引擎仅输出 **1 炸 / power=1 / 助攻**。根因不是 `_score_power` 算错，而是 **拆炸发生早于策略分支**，导致 BOMB_FIRST / ROUND_OPTIMAL / ALL_COMBOS 去重后只剩 1 方案。

## 做法（时序定音）

### 修复前（反模式）

```text
Step1 SF池 = 非炸 + 预拆 ≤10 炸（safe_bomb_cards）
     ↓
三分支（break_bombs 差异无效，8/T 已不在 reserved_bombs）
     ↓
multi_pass 组三连对 → 仅 Q 炸
```

### 修复后（本 Playbook）

```text
Step1 SF池 = 仅非炸牌；all_bombs 全部保留
     ↓
Step2 _make_plan_from_sf：
  · BOMB_FIRST     break_bombs=False → 保留全部炸弹
  · ROUND_OPTIMAL  break_bombs=True  → GUA-072 拆 ≤10 炸，去单化
  · ALL_COMBOS     break_bombs=True  + 双顺子
     ↓
Step4 multi_pass → Step5 重分类 → 评分选优
```

**代码触点**（`src/v/nn/features/grouping_engine.py` · `_enumerate_plans`）：

- 删除 Step1 的 `safe_bomb_cards` 预拆
- `protected_bombs` → **`all_bombs = bombs[:]`** 传入各策略
- SF 检测仍用 Step1 专用 `_detect_straight_flushes`（**不可**塞进 multi_pass，见 GUA-080-completion SF 核查）

### 设计原则（可复用到其他模块）

| 原则 | 说明 |
|------|------|
| **策略分支前不要消耗「本应由分支决定」的资源** | 拆不拆炸应由 `break_bombs` 决定，不应在公共前置步骤偷偷拆掉 |
| **优先改时序，其次改阈值** | 同一阈值下，押后执行可产出 **2 类方案**（保炸 vs 结构），无需新参数 |
| **验收看策略分化** | `--pre-dedup` 应看到 BOMB_FIRST 与 ROUND_OPTIMAL **结构不同** |

## 验证

### 1. 组牌引擎（唯一验收入口）

```bash
python scripts/checks/check_grouping_engine.py \
  --hand "D2,C3,D3,S5,D5,S6,H6,D6,C7,D7,S8,H8,C8,C8,D8,S9,C9,HT,HT,CT,CT,SQ,HQ,CQ,DQ,DK,SA" \
  --rank J --pre-dedup
```

**通过标准（PB-001 标杆手）**：

| 策略 | 炸数 | power | 角色 | 总分（约） |
|------|------|-------|------|------------|
| BOMB_FIRST | **3** | **5** | **主攻** | **~0.46** |
| ROUND_OPTIMAL | 1 | 1 | 助攻 | ~0.26 |

去重后 **≥2 种结构**；`enumerate_groupings` 的 best 应为 **BOMB_FIRST**。

### 2. 回归

```bash
python -m pytest tests/test_grouping_engine.py -q
```

### 3. 批跑（GUA-080 关单观测，非 PB 必跑）

3 局 V7 批跑 + `card_mask` 炸弹组数分布；见 GUA-080-completion 关单条件。

## 反例

- ❌ **改 GUA-072 阈值**（如一律不可拆 8/T）— 会伤 ROUND_OPTIMAL 去单化路径，应先试时序押后  
- ❌ **Step1 预拆小炸「为了方便 SF 检测」** — SF 池应是非炸牌；需 SF 时走 `_detect_straight_flushes`，勿拆炸进池  
- ❌ **只测 `enumerate_groupings` 去重后 1 方案** — 必须用 `--pre-dedup` 看三分支是否分化  
- ❌ **忽略 grouping_scanner 降级** — 实战若 import 失败，单测通过仍可能弱于对战（见 GUA-080-completion §grouping_scanner）

## 延伸阅读

- 个案与关单：[`issues/GUA-080-completion.md`](../issues/GUA-080-completion.md)  
- 工作流：[`工作流.md`](../工作流.md) WF-05  
- SF 与 multi_pass 对比：`scripts/analysis/compare_sf_detection_vs_multipass.py`
