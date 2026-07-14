# 南邮离线平台 actionList 候选缺失 · 反馈信（可发送）

**致**：南京邮电大学掼蛋离线平台开发团队  
**日期**：2026-07-11  
**来源**：双上计分王 AI 项目（YiFeiAI-GD）  
**平台版本**：`guandan_offline_v1006`  
**现象登记**：仓库 `ISSUES.md` → **GUA-124**（observation）

> **与 2026-06-28 初稿的关系**  
> 我方曾对批跑 `202606282019*.json` 做过全量「PASS-only = 漏候选」复核（脚本 `scripts/analysis/verify_actionlist_pass_only.py`），结论为：**多数 PASS-only 按该步 `curRank` 重算后合理**，原稿 §3.2–3.5 中「44 例明确可压但未给出」**不能作为平台 bug 依据**。  
> 初稿全文保留于 [`archive/南邮离线平台-actionList候选缺失观测报告.md`](./archive/南邮离线平台-actionList候选缺失观测报告.md)，**请勿再发该版**。  
> **本信仅呈报一条经牌谱全量对账、可独立复现的 GUA-124 类案例**（逢人配竞争 → 同花顺变体未枚举）。

---

## 〇、致信

尊敬的老师，您好：

我是一名掼蛋爱好者，借助贵团队开放的 [掼蛋 AI 竞赛平台](https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html) 自学 AI 客户端开发（项目 YiFeiAI-GD / 双上计分王）。

在 V7 决策链路复盘中，我们发现一类与 **actionList 枚举完备性** 相关的现象：平台下发的合法动作列表中**缺少**按规则可压当前 `greaterAction` 的 **同花顺（StraightFlush）** 候选，而**同一张逢人配（级牌）** 已出现在另一档 **炸弹** 候选中。客户端协议要求只能回传 `actIndex`（列表下标），**无法补报未枚举动作**。

以下提供**最小复现**（单局、单步、完整 JSON 字段），供贵方 C++ 引擎侧排查。如需原始牌谱或协助复现，我们可随时配合。

再次感谢贵团队开放的平台与竞赛资源。

---

## 一、现象摘要

| 项 | 内容 |
|----|------|
| 局面 | 对手 @3 以 **五星炸 `Bomb/J`** 控牌后，我方 yf2（座位 2）跟压 |
| 平台 `actionList` | **仅 2 项**：`PASS` + `Bomb/K`（四 K + **H2 逢人配** 凑五星 K 炸） |
| 缺失 | 手牌中可压五 J 炸的 **`StraightFlush`：`CA, C2, C3, H2, C5`** 未出现在列表中 |
| 牌力 | **同花顺 > 五星炸**（贵方规则与我方对照 `04_card_types_guide.md` §4.1 一致） |
| 根因假设（GUA-124） | 逢人配 `H2` 已编入 `Bomb/K`；**未同时枚举**「同花顺 + 同一 H2」变体 |

---

## 二、复现环境

| 项 | 值 |
|----|-----|
| 牌谱 | `game_records_v7/20260708230844225341 [yf2_v7]-[opponent_1_3]-[1]-[2].json` |
| `game_id` | `20260708230844225341` |
| 客户端 | `yf2_v7`，`player_id = 2` |
| 级牌 | `curRank = selfRank = oppoRank = "2"` |

---

## 三、牌局步序（`actions[]`，1-based 步号）

| 步号 | 席位 | 动作 | 说明 |
|------|------|------|------|
| 61 | @3 | `Bomb/J`：`SJ, HJ, CJ, CJ, DJ` | 五 J 五星炸；@3 约剩 5 张 |
| 62 | @0 | `PASS` | |
| 63 | @1 | `PASS` | |
| **64** | **@2（yf2）** | **本信锚点：决策时刻** | 须从平台 `actionList` 选择 `actIndex` |

> 注：61 步为 @3 出炸；**候选缺失发生在 64 步**（yf2 首次可跟压该五 J 炸）。

同期 `actions[62]`、`actions[63]` 的 `greater_action` 均为上述 `Bomb/J`，`greater_pos = 3`。

---

## 四、决策时刻 JSON 字段（step 64）

录自该步 `my_decisions[].context`（由平台 `act` 消息经 `decision_context_from_act` 写入；`actionList_size ≤ 8` 时 `actionList_sample` 为**全量**，非截断）：

```json
{
  "myPos": 2,
  "curPos": 1,
  "greaterPos": 3,
  "curRank": "2",
  "selfRank": "2",
  "oppoRank": "2",
  "handCards_size": 15,
  "handCards": [
    "H3", "C3", "D3", "H4", "D4", "S5", "H5", "C5",
    "SK", "HK", "CK", "DK", "CA", "H2", "C2"
  ],
  "actionList_size": 2,
  "actionList_sample": [
    { "type": "PASS", "rank": "PASS", "cards": [] },
    {
      "type": "Bomb",
      "rank": "K",
      "cards": ["SK", "HK", "CK", "DK", "H2"]
    }
  ]
}
```

**圈况（`greaterAction`，同期）**：

```json
["Bomb", "J", ["SJ", "HJ", "CJ", "CJ", "DJ"]]
```

---

## 五、实际下发 vs 期望应多出的候选

### 5.1 平台实际（全量 2 项）

| actIndex | 类型 | 牌张 |
|----------|------|------|
| 0 | `PASS` | — |
| 1 | `Bomb/K` | `SK, HK, CK, DK, H2` |

### 5.2 期望额外枚举（当前缺失）

| 类型 | 牌张 | 能否压 `Bomb/J` |
|------|------|----------------|
| **`StraightFlush`** | **`CA, C2, C3, H2, C5`** | **能** |

建议平台枚举示例（`rank` 字段以贵方引擎为准）：

```json
["StraightFlush", "<rank>", ["CA", "C2", "C3", "H2", "C5"]]
```

说明：`curRank=2` 时 **`H2` 为红桃逢人配**；`C2, C3, C5, CA` 为梅花同花结构，逢人配补全同花顺。

---

## 六、非客户端过滤的自证

1. `yf2_v7` 从 `act` 消息直接读取 `actionList`，决策前**不增删**候选。  
2. `normalize_action_list()`（`src/communication/v7_game_recorder.py` L44–57）**仅**规范化牌面字符串。  
3. `actionList_size = 2` 且 `actionList_sample` 长度同为 2 → 当回合平台下发即为 2 项。  
4. 我方诊断 `find_latent_bomb_like_beaters_not_in_action_list` 在本局输出 latent：`['CA','C2','C3','H2','C5']`，且牌理可压 `Bomb/J`。

---

## 七、请贵方确认的问题

1. step 64 局面下，C++ 枚举是否**本应**包含上述 `StraightFlush`？  
2. 逢人配同时参与「五星 K 炸」与「同花顺」时，枚举策略是否有意只保留一档？若有，是否有文档说明？  
3. 是否方便在 exe 侧增加当回合 `actionList` 完整 dump，便于与客户端 `actionList_sample` 对账？

---

## 八、关联案例（同类型，非本信主证）

仓库内 **GUA-124** 另有一锚点（`game_id` 不同、步 76）：`actionList` 仅 `PASS` + `Bomb/J`（含 `H9`），组牌可见方片 5–9 同花顺可压 `Bomb/6` 但未列出。模式一致：**逢人配编入一档 bomb-like，同花顺变体未并列枚举**。

---

## 九、附件与仓库索引

| 资源 | 路径 |
|------|------|
| 本局牌谱 | `game_records_v7/20260708230844225341 [yf2_v7]-[opponent_1_3]-[1]-[2].json` |
| 决策 trace | `game_decision_traces/20260708230844225341.jsonl`（约第 16 行：`candidates=2`） |
| 现象登记 | `docs/guandan-brain/ISSUES.md` → GUA-124 |
| 完成定义片段 | `docs/guandan-brain/issues/GUA-123-completion.md` §8 |
| 初稿（已撤回，勿发） | `docs/analysis/archive/南邮离线平台-actionList候选缺失观测报告.md` |
| 本项目仓库 | https://gitee.com/Philsz/yifei-ai-gd |

---

## 十、结语

以上仅为一条可独立核验的观测，样本有限，不一定代表平台全貌。我们如实呈报，冀对贵方引擎完善有所助益。如需原始 JSON、批跑日志或远程协助复现，请随时联系。

此致  
敬礼

---

## 十一、南邮回复（2026-07-11）

| 项 | 内容 |
|----|------|
| 回复要点 | 本信所述现象属于 **`guandan_offline_v1006` 老版本**；请以 **最新服务器版本** 为准 |
| 最新服来源 | GitHub：[GameAI-NJUPT/OpenGuanDan](https://github.com/GameAI-NJUPT/OpenGuanDan) |
| 部署参考（README） | Java：`guandan-java-1.0.0.jar`（JDK 17+）；Windows 原生：`guandan.exe`；WebSocket **`ws://127.0.0.1:8181`**（单进程 HTTP 3000 + WS 8181） |
| 与 v1006 差异 | v1006 离线竞赛 exe：`ws://127.0.0.1:23456/game/{client}`；OpenGuanDan 为 **CREATE_ROOM / JOIN_ROOM / PLAY** 房间协议，**非同一套 API** |
| 我方结论 | GUA-124 锚点在 **v1006 牌谱** 上仍成立；南邮称新版已修，**尚未**在 OpenGuanDan 上复验 step64 同局面 `actionList` |
| 迭代登记 | `docs/guandan-brain/ITERATIONS.md` → `v7-gua124-openguandan-reply`；ISSUES **GUA-124 closed**（v1006 侧 vendor 说明） |

**建议后续**：克隆 OpenGuanDan → 本地起服 → 构造/回放 GUA-124 锚点手牌，核对 `actionList` 是否枚举 `StraightFlush`；若迁移批跑，需单独评估 v7 客户端协议适配。

---

**建议邮件主题（中英文任选）**

- 中文：`[v1006] actionList 未枚举可压同花顺（逢人配竞争）· 最小复现 game_id=20260708230844225341 step64`
- English：`[v1006] actionList missing StraightFlush counter (wildcard in Bomb/K) — game_id=20260708230844225341 step 64`
