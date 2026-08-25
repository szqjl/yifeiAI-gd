# GUA-275 / 276 / 277 完成定义

**原则真源**（match [`6a8d3d40`](https://www.botzone.org.cn/match/6a8d3d400fbd680d7c8303ba) 全局面复盘）：

> **同型顺压 > 保级牌/对子结构 > 炸**；领出优先消耗无控力的中小结构，勿先甩 K/王。

关联：**GUA-274**（P0a 误硬拦，已实施）。

---

## GUA-275 · 有同型可压时禁止 R11 改炸

| 项 | 内容 |
|----|------|
| 锚点 | 对10 时 `actionList` 含 Pair×3 却 Bomb/3 |
| 定音 | `_recommend_play` 跟上家改炸前：若 `actionList` 仍有能压 `greater` 的同型非炸动作 → **禁止改炸**，改出最廉同型 |
| 例外 | `greater` 已是 Bomb/SF；或同型候选全部拆 Bomb/SF 核 |
| 停手 | 构造态：Pair/T + JJ/QQ/对2 + 炸 → 出 Pair/J 非 Bomb；无同型时仍可 R11 |

## GUA-276 · 跟单勿拆 TWT/级牌 trips 核（有王可压时）

| 项 | 内容 |
|----|------|
| 锚点 | `Single/A` 时拆 `trip_in_three_with_two` 的 `D2`，手中有 `SB` |
| 定音 | 有 SB/HR 能压时，**禁止**优先拆 `trip_in_three_with_two` / `trips`(级牌) 出单；王控单优先于拆核级牌 |
| 边界 | 无王且无其他可压散单时，仍可按 GUA-233 拆级牌 trips |
| 停手 | 构造态：TWT 核三张2 + SB，压 Single/A → Single/B 非 Single/2 |

## GUA-277 · 中局领出手牌>10：禁优先高耗损单

| 项 | 内容 |
|----|------|
| 锚点 | Bomb/3 回手后 18 张领出 `Single/K`，仍有 JJ/QQ/对2/顺 |
| 定音 | `len(hand)>10` 自由领出时：若散单仅剩 K/A/级牌/王等高耗损，**优先 loose 小对或顺**，勿先甩 K |
| 例外 | 无敌对/无敌顺可领；残局 `rest≤10` 不走本条（交残局管线） |
| 停手 | 构造态：散单仅 SK+DA+SB + loose Pair/8 + Straight → 领 Pair/8 或 Straight，非 Single/K |

---

## 验收命令

```bash
python -m pytest tests/test_gua275_276_277_hand_clear_priority.py -q
```
