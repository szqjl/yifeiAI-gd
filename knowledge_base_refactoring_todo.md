# 知识库重构方案 TODO

## 🎯 目标
将现有的文本知识库转化为AI可理解、可执行的结构化数据，实现"知识增强"决策。

## 📊 现状分析
- **现有知识库**: 主要是Markdown文本，AI无法直接使用。
- **现有代码**: `lalala` 策略硬编码在代码中，缺乏灵活性。
- **目标架构**: V4混合决策引擎 (Layer 1: lalala, Layer 2: DecisionEngine, Layer 3: KnowledgeEnhanced)。

## 🛠️ 重构方案

### 阶段 1: 知识库结构化 (Formatting)
将现有文档转换为标准格式，便于程序解析。

- [ ] **F1. 建立目录结构**
  - `docs/knowledge/rules/` (规则)
  - `docs/knowledge/strategy/` (策略)
  - `docs/knowledge/skills/` (技巧)
- [ ] **F2. 格式化规则文档**
  - 转换 `江苏掼蛋规则.md` 等为标准Markdown (含YAML头)。
  - 统一术语 (Single, Pair, Bomb 等)。
- [ ] **F3. 格式化技巧文档**
  - 转换 `掼蛋技巧秘籍.md` 为独立的技巧文件。
  - 添加标签 (tags) 和 适用阶段 (game_phase)。

### 阶段 2: 知识检索引擎 (Retriever)
实现 `KnowledgeRetriever` 类，用于加载和检索知识。

- [ ] **R1. 实现 Markdown 解析器**
  - 解析 YAML 元数据 (title, tags, priority)。
  - 解析正文内容。
- [ ] **R2. 实现 知识索引**
  - 基于 tags 和 game_phase 建立索引。
  - 实现 `query(context)` 方法，根据当前游戏状态检索相关知识。
- [ ] **R3. 实现 缓存机制**
  - 避免重复解析文件。

### 阶段 3: 知识应用层 (Application)
在 `KnowledgeEnhancedDecision` (Layer 3) 中应用检索到的知识。

- [ ] **A1. 规则转化 (Rule Translation)**
  - **关键任务**: 将文本规则转化为代码逻辑。
  - 示例: "队友剩牌少于5张" -> `if teammate_cards <= 5: ...`
  - 实现 `KnowledgeTranslator` 类或在 `KnowledgeEnhancedDecision` 中硬编码常用规则的解析逻辑。
- [ ] **A2. 评分增强 (Score Boosting)**
  - 根据检索到的技巧，对候选动作进行加分/减分。
  - 示例: 检索到 "队友保护" 技巧 -> 提高 PASS 的分数。
- [ ] **A3. 动态权重**
  - 根据 `priority` 动态调整加分幅度。

### 阶段 4: 验证与优化
- [ ] **V1. 单元测试**: 测试 Retriever 和 Translator。
- [ ] **V2. 集成测试**: 验证 Layer 3 是否正确影响决策。
- [ ] **V3. 实战测试**: 对比开启/关闭知识增强的胜率。

## 📝 立即执行 (Next Steps)
1.  创建 `docs/knowledge` 的标准目录结构。
2.  选择 3-5 个核心技巧（如队友保护、对手压制）进行格式化和代码实现。
3.  在 `KnowledgeEnhancedDecision` 中集成这些核心技巧。
