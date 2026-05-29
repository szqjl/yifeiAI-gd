# main 与 origin/main 分支策略（已拍板）

| 字段 | 值 |
|------|-----|
| 拍板日期 | 2026-05-29 |
| 依据 | [M-V-Series-治理方案.md](./M-V-Series-治理方案.md) §4 |
| 状态 | **生效** |

---

## 1. 现状（拍板时）

| 分支 | 提交 | 说明 |
|------|------|------|
| `origin/main` | `e767f28` | 治理前稳定线；含早期 M/V 混合与训练历史 |
| `origin/m-dev` | `b2ae187`（及之后） | **主开发线**，领先 `main` **435** 个 commit |
| Gitee 默认分支 | **`m-dev`** | `git remote show origin` → `HEAD branch: m-dev` |
| 分叉方向 | `main..m-dev` 仅前进 | `m-dev..main` 为 **0**（main 无独有提交） |

---

## 2. 拍板结论

### 2.1 角色分工

| 分支 | 角色 | 日常开发 | push 目标 |
|------|------|----------|-----------|
| **`m-dev`** | M 系列主集成线 | **是** | `origin/m-dev` |
| **`origin/main`** | 发布 / 稳定快照 | **否** | 仅里程碑合并时更新 |
| **本地 `main`** | 跟踪 `origin/main` | **否** | 禁止直接提交功能代码 |

### 2.2 origin/main 冻结策略（当前阶段）

- **`origin/main` 保持 `e767f28`，不在未达里程碑前 fast-forward 或 force-push。**
- 理由：当前 M × lalala 尚无稳定胜率，治理与脚本收敛均在 `m-dev`；过早更新 `main` 会混淆「可发布快照」与「实验集成线」。
- 治理前 `main` 线已通过 tag **`archive/main-pre-governance-20260528`** 永久标记，供历史查阅与 diff 基线。

### 2.3 何时允许 m-dev → main

满足 **全部** 条件方可发起合并 PR（目标分支 `main`）：

1. **M 冒烟套件**（治理方案 §7.3）通过；
2. **30 局 regression** diff 无 crash、报告可生成（行为相关变更时）；
3. **团队发布决议**（Issue/群聊/ITERATIONS 一行记录里程碑名与日期）；
4. **未引入大文件**进 Git（Layer 2 仍走 COS）。

合并方式：**merge commit**（保留 `m-dev` 历史），**禁止**对 `main` 做 `--force` 除非灾难恢复且团队书面同意。

### 2.4 本地 main 使用规范

```bash
# 克隆后默认已在 m-dev（Gitee 默认分支）
git checkout m-dev && git pull origin m-dev

# 仅需对比治理前快照时
git checkout main && git pull origin main   # 应停在 e767f28 + tag
git checkout m-dev

# 禁止
git checkout main && git commit ...           # ✗ 日常开发
git push origin main                          # ✗ 未经里程碑 PR
```

### 2.5 与「本地旧 main」表述的关系

治理方案 §4.2 中「本地旧 main」指 **tag 锚点 `archive/main-pre-governance-20260528` 所标记的快照**，与当前 **`origin/main` 指向同一 commit**。二者不是两条分叉线；**拍板后统一口径**：

- **历史线** = `e767f28` = tag `archive/main-pre-governance-20260528` = 当前 `origin/main`；
- **活跃线** = `m-dev`。

---

## 3. 操作清单（已执行 / 待 PR 合并）

- [x] 本文档写入 `docs/governance/main-branch-policy.md`
- [x] 更新 `docs/versions/MATRIX.md` §2
- [x] 更新 handoff「main 策略」为已结案
- [x] 本地创建 tag `archive/main-pre-governance-20260528` → `e767f28`
- [x] `git push origin archive/main-pre-governance-20260528`（2026-05-29 已推送 Gitee）
- [ ] 里程碑到达后：按 §2.3 合并 `m-dev` → `main`

---

## 4. 相关文档

| 文档 | 说明 |
|------|------|
| [M-V-Series-治理方案.md](./M-V-Series-治理方案.md) | 总纲 §4 分支治理 |
| [docs/versions/MATRIX.md](../versions/MATRIX.md) | 分支状态矩阵 |
| [分析接续-handoff.md](./分析接续-handoff.md) | 换机接续 |
| [GIT_SETUP_GUIDE.md](../governance/git-setup-guide.md) | 旧版 Git 指南（**分支策略以本文与治理方案为准**） |
