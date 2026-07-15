---
type: concept
title: "Agent Bootstrap 工作流"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/AGENT_FIRST_MESSAGE.md
  - docs/guandan-brain/AGENT_PUSH_CHECKLIST.md
tags:
  - agent
  - workflow
  - bootstrap
  - wf-01..wf-12
status: current
related_gua:
  - GUA-033
date: 2026-07-15
---

# Agent Bootstrap 工作流

## 定义

Agent 从进入项目到完成交付的完整生命周期，由三份核心文档构成：

| 文档 | 角色 |
|------|------|
| [[AGENT_BOOTSTRAP]] | 工作流真源（WF-01 ~ WF-12） |
| [[AGENT_FIRST_MESSAGE]] | 首条消息模板 |
| [[AGENT_PUSH_CHECKLIST]] | 推送前自检清单 |

⚠️ 当三份文档内容重复时，以 [[AGENT_FIRST_MESSAGE]] 为真源。

## 工作流阶段

### WF-01 ~ WF-03：启动与上下文加载

- 读取 [[AGENT_BOOTSTRAP]] 全部章节
- 确认当前引擎版本（[[engine-m3]] 或 [[engine-v7]]）
- 加载 [[AGENT_FIRST_MESSAGE]] 模板

### WF-04 ~ WF-06：任务理解与 GUA 关联

- 解析任务描述，匹配 [[ISSUES]] 中的 GUA 编号
- 标记新发现的 GUA（缺陷、迭代、决策）
- 检查 [[gua-033]] 等已定音 GUA 是否被任务违反

### WF-07 ~ WF-09：执行与验证

- 修改代码
- 跑单元测试
- 跑小规模批跑（见 [[batch-evaluation]]）

### WF-10 ~ WF-12：交付与复核

- 提交 commit
- 跑完整批跑验证 KPI
- 用 [[AGENT_PUSH_CHECKLIST]] 自检
- 推送 PR

## V7 执行卡片闭环

V7 NN 引擎特有的闭环流程：

```
replay → WF-12 → 准入审查 → 修复 → 批跑 → 复核
```

详见 [[engine-v7]]。

## LLM Wiki 集成

工作流中嵌入 LLM Wiki 工具链：

```bash
python scripts/wiki.py init      # 初始化
python scripts/wiki.py ingest    # 摄入新文件
python scripts/wiki.py query     # 查询
python scripts/wiki.py lint      # 健康检查
```

目前已摄入 107 个源文件（见 [[overview]]）。

## 关键检查点

1. **[[gua-033]] 定音**：所有胜利数解读必须区分"局"和"副"
2. **数据目录分离**：M3 用 `game_records`，V7 用 `game_records_v7`
3. **`--target-games` 须为 3 的倍数**：见 [[batch-evaluation]]
4. **共用层修改需同步 M 和 V 两条线**
```

## 更新页面
