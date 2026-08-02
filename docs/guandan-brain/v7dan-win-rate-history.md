# V7Dan 队胜率历史（v7dan vs DanZero）

> **目的**：v7dan 实验线（v1006 平台，队A = yf1_v7dan+yf2_v7dan 的 V7 引擎，队B = DanZero client3/client4）对战 KPI 追踪。每次批跑结果强制记录，与 V7（vs Lalala）、V8（OpenGuanDan）分开统计。
> **创建**：2026-07-31（真实 DanZero DMC 接入后首跑）
> **关联**：[`ITERATIONS.md`](./ITERATIONS.md)、[`SCRIPT_INDEX.md`](./SCRIPT_INDEX.md) §scripts/launchers/v7dan/
>
> **对手权重可信性（2026-08-02 已校验）**：队B 挂载 `models/danzero/q_network.ckpt`（DMC Q-net，论文 arXiv:2312.02561 主方法）经 SHA-256 实测与官方 `submit-paper/Danzero_plus/wintest/danzero/q_network.ckpt` **逐字节一致**（5,368,401 字节，hash `A6F132E5...7EA1A3`）→ 官方 30 天训练权重，非占位/伪造。PPO 部分官方未放权重未挂载。详见 [`offline_platform/danzero_plus/README.md`](../../offline_platform/danzero_plus/README.md)。

---

## 记录格式（每次批跑一行）

```
| 日期 | 目标 GUA | 改动摘要 | 批跑命令 | 局数 | V7Dan 队胜率 | 副数 | 备注 |
```

**字段说明**：
- **局数**：`--games N`（任意正整数）
- **V7Dan 队胜率**：`victoryNum[0]` vs `[1]`（0+2 一队，1+3 一队；禁止四席相加）
- **副数**：`game_records_v7dan/` mtime 窗新增 JSON 数 / 2（yf1/yf2 双录）
- **备注**：副胜率 / 末级分布 / 残局扫描 / 日志文件名 / 与上批对比

---

## 记录

| 日期 | 目标 GUA | 改动摘要 | 批跑命令 | 局数 | V7Dan 队胜率 | 副数 | 备注 |
|------|---------|---------|---------|------|----------|------|------|
| 2026-07-31 | 实验线（无 GUA） | **真实 DanZero（DMC Q-net）接入 + 批跑死循环修复首跑**。`src/communication/danzero_nn.py`（567 维 state → argmax Q）+ `danzero_policy.py` 重写；`executor.py` +`record_dir` 参数修复 v7dan 超时兜底误查 M3 目录 | `python scripts/launchers/v7dan/run_v7dan_vs_danzero_games.py --games 3` | 3 | **3/3（100%）** | **30** | 副胜 **20/30（66.7%）**；队头游率 66.7%（yf1=12 / yf2=8）；双上率 46.7%；双下率 16.7%；末游率 yf1=3.3% **yf2=26.7%**；V7 末级 ≤5:12 / J-K:6 / A:4；残局扫描 Q 命中 85.9%（Q1=655/Q3=17）；R-G080-4 零退化；`restart_count=0`；L1 `victoryNum=[3,0,3,0]` L1/L3/L3′ 一致；日志：`logs\v7dan_vs_danzero_20260731_213025.log`。vs V7 对 Lalala 历史最高副胜 25.5%（GUA-065）——对手不同（DanZero≠Lalala）不可直接跨线比较。 |
| 2026-07-31 | 实验线（无 GUA） | 无代码变更。9 局目标批跑第 3 批被中断（23:06 启动、23:22 游戏中段终止），净完成 **6/9**（批次 1+2），批 3 未计入 | `python scripts/launchers/v7dan/run_v7dan_vs_danzero_games.py --games 9` | 6 | **5/6（83.3%）** | **134** | 批 vn 分列：批1 `[2,1,2,1]`（V7 2:1）、批2 `[3,0,3,0]`（V7 3:0）；副胜 **86/134（64.2%）**（会话1 68.8% / 会话2 57.4%）；双上率 38.1%、双下率 15.7%；队头游率 64.2%；末游率 yf1=16/134（11.9%）、**yf2=27/134（20.1%）**；V7 末级 ≤5:44 / J-K:26 / A:18（达 A 副数 18）；yf1 PASS 47.4%（近似 1211）/ yf2 43.6%（近似 1044）；窗口内 1 损坏 `[yf2]…[42]`，批3 残留 2 损坏未计入；`restart_count=2`、`completed_games=6/9`（批3 中断，state 停在 batch3）；日志 `logs\v7dan_vs_danzero_20260731_222223.log`。vs 首跑 3/3（100%）——样本小，差异不显著。 |
| 2026-08-02 | 实验线（无 GUA） | 无代码变更。续跑 3 局（补足 9 局样本）；DanZero 侧 `danzero_nn.py` 加载官方 DMC Q-net 权重（已 SHA-256 校验=`submit-paper/Danzero_plus/wintest/danzero/q_network.ckpt`，见 `offline_platform/danzero_plus/README.md`） | `python scripts/launchers/v7dan/run_v7dan_vs_danzero_games.py --games 3` | 3 | **3/3（100%）** | **42** | 本批 vn `[3,0,3,0]`（L1 自检通过）；副胜 **30/42（71.4%）**；双上率 47.6%、双下率 9.5%；队头游率 71.4%；末游率 yf1=6/42（14.3%）、yf2=8/42（19.0%）；V7 末级 ≤5:17 / J-K:6 / A:6（达 A 副数 6）；DanZero 模型真实加载（`load tf weights success (DMC Q-net, 6 layers)`，client3 有非 0 决策如 ThreeWithTwo/Pair）非骨架降级；`restart_count=0`、`completed_games=3/3`；日志 `logs\v7dan_vs_danzero_20260802_085935.log` + `danzero_20260802_090009.log`。**累计（首跑 3 + 中断批 6 + 本次 3）**：9 局目标达成，V7 队胜 **8/9（88.9%）**，副级 20/30+86/134+30/42 = 136/206（66.0%）。 |
| 2026-08-02 | 实验线（无 GUA） | 无代码变更。**净盘后 21 局扩样本**（`game_records_v7dan` 清空 404 残留再跑）；DanZero 官方 DMC Q-net 权重不变（SHA-256 已校验） | `python scripts/launchers/v7dan/run_v7dan_vs_danzero_games.py --games 21` | 21 | **19/21（90.5%）** | **279** | 批 vn（7 批×3）：批1 `[2,1,2,1]`、批2~6 `[3,0,3,0]`×5、批7 `[2,1,2,1]` → Team A 2+3×5+2=**19**（scores.json `team_a_wins=19` 与 analyze 累加 `[19,2,19,2]` 三方一致）；副胜 **191/279（68.5%）**（会话副胜 51.4/85.4/61.3/75.0/71.8/64.3/69.0%）；双上率 40.5%（113/279）；双下率 15.4%（43/279）；队头游率 68.5%；末游率 **yf1=38/279（13.6%）/ yf2=71/279（25.4%）**（yf2 末游持续偏高，会话1 达 35.1%）；V7 末级 ≤5:96 / J-K:56 / A:38；`restart_count=6`（7 批，正常）、`completed_games=21/21`；日志 `logs\v7dan_vs_danzero_20260802_090832.log`。vs 前 9 局累计 8/9（88.9%）——样本扩大后 90.5%，**yf2 末游率偏高仍待 WF-12 抽查**。 |

---
