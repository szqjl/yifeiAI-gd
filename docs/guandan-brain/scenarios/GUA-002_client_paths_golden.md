# GUA-002 — 各版本四条客户端路径（金样例引用）

## 目的

对 M1 / V4 / V5 / V6 使用**同一套** lalala 对手位（client3/client4），仅替换 YiFei 侧 `yf1_*` / `yf2_*`。自动化与人工核对时以本文件与.machine-readable 的 `client_sets.json` 为准。

## 引用

见同目录 `client_sets.json` 中键 `m1`、`v4`、`v5`、`v6`。

## 期望（可自动化断言）

- 上述 JSON 中列出的每个 `src/communication/*.py`，在**当前检出分支**下均应存在；若某版本脚本尚未合并到本分支，对应键可跳过（例如 V6：`yf1_v6.py` / `yf2_v6.py` 常见于 `v6-dev`，主干可能暂无文件）。
- 坐位语义：索引 0、2 为 YiFei 队；1、3 为 lalala 队（与 `batch_executor_gui.py` 注释一致）。
