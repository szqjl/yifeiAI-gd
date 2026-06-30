# Handoff: m-dev 推送治理合规补录

| 字段 | 内容 |
|------|------|
| 日期 | 2026-05-31 |
| 分支 | m-dev @ **09d4f95** |
| 状态 | 已结案（自动化冒烟）；批跑满跑待本机 |
| 依据 | [M-V-Series-治理方案.md](../../governance/M-V-Series-治理方案.md) §7.3 / §8.2 |

## 背景

`fe3039b` 推送已符合分支/远程/产物不进库，但未跑 §7.3 M 冒烟、未执行 `verify_gitignore`、无专用 handoff。本 handoff 补录治理检查结果。

## 已完成（2026-05-31 Agent 环境）

| 项 | 结果 |
|----|------|
| **pytest 回归** | `test_batch_executor_counting` + `test_game_recorder_merge` + `test_m3_*` + `test_trick_state_gua027` → **48 passed, 3 skipped** |
| **M3 客户端 import** | `yf1_m3.py` / `yf2_m3.py` 可加载 |
| **M3 引擎 import** | `PYTHONPATH=src` → `M3DecisionEngine` OK |
| **batch_executor 诊断** | `--diagnose-only` 退出码 0（exe 存在；stdout 未解析 settingTimes，已知诊断局限） |
| **WebSocket 配置** | `check_websocket_config.py` — `config.yaml` 为 **GBK**；脚本已增多编码读取 → **pass** |
| **verify_gitignore** | 新增根目录 `verify_gitignore.py`；暂存区/大文件/models 检查 **pass** |
| **30 局 offline replay** | **未跑** — 本机 `game_records/` 空；须人类按 `LOCAL_EVAL_CHECKLIST` 净盘 `--target-games 10`（4 批满跑） |

## 未完成（须本机）

1. **满跑 10 局**：`completed_games=10`、`restart_count≥3`、批末 `victoryNum` 满足 `[0]=[2]`、`[1]=[3]`、`[0]+[1]=10`。
2. **30 局 regression diff**（治理 §8.2 行为变更时）：COS `pull_regression` 或本机积累后再 diff。
3. **GitHub 镜像**（可选）：`scripts/tools/sync_github_mirror.ps1 -SkipFetch`。

## 相关 commit（推送批次）

```
b68a535 docs: 局/副/victoryNum 口径与 Agent 批跑入门
4170a72 fix(batch_executor): completed_games 按平台批次数累计（方案 A+C）
0e58c19 feat(m3): GUA-026~031 决策 guard 与记牌/平台对齐
fe3039b docs(knowledge): 规则库重组、replay 工具与 PRINCIPLES 映射
```

## 下一步唯一动作

本机净盘跑满 `--target-games 10`（M3 vs lalala），用批末 **`victoryNum[0]` vs `[1]`** 填 `ITERATIONS.md`；若 `[0]≠[2]` 不得报胜率。
