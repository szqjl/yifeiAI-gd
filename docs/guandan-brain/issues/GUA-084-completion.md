# GUA-084 完成定义（五星炸保护 / SF 分支保炸候选）

> **登记**：2026-06-01  
> **回放锚点**：`game_records_v7/20260628091704590941` 副 `[11]-[2]`（yf1 贡后 27 张，级牌 8）  
> **根因个案**：`_basic_classify` 正确识别 **五星 10**（CT×2 HT ST DT），但 `SF_FIRST` + `break_bombs=True` 将整炸扔进 singles → 三带二贪心配 777+对10、999+对10，**五星炸消失**。

## 与 GUA-080 冻结的关系（必读）

| GUA-080 冻结项 | GUA-084 是否触碰 | 说明 |
|----------------|------------------|------|
| `_score_plan_v2` 四维权重 | **否** | 不改 0.5/0.3/0.1/0.1 |
| `determine_role` 阈值 | **否** | |
| 枚举策略 **数量** Top3 截断 | **否** | 仍 `enumerate_groupings()[:3]` |
| **拆炸结构规则** | **是（批准例外）** | 修正「5+ 同点整炸误拆」**逻辑 bug**，非为抬 KPI 调参 |
| SF 分支 **新增 1 条候选** | **是（批准例外）** | 仅 +1 方案参与评分，不增权重 |

**定音**：GUA-084 属于 **PB-001 / GUA-072 拆炸时序** 的结构性补丁；实施后须 **3 局冒烟 + R-G080-4 零退化**，但 **不以副胜率升降作为关单条件**（与 GUA-080 组牌冻结 KPI 条款一致）。

---

## 目标行为（三条规则）

### R-G084-1 · 三带二禁止「吃炸对」

**规则**：`_detect_three_with_two` 配对时，**禁止**使用「本应保留为炸弹（≥4 张同 rank）」的对子。

**判定**（实现任选其一，推荐 A）：

| 方案 | 做法 |
|------|------|
| **A（推荐）** | 配对前维护 `rank_count`（当前 pool 中该 rank 总张数）；若 `count(rank) ≥ 4` 或该 rank 已在 `remaining_bombs` 中 → **跳过**该 pair，尝试下一对 |
| B | 三带二前先 `_classify_no_bombs` 的 pair 仅来自 `count≤3` 的 rank |

**不改**：三张侧贪心顺序、钢板/顺子/三连对 pass 顺序。

**pytest 锚点**：五星 10 已保留为炸时，777 不得再配 CT CT；应配 22 或留对子给 QQQ。

---

### R-G084-2 · 5+ 同点：保 4 星核，限量 peel（替代整炸 dump）

**替换** `_make_plan_from_sf` Step2 中对 `break_bombs=True` 的「整炸 `pool_s.extend(rb)`」逻辑。

**常量**：

```text
BOMB_CORE_MIN = 4          # 掼蛋最小炸弹张数
```

**拆炸决策表**（`break_bombs=False` 时 peel=0，炸弹全留）：

| 炸弹张数 n | rank 条件 | peel 上限 `max_peel = n - 4` | 默认枚举（break_bombs=True） |
|------------|-----------|------------------------------|--------------------------------|
| n ≤ 4 | rank ≤ 10 | 可 **整炸** 进 singles（**维持 GUA-072**） | peel = n（整炸） |
| n ≤ 4 | rank > 10 | 不拆 | peel = 0 |
| n ≥ 5 | 任意 | max_peel = n − 4 | peel ∈ {0, 1, …, max_peel} **按方案生成变体** |

**peel 语义**：

- **保留**：`core = bomb[0:4]`（按 `_card_rank_value` + 花色稳定排序后取前 4 张）→ `remaining_bombs`
- **剥离**：`peel = bomb[4:4+peel_count]` → 进 `pool_s`，仅用于 **同花顺 / 顺子 / 三连对**（multi_pass 既有逻辑），**不得**在 Step5 重分类后再把同 rank 4 张以下拼回三带二对子（与 R-G084-1 联动）

**用户口径映射**：

| n | 允许 |
|---|------|
| **5** | 保 4 炸 + 最多 **拆 1 张** 组 SF/顺子 |
| **6** | 保 4 炸 + 拆 **1 张**（同 5 星）或拆 **2 张** 组 SF / 三连对 / 顺子 |
| **7+** | 依次类推，peel ≤ n−4 |

**最小实现（Phase A）**：

1. 新增 `_split_bomb_for_break(bomb, peel_count) -> (core_bomb|None, peeled_singles)`
2. `n≥5` 且 `break_bombs=True`：对 **每个** 大炸枚举 `peel_count=0..max_peel`（可先 **只实现 0 与 max_peel** 两个端点，pytest 用 yf1 手牌要求 peel=0 方案进 Top3）
3. `n≤4` 且 `_safe_to_break_bomb`：保持现有整炸行为

**Phase B（同 GUA 关单前可选）**：6 星中间 peel=1 变体；7 星 peel=1,2,3 全枚举（注意 dedup key 去重）。

**pytest 锚点（yf1 贡后手牌，curRank=8）**：

- [ ] 存在方案含 **5 炸 10** 或 **4 炸 10 + 1 单 10**，且 **无**「777+对10 且 999+对10 同时消耗 4 张 10」
- [ ] `check_grouping_engine.py` 最优方案 **炸弹数 ≥ 2**（K 炸 + 10 炸）或 score 明确优于现 SF_FIRST 0.43 错案

---

### R-G084-3 · 有 SF 时追加 BOMB_FIRST 候选

**现状**：`all_sf_results` 非空时 **只** 生成 `SF_FIRST / ROUND_OPTIMAL / ALL_COMBOS`，且 **全部** `break_bombs=True` → **无保炸方案**。

**最小改法**（`grouping_engine.py` `_enumerate_plans`，约 L1467）：

```python
# 在现有 SF_FIRST × SF候选 循环之后追加一条（每个 SF 候选 1 条，或仅对 best SF 候选 1 条）
plans.append(_make_plan_from_sf(
    nat, wild, rem_s, rem_p, rem_t, rem_w, res_b,
    "BOMB_FIRST", break_bombs=False, double_st=False,
))
```

**推荐**：**每个 SF 候选各 +1 条 BOMB_FIRST**（与 SF 同结构、保炸），dedup 后仍 ≤3 条输出；若超 3，按 **score 排序** 再 `[:3]`（GUA-074 不变）。

**预期**：yf1 手牌 Top1 变为 **BOMB_FIRST**（5 炸 10 + 4 炸 K + SF + 三带二用 22 等对），或 SF_FIRST 与 BOMB_FIRST 同分但 bomb 结构正确。

**pytest**：

- [ ] `_enumerate_plans(hand, "8", dedup=False)` 含 `strategy=="BOMB_FIRST"` 且 `len(bombs)>=2`
- [ ] `enumerate_groupings(hand,"8")[0].bombs` 含 5 张 10

---

## 最小代码触点（仅 `grouping_engine.py`）

| 函数 | 改动 |
|------|------|
| `_detect_three_with_two` | R-G084-1：跳过「炸 reserved」对子 |
| `_make_plan_from_sf` Step2 | R-G084-2：`_split_bomb_for_break` 替代 `pool_s.extend(rb)` |
| `_enumerate_plans` | R-G084-3：SF 分支 + BOMB_FIRST；可选 peel 变体乘积 dedup |
| `_score_plan_v2` | **不改** |
| `enumerate_groupings` | **不改** 签名；行为随 plans 变 |

**预估 diff**：~80–120 行 + 新测 `tests/test_gua084_bomb_core_protect.py`（≥6 case）。

**验收脚本**：

```bash
python scripts/checks/check_grouping_engine.py --hand "S2,H2,C3,C3,..." --rank 8
```

---

## 关单条件

> **禁止伪关单**：回放 `90941` 仅作发现样例；**不得**要求批跑再抽到同副 27 张验证首出（ISSUES「复盘→验收」定音）。关单 = **构造态 pytest / check 脚本** + **R-G080-4 零退化**。

- [x] R-G084-1/2/3 代码合入 + pytest ≥6 pass（`test_gua084_bomb_core_protect.py` 10/10；grouping 回归 147 pass）
- [x] **构造态**：贡后 HAND 字符串 + `check_grouping_engine --rank 8` → Top **5炸10+4炸K**，score **≈0.606**，无 TWT 对10
- [ ] R-G080-4：3 局冒烟 **零** scanner/card_mask 降级（**非**同副复现）
- [ ] **不要求**副胜率回升（GUA-080 冻结 KPI 条款）

## 关联

- GUA-080 / [[PB-001-gua072-bomb-break-timing]]（拆炸时序真源）
- GUA-072（≤10 小炸可拆 — **4 星**；GUA-084 约束 **5+ 星**）
- GUA-063（`to_card_mask` is_core；5 炸 is_core=1.0）
- GUA-081（决策层三带二 fallback — **本 GUA 只动组牌**）
- PRINCIPLES **RH-P02 / CG-B03**（勿破炸组 SF — 组牌层对齐）

## 非目标

- 不改 `ultimate_win_rate_engine_v7` 推荐器 / Guard
- 不调 `_score_plan_v2` 权重
- 不解决 `card_mask` JSON 同 key 覆盖（GUA-079 另项）
