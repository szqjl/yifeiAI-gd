# 项目文档索引

本文档提供了项目中所有文档的完整索引和分类说明。

## 📚 文档结构

```
docs/
├── governance/                  # 治理、COS、文档审查、repo 清理台账
│   ├── M-V-Series-治理方案.md
│   ├── DOCUMENT_AUDIT.md
│   └── repo-cleanup-inventory.md
├── architecture/                # 客户端架构总纲
│   └── 掼蛋AI客户端架构方案.md
├── project/                     # 项目历程与里程碑
├── versions/                    # V 系列版本对比（归档）
├── competition/                 # 比赛与对手分析
├── README.md                    # 文档目录总览
├── DOCUMENTATION_INDEX.md       # 本文档（完整索引）
│
├── quickstart/                  # 快速开始指南
│   ├── QUICK_START_MONITORING.md      # 训练监控快速开始
│   └── README_SMART_TRAINING.md       # 智能训练快速开始
│
├── archive/                     # 历史 rules/skill/implementation 等
│   └── implementation/
│       ├── 实施指导_总览_执行手册.md
│       ├── …（多部分实施指导）
│       └── 执行AI必读文件清单.md
│
├── training/                    # 训练相关文档
│   ├── 历次训练效果汇总.md
│   ├── 训练监控工具替代方案.md
│   ├── 智能训练插件使用指南.md
│   ├── 阶段0-实施基础验证.md
│   ├── 阶段1-完善信息提取.md
│   ├── 阶段2-策略理解深化.md
│   ├── 阶段3-动作预测精度提升.md
│   ├── 阶段4-持续优化.md
│   ├── 阶段5-高级策略学习.md
│   ├── 阶段6-游戏导向训练.md
│   ├── 阶段7-策略学习重构.md
│   ├── 阶段8-强化学习整合.md
│   └── ... (更多训练文档)
│
├── development/                 # 开发相关文档
│   ├── 分支开发指南.md
│   ├── M1优化功能配置说明.md
│   ├── M1卡牌一致性修复说明.md
│   ├── M1开局主动出牌策略说明.md
│   ├── M1策略问题分析与修复计划.md
│   ├── video-assets/ep1-debut/   # 第1期视频幻灯片与配图
│   ├── 手牌最优组合扫描器设计说明.md
│   ├── 手牌扫描器与上下文衔接优化说明.md
│   └── 智能体提升优化版.md
│
├── analysis/                    # 分析报告
│   ├── 1312_data_conversion_completeness.md
│   ├── 1312_data_format_analysis.md
│   ├── ADVANCED_WIN_RATE_ANALYSIS.md
│   ├── REPLAY_SYSTEM_COMPARISON.md
│   ├── RL调试信息问题分析.md
│   ├── YF决策问题分析与修复.md
│   ├── YF手牌接收与拆牌问题分析.md
│   ├── 复杂牌型优先级优化要点.md
│   ├── 天然单张定义说明.md
│   ├── 扫描器vs客户端分析器对比分析.md
│   ├── 拆炸弹问题分析与修复.md
│   └── json_data_update_recommendation.md
│
├── reports/                     # 项目报告和总结
│   ├── m1/                      # M1相关报告
│   │   ├── M1行为分析报告.md
│   │   ├── M1行为改善分析总结.md
│   │   ├── M1行为改善对比分析.md
│   │   ├── M1最新对局改善分析.md
│   │   ├── M1最新修复总结.md
│   │   ├── M1_PASS问题分析报告.md
│   │   ├── M1_PASS问题修复总结.md
│   │   ├── M1_PASS问题修复完成报告.md
│   │   └── M1_20251224_问题分析报告.md
│   ├── YF掼蛋优化实施报告.md
│   ├── 项目优化执行日志.md
│   ├── objective_summary.md
│   └── README_优化项目.md
│
├── fixes/                       # 问题修复记录
│   ├── M1_20251224_问题修复记录.md
│   ├── STRATEGY_UNDERSTANDING_FIX.md
│   └── GAME_ISSUE_FIX_SUMMARY.md
│
├── usage/                       # 使用指南
│   ├── STAGE6_GUI_README.md
│   ├── REPLAY_README.md
│   ├── batch_update_guide.md
│   ├── enhanced_gui_guide.md
│   ├── 1312_converter_improvements.md
│   ├── 1312_data_integration_guide.md
│   └── szqjl_data_update_summary.md
│
├── knowledge/                   # 知识库文档
│   ├── QUICK_START.md
│   ├── 术语统一规范.md
│   ├── rules/                   # 规则文档
│   └── skills/                  # 技能文档
│
├── integration/                 # 集成相关
│   └── yfv5_stage5_integration_plan.md
│
└── utils/                       # 工具文档
    └── 编码修复说明.md
```

## 🎯 文档分类说明

### 1. 快速开始 (quickstart/)
**用途**: 帮助新用户快速上手项目
- 训练监控快速开始指南
- 智能训练快速开始

**适合人群**: 新用户、快速参考

### 2. 实施指导（archive/implementation/，已归档）
**用途**: 历史 V6 多部分实施指导，备查  
**日常入口**: `docs/development/`、`docs/guandan-brain/`

### 3. 训练文档 (training/)
**用途**: 模型训练相关的所有文档
- 训练阶段说明
- 训练效果汇总
- 训练工具使用指南

**适合人群**: 训练工程师、研究人员

### 4. 开发文档 (development/)
**用途**: 功能开发和优化说明
- 功能设计说明
- 优化方案
- 开发指南

**适合人群**: 开发者

### 5. 分析报告 (analysis/)
**用途**: 问题分析和优化建议
- 问题分析报告
- 数据格式分析
- 性能分析

**适合人群**: 分析师、开发者

### 6. 项目报告 (reports/)
**用途**: 项目总结和成果报告
- M1相关报告
- 优化实施报告
- 项目执行日志

**适合人群**: 项目管理者、开发者

### 7. 问题修复 (fixes/)
**用途**: 问题修复记录
- 修复记录
- 修复总结

**适合人群**: 开发者、维护者

### 8. 使用指南 (usage/)
**用途**: 工具和功能的使用说明
- GUI使用指南
- 数据转换指南
- 回放系统说明

**适合人群**: 用户、开发者

### 9. 知识库 (knowledge/)
**用途**: 掼蛋游戏知识和规则
- 游戏规则
- 策略技能
- 术语规范

**适合人群**: 所有用户

## 📖 推荐阅读顺序

### 新用户入门
1. `README.md` (根目录) - 项目总览
2. `docs/quickstart/` - 快速开始指南
3. `docs/knowledge/QUICK_START.md` - 知识库快速开始

### 开发者
1. `docs/archive/implementation/实施指导_总览_执行手册.md` - 历史 V6 实施流程（归档）
2. `docs/development/` - 开发相关文档
3. `docs/training/` - 训练相关文档

### 问题排查
1. `docs/fixes/` - 查看修复记录
2. `docs/analysis/` - 查看问题分析
3. `docs/reports/m1/` - 查看M1相关问题

### 训练相关
1. `docs/training/历次训练效果汇总.md` - 训练历史
2. `docs/training/训练监控工具替代方案.md` - 监控工具
3. `docs/training/阶段*.md` - 各阶段训练说明

## 🔍 快速查找

### 按主题查找

**训练相关**
- 训练效果: `docs/training/历次训练效果汇总.md`
- 训练工具: `docs/training/训练监控工具替代方案.md`
- 训练阶段: `docs/training/阶段*.md`

**M1相关问题**
- 所有M1报告: `docs/reports/m1/`
- M1开发文档: `docs/development/M1*.md`
- M1修复记录: `docs/fixes/M1_*.md`

**实施指导**
- 历史实施文档: `docs/archive/implementation/`

**问题分析**
- 所有分析: `docs/analysis/`
- 修复记录: `docs/fixes/`

## 📝 文档维护

### 添加新文档时的分类原则

1. **快速开始类** → `docs/quickstart/`
   - 30秒快速开始
   - 快速参考指南

2. **实施指导类（历史）** → `docs/archive/implementation/`
   - 详细实施步骤
   - 执行检查清单

3. **训练相关** → `docs/training/`
   - 训练配置
   - 训练效果
   - 训练工具

4. **开发相关** → `docs/development/`
   - 功能设计
   - 优化方案
   - 开发指南

5. **分析报告** → `docs/analysis/` 或 `docs/reports/`
   - 问题分析 → `docs/analysis/`
   - 项目报告 → `docs/reports/`

6. **使用指南** → `docs/usage/`
   - 工具使用
   - 功能使用

7. **问题修复** → `docs/fixes/`
   - 修复记录
   - 修复总结

## 🔗 相关链接

- [项目主README](../README.md)
- [文档目录README](README.md)
- [知识库快速开始](knowledge/QUICK_START.md)

---

**最后更新**: 2025-01-10  
**维护者**: AI Assistant
