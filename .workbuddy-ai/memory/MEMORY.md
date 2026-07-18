# 项目长期记忆（MEMORY.md）

> 真源：`docs/guandan-brain/工作流.md`、`AGENTS.md`、`.cursor/rules/guandan-context.mdc`。
> 本文件只存**跨会话需要**的硬规则、当前活跃分支、口径陷阱。

## 身份
- 用户：**阿亮总**
- 助手：**buddy**
- 项目：`D:\guandanscore\YiFeiAI-GD`（南邮掼蛋 AI 客户端 / v1006 / OpenGuanDan）

## 当前活跃分支（2026-07-18）
- **v8-dev**：OpenGuanDan 新版服务器迁移（`ws://127.0.0.1:8181`），已跑通 3-5 局批跑，V8 5/5 LALALA；下一步：多局稳定性 + scores.json 累计
- **v7-dev**：v1006 回退基线；最近 GUA-141/142（排序 Q1 + 敌剩 6）已收
- **m-dev**：M3 交付线；M1 frozen；队 KPI **只看 M3 批跑**
- 牌谱目录分离：M3 → `game_records/`；V7 → `game_records_v7/`；V8 → `game_records_v8/`

## 工作流真源（按使用频度）
- **WF-01** 新会话 / 自启动：`git branch` → 读 ITERATIONS 最新行 + ISSUES open P0 → 3 行汇报
- **WF-04** 批跑 / 胜率：**Shell 列 `logs/`**（禁 IDE Grep）→ 对账 L1/L2/L3/L3'/L4 → 写胜率史
- **WF-12** 决策链路 / 败招：牌谱 + log → 还原 decide 管线 → R-D01~R-D08
- **WF-05** 组牌引擎单测：唯一入口 `check_grouping_engine.py` + `--pre-dedup`
- **WF-07** handoff：只做「下一步唯一动作」
- **WF-08** push：`AGENT_PUSH_CHECKLIST` + `pre_push_check.bat`（仅用户明确要求时）

## 5 条铁律（必刻）
1. **`logs/` 必须用 Shell**（`Get-ChildItem` / `rg`），IDE Grep 读不到
2. **L1/L2/L3/L3'/L4 对账**：L3 在 `<repo_root>/v7_vs_lalala_scores.json`（**根目录**，非 `batch_executor/`）
3. **`victoryNum` 语义双轨**：V7=升级数(0/1/2/3)；V8=各席副胜次数。**禁** V7 vn 元素当胜局数累加
4. **队胜只算 `victoryNum[0]` vs `[1]`**（0+2 一队，1+3 一队），**禁**四席相加
5. **批跑 `--target-games` 必须 3 的倍数**（3/9/12），勿用 10
6. **报告/分析类产出必须写盘**——WF-12 报告 → `docs/analysis/WF-12-<game_id>-<副序>-<yf>-<主题>.md`；**收尾时必须主动向用户报路径**（聊天贴文 ≠ 报告写盘）。其它工作流报告目录见各自 spec。

## 牌型术语（与平台 v1006 对齐，禁 snake_case 幽灵键）
- 平台 `action[0]`：`Single` `Pair` `Trips` `ThreeWithTwo` `ThreePair` `TwoTrips` `Straight` `StraightFlush` `Bomb` `FourKings`（= 王炸 = 2 大王 + 2 小王）
- 阶段 `stage`：`beginning` `tribute` `anti-tribute` `back` `play` `episodeOver` `gameOver` `gameResult`
- 等级字段：`curRank` / `selfRank` / `oppoRank`
- 特殊动作：`tribute` `back` `PASS`
- **内部 group_type → 平台名**（仅代码注释 / 文档对照用）：
  - `trip_in_three_with_two` / `pair_in_three_with_two` → 平台 `ThreeWithTwo`
  - `pair_in_three_pair` → 平台 `ThreePair`
  - `trip_in_steel_plate` → 平台 `TwoTrips`（钢板）

## 净盘（批跑前必做）
- M3：`game_records/*.json` + `m3_vs_lalala_*.json` + `logs/*`
- V7：`game_records_v7/*.json` + `v7_vs_lalala_*.json` + `logs/*`
- V8：`game_records_v8/*.json` + `v8_vs_lalala_*.json` + `logs/*`
- 共用：停 `guandan_offline_v1006` / `guandan.exe` 进程；删 `tmp/.batch_executor.lock`；`batch_executor/latest_victory_num.json`、`current_batch.json`、`execution_state.json`

## V8 关键差异（vs V7）
- 消息嵌套：`{type, data}`（v1006 是平铺）
- act 回包：`actionList[indexRange]` 索引选（v1006 是 `actIndex`）
- 建房间：v8 显式 `CREATE_ROOM` + `JOIN_ROOM`（4 人 room），v1006 平台调度
- 还贡：v8 文档**显式禁止 > 10**
- 断线：v8 **不自动重连**
- 牌型新增：`FourKings`（= 王炸）

## 知识检索
- 实时（不走 Wiki）：ITERATIONS、ISSUES、handoff
- Wiki 综合：先 `python scripts/wiki.py query "关键词"`
- 改 docs 后：`python scripts/wiki.py ingest`

## 当前 P0 池（待阿亮总确认是否还要展开）
- GUA-143/144/145/146（V8 迁移基础设施）
- GUA-147（V8 诊断增强）
- GUA-148（V8 scores 追踪，已 5/5 验证）
- GUA-124（v1006 平台 SF 漏枚举，v1006 侧关单；**v8 侧未复验** → 潜在 P0）

## 维护
- 长期事实（用户偏好、跨迭代规则）→ 本文件
- 单次 / 当日 → `YYYY-MM-DD.md`（append-only）
- 30 天前的 daily log 蒸馏到本文件
