# M1 对 lalala 测试计划（GUA-022）

> 目标：系统验证 M1 对 lalala 的 P0 追赶效果  
> 负责人：hermes-win（项目负责人授权 CLI 执行）  
> 日期：2026-05-21  
> 状态：草稿，待良总确认后执行

---

## 一、基线确认

**当前基线（未经任何改动）**：

| 指标 | 值 | 来源 |
|------|----|------|
| M1 vs lalala 队胜率 | **0%** | `victoryNum=[0,3,0,3]`（EVAL.md L58，实测记录） |
| 测试局数标准 | **16局/次** | 离 platform 说明书 |
| 达标线 | **>50%** | 同上 |
| 战队编排 | 队A：yf1_m1(pos0) + yf2_m1(pos2) vs 队B：lalala client3(pos1) + client4(pos3) | `START_M1_GUI.bat` |

**基线复现方式**：
```bash
cd C:\yifeGDBOT
py batch_executor_gui_m1.py
# 或无头 CLI（需指定 m1 四客户端 + server path）
python -m batch_executor --server-path "offline_platform/guandan_offline_v1006.exe" --target-games 16 --clients src/communication/yf1_m1.py src/communication/run_lalala_client3.py src/communication/yf2_m1.py src/communication/run_lalala_client4.py
```

**胜负判定**：victoryNum[0] > victoryNum[1] → 队A（YiFei/M1）胜；否则负。

---

## 二、测试矩阵（迭代用）

每次代码改动后，按以下顺序执行：

### 阶段 1：P0 改动验证

| 测试编号 | 测试内容 | 验收标准 |
|---------|---------|---------|
| T1 | `combine_handcards` 移植（lalala `utils.py:13`） | 独立可测，不影响现有流程 |
| T2 | `choose_bomb` 移植（lalala `utils.py:297-367`） | 同上 |
| T3 | context 补维度（`pass_num` / `numofnext` / `numofgreaterPos`） | `_build_context()` 输出包含缺失字段 |
| T4 | T1+T2+T3 合并后 16 局对 lalala | **>50% 队胜率** |

### 阶段 2：P1 改动验证

| 测试编号 | 测试内容 | 验收标准 |
|---------|---------|---------|
| T5 | Single/Pair 被动规则移植（去重 ProtectionStrategy） | 16 局对 lalala，胜率环比 T4 提升 |
| T6 | active 优先级链替换 | 同上，影响较大需 eval 把关 |

### 阶段 3：GUA-022 根因隔离验证

目标：区分 `should_protect()` 和 `combine_handcards` 各自影响。

| 测试编号 | 测试内容 | 方法 |
|---------|---------|------|
| T7 | 只改动 `should_protect()` → 复现 0% 胜率 | 对比改动前后基线，确认 GUA-022 根因 |
| T8 | 只移植 `combine_handcards` → 复现 0% 胜率 | 隔离变量 |
| T9 | 两者同时移植 → 观察是否有质变 | 关键测试 |

**注意**：T7/T8/T9 是代码改动，不是测试脚本改动。

---

## 三、执行脚本（Cursor 负责）

> **架构发现（2026-05-22）**：
> - M1 客户端（yf1_m1.py/yf2_m1.py）使用 `RuleBasedDecisionEngineM1`
> - 决策链路：`yf1_m1.py` → `RuleBasedDecisionEngineM1` → `BasePhaseHandler` → `HandStructureAnalyzer` → `HandCombiner.combine_handcards()`
> - `HandCombiner` 来自 `game_logic/hand_combiner.py`（**不是** `communication/utils.py`！）
> - `strategy_engine.py`（TeammateProtectionStrategy）通过 `BasePhaseHandler._init_strategy_engine()` 被引用
> - 测试 patch 目标：T7→`strategy_engine.py` ✅，T8/T9→`game_logic/hand_combiner.py`（已修复）


### 3.1 基线测试脚本

```python
# test_m1_vs_lalala_baseline.py
# 用法：python test_m1_vs_lalala_baseline.py --games 16
import subprocess, json, glob, sys
from pathlib import Path
from collections import defaultdict

GAME_RECORDS_DIR = Path("game_records")
SERVER_PATH = "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"
CLIENTS = [
    "src/communication/yf1_m1.py",
    "src/communication/run_lalala_client3.py",
    "src/communication/yf2_m1.py",
    "src/communication/run_lalala_client4.py",
]

def run_games(n):
    cmd = [
        sys.executable, "-m", "batch_executor",
        "--server-path", SERVER_PATH,
        "--target-games", str(n),
        "--clients", *CLIENTS,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def parse_victorynum(record_path):
    with open(record_path) as f:
        d = json.load(f)
    # 尝试从 game_info / result / victoryNum 提取
    # 见 EVAL.md：victoryNum 队伍维度
    # pos0+2=队A(M1)，pos1+3=队B(lalala)
    for key in ["game_info", "result", "game_result"]:
        if key in d:
            vn = d[key].get("victoryNum", []) if isinstance(d[key], dict) else []
            if vn:
                return vn
    return None

def main(n=16):
    # 跑游戏
    ok = run_games(n)
    if not ok:
        print("[FAIL] 游戏未完成")
        return
    
    # 解析记录
    new_records = sorted(Path(GAME_RECORDS_DIR).glob("*yf1_m1*.json"),
                         key=lambda p: p.stat().st_mtime, reverse=True)[:n]
    
    wins, losses = 0, 0
    for r in new_records:
        vn = parse_victorynum(r)
        if vn is None:
            continue
        # 队A = pos0+2, 队B = pos1+3
        team_a = vn[0] + vn[2]  # yf1_m1 + yf2_m1
        team_b = vn[1] + vn[3]  # lalala
        if team_a > team_b:
            wins += 1
        else:
            losses += 1
    
    total = wins + losses
    win_rate = wins / total if total > 0 else 0
    print(f"局数：{total}，胜：{wins}，负：{losses}，胜率：{win_rate:.1%}")
    
    # 通过标准
    if win_rate > 0.5:
        print("[PASS] 达标")
    else:
        print("[FAIL] 未达标")

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 16)
```

### 3.2 GUA-022 根因隔离测试脚本

```python
# test_gua022_isolation.py
"""
T7/T8/T9：隔离 should_protect() vs combine_handcards 的各自影响

策略：
- T7: 注释掉 should_protect() 调用，观察对胜率影响
- T8: 只保留 combine_handcards 移植，不动 should_protect
- T9: 两者同时生效

每轮测试前需改代码 → 跑 16 局 → 记录 victoryNum
"""

import subprocess, json
from pathlib import Path

SERVER_PATH = "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"

def run_and_report(clients_config, label):
    """跑 16 局，返回胜负统计"""
    # clients_config = ["yf1_m1.py", "run_lalala_client3.py", ...]
    cmd = [sys.executable, "-m", "batch_executor",
           "--server-path", SERVER_PATH,
           "--target-games", "16",
           "--clients", *clients_config]
    result = subprocess.run(cmd, capture_output=True)
    # 解析 victoryNum...
    # （完整实现同上）
    return {"wins": 0, "losses": 0, "win_rate": 0.0}  # placeholder
```

---

## 四、执行顺序

```
1. Cursor 写 test_m1_vs_lalala_baseline.py
   ↓
2. Cursor 写 test_gua022_isolation.py  
   ↓
3. 执行 T7/T8/T9（隔离测试）
   ↓
4. 评审 → 发现 GUA-022 根因
   ↓
5. P0 代码改动（T1+T2+T3）
   ↓
6. Cursor 评审代码
   ↓
7. 跑 T4（16局）
   ↓
8. 评审结果
   ↓
9. 决定下一步（T5/T6 或直接收尾）
```

---

## 五、质量门控

- 代码改动必须经过 **交叉评审**（opencode + cursor）才能执行
- 每轮测试结果写回 `ITERATIONS.md`
- 达标（>50%）后须在 `ISSUES.md` 关闭 GUA-022
