# §8.2 30 局 offline regression diff（regression-lalala-v1）

| 字段 | 内容 |
|------|------|
| 日期 | 2026-05-31 |
| 分支 | m-dev |
| 治理依据 | [M-V-Series-治理方案.md](../governance/M-V-Series-治理方案.md) §7.1 / §8.2 |
| 回归集 | `data/manifests/regression-lalala-v1.json`（**30 个 replay JSON = 30 副**，M1 `yf1_m1` 录制；**≠** 平台 `--target-games 30` 局） |
| 本地目录 | `data/artifacts/replays/regression-lalala-v1/`（**不进 Git**） |
| 结论 | **pass** — 30/30 拉取、30/30 `GameRecorder.load_game` 无 crash、pytest 通过、决策/审计报告可生成 |

---

## 1. COS 拉取

```bash
python scripts/cos/pull_regression.py
```

| 指标 | 结果 |
|------|------|
| ok / skip / fail | **30 / 0 / 0** |
| sha256 | 30/30 校验通过 |
| 依赖 | `config/cos.env` + `cos-python-sdk-v5`（本机已安装） |

---

## 2. GameRecorder 离线 load（无 exe）

对 30 个 JSON 调用 `GameRecorder.load_game`（含 merge 逻辑）：

| 指标 | 结果 |
|------|------|
| 文件数 | 30 |
| load crash | **0** |
| 合计 `actions[]` 步 | 2927 |
| 合计 `my_decisions[]`（yf1 视角） | 785 |

**说明**：manifest 仅含 `yf1_m1` 单客户端 JSON；merge 在同目录无 `yf2_m1` 配对时退化为单文件 load，符合预期。

---

## 3. pytest

```bash
pytest tests/test_m3_gua026.py tests/test_m3_gua029.py tests/test_m3_gua031.py \
  tests/test_m3_platform_align_gua028.py tests/test_trick_state_gua027.py \
  tests/test_m3_contracts_layout.py tests/test_game_recorder_merge.py -q
```

| 结果 | 数量 |
|------|------|
| passed | **43** |
| skipped | 3（merge 集成需特定 fixture） |
| failed | 0 |

（Windows shell 不展开 `test_m3_*.py` glob；上表为仓库内全部 `test_m3_*.py` 文件。）

---

## 4. 决策模式摘要（录制基线，非 M3 重算 diff）

```bash
python scripts/analyze_decisions.py \
  --records data/artifacts/replays/regression-lalala-v1 \
  --player yf1_m1
```

| 玩家 | 副数 | 决策步 | PASS 率 | 炸弹 | 炸弹/副 |
|------|------|--------|---------|------|---------|
| yf1_m1 | 30 | 785 | **49.7%** | 40 | 1.33 |

**与 M3 行为 diff**：本轮**未**对 30 副逐手重跑 `M3DecisionEngine`（仓库尚无统一 replay→decide 对比脚本）。§8.2 最小交付为：**load 无 crash + pytest + 可读的录制基线统计**。M3 相对录制的逐步 diff 待后续 `replay→decide` 工具链接入后再填「变更局数/步数」。

---

## 5. greater_pos 审计（`audit_greater_in_records` 思路）

对同目录 30 文件跑 `audit_file` 汇总：

| 指标 | 值 |
|------|-----|
| 非 PASS 步 | 1498 |
| 单牌可比对步 | 784 |
| 录制 greater 错改（单牌） | 328（29/30 文件有样本） |

**解读**：与 [`audit_greater_in_records.py`](../../scripts/tools/audit_greater_in_records.py) 说明一致——历史 JSON 的 `greaterAction` 来自平台 notify，**不等于 M3 实战输入**；M3 对战用 WebSocket + `trick_state`（GUA-027）。本审计为**录制质量基线**，**不构成 §8.2 fail**。

---

## 6. 抽样 3 副（manifest）

| reg id | game_id（前缀） | 文件名 round | yf1 决策数 | PASS 率 | 炸弹 |
|--------|-----------------|--------------|------------|---------|------|
| reg-001 | 20260113110809115923 | 19 | 21 | ~48% | 1 |
| reg-010 | 20260421124132048517 | 23 | 26 | ~54% | 2 |
| reg-018 | 20260421140528426468 | **50** | 45 | ~44% | 3 |

reg-018 为 30 集中最长副（round=50），load 与统计均正常。

---

## 7. 通过标准对照（§8.2）

| 要求 | 状态 |
|------|------|
| 30/30 COS 拉取 | ✅ |
| 30/30 load 无 crash | ✅ |
| pytest（M3 + game_recorder） | ✅ 43 passed |
| 产出 diff/分析报告 | ✅ 本文 |
| 对 lalala 胜率 | **不要求** |
| 不提交 artifacts / game_records | ✅ 仅本文 + ITERATIONS |

---

## 8. 未覆盖（另开 ITERATIONS 行）

- **`--target-games 10` 满跑 4 批**（平台局数 / 批末 `victoryNum[0]` vs `[1]`）— 与 30 副 regression **不是同一验收**。
- **M3 逐步 replay diff** — 待工具；当前仅录制基线 + 基础设施冒烟。
