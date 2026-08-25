# V9 Botzone 在线 Bot（轻量 DMC）

V8 规则栈在线 Bot 保持不变（`scripts/launchers/botzone/`）。  
本目录为 **V9**：NumPy DMC + V8 `ActionListGenerator`（与 `fd_v8_bridge` 训练对齐）。

## 打包

```bash
python scripts/launchers/botzone_v9/package_v9_dmc_online.py
python scripts/launchers/botzone_v9/package_v9_dmc_online.py --dry-run
```

产出：`data/eval/botzone/v9_dmc_online_bot_YYYYMMDD_v9_N.zip`

**注意**：V9 zip 内 `src/v/nn/__init__.py` 为轻量 stub，**不得**含 V7 引擎 import；若线上报 `No module named ultimate_win_rate_engine_v7`，请重新打包并上传新 zip。

## 权重（Botzone 用户存储）

上传至 Botzone「用户存储空间」，优先文件名：

1. `data/dmc_v9_weights.npz`
2. `data/dmc_v8_bridge_A150.npz`
3. `data/dmc_fd_native_A150.npz`

本地开发可自动回退到仓库 `models/dmc_*.npz`（仅本地，不上传）。

## 本地验证

```bash
python -m pytest tests/test_dmc_botzone_decide.py -q

# deal + play 冒烟
python -c "
import json, subprocess, sys
deal={'stage':'deal','your_id':0,'deliver':list(range(27)),'global':{'level':'2'}}
play={'stage':'play','your_id':0,'global':{'level':'2'},'done':[],'history':[],'pass_on':-1}
payload=json.dumps({'requests':[deal,play],'responses':[[]]})
subprocess.run([sys.executable,'scripts/launchers/botzone_v9/__main__.py'],input=payload,text=True)
"
```

## 决策链

```
Botzone JSON → BotzoneMirror（FableDan obs）
            → ActionListGenerator（V8 actionList）
            → list_mappable_v8_actions + DmcMlp argmax
            → [[cards_int], [claim_int]]
```

进贡/还牌走 FableDan 规则函数，不经 DMC。
