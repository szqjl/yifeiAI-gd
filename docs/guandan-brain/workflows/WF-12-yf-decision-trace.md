# WF-12 · yf 出牌决策链路分析

> **目的**：对 **yf1_v7 / yf2_v7 / yf1_m3 / yf2_m3** 某一出牌步做**可复现的决策链路还原**，定位「为何我方不胜 / 副级失误 / 浪费炸弹」的根因，并导向 **GUA 登记或最小修复**。  
> **与 WF-04 分工**：WF-04 = 批跑 KPI（局胜/副胜）；**WF-12 = 单步微观决策**（哪一层选了什么、为何）。  
> **与 WF-06 分工**：WF-06 = 回放工具 + `replay_word.md` 叙事；**WF-12 = 引擎日志 + `my_decisions` 的管线级证据**。

---

## 1. 触发

| 触发词 | 示例 |
|--------|------|
| 分析 yf 决策 / 决策链路 / 为何出这手 | 「分析 yf1 步 7 为何开炸」 |
| 我方不胜根因 / 典型败招 | 「这副为何 0 胜，看关键步」 |
| GUA 回放锚点 | ISSUES 中已写 `game_id` + 步号 |

**输入最少信息**（人类任选其一）：

```text
游戏: <game_records 文件名或 game_id>
<步号>/<总步>  <谁出牌>  <牌面>
```

示例：

```text
游戏: 20260628091707150272 [yf1_v7]-[opponent_1_3]-[16]-[2].json
6/73  对手@3  ♠6 ♥6 ♦6 ♥2 ♦2
7/73  yf1_v7  ♠8 ♠8 ♣8 ♦8
```

---

## 2. Agent 必做步骤（按序）

### 2.0 Agent 自检（动手前 · 不可跳）

**yf1 / yf2 通用**；未完成即写结论 = 流程违规。

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 读 [`SCRIPT_INDEX.md`](../SCRIPT_INDEX.md) §三「yf 单步决策链路（WF-12）」 | 确认牌谱目录、日志路径 |
| 2 | **打开分析对象 JSON** | yf1：人类给的 `*yf1_v7*` / `*yf1_m3*` 文件；yf2：按 §2.1 **配对** yf2 文件 |
| 3 | **对齐目标步** → `my_decisions` 条目 | 见 §2.2；已拿到 **`context.handCards`（整手）** |
| 4 | 读 **`my_decisions.context.curRank`** | 出牌时刻级牌；**禁止**只用 JSON 根 `game_info.curRank` |
| 5 | 对 **`logs/yf1_*.log` / `logs/yf2_*.log`**（与分析对象一致） | 用 `actions[步号-1].timestamp` ±1s 补管线证据 |
| 6 | 再写圈况 → 管线 → R-Dxx | 证据含：**分析对象文件名** + `handCards_size` + 日志行 |

### 2.1 定位分析对象 JSON（yf1 / yf2）

**文件名格式**（与 `scripts/tools/yf_replay.py::RECORD_NAME_RE` 一致）：

```text
{timestamp} [{client}]-[opponent_1_3]-[{round}]-[{suffix}].json
```

#### yf1（多数情况：人类直接给文件名）

| 项 | 说明 |
|----|------|
| **入口** | 人类输入的 `game_records_v7/*yf1_v7*` 或 `game_records/*yf1_m3*` 路径 |
| **也可用** | 文件名前缀 `game_id` **仅对 yf1 文件有效**（yf1 与 JSON 内 `game_id` 一致） |
| **校验** | `player_id==0`、`player_name` 含 `yf1`；**决策读本文件 `my_decisions`**（`context.myPos` 均为 0） |
| **日志** | `logs/yf1_v7_*.log`（或 `yf1_m3`），与牌谱 `start_time` 同批 |

#### yf2（必须配对，禁止用 yf1 的 game_id）

**定音**：yf2 JSON 的 **`game_id` 与 yf1 不同**；配对键是 **`[round]-[suffix]`**，不是 `game_id`。

```text
yf1: 20260701175356173308 [yf1_v7]-[opponent_1_3]-[36]-[2].json
yf2: 20260701175356193021 [yf2_v7]-[opponent_1_3]-[36]-[2].json
```

| 优先级 | 真源 |
|--------|------|
| **①** | 配对后的 **yf2 JSON** → `my_decisions[]` |
| **②** | `logs/yf2_v7_*.log`（timestamp ±1s） |
| **③** | 任意席 JSON 的 `actions[]` → **仅圈况**，不得推断 yf2 整手 |

**配对算法**（同 `yf_replay._try_load_teammate_record`）：

1. 从 yf1 文件名解析 `[round]`、`[suffix]`。
2. 同目录逐文件匹配 `client=yf2_v7`（或 `yf2_m3`）且 **同 `[round]-[suffix]`**（勿用 `glob('*-[36]-*')`，`[]` 是字符类）。
3. 多候选时取 **文件名 timestamp 与 yf1 最接近** 者。

```python
import re
from pathlib import Path

RECORD_NAME_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)

def pair_teammate_json(yf1_path: Path) -> Path | None:
    m = RECORD_NAME_RE.match(yf1_path.name)
    if not m or "yf1" not in m.group(2):
        return None
    teammate = m.group(2).replace("yf1", "yf2", 1)
    rnd, suf = m.group(4), m.group(5)
    my_ts = int(m.group(1))
    candidates = []
    for f in yf1_path.parent.iterdir():
        sm = RECORD_NAME_RE.match(f.name)
        if sm and sm.group(2) == teammate and sm.group(4) == rnd and sm.group(5) == suf:
            candidates.append(f)
    return min(candidates, key=lambda p: abs(int(p.name.split(" ", 1)[0]) - my_ts)) if candidates else None
```

### 2.2 对齐目标步 → `my_decisions`（yf1 / yf2 共用）

**定音**：`my_decisions[].action_index` = 当时 **`actionList` 的下标（actIndex）**，**不是** `actions[]` 的步号。

| 步 | 做法 |
|----|------|
| 1 | 在分析对象 JSON 取 `play = actions[步号 - 1]` |
| 2 | 确认 **`play.cur_pos == player_id`**（yf1→0，yf2→2）；否则该步不是分析对象出牌，不能对齐 |
| 3 | 统计 **`actions[:步号]`** 内该玩家出牌次数 → **`turn_idx`**（0-based，第几次轮到本席出牌） |
| 4 | 筛 **`play_decisions`** = `my_decisions` 中 **`stage=='play'`** 或 **`stage is None 且 source=='act'`** 的条目（**排除** `tribute` / `back`） |
| 5 | 取 **`play_decisions[turn_idx]`**；用 **`action_key(decision.action) == action_key(play.cur_action)`** 校验 |
| 6 | 若 ordinal 与 action 不一致且 **`action_key` 全表唯一匹配** → 回退到该唯一条目；否则 **报错**，禁止猜 |
| 7 | 读该条的 **`context.handCards`**（整手）、**`curRank`**、**`role`**、**`card_mask`**、**`layer`** |

**禁止**：仅用 `action_key` 全表搜索（PASS / 同型重复会撞车）；禁止把 `play.cur_action` 张数当 `handCards`；禁止用 JSON 根 `game_info.curRank` 代替 `context.curRank`。

#### 对齐片段（Python，yf1/yf2 共用）

下列代码已在 **`game_records_v7/*yf1_v7*.json` 全量出牌步**（1615 步）及 **yf2 `56193021` 步 37** 上跑通；复制时保持 **`action_key` + ordinal + 双校验** 顺序不变。

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def action_key(action: Any) -> Optional[tuple]:
    """平台动作归一化：(TYPE, RANK, sorted(cards))，用于与 cur_action 比对。"""
    if not isinstance(action, list) or not action:
        return None
    typ = str(action[0]).upper()
    rank = str(action[1]).upper() if len(action) > 1 else ""
    cards_raw = action[2] if len(action) > 2 and isinstance(action[2], list) else []
    return (typ, rank, tuple(sorted(str(c).upper() for c in cards_raw)))


def is_play_decision(decision: Dict[str, Any]) -> bool:
    """play 回合决策；贡/还（tribute/back）不计入出牌 ordinal。"""
    ctx = decision.get("context") or {}
    stage = ctx.get("stage")
    if stage in ("tribute", "back"):
        return False
    if stage == "play":
        return True
    return stage is None and ctx.get("source") == "act"


def find_decision_at_step(
    game_data: Dict[str, Any], step_num: int
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    1-based 步号 → 分析对象 JSON 内对应的 my_decisions 条目 + actions 行。

    返回 (decision, play)；decision['context']['handCards'] 为出牌前整手。
    """
    actions: List[Dict[str, Any]] = game_data.get("actions") or []
    player_id = game_data.get("player_id")
    if player_id is None:
        raise ValueError("game_data missing player_id")
    if step_num < 1 or step_num > len(actions):
        raise ValueError(f"step {step_num} out of range 1..{len(actions)}")

    play = actions[step_num - 1]
    if play.get("cur_pos") != player_id:
        raise ValueError(
            f"step {step_num} cur_pos={play.get('cur_pos')} != player_id={player_id}; "
            "pick a step where the analysis subject acted"
        )

    turn_idx = sum(1 for a in actions[:step_num] if a.get("cur_pos") == player_id) - 1
    play_decisions = [d for d in game_data.get("my_decisions") or [] if is_play_decision(d)]
    if turn_idx >= len(play_decisions):
        raise ValueError(
            f"no play my_decisions[{turn_idx}] "
            f"(have {len(play_decisions)} play entries, need turn #{turn_idx + 1})"
        )

    decision = play_decisions[turn_idx]
    expected_key = action_key(play.get("cur_action"))
    if action_key(decision.get("action")) != expected_key:
        matches = [
            i
            for i, d in enumerate(play_decisions)
            if action_key(d.get("action")) == expected_key
        ]
        if len(matches) == 1:
            decision = play_decisions[matches[0]]
        else:
            raise ValueError(
                f"ordinal/action mismatch at step {step_num}: "
                f"cur_action={play.get('cur_action')!r}, "
                f"ordinal_decision={decision.get('action')!r}, "
                f"action_key_matches={matches}"
            )

    return decision, play


# --- 金样例：yf2 步 37（56173308 副 / 56193021 yf2 JSON）---
if __name__ == "__main__":
    yf2 = Path("game_records_v7/20260701175356193021 [yf2_v7]-[opponent_1_3]-[36]-[2].json")
    data = json.loads(yf2.read_text(encoding="utf-8"))
    dec, play = find_decision_at_step(data, 37)
    assert play["cur_action"][:2] == ["ThreeWithTwo", "T"]
    assert dec["context"]["curRank"] == "Q"          # 不是 game_info.curRank=2
    assert dec["context"]["handCards_size"] == 20    # 不是 cur_action 的 5 张
    assert dec["layer"] == "GUA-075推荐"
    print("OK", dec["action"], "hand", len(dec["context"]["handCards"]), "rank", dec["context"]["curRank"])
```

**金样例期望输出**（2026-07-01 批跑牌谱）：

| 字段 | 值 |
|------|-----|
| `play.cur_action` | `ThreeWithTwo/T` + 5 张（`ST ST DT S3 H3`） |
| `dec.context.handCards_size` | **20**（含未出的 `D3`） |
| `dec.context.curRank` | **`Q`** |
| `dec.layer` | `GUA-075推荐` |
| `turn_idx` | **9**（yf2 本副第 10 次出牌） |

本地一键回归：`python scripts/tools/wf12_find_decision_at_step.py`（与上文片段同源）。

**常见误读**：

| 误读 | 正确 |
|------|------|
| 用 yf1 的 `game_id` glob yf2 | yf2 用 **`[round]-[suffix]`** 配对 |
| 用 yf1 的 `my_decisions` 分析 yf2 | yf1 JSON 内 **`myPos` 恒为 0** |
| 把 `my_decisions.action_index` 当步号 | 它是 **actIndex**；步号对齐靠 **ordinal + `action_key` 双校验** |
| 全表搜第一个 `action_key` 相等 | PASS/同型重复会错；必须 **先 ordinal 再校验** |
| 把 `cur_action` 张数当整手 | 读 **`context.handCards`** |

---

| 步 | 动作 | 真源 |
|----|------|------|
| **① 定位牌谱** | V7 → `game_records_v7/`；M3 → `game_records/`。**yf1**：直接开给定文件；**yf2**：§2.1 配对 | 勿混目录 |
| **② 还原圈况** | 读 `actions[]` 该步前后 3～5 步（任一 JSON 步序相同） | 平台 notify 流水 |
| **③ 读决策快照** | 分析对象 JSON → §2.2 对齐 `my_decisions` | **禁止**跳过；**禁止**用 yf1 的 decisions 写 yf2 |
| **④ 对日志** | **`logs/yf1_*.log` 或 `logs/yf2_*.log`**（与分析对象一致）搜 ±1s | Layer 2，不进 Git |
| **⑤ 还原管线** | 按 §3 决策层顺序，写出**实际命中层**与**被跳过/拦截层** | 见下 |
| **⑥ 根因分类** | 归入 §4  taxonomy 之一（可多标签） | 导向 GUA |
| **⑦ 产出报告** | 格式见 [`工作流.md`](../工作流.md) §2.6 | 人类可读 |
| **⑧ 后续动作** | 可修 → 登记/更新 **GUA**（WF-10）+ pytest 构造态；仅观测 → 摘要写入 `replay_word.md` 或 analysis handoff | 禁止为单局写特例 |

**禁止**：

- 只凭 `actions[]` 猜意图、不读 `my_decisions` / 日志。
- **分析 yf2 却未配对 yf2 JSON，或把 `cur_action` 出牌张数当整手。**
- **用 JSON 根 `game_info.curRank` 代替 `my_decisions.context.curRank`。**
- 用 replay 逐步一致作为关单标准（ISSUES 头部「复盘发现 → 实现 → 验收」）。
- 篡改牌谱或日志。

---

## 3. V7 决策管线（`UltimateWinRateEngineV7.decide`）

自上而下，**先命中者先 return**（回退路径除外）：

| 层 | 模块 | 日志关键词 | 典型职责 |
|----|------|------------|----------|
| L0 | 组牌引擎 | `组牌引擎: role=` | `card_mask` / `group_type_map` |
| L0b | MemoryTracker + 信念 | `belief inject`（debug） | GUA-072 `_belief` |
| L1 | 残局管线 | `残局管线命中` / `Q0`～`Q3` | GUA-078；激活则常直接 return |
| L2 | **GUA-075 推荐** | `GUA-075 推荐:` → `主路径: … actIndex=` ✅ | 四场景：领出/跟上家/卡下家/让对家 |
| L2′ | 组牌保护 | `推荐被组牌保护拦截: … 拆 bomb` | 推荐有效但被 mask 挡 → **掉进回退** |
| L3 | Guard filter | `filter_action_list` | v7_guards 硬删 |
| L4 | 组牌前置过滤 | `前置过滤: role=` | `_group_consistency_filter` |
| L5 | 接风/投喂 | `接风` / `投喂` | 重排，不删 |
| L6 | NN | `模型决策` / 无 GUA-075 成功日志 | `_model_decision`（常 argmax 坍缩） |
| L7 | Heuristic 覆盖 | `heuristic top3`（debug） | 拆局 / 王滥用 → `_heuristic_select` |
| L8 | validate / fallback | `规则回退` | 最后兜底 |

**M3**：管线不同，读 `m3_decision_engine` + `TrickSequenceTracker`；WF-12 同样适用「牌谱 + my_decisions + 客户端 log」，层名换为 M3 guard Rxx。

---

## 4. 根因 taxonomy（导向 GUA）

| 标签 | 含义 | 常见修复方向 |
|------|------|--------------|
| **R-D01 推荐被 mask 挡** | GUA-075 选对型但拆 core → 回退出炸/NN | 下一档同型（GUA-081） |
| **R-D02 推荐缺失** | 无同型、R11 让道 PASS，局面需压 | R11 阈值 / 三带二 builder |
| **R-D03 残局未命中** | `numofplayers` 假 / Q 未触发 | GUA-078 / publicInfo.rest |
| **R-D04 组牌锁死** | 对子/三张 is_core 导致无法合法压牌 | grouping to_card_mask / 借调 API |
| **R-D05 启发式/NN 劣选** | 有合法小压却选炸/王/拆对 | GUA-071 规则、GUA-079 最小压制 |
| **R-D06 场态误读** | greaterPos/curPos/队友识别错 | GUA-027 类、greaterAction |
| **R-D07 记录/贡还** | initial_hand 与出牌不一致 | GUA-067/081 recorder |
| **R-D08 知识未接入** | 人类常识有、代码无 | GUA-073 映射 → guard/heuristic |

分析结论须标 **至少一个 R-Dxx** + **证据行**（日志或 JSON 字段）。

---

## 5. 命令与文件速查

```bash
# 牌谱目录（V7 双客户端各写一份 JSON，game_id 可不同）
# V7: game_records_v7/{ts} [yf1_v7|yf2_v7]-[opponent_1_3]-[{round}]-[{suffix}].json
# M3: game_records/{ts} [yf1_m3|yf2_m3]-....json
# 配对 yf2：同 [round]-[suffix]，见 §2.1；实现 yf_replay._try_load_teammate_record

# 客户端日志（与牌谱 start_time 同批；yf2 分析读 yf2_v7 日志）
# logs/yf1_v7_YYYYMMDD_HHMMSS.log
# logs/yf2_v7_YYYYMMDD_HHMMSS.log

# 批跑总日志（vn / batch_games）
# logs/v7_vs_lalala_YYYYMMDD_HHMMSS.log

# 按步 timestamp 对日志（步 N 的时间戳来自 actions[N-1]）
rg "GUA-075|残局管线|组牌保护|handCards=|actIndex=" logs/yf2_v7_*.log
```

| 文件 | 用途 |
|------|------|
| [`SCRIPT_INDEX.md`](../SCRIPT_INDEX.md) §三 | WF-12 入口与脚本索引 |
| `scripts/tools/yf_replay.py` | 回放 + **yf1↔yf2 配对**；新牌谱支持 A/B/C 离线决策链路（A 实战事实、B Layer/Guard/Intent、C 候选/Memory/GUA） |
| `scripts/tools/wf12_find_decision_at_step.py` | §2.2 **`find_decision_at_step`** 可运行副本 + 金样例回归 |
| `src/v/nn/ultimate_win_rate_engine_v7.py` | V7 `decide()` / `_heuristic_select` / GUA-075 |
| `src/v/nn/guards/v7_guards.py` | Guard R01～R12 |
| `src/v/nn/endgame/` | 残局 Q0～Q3 |
| `src/communication/v7_game_recorder.py` | `my_decisions`、贡还 `initial_hand` |
| `docs/guandan-brain/ISSUES.md` | 登记 GUA |
| **`docs/analysis/WF-12-<game_id>-<副序>-<yf>-<主题>.md`** | **WF-12 报告默认输出目录**（必须在收尾时主动报路径） |

> **输出路径规范**：每份 WF-12 报告一律写盘到 `docs/analysis/`，命名 `WF-12-<game_id>-<副序>-<yf1|yf2>-<主题>.md`（主题中文短句，如「Q0让道决策分析」）。**Agent 必须在每次收尾时主动向用户报路径**，禁止只把报告贴在聊天里。
| `replay_word.md`（仓根） | 典型步人类可读摘要 |

---

## 6. 报告模板（复制使用）

```markdown
## WF-12 决策链路：<game_id> 步 <N>/<M>

### 圈况
- 分析对象：`yf1` / `yf2` 及 **JSON 文件名**
- 级牌 / 角色 / 手牌数：**`my_decisions.context`**（`curRank`、`role`、`handCards_size`）
- 上家控牌 / 队友 / 对手出牌：
- greaterPos / greaterAction：

### 实际出牌
- 动作 / actIndex：
- 决策层：**L?**（证据：日志一行或 my_decisions）

### 管线还原（按序）
1. GUA-075：…
2. mask 拦截：…
3. 回退：Guard → … → NN/heuristic → 最终 actIndex=

### 根因
- **R-D0?**：…
- 人类可优解：…（非关单标准）

### 建议
- [ ] 登记 GUA-xxx / 更新 GUA-081
- [ ] pytest 构造态：tests/test_gua0xx_….
- [ ] 批跑：**R-G080-4 零退化**（`v7-win-rate-history.md`）；**禁止**以「再跑同副 replay 逐步一致」为 pass
```

---

## 7. 范例（GUA-081 锚点）

**牌谱**：`20260628091707150272`，步 7，yf1 四炸 8888 压对手三带二 666+22。

| 层 | 结果 |
|----|------|
| GUA-075 | 推荐 `ThreeWithTwo/8`（888+22） |
| L2′ | **组牌保护拦截**（拆 8 炸） |
| 回退 | 无二次三带二 fallback → **actIndex=116 Bomb/8** |
| 根因 | **R-D01** + 缺 fallback（→ GUA-081） |

完整日志行见批跑 `logs/v7_vs_lalala_20260628_091551.log` 同秒 `GUA-075 推荐被组牌保护拦截`。

---

## 8. 维护

- 新增决策层或改 `decide()` 顺序 → 更新 §3 表 + Skill。
- 新 taxonomy → §4 追加 R-Dxx，并在 ISSUES 交叉引用。
- 关单 GUA 若方法论可复用 → **WF-11** Playbook（如 PB-001 拆炸时序）。
- **yf1/yf2 配对或 recorder 字段变更** → 同步 §2.0–§2.2（含 Python 片段）、`wf12_find_decision_at_step.py`、`yf_replay.py`、`SCRIPT_INDEX.md`。
