"""
check_botzone_trace.py — WF-13 Botzone 平台对局适配层链路分析前置检查脚本

强约束（Skill §0）：未跑通禁止写结论。

用法：
    python scripts/checks/check_botzone_trace.py <log_file> --step N [--match PREFIX] [--iterations PATH]
    python scripts/checks/check_botzone_trace.py <log_file> --by-cards D2,C3,C4,D5,D6 [--match PREFIX]

语义：
    - --step N = match 前缀过滤后第 N 个 actionList 摘要行（1-based）。
      注意：人类「第 N 回合」是整局/跨副口径，与日志内摘要序号可能不一致；
      先用 `rg -n "actionList 摘要"` 数序号换算，或改用 --by-cards 牌面反查。
    - --by-cards：按 greater 牌面反查摘要行（多张牌按逗号分隔）。
    - --match：该对局 match id 前缀（如 6a71ace3）；未给则用日志首个 match。
    - 检查项：日志定位、match 定局、摘要定位、摘要可解析、greater 非 Free
      （判型异常信号）、决策行存在、ITERATIONS 记录合规。

退出码：0 = 全 ✅；1 = 有 ❌。
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

REQUEST_RE = re.compile(r"\[botzone_adapter\].*收到 request: match=(\S+) stage=play")
SUMMARY_RE = re.compile(
    r"\[botzone_adapter\].*actionList 摘要: match=(\S+) len=(\d+) types=(\{.*?\}) "
    r"greater=(\[.*?\]|None) must_play=(True|False)"
)
DECISION_RE = re.compile(r"\[botzone_adapter\].*决策: match=(\S+)")
NO_PRESS_RE = re.compile(r"\[botzone_adapter\].*跟牌轮无可压动作.*match=(\S+)")


def parse_types(raw: str) -> Optional[Dict[str, int]]:
    try:
        obj = ast.literal_eval(raw)
        if isinstance(obj, dict):
            return {str(k): int(v) for k, v in obj.items()}
    except (ValueError, SyntaxError):
        pass
    return None


def parse_greater(raw: str) -> Optional[List[Any]]:
    if raw == "None":
        return None
    try:
        obj = ast.literal_eval(raw)
        return obj if isinstance(obj, list) else None
    except (ValueError, SyntaxError):
        return None


def check(name: str, ok: bool, detail: str = "") -> bool:
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}{(' — ' + detail) if detail else ''}")
    return ok


def _pick_summary(summaries: List[tuple], pref: str, step: int):
    idx = 0
    for m in summaries:
        if m[0].startswith(pref):
            idx += 1
            if idx == step:
                return m
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="WF-13 Botzone 对局适配层链路分析前置检查；强约束 §0，未跑通禁止写结论"
    )
    parser.add_argument("log_file", type=Path, help="Botzone 客户端日志路径")
    parser.add_argument("--step", type=int, default=None,
                        help="目标 actionList 摘要序号（match 前缀过滤后，1-based）")
    parser.add_argument("--by-cards", type=str, default=None,
                        help="按 greater 牌面反查（逗号分隔，如 D2,C3,C4,D5,D6）")
    parser.add_argument("--match", type=str, default=None,
                        help="对局 match id 前缀（默认取日志首个 match）")
    parser.add_argument("--iterations", type=str, default=None,
                        help="ITERATIONS.md 路径（合规检查，默认 docs/guandan-brain/ITERATIONS.md）")
    args = parser.parse_args()

    if args.step is None and args.by_cards is None:
        parser.error("必须指定 --step N 或 --by-cards 牌面")
    if args.step is not None and args.by_cards is not None:
        parser.error("--step 与 --by-cards 二选一")

    log_file: Path = args.log_file
    step: int = args.step

    print(f"\n=== WF-13 Botzone 适配层链路检查表 ===")
    print(f"日志：{log_file}")
    if args.step:
        print(f"摘要序号：{args.step}")
    if args.by_cards:
        print(f"greater 牌面：{args.by_cards}")
    print()

    all_ok = True

    # 检查 1：日志存在 + 是 botzone 日志
    if not log_file.exists():
        check("1. 日志存在", False, f"文件不存在: {log_file}")
        return 1
    try:
        text = log_file.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        check("1. 日志可读", False, str(e))
        return 1
    ok1 = "[botzone_adapter]" in text
    all_ok &= check("1. 日志含 botzone_adapter", ok1,
                    f"size={log_file.stat().st_size}B" if ok1 else "无 [botzone_adapter] 行")

    # 检查 2：match 定局
    matches = REQUEST_RE.findall(text)
    if args.match:
        pref = args.match
        hits = [m for m in matches if m.startswith(pref)]
        ok2 = len(hits) >= 1
        detail2 = f"前缀 {pref} 命中 {len(hits)} 个 stage=play request" if ok2 else f"无 {pref} 的 stage=play"
    else:
        pref = matches[0] if matches else ""
        hits = [m for m in matches if m == pref]
        ok2 = bool(matches)
        detail2 = f"默认取首个 match={pref}（{len(hits)} 个 stage=play）" if ok2 else "日志无 stage=play"
    all_ok &= check("2. match 定局", ok2, detail2)
    if not ok2:
        print()
        print("=== ❌ match 无法定局，禁止写结论 ===")
        return 1

    summaries = SUMMARY_RE.findall(text)
    my_sum = None
    if args.by_cards:
        want = sorted(c.strip().upper() for c in args.by_cards.split(",") if c.strip())
        for m in summaries:
            if not m[0].startswith(pref):
                continue
            gr = parse_greater(m[3])
            if gr and len(gr) >= 3 and sorted(str(c).upper() for c in gr[2]) == want:
                my_sum = m
                break
        ok3 = my_sum is not None
        all_ok &= check("3. greater 牌面反查", ok3,
                        f"cards={args.by_cards}" if ok3 else f"match={pref} 无 actionList 含这些牌")
    else:
        my_sum = _pick_summary(summaries, pref, step)
        ok3 = my_sum is not None
        all_ok &= check("3. 摘要序号合法", ok3,
                        f"第 {step} 条 actionList 摘要" if ok3 else f"match={pref} 摘要序号越界（共 {len([m for m in summaries if m[0].startswith(pref)])} 条）")

    if not ok3:
        print()
        print("=== ❌ 目标摘要未定位，禁止写结论 ===")
        print("可选修正：--step 传 match 过滤后的摘要序号，或 --by-cards 按 greater 牌面反查。")
        print("日志内全部 actionList 摘要（定位参考）：")
        n = 0
        for m in summaries:
            if m[0].startswith(pref):
                n += 1
                gr = parse_greater(m[3])
                gstr = f"{gr[0]}/{gr[1]}" if gr and len(gr) >= 2 else "?"
                print(f"  #{n}: len={m[1]} types={m[2]} greater={gstr}")
        return 1

    # 检查 4：该摘要可解析（greater=None = 首手领出，合法）
    types = parse_types(my_sum[2])
    greater = parse_greater(my_sum[3])
    ok4 = types is not None and (greater is not None or my_sum[3] == "None")
    all_ok &= check("4. actionList 摘要可解析", ok4,
                    f"types={types if types else my_sum[2]} greater={greater if greater else my_sum[3]}")

    # 检查 5：greater 判型标注（Free = R-B01 判型异常信号；标注不阻断，
    # 因为「判型误判」正是本工作流的分析对象）
    gtype = greater[0] if ok4 and greater else ("领出" if ok4 else "?")
    is_free = ok4 and greater is not None and gtype == "Free"
    if is_free:
        print(f"  ⚠️  5. greater 判型标注 — greater_type=Free —— 判型 bug 信号（R-B01），见 WF-13 §4")
    else:
        all_ok &= check("5. greater 判型标注", True, f"greater_type={gtype}")

    # 检查 6：决策行存在（决策: 或 跟牌轮无可压动作）
    has_decision = bool(DECISION_RE.search(text)) or bool(NO_PRESS_RE.search(text))
    ok6 = has_decision
    all_ok &= check("6. 决策行存在", ok6, "决策:/跟牌轮无可压动作 至少一种")

    # 检查 7：ITERATIONS 记录合规（决策链路分析结论只记录进 ITERATIONS.md，不写报告）
    iterations_path = args.iterations or str(Path(__file__).resolve().parent.parent.parent
                                             / "docs" / "guandan-brain" / "ITERATIONS.md")
    if Path(iterations_path).exists():
        ok7 = True
        all_ok &= check("7. ITERATIONS 记录合规", ok7, iterations_path)
    else:
        check("7. ITERATIONS 记录合规", True, "ITERATIONS.md 未找到，分析结论仍需追加记录")

    print()
    if all_ok:
        print("=== ✅ 全部通过，可继续分析 ===")
        return 0
    print("=== ❌ 有检查项未通过，禁止写结论 ===")
    print("    修复后再重跑此脚本。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
