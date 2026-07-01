---
tags: [MOC, GUA, index]
created: 2026-06-17
topic: 全部 GUA 编号快速索引
---

# GUA 编号快速索引

> 按编号查找对应迭代文件和状态。

## GUA-001 ~ GUA-030

| GUA | 主题 | 状态 | 文件 |
|-----|------|------|------|
| GUA-001 | 文档可读性 | closed | [[m1-pass-gua020-021]] |
| GUA-014 | 拆牌优先级（联动 GUA-022） | closed | [[m1-strategy-gua022]] |
| GUA-020 | yf1 vs yf2 PASS 率对照 | closed | [[m1-pass-gua020-021]] |
| GUA-021 | 减少问题 PASS | closed | [[m1-pass-gua020-021]] |
| GUA-022 | M1 队胜率（frozen） | closed | [[m1-strategy-gua022]] |
| GUA-024 | M3 play 全 PASS 根因 | closed | [[m3-integration-gua024-028]] |
| GUA-025 | 回放手牌误合并 | closed | [[m3-integration-gua024-028]] |
| GUA-026 | 三带二拆牌/炸弹保护 | closed | [[m3-strategy-gua026-029]] |
| GUA-027 | 场态重算 | closed | [[m3-integration-gua024-028]] |
| GUA-028 | v1006 三项对齐 | closed | [[m3-integration-gua024-028]] |
| GUA-029 | 炸弹可执行规则包 | closed | [[m3-strategy-gua026-029]] |
| GUA-030 | 原则映射表 | closed | [[m3-skills-mapping-gua030]] |

## GUA-031 ~ GUA-053

| GUA | 主题 | 状态 | 文件 |
|-----|------|------|------|
| GUA-031 | 传牌 guard | closed | [[m3-guards-gua031-036]] |
| GUA-032 | 记牌算牌 | closed | [[m3-guards-gua031-036]] |
| GUA-033 | victoryNum 异常 | closed | [[batch-executor]] |
| GUA-034 | 残局拦头游 | closed | [[m3-guards-gua031-036]] |
| GUA-035 | END-M02+ 对手剩张过滤 | closed | [[m3-guards-gua031-036]] |
| GUA-036 | 控权+接风配合 | closed | [[m3-guards-gua031-036]] |
| GUA-037a | V7 静态特征 124 维 | closed | [[v7-features-gua037-038]] |
| GUA-037b | V7 动态特征 LSTM 64 维 | closed | [[v7-features-gua037-038]] |
| GUA-038 | V7 BC 热启动训练 | closed (基建) | [[v7-features-gua037-038]] |
| GUA-041 | V7 路径债清理 | closed | [[v7-infra-gua041-049]] |
| GUA-042 | ABL-GD 评估 | closed | [[V7-Development]] |
| GUA-043 | 专利审计 | closed | [[V7-Development]] |
| GUA-044 | 四席就绪门闩 | closed | [[v7-infra-gua041-049]] |
| GUA-045 | V7 P0 Guard 壳 | closed | [[v7-strategy-gua045-053]] |
| GUA-047 | 73s 卡顿诊断 | closed (误判) | [[v7-infra-gua041-049]] |
| GUA-048 | 日志 dump 延迟 | open (P2) | [[v7-infra-gua041-049]] |
| GUA-049 | race condition 修复 | closed (P0) | [[v7-infra-gua041-049]] |
| GUA-050 | 局面信念向量 | open | [[v7-features-gua037-038]] |
| GUA-051 | 稠密 Reward 9 种 | closed | [[v7-strategy-gua045-053]] |
| GUA-052 | 全量记牌 MemoryTracker | closed | [[v7-strategy-gua045-053]] |
| GUA-053 | 方案增补套路 | open (仅文档) | [[v7-strategy-gua045-053]] |

## GUA-054 ~ GUA-061

| GUA | 主题 | 状态 | 文件 | 完成定义 |
|-----|------|------|------|----------|
| GUA-054 | V7 组牌中间表示（grouping_scanner 9 维） | open (P0) | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |
| GUA-055 | V7 动作空间二阶段过滤 | open (P0) | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |
| GUA-056 | V7 双上节奏 reward | open (P1) | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |
| GUA-057 | V7 记牌模块（108 维概率分布） | open (P1) | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |
| GUA-058 | V7 策略模块（4 分类） | open (P1) | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |
| GUA-059 | BC v2 退化根因定位 | open (P0) | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |
| GUA-060 | BC val_acc 36.46% 锁死 → 终止 BC 调参 | closed | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |
| GUA-061 | 模块化架构（GroupingEngine） | **open (P0) ← 当前** | [[v7-bc-training-gua059-061]] | 见 ISSUES 备注 |

> **完成定义**：已关单 GUA 的详细实施条件见 `issues/GUA-xxx-completion.md`。

## V7-xxx 编号

| 编号 | 主题 | 状态 | 文件 |
|------|------|------|------|
| V7-006 | 端到端决策链路 | closed | [[v7-infra-gua041-049]] |
| V7-007 | 胜率基线测试 | open | [[v7-features-gua037-038]] |
| V7-010 | 服务器 exe 迁出仓库 | closed | [[v7-infra-gua041-049]] |
