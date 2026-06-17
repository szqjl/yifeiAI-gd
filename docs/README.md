# 文档目录

本目录包含项目的所有详细文档。

## 📚 快速导航

### 🚀 新用户入门
- **[文档完整索引](DOCUMENTATION_INDEX.md)** - 所有文档的完整索引和分类
- **[快速开始指南](quickstart/)** - 快速上手项目

### 🧠 治理与归类（改仓库结构前可读）
- **[M-V 治理方案](governance/M-V-Series-治理方案.md)** · **[文档审查台账](governance/DOCUMENT_AUDIT.md)**（2026-05-29）
- **[Kanban 看板](governance/KANBAN.md)** · **[飞书卡片集成](governance/KANBAN_CARD_INTEGRATION.md)**
- **[main 分支策略](governance/main-branch-policy.md)** · **[COS 接入](governance/COS-接入指南.md)**
- **[启动脚本 launchers](../../scripts/launchers/README.md)** — 根目录 `START_*.bat` 真源（Phase 5）
- **[根目录散落物审查](governance/ROOT_ARTIFACT_AUDIT.md)**（2026-05-29）

### 🧠 掼蛋 AI 迭代大脑（改代码前先读）
- **[guandan-brain 说明与索引](guandan-brain/README.md)** - 缺陷（ISSUES）、迭代日志（ITERATIONS）、评测（EVAL）；与代码同仓的真源台账
- **[指挥系统（规划 / 统筹 / 部署）](guandan-brain/COMMAND_SYSTEM.md)** - 大脑与执行层分工、标准一轮流程
- **[本机评测清单](guandan-brain/LOCAL_EVAL_CHECKLIST.md)** - 哪些须在你本机跑对局、哪些只维护文档
- **[给执行 AI 的改决策说明](guandan-brain/PROMPT_FOR_DECISION_FIX.md)** - 复制整段让 AI 按评测结论改 **`src/m/m3/`**（M1 已 frozen，见 ISSUES「引擎维护策略」）

### 📖 主要文档分类

#### 1. 实施指导（已归档）

历史 V6 实施手册已迁入 [archive/implementation/](archive/implementation/)；日常开发见 [development/](development/)、[guandan-brain/](guandan-brain/)。

#### 2. 训练文档 (training/)
模型训练相关的所有文档
- [历次训练效果汇总](training/历次训练效果汇总.md)
- [训练监控工具替代方案](training/训练监控工具替代方案.md)
- [各阶段训练说明](training/)

#### 3. 开发文档 (development/)
功能开发和优化说明
- [分支开发指南](development/分支开发指南.md)
- [M1相关开发文档](development/M1*.md)

#### 4. 分析报告 (analysis/)
问题分析和优化建议
- [所有分析报告](analysis/)
- [Agent 会话归档](analysis/agent-sessions/)（原 `claude-analysis/`）
- [任务 handoff](analysis/handoffs/)
- [M1分析报告](reports/m1/)

#### 5. 项目报告 (reports/)
项目总结和成果报告
- [M1相关报告](reports/m1/)
- [优化实施报告](reports/)

#### 6. 使用指南 (usage/)
工具和功能的使用说明
- [GUI使用指南](usage/)
- [回放系统说明](usage/REPLAY_README.md)

#### 6. 知识库文档 (knowledge/)
掼蛋游戏知识和规则（**唯一真源**）
- [知识库快速开始](knowledge/QUICK_START.md)
- [游戏规则](knowledge/rules/)
- [策略技能](knowledge/skills/)
- 历史 OCR/txt 摘录见 [archive/skill/](archive/skill/)、[archive/rules/](archive/rules/)

#### 7. 迭代大脑 (guandan-brain/)
版本—缺陷—评测—决策台账（非通用知识库）
- [README：使用顺序与维护约定](guandan-brain/README.md)
- [ISSUES.md](guandan-brain/ISSUES.md) · [ITERATIONS.md](guandan-brain/ITERATIONS.md) · [EVAL.md](guandan-brain/EVAL.md)
- [评测场景目录](guandan-brain/scenarios/)

## 📋 文档列表（根目录已迁入子目录，见 [DOCUMENT_AUDIT](governance/DOCUMENT_AUDIT.md)）

### 核心架构文档
- [掼蛋AI客户端架构方案](architecture/掼蛋AI客户端架构方案.md)
- [掼蛋AI完整开发指南](development/掼蛋AI完整开发指南.md)

### 比赛相关
- [掼蛋AI相关比赛汇总](competition/掼蛋AI相关比赛汇总.md)
- [一等奖 lalala 分析](competition/一等奖代码优秀特点分析.md)

### 工具和配置
- [Git设置指南（旧版）](governance/git-setup-guide.md) — 分支以 [main-branch-policy](governance/main-branch-policy.md) 为准
- [WebSocket配置](development/WEBSOCKET_CONFIG.md)
- [OCR和Markitdown指南](usage/OCR_AND_MARKITDOWN_GUIDE.md)
- [推送前检查指南](development/推送前检查指南.md)

### 模型和版本
- [模型文件管理方案](governance/模型文件管理方案.md) — Artifact 主路径见 [COS-接入指南](governance/COS-接入指南.md)
- [V4 V5对比（归档）](versions/V4_V5_COMPARISON.md)
- [V5模型加载和调试信息（归档）](versions/V5_MODEL_LOADING_AND_DEBUG_INFO.md)

### 项目与规划
- [项目开发历程总览](project/项目开发历程总览.md)
- [一年期限与里程碑](project/项目一年期限与里程碑.md)

## 🔍 按主题查找

### 训练相关
- 训练效果: [历次训练效果汇总](training/历次训练效果汇总.md)
- 训练工具: [训练监控工具替代方案](training/训练监控工具替代方案.md)
- 训练阶段: [各阶段训练说明](training/阶段*.md)

### M1相关问题
- 所有M1报告: [reports/m1/](reports/m1/)
- M1开发文档: [development/M1*.md](development/)
- M1修复记录: [fixes/M1_*.md](fixes/)

### 实施指导（归档）
- 历史手册: [archive/implementation/](archive/implementation/)

### 问题分析
- 所有分析: [analysis/](analysis/)
- 修复记录: [fixes/](fixes/)

## 🔧 已知字段约定 / 近期修复

### selfRank / oppoRank / curRank 写入位置（2026-05-29）

> **语义（必读）**：平台用语为 **我方等级 / 对方等级 / 当前等级**（见 [v1006 使用说明书 PDF 第 5–7 页](../offline_platform/掼蛋平台使用说明书v1006.pdf) `act` 示例）。`game_info` 与 `act` · `play` 可能不一致（开局快照 vs 进贡还贡后真值）。详见 [项目 README「别混」一节](../README.md#selfrank--opporank--currank-别混beginning-vs-act)。

平台 **`act` 消息**里有 `selfRank / oppoRank / curRank`（PDF 第 5 页起）；**`notify` · `play` 广播不带**（PDF 第 3 页示例），所以历史 `game_records/*.json` 里：

| 写入路径 | 来源 | 历史情况 |
|---|---|---|
| `game_info` | `start_game(game_info=...)` 调用方传入 | 调用方传 None → 全 None |
| `actions[].context` | `notify/play` 通知里的 data | 该消息**不含**三字段 → 客户端用缓存填充，非服务器逐条下发 |
| `my_decisions[].context` | yf1_m1.py:381 / yf2_m1.py:385 自建字典 | **历史压根没塞这三字段** ❌ |

**修复**：[src/communication/yf1_m1.py](../src/communication/yf1_m1.py#L385-L391) 和 [src/communication/yf2_m1.py](../src/communication/yf2_m1.py#L385-L391) 的 `decision_context` 增加 `selfRank/oppoRank/curRank`，从下一次跑就有真实级牌。

**消费侧**：[scripts/tools/yf_replay.py](../scripts/tools/yf_replay.py#L498-L527) 的 `_resolve_levels` 改成三层 fallback：`game_info → my_decisions[].context → actions[].context`，旧文件仍 fallback 到 `'2'`，不会破坏回放。

实测新记录 `20260529003420492436 [yf1_m1]-[25].json`：`selfRank='2', oppoRank='A', curRank='A'`（对方等级 A、当前等级 A，与 0 胜结论一致）。

**平台字段对照**：`selfRank`=我方等级，`oppoRank`=对方等级，`curRank`=当前等级（`play` 阶段即本副打几）。

---



### 新用户入门
1. [项目主README](../README.md) - 项目总览
2. [快速开始指南](quickstart/) - 快速上手
3. [知识库快速开始](knowledge/QUICK_START.md) - 了解知识库

### 开发者
1. [掼蛋 AI 迭代大脑](guandan-brain/README.md) - 先对齐本轮 ISSUES / ITERATIONS / EVAL
2. [开发指南](development/掼蛋AI完整开发指南.md) — 日常开发入口（历史实施手册见 `archive/implementation/`）
3. [开发相关文档](development/) - 开发指南
4. [训练相关文档](training/) - 训练指南

### 问题排查
1. [修复记录](fixes/) - 查看修复记录
2. [问题分析](analysis/) - 查看问题分析
3. [M1相关问题](reports/m1/) - 查看M1相关问题

## 🔗 相关链接

- [项目主README](../README.md)
- [完整文档索引](DOCUMENTATION_INDEX.md)
- [掼蛋 AI 迭代大脑](guandan-brain/README.md)
- [知识库快速开始](knowledge/QUICK_START.md)

---

**最后更新**: 2026-05-30（增补「beginning vs act 等级语义」；见主 README）
**维护者**: AI Assistant
