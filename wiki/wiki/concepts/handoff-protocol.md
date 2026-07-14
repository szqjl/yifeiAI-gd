---
type: concept
title: "Handoff 接续协议"
sources:
  - docs/governance/分析接续-handoff.md
  - docs/guandan-brain/handoff/
tags:
  - handoff
  - collaboration
  - protocol
status: current
related_gua: []
date: 2026-06-18
---

# Handoff 接续协议

## 概念定义

**Handoff 协议**是双上计分王项目中跨设备/跨 Agent 协作的**上下文传递规范**。当一次会话无法在单轮内完成，或需要交接给另一台机器/另一个 Agent 时，通过结构化文档传递最小可用上下文。

## 适用场景

1. **跨设备开发** — 笔记本与台式机交替使用
2. **跨 Agent 协作** — Claude Code / Cursor / 人工 之间轮换
3. **长周期中断恢复** — 数天乃至数周后的任务续推

## 文档结构

存放路径：**`docs/guandan-brain/handoff/YYYY-MM-DD-主题.md`**

5 段必备结构：

| 段落 | 作用 | 字数建议 |
|------|------|----------|
| 背景 | 当前在做什么、为何做 | 100-200 字 |
| 已完成 | 已确认落地的成果（带 commit/文档链接） | 列表 |
| 未完成 | 尚未推进、阻塞原因 | 列表 |
| 关键结论 | 已成定论的判断（避免重新论证） | 3-5 条 |
| 下一步唯一动作 | 接手者**只做这一件事** | 1 句 |

## 5 分钟原则

接手者从打开 handoff 文档到开始执行，**应控制在 5 分钟内**：

1. 读完 5 段（2 分钟）
2. 跳到「下一步唯一动作」（1 分钟）
3. 验证环境/前置条件（2 分钟）
4. 开始执行

## 数据分层

handoff 文档中**不存**大文件本体，只存**引用**：

- **Git** = 文本/结论/图表/小文件（< 1 MB）
- **COS（云存储）** = 大文件/replay/模型
- **聊天窗口** = **不存任何资料**

## 反模式

- ❌ 「背景」段写成项目历史综述
- ❌ 「下一步」写多个并列任务（应只写**唯一动作**）
- ❌ 把 handoff 写成 README（应聚焦于「断点」）
- ❌ handoff 文档超 2000 字（信息密度过低）

## 关联页面

- [[分析接续-handoff-summary]] — 来源摘要
- [[artifact-storage-strategy]] — COS/Git 分层
- [[模型文件管理方案-summary]] — 云存储实现细节
- [[document-governance]] — 文档治理
