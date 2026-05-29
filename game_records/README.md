# 对局记录（本地）

本目录存放批跑 / 客户端产出的 JSON 对局记录（**不进 Git 大文件**，仅保留本说明）。

## 约定

- 新对局由 batch_executor 或 src/communication/yf*_m1.py 等写入此目录。
- 历史样本已分析完毕（见 docs/guandan-brain/ITERATIONS.md GUA-020/021 等）；**2026-05-29 已清空本地旧记录**。
- 改决策逻辑后的回归：重新跑局生成新 game_id，勿与已删旧文件混统计。

## 评测口径

成对 yf1_m1 + yf2_m1 同 game_id 计 1 局；详见 docs/guandan-brain/EVAL.md、LOCAL_EVAL_CHECKLIST.md。
