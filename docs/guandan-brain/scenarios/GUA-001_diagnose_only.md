# GUA-001 — 批量执行器诊断（无对局）

## 目的

不启动完整对局，验证离线服务器路径可用、诊断流程可走通。

## 命令（在项目根目录）

将 `<SERVER_EXE>` 换成本机存在的 `guandan_offline_v1006.exe` 路径（GUI 默认尝试顺序见 `batch_executor_gui.py` 中 `load_default_config` 的 `possible_paths`，常见为 `server/guandan_offline_v1006.exe` 或自备路径）。

```bash
python -m batch_executor --server-path "<SERVER_EXE>" --diagnose-only
```

## 期望

- 进程退出码为 0。
- 日志/输出中无「服务器文件不存在」类致命错误。
- 诊断报告能给出「期望游戏次数 / 实际检测」等字段（具体以当时服务器为准）。
