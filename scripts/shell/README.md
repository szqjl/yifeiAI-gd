# Shell 脚本（WSL / Linux / Git Bash）

> Phase 5（2026-05-29）：原根目录 `.sh` 迁入此目录；执行前自动 `cd` 仓库根。

## 脚本

| 文件 | 用途 |
|------|------|
| `train_m1_optimized.sh` | M1 优化训练（对等 `scripts/launchers/m/START_M1_TRAINING.bat`） |
| `run_new_test.sh` | 16 局 M1 vs lalala 批跑（对等 `scripts/launchers/tools/run_new_test.bat`） |
| `auto_clean_large_files.sh` | 自动清理大文件（模型检查点、文档等） |
| `clean_large_files.sh` | Git 仓库大文件清理（交互式） |
| `check_repo_size.sh` | 本地仓库容量检查 |

## 使用

```bash
bash scripts/shell/train_m1_optimized.sh
```

## 约定

- 每个脚本头部设置 `REPO_ROOT` 并 `cd` 至仓库根。
- Windows 日常入口优先使用 `scripts/launchers/` 下 `.bat`。
- 根目录 **无** `.sh` 真源；勿在根目录新增 shell 脚本。
