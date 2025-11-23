# 基于规则的掼蛋AI训练手册 — 丁华秘籍合并说明

已将 `docs/skill/掼蛋技巧秘籍_OCR.txt` 的关键信息整理并生成摘要文件：`docs/丁华掼蛋秘籍_整合.md`。

要点建议（可合并到训练手册相应章节）：
- 从 OCR 中抽取的“首轮进攻/留牌/炸弹使用时机”等规则可直接作为 `priority_rules` 的示例条目。
- 建议把若干典型策略转成训练样例（self-play 的 replay case），用于评估规则改动对胜率的影响。

如果需要，我可以：
- 抽取若干高置信度的规则并直接生成 YAML/JSON 示例，插入到 `config` 或 `data/replays`；
- 或把这些规则写入 `src/decision/advanced_rules.py` 的注释示例部分。
