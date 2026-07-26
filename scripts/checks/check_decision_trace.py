"""
check_decision_trace.py — WF-12 决策链路分析前置检查脚本

强约束（Skill §0）：未跑通禁止写结论。

用法：
    python scripts/checks/check_decision_trace.py <game_records_json> --step N

退出码：
    0 = 全 ✅
    1 = 有 ❌
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- 常量（与 workflow §2.1/§2.2 对齐）---
RECORD_NAME_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)

# 配对 yf2：从 yf1 文件名解析 → 同 [round]-[suffix]、client 替换
def parse_record_name(path: Path) -> Optional[Dict[str, str]]:
    m = RECORD_NAME_RE.match(path.name)
    if not m:
        return None
    return {
        "timestamp": m.group(1),
        "client": m.group(2),
        "opponent": m.group(3),
        "round": m.group(4),
        "suffix": m.group(5),
    }


def action_key(action: Any) -> Optional[tuple]:
    if not isinstance(action, list) or not action:
        return None
    typ = str(action[0]).upper()
    rank = str(action[1]).upper() if len(action) > 1 else ""
    cards_raw = action[2] if len(action) > 2 and isinstance(action[2], list) else []
    return (typ, rank, tuple(sorted(str(c).upper() for c in cards_raw)))


def is_play_decision(decision: Dict[str, Any]) -> bool:
    ctx = decision.get("context") or {}
    stage = ctx.get("stage")
    if stage in ("tribute", "back"):
        return False
    if stage == "play":
        return True
    return stage is None and ctx.get("source") == "act"


def find_decision_at_step(
    game_data: Dict[str, Any], step_num: int
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    actions: List[Dict[str, Any]] = game_data.get("actions") or []
    player_id = game_data.get("player_id")
    if player_id is None:
        raise ValueError("game_data missing player_id")
    if step_num < 1 or step_num > len(actions):
        raise ValueError(f"step {step_num} out of range 1..{len(actions)}")

    play = actions[step_num - 1]
    if play.get("cur_pos") != player_id:
        raise ValueError(
            f"step {step_num} cur_pos={play.get('cur_pos')} != player_id={player_id}; "
            "pick a step where the analysis subject acted"
        )

    turn_idx = sum(1 for a in actions[:step_num] if a.get("cur_pos") == player_id) - 1
    play_decisions = [d for d in game_data.get("my_decisions") or [] if is_play_decision(d)]
    if turn_idx >= len(play_decisions):
        raise ValueError(
            f"no play my_decisions[{turn_idx}] "
            f"(have {len(play_decisions)} play entries, need turn #{turn_idx + 1})"
        )

    decision = play_decisions[turn_idx]
    expected_key = action_key(play.get("cur_action"))
    if action_key(decision.get("action")) != expected_key:
        matches = [
            i for i, d in enumerate(play_decisions)
            if action_key(d.get("action")) == expected_key
        ]
        if len(matches) == 1:
            decision = play_decisions[matches[0]]
        else:
            raise ValueError(
                f"ordinal/action mismatch at step {step_num}: "
                f"cur_action={play.get('cur_action')!r}, "
                f"ordinal_decision={decision.get('action')!r}, "
                f"action_key_matches={matches}"
            )
    return decision, play


def pair_teammate_json(yf1_path: Path) -> Optional[Path]:
    m = parse_record_name(yf1_path)
    if not m or "yf1" not in m["client"]:
        return None
    teammate = m["client"].replace("yf1", "yf2", 1)
    rnd, suf = m["round"], m["suffix"]
    my_ts = int(m["timestamp"])
    candidates = []
    for f in yf1_path.parent.iterdir():
        sm = parse_record_name(f)
        if sm and sm["client"] == teammate and sm["round"] == rnd and sm["suffix"] == suf:
            candidates.append(f)
    return min(candidates, key=lambda p: abs(int(p.name.split(" ", 1)[0]) - my_ts)) if candidates else None


def find_client_log(json_path: Path, client: str) -> Optional[Path]:
    """匹配 logs/yf{1|2}_*.log 与 json start_time 同批"""
    logs_dir = json_path.parent.parent / "logs"
    if not logs_dir.exists():
        return None
    # 简化：检查至少一个匹配的 log 文件
    pattern_logs = list(logs_dir.glob(f"{client}_*.log"))
    if not pattern_logs:
        return None
    # 取最新的一个（实际应该匹配 start_time，但 logs 不直接关联 JSON，按存在性兜底）
    return sorted(pattern_logs, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def check(name: str, ok: bool, detail: str = "") -> bool:
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name}{(' — ' + detail) if detail else ''}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="WF-12 决策链路分析前置检查；强约束 §0，未跑通禁止写结论"
    )
    parser.add_argument("json_file", type=Path, help="牌谱 JSON 文件路径")
    parser.add_argument("--step", type=int, required=True, help="目标步号（1-based）")
    parser.add_argument("--no-pair-check", action="store_true", help="yf1 模式跳过 yf2 配对检查")
    parser.add_argument("--report-path", type=str, default=None, help="指定报告路径（合规检查）")
    args = parser.parse_args()

    json_file: Path = args.json_file
    step: int = args.step

    print(f"\n=== WF-12 决策链路检查表 ===")
    print(f"牌谱：{json_file}")
    print(f"步号：{step}\n")

    all_ok = True

    # 检查 1：JSON 存在 + 可解析
    if not json_file.exists():
        check("1. 牌谱 JSON 存在", False, f"文件不存在: {json_file}")
        return 1
    try:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        check("1. 牌谱 JSON 可解析", True)
    except json.JSONDecodeError as e:
        check("1. 牌谱 JSON 可解析", False, str(e))
        return 1

    # 解析文件名
    parsed = parse_record_name(json_file)
    if not parsed:
        check("2. 文件名格式合规", False, "不符合 {ts} [{client}]-[opponent_1_3]-[{round}]-[{suffix}].json")
        return 1
    client = parsed["client"]
    is_yf1 = "yf1" in client
    is_yf2 = "yf2" in client

    # 检查 2：玩家标识对齐
    player_id = data.get("player_id")
    expected_pid = 0 if is_yf1 else (2 if is_yf2 else None)
    if expected_pid is None:
        check("2. 玩家标识对齐", False, f"无法识别 client={client}")
        return 1
    ok2 = player_id == expected_pid
    if not ok2:
        all_ok = False
    check(
        "2. 玩家标识对齐",
        ok2,
        f"player_id={player_id}, 期望={expected_pid} ({'yf1' if is_yf1 else 'yf2'})",
    )

    # 检查 3：步号合法性
    actions = data.get("actions") or []
    ok3 = 1 <= step <= len(actions)
    if not ok3:
        all_ok = False
    check("3. 步号合法性", ok3, f"1<={step}<={len(actions)}")

    # 检查 4：步号归属正确
    play = actions[step - 1] if ok3 else None
    cur_pos = play.get("cur_pos") if play else None
    ok4 = (cur_pos == player_id) if play else False
    if not ok4:
        all_ok = False
    check("4. 步号归属正确", ok4, f"actions[{step-1}].cur_pos={cur_pos}, player_id={player_id}")

    # 检查 5/6：双校验（find_decision_at_step）
    try:
        decision, _ = find_decision_at_step(data, step)
        ok5 = True
        ok6 = True
        ctx = decision.get("context") or {}
        detail6 = f"handCards_size={ctx.get('handCards_size', '?')}, curRank={ctx.get('curRank', '?')}, layer={decision.get('layer', '?')}"
        check("5. my_decisions 至少 1 条 play 决策", ok5)
        check("6. ordinal + action_key 双校验通过", ok6, detail6)
    except ValueError as e:
        all_ok = False
        check("5. my_decisions 至少 1 条 play 决策", False, str(e))
        check("6. ordinal + action_key 双校验通过", False, "前置检查失败")

    # 检查 7：yf2 必须配对 yf2 JSON
    if is_yf2 and not args.no_pair_check:
        # 找同副 yf1 文件，再通过其配对 yf2 验证是否就是当前文件
        # 简化：找同 [round]-[suffix] 的 yf1
        same_round_suffix = [
            f for f in json_file.parent.iterdir()
            if parse_record_name(f)
            and parse_record_name(f)["round"] == parsed["round"]
            and parse_record_name(f)["suffix"] == parsed["suffix"]
            and "yf1" in parse_record_name(f)["client"]
        ]
        if not same_round_suffix:
            all_ok = False
            check("7. yf2 必须配对 yf2 JSON", False, f"找不到同副 yf1 JSON（round={parsed['round']}, suffix={parsed['suffix']}）")
        else:
            yf1_path = same_round_suffix[0]
            expected_yf2 = pair_teammate_json(yf1_path)
            if expected_yf2 is None or expected_yf2 != json_file:
                all_ok = False
                check("7. yf2 必须配对 yf2 JSON", False, f"配对算法返回 {expected_yf2}, 期望 {json_file}")
            else:
                check("7. yf2 必须配对 yf2 JSON", True, f"配对自 {yf1_path.name}")
    elif is_yf2 and args.no_pair_check:
        check("7. yf2 必须配对 yf2 JSON", True, "--no-pair-check 已跳过")
    else:
        check("7. yf2 必须配对 yf2 JSON", True, f"{client}（非 yf2，配对检查不适用）")

    # 检查 8：客户端日志存在
    client_log = find_client_log(json_file, client)
    ok8 = client_log is not None
    if not ok8:
        all_ok = False
    check("8. 客户端日志存在", ok8, str(client_log) if client_log else f"logs/{client}_*.log 不存在")

    # 检查 9：报告路径合规（默认路径或指定路径）
    if args.report_path:
        report_path = Path(args.report_path)
        # 命名规范：docs/analysis/WF-12-<game_id>-<yf1|yf2>-<主题>.md（主题可包含数字/中文/短横线）
        expected_pattern = re.compile(
            r"^docs/analysis/WF-12-.+-(yf1|yf2)-.+\.md$"
        )
        relative = str(report_path).replace("\\", "/")
        ok9 = bool(expected_pattern.match(relative))
        if not ok9:
            all_ok = False
        check("9. 报告路径合规", ok9, relative)
    else:
        check("9. 报告路径合规", True, "未指定 report-path（将按 §5 命名规则自动生成）")

    print()
    if all_ok:
        print("=== ✅ 全部通过，可继续分析 ===")
        return 0
    else:
        print("=== ❌ 有检查项未通过，禁止写结论 ===")
        print("    修复后再重跑此脚本。")
        return 1


if __name__ == "__main__":
    sys.exit(main())