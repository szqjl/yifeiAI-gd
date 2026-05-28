# 分析 / 训练中途换机 — 接续说明（Handoff）

> 换电脑或新开 Agent 时，**先读本文 + 最新 handoff 文件**，再动手。

## 1. 问题

- 分析训练数据到一半，或刚结束但未写入仓库 → 新机器上的 Agent **不知道**上一台上的结论、假设、下一步。
- COS 解决 **文件**；Git + handoff 解决 **上下文**。

## 2. 换机前 5 分钟清单（旧电脑）

在离开前尽量做完；做不完也要写进 handoff「未完成项」。

- [ ] **Git**：提交并 push 代码 + `docs/analysis/handoffs/最新-*.md`
- [ ] **结论落盘**：不要把关键结论只留在聊天里；写入 handoff 或 `docs/training/` / `docs/analysis/`
- [ ] **COS**（若有大文件）：上传本阶段用到的 replay / eval JSON / 当前 `.pth`；记下 `object_key`
- [ ] **新建 handoff**：复制 [handoff 模板](#4-handoff-模板) 到 `docs/analysis/handoffs/YYYY-MM-DD-简短主题.md`
- [ ] **可选**：`git log -3 --oneline` 贴进 handoff 的「相关 commit」

## 3. 新电脑 / 新 Agent 怎么继续

1. `git pull`（`m1-dev`）
2. 打开 `docs/analysis/handoffs/` 下**日期最新**的一篇
3. 读 handoff 里的 **「下一步唯一动作」**（只写一条主任务，避免 Agent 发散）
4. 若 handoff 写了 COS 路径：`python scripts/cos/sync_pull_all.py` 或按路径单独拉
5. 对新 Agent 的第一条消息可写：

   ```text
   请先读 docs/governance/分析接续-handoff.md 和
   docs/analysis/handoffs/<文件名>，按其中「下一步」继续，不要从零重做已完成步骤。
   ```

## 4. Handoff 模板

新建文件：`docs/analysis/handoffs/YYYY-MM-DD-主题.md`

```markdown
# Handoff: <主题>

| 字段 | 内容 |
|------|------|
| 日期 | YYYY-MM-DD |
| 分支 | m1-dev @ <commit 短 hash> |
| 状态 | 进行中 / 已结论待验证 / 已结案 |
| 负责人 | （可选） |

## 背景（2～3 句）
要回答什么问题？例如：lalala 某类败局是否与拆炸弹有关。

## 已完成
- [x] 步骤 1 …（输出文件路径）
- [x] 步骤 2 …

## 未完成 / 进行中
- [ ] 步骤 3 …（卡在哪里、已试什么）

## 关键结论（有据）
- 结论 1 → 依据：`training_logs/xxx.json` 或 replay `reg-00x`
- 假设（待证）：…

## 数据与产物位置
| 类型 | 路径 |
|------|------|
| 本地 | `training_logs/...` |
| COS | `replays/incidents/...`（bucket key） |
| Git | `docs/training/...` |

## 下一步唯一动作
（只写一条，例如：对 handoff 中列出的 5 局 replay 跑 offline diff，输出到 `docs/analysis/xxx.md`）

## 不要重做
- 已确认无用的方向：…
```

## 5. 什么放 Git、什么放 COS

| 内容 | 存放 | 原因 |
|------|------|------|
| handoff、分析结论、图表说明 | **Git** | Agent 和队友能直接读 |
| 原始大日志、全量 replay、模型 | **COS** | 体积大 |
| 聊天窗口 | **不存** | 换机即丢失 |

## 6. 分析「到一半」的典型接续

| 阶段 | 旧电脑留下 | 新电脑先做 |
|------|------------|------------|
| 扫日志 halfway | handoff 写「已扫文件列表 + 当前统计表路径」 | 从下一文件继续扫 |
| 脚本跑了一半 | 提交脚本 + handoff 写命令与输出目录 | 同一命令加 `--resume` 或跳过已完成输出 |
| 结论已出未写 PR | handoff 写结论 + 建议改哪些文件 | 按结论改代码 → regression |

## 7. 相关文档

- [COS-接入指南.md](./COS-接入指南.md) — 文件同步
- [M-V-Series-治理方案.md](./M-V-Series-治理方案.md) — 分支与回归 30 局
