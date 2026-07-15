```markdown
---
type: meta
title: "Wiki 目标与方向"
sources:
  - docs/guandan-brain/v8-win-rate-history.md
  - docs/guandan-brain/ITERATIONS.md
tags:
  - meta
  - purpose
status: current
date: 2026-07-15
---

# Wiki 目标与方向（2026-07-15 更新）

## 调整说明
原 Wiki 目标中"V7 是未来方向 / M3 已达瓶颈"的表述已**部分过时**。当前实际状态：

- **V7**：NN 引擎主迭代，但 BC 路线已死（GUA-064），转向 GUA-039b 自对弈
- **V8**：新平台 OpenGuanDan 迁移，与 V7 并行进行（GUA-143~148）
- **M3**：规则引擎已 frozen，但其逻辑被 V7 借鉴（如 GUA-065 队友识别）

## 当前主迭代双线

| 线路 | 定位 | 状态 |
|------|------|------|
| V7+ | NN 引擎迭代（BC→RL 转型） | GUA-039b 自对弈待实施 |
| V8 | OpenGuanDan 平台迁移 | 7 个迁移 GUA 进行中 |

## 关键问题（更新版）

1. V7 引擎 BC 路线已死，下一步 GUA-039b 自对弈如何启动？
2. V8 平台迁移何时能完成基线（30 局 ≥ 30%）？
3. GUA-064 argmax collapse 是否需要彻底放弃 BC 路线？
4. M3→V7 知识传承路径如何文档化？
5. 副胜率方差问题（≥9 局门槛）如何标准化？

## 演进中的论点（更新版）

1. ~~V7 是未来方向~~ → **V7+ 和 V8 并行，V7 是 NN 引擎迭代，V8 是平台迁移**
2. **批跑是唯一真源**：所有策略改动必须经过离线批跑验证
3. **GUA 编号体系是脊柱**：所有缺陷、迭代、分析都挂在 GUA 上
4. **局 ≠ 副**：数据解读的核心口径问题
5. **V 系列治理补课**：避免 V4-V5 覆辙，所有评估必须留痕
```

---
