# 评测 / 实验 JSON 归档

历史批跑、T8/T9、Phase4 验证等**一次性输出**，非运行时真源。

| 文件 | 日期 | 说明 |
|------|------|------|
| `test_phase4_final_verification_report.json` | 2026-05-25 | Phase4 验证未达标（胜率 0%） |
| `test_t8_results.json` | 2026-05-22 | T8 空样本 |
| `test_t9_results.json` | 2026-05-22 | T9 16 局 0 胜 |
| `test_t9_results_backup.json` | — | T9 备份 |

**新跑结果**请写入 `data/eval/`（可 gitignore）；`scripts/tools/run_t9_direct.py` 默认输出 `data/eval/test_t9_results.json`。
