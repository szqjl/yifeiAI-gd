# WF-13 · Botzone 平台对局「牌型识别 → actionList → 意图」链路分析

> **目的**：对 **Botzone / OpenGuanDan 平台对局**（`botzone_adapter.py`，无 `game_records` 落盘）某一出牌步做**可复现的适配层链路还原**，定位「该压不压 / 牌型误判 / 候选缺失」的根因，并导向 **GUA 登记或最小修复**。  
> **与 WF-04 分工**：WF-04 = 批跑 KPI（局胜/副胜）；**WF-13 = 单步微观适配层决策**（`_classify_action` 判型、`generate_follow_actions` 候选、引擎意图）。  
> **与 WF-12 分工**：WF-12 = **有牌谱落盘**的 yf 决策链路（`my_decisions` + `game_records`）；**WF-13 = 无牌谱落盘**的 Botzone 对局，数据源是**客户端日志 `logs/v8_vs_botzone_*.log`** + `src/communication/botzone_adapter.py` 代码。

---

## 1. 触发

| 触发词 | 示例 |
|--------|------|
| Botzone 该压不压 / 为何不压制 | 「Botzone 第 24 回合，V8 有 5-9 顺子为何 PASS」 |
| 牌型识别 / 误判 Free / 候选缺失 | 「对手 2-6 顺子被识别成 Free」 |
| actionList 异常（只剩 PASS+SF） | 「跟牌轮 actionList 只有 PASS 和 3 个同花顺」 |
| 平台对局适配层根因 | 「match=6a71ace3… 的适配问题」 |

**输入最少信息**（人类任选其一）：

```text
日志: <logs/v8_vs_botzone_*.log 文件名>
回合: <第 N 个 play request / 关键动作牌面>
```

示例：

```text
日志: logs/v8_vs_botzone_20260804_170909.log
match: 6a71ace327e7bf01db1057b9
第 24 回合：2 号玩家打 2-6 顺子，3 号队友和 4 号对手都过，1 号玩家有 5-9 顺子却 PASS
```

---

## 2. Agent 必做步骤（按序）

### 2.0 Agent 自检（动手前 · 不可跳）

**强约束（Skill §0）**：未跑 `python scripts/checks/check_botzone_trace.py <日志> <回合>` 全 ✅，禁止写结论。脚本必须输出全 ✅ 才可继续。

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 日志文件存在且含 `[botzone_adapter]` | 退出码 0 |
| 2 | 日志含目标 `match=` 且仅一个对局 | `rg -c "match="` 区分 deal/play |
| 3 | 目标回合 = 第 N 个 `stage=play` request | 计数 `收到 request.*stage=play` |
| 4 | 该回合的 `actionList 摘要` 行存在 | 含 `types=` / `greater=` / `must_play=` |
| 5 | 读 `play request raw` 的 `history` | 还原 **greater 出牌者** 与当前圈况 |
| 6 | 对 `botzone_adapter.py` 复现 `_classify_action` | 用日志 `greater=` 牌面喂进判型 |
| 7 | 复现 `generate_follow_actions` | 对照 actionList 摘要 types 差异 |
| 8 | 写证据 → R-Bxx → 记录进 ITERATIONS.md | 见 §4、§6 ITERATIONS 记录模板 |

### 2.1 定位日志（Botzone 无 game_records）

**定音**：Botzone 平台对局**不写 `game_records`**；唯一证据链在客户端日志 **`logs/v8_vs_botzone_*.log`**（不进 Git，`git status` 看不到属正常）。

| 项 | 说明 |
|----|------|
| **入口** | 人类给的日志文件名，或 `logs/` 下按 `LastWriteTime` 最新 `*_botzone_*` |
| **match 定局** | 日志首行 `match=<id>`（`deal` request 只出现一次）；跨回合须**同一 match** |
| **玩家映射** | V8 = player 0（Botzone 1 号）；队友 player 2（3 号）；对手 player 1/3（2 号/4 号） |
| **回合口径** | 第 N 个 `收到 request: match=... stage=play`（**deal 不计**） |

```powershell
# 定位日志
Get-ChildItem logs -Force | Sort-Object LastWriteTime -Descending |
  Where-Object { $_.Name -like '*botzone*' } |
  Format-Table Name, Length, LastWriteTime -AutoSize

# 数回合（目标步的 stage=play 序号）
rg -n "收到 request: match=.*stage=play" logs/v8_vs_botzone_*.log
```

### 2.2 对齐目标回合 → actionList 摘要

**定音**：日志里每个 `stage=play` request 对应引擎一次决策；`actionList 摘要` 行打印了引擎**收到的候选**（`types=` 分布 + `greater=` + `must_play=`）。

| 步 | 做法 |
|----|------|
| 1 | 数到第 N 个 `stage=play` request 行 → 读紧随其后的 `actionList 摘要` |
| 2 | 记录 **`len`**、**`types`**（键即引擎可见候选牌型）、**`greater`**、**`must_play`** |
| 3 | 读 `play request raw` 的 `history`：`response` 非空的玩家 = 该步动作方；`greater` 出牌者由此定 |
| 4 | 顺 `GUA-075 推荐` / `残局管线命中` / `决策:` 行 → 得最终 `actIndex` 与动作 |

**禁止**：把 `actionList 摘要` 的 `types` 当「我方全部可出牌」；`types` 是**引擎候选**，缺失即根因信号（见 §4 R-B02）。

### 2.3 还原牌型识别（`_classify_action`）

把 `greater` 的牌面（V8 牌面，如 `['D2','C3','C4','D5','D6']`）喂进：

```python
from src.communication.botzone_adapter import BotzoneAdapter
a = BotzoneAdapter("test", "test_key")
print(a._classify_action(["D2", "C3", "C4", "D5", "D6"]))  # 期望 ['Straight','2',...]
```

**对照**：日志 `greater=` 首元素。若日志是 `Free` 而直接判型得 `Straight` → **修复已生效，该日志为修复前产物**；若一致为 `Free` → bug 仍在。

**判型函数**（`src/communication/botzone_adapter.py`）：

| 函数 | 行 | 职责 |
|------|-----|------|
| `_bz_response_to_v8_action` | 1008 | Botzone 卡号列表 → V8 牌面 → `_classify_action` |
| `_classify_action` | 1015 | 判型；5 张 → `_is_straight_ranks`（官方 10 窗口，级牌不提升） |
| `_is_straight_ranks` | 1060 | 5 张 rank 是否官方顺子窗口（A2345…TJQKA） |
| `_straight_low` | 1067 | 顺子低牌（裁判 `points[0]` 语义：A2345→A、TJQKA→T） |
| `_rank_to_order` | 170 | 级牌提升为 15（仅用于比大小，**不用于判型**） |

### 2.4 复现候选生成（`generate_follow_actions`）

把 greater + 手牌喂进，对比 `actionList 摘要.types`：

```python
from src.communication.botzone_adapter import ActionListGenerator
gen = ActionListGenerator(cur_rank="2")   # cur_rank 取日志 global.level
hand = ["S5", "S6", "C7", "C8", "S9"]
greater = ["Straight", "2", ["D2", "C3", "C4", "D5", "D6"]]
acts = gen.generate_follow_actions(hand, greater)
from collections import Counter
print(Counter(a[0] for a in acts))        # 期望含 Straight
print([a for a in acts if a[0] == "Straight"])
```

**对照**：`generate_follow_actions`（行 297）按 `greater_type` 分派（行 316-411）；若 `greater_type='Free'` → **任何分支都不命中**，只剩 PASS + 炸/SF 兜底（行 393-411）→ 即日志 `types={'PASS':1,'StraightFlush':3}`。**`Free` 是判型 bug 的入口信号**。

### 2.5 还原意图（引擎侧）

- 候选正常时：顺 `GUA-075 推荐` / `残局管线命中` / `决策:` 行确定 actIndex（此层根因归 **R-B08**，走 WF-12 管线）。
- 候选缺失时：引擎只能 PASS（无同型可选），**根因在适配层判型，不在意图**。

### 2.6 后续动作

| 情形 | 动作 |
|------|------|
| 判型 bug（Free 误判） | 修 `_classify_action` / `_is_straight_ranks`，加 pytest 构造态，锚定 match |
| 候选生成分支缺失 | 修 `generate_follow_actions` 分支（`_all_straight_windows` / `_sf_bomb_candidates`） |
| 配子补炸缺失（444+H2 无 Bomb 候选） | 归 R-B09 → `_wild_bomb_candidates` / `_replace_bomb_covering`（GUA-199） |
| 意图层问题（候选正常仍 PASS） | 归 R-B08 → 转 WF-12 管线分析 |
| 仅观测 | 摘要写入 `docs/guandan-brain/ITERATIONS.md` 追加行，**禁止为单局写特例 / 写 docs/analysis 报告** |

---

## 3. Botzone 适配层决策链路

```text
Botzone request (stage=play, history)
  → 解析 greater（_bz_response_to_v8_action 判型）
  → must_play / 接风领出判定（行 1389-1418）
  → generate_follow_actions（候选：压 greater + 炸 + SF，行 1446）
  → actionList（行 1524 摘要打印）
  → 引擎 decide（GUA-075 / 残局 / NN）→ actIndex
  → 合法性防线 _beats（行 1567-1581）→ 决策
```

日志证据行的**先后顺序**即管线顺序：`收到 request` → `actionList 摘要` → `GUA-075 推荐 / 残局管线命中` → `决策:`。

---

## 4. 根因 taxonomy（导向 GUA）

| 标签 | 含义 | 常见修复方向 |
|------|------|--------------|
| **R-B01 判型误判（Free）** | `_classify_action` 把合法牌型判成 `Free` → 跟牌候选整型缺失 | 官方 10 窗口 `_is_straight_ranks`；级牌不提升（`_rank_to_order` 只比大小） |
| **R-B02 候选分支缺失** | `greater_type` 合法但 `generate_follow_actions` 无对应分支 | 补分支 / 统一走 `_all_straight_windows` |
| **R-B03 顺子比大小错位** | Straight/SF 跟牌用低牌比大小，或级牌提升把顺子窗口打断 | `_straight_top_order` 取窗口高牌；`_straight_low` 对齐裁判 `points[0]` |
| **R-B04 接风/领出误判** | `must_play` / 接风领出判定错 → 领出轮被当跟牌轮（或反之） | 行 1316-1372 `self_lead` / `done_greater_lead` 判定 |
| **R-B05 玩家映射错** | greater 出牌者 / 队友识别错（player 号 ↔ 座次） | 玩家映射表 §2.1；`(myPos+2)%4` |
| **R-B06 响应转换错** | `_v8_action_to_bz_response` 卡号/序错 → 平台判非法 | 卡号映射 `bz_to_v8_cards` 往返一致 |
| **R-B07 手牌跟踪不同步** | `hand_cards` 与平台 history 不符 → 候选缺失/多余 | 手牌增量跟踪；重连重同步 |
| **R-B08 意图层该压不压** | 候选正常、引擎仍 PASS（GUA-075/残局/heuristic 决策） | 转 **WF-12** 管线分析（非适配层） |
| **R-B09 配子补炸缺失** | 逢人配（H2）本可补自然 3 张同 rank 成 4 炸，候选仅自然 4+ 同 rank → actionList 无 Bomb，引擎拆炸弹 core 打弱牌 | `_wild_bomb_candidates`（GUA-199）；`_build_bz_claim` 炸弹配子替换 `_replace_bomb_covering` |

分析结论须标 **至少一个 R-Bxx** + **证据行**（日志行 + 代码行）。

---

## 5. 命令与文件速查

```bash
# 前置检查（Skill §0 强约束；二选一）
# --step N：match 过滤后的第 N 条 actionList 摘要（先 rg 数序号）
# --by-cards：按 greater 牌面反查（推荐，免疫序号口径差）
python scripts/checks/check_botzone_trace.py logs/v8_vs_botzone_20260804_170909.log --match 6a71ace3 --by-cards D2,C3,C4,D5,D6

# 日志回合计数与摘要
rg -n "收到 request: match=.*stage=play" logs/v8_vs_botzone_*.log
rg -n "actionList 摘要|决策:|GUA-075|残局管线" logs/v8_vs_botzone_*.log
```

| 文件 | 用途 |
|------|------|
| [`SCRIPT_INDEX.md`](../SCRIPT_INDEX.md) §三 | WF-13 入口与脚本索引 |
| `src/communication/botzone_adapter.py` | 适配层真源：`_classify_action`(1047) / `generate_follow_actions`(299) / `_wild_bomb_candidates`(451) / `_all_straight_windows`(552) |
| `tests/test_botzone_adapter.py` | 判型 + 跟牌回归测试（`test_classify_straight_with_level_card_low` / `test_follow_straight_beats_level_low_straight`） |
| `logs/v8_vs_botzone_YYYYMMDD_HHMMSS.log` | Botzone 对局唯一证据链（不进 Git） |
| **`docs/guandan-brain/ITERATIONS.md`** | **决策链路分析结论唯一输出位置**（表格追加行，见 §6 模板） |

> **输出规范**：决策链路分析结论**不写 `docs/analysis/` 报告**，一律作为一行记录追加进 `docs/guandan-brain/ITERATIONS.md`（沿用该文件模板：日期 / 迭代名 / 目标 GUA / 改动摘要 / 评测结果摘要 / 下轮 priority）。**Agent 必须在每次收尾时主动向用户报「已追加 ITERATIONS 行」**，禁止只把结论贴在聊天里。

---

## 6. ITERATIONS 记录模板（复制使用）

> 与 `docs/guandan-brain/ITERATIONS.md` 表格列一致，在文件末尾追加一行（表头不动）。commit 未发生时「改动摘要」以代码路径 + 行号描述。

```markdown
| YYYY-MM-DD | WF-13 match=<前 8 位> 回合 <N> | GUA-xxx, … | **决策链路分析结论**（不写报告）。match=<id> 回合 <N>：<圈况一句话>；`actionList 摘要` types=… / greater=… / must_play=…；适配层还原 `_classify_action`→…、`generate_follow_actions`→…；根因 **R-Bxx**（<一行解释>）；证据：日志行 <时间> + 代码行 <file:line>；修复方向 <…>。 | check_botzone_trace.py 全 ✅；pytest <构造态名> 通过 / 修复后重放本局日志复核（禁止改日志） | 下轮：<…> |
```

---

## 7. 范例（match=6a71ace3 第 24 回合 · GUA 锚点）

**日志**：`logs/v8_vs_botzone_20260804_170909.log`，match=6a71ace327e7bf01db1057b9。

| 步 | 结果 |
|----|------|
| 回合 24 | 2 号（player 1）打 `['D2','C3','C4','D5','D6']`（2-6 顺子）；3 号队友、4 号对手均过；1 号 V8（player 0）跟牌 |
| `actionList 摘要` | `len=4 types={'PASS':1,'StraightFlush':3} greater=['Free','2',['D2','C3','C4','D5','D6']] must_play=False` |
| 修复前 `_classify_action` | `_is_consecutive` + `_rank_to_order`（级牌 2 提升 15）→ `[3,4,5,6,15]` 不连续 → **`Free`** |
| 候选生成 | `greater_type='Free'` 无分支 → 只剩 PASS + 3 SF 兜底 → 5-9 顺子不在候选 |
| 意图 | `GUA-075 主路径 recommend=PASS actIndex=0` → PASS |
| 修复 | `_classify_action` 5 张改官方 10 窗口 `_is_straight_ranks` + `_straight_low`；级牌不提升 |
| 回归 | `test_classify_straight_with_level_card_low` / `test_follow_straight_beats_level_low_straight` 通过 |

**修复后复现验证**：

```python
from src.communication.botzone_adapter import ActionListGenerator
from collections import Counter
gen = ActionListGenerator(cur_rank="2")
acts = gen.generate_follow_actions(["S5","S6","C7","C8","S9"],
                                   ["Straight","2",["D2","C3","C4","D5","D6"]])
print(Counter(a[0] for a in acts))          # {'PASS':1,'Straight':32,'StraightFlush':3}
print([a for a in acts if a[0]=="Straight"])  # 含 ['Straight','5',['S5','S6','C7','C8','S9']]
```

> **同类扫描**：同 match 还出现过 `greater=['Free','6',['S6','S5','S4','S3','S2']]`（回合 3，同一根因）；修复后应全部归为 `Straight`。

---

## 8. 维护

- 适配层新增判型 / 候选分支 → 更新 §3 链路与 §4 taxonomy。
- 新 R-Bxx → §4 追加，并在 ISSUES 交叉引用。
- 关单 GUA 若方法论可复用 → **WF-11** Playbook。
- `_classify_action` / `generate_follow_actions` / `_wild_bomb_candidates` / 日志字段变更 → 同步 §2.3–§2.4 Python 片段、`check_botzone_trace.py`、`SCRIPT_INDEX.md`。
