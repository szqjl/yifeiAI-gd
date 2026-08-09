# GUA-217 配子补普通顺子缺位：actionList 生成器 `_generate_straights` 缺配子支持 — 细案

> 登记：2026-08-09 · 状态：修复已实现，待 commit/重启监听/实局验证
> 对局：match `v8_14_online_6a7772fb`（2026-08-09 03:37，tmp/v8_14_online_requests.json 回合 12）
> 日志：`logs/fetch_match_v8_14_online.log`（重放）

## 一、场景复现

3 号玩家（player2=v8_14 在线 bot）出完 Bomb/K 后领出，剩余手牌 5 张：

```
['HA', 'D2', 'H2', 'D4', 'S5']
```

H2 为配子（级牌 2 的红桃），可当任意非大小王牌。**组牌引擎已识别**：

```
G0(straight):['HA', 'D2', 'H2', 'D4', 'S5']  ← A2345 顺子（H2 当 3）
```

但实际决策输出 `[[0],[0]]`（Single/A，拆 HA），未打整把顺子。

## 二、决策链（修复前）

```
组牌引擎: role=主攻 handCards=5 → G0(straight) 已识别 A2345
actionList 摘要: len=6 types={'Single': 5, 'Pair': 1}   ← 无 Straight！
endgame_decider → Q0 自己冲刺: idx=0 type=Single
残局管线命中: actIndex=0 cards=['HA']
决策: Single/A
```

**组牌引擎识别了顺子，但 actionList（候选池）里根本没有 Straight**，残局管线只能从
Single×5 + Pair×1 中选，选了大单张 A。

## 三、根因

`src/communication/botzone_adapter.py` 的 `ActionListGenerator._generate_straights`（L602）
只用自然 rank 枚举顺子窗口：

```python
rank_set = set(rank_groups.keys())
for window in self._straight_windows(rank_set):
    ...
```

手牌 `HA D2 H2 D4 S5` 的自然 rank = {A, 2, 4, 5}（H2 归入 rank '2' 组），缺 '3'，
A2345 窗口无法通过 `all(r in rank_set)` 检查 → **普通顺子候选永远无法由配子补缺位**。

对比：同花顺生成器 `_generate_h2_wild_straight_flushes`（L643）**有**配子补缺位逻辑
（`wild = f"H{self.cur_rank}"` 动态级牌，缺位数 ≤ 配子数时用配子补），但只用于同花顺。
普通顺子无对应实现。

另：`_build_bz_claim`（L1447）只处理 `Bomb`/`StraightFlush` 的配子 claim 替换；若
普通 Straight 含配子，claim 须把配子替换为所代表 rank 的牌，否则裁判判（G2）INVALID_TYPE。

## 四、修复方案

| 位置 | 改动 |
|------|------|
| `ActionListGenerator` 新增 `_generate_wild_straights` | 基于 10 个标准窗口枚举，剔除配子后的自然 rank 缺位 ≤ 配子数时用配子补位生成 Straight 候选 |
| `_generate_straights` 签名 | 追加 `hand_cards` 参数，内部叠加 `_generate_wild_straights` 候选 |
| `generate_lead_actions` L261 后 | `actions.extend(self._generate_straights(rank_groups, suits, hand_cards))` |
| `generate_follow_actions` Straight 分支 L295 后 | `actions.extend(self._generate_wild_straights(hand_cards, greater_straight_top))` |
| `_build_bz_claim` L1460 附近 | 新增 `Straight` 分支：含配子时 `_replace_straight_covering` 替换 claim |
| 新增 `_replace_straight_covering` | 仿 `_replace_sf_covering`/`_replace_bomb_covering`，把配子替换为所补 rank 的牌 |

关键约束：
- 配子 `H{cur_rank}` **动态**（级牌可为 2..K、A，平台 level 字段），非写死 H2；
- 一个窗口至多补 `wild_count` 个缺位（双副可能 2 张配子）；
- 缺位数 = 0 的窗口跳过（自然顺子已由 `_generate_straights` 生成，避免重复）；
- 配子放在 cards 末尾（参照 `_wild_bomb_candidates` 注释，保证 rank 判定用自然牌）；
- 跟牌轮须比窗口最高牌（`_rank_to_order(window[-1], cur_rank)`）压 greater，与
  `_straight_top_order` 一致。

## 五、验证

- [x] 最小复现：`generate_lead_actions(['HA','D2','H2','D4','S5'])` 修复前仅
      `Single×5 + Pair×1`，修复后含 `Straight/A ['HA','D2','D4','S5','H2']`（H2 当 3）；
- [x] 动态级牌：`cur_rank=6` 时 H6 补 2-6 窗口缺位生成 `Straight/2`（非写死 H2）；
- [x] 跟牌轮：H2 补 4 的 4-8 顺子可压 3-7 greater（比窗口最高牌），生成器正确过滤；
- [x] `_build_bz_claim` 对含配子 Straight 输出替换后的 claim（H2→C3，判型唯一）；
      配子作自然级牌（A2345 窗口 H2 当 2）时 claim==action 不替换；
- [x] 回归：`tests/test_botzone_adapter.py` 100 通过（新增 4 条 GUA-217 用例）；
      `test_gua164`/`test_grouping_engine`/`test_card_mask_group_members` 等 103 通过
      （`test_forward_wrap_real_game` 失败为缺失 game_records 文件的既有问题，与本改动无关）；
- [x] 决策链路：组牌引擎 G0(straight) 与 actionList Straight/A 现可精确匹配
      （日志 `logs/fetch_match_v8_14_online.log` 原「推荐精确匹配失败 → 拆 HA」路径消除）；
- [ ] 实局/Botzone 验证后关闭。
