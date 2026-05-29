# 文档审查与归类台账（2026-05-29）

> 依据 [M-V-Series-治理方案.md](./M-V-Series-治理方案.md) §5.4。  
> 根目录散落文档已迁入子目录；原路径保留**跳转 stub**（除 `README.md`）。

## 图例

| 有效性 | 含义 |
|--------|------|
| **有效** | 内容仍可用，路径已更新，可继续维护 |
| **有效·需对齐** | 内容可用，但与当前 `m-dev` / M-V 分层不完全一致，阅读时对照治理方案与 `docs/versions/MATRIX.md` |
| **有效·归档** | 历史记录，保留备查，非日常入口 |
| **待修复** | 正文乱码或 frontmatter 错误，需 UTF-8/模板修复后再作真源 |

## 审查结果

| 原路径（`docs/` 根） | 新路径 | 有效性 | 说明 |
|----------------------|--------|--------|------|
| 掼蛋AI客户端架构方案.md | `architecture/` | **有效** | 已 UTF-8 修复（`scripts/tools/fix_doc_encoding.py`）；**v2.7** 增补 M/V/`contracts` 章节 |
| 掼蛋AI完整开发指南.md | `development/` | 有效·需对齐 | 已 UTF-8 修复；frontmatter 仍含未渲染的 `datetime.now()` 模板 |
| 掼蛋AI相关比赛汇总.md | `competition/` | **有效** | UTF-8 正常；平台与赛事索引（2026-04-21 更新） |
| 掼蛋AI知识应用框架.md | `knowledge/` | 有效·需对齐 | 已 UTF-8 修复；与 `docs/knowledge/` 结构对照 |
| 结构化Prompt规范.md | `development/` | **有效** | Agent 协作指令规范，仍适用 |
| 模型文件管理方案.md | `governance/` | 有效·需对齐 | 大文件不进 Git；**以 [COS-接入指南.md](./COS-接入指南.md) 为现行 Artifact 真源**，本文作补充 |
| 推送前检查指南.md | `development/` | **有效** | 推送前检查；脚本路径以 `scripts/checks/` 为准 |
| 项目开发历程总览.md | `project/` | 有效·需对齐 | 2026-02 快照；分支已改为 **`m-dev`**，非文内 `main/develop` |
| 项目一年期限与里程碑.md | `project/` | **有效** | 一年期限与「有胜率」约定 |
| 一等奖代码优秀特点分析.md | `competition/` | **有效** | lalala 一等奖分析；已 UTF-8 修复 |
| 知识库格式化方案.md | `knowledge/` | 有效·需对齐 | 已 UTF-8 修复；与 `knowledge/rules`、`skills` 目录对齐 |
| cleanup_summary.md | `governance/archive/` | 有效·归档 | 2025-12-17 大文件清理记录 |
| DanZero+论文分析-架构借鉴建议.md | `analysis/` | **有效** | RL 论文借鉴，UTF-8 正常 |
| DEVELOPMENT_RULES.md | `development/` | **有效** | 已 UTF-8 修复；与 `CLAUDE.md` 时间规则一致 |
| DOCUMENTATION_INDEX.md | `docs/`（保留） | 有效·需对齐 | 总索引；本节 + 子目录 README 为补充 |
| GIT_SETUP_GUIDE.md | `governance/git-setup-guide.md` | 有效·归档 | **已替换为弃用说明**；分支以 [main-branch-policy.md](./main-branch-policy.md) 为准 |
| gitee_repo_capacity_guide.md | `governance/gitee-repo-capacity-guide.md` | **有效** | 容量与清理；模型现走 COS |
| guandan-basic-knowledge.md | `knowledge/guandan-basic-knowledge.md` | **有效** | M2 对战基础知识；与 README 摘要一致 |
| OCR_AND_MARKITDOWN_GUIDE.md | `usage/` | **有效** | OCR / MarkItDown 工具链 |
| REPLAY_IMPROVEMENTS.md | `usage/` | **有效** | 回放工具改进清单 |
| REPLAY_TRAINING_GUIDE.md | `training/` | 有效·需对齐 | 回放训练；已 UTF-8 修复 |
| repo-cleanup-inventory.md | `governance/` | **有效** | Phase 4 脚本收敛台账（已完成） |
| V4_V5_COMPARISON.md | `versions/` | 有效·归档 | V4/V5 对比；V 客户端已 **deprecated**，仅对照 |
| V5_MODEL_LOADING_AND_DEBUG_INFO.md | `versions/` | 有效·归档 | V5 调试；非 M 主迭代入口 |
| WEBSOCKET_CONFIG.md | `development/` | **有效** | 与 `config.yaml`、`scripts/checks/check_websocket_config.py` 一致 |

## 未移动

| 文件 | 原因 |
|------|------|
| `README.md` | 文档目录入口，保持 `docs/README.md` |
| `DOCUMENTATION_INDEX.md` | 全库索引，保持根级便于发现 |

## 重复与真源

| 主题 | 真源 | 备注 |
|------|------|------|
| 掼蛋基础知识 | `knowledge/guandan-basic-knowledge.md` | `analysis/agent-sessions/guandan-basic-knowledge.md` 为分析副本 |
| 规则/技巧文本 | `knowledge/rules/`、`knowledge/skills/` | 旧 `docs/rules`、`docs/skill` → `archive/`（Phase 5f） |
| lalala 参考源码 | `reference/lalala/` | 勿在 `docs/` 内保留 `.py` |
| Agent 会话分析 | `analysis/agent-sessions/` | 原 `claude-analysis/`（Phase 5f） |
| Git 分支策略 | `governance/main-branch-policy.md` | 取代 `git-setup-guide.md` 中的 develop/main 叙述 |
| Artifact / 模型 | `governance/COS-接入指南.md` | 取代仅写「云盘下载」的 `模型文件管理方案.md` 作为主路径 |
| 迭代 / 缺陷 | `guandan-brain/ISSUES.md`、`ITERATIONS.md` | 改代码前必读 |

## Phase 5f 目录迁移（2026-05-29）

| 原路径 | 新路径 | 根 stub |
|--------|--------|---------|
| `docs/rules/` | `docs/archive/rules/` | `docs/rules/README.md` |
| `docs/skill/` | `docs/archive/skill/` | `docs/skill/README.md` |
| `docs/claude-analysis/` | `docs/analysis/agent-sessions/` | `docs/claude-analysis/README.md` |
| `docs/competition/lalala/lalala_src/*.py` | `reference/lalala/` | `docs/competition/lalala/lalala_src/README.md` |
| `docs/implementation/` | `docs/archive/implementation/` | `docs/implementation/README.md` |

迁移工具：`migrate_docs_phase5f.py`、`migrate_docs_phase5g.py`；路径守卫：`python scripts/checks/check_doc_paths.py`。

## 维护约定

1. 新增文档**禁止**再堆在 `docs/` 根（除 `README.md`、`DOCUMENTATION_INDEX.md`）。
2. 移动文档时更新本表一行，并在旧路径保留 stub（可用 `scripts/tools/_write_doc_redirect_stubs.py`）。
3. 发现乱码文件：运行 `python scripts/tools/fix_doc_encoding.py`（或编辑器 UTF-8 重存）后在本表更新有效性。
