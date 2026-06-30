# -*- coding: utf-8 -*-
"""
GUA-097: 每条 IP / 关键 feature 上线前对照批跑 helper

设计目标:
- 真正执行净盘 + 批跑 + GUA-096 落盘，而不是只记账
- 支持 IP 实验，也支持像 GUA-091 这类 stage 入口 feature 的 baseline/enable 对照
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ABLATION_LOG = ROOT / "docs/guandan-brain/iterations" / "v7-gua097-ablation-log.md"
POST_BATCH = ROOT / "scripts/hooks/post_batch_log.py"
LAUNCHER = ROOT / "scripts/launchers/v7/run_v7_vs_lalala_games.py"
VN_FILE = ROOT / "batch_executor/latest_victory_num.json"

IP_REGISTRY = {
    "IP-01": "对手连续出 2+ Straight → oppo_has_straight_p += 0.3",
    "IP-02": "对手连续出 2+ ThreeWithTwo → oppo_has_straight_p += 0.4 (相克反推)",
    "IP-03": "对手出 5-9 Straight → 5-9 三张/炸概率低",
    "IP-04": "对手出小 Straight 被压未接回 → 7+ 三张概率高",
    "IP-05": "队友连续出 2+ ThreeWithTwo → teammate_needs_feed_type = 'trips'",
    "IP-06": "队友连续出 2+ Straight → teammate_needs_feed_type = 'single'",
    "IP-07": "对手从未出过 Single → oppo_singles_count_estimate += 2",
    "IP-08": "对手炸弹+同花顺 ≥ 2 → oppo_has_three_with_two_p -= 0.3",
    "IP-09": "10+ 牌分布推断",
    "IP-10": "缺张算同牌炸 (断张越多越可能成炸)",
    "IP-11": "进贡无级牌 = 'high' 隐藏对手",
    "IP-12": "对手剩余 X 张的概率分布 (8/7/6/5 张概率表)",
    "IP-13": "双进贡都是级牌 → 王在进贡对手",
    "IP-14": "出 5-9 顺 → 该段单牌多对子少",
    "IP-15": "对手出小牌后弃权 → 不需要该牌型",
    "IP-16": "8 张 10 出完 → 5-9 顺已登基",
    "IP-17": "胜方掌握进贡方最大牌",
    "IP-18": "出牌点位暗示手牌强弱",
    "IP-19": "10+ 牌分布概率",
    "IP-20": "算四大天王在谁家",
    "IP-21": "算同花顺花色",
}

FEATURE_REGISTRY = {
    "GUA-091": {
        "description": "stage_2 中局入口 _stage_mid_dispatch",
        "env_on": {"V7_ENABLE_STAGE2_DISPATCH": "1"},
        "env_off": {"V7_ENABLE_STAGE2_DISPATCH": "0"},
    },
}


def ensure_log():
    if not ABLATION_LOG.exists():
        ABLATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        ABLATION_LOG.write_text(
            "# GUA-097 Ablation Log — IP / Feature 对照批跑\n\n"
            "> **设计目标**：每条 IP 或关键 feature 上线前必须跑基线 + 启用后批跑。\n\n"
            "| date | mode | ip_id | description | win_rate | delta_vs_baseline | 备注 |\n"
            "|------|------|-------|-------------|----------|-------------------|------|\n",
            encoding="utf-8",
        )


def append_ablation(date, mode, exp_id, description, win_rate, delta, note):
    ensure_log()
    with open(ABLATION_LOG, "a", encoding="utf-8") as f:
        f.write(
            f"| {date} | {mode} | {exp_id or '-'} | {description} | "
            f"{win_rate or '-'} | {delta or '-'} | {note} |\n"
        )


def load_vn():
    if not VN_FILE.exists():
        return None
    try:
        return json.loads(VN_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def calc_team_win_rate(vn_payload):
    vn = (vn_payload or {}).get("victoryNum", [])
    if not isinstance(vn, list) or len(vn) < 4:
        return None, None
    team_a = vn[0]
    team_b = vn[1]
    total = team_a + team_b
    if total <= 0:
        return "0/0 (0.0%)", 0.0
    return f"{team_a}/{total} ({team_a / total * 100:.1f}%)", team_a / total


def clean_v7_runtime_artifacts():
    subprocess.run(
        [
            "taskkill",
            "/IM",
            "guandan_offline_v1006.exe",
            "/F",
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
    )

    for rel in [
        "tmp/.batch_executor.lock",
        "v7_vs_lalala_scores.json",
        "v7_vs_lalala_state.json",
        "batch_executor/latest_victory_num.json",
        "batch_executor/current_batch.json",
        "execution_state.json",
    ]:
        fp = ROOT / rel
        try:
            if fp.exists():
                fp.unlink()
        except Exception:
            pass

    for pattern in ["game_records_v7/*.json", "logs/*"]:
        for fp in ROOT.glob(pattern):
            try:
                if fp.is_file():
                    fp.unlink()
            except Exception:
                pass


def build_run_env(*, ip_id=None, feature_id=None, enable=False):
    env = dict(os.environ)
    env.setdefault("V7_ENABLE_DECISION_TRACE", "1")
    if ip_id:
        env["V7_ENABLE_IPS"] = ip_id if enable else ""
    if feature_id:
        spec = FEATURE_REGISTRY[feature_id]
        env.update(spec["env_on"] if enable else spec["env_off"])
    return env


def run_batch(games, env):
    cmd_list = [sys.executable, str(LAUNCHER), "--games", str(games)]
    print(f"[GUA-097] 执行批跑: {' '.join(cmd_list)}")
    result = subprocess.run(
        cmd_list,
        cwd=str(ROOT),
        env=env,
        text=True,
    )
    return result.returncode == 0, cmd_list


def run_post_batch(gua_id, change, cmd, games, note):
    cmd_list = [
        sys.executable,
        str(POST_BATCH),
        "--gua-id",
        gua_id,
        "--change",
        change,
        "--cmd",
        cmd,
        "--games",
        str(games),
        "--note",
        note,
        "--quiet",
    ]
    r = subprocess.run(cmd_list, capture_output=True, text=True, cwd=str(ROOT))
    if r.returncode != 0:
        print(f"[WARN] post_batch 失败: {r.stderr}", file=sys.stderr)
    return r.returncode == 0


def parse_args():
    p = argparse.ArgumentParser(description="GUA-097 IP / Feature 对照批跑 helper")
    p.add_argument("--mode", choices=["baseline", "enable", "diff", "list"], required=True)
    p.add_argument("--ip-id", help="IP 规则 ID (如 IP-07)")
    p.add_argument("--feature-id", help="Feature ID (如 GUA-091)")
    p.add_argument("--games", type=int, default=3, help="每轮局数 (默认 3)")
    return p.parse_args()


def main():
    args = parse_args()

    if args.mode == "list":
        print("# IP Registry:")
        for ip, desc in IP_REGISTRY.items():
            print(f"  {ip}: {desc}")
        print("# Feature Registry:")
        for fid, spec in FEATURE_REGISTRY.items():
            print(f"  {fid}: {spec['description']}")
        return

    if args.feature_id and args.feature_id not in FEATURE_REGISTRY:
        print(
            f"[ERROR] --feature-id 必须是 FEATURE_REGISTRY 中的: {list(FEATURE_REGISTRY.keys())}",
            file=sys.stderr,
        )
        sys.exit(2)
    if args.ip_id and args.ip_id not in IP_REGISTRY:
        print(
            f"[ERROR] --ip-id 必须是 IP_REGISTRY 中的: {list(IP_REGISTRY.keys())}",
            file=sys.stderr,
        )
        sys.exit(2)

    exp_id = args.feature_id or args.ip_id or "-"
    desc = (
        FEATURE_REGISTRY[args.feature_id]["description"]
        if args.feature_id
        else IP_REGISTRY.get(args.ip_id, "全部 IP 关闭")
    )

    if args.mode == "baseline":
        change = (
            f"[BASELINE] {args.feature_id} 关闭"
            if args.feature_id
            else "[BASELINE] 全部 IP 规则关闭"
        )
        gua_id = (
            f"GUA-097-{args.feature_id}-BASELINE"
            if args.feature_id
            else "GUA-097-BASELINE"
        )
        note = (
            f"GUA-097 baseline ({args.feature_id} off: {desc})"
            if args.feature_id
            else "GUA-097 baseline (无 IP 规则)"
        )
        clean_v7_runtime_artifacts()
        ok, cmd_list = run_batch(
            args.games,
            build_run_env(ip_id=args.ip_id, feature_id=args.feature_id, enable=False),
        )
        if not ok:
            print("[ERROR] baseline 批跑失败", file=sys.stderr)
            sys.exit(3)
        cmd = " ".join(cmd_list)
        run_post_batch(gua_id, change, cmd, args.games, note)
        win_rate_str, _ = calc_team_win_rate(load_vn())
        append_ablation(
            datetime.date.today().isoformat(),
            "baseline",
            exp_id,
            desc if args.feature_id else "全部 IP 关闭",
            win_rate_str or "(见 win-rate-history.md)",
            "-",
            note,
        )
        print(f"[GUA-097] baseline 已跑 + 落盘")
        return

    if args.mode == "enable":
        if not args.feature_id and not args.ip_id:
            print("[ERROR] enable 模式需要 --ip-id 或 --feature-id", file=sys.stderr)
            sys.exit(2)
        change = f"[ENABLE] 启用 {args.feature_id or args.ip_id}"
        gua_id = f"GUA-097-{args.feature_id or args.ip_id}"
        note = f"GUA-097 enable {args.feature_id or args.ip_id} ({desc})"
        clean_v7_runtime_artifacts()
        ok, cmd_list = run_batch(
            args.games,
            build_run_env(ip_id=args.ip_id, feature_id=args.feature_id, enable=True),
        )
        if not ok:
            print("[ERROR] enable 批跑失败", file=sys.stderr)
            sys.exit(3)
        cmd = " ".join(cmd_list)
        run_post_batch(gua_id, change, cmd, args.games, note)
        win_rate_str, _ = calc_team_win_rate(load_vn())
        append_ablation(
            datetime.date.today().isoformat(),
            "enable",
            exp_id,
            desc,
            win_rate_str or "(见 win-rate-history.md)",
            "TBD",
            note,
        )
        print(f"[GUA-097] enable {args.feature_id or args.ip_id} 已跑 + 落盘")
        return

    if args.mode == "diff":
        if not ABLATION_LOG.exists():
            print(f"[ERROR] {ABLATION_LOG} 不存在 — 先跑 baseline + enable", file=sys.stderr)
            sys.exit(2)
        print(
            f"[GUA-097] diff 模式: 请对比 win-rate-history.md / {ABLATION_LOG.name} "
            f"中 {args.feature_id or args.ip_id or '?'} 的 baseline 与 enable 两行"
        )
        return


if __name__ == "__main__":
    main()
