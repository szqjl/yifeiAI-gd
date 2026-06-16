# -*- coding: utf-8 -*-
"""gameResult / victoryNum 解析与批级校验（GUA-033，对齐 v1006 final 字段）。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def extract_victory_num_from_game_result(data: dict) -> List[int]:
    """
    从 gameResult 通知提取批末 victoryNum。
    优先 v1006 顶层 ``final``，其次 ``victoryNum`` / result 字典。
    禁止从 episodeOver 的 result 列表 index 4 取值。
    """
    if not isinstance(data, dict):
        return []

    final = data.get("final")
    if isinstance(final, list) and len(final) >= 4:
        return [int(x) for x in final[:4]]

    top_vn = data.get("victoryNum")
    if isinstance(top_vn, list) and len(top_vn) >= 4:
        return [int(x) for x in top_vn[:4]]

    result = data.get("result", {})
    if isinstance(result, dict):
        vn = result.get("victoryNum")
        if isinstance(vn, list) and len(vn) >= 4:
            return [int(x) for x in vn[:4]]
        batch_final = result.get("final")
        if isinstance(batch_final, list) and len(batch_final) >= 4:
            return [int(x) for x in batch_final[:4]]

    return []


def validate_batch_victory_num(
    victory_num: List[int],
    expected_batch_games: Optional[int] = None,
) -> Tuple[bool, str]:
    """校验批末 victoryNum：同队 [0]=[2]、[1]=[3]，且 [0]+[1]==batch_games。"""
    if not isinstance(victory_num, list) or len(victory_num) < 4:
        return False, "victoryNum 长度不足 4"

    try:
        vn = [int(x) for x in victory_num[:4]]
    except (TypeError, ValueError):
        return False, "victoryNum 含非整数"

    if vn[0] != vn[2] or vn[1] != vn[3]:
        return False, "同队不一致: [0]={},[2]={}, [1]={},[3]={}".format(
            vn[0], vn[2], vn[1], vn[3]
        )

    team_total = vn[0] + vn[1]
    if expected_batch_games is not None and team_total != expected_batch_games:
        return False, "[0]+[1]={} != batch_games={}".format(team_total, expected_batch_games)

    return True, ""


def resolve_expected_batch_games(
    setting_times: Optional[int] = None,
    project_root: Optional[Path] = None,
) -> Optional[int]:
    """合并 batch_executor 批文件、环境变量、gameOver.settingTimes（末位 fallback）。"""
    root = project_root or Path(__file__).resolve().parent.parent.parent

    batch_file = root / "batch_executor" / "current_batch.json"
    if batch_file.exists():
        try:
            payload = json.loads(batch_file.read_text(encoding="utf-8"))
            bg = payload.get("batch_games")
            if bg is not None:
                return int(bg)
        except (json.JSONDecodeError, TypeError, ValueError, OSError):
            pass

    env_val = os.environ.get("BATCH_GAMES")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            pass

    if setting_times is not None:
        try:
            return int(setting_times)
        except (TypeError, ValueError):
            pass

    return None


def build_local_batch_victory_num(team_a_wins: int, team_b_wins: int) -> List[int]:
    """由本批队胜计数构造 victoryNum。"""
    return [team_a_wins, team_b_wins, team_a_wins, team_b_wins]


def build_latest_victory_num_payload(
    victory_num: List[int],
    batch_games: Optional[int] = None,
    *,
    server_vn_raw: Optional[List[int]] = None,
    vn_source: str = "server",
    player: str = "yf1_m3",
) -> Dict[str, Any]:
    """构造 batch_executor/latest_victory_num.json 内容（含对账字段）。"""
    from datetime import datetime

    payload: Dict[str, Any] = {
        "victoryNum": victory_num,
        "batch_games": batch_games,
        "vn_source": vn_source,
        "timestamp": datetime.now().isoformat(),
        "player": player,
    }
    if server_vn_raw is not None:
        payload["server_vn_raw"] = server_vn_raw
    return payload


def build_game_result_payload(data: dict) -> dict:
    """构造写入 game_records 的 result 字典。"""
    victory_num = extract_victory_num_from_game_result(data)
    payload: Dict[str, Any] = {}
    if victory_num:
        payload["victoryNum"] = victory_num
    draws = data.get("draws")
    if isinstance(draws, list):
        payload["draws"] = draws
    return payload
