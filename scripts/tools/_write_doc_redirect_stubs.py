# -*- coding: utf-8 -*-
"""Create one-line redirect stubs after docs root reorganization."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "docs"

MOVES = [
    ("掼蛋AI客户端架构方案.md", "architecture/掼蛋AI客户端架构方案.md"),
    ("掼蛋AI完整开发指南.md", "development/掼蛋AI完整开发指南.md"),
    ("掼蛋AI相关比赛汇总.md", "competition/掼蛋AI相关比赛汇总.md"),
    ("掼蛋AI知识应用框架.md", "knowledge/掼蛋AI知识应用框架.md"),
    ("结构化Prompt规范.md", "development/结构化Prompt规范.md"),
    ("模型文件管理方案.md", "governance/模型文件管理方案.md"),
    ("推送前检查指南.md", "development/推送前检查指南.md"),
    ("项目开发历程总览.md", "project/项目开发历程总览.md"),
    ("项目一年期限与里程碑.md", "project/项目一年期限与里程碑.md"),
    ("一等奖代码优秀特点分析.md", "competition/一等奖代码优秀特点分析.md"),
    ("知识库格式化方案.md", "knowledge/知识库格式化方案.md"),
    ("cleanup_summary.md", "governance/archive/cleanup_summary.md"),
    ("DanZero+论文分析-架构借鉴建议.md", "analysis/DanZero+论文分析-架构借鉴建议.md"),
    ("DEVELOPMENT_RULES.md", "development/DEVELOPMENT_RULES.md"),
    ("GIT_SETUP_GUIDE.md", "governance/git-setup-guide.md"),
    ("gitee_repo_capacity_guide.md", "governance/gitee-repo-capacity-guide.md"),
    ("guandan-basic-knowledge.md", "knowledge/guandan-basic-knowledge.md"),
    ("OCR_AND_MARKITDOWN_GUIDE.md", "usage/OCR_AND_MARKITDOWN_GUIDE.md"),
    ("REPLAY_IMPROVEMENTS.md", "usage/REPLAY_IMPROVEMENTS.md"),
    ("REPLAY_TRAINING_GUIDE.md", "training/REPLAY_TRAINING_GUIDE.md"),
    ("repo-cleanup-inventory.md", "governance/repo-cleanup-inventory.md"),
    ("V4_V5_COMPARISON.md", "versions/V4_V5_COMPARISON.md"),
    ("V5_MODEL_LOADING_AND_DEBUG_INFO.md", "versions/V5_MODEL_LOADING_AND_DEBUG_INFO.md"),
    ("WEBSOCKET_CONFIG.md", "development/WEBSOCKET_CONFIG.md"),
]

STUB = """# 文档已迁移

> **新位置**：[{target}]({target})  
> **归类说明**：[DOCUMENT_AUDIT.md](governance/DOCUMENT_AUDIT.md)

请勿在本路径继续编辑；请打开上方链接中的文件。
"""

for old_name, new_rel in MOVES:
    stub = ROOT / old_name
    stub.write_text(STUB.format(target=new_rel), encoding="utf-8")
print("stubs:", len(MOVES))
