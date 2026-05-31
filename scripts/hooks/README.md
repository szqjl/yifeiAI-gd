# Git hooks（推送治理）

| 文件 | 用途 |
|------|------|
| `pre-push` | 阻止推 `main`、拦截 Layer 2 大文件进远程 |
| `pre_push_validate.py` | 校验逻辑（`pre_push_check.bat` 与 hook 共用） |
| `install-hooks.bat` | 本机一次性：`git config core.hooksPath scripts/hooks` |

## 安装（本机一次）

```bat
scripts\hooks\install-hooks.bat
```

## 手动检查（Agent / 人类推送前）

```bat
pre_push_check.bat
```

或：

```bat
python scripts/hooks/pre_push_validate.py
```

## Agent 必读

- [`docs/guandan-brain/AGENT_PUSH_CHECKLIST.md`](../../docs/guandan-brain/AGENT_PUSH_CHECKLIST.md)
- [`docs/governance/M-V-Series-治理方案.md`](../../docs/governance/M-V-Series-治理方案.md) §4 / §6 / §8

Hook **不能**代替阅读治理文档；只 enforce 分支与 Layer 2 硬规则。
