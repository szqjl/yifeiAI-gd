# GUI 批跑界面

| 文件 | 说明 |
|------|------|
| `batch_executor_gui.py` | 通用批跑 GUI（V4/V5 等） |
| `batch_executor_gui_m1.py` | M1 硬编码规则引擎 GUI |
| `batch_executor_gui_m2.py` | M2 优化引擎 GUI |
| `batch_executor_gui_m3.py` | M3 合约引擎 GUI |
| `start_gui.py` | 启动 `batch_executor_gui.py` 的便捷入口 |

## 启动

- M1：`scripts/launchers/m/START_M1_GUI.bat` 或 `python scripts/gui/batch_executor_gui_m1.py`
- 通用：`python scripts/gui/start_gui.py`（根目录 `start_gui.py` 为薄 stub）

## 路径

各 GUI 通过 `Path(__file__).resolve().parents[2]` 将仓库根加入 `sys.path`。
