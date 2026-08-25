# GUA-278 完成定义

**原则**（match [`6a8d4603`](https://www.botzone.org.cn/match/6a8d46030fbd680d7c8309f2)）：

> 下家敌 `remaining≤2` 且 `actionList` 有 Bomb/StraightFlush 时，**禁止**「拆核→PASS」；改出最廉炸族截断。不要优先 GUA-135 min TWT 再被拆核拦死。

关联：GUA-135、GUA-150、GUA-199（拆核转 PASS）、GUA-252（敌≤5 拆核豁免，本刀是炸兜底而非豁免拆核）。

---

## 定音

| 项 | 内容 |
|----|------|
| 触发 | `greaterPos == (myPos+1)%4`（下家）且其 `remaining∈{1,2}`，且 actionList 含 Bomb 或 StraightFlush |
| 行为 | ① GUA-135 / GUA-150 夺权前优先最廉炸；② Q1 若已选非 PASS 且拆核，改最廉炸而非 PASS |
| 最廉 | Bomb ≻ StraightFlush；同族张少 ≻ 点小（`_select_cheapest_bomb_or_sf`） |
| 非触发 | 上家敌；下家 rem>2；无炸族候选 |

## 停手

```bash
python -m pytest tests/test_gua278_lower_enemy_critical_bomb.py -q
```

构造态：下家 TWT/K + rem=2 + 拆核 TWT 与 Bomb 同在 actionList → 出 Bomb/3 非 PASS。
