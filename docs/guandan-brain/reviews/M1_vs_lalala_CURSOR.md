# Cursor 评审结果：M1_vs_lalala.md

评审时间：2026-05-21
评审模型：ask-cursor (默认模型)

---

## 1. 可理解性反馈

### 表述较清晰的部分
- **§1 定位对比**、**§6 牌型分发 vs 通用评分**：表格 + trade-off 一句话，读者能快速建立「lalala = 一牌型一方法 / M1 = 阶段路由 + 通用评分」的心智模型。
- **§3 lalala `active()` 优先级链**：伪代码 + `cur` 阈值数组，和一等奖代码风格一致，好对照。
- **§8 核心差距总结**：四条结论与 §5、§7 呼应，适合当「改 M1 的 checklist」。

### 略显模糊或需读者自行补全的地方

| 位置 | 问题 |
|------|------|
| §2 M1 阶段分段 | 「>15 / 10–15 / 6–10 / ≤5」未写对应 Handler 类名或 `stage_router` 路由条件，和 lalala 的 `≤10` 对照不够「一行对一行」。 |
| §4 M1 单张管牌 | 写「在 `MidEarlyPassiveHandler` 等 Handler 内」，未指明**哪条路径**在管单张时是否调用 `HandStructureAnalyzer` / `OptimalCombinationScanner`（文档说「分散、针对性不足」，缺一条调用链证据）。 |
| §5 GUA-022 | 「阈值 2.25」「protection_score 积累」有结论，但**没有举例**（某一局：各 rule 打分 → 是否 PASS），非实现者难判断「过强」是否可复现。 |
| §7 战绩 | `victoryNum=[0,3,0,3]` 含义未解释（两队？几局？哪边是 M1）；PASS 率与「问题 PASS」定义（有非 PASS 仍 PASS）未链到日志字段。 |
| §3「一手出完」 | 与源码状态需区分：**开局** `OpeningActiveHandler` 明确注释不查一手出完；**残局/其它 Handler** 里仍有 `_check_one_hand_complete` / `check_one_hand_finish`。文档 §8 第 2 条略笼统，易被理解成「全引擎都没有」。 |

### 结构评价
- **最有价值**：§3（主动）、§4（单张被动）、§5（队友保护 + GUA-022）、§8（总结）。
- **相对薄弱**：§1（缺 lalala 仓库/版本指针）、§7（数据可复现性不足）、缺「建议改法优先级 / 验证指标」一节。

---

## 2. 读后感

### 对这篇分析印象最深的一点

本文把 M1 输 lalala 的主因收敛到**架构差异带来的行为差异**，而不是泛泛说「规则弱」：尤其是 **队友保护从 lalala 的「条件式 PASS」变成 M1 的「多规则累加 + 动态阈值」**，并点名 GUA-022 与 `protection_threshold=2.25`，这和 `strategy_engine.py` 里 `TeammateProtectionStrategy` / `OpponentSprintWhenTeammateLeadsRule` 的设计意图一致。

§4 对 lalala `Single()` 的「成员类型 / 不拆组合」拆解，也解释了为何通用 `PrioritySystem` 在管单张时可能不如专用分支。

§6 的 trade-off（可调参 vs 黑盒评分）对后续是继续修 M1 还是回退「分牌型 Handler」有决策价值。

### 本文最大的不足

**证据链不完整**：多处写「M1 对应实现」但未给文件路径、函数名或行号（对比 lalala 的 `action.py:964` 很不对称）。

**「一手出完」结论需分场景**：源码里开局主动确实写了「不需要检查一手出完」，但其它阶段仍有相关逻辑；§8 若不分场景，指导改代码时可能改错入口。

**战绩与因果**：0 胜 + 高 PASS 率能支撑「保护过激」叙事，但未排除通信层、动作列表解析、阶段误判等混杂因素，因果略跳。

### 还有哪些疑问或想深入了解的地方

1. **各 `*PassiveHandler` 在管单张时**，`PrioritySystem.select()` 的输入是否含 `combine_handcards` 等价信息？权重里有没有「破坏 bomb_member / straight_member」的硬惩罚？

2. **`should_protect` 为 true 时**，最终是强制 PASS（`get_protection_action` → 0）还是仍走 `select()`？两条路径的优先级在 `phase_handlers` 里谁先谁后？

3. **10 局 0 胜** 的复现命令、种子、双方座位与级牌规则是否固定？`victoryNum` 四维各代表谁？

4. lalala 的 **`one_hand()` 与 M1 `EndgameEarly/Late`** 在相同手牌下的动作 diff 抽样（哪怕 3–5 个典型局面），会比纯文字对照更有说服力。

---

## 3. 与源码的快速核对（支撑/修正文档）

**开局主动不做「一手出完」**——文档 §3/§8 在「开局」语境下成立：

```
50:77:C:\yifeGDBOT\.worktrees\t_58e744c5\src\decision\phase_handlers.py
    def handle(self, message: Dict) -> int:
        """开局策略：专注于建立牌型结构，不考虑快速出完"""
        ...
        # 开局不需要检查"一手出完"（优化：避免不必要的检查）
        # 开局策略：建立牌型结构
        result = self._build_structure_strategy(message, action_list, handcards)
```

**队友保护阈值与 GUA-022**——与 §5 一致：

```
196:234:C:\yifeGDBOT\.worktrees\t_58e744c5\src\decision\strategy_engine.py
    def should_protect(self, message: Dict, context: Dict) -> bool:
        protection_score = 0.0
        for rule in self.protection_rules:
            score = rule.evaluate(message, context)
            protection_score += score
        threshold = self._get_dynamic_threshold(message, context)
        return protection_score >= threshold
    ...
        base_threshold = float(self.config.get("protection_threshold", 2.25))
```

其它 Handler 中仍存在 `one_hand_idx = self._check_one_hand_complete(...)`，故改进文档时建议把「缺少一手出完优先」限定为 **OpeningActive / 中前期主动**，或单独列一张「各阶段是否检查 one_hand」表。

---

## 4. 自评

认真程度：**非常认真**（通读全文、对照 `INSTRUCT_M1_vs_lalala_cursor.md`、抽查 M1 源码验证关键论断）。
