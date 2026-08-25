# external/ 第三方依赖

本目录存放 V9 DMC / 对照实验用的上游源码。**代码入 Git**；**权重与编译二进制不入 Git**（`pre_push` 禁止 >1MB，见根 `.gitignore`）。

| 目录 | 用途 | 权重 / 二进制 |
|------|------|----------------|
| `FableDan/` | fd_native DMC 仿真（已 vendored） | 训练自产 `.npz`，见 `scripts/launchers/botzone_v9/` |
| `DanLM_src/` | DanLM 掼蛋大模型（Botzone #1 对照） | 见下方 DanLM |
| `Danzero_plus/` | DanZero+ 官方 RL 框架（v7dan 对照） | 见下方 DanZero+ |

## DanLM_src

- 上游：<https://github.com/dashidhy/DanLM>
- 本地路径：`external/DanLM_src/`
- **权重**（需自行放入，已 gitignore）：
  - `ckpts/DanLM_v1/dansformer_v1_best_eval.pt`
  - `ckpts/DanZero_v3_rep_v1t/best_eval_001.pt`
  - 及同目录下 `.onnx`（可选 int8）
- 评估示例见 `DanLM_src/README.md` 的 `evaluate.py` 小节。

## Danzero_plus

- 上游：<https://github.com/submit-paper/Danzero_plus>
- 本地路径：`external/Danzero_plus/`
- **DMC Q-net 权重**（需自行放入，已 gitignore）：
  - `wintest/danzero/q_network.ckpt`（与官方 wintest 一致，SHA-256 见 `offline_platform/danzero_plus/README.md`）
  - 或 `actor_torch/q_network.ckpt`
- **编译二进制**（已 gitignore，从上游构建或拷贝）：
  - `actor_n/guandan`、`actor_torch/danserver`、`wintest/torch/danserver`

## 克隆后一键检查

```powershell
# 应存在源码、无强制权重（推理前需补 ckpt）
Test-Path external/FableDan/fabledan/engine.py
Test-Path external/DanLM_src/README.md
Test-Path external/Danzero_plus/README.md
```
