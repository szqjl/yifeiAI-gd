---
type: concept
title: "V7 Guard 规则全集 (R01-R15)"
sources:
  - docs/guandan-brain/ITERATIONS.md
  - docs/guandan-brain/组牌-NN衔接设计-软引导vs硬约束.md
tags:
  - v7
  - guard
  - rules
  - R01-R15
status: current
related_gua:
  - GUA-031
  - GUA-065
  - GUA-066
  - GUA-068
  - GUA-069
  - GUA-070
date: 2026-06-20
---

# V7 Guard 规则全集 (R01-R15)

V7 三层管线 Layer 1 的 **15 条硬排除规则**，详见 wiki/concepts/three-layer-pipeline.md。

## 规则清单

| ID | 名称 | 主题 | GUA | 状态 |
|----|------|------|-----|------|
| R01 | _rule_r01_* | （基础规则 1） | — | closed |
| R02 | _rule_r02_* | （基础规则 2） | — | closed |
| ... | ... | ... | ... | ... |
| R07 | 队友让道 | 队友保护 | GUA-065 | closed |
| R08 | 送小单 | 队友喂牌 | GUA-065 | closed |
| R09 | 送对 | 队友喂牌 | GUA-065 | closed |
| **R10** | **领出不炸** | 炸弹慎出 | **GUA-066** | closed |
| **R11** | **全局抑制牌节流** | unbeatable_card_throttle | **GUA-068**
