# 评测场景（可选）

每局一个文件：`yaml` / `json` / 简记 `md` 均可。建议至少包含：

- 局面：手牌、当前墩、轮到你时的合法动作集（若可推导则写推导前提）。
- 期望：允许的动作集合、或禁止动作、或「队友应判定为 X」。

命名示例：`GUA-001_min_repro.yaml`。

已落地的金样例文件：

- `client_sets.json`：M1/V4/V5/V6 四条客户端路径（与 `batch_executor_gui.py` 中注释一致）。
- `GUA-001_diagnose_only.md`：仅诊断、不对局。
- `GUA-002_client_paths_golden.md`：路径金样例说明（与 JSON 对照）。
- `M1_yf1_vs_yf2_comparison.md`：M1 双客户端对照步骤；**§6 已测结果**（10 个 `game_id`、PASS 率等，**GUA-020 closed**）。
