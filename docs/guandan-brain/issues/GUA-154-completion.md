# GUA-154 完成定义：重复牌串跨组归属不得漏检拆核

> **状态**：implemented（2026-07-21；构造态、trace 与回归通过，待 V8 批跑关单）
> **WF-12 锚点**：`20260721070501773000 [yf1_v8]-[opponent_1_3]-[6]-[2].json` 步 **17/81**
> **关联**：GUA-063、GUA-070、GUA-075、GUA-082、GUA-091、GUA-098

## 0. 现象

两副牌中的两个同名 `C3` 分属不同组：一个属于 `StraightFlush C2-C6`，另一个属于 `ThreePair` 的 33 子组。**该组牌方案正确，体现了同名牌实例可以灵活分配到不同结构。** 缺陷发生在 `to_card_mask()` 导出阶段：实例级方案被压成 `card_mask: Dict[str, tuple]`，只能保留一个 `C3` 归属，后写的 `pair_in_three_pair` 覆盖同花顺归属。

结果：

1. `Trips/3 [C3,D3,C3]` 被 `_get_broken_core_type()` 误判为 `broken=None`。
2. `_heuristic_select()` 把三个牌串都映射到同一 gid，错误判为 group-consistent 并奖励 `+10000`。
3. 完整 `StraightFlush` 反因 `C3` 指向另一 gid，被误判为跨组拆核或受到拆局扣分。
4. 实战选择 `Trips/3` 后，`natural_turn_count` 从 6 增至 7，`single_residue` 从 2 增至 4。

## 1. Phase A 收敛

| 项 | 内容 |
|----|------|
| 表示层 | 保留正确的灵活组牌方案；另为同牌串保存全部实例/组归属，不得再以单值 `Dict[str, tuple]` 作为 touched-gid 真源 |
| 拆核判定 | `_get_broken_core_type()` 按动作牌多集合与 `group_members` 的全部潜在归属检查；任一核心组被部分消费即判拆核 |
| 自由领出 | `Trips/3` 同时消费同花顺 `C3` 与 33 子组时必须被拦截；不得因动作张数超过单个 gid 成员数而判为完整组 |
| 启发式 | `_is_group_consistent()` 与 `_group_break_penalty()` 使用实例感知归属；禁止给本锚点 `Trips/3` 加 `+10000` |
| 平台映射 | `StraightFlush`、`Trips`、`ThreePair` 保持平台标准名；`pair_in_three_pair` 仅为内部子组名 |

## 2. 停手条件

1. ✅ 构造态复现锚点 20 张手牌，完整 `StraightFlush C2 C3 C4 H7 C6` 不被判拆核。
2. ✅ `Trips/3 C3 D3 C3` 被识别为拆 `StraightFlush`，自由领出时从候选中移除。
3. ✅ 覆盖“两张同名牌分属两个 core 组”“同名牌全部属于同一炸弹”“动作重复张数大于单个 gid 成员数”三类多集合测试。
4. ✅ 最终动作 trace 记录 `action`、`memberships`、`allocation`、`broken_types`，便于 WF-12 复核。
5. ⏳ V7/V8 共享测试已通过；仍需净盘 V8 至少 3 局，确认日志中不再出现同类 `Trips` 拆 `StraightFlush` 的误放行。

## 3. 实现与验证

- 保留 `to_card_mask()` 三返回值兼容接口；新增 `_build_card_memberships()` 从 `group_members` 派生 `card → {gid: 实例数}`。
- `_best_group_allocation()` 为平台动作中的同名牌选择最小拆核实例分配；优先保留 `Bomb` / `StraightFlush`，同时允许使用真正的散张副本。
- `_get_broken_core_type()`、自由领出复合组检查、heuristic 组局一致性和拆局扣分统一消费实例分配结果。
- 锚点结果：`memberships[C3]={0:1,4:1}`；`Trips/3 broken=StraightFlush`；完整 `StraightFlush broken=None`；过滤映射 `[-1,0]`。
- heuristic：修复前 `Trips/3=9977`、`StraightFlush=-254`；修复后 `Trips/3=-318`、`StraightFlush=10046`。
- 性能：10,000 次拆核检查总计约 316ms，平均约 `31.6µs/次`。
- pytest：`92/92` core/Guard/heuristic，`61/61` 组牌引擎，`73/73` 残局/推荐/反炸；另一次扩展集 `177` 项通过，唯一失败为既有 V7 launcher 测试假设模块含 `subprocess` 属性，与本改动无关。

## 4. 建议测试

```bash
python -m pytest tests/test_card_mask_group_members.py tests/test_gua063_grouping_nn_bridge.py tests/test_gua116_main_attack_lead.py -q
```

新增：`tests/test_gua154_duplicate_card_cross_group.py`。
