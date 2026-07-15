```markdown
---
type: entity-module
title: "BC 训练器（bc_trainer.py）"
sources:
  - docs/guandan-brain/ITERATIONS.md
tags:
  - module
  - bc
  - training
status: current
related_gua:
  - GUA-064
date: 2026-07-15
---

# BC 训练器

## 文件
- `bc_trainer.py`
- `bc_dataset.py`
- `train_bc_v7.py`

## 职责
**行为克隆（Behavior Cloning）训练管线**：
- 从人类/规则对局数据学习
- 输出 `bc_model_v2` / `bc_model_v3.pth`
- 保存到 `models/v-nn/`

## 状态
**BC 路线已死**（GUA-064）：
- 2048 维输出仅用 2 维（argmax collapse）
- 5 次批跑 0/12 一致
- 需转向 GUA-039b 自对弈（RL）

## 关联
- [[bc-argmax-collapse]] — 核心失败原因
- [[gua-064]] — argmax collapse GUA
```

---
