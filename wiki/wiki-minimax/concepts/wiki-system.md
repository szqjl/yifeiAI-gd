---
type: concept
title: "LLM Wiki 知识图谱系统"
sources:
  - docs/guandan-brain/AGENT_BOOTSTRAP.md
  - docs/guandan-brain/COMMANDER_NOTES.md
tags:
  - wiki
  - knowledge-graph
  - tool
  - llm
status: current
related_gua: []
date: 2026-06-17
---

# LLM Wiki 知识图谱系统

## 定义
v7.2 引入的 **LLM 驱动的持久化知识图谱系统**，用于沉淀项目知识、避免 Agent 重复劳动。

## 工具入口
`scripts/wiki.py` 提供 4 个子命令：

| 子命令 | 用途 |
|--------|------|
| `init` | 初始化 Wiki 目录结构 |
| `ingest` | 摄入新文件（SHA256 增量检测） |
| `query <主题>` | 查询主题（语义搜索 + 图谱扩展） |
| `lint` | 健康检查（断链、孤立、过时） |

## 目录结构
```
wiki/
├── purpose.md          # Wiki 目标
├── schema.md           # 页面类型与 frontmatter 规范
├── raw/                # 原始资料（符号链接 → docs/）
├── wiki/
│   ├── index.md        # 内容目录 (MOC)
│   ├── log.md          # 操作日志
│   ├── overview.md     # 全局概要
│   ├── sources/        # 资料摘要
│   ├── entities/       # 实体页 (GUA/Engine/Module)
│   ├── concepts/       # 概念页
│   ├── queries/        # 查询回答
│   └── synthesis/      # 综合分析
└── .wiki/              # 配置与缓存
    ├── config.json
    ├── source_manifest.json
    └── cache/
```

## 页面类型
- `source-summary`：原始资料摘要（`wiki/sources/`）
- `entity-gua`：GUA 缺陷条目（`wiki/entities/gua-xxx.md`）
- `entity-engine`：引擎版本（`wiki/entities/engine-xxx.md`）
- `entity-module`：代码模块（`wiki/entities/module-xxx.md`）
- `concept`：概念/方法论（`wiki/concepts/`）
- `query-answer`：查询回答（`wiki/queries/`）
- `synthesis`：综合分析（`wiki/synthesis/`）

## 工作流

### 摄入（Ingest）
1. SHA256 增量检测新文件
2. 第一步分析：提取实体、概念、关联
3. 第二步生成：创建/更新页面
4. 更新 `index.md` / `log.md` / `overview.md`

### 查询（Query）
1. 标题匹配 + 全文搜索
2. 通过 wikilink 和 `sources[]` 图谱扩展
3. LLM 综合回答

### 健康检查（Lint）
- 断链检测
- 孤立页面（入链 ≤ 1）
- 过时页面（`status != current`）
- 来源一致性

## 命名约定
- 文件名：英文小写 + 连字符（`agent-bootstrap-workflow.md`）
- 标题：中文描述（`# Agent Bootstrap 工作流`）
- Wikilink：`页面文件名`（无扩展名）
- GUA 引用：`GUA-XXX`（全文一致）

## 关联页面
- [[agent-bootstrap-workflow]] — Wiki query 是 5 步读法第 1 步
- [[v7-current-state]] — V7 综合状态
