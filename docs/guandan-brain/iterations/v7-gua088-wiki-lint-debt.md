# GUA-088 · wiki · lint 健康债务登记

> **状态**：open 🟡 (登记 2026-06-29)
> **严重级别**：P3 observation（**不影响主线**——只 wiki 索引质量）
> **标签**：wiki, lint, observation
> **触发**：python scripts/wiki.py lint 输出健康债务

---

## 1. 现象（2026-06-29 净盘后跑 lint）

`
总计: 断链 47 | 孤立 216 | 格式 0 | 来源 239
`

- **格式 0** ✅ 干净（YAML frontmatter 全部合规）
- **断链 47** 🟡 [[link]] 引用但 wiki 无对应页
- **孤立 216** 🟢 页存在但入链 = 0（预期内：source-summary/concept 新页未 enrich）
- **来源 239** 🔴 frontmatter sources: 字段引用的相对路径解析失败

**与 GUA-086/087 无关**——本批 ingest 收 4 页正常，问题是历史 ingest 累积。

---

## 2. 47 断链分类

| 类别 | 数量 | 性质 | 处理 |
|------|------|------|------|
| GUA 实体页缺失 ([[gua-NNN]] / [[GUA-067]]) | ~25 | 期望指向 ntities/gua-NNN.md 但未建 | 增量 ingest 触发 LLM 建 |
| 模块页缺失 | 4 | module-endgame-preprocessor / module-heuristic-select / module-v7-guard-pipeline / yf1_m3 | 增量 ingest |
| 工作流页缺失 | 2 | wf-04-batch-kpi / wf-10-guard-rule | 标签可补 |
| 设计/方法论页缺失 | ~10 | nd-position-design-summary / 	hree-engine-tdd-pipeline / 
o-pseudo-closure / 批跑评测体系 / PB-001-gua072-bomb-break-timing | 增量 ingest |
| source-summary 缺失 | 2 | source-summary:v7-win-rate-history-summary / source-summary:workflow-summary | 路径解析错 |
| 占位/语法错 | 3 | [[4][6]] / [[gua-062] 残局豁免口径 [5]] | 改源 |
| v7-current-state 锚点 | 3 | [[v7-current-state#T1]] / T2 / T3 | 加标题 |
| gua-080/084 复合键 | ~5 | [[gua-080\|组牌冻结]] / [[gua-084\|R-G084-1]] | 拆链或建子页 |

---

## 3. 216 孤立的本质

**孤立 = 缺入链**。两种成因：
1. **新生成未 enrich**：ingest 给 source/concept 页，但 synthesis 阶段没加 cross-link
2. **anchor-only 页**：如 concept-*.md 是定义性页面，本来就不被 inline 引用

**结论**：216 多数是 (1)——synthesis/ 24 页 + concepts/ 150 页 + 其它。**可作为 wiki 后续 enrich 阶段任务**。

---

## 4. 239 来源缺失初步分析

怀疑点：frontmatter sources: 字段写的是 iterations/xxx.md（相对路径），但 lint 解析时按 wiki/ 根目录解析，找 iterations/ 当然不存在。

**验证方法**：跑 lint 时输出 ''{rel}: 引用 {src} 不存在''，看 src 的具体形式。

**修复候选**：
- 选项 A：把 sources: 改成 ../docs/guandan-brain/iterations/xxx.md 绝对相对
- 选项 B：让 wiki.py 解析时支持相对 RAW_SOURCES 根
- 选项 C：直接看 5 条样例判定是不是误报

---

## 5. 完成定义（待定）

- [ ] 跑 wiki.py lint 抽 5 条断链 + 5 条来源缺失**具体**记录
- [ ] 判断 47 断链是否需要手工建页，还是 LLM 增量 ingest 自动建
- [ ] 判断 239 来源是不是误报（路径解析 bug）
- [ ] 修后 wiki.py lint 输出：断链 < 10 / 孤立 < 50 / 来源 < 5
- [ ] 不必追求 0/0/0（wiki 永远有自然漂移）

---

## 6. 关联

- **GUA-086/087**：本次 ingest 正常收录 4 页，无断链
- **docs/analysis/archive/**：本批 ingest 22 源后 archive 也已收录
- 后续：增量 ingest + 手工补链是双轨
