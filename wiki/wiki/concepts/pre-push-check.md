---
type: concept
title: "推送前检查双保险"
sources:
  - docs/guandan-brain/SCRIPT_INDEX.md
tags:
  - concept
  - pre-push
  - git-hooks
  - validation
  - quality-gate
status: current
related_gua: []
date: 2026-06-20
---

# 推送前检查双保险

## 概述

项目实施**应用层 + Hook 层**双重推送前检查，确保代码质量、`.gitignore` 完整性、敏感信息不泄露。

## 双保险机制

### 第一道：应用层 `verify_gitignore.py`

- **位置**：`scripts/checks/verify_gitignore.py`
- **触发**：手动执行或 CI 流水线
- **职责**：
  1. 验证 `.gitignore` 规则覆盖所有临时文件（`*.pyc`、`__pycache__/`、`*.log` 等）
  2. 检测仓库中是否有**已追踪的应忽略文件**
  3. 输出修复建议

```bash
python scripts/checks/verify_gitignore.py
```

### 第二道：Hook 层 `pre_push_validate.py`

- **位置**：`scripts/hooks/pre_push_validate.py`
- **触发**：Git pre-push hook（自动）
- **职责**：
  1. 检测推送分支是否符合命名规范
  2. 运行单元测试（`pytest scripts/tests/`）
  3. 调用 [[module-qoder-agent]] 的代码评审模板
  4. 验证 commit message 格式

```bash
# 安装 hook
cp scripts/hooks/pre_push_validate.py .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## 双保险协同

```
git push origin <branch>
    ↓
.git/hooks/pre-push 触发
    ↓
pre_push_validate.py 执行：
    ├── 1. 分支命名检查
    ├── 2. 运行 pytest
    ├── 3. 调用 Qoder Agent 评审
    └── 4. 验证 commit message
    ↓
（任一失败则阻断推送）
    ↓
CI 流水线再次执行 verify_gitignore.py
    ↓
合并入库
```

## 配置

- `_env.bat`（`scripts/launchers/_env.bat`）— 公共环境变量
- `pre_push_check.bat`（根目录 / `scripts/launchers/tools/`）— 一键执行两道检查

## 关联页面

- [[module-qoder-agent]] — Qoder Agent SDK（代码评审）
- [[module-script-launchers]] — 启动器分层（含 pre_push_check.bat）
- [[SCRIPT_INDEX-summary]] — 完整脚本索引
