# -*- coding: utf-8 -*-
"""导出 M3 10 局 vs M1 12 局批跑 WARNING 对照表到 docs/analysis/。"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_MD = ROOT / "docs" / "analysis" / "batch-warnings-comparison-2026-05-31.md"
OUT_M3_CLIENT = ROOT / "docs" / "analysis" / "batch-warnings-m3-10-full.txt"
OUT_M1_CLIENT = ROOT / "docs" / "analysis" / "batch-warnings-m1-12-full.txt"

RUNS = {
    "M3 净盘 10 局": {
        "batch_log": ROOT / "logs" / "batch_executor_20260531_201339.log",
        "client_globs": [
            "yf1_m3_20260531_201407.log",
            "yf1_m3_20260531_201530.log",
            "yf1_m3_20260531_201652.log",
            "yf1_m3_20260531_201805.log",
            "yf2_m3_20260531_201414.log",
            "yf2_m3_20260531_201537.log",
            "yf2_m3_20260531_201700.log",
            "yf2_m3_20260531_201812.log",
        ],
    },
    "M1 净盘 12 局": {
        "batch_log": ROOT / "logs" / "batch_executor_20260531_204844.log",
        "client_globs": [
            "yf1_m1_20260531_204913.log",
            "yf1_m1_20260531_205025.log",
            "yf1_m1_20260531_205143.log",
            "yf1_m1_20260531_205251.log",
            "yf2_m1_20260531_204920.log",
            "yf2_m1_20260531_205033.log",
            "yf2_m1_20260531_205150.log",
            "yf2_m1_20260531_205258.log",
        ],
    },
}


def extract_warnings(path: Path) -> list[tuple[int, str]]:
    if not path.exists():
        return []
    out: list[tuple[int, str]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if "WARNING" in line:
            out.append((i, line))
    return out


def categorize(line: str) -> str:
    if "检测到参数不匹配" in line:
        return "诊断：exe 场数未解析"
    if "match_key 增量" in line:
        return "台账：副数>>局数"
    if "latest_victory_num" in line:
        return "批末：无交叉验证文件"
    if "卡牌验证失败" in line:
        return "GameRecorder：卡牌验证"
    if "gameResult" in line and "vn" in line:
        return "GUA-033：gameResult fallback"
    if "无victoryNum" in line:
        return "M1：待回填 victoryNum"
    if "break protected combination" in line:
        return "M1：保护组合跳过"
    if "Invalid action index" in line:
        return "M1：actIndex 越界兜底"
    if "Coercing PASS" in line:
        return "M1：PASS 强制改出"
    if "anti-tribute" in line:
        return "M1：抗贡通知未识别"
    if "Cannot suppress" in line or "fallback: returning" in line:
        return "M1：阶段 handler fallback"
    if "手牌移除不完整" in line:
        return "GameRecorder：手牌扣减"
    return "其他"


def write_full_client_dump(path: Path, run_name: str, client_globs: list[str]) -> int:
    lines = [
        f"# {run_name} — 客户端 WARNING 完整原文",
        "# 逐行未去重；含 yf1 + yf2 各 4 批",
        "",
    ]
    total = 0
    for g in client_globs:
        p = ROOT / "logs" / g
        lines.append(f"## {g}")
        lines.append("")
        ws = extract_warnings(p)
        total += len(ws)
        if not ws:
            lines.append("（无 WARNING）")
        else:
            lines.extend(text for _, text in ws)
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return total


def main() -> None:
    data: dict = {}
    for run_name, cfg in RUNS.items():
        batch_ws = extract_warnings(cfg["batch_log"])
        clients: dict[str, list] = {}
        all_client: list[tuple[str, int, str]] = []
        for g in cfg["client_globs"]:
            p = ROOT / "logs" / g
            ws = extract_warnings(p)
            clients[g] = ws
            all_client.extend((g, ln, text) for ln, text in ws)
        data[run_name] = {"batch": batch_ws, "clients": clients, "all_client": all_client}

    m3_c = write_full_client_dump(OUT_M3_CLIENT, "M3 净盘 10 局", RUNS["M3 净盘 10 局"]["client_globs"])
    m1_c = write_full_client_dump(OUT_M1_CLIENT, "M1 净盘 12 局", RUNS["M1 净盘 12 局"]["client_globs"])

    def cat_counts(all_client: list) -> Counter:
        c: Counter = Counter()
        for _, _, text in all_client:
            c[categorize(text)] += 1
        return c

    m3_cat = cat_counts(data["M3 净盘 10 局"]["all_client"])
    m1_cat = cat_counts(data["M1 净盘 12 局"]["all_client"])
    all_cats = sorted(set(m3_cat) | set(m1_cat))

    notes = {
        "诊断：exe 场数未解析": "batch_executor 启动诊断；exe stdout 无场数",
        "台账：副数>>局数": "1 局含多副；match_key 为副级计数",
        "批末：无交叉验证文件": "M1 不写 latest_victory_num.json",
        "GameRecorder：卡牌验证": "出牌与初始手牌快照校验",
        "GUA-033：gameResult fallback": "batch_games=1；服务器 vn 为 3 局合计",
        "M1：待回填 victoryNum": "episodeOver 先落盘、gameResult 后回填",
        "M1：保护组合跳过": "OpeningActive 拆结构保护",
        "M1：actIndex 越界兜底": "决策 index 非法 → 0(PASS)",
        "M1：PASS 强制改出": "StageRouter coerce 非 PASS",
        "M1：抗贡通知未识别": "stage=anti-tribute",
        "M1：阶段 handler fallback": "Endgame 等分支 fallback",
        "GameRecorder：手牌扣减": "期望移除张数与实际不符",
        "其他": "见完整原文文件",
    }

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md: list[str] = [
        "# 批跑 WARNING 对照表（M3 10 局 vs M1 12 局）",
        "",
        f"**生成时间**：{now}",
        "",
        "## 来源",
        "",
        "| 批跑 | batch_executor 日志 | 客户端 | ITERATIONS |",
        "|------|---------------------|--------|------------|",
        "| **M3 净盘 10 局** | `logs/batch_executor_20260531_201339.log` | `yf1_m3`/`yf2_m3` ×4 批 | GUA-022/026 M3 净盘批跑 |",
        "| **M1 净盘 12 局** | `logs/batch_executor_20260531_204844.log` | `yf1_m1`/`yf2_m1` ×4 批 | GUA-022 M1 净盘 12 局 |",
        "",
        "## 数量总览",
        "",
        "| 来源 | M3 10 局 | M1 12 局 |",
        "|------|----------|----------|",
        f"| batch_executor WARNING | {len(data['M3 净盘 10 局']['batch'])} | {len(data['M1 净盘 12 局']['batch'])} |",
        f"| 客户端 WARNING（yf1+yf2 合计） | {m3_c} | {m1_c} |",
        "",
        "**完整客户端 WARNING 原文**（逐行、未去重）见：",
        "",
        "- [`batch-warnings-m3-10-full.txt`](./batch-warnings-m3-10-full.txt)",
        "- [`batch-warnings-m1-12-full.txt`](./batch-warnings-m1-12-full.txt)",
        "",
        "## 分类对照（客户端）",
        "",
        "| 分类 | M3 10 局 | M1 12 局 | 说明 |",
        "|------|----------|----------|------|",
    ]
    for cat in all_cats:
        md.append(f"| {cat} | {m3_cat.get(cat, 0)} | {m1_cat.get(cat, 0)} | {notes.get(cat, '')} |")

    md.extend(
        [
            "",
            "---",
            "",
            "## batch_executor WARNING 完整原文",
            "",
            "### M3 净盘 10 局（5 条）",
            "",
            "```text",
        ]
    )
    for _, line in data["M3 净盘 10 局"]["batch"]:
        md.append(line)
    md.extend(["```", "", "### M1 净盘 12 局（7 条）", "", "```text"])
    for _, line in data["M1 净盘 12 局"]["batch"]:
        md.append(line)
    md.extend(["```", "", "---", "", "## 客户端 WARNING 按文件对照", "", "| 文件 | M3 WARNING 数 | M1 WARNING 数 |", "|------|---------------|---------------|"])

    m3_files = RUNS["M3 净盘 10 局"]["client_globs"]
    m1_files = RUNS["M1 净盘 12 局"]["client_globs"]
    for i in range(4):
        yf1_m3, yf2_m3 = m3_files[i], m3_files[i + 4]
        yf1_m1, yf2_m1 = m1_files[i], m1_files[i + 4]
        n_m3_yf1 = len(data["M3 净盘 10 局"]["clients"].get(yf1_m3, []))
        n_m3_yf2 = len(data["M3 净盘 10 局"]["clients"].get(yf2_m3, []))
        n_m1_yf1 = len(data["M1 净盘 12 局"]["clients"].get(yf1_m1, []))
        n_m1_yf2 = len(data["M1 净盘 12 局"]["clients"].get(yf2_m1, []))
        md.append(f"| 批{i + 1} `{yf1_m3}` | {n_m3_yf1} | — |")
        md.append(f"| 批{i + 1} `{yf1_m1}` | — | {n_m1_yf1} |")
        md.append(f"| 批{i + 1} `{yf2_m3}` | {n_m3_yf2} | — |")
        md.append(f"| 批{i + 1} `{yf2_m1}` | — | {n_m1_yf2} |")

    md.extend(
        [
            "",
            "---",
            "",
            "## 批末对账（M3 第 4 批，INFO 非 WARNING，供对照）",
            "",
            "```text",
        ]
    )
    for line in RUNS["M3 净盘 10 局"]["batch_log"].read_text(encoding="utf-8").splitlines():
        if "批末对账" in line or "批末 victoryNum 校验通过" in line:
            md.append(line)
    md.extend(
        [
            "```",
            "",
            "---",
            "",
            "## 解读要点",
            "",
            "1. **「检测到参数不匹配」**：两次均有；根因是 v1006 exe 不在 stdout 打印 argv 局数，非批跑失败。",
            "2. **「match_key 增量 >> batch_games」**：副（episodeOver）≠ 局（gameOver）；分析 PASS 用牌谱，队胜用批末 vn。",
            "3. **M1 四次「未找到 latest_victory_num.json」**：M1 客户端未写该文件；M3 由 `yf1_m3` 写入。",
            "4. **M3 批 4 gameResult fallback**：见 `yf1_m3_20260531_201805.log` 与 platform-data-interpretation §4.3.1。",
            "5. **M1 客户端 WARNING 远多于 M3**：大量 OpeningActive 保护组合、actIndex 越界；M3 以 GameRecorder 卡牌校验为主。",
            "",
            "## 再生成",
            "",
            "```bash",
            "python scripts/tools/export_batch_warnings_comparison.py",
            "```",
        ]
    )

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT_MD}")
    print(f"M3 client WARNING lines: {m3_c} -> {OUT_M3_CLIENT}")
    print(f"M1 client WARNING lines: {m1_c} -> {OUT_M1_CLIENT}")


if __name__ == "__main__":
    main()
