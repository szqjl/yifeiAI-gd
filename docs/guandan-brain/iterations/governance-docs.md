---
tags: [governance, docs, handoff, replay, tribute]
created: 2026-05-29
updated: 2026-06-01
topic: 治理文档、回放工具与录牌
related: [[Infrastructure]], [[phase5-infra]]
---

# 治理文档、回放工具与录牌

> 来源：[[ITERATIONS]] 2026-05-29 ~ 2026-06-01

## 文档治理

| 日期 | 内容 |
|------|------|
| 2026-05-29 | docs 根目录归类：24 篇迁入子目录；`DOCUMENT_AUDIT.md` |
| 2026-05-29 | docs UTF-8 修复：`fix_doc_encoding.py`；架构 v2.7 增补 `src/m/` `src/v/` `contracts/` |
| 2026-05-29 | 清空 `game_records`：1488 JSON 已删；`.gitignore` 改 `game_records/*` |

## GitHub 镜像

- `sync_github_mirror.ps1`：fetch 可 `-SkipFetch`、失败重试
- 已删 `github/develop`、推送 `github/m-dev`
- **禁止 push main**；日常开发 m-dev

## 回放工具

| 日期 | 迭代 | 内容 |
|------|------|------|
| 2026-06-01 | 贡牌录牌 P0/P1 | `yf_replay.py` `apply_tribute_back_to_hand`；yf1/yf2_m3 notify tribute/back；pytest **22 passed** |
| 2026-06-01 | 回放 curRank 真值 | `resolve_episode_levels`：stage=play·act 优先，贡还 notify 不覆盖 |
| 2026-06-01 | 净盘 3 局验收 | 贡还录牌 pass；四类 source 齐全 |

## Handoff 接续

| 日期 | 文件 | 内容 |
|------|------|------|
| 2026-05-31 | `2026-05-31-M3-skills映射与组牌总纲.md` | skills §16–§22 评估摘要 + M3 待办 + 未提交清单 |
| 2026-05-31 | `2026-05-31-m-dev-push-governance-compliance.md` | m-dev 推送治理合规补录 |

## 引擎维护策略定音

- M1 = frozen / 非交付线（GUA-022 closed）
- M3 = 主交付 + `IDecisionProvider`
- P0 guard → `m3_decision_engine`
- 组牌/牌力 → V5+

## 相关测试

- `test_yf_replay_tribute_back.py`：6 passed
- `test_yf1_m3_back_notify.py`：16 passed
- `test_yf_replay_levels.py`：4 passed
