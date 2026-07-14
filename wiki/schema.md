# Wiki Schema

## 页面类型

| 类型 | 目录 | 说明 | 命名规则 | 示例 |
|------|------|------|----------|------|
| `source-summary` | `wiki/sources/` | 原始资料的结构化摘要 | `{原始文件名}-summary.md` | `ISSUES-summary.md` |
| `entity-gua` | `wiki/entities/` | GUA 缺陷条目 | `gua-{编号}.md` | `gua-061.md` |
| `entity-engine` | `wiki/entities/` | 引擎版本 | `engine-{名称}.md` | `engine-m3.md` |
| `entity-module` | `wiki/entities/` | 代码模块 | `module-{名称}.md` | `module-batch-executor.md` |
| `concept` | `wiki/concepts/` | 概念/方法论 | `{概念名}.md` | `batch-evaluation.md` |
| `query-answer` | `wiki/queries/` | 保存的查询回答 | `query-{日期}-{主题}.md` | `query-0617-v7-status.md` |
| `synthesis` | `wiki/synthesis/` | 跨资料综合分析 | `synthesis-{主题}.md` | `synthesis-v7-current-state.md` |
| `meta` | `wiki/` 根 | 元数据/索引 | `index.md`, `log.md`, `overview.md` | — |

## Frontmatter 必填字段

```yaml
---
type: concept              # 页面类型
title: "批跑评测体系"       # 页面标题
sources:                   # 贡献此页面的原始资料
  - docs/guandan-brain/EVAL.md
  - docs/guandan-brain/LOCAL_EVAL_CHECKLIST.md
tags:                      # 分类标签
  - evaluation
  - batch
  - kpi
status: current            # current | outdated | draft
related_gua:               # 关联的 GUA 编号
  - GUA-033
date: 2026-06-17           # 最后更新日期
---
```

## 命名约定

- 文件名：英文小写 + 连字符（`batch-evaluation.md`）
- 标题：中文描述（`# 批跑评测体系`）
- Wikilink：`页面文件名`（无扩展名）
- GUA 引用：`GUA-061`（全文一致）

## 工作流

### 摄入（Ingest）
1. 读取 `raw/` 下新文件或变更文件（SHA256 增量检测）
2. 第一步（分析）：提取关键实体、概念、与现有 Wiki 的关联
3. 第二步（生成）：创建/更新 Wiki 页面、交叉引用、更新 index/log/overview
4. 记录日志到 `wiki/log.md`

### 查询（Query）
1. 接收用户问题
2. 搜索 wiki/ 目录（标题匹配 + 全文搜索）
3. 图谱扩展（通过 wikilink 和 sources[] 发现关联页面）
4. LLM 综合回答

### 健康检查（Lint）
1. 断链检测（wikilink 指向不存在的页面）
2. 孤立页面（入链 ≤ 1）
3. 过时页面（frontmatter status != current）
4. 来源一致性（sources[] 文件是否存在）

## 目录结构

```
wiki/
├── purpose.md              # Wiki 目标与方向
├── schema.md               # 本文件
├── raw/                    # 原始资料（不可变，可含符号链接）
│   ├── guandan-brain/      # → docs/guandan-brain/
│   └── analysis/           # → docs/analysis/
├── wiki/
│   ├── index.md            # 内容目录（Map of Content）
│   ├── log.md              # 操作日志（时序、可解析）
│   ├── overview.md         # 全局概要（每次摄入后自动更新）
│   ├── sources/            # 资料摘要页
│   ├── entities/           # 实体页
│   ├── concepts/           # 概念页
│   ├── queries/            # 查询回答
│   └── synthesis/          # 综合分析
└── .wiki/                  # 配置与缓存
    ├── config.json          # LLM 配置
    ├── source_manifest.json # 源文件哈希表
    └── cache/               # 摄入缓存
```
