#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Botzone 对局数据拉取 + 本地重放（分析在线/Local AI bot 对局的决策链）。

数据源：Botzone 对局回放端点 GET /match/<match_id>?lite=true
（公开可访问，无需登录；logs 为 Judge 视角回合记录）。

用途：把平台上某一场对局（含上传的在线 v8 bot 参与的对局）的
requests/responses 拉回本地，逐回合喂 BotzoneAdapter.handle_online_turn_sync
全量重放，将 V8 决策链（actionList 摘要 / 判型 / 意图）落盘到
logs/fetch_match_<match>.log，随后可按工作流 WF-13 用
scripts/checks/check_botzone_trace.py 定位「该压不压 / 牌型误判 / 候选缺失」。

使用方式:
    python scripts/launchers/botzone/fetch_match.py --match <match_id> [--player 0]
        [--out data/eval/botzone/match_<match_id>.json] [--replay] [--no-verify]

    --match     Botzone 对局 id（如 6a73e53d27e7bf01db12c646）
    --player    要分析的玩家座位（V8 座位，默认 0）
    --out       拉取的 requests/responses JSON 保存路径
    --replay    拉取后逐回合本地重放，决策链日志写 logs/fetch_match_<match>.log
    --no-verify 跳过 requests/responses 条数与合法性校验
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

_BASE = "https://www.botzone.org.cn"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Botzone 对局数据拉取 + 本地重放",
    )
    parser.add_argument("--match", required=True, help="Botzone 对局 id")
    parser.add_argument("--player", type=int, default=0, help="要分析的玩家座位（默认 0）")
    parser.add_argument("--out", default=None, help="requests/responses JSON 保存路径")
    parser.add_argument("--replay", action="store_true", help="拉取后逐回合本地重放")
    parser.add_argument("--no-verify", action="store_true", help="跳过校验")
    return parser.parse_args(argv)


def fetch_match_data(match_id: str) -> dict:
    """拉取对局回放 JSON。公开端点，无需登录。"""
    url = f"{_BASE}/match/{match_id}?lite=true"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as res:
        body = res.read().decode("utf-8")
    return json.loads(body)


def extract_player_stream(logs: list, player: int) -> tuple[list, list]:
    """从 logs 提取指定玩家的 requests 序列与 responses 序列。

    logs 为 Judge 视角回合记录：
      - 偶数索引：Judge 输出，output.content[<player>] = 发给该玩家的单回合 request；
      - 奇数索引：本回合各 bot 输出，output[<player>].response = 该玩家本回合响应。

    返回 (requests, responses) 与 Botzone 在线 bot 收到的
    {"requests": [...], "responses": [...]} 格式一致（requests 为该玩家
    按时间序的全部请求，含首回合 deal；responses 为其全部历史响应）。
    """
    requests: list = []
    responses: list = []
    key = str(player)
    for i, entry in enumerate(logs):
        if not isinstance(entry, dict):
            continue
        if i % 2 == 0:
            # Judge 回合：output.content[<player>] = 发给该玩家的单回合 request
            output = entry.get("output")
            content = output.get("content") if isinstance(output, dict) else None
            if isinstance(content, dict) and key in content:
                requests.append(content[key])
        else:
            # bot 回合：顶层直接是 {player_id: {response, verdict, ...}}
            player_out = entry.get(key)
            if isinstance(player_out, dict) and "response" in player_out:
                responses.append(player_out["response"])
    return requests, responses


def validate_stream(requests: list, responses: list) -> list[str]:
    """返回校验失败信息列表（空 = 通过）。"""
    errs: list[str] = []
    if not requests:
        errs.append("requests 为空")
        return errs
    if requests[0].get("stage") != "deal":
        errs.append(f"首个 request stage={requests[0].get('stage')!r} 非 deal")
    if len(responses) != len(requests) - 1:
        errs.append(f"responses({len(responses)}) 应比 requests({len(requests)}) 少 1")
    return errs


def setup_replay_log(match_id: str) -> logging.Logger:
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"fetch_match_{match_id}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8", mode="w"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return logging.getLogger("fetch_match")


def replay(match_id: str, requests: list, responses: list, player: int) -> int:
    """逐回合全量重放：对每个前缀 (reqs[:k+1], resps[:k]) 决策一次。

    复用 adapter.handle_online_turn_sync 的全量重放语义（每回合决策时
    重新喂入截至该回合的全部请求重建状态），每次决策用新的 adapter 实例
    保证状态干净；引擎加载一次复用。返回完成的决策回合数。
    """
    from src.communication.botzone_adapter import BotzoneAdapter
    from src.v.nn import UltimateWinRateEngineV7

    logger = setup_replay_log(match_id)
    engine = UltimateWinRateEngineV7(player_id=player, use_grouping_engine=True)

    done = 0
    for k in range(len(requests)):
        full_input = {
            "requests": requests[: k + 1],
            "responses": responses[:k],
        }
        adapter = BotzoneAdapter(
            user_id="replay", api_key="", decision_engine=engine, player_id=player,
        )
        try:
            resp = adapter.handle_online_turn_sync(full_input)
        except Exception as e:
            logger.error("重放回合 %d 异常: %s", k, e, exc_info=True)
            resp = None
        if resp is not None:
            logger.info("重放回合 %d 决策: %s", k, resp)
            done += 1
    logger.info("重放完成: %d/%d 回合", done, len(requests))
    return done


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print(f"[拉取] match={args.match} player={args.player} ...")
    data = fetch_match_data(args.match)
    status = data.get("status")
    success = data.get("success")
    print(f"[拉取] status={status} success={success} logs={len(data.get('logs') or [])} 条")
    if not success:
        print("[错误] 平台返回 success=false，对局可能不存在或尚未完成")
        return 2

    requests, responses = extract_player_stream(data.get("logs") or [], args.player)
    print(f"[解析] 玩家 {args.player}: requests={len(requests)} responses={len(responses)}")

    if not args.no_verify:
        errs = validate_stream(requests, responses)
        if errs:
            print("[错误] 校验失败:")
            for e in errs:
                print("   -", e)
            return 3

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "match_id": args.match,
            "player": args.player,
            "status": status,
            "players": data.get("players"),
            "requests": requests,
            "responses": responses,
        }
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        print(f"[保存] {out_path}")

    if args.replay:
        print(f"[重放] 逐回合本地重放（日志 logs/fetch_match_{args.match}.log）...")
        done = replay(args.match, requests, responses, args.player)
        print(f"[重放] {done}/{len(requests)} 回合完成")
        print(f"[重放] 决策链日志: {project_root / 'logs' / f'fetch_match_{args.match}.log'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
