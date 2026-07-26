# Handoff: GUA-168 末局 bomb+单张 先出单试探修复

| 字段 | 内容 |
|------|------|
| 日期 | 2026-07-26 |
| 分支 | `v8-dev` |
| 状态 | **代码修复 + 测试新增，已验证通过** |
| 关联 ISSUES | GUA-168（新增） |
| 关联迭代 | ITERATIONS `v8-endgame-bomb-single-lead-fix` 行 |
| 锚点 | `game_records_v8/20260725173841056937 [yf1_v8]-[opponent_1_3]-[13]-[2].json` 步 75-85 |

## 背景（2 句）

yf1_v8 第 13 局第 2 副，手牌剩 `CA` (单A) + `StraightFlush/A` (S2,S3,S4,HA,SA)，对手 1 剩 5 张、对手 3 剩 10 张（均非 1 张）。原逻辑（GUA-151）直接出 StraightFlush/A 导致单 A 无人管、对手回手；正确策略应先出单 A 试探，StraightFlush 兜底。

## 修复前行为（错）

> GUA-151 `bomb_size >= total_cards - 1` 触发 → 直接出炸弹（StraightFlush/A）→ 单 A 留最后被对手管制

## 修复后行为（对）

> 检测到手牌结构为 **bomb(5张) + 单张(1张)** 且 **对手无人剩 1 张** → 优先出单 A（idx=1）→ 对手不过则 StraightFlush/A 兜底（idx=2）收官

## 代码改动点

**文件**：`src/v/nn/endgame/endgame_decide.py`

1. `_q0_self_sprint()` 新增 `_is_bomb_plus_single()` 结构识别
2. `_q0_self_sprint()` 新增 `_any_enemy_has_one_card()` 对手剩牌检查
3. GUA-151 `bomb_size >= total - 1` 条件前置增加：
   - 非 bomb+单张结构 → 走原逻辑
   - bomb+单张但对手有人剩 1 张 → 走原逻辑（保留 GUA-151 抢跑保护）
   - bomb+单张且对手均非 1 张 → **跳过 GUA-151**，进入正常排序（单张优先）

## 测试新增

**文件**：`tests/test_gua168_bomb_plus_single_lead.py`（4 用例全绿）

| 用例 | 场景 | 期望 |
|------|------|------|
| `test_gua168_bomb_plus_single_lead_prefers_single_first` | 对手 5/10 张 | 先出单 |
| `test_gua168_bomb_plus_single_enemy_has_one_card_fallback_to_bomb` | 对手 1/10 张 | 直接出炸弹（GUA-151） |
| `test_gua168_bomb_plus_single_both_enemies_one_card` | 对手 1/1 张 | 直接出炸弹（GUA-151） |
| `test_gua168_not_bomb_plus_single_structure` | 手牌非 bomb+单张 | 走原逻辑，不触发新分支 |

## 术语对齐（强制）

| 内部 | 平台标准名 |
|------|-----------|
| `StraightFlush` | `StraightFlush`（同花顺 > 5星炸） |
| `Single` | `Single`（单张） |
| `Bomb` | `Bomb`（炸弹统称） |

> 代码注释、测试、文档均按平台标准写法；内部结构键如 `group_type: trip_in_three_with_two` 等保留行内注释对照。

## 行动清单

| 文件 | 改动 |
|------|------|
| `src/v/nn/endgame/endgame_decide.py` | 修复 GUA-168 核心逻辑 |
| `tests/test_gua168_bomb_plus_single_lead.py` | 新增 4 个 pytest |
| `docs/guandan-brain/ISSUES.md` | 新增 GUA-168 条目 |
| `docs/guandan-brain/ITERATIONS.md` | 追加 `v8-endgame-bomb-single-lead-fix` 行 |
| `docs/guandan-brain/handoff/2026-07-26-GUA-168-endgame-bomb-single-lead-fix.md` | 本 handoff |

## 验证命令

```bash
# 单测 GUA-168
python -m pytest tests/test_gua168_bomb_plus_single_lead.py -v

# 全量 endgame 回归（排除 GUI 无关测试）
python -m pytest tests/ -k "endgame or GUA-15" -v --ignore=tests/test_gui_launch.py
```

## 一句话结论

> **末局 bomb+单张结构、对手无人 1 张时：先出单试探、炸弹兜底**；GUA-151 仅在对手有人 1 张时触发抢跑保护，两者互补不冲突。