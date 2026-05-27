# P0改进验证 - 第一阶段测试报告

**日期**：2026-05-27  
**测试类型**：自动化验证与参数调优  
**状态**：⏳ 初步验证完成，发现需要调优的参数

---

## I. 测试执行情况

### 第一轮测试（本地平台）

| 指标 | 结果 |
|-----|------|
| 游戏数 | 10局完成 ✓ |
| 平台启动 | 成功 ✓ |
| 游戏运行 | 成功 ✓ |
| 游戏记录保存 | ⚠️ 未保存（平台连接问题） |
| 分析脚本 | ⚠️ 解析错误 |

### 测试环境
- 本地掼蛋平台：guandan_offline_v1006.exe
- M1决策引擎：最新版本（含P0-①②③④改进）
- 对局方式：M1 vs M1（yf1_m1 + yf2_m1）

---

## II. 关键发现

### 检测到的问题

**问题1：两手规划未触发**
- 症状：搜索日志中未找到 `【P0改进②】` 标记
- 可能原因：`endgame_threshold` 设置为12太高，很少进入残局规划
- 建议调整：**12 → 10**（使更多残局进入规划）

**问题2：传牌动作未触发**
- 症状：搜索日志中未找到 `【P0改进③】` 标记
- 可能原因：PassiveHandler的触发条件过严格
  - `teammate_remain <= 15` 太保守
  - `card_power >= 4` 太保守
- 建议调整：**teammate_remain 15→12** 或 **card_power 4→3**

**问题3：分析脚本异常**
- 原因：第一轮游戏记录未保存
- 影响：无法验证两手规划和传牌的实际触发情况
- 解决：需要联网再测一次

---

## III. 参数自动调优方案

### 阶段1：激进调优（提高触发概率）

**文件1：`src/decision/endgame_planner.py`**
```python
# Line 14
# 修改前: endgame_threshold = 12
# 修改后: endgame_threshold = 10
```
**理由**：两手规划需要在更多残局中触发，10张牌时就应该进行两手规划

**文件2：`src/decision/teammate_opportunity_finder.py`**
```python
# Line 180 (should_prioritize_passing方法)
# 修改前: teammate_remain > 15
# 修改后: teammate_remain > 12
```
**理由**：当队友剩12-15张牌时也应该尝试传牌，帮助队友渡过mid阶段

**文件3：`src/decision/teammate_opportunity_finder.py`**
```python
# Line 186 (should_prioritize_passing方法)
# 修改前: card_power < 4
# 修改后: card_power < 3
```
**理由**：降低对自己牌力的要求，更积极地为队友创造机会

### 阶段2：保守调优（如果阶段1过度触发）

如果调优后发现两手规划或传牌动作过度触发，反向调整：
- `endgame_threshold`: 10 → 8（更激进）或 12 → 13（更保守）
- `teammate_remain`: 12 → 15（保守）或 9（激进）
- `card_power`: 3 → 2（激进）或 5（保守）

---

## IV. 实施计划

### 立即执行（Task A - 参数调优）

```bash
# 1. 修改endgame_planner.py
vim src/decision/endgame_planner.py  # Line 14: 12 → 10

# 2. 修改teammate_opportunity_finder.py
vim src/decision/teammate_opportunity_finder.py
  # Line 180: 15 → 12
  # Line 186: 4 → 3

# 3. 提交更改
git add -A
git commit -m "tuning(P0): 调低两手规划和传牌触发阈值"

# 4. 再次测试（10局以上）
python p0_verification_auto.py 10
```

### 二次验证（Task B - 效果评估）

测试完成后检查：
1. 日志中是否出现 `【P0改进②】` 和 `【P0改进③】`
2. 触发频率是否合理（两手规划: >1次/副, 传牌: >0.5次/副）
3. M1队胜场数是否改善

---

## V. 完整调优参数表

| 参数 | 文件 | 当前值 | 推荐值 | 激进值 | 保守值 |
|------|------|-------|-------|-------|-------|
| `endgame_threshold` | endgame_planner.py:14 | 12 | **10** | 8 | 13 |
| `teammate_remain` | teammate_opportunity_finder.py:180 | 15 | **12** | 9 | 18 |
| `card_power` | teammate_opportunity_finder.py:186 | 4 | **3** | 2 | 5 |
| `high_ranks` 列表 | history_tracker.py:147 | A,K,Q,J,T,9 | 不改 | A,K,Q,J,T,9,8 | A,K,Q,J,T |

---

## VI. 诊断清单

### 如果调优后效果仍未改善，检查：

- [ ] git status确认参数文件已保存
- [ ] 代码中是否有其他地方还使用旧参数常数（grep检查）
- [ ] PassiveHandler中P0-③的try/except是否吞掉了异常（启用debug日志）
- [ ] history_tracker是否正确初始化（检查stage_router.__init__）
- [ ] 是否有其他地方覆盖context中的history_info

### 调试模式（启用verbose日志）

```python
# 在 phase_handlers.py 的 P0-③ 集成代码中改为：
logger = logging.getLogger("PassiveHandler")
logger.setLevel(logging.DEBUG)

# 启用：
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## VII. 期望效果（调优后）

| 指标 | 当前状态 | 调优后目标 |
|-----|---------|----------|
| 两手规划触发次数 | 0 | >10次/100副 |
| 传牌动作次数 | 0 | >5次/100副 |
| 残局PASS率 | 高 | 明显下降 |
| M1队胜场 | 0/298 | ≥1/10副 |
| 控场能力 | 被动 | 更积极 |

---

## VIII. 风险评估

| 调优项 | 风险等级 | 可能副作用 |
|------|--------|---------|
| 降低endgame_threshold | 低 | 可能在mid阶段误触发两手规划 |
| 降低teammate_remain | 中 | 传牌过度可能导致自己无牌可出 |
| 降低card_power | 中 | 可能在弱牌时做出不稳健决策 |

**缓解措施**：所有调优都包装在try/except中，失败时自动回退。

---

## IX. 后续工作（如果本轮有效）

### P1改动（下一阶段）
- [ ] 激活bomb_strategy()的P0-④规则
- [ ] 增强对手建模（基于history的统计分析）
- [ ] 队伍协作深化（如主动预留牌给队友）

### P2改动（远期）
- [ ] Lv3全局对抗策略
- [ ] 强化学习集成
- [ ] 多轮策略规划

---

## X. 执行脚本

快速执行调优的shell脚本（自动修改+测试）：

```bash
#!/bin/bash
# p0_quick_tune.sh - P0参数一键调优

echo "【阶段1】修改参数..."
# 修改endgame_planner.py
sed -i 's/endgame_threshold = 12/endgame_threshold = 10/g' src/decision/endgame_planner.py

# 修改teammate_opportunity_finder.py
sed -i 's/teammate_remain > 15/teammate_remain > 12/g' src/decision/teammate_opportunity_finder.py
sed -i 's/card_power < 4/card_power < 3/g' src/decision/teammate_opportunity_finder.py

echo "【阶段2】提交更改..."
git add -A
git commit -m "tuning(P0): 激进调低两手规划和传牌触发阈值"

echo "【阶段3】运行测试..."
python p0_verification_auto.py 10

echo "✓ 调优完成！检查log/results"
```

---

**下一步**：执行上述参数调优，再运行一轮10局对战验证效果。

