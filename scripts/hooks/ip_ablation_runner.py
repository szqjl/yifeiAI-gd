# -*- coding: utf-8 -*-
"""
GUA-097: 每条 IP 上线前对照批跑 helper

设计目标:
- 不改任何业务代码——只生成"启用 vs 关闭 IP-X"的对照批跑配置
- 强制"加规则前必须有基线、加规则后必须有验证"——机械化 v4v5v6 教训 §6.2 "加规则不测"

使用流程:
    1) 跑基线 (全部 IP 关闭):  python scripts/hooks/ip_ablation_runner.py --mode baseline
       → 净盘 + 批跑 + 写 v7-win-rate-history.md (GUA-096 联动)
    2) 启用单条 IP-X:          python scripts/hooks/ip_ablation_runner.py --mode enable --ip-id IP-07
       → 净盘 + 批跑 + 对比
    3) 跑完看 win_rate 差:     python scripts/hooks/ip_ablation_runner.py --mode diff --ip-id IP-07

约束:
- 每次跑都强制走 GUA-096 (post_batch_log)
- 输出 ABLATION_LOG.md (v7-gua097-ablation-log.md) 一行
"""
import argparse
import datetime
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ABLATION_LOG = ROOT / "docs/guandan-brain/iterations" / "v7-gua097-ablation-log.md"
POST_BATCH = ROOT / "scripts/hooks/post_batch_log.py"

# IP 规则 ID 与对应 heuristic/guard 描述 (来自 §7.2.4.1 IP-01~IP-13 + §7.9.2 IP-14~IP-21)
IP_REGISTRY = {
    # 相生相克 (Layer 2 推断)
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


def ensure_log():
    if not ABLATION_LOG.exists():
        ABLATION_LOG.parent.mkdir(parents=True, exist_ok=True)
        ABLATION_LOG.write_text(
            "# GUA-097 Ablation Log — IP 规则对照批跑\n\n"
            "> **设计目标**：每条 IP 规则上线前必须跑基线 + 启用后批跑，机械化 V 系列「加规则不测」教训。\n"
            "> **每行格式**：`date | mode | ip_id | description | win_rate | delta_vs_baseline`\n\n"
            "| date | mode | ip_id | description | win_rate | delta_vs_baseline | 备注 |\n"
            "|------|------|-------|-------------|----------|-------------------|------|\n",
            encoding="utf-8",
        )


def run_post_batch(gua_id, change, cmd, games, note):
    """联动 GUA-096 写 win-rate-history"""
    cmd_list = ["python", str(POST_BATCH),
                "--gua-id", gua_id,
                "--change", change,
                "--cmd", cmd,
                "--games", str(games),
                "--note", note,
                "--quiet"]
    r = subprocess.run(cmd_list, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[WARN] post_batch 失败: {r.stderr}", file=sys.stderr)
    return r.returncode == 0


def append_ablation(date, mode, ip_id, description, win_rate, delta, note):
    ensure_log()
    with open(ABLATION_LOG, "a", encoding="utf-8") as f:
        f.write(f"| {date} | {mode} | {ip_id or '-'} | {description} | {win_rate or '-'} | {delta or '-'} | {note} |\n")


def main():
    p = argparse.ArgumentParser(description="GUA-097 IP 规则对照批跑 helper")
    p.add_argument("--mode", choices=["baseline", "enable", "diff", "list"], required=True)
    p.add_argument("--ip-id", help="IP 规则 ID (如 IP-07)")
    p.add_argument("--games", type=int, default=3, help="每轮局数 (默认 3)")
    args = p.parse_args()

    if args.mode == "list":
        print("# IP Registry:")
        for ip, desc in IP_REGISTRY.items():
            print(f"  {ip}: {desc}")
        return

    if args.mode == "baseline":
        # 基线：所有 IP 关闭
        change = "[BASELINE] 全部 IP 规则关闭"
        gua_id = "GUA-097-BASELINE"
        note = "GUA-097 baseline (无 IP 规则)"
        cmd = f"python scripts/launchers/v7/run_v7_vs_lalala_games.py --games {args.games}"
        run_post_batch(gua_id, change, cmd, args.games, note)
        append_ablation(datetime.date.today().isoformat(), "baseline", "-",
                        "全部 IP 关闭", "(见 win-rate-history.md)", "-", note)
        print(f"[GUA-097] baseline 已跑 + 落盘")
        return

    if args.mode == "enable":
        if not args.ip_id or args.ip_id not in IP_REGISTRY:
            print(f"[ERROR] --ip-id 必须是 IP_REGISTRY 中的: {list(IP_REGISTRY.keys())}", file=sys.stderr)
            sys.exit(2)
        change = f"[ENABLE] 启用 {args.ip_id}"
        gua_id = f"GUA-097-{args.ip_id}"
        note = f"GUA-097 enable {args.ip_id} ({IP_REGISTRY[args.ip_id]})"
        cmd = f"python scripts/launchers/v7/run_v7_vs_lalala_games.py --games {args.games} --enable-ip {args.ip_id}"
        run_post_batch(gua_id, change, cmd, args.games, note)
        append_ablation(datetime.date.today().isoformat(), "enable", args.ip_id,
                        IP_REGISTRY[args.ip_id], "(见 win-rate-history.md)", "TBD", note)
        print(f"[GUA-097] enable {args.ip_id} 已跑 + 落盘")
        return

    if args.mode == "diff":
        # 读 ablation log 取 baseline + enable 两行做差
        if not ABLATION_LOG.exists():
            print(f"[ERROR] {ABLATION_LOG} 不存在 — 先跑 baseline + enable", file=sys.stderr)
            sys.exit(2)
        print(f"[GUA-097] diff 模式: 请对比 win-rate-history.md 中 BASELINE 与 GUA-097-{args.ip_id or '?'} 两行")
        print(f"        见 {ABLATION_LOG} 末尾两行")
        return


if __name__ == "__main__":
    main()
