# 决策流程重构 TODO

## 目标
将当前的"后备链"架构改为"增强模式"架构，让知识库真正发挥作用

## 当前问题（已解决 ✅）
- ✅ Layer 1 (YF) 现在返回候选列表，不再阻塞后续层
- ✅ Layer 2 (DecisionEngine) 现在正常执行，返回多个候选
- ✅ Layer 3 (Knowledge) 现在每次决策都会执行，进行知识增强评分
- ✅ 知识库已实现为"增强层"，对候选动作进行评分增强

## 目标架构

```
决策流程：
1. 关键规则检查（硬约束）→ 立即返回
2. 生成候选动作（Layer 1 + Layer 2）
3. 知识增强评分（Layer 3）
4. 选择最优动作
```

---

## TODO 清单

### ✅ 阶段 0：准备工作
- [x] 创建重构TODO文档
- [ ] 备份当前代码
- [ ] 创建测试分支

### 📋 阶段 1：修改 HybridDecisionEngineV4 架构

**文件**: `src/decision/hybrid_decision_engine_v4.py`

#### ✅ Task 1.1: 添加关键规则层 (已完成)
- [x] 添加 `_apply_critical_rules(message)` 方法
- [x] 实现队友保护规则
  - 队友剩余牌 <= 3 → 立即PASS
  - 队友剩余牌 <= 5 且出大牌(A+) → PASS
- [x] 实现对手压制规则
  - 对手剩余牌 <= 3 → 必须出牌压制
  - 对手剩余牌 <= 5 且被动模式 → 尝试压制
- [x] 实现进贡阶段保护规则
  - 进贡阶段框架已添加（待具体规则）
- [x] 添加辅助方法
  - `_check_teammate_protection()` - 队友保护检查
  - `_check_opponent_suppression()` - 对手压制检查
  - `_check_tribute_protection()` - 进贡保护检查
  - `_find_best_beat_action()` - 寻找最佳压制动作
  - `_get_card_value()` - 牌值转换
- [x] 更新统计系统支持 CriticalRules 层
- [x] 创建测试文件 `test_critical_rules.py`
- [x] 所有测试通过 (6/6)

#### ✅ Task 1.2: 修改 decide() 主流程 (已完成)
- [x] 在 decide() 开头添加关键规则检查
- [x] 如果关键规则触发，直接返回动作
- [x] 修改 Layer 1/2 为候选生成模式
- [x] 添加 Layer 3 增强评分
- [x] 选择最优动作返回
- [x] 创建测试文件 `test_task1_2_enhanced_architecture.py`
- [x] 所有测试通过 (5/5)

#### ✅ Task 1.3: 修改 Layer 调用逻辑 (已完成)
- [x] 修改 `_try_yf()` 返回候选动作列表而非单一动作
- [x] 修改 `_try_decision_engine()` 返回候选动作列表
- [x] 更新 `_generate_candidates()` 方法整合 Layer 1/2
- [x] `_select_best()` 方法已存在且功能完整
- [x] 所有测试通过 (5/5)

---

### 📋 阶段 2：修改 YFAdapter 为候选生成模式

**文件**: `src/communication/lalala_adapter_v4.py`

#### ✅ Task 2.1: 修改 decide() 方法 (已完成)
- [x] 保持 `decide()` 方法名（向后兼容）
- [x] 返回候选动作列表 `List[tuple]` 格式: `[(action_idx, score), ...]`
- [x] 移除触发 Layer 2/3 的逻辑（返回 None），改为返回空列表
- [x] 更新 `_try_yf()` 方法适配新格式
- [x] 所有测试通过 (5/5)

#### ✅ Task 2.2: 添加候选评分 (已完成)
- [x] 为 YF 返回的动作添加基础评分
- [x] 考虑返回 top-3 候选而非单一动作（主要选择 + top-2 额外候选）
- [x] 添加 `_score_yf_action()` 方法
- [x] 添加 `_get_rank_value()` 方法（牌值转换）
- [x] 添加 `_get_additional_candidates()` 方法（额外候选生成）
- [x] 所有测试通过 (5/5)

---

### 📋 阶段 3：增强 KnowledgeEnhancedDecision

**文件**: `src/knowledge/knowledge_enhanced_decision.py`

#### ✅ Task 3.1: 修改为增强评分模式 (已完成)
- [x] 添加 `enhance_candidates(candidates, message)` 方法
- [x] 接收候选列表，返回增强后的评分列表
- [x] 保留现有的 `_apply_knowledge_rules()` 逻辑
- [x] 更新 `hybrid_decision_engine_v4.py` 使用新接口
- [x] 所有测试通过 (5/5)

#### Task 3.2: 完善策略规则
- [x] 验证队友保护规则正确性 ✅
- [ ] 验证对手压制规则正确性
- [ ] 添加更多策略规则（参考 lalala）
- [ ] 调整评分权重

---

### 📋 阶段 4：添加关键规则实现

**新文件**: `src/decision/critical_rules.py`

#### Task 4.1: 创建关键规则模块
- [ ] 创建 `CriticalRules` 类
- [ ] 实现 `check_teammate_protection(message)` 方法
- [ ] 实现 `check_opponent_suppression(message)` 方法
- [ ] 实现 `check_tribute_protection(message)` 方法

#### Task 4.2: 规则优先级
- [ ] 定义规则优先级顺序
- [ ] 添加规则冲突处理
- [ ] 添加规则日志记录

---

### 📋 阶段 5：测试与验证

#### Task 5.1: 单元测试
- [ ] 测试关键规则触发条件
- [ ] 测试候选生成逻辑
- [ ] 测试知识增强评分
- [ ] 测试完整决策流程

#### Task 5.2: 集成测试
- [ ] 运行单局测试，检查日志
- [ ] 验证 Layer 3 是否被调用
- [ ] 验证决策时间 < 1.0s
- [ ] 检查决策合理性

#### Task 5.3: 对战测试
- [ ] 运行 10 局对战测试
- [ ] 记录 Layer 使用统计
- [ ] 对比重构前后战绩
- [ ] 分析失败案例

---

### 📋 阶段 6：优化与调整

#### Task 6.1: 性能优化
- [ ] 优化候选生成速度
- [ ] 优化知识规则评估速度
- [ ] 添加缓存机制（如需要）

#### Task 6.2: 策略调优
- [ ] 根据测试结果调整规则权重
- [ ] 添加缺失的关键规则
- [ ] 优化评分算法

#### Task 6.3: 文档更新
- [ ] 更新架构说明文档
- [ ] 更新 API 文档
- [ ] 添加使用示例

---

## 实施顺序

**第一步**: ✅ 阶段 1 Task 1.1 - 添加关键规则层 (已完成)
**第二步**: 阶段 1 Task 1.2 - 修改主流程 (已完成 ✅)
**第三步**: 阶段 1 Task 1.3 - 修改 Layer 调用逻辑 (已完成 ✅)
**第四步**: 阶段 3 Task 3.1 - 修改为增强模式 (进行中)
**第五步**: 阶段 5 Task 5.2 - 集成测试
**第六步**: 其他任务按需执行

---

## 风险控制

1. **每完成一个阶段，立即测试**
2. **保留原有代码作为备份**
3. **使用 git 分支管理**
4. **记录每次修改的影响**

---

## 预期效果

- ✅ Layer 3 (Knowledge) 每次决策都会执行
- ✅ 关键规则能快速响应紧急情况
- ✅ 知识库真正发挥增强作用
- ✅ 决策更加合理和灵活
- ✅ 战绩提升到 lalala 水平（40-50%）

---

## 当前状态

- **进度**: 阶段 1 Task 1.1, 1.2, 1.3 完成 ✅
- **状态**: 
  - ✅ 关键规则层已实现并测试通过 (Task 1.1)
  - ✅ 增强模式架构已实现 (Task 1.2)
  - ✅ Layer 调用逻辑已修改为候选列表模式 (Task 1.3)
- **测试结果**: 
  - Task 1.1: 6/6 测试通过 🎉
  - Task 1.2: 5/5 测试通过 🎉
  - Task 1.3: 5/5 测试通过 🎉
- **下一步**: 阶段 2 (可选) 或 阶段 3 (增强 KnowledgeEnhancedDecision)

