# yifegdbot-onboarding — OpenCode 评审结果

评审对象：`docs/guandan-brain/SKILL_yifegdbot-onboarding.md`
评审人：opencode（Hermes 代笔）
日期：2026-05-21

---

## 准确性

| 项目 | 文档描述 | 代码实际 | 判断 |
|------|----------|----------|------|
| 双并行线架构 | M1 vs V4/V5/V6 并行 | ✓ 正确 | 准确 |
| M1 非 ML | 纯硬编码规则引擎 | ✓ 正确 | 准确 |
| 5阶段细分路由 | Opening/MidEarly/MidLate/EndgameEarly/EndgameLate | ✓ 正确 | 准确 |
| V5 层数 | 3层 | 实际是5层（Critical Rules → Rule-Based → Knowledge Enhanced → Select → Random Fallback） | **错误** |
| PhaseHandler 数量 | 10个 | 实际12个（含 TributeHandler、BackHandler） | **错误** |
| V6 状态 | 规划中 | .bak 废弃文件，非活跃 | **错误** |
| StrategyEngine 归属 | M1 专属 | 是 BasePhaseHandler 共用基础设施，V5 也用 | **错误** |
| 训练 pipeline | BC 预训练 + RL 自弈 | 实际是 BC + PPO RL，描述过于简化 | **需补充** |

## 重要遗漏

- `src/game_logic/` 子包完全未提及
- `rl_decision_engine.py` 等多个决策引擎变体未列出
- `lalala_adapter` 等通信层变体缺失
- 缺少对 lalala（对手平台）的介绍

## 可改进项

- V5 层数描述建议改为「5层决策架构（Critical Rules → Rule-Based → Knowledge → Select → Random Fallback）」
- PhaseHandler 描述建议改为「12个 PhaseHandler（10个常规阶段 + TributeHandler + BackHandler）」
- V6 状态建议改为「已废弃（.bak 文件）」
- StrategyEngine/HandStructureAnalyzer 建议移至「共用层」章节
