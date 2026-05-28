# 版本与分支状态矩阵

> 治理总纲：[docs/governance/M-V-Series-治理方案.md](../governance/M-V-Series-治理方案.md)

**维护说明**：里程碑或冒烟开关变化时更新本表；`最后更新` 使用系统当前日期。

| 字段 | 值 |
|------|-----|
| 最后更新 | 2026-05-28 |
| 默认开发分支 | `m1-dev` |
| canonical 远程 | Gitee `origin` |
| V-default-smoke | **OFF** |

---

## 1. 系列总览

| 系列 | 子路径 | 代号 | 状态 | 默认用于比赛 | 备注 |
|------|--------|------|------|----------------|------|
| **M** | — | m1 | **Production** | 是 | 对 lalala 主迭代，尚无稳定胜率 |
| **M** | — | m2 | Integration | 否 | 工程化、批跑、offline_platform |
| **M** | — | m3 | Planned | 否 | 契约 `IDecisionProvider` 待冻结 |
| **V-learn** | 自学 | v4 | Archive | 否 | 适配/验证 |
| **V-learn** | 自学 | v5 | Standby | 否 | V 冒烟 OFF 前不阻塞 M PR |
| **V-learn** | 自学 | v6 | Archive | 否 | 分支 `v6-dev`，MOE 实验 |
| **V-nn** | 神经网络 | v7 | Experiment | 否 | 分支 `v7-dev` |

---

## 2. Git 分支映射

| 分支 | 系列 | 跟踪远程 | 角色 |
|------|------|----------|------|
| `m1-dev` | M | `origin/m1-dev` | **主开发 / 集成** |
| `v7-dev` | V-nn | `origin/v7-dev` | v7 实验 |
| `v6-dev` | V-learn | `origin/v6-dev` | 归档，默认不合并 |
| `main` | 发布 | `origin/main` | 稳定快照 |
| `github/*` | 镜像 | — | **暂不维护**（2026-05-28） |

---

## 3. 客户端与决策入口（速查）

| 场景 | 分支 | 客户端 | 决策核心 |
|------|------|--------|----------|
| **当前：M × lalala** | `m1-dev` | `yf1_m1.py`, `yf2_m1.py` | M 硬编码策略 + lalala 适配 |
| V-learn 实验 | `m1-dev` / 特性分支 | `yf1_v5.py`, `yf2_v5.py` | `hybrid_decision_engine_v5` 等 |
| V-nn 实验 | `v7-dev` | `yf1_v7.py`, `yf2_v7.py` | `ultimate_win_rate_engine_v7.py` |
| 历史 | 本地旧 `main` | v4/v5/stage* | 仅查阅，不扩展 |

---

## 4. 质量门禁状态

### 4.1 回归集

| 项 | 值 |
|----|-----|
| 名称 | `regression-lalala-v1` |
| 局数 | **30** |
| Manifest | `data/manifests/regression-lalala-v1.json` |
| 对象存储路径 | `YiFeiAI-GD-artifacts/replays/regression-lalala-v1/` |

### 4.2 V 默认冒烟

| 项 | 值 |
|----|-----|
| 当前 | **OFF** |
| 启用条件 A | lalala 近 **50** 局胜率 **≥ 40%** |
| 启用条件 B | m3 契约冻结 + M 冒烟 **7** 天绿 |
| 启用日期 | — |
| ON 后默认 V 薄冒烟 | v5（待定，启用时在此填写） |

### 4.3 改 M → `m1-dev` PR（当前）

- M 冒烟（§ 治理方案 7.3）
- 30 局 replay diff（行为变更时）
- **不**要求 v5 通过

---

## 5. Artifacts 存储

| 类型 | 位置 | 进 Git |
|------|------|--------|
| 代码 | 仓库 | 是 |
| Manifest | `data/manifests/` | 是 |
| 全部 Artifact（replay / 模型 / eval） | **腾讯云 COS**（唯一网盘） | 否（仅 manifest + 本地 `data/artifacts/` 镜像） |

---

## 6. 修订日志

| 日期 | 变更 |
|------|------|
| 2026-05-28 | 初版：V-smoke OFF；m1-dev 为默认；30 局回归 |
