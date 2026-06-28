# -*- coding: utf-8 -*-
"""
V7 调试 GUI — 牌谱录入 → 组局展示 → 模拟对手出牌 → V7 应对决策

用法：
  python tests/debug_v7_gui.py
  然后浏览器打开 http://127.0.0.1:5000
"""

import sys
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, jsonify, render_template_string, send_from_directory

# ── 日志 ──────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("debug_v7_gui")
logger.setLevel(logging.DEBUG)

# ── 导入 V7 引擎和辅助 ────────────────────────────────
from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7
from src.v.nn.guards.v7_guards import (
    get_action_type, get_action_rank, get_card_rank, get_card_value,
    ACTION_TYPE_PASS, ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR,
    ACTION_TYPE_TRIPS, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
    ACTION_TYPE_THREE_PAIR, ACTION_TYPE_TWO_TRIPS, ACTION_TYPE_THREE_WITH_TWO,
    ACTION_TYPE_STRAIGHT, ACTION_TYPE_FREE,
    CARD_RANK_ORDER, SUITS,
)
from tests.debug_v7_single_hand import (
    generate_action_list, build_game_state,
    make_action, PASS_ACTION,
)

# ── 常量 ──────────────────────────────────────────────
TYPE_LABELS = {
    "PASS": "过",
    "Single": "单张", "Pair": "对子", "Trips": "三张",
    "Bomb": "炸弹", "StraightFlush": "同花顺", "Straight": "顺子",
    "ThreePair": "三连对", "TwoTrips": "钢板", "ThreeWithTwo": "三带二",
}

app = Flask(__name__)

# 静态资源路由（大小王图片）
@app.route("/assets/<path:filename>")
def static_files(filename):
    return send_from_directory(str(PROJECT_ROOT / "assets" / "replay"), filename)

# ── 全局引擎实例（单例，复用 MemoryTracker） ─────────
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = UltimateWinRateEngineV7(player_id=0)
    return _engine

def _count_groups(plan):
    """计算牌组数量。"""
    if plan is None:
        return 0
    return (len(plan.bombs) + len(plan.straight_flushes) + len(plan.straights)
            + len(plan.trips) + len(plan.pairs) + len(plan.three_pairs)
            + len(plan.three_with_twos) + len(plan.steel_plates))

# ═══════════════════════════════════════════════════════
#  API 端点
# ═══════════════════════════════════════════════════════

@app.route("/api/grouping", methods=["POST"])
def api_grouping():
    """分析手牌组局。"""
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": f"JSON解析失败: {e}"}), 400

    hand_cards = data.get("hand_cards", [])
    cur_rank = data.get("cur_rank", "2")

    if not hand_cards:
        return jsonify({"error": "请录入手牌"}), 400

    try:
        engine = get_engine()
        # 重置引擎状态以处理新手牌
        engine._last_hand_hash = -1
        engine._tracker_initialized = False
        engine._tracker = None

        gs = {
            "handCards": hand_cards,
            "curRank": cur_rank,
            "myPos": 0,
            "actionList": [],
            "history": [],
            "recentPlays": [],
            "publicInfo": [{"rest": 27}, {"rest": 27}, {"rest": 27}, {"rest": 27}],
            "greaterAction": ["PASS", "", []],
            "curAction": ["PASS", "", []],
            "curPos": 0,
            "greaterPos": 0,
            "stage": "play",
            "selfRank": cur_rank,
            "oppoRank": cur_rank,
            "curBombNum": 0,
            "numofplayers": [27, 27, 27, 27],
        }

        engine._run_grouping_engine(gs)
    except Exception as e:
        logger.error(f"Grouping engine error: {e}", exc_info=True)
        return jsonify({"error": f"组局引擎失败: {e}"}), 500

    plan = engine._best_plan
    role = engine._current_role or "未知"

    result = {
        "role": role,
        "hand_count": len(hand_cards),
        "groups": {},
        "raw_groups": {},
    }

    if plan is not None:
        d = plan.to_dict()
        # 按牌型分组，每组列出具体牌
        for type_name, groups in d.items():
            if not groups:
                continue
            label = TYPE_LABELS.get(type_name, type_name)
            formatted = []
            raw_list = []
            for g in groups:
                if isinstance(g, list) and g and isinstance(g[0], list):
                    # 嵌套列表（如 ThreeWithTwo: [[trip], [pair]]）
                    flat = []
                    for sub in g:
                        flat.extend(sub)
                    formatted.append(format_cards(flat))
                    raw_list.append(list(flat))
                else:
                    formatted.append(format_cards(g))
                    raw_list.append(list(g) if isinstance(g, (list, tuple)) else [g])
            result["groups"][label] = formatted
            result["raw_groups"][label] = raw_list
        result["total_groups"] = _count_groups(plan)
        result["total_rounds"] = plan.num_rounds()

    # 散牌
    singles = []
    if plan is not None and plan.singles:
        singles = plan.singles
    if singles:
        result["singles"] = format_cards(singles)

    return jsonify(result)


@app.route("/api/decide", methods=["POST"])
def api_decide():
    """V7 应对对手出牌。"""
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": f"JSON解析失败: {e}"}), 400

    hand_cards = data.get("hand_cards", [])
    opponent_action = data.get("opponent_action")
    cur_rank = data.get("cur_rank", "2")
    my_pos = data.get("my_pos", 0)

    if not hand_cards:
        return jsonify({"error": "请录入手牌"}), 400
    if not opponent_action:
        opponent_action = PASS_ACTION

    try:
        engine = get_engine()
        engine._last_hand_hash = -1
        engine._tracker_initialized = False
        engine._tracker = None

        # 构造 game_state
        gs = build_game_state(
            hand=hand_cards,
            greater_action=opponent_action,
            my_pos=my_pos,
            cur_pos=(my_pos + 1) % 4,
            greater_pos=(my_pos + 1) % 4,
            cur_rank=cur_rank,
        )

        result_idx = engine.decide(gs)
    except Exception as e:
        logger.error(f"Decide error: {e}", exc_info=True)
        return jsonify({"error": f"决策失败: {e}"}), 500

    act_list = gs["actionList"]
    result_action = act_list[result_idx] if 0 <= result_idx < len(act_list) else None

    result = {
        "action_index": result_idx,
        "action": None,
        "role": engine._current_role or "未知",
        "guard_filtered": engine.guard_filtered_count,
        "guard_override": engine.guard_override_count,
        "group_filtered": engine.group_filtered_count,
        "heuristic_decisions": engine.heuristic_decisions,
        "candidate_count": len(act_list),
    }

    if result_action:
        a_type = result_action[0] if isinstance(result_action, list) and result_action else "?"
        a_rank = result_action[1] if isinstance(result_action, list) and len(result_action) >= 2 else ""
        a_cards = result_action[2] if isinstance(result_action, list) and len(result_action) >= 3 else []
        result["action"] = {
            "type": a_type,
            "type_label": TYPE_LABELS.get(a_type, a_type),
            "rank": a_rank,
            "cards": a_cards,
            "cards_display": format_cards(a_cards) if a_cards else "PASS",
        }

    # 组局信息
    plan = engine._best_plan
    if plan is not None:
        d = plan.to_dict()
        groups = {}
        raw_groups = {}
        for type_name, groups_list in d.items():
            if not groups_list:
                continue
            label = TYPE_LABELS.get(type_name, type_name)
            formatted = []
            raw_list = []
            for g in groups_list:
                if isinstance(g, list) and g and isinstance(g[0], list):
                    flat = []
                    for sub in g:
                        flat.extend(sub)
                    formatted.append(format_cards(flat))
                    raw_list.append(list(flat))
                else:
                    formatted.append(format_cards(g))
                    raw_list.append(list(g) if isinstance(g, (list, tuple)) else [g])
            groups[label] = formatted
            raw_groups[label] = raw_list
        result["groups"] = groups
        result["raw_groups"] = raw_groups
        result["total_groups"] = _count_groups(plan)
        result["total_rounds"] = plan.num_rounds()

    return jsonify(result)


# ── 辅助 ──────────────────────────────────────────────

SUIT_SYMBOLS = {"S": "♠", "H": "♥", "C": "♣", "D": "♦"}
RANK_DISPLAY = {
    "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7",
    "8": "8", "9": "9", "T": "10", "J": "J", "Q": "Q", "K": "K", "A": "A",
    "SB": "🃏", "HR": "👑",
}

def format_cards(cards: List[str]) -> str:
    """格式化卡牌列表为人可读字符串。"""
    if not cards:
        return ""
    parts = []
    for c in cards:
        if c in ("SB", "HR"):
            parts.append(RANK_DISPLAY.get(c, c))
        elif len(c) >= 2:
            suit = SUIT_SYMBOLS.get(c[0], c[0])
            rank = RANK_DISPLAY.get(c[1:], c[1:])
            parts.append(f"{suit}{rank}")
        else:
            parts.append(c)
    return " ".join(parts)

# ═══════════════════════════════════════════════════════
#  HTML 前端
# ═══════════════════════════════════════════════════════

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>V7 行牌决策调试器</title>
<style>
  :root {
    --felt: #0d5e2e;
    --felt-dark: #0a4522;
    --gold: #d4a843;
    --gold-light: #f0d68a;
    --card-white: #faf9f6;
    --card-red: #c0392b;
    --card-black: #1a1a1a;
    --text: #e8e6e0;
    --text-dim: #a8a69e;
    --panel-bg: rgba(0,0,0,0.35);
    --panel-border: rgba(212,168,67,0.25);
    --accent-red: #e74c3c;
    --accent-blue: #3498db;
    --accent-green: #2ecc71;
    --font-display: 'Georgia', 'Songti SC', 'SimSun', serif;
    --font-body: 'Palatino', 'Georgia', 'KaiTi', serif;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: var(--font-body);
    background: radial-gradient(ellipse at center, #0f6b35 0%, #083d1e 40%, #052410 100%);
    color: var(--text);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* 牌桌纹理 */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.02'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 20px;
    position: relative;
    z-index: 1;
  }

  /* 标题 */
  .header {
    text-align: center;
    margin-bottom: 28px;
  }
  .header h1 {
    font-family: var(--font-display);
    font-size: 2.2rem;
    color: var(--gold-light);
    text-shadow: 0 2px 8px rgba(0,0,0,0.5);
    letter-spacing: 0.04em;
  }
  .header .subtitle {
    color: var(--text-dim);
    font-size: 0.9rem;
    margin-top: 4px;
  }

  /* 主布局 */
  .main-grid {
    display: grid;
    grid-template-columns: 1fr 2fr;
    grid-template-rows: auto auto auto;
    gap: 16px;
  }

  /* 面板 */
  .panel {
    background: var(--panel-bg);
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    padding: 16px;
    backdrop-filter: blur(4px);
  }
  .panel-header {
    font-family: var(--font-display);
    font-size: 1rem;
    color: var(--gold);
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(212,168,67,0.2);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .panel-header .icon {
    font-size: 1.1rem;
  }
  .panel-header .header-stats {
    margin-left: auto;
    display: flex;
    gap: 10px;
    font-size: 0.78rem;
    color: var(--text-dim);
    font-family: var(--font-body);
  }
  .panel-header .header-stats span {
    white-space: nowrap;
  }

  /* 牌谱输入 */
  .panel-hand { grid-column: 1; grid-row: 1; }
  .panel-opponent { grid-column: 1; grid-row: 2; }

  /* 右侧堆叠容器：原始手牌/最优组局/V7应对 紧凑纵向排列 */
  .right-stack {
    grid-column: 2; grid-row: 1 / 3;
    display: flex; flex-direction: column; gap: 16px;
  }
  .right-stack .panel { margin: 0; }  /* 清除面板可能的 margin */

  textarea, select, input {
    font-family: var(--font-body);
    background: rgba(0,0,0,0.4);
    border: 1px solid rgba(212,168,67,0.3);
    color: var(--text);
    padding: 10px 12px;
    border-radius: 6px;
    font-size: 0.95rem;
    width: 100%;
    transition: border-color 0.2s;
  }
  textarea { resize: vertical; min-height: 70px; }
  textarea:focus, select:focus, input:focus {
    outline: none;
    border-color: var(--gold);
    box-shadow: 0 0 0 2px rgba(212,168,67,0.15);
  }

  .input-row {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
    align-items: center;
  }
  .input-row select { flex: 1; }
  .input-row input { flex: 2; }
  .input-row .rank-select { flex: 1; }

  label {
    display: block;
    font-size: 0.85rem;
    color: var(--text-dim);
    margin-bottom: 4px;
  }

  /* 按钮 */
  .btn {
    font-family: var(--font-display);
    padding: 10px 24px;
    border: 1px solid var(--gold);
    background: linear-gradient(180deg, rgba(212,168,67,0.2), rgba(212,168,67,0.08));
    color: var(--gold-light);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.95rem;
    transition: all 0.2s;
    white-space: nowrap;
  }
  .btn:hover {
    background: linear-gradient(180deg, rgba(212,168,67,0.35), rgba(212,168,67,0.15));
    box-shadow: 0 0 12px rgba(212,168,67,0.2);
  }
  .btn-primary {
    background: linear-gradient(180deg, rgba(212,168,67,0.4), rgba(212,168,67,0.2));
    border-color: var(--gold-light);
    font-weight: bold;
  }
  .btn-small {
    padding: 6px 16px;
    font-size: 0.82rem;
  }

  /* 卡牌展示 */
  .cards-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin: 8px 0;
  }
  .card-tag {
    background: var(--card-white);
    color: var(--card-black);
    padding: 4px 9px;
    border-radius: 4px;
    font-family: var(--font-display);
    font-size: 0.9rem;
    font-weight: bold;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    border: 1px solid #ccc;
    display: inline-flex;
    align-items: center;
    gap: 2px;
  }
  .card-tag.red { color: var(--card-red); }
  .card-tag.joker-small { background: linear-gradient(135deg, #e8e8e8, #b0b0b0); color: #333; }
  .card-tag.joker-big { background: linear-gradient(135deg, #ffe0e0, #ff8888); color: #800; }
  .card-tag.pass {
    background: rgba(255,255,255,0.1);
    color: var(--text-dim);
    border: 1px dashed var(--panel-border);
    font-style: italic;
    box-shadow: none;
  }

  /* 组局展示 - 横排按点数排列 */
  .hand-table {
    display: flex;
    gap: 4px;
    overflow-x: auto;
    padding: 6px 0 10px;
    align-items: flex-end;
  }
  .rank-column {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 36px;
    gap: 1px;
  }
  .rank-header {
    font-size: 0.82rem;
    font-weight: bold;
    color: var(--gold-light);
    margin-bottom: 3px;
    font-family: var(--font-display);
    text-align: center;
    width: 100%;
    padding: 2px 0;
    background: rgba(0,0,0,0.25);
    border-radius: 3px;
  }
  .rank-cell {
    width: 34px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 3px;
    font-size: 0.74rem;
    font-family: var(--font-display);
    font-size: 0.82rem;
    font-weight: bold;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
    border: 1.5px solid rgba(255,255,255,0.25);
    background: var(--card-white);
    color: var(--card-black);
  }
  .rank-cell.red { color: var(--card-red); }
  .rank-cell.in-bomb {
    border: 2px solid var(--accent-red);
    box-shadow: 0 0 6px rgba(231,76,60,0.35);
  }
  .rank-cell.in-sfl {
    border: 2px solid #e67e22;
    box-shadow: 0 0 6px rgba(230,126,34,0.35);
  }
  .rank-cell.in-straight {
    border: 2px solid var(--accent-blue);
    box-shadow: 0 0 6px rgba(52,152,219,0.35);
  }
  .rank-cell.in-three {
    border: 2px solid #9b59b6;
    box-shadow: 0 0 6px rgba(155,89,182,0.35);
  }
  .rank-cell.in-pair {
    border-style: dashed;
    border-color: var(--gold);
  }
  .rank-cell.joker-cell {
    background: rgba(0,0,0,0.08);
    border-color: #999;
  }
  .rank-cell.joker-big-cell {
    background: rgba(200,0,0,0.08);
    border-color: #c66;
  }

  /* 组局分组显示 — 横排一行 */
  .grouping-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: flex-start;
  }
  .group-block {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,255,255,0.04);
    border-radius: 6px;
    padding: 5px 8px;
    border: 1.5px solid rgba(255,255,255,0.1);
  }
  .group-block-label {
    font-size: 0.75rem;
    white-space: nowrap;
    padding-right: 4px;
    border-right: 1px solid rgba(255,255,255,0.15);
  }
  .group-block-rows {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .group-block .card-cluster {
    display: inline-flex;
    gap: 1px;
    background: rgba(0,0,0,0.18);
    padding: 2px 5px;
    border-radius: 4px;
    border: 1px solid rgba(255,255,255,0.08);
  }
  .group-block .card-cluster .rank-cell {
    font-size: 0.72rem;
    min-width: 20px;
    min-height: 22px;
  }

  /* 旧样式保留但不使用 */
  .group-summary {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid rgba(212,168,67,0.2);
  }
  .group-chip {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    border: 1px solid;
    white-space: nowrap;
  }
  .group-chip.bomb-chip { color: var(--accent-red); border-color: rgba(231,76,60,0.4); background: rgba(231,76,60,0.1); }
  .group-chip.sfl-chip { color: #e67e22; border-color: rgba(230,126,34,0.4); background: rgba(230,126,34,0.1); }
  .group-chip.straight-chip { color: var(--accent-blue); border-color: rgba(52,152,219,0.4); background: rgba(52,152,219,0.1); }
  .group-chip.three-chip { color: #9b59b6; border-color: rgba(155,89,182,0.4); background: rgba(155,89,182,0.1); }
  .group-chip.pair-chip { color: var(--gold); border-color: rgba(212,168,67,0.4); background: rgba(212,168,67,0.1); }
  .group-chip.single-chip { color: var(--text-dim); border-color: rgba(168,166,158,0.3); background: rgba(168,166,158,0.06); }

  /* 角色标签 */
  .role-badge {
    float: right;
    font-size: 0.82rem;
    padding: 2px 12px;
    border-radius: 12px;
    background: rgba(212,168,67,0.2);
    color: var(--gold-light);
    border: 1px solid rgba(212,168,67,0.4);
  }
  .role-badge.main { background: rgba(231,76,60,0.2); color: #e74c3c; border-color: rgba(231,76,60,0.4); }
  .role-badge.support { background: rgba(52,152,219,0.2); color: #3498db; border-color: rgba(52,152,219,0.4); }

  /* 决策结果 - 紧凑横向 */
  .decision-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: rgba(0,0,0,0.25);
    border-radius: 6px;
    flex-wrap: wrap;
  }
  .decision-bar .decision-text {
    font-family: var(--font-display);
    font-size: 0.9rem;
    color: var(--gold-light);
    white-space: nowrap;
  }
  .decision-bar .decision-cards-row {
    display: flex;
    gap: 3px;
    flex-wrap: wrap;
  }
  .decision-bar .card-tag {
    font-size: 0.85rem;
    padding: 3px 8px;
  }
  .decision-bar .card-tag.pass {
    font-style: italic;
    color: var(--text-dim);
  }
  .decision-meta {
    margin-left: auto;
    display: flex;
    gap: 8px;
    font-size: 0.72rem;
    color: var(--text-dim);
    flex-wrap: wrap;
  }
  .decision-meta span {
    white-space: nowrap;
    background: rgba(0,0,0,0.2);
    padding: 1px 6px;
    border-radius: 3px;
  }

  /* 统计信息 */
  .stat-row {
    display: flex;
    gap: 16px;
    margin-top: 8px;
    font-size: 0.82rem;
    color: var(--text-dim);
    flex-wrap: wrap;
  }
  .stat-item {
    padding: 3px 8px;
    background: rgba(0,0,0,0.2);
    border-radius: 4px;
  }

  /* 预设场景 */
  .presets {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 8px;
  }
  .preset-btn {
    padding: 5px 12px;
    font-size: 0.78rem;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.15);
    color: var(--text-dim);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .preset-btn:hover {
    background: rgba(212,168,67,0.15);
    border-color: rgba(212,168,67,0.4);
    color: var(--gold-light);
  }

  /* 加载/错误 */
  .loading {
    text-align: center;
    padding: 20px;
    color: var(--text-dim);
  }
  .error-msg {
    color: var(--accent-red);
    padding: 10px;
    background: rgba(231,76,60,0.1);
    border-radius: 6px;
    font-size: 0.9rem;
  }
  .empty-state {
    text-align: center;
    color: var(--text-dim);
    padding: 30px;
    font-style: italic;
  }

  /* 提示 */
  .tip {
    font-size: 0.78rem;
    color: var(--text-dim);
    margin-top: 4px;
    font-style: italic;
  }

  @media (max-width: 768px) {
    .main-grid { grid-template-columns: 1fr; }
    .panel-hand, .panel-opponent, .right-stack {
      grid-column: 1;
    }
    .right-stack { grid-row: auto; }
  }
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <h1>♢ V7 行牌决策调试器 ♢</h1>
    <div class="subtitle">牌谱录入 → 最优组局 → 模拟对手 → V7 应对决策</div>
  </div>

  <div class="main-grid">

    <!-- 1. 牌谱录入 -->
    <div class="panel panel-hand">
      <div class="panel-header"><span class="icon">🂠</span> 手牌录入</div>
      <label>手牌（空格分隔，如 S3 H3 D4 C5 SB HR）</label>
      <textarea id="handInput" placeholder="粘贴手牌，如：S3 H3 D3 C3 H5 S5 D6 C6 H7 S7 D8 C8 H9 S9 DT CT HJ SJ DJ CJ HQ SQ HA SA"></textarea>
      <div class="input-row" style="margin-top:8px;">
        <label style="margin:0;" for="curRank">级牌:</label>
        <select id="curRank" style="width:80px;">
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4</option>
          <option value="5">5</option>
          <option value="6">6</option>
          <option value="7">7</option>
          <option value="8">8</option>
          <option value="9">9</option>
          <option value="T">10</option>
          <option value="J">J</option>
          <option value="Q">Q</option>
          <option value="K">K</option>
          <option value="A">A</option>
        </select>
        <button class="btn" onclick="randomDeal()" title="随机生成一副手牌" style="padding:8px 12px; font-size:0.78rem;">🎲 随机发牌</button>
        <button class="btn btn-primary" onclick="analyzeHand()" style="margin-left:auto;">组局</button>
      </div>

      <div style="margin-top:10px; font-size:0.82rem; color:var(--text-dim);">预设场景：</div>
      <div class="presets">
        <button class="preset-btn" onclick="loadPreset('pair')">对子压制</button>
        <button class="preset-btn" onclick="loadPreset('bomb')">炸弹+散张</button>
        <button class="preset-btn" onclick="loadPreset('lead')">领出起手</button>
        <button class="preset-btn" onclick="loadPreset('mixed')">混合牌型</button>
      </div>
    </div>

    <!-- 右侧堆叠：原始手牌 → 最优组局 → V7 应对 -->
    <div class="right-stack">

    <div class="panel panel-raw-hand">
      <div class="panel-header">
        <span class="icon">🂠</span> 原始手牌
        <div class="header-stats">
          <span id="rawHandCount">0 张</span>
        </div>
      </div>
      <div id="rawHandResult">
        <div class="empty-state">请输入手牌后点击「组局」</div>
      </div>
    </div>

    <div class="panel panel-grouping">
      <div class="panel-header">
        <span class="icon">📊</span> 最优组局
        <span id="groupingRole" class="role-badge" style="display:none;"></span>
        <div class="header-stats" id="groupingStats" style="display:none;"></div>
      </div>
      <div id="groupingResult">
        <div class="empty-state">请先录入牌谱并点击「组局」</div>
      </div>
    </div>

    <div class="panel panel-result">
      <div class="panel-header">
        <span class="icon">🤖</span> V7 应对
        <span id="resultRole" class="role-badge" style="display:none;"></span>
      </div>
      <div id="decisionResult">
        <div class="empty-state">请录入对手出牌并点击「对手出牌」</div>
      </div>
    </div>

    </div><!-- /right-stack -->

    <!-- 3. 模拟对手出牌 -->
    <div class="panel panel-opponent">
      <div class="panel-header"><span class="icon">🎯</span> 模拟对手出牌</div>
      <label>牌型</label>
      <div class="input-row">
        <select id="oppType">
          <option value="Single">单张</option>
          <option value="Pair">对子</option>
          <option value="Trips">三张</option>
          <option value="Straight">顺子(5+)</option>
          <option value="StraightFlush">同花顺(5+)</option>
          <option value="ThreePair">三连对</option>
          <option value="TwoTrips">钢板</option>
          <option value="ThreeWithTwo">三带二</option>
          <option value="Bomb">炸弹</option>
          <option value="PASS">让牌(对手领出)</option>
        </select>
      </div>
      <label>点数（单张/对子/三张用，如 A, K, Q, 2；顺子/同花顺填起始点数；炸弹/钢板不填自动生成）</label>
      <div class="input-row">
        <input type="text" id="oppRank" placeholder="如: A">
        <button class="btn" onclick="opponentPlay()" style="margin-left:auto;">对手出牌 → V7 应对</button>
      </div>
      <div id="opponentPreview" style="margin-top:6px; font-size:0.85rem; color:var(--text-dim);"></div>
    </div>

  </div>
</div>

<script>
  let currentHand = null;
  let currentRank = "2";

  function getHandInput() {
    const raw = document.getElementById('handInput').value.trim();
    if (!raw) return [];
    return raw.split(/\s+/).filter(s => s.length > 0);
  }

  function getCurRank() {
    return document.getElementById('curRank').value || "2";
  }

  // ── 预设场景 ────────────────────────────────────────

  const PRESETS = {
    pair: {
      hand: "S5 H5 D5 C5 SA HA DK CK DQ CQ H7 S3 D9 CJ HT SB",
      oppType: "Pair",
      oppRank: "Q",
      desc: "对手出对Q — 我有对K对A但选了炸弹"
    },
    bomb: {
      hand: "S3 H3 D3 C3 SK HK DK CK SA HA DQ CJ HT D9 C8 SB",
      oppType: "Single",
      oppRank: "T",
      desc: "对手出单T — 看会不会浪费炸弹"
    },
    lead: {
      hand: "S3 H3 D3 C3 SK HK SA HA DQ CQ CJ HJ HT D9 C8 S7 SB HR",
      oppType: "PASS",
      oppRank: "",
      desc: "我领出 — 看V7选什么牌型起手"
    },
    mixed: {
      hand: "S8 H8 D8 C8 SK HK DK CK SA HA DQ CQ CJ D9 S7 HT D6 SB HR",
      oppType: "Single",
      oppRank: "A",
      desc: "对手出单A — 是否用小王应对"
    },
  };

  function loadPreset(name) {
    const p = PRESETS[name];
    if (!p) return;
    document.getElementById('handInput').value = p.hand;
    document.getElementById('oppType').value = p.oppType;
    document.getElementById('oppRank').value = p.oppRank;
    document.getElementById('opponentPreview').innerHTML = `<em>${p.desc}</em>`;
    currentHand = p.hand.split(/\s+/);
    currentRank = getCurRank();
    renderRawHand();
  }

  // ── 原始手牌渲染 ────────────────────────────────────

  function renderRawHand() {
    const cards = currentHand || [];
    document.getElementById('rawHandCount').textContent = `${cards.length} 张`;

    if (!cards.length) {
      document.getElementById('rawHandResult').innerHTML =
        '<div class="empty-state">请输入手牌</div>';
      return;
    }

    const cardMap = buildCardMap(cards);
    let html = '<div class="hand-table">';
    for (const r of RANK_ORDER) {
      const cardsOfRank = cardMap[r];
      if (!cardsOfRank || cardsOfRank.length === 0) continue;
      html += `<div class="rank-column">`;
      for (const p of cardsOfRank) {
        html += renderCardCellSimple(p);
      }
      html += `</div>`;
    }
    html += '</div>';
    document.getElementById('rawHandResult').innerHTML = html;
  }

  function renderCardCellSimple(p) {
    let cls = 'rank-cell';
    const isRed = p.suit === '♥' || p.suit === '♦';
    if (isRed) cls += ' red';

    if (p.rank === 'B') {
      return `<span class="${cls}"><img src="/assets/joker_small.png" alt="小王" style="width:38px;height:24px;vertical-align:middle;"></span>`;
    } else if (p.rank === 'R') {
      return `<span class="${cls}"><img src="/assets/joker_big.png" alt="大王" style="width:38px;height:24px;vertical-align:middle;"></span>`;
    } else {
      const rankDisplay = p.rank === 'T' ? '10' : p.rank;
      return `<span class="${cls}">${p.suit}${rankDisplay}</span>`;
    }
  }

  // ── 分析牌谱 ────────────────────────────────────────

  async function analyzeHand() {
    currentHand = getHandInput();
    currentRank = getCurRank();
    if (!currentHand.length) {
      document.getElementById('groupingResult').innerHTML =
        '<div class="error-msg">请输入手牌</div>';
      return;
    }

    // 先显示原始手牌
    renderRawHand();

    document.getElementById('groupingResult').innerHTML =
      '<div class="loading">⏳ 组牌引擎计算中...</div>';

    try {
      const resp = await fetch('/api/grouping', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({hand_cards: currentHand, cur_rank: currentRank}),
      });
      const data = await resp.json();

      if (data.error) {
        document.getElementById('groupingResult').innerHTML =
          `<div class="error-msg">${data.error}</div>`;
        return;
      }

      saveHand();  // 记住本次手牌
      renderGrouping(data);
    } catch (e) {
      document.getElementById('groupingResult').innerHTML =
        `<div class="error-msg">网络错误: ${e.message}</div>`;
    }
  }

  // ── localStorage 记忆上次手牌 ──────────────────────────
  const LS_KEY = 'v7debug_last_hand';
  function saveHand() {
    const raw = document.getElementById('handInput').value.trim();
    const rank = document.getElementById('curRank').value;
    if (raw) {
      localStorage.setItem(LS_KEY, JSON.stringify({hand: raw, rank: rank}));
    }
  }
  function restoreHand() {
    try {
      const saved = JSON.parse(localStorage.getItem(LS_KEY));
      if (saved && saved.hand) {
        document.getElementById('handInput').value = saved.hand;
        if (saved.rank) document.getElementById('curRank').value = saved.rank;
        currentHand = saved.hand.split(/\s+/);
        currentRank = saved.rank || '2';
        renderRawHand();
      }
    } catch(e) { /* ignore */ }
  }

  // ── 随机发牌 ──────────────────────────────────────────
  function randomDeal() {
    const suits = ['S','H','C','D'];
    const ranks = ['2','3','4','5','6','7','8','9','T','J','Q','K','A'];
    // 一副牌 54 张（含 2 张王），随机取 27 张
    let deck = [];
    for (const r of ranks) {
      for (const s of suits) {
        deck.push(s + r);
      }
    }
    deck.push('SB'); // 小王
    deck.push('HR'); // 大王
    // Fisher-Yates 洗牌
    for (let i = deck.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [deck[i], deck[j]] = [deck[j], deck[i]];
    }
    const hand = deck.slice(0, 27);
    // 按点数排序
    const rankOrder = {'2':1,'3':2,'4':3,'5':4,'6':5,'7':6,'8':7,'9':8,'T':9,'J':10,'Q':12,'K':13,'A':14};
    hand.sort((a,b) => {
      const ra = a.slice(1), rb = b.slice(1);
      if (ra === 'H' || ra === 'B') return 1;
      if (rb === 'H' || rb === 'B') return -1;
      return (rankOrder[ra]||0) - (rankOrder[rb]||0) || a[0].localeCompare(b[0]);
    });
    document.getElementById('handInput').value = hand.join(' ');
    currentHand = hand;
    currentRank = getCurRank();
    renderRawHand();
    saveHand();
  }

  function renderGrouping(data) {
    const roleEl = document.getElementById('groupingRole');
    roleEl.style.display = 'inline-block';
    let roleClass = '';
    if (data.role.includes('主攻') || data.role.includes('强主')) roleClass = 'main';
    else roleClass = 'support';
    roleEl.className = `role-badge ${roleClass}`;
    roleEl.textContent = data.role;

    const statsEl = document.getElementById('groupingStats');
    if (data.total_groups) {
      statsEl.style.display = 'flex';
      statsEl.innerHTML = `<span>牌组: ${data.total_groups}</span><span>轮次: ${data.total_rounds}</span><span>手牌: ${data.hand_count}张</span>`;
    } else {
      statsEl.style.display = 'none';
    }

    const groups = data.raw_groups || data.groups;
    if (!groups || Object.keys(groups).length === 0) {
      document.getElementById('groupingResult').innerHTML =
        '<div class="empty-state">组队结果为空</div>';
      return;
    }

    let html = '<div class="grouping-row">';

    for (const type of GROUP_PRIORITY) {
      const items = groups[type];
      if (!items || !items.length) continue;

      const color = GROUP_COLORS[type] || { border: '#888', bg: 'rgba(136,136,136,0.06)' };
      const borderColor = color.border;

      html += `<div class="group-block" style="border-color:${borderColor};">`;
      html += `<span class="group-block-label" style="color:${borderColor};">${type}×${items.length}</span>`;
      html += `<span class="group-block-rows">`;

      for (const grp of items) {
        html += `<span class="card-cluster" style="border-color:${borderColor}44;">`;
        if (Array.isArray(grp)) {
          for (const card of grp) {
            html += renderCardFromCode(card);
          }
        } else if (typeof grp === 'string') {
          const parts = grp.split(' ');
          for (const p of parts) {
            html += renderCardFromDisplay(p);
          }
        }
        html += `</span>`;
      }

      html += `</span>`;  // group-block-rows
      html += `</div>`;  // group-block
    }

    html += '</div>';  // grouping-row

    document.getElementById('groupingResult').innerHTML = html;
  }

  // 横排顺序：同花顺 → 炸弹 → 三带二 → 顺子 → 钢板 → 三连对 → 对子 → 单张
  const GROUP_PRIORITY = ['同花顺', '炸弹', '三带二', '顺子', '钢板', '三连对', '三张', '对子', '单张'];
  const GROUP_COLORS = {
    '同花顺': { border: '#e67e22', bg: 'rgba(230,126,34,0.08)' },
    '炸弹':   { border: '#e74c3c', bg: 'rgba(231,76,60,0.08)' },
    '三带二': { border: '#f39c12', bg: 'rgba(243,156,18,0.08)' },
    '顺子':   { border: '#3498db', bg: 'rgba(52,152,219,0.08)' },
    '钢板':   { border: '#9b59b6', bg: 'rgba(155,89,182,0.08)' },
    '三连对': { border: '#2ecc71', bg: 'rgba(46,204,113,0.08)' },
    '三张':   { border: '#1abc9c', bg: 'rgba(26,188,156,0.08)' },
    '对子':   { border: '#f1c40f', bg: 'rgba(241,196,15,0.08)' },
    '单张':   { border: '#7f8c8d', bg: 'rgba(127,140,141,0.06)' },
  };

  // ── 从原始牌码渲染卡片 ──────────────────────────────
  function renderCardFromCode(code) {
    code = String(code);
    // 大小王（图片清晰，38×24px）
    if (code === 'SB' || code === 'B') return `<span class="rank-cell"><img src="/assets/joker_small.png" style="width:38px;height:24px;vertical-align:middle;"></span>`;
    if (code === 'HR' || code === 'R') return `<span class="rank-cell"><img src="/assets/joker_big.png" style="width:38px;height:24px;vertical-align:middle;"></span>`;
    // 配牌
    if (code === 'XX' || code === '?') {
      return `<span class="rank-cell" style="background:rgba(212,168,67,0.3);">配</span>`;
    }

    const suit = code[0];
    const rank = code.slice(1);
    const SUIT_SYM = { 'S': '♠', 'H': '♥', 'C': '♣', 'D': '♦' };

    let cls = 'rank-cell';
    if (suit === 'H' || suit === 'D') cls += ' red';

    const rankDisp = rank === 'T' ? '10' : rank;
    return `<span class="${cls}">${SUIT_SYM[suit] || suit}${rankDisp}</span>`;
  }

  // ── 从格式化字符串渲染卡片（fallback） ────────────────
  function renderCardFromDisplay(display) {
    if (!display) return '';

    if (display === '🃏') return `<span class="rank-cell"><img src="/assets/joker_small.png" style="width:38px;height:24px;vertical-align:middle;"></span>`;
    if (display === '👑') return `<span class="rank-cell"><img src="/assets/joker_big.png" style="width:38px;height:24px;vertical-align:middle;"></span>`;

    let cls = 'rank-cell';
    const firstCh = display[0];
    if (firstCh === '♥' || firstCh === '♦') cls += ' red';

    // 处理特殊情况："S B" 等碎片
    if (display.length <= 2 && !['♠','♥','♣','♦'].includes(firstCh)) {
      return `<span class="${cls}">${display}</span>`;
    }

    return `<span class="${cls}">${display}</span>`;
  }

  // ── 对手出牌 → V7 决策 ──────────────────────────────

  async function opponentPlay() {
    currentHand = getHandInput();
    currentRank = getCurRank();
    if (!currentHand.length) {
      document.getElementById('decisionResult').innerHTML =
        '<div class="error-msg">请先录入牌谱</div>';
      return;
    }

    renderRawHand();

    const oppType = document.getElementById('oppType').value;
    const oppRank = document.getElementById('oppRank').value.trim();

    let opponentAction;
    if (oppType === 'PASS') {
      opponentAction = ['PASS', '', []];
    } else {
      // 根据牌型生成对手出牌
      const r = oppRank || "2";
      const r2 = r === "T" ? "T" : (r === "2" ? "2" : r);
      const suitCycle = ["S", "H", "C", "D"];
      let cards = [];
      if (oppType === 'Single') cards = [`${suitCycle[0]}${r2}`];
      else if (oppType === 'Pair') cards = [`${suitCycle[0]}${r2}`, `${suitCycle[1]}${r2}`];
      else if (oppType === 'Trips') cards = [`${suitCycle[0]}${r2}`, `${suitCycle[1]}${r2}`, `${suitCycle[2]}${r2}`];
      else if (oppType === 'Bomb') {
        cards = [`${suitCycle[0]}${r2}`, `${suitCycle[1]}${r2}`, `${suitCycle[2]}${r2}`, `${suitCycle[3]}${r2}`];
        opponentAction = ['Bomb', r2, cards];
      } else if (oppType === 'Straight') {
        // 顺子：从起始rank连续5张，各不同花色
        const rankSeq = ['2','3','4','5','6','7','8','9','T','J','Q','K','A'];
        let startIdx = rankSeq.indexOf(r2);
        if (startIdx < 0 || startIdx > rankSeq.length - 5) startIdx = 0;
        cards = rankSeq.slice(startIdx, startIdx + 5).map((rk, i) => `${suitCycle[i % 4]}${rk}`);
      } else if (oppType === 'StraightFlush') {
        // 同花顺：同花色连续5张
        const rankSeq = ['2','3','4','5','6','7','8','9','T','J','Q','K','A'];
        let startIdx = rankSeq.indexOf(r2);
        if (startIdx < 0 || startIdx > rankSeq.length - 5) startIdx = 0;
        cards = rankSeq.slice(startIdx, startIdx + 5).map(rk => `S${rk}`);
      } else if (oppType === 'ThreePair') {
        // 三连对：3个连续对子 = 6张
        const rankSeq = ['2','3','4','5','6','7','8','9','T','J','Q','K','A'];
        let startIdx = rankSeq.indexOf(r2);
        if (startIdx < 0 || startIdx > rankSeq.length - 3) startIdx = 0;
        cards = [];
        for (let i = 0; i < 3; i++) {
          const rk = rankSeq[startIdx + i];
          cards.push(`S${rk}`, `H${rk}`);
        }
      } else if (oppType === 'TwoTrips') {
        // 钢板：2个连续三张 = 6张
        const rankSeq = ['2','3','4','5','6','7','8','9','T','J','Q','K','A'];
        let startIdx = rankSeq.indexOf(r2);
        if (startIdx < 0 || startIdx > rankSeq.length - 2) startIdx = 0;
        cards = [];
        for (let i = 0; i < 2; i++) {
          const rk = rankSeq[startIdx + i];
          cards.push(`S${rk}`, `H${rk}`, `C${rk}`);
        }
      } else if (oppType === 'ThreeWithTwo') {
        // 三带二：3张X + 2张Y（把第二点数放在隐藏字段或默认可换的）
        cards = [`S${r2}`, `H${r2}`, `C${r2}`, `S3`, `H3`];
      } else {
        cards = [`${suitCycle[0]}${r2}`];
      }

      if (oppType !== 'Bomb') {
        opponentAction = [oppType, r2, cards];
      }
    }

    document.getElementById('opponentPreview').innerHTML =
      `模拟对手出牌: <strong>${oppType} ${oppRank || ''}</strong>`;

    document.getElementById('decisionResult').innerHTML =
      '<div class="loading">⏳ V7 思考中...</div>';

    try {
      const resp = await fetch('/api/decide', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          hand_cards: currentHand,
          opponent_action: opponentAction,
          cur_rank: currentRank,
        }),
      });
      const data = await resp.json();

      if (data.error) {
        document.getElementById('decisionResult').innerHTML =
          `<div class="error-msg">${data.error}</div>`;
        return;
      }

      renderDecision(data);

      // 同时刷新组局展示
      if (data.groups) {
        renderGrouping({ ...data, hand_count: currentHand.length });
      }
    } catch (e) {
      document.getElementById('decisionResult').innerHTML =
        `<div class="error-msg">网络错误: ${e.message}</div>`;
    }
  }

  function renderDecision(data) {
    const roleEl = document.getElementById('resultRole');
    roleEl.style.display = 'inline-block';
    let roleClass = data.role.includes('主攻') ? 'main' : 'support';
    roleEl.className = `role-badge ${roleClass}`;
    roleEl.textContent = data.role;

    let html = '<div class="decision-bar">';

    const act = data.action;
    if (act) {
      html += `<span class="decision-text">V7 → <strong>${act.type_label}</strong></span>`;
      if (act.cards_display === 'PASS') {
        html += `<span class="card-tag pass">PASS</span>`;
      } else {
        html += `<span class="decision-cards-row">${renderCardRow(act.cards_display)}</span>`;
      }
    } else {
      html += `<span class="decision-text">V7 → <strong>PASS</strong></span>`;
    }

    html += `<div class="decision-meta">`;
    html += `<span>候选:${data.candidate_count}</span>`;
    html += `<span>Guard:${data.guard_filtered}/${data.guard_override}</span>`;
    html += `<span>组牌:${data.group_filtered}</span>`;
    html += `<span>启发:${data.heuristic_decisions}</span>`;
    html += `</div>`;

    html += `</div>`;
    document.getElementById('decisionResult').innerHTML = html;
  }

  // ── 卡牌渲染（横排按点数）─────────────────────────

  function parseCard(cardStr) {
    // "SB" → {rank:"B", suit:""}, "HR" → {rank:"R", suit:""}
    // "S3" → {rank:"3", suit:"♠"}
    if (cardStr === 'SB' || cardStr === '🃏') return {rank:'B', suit:'', raw:'SB'};
    if (cardStr === 'HR' || cardStr === '👑') return {rank:'R', suit:'', raw:'HR'};
    const suit = SUIT_MAP[cardStr[0]] || cardStr[0];
    const rank = cardStr.slice(1);
    return {rank, suit, raw: cardStr};
  }

  const SUIT_MAP = {'S':'♠','H':'♥','C':'♣','D':'♦'};
  const RANK_ORDER = ['A','K','Q','J','T','9','8','7','6','5','4','3','2','B','R'];
  const RANK_LABEL = {
    'A':'A','K':'K','Q':'Q','J':'J','T':'10','9':'9','8':'8','7':'7',
    '6':'6','5':'5','4':'4','3':'3','2':'2','B':'小','R':'配'
  };

  function buildCardMap(cards) {
    // cards → {rank: [cardStr, ...]}
    const map = {};
    for (const c of cards) {
      const p = parseCard(c);
      if (!map[p.rank]) map[p.rank] = [];
      map[p.rank].push(p);
    }
    return map;
  }

  function buildGroupTagMap(groups) {
    // 给每张牌打上组类型标签
    const tag = {}; // rawCardStr → groupType
    if (!groups) return tag;
    for (const [label, items] of Object.entries(groups)) {
      let gtype = 'pair';
      if (label.includes('炸弹')) gtype = 'bomb';
      else if (label.includes('同花')) gtype = 'sfl';
      else if (label.includes('顺子')) gtype = 'straight';
      else if (label.includes('三') || label.includes('钢')) gtype = 'three';
      else if (label.includes('对')) gtype = 'pair';
      else gtype = 'single';

      for (const item of items) {
        const parts = item.split(/\s+/).filter(s => s);
        for (const c of parts) {
          tag[c] = gtype;
        }
      }
    }
    // 散牌
    return tag;
  }

  function renderCardCell(p, groupTag) {
    let cls = 'rank-cell';
    const isRed = p.suit === '♥' || p.suit === '♦';
    if (isRed) cls += ' red';
    if (groupTag === 'bomb') cls += ' in-bomb';
    else if (groupTag === 'sfl') cls += ' in-sfl';
    else if (groupTag === 'straight') cls += ' in-straight';
    else if (groupTag === 'three') cls += ' in-three';
    else if (groupTag === 'pair') cls += ' in-pair';

    let display;
    if (p.rank === 'B') {
      return `<span class="${cls}"><img src="/assets/joker_small.png" alt="小王" style="width:38px;height:24px;vertical-align:middle;"></span>`;
    } else if (p.rank === 'R') {
      return `<span class="${cls}"><img src="/assets/joker_big.png" alt="大王" style="width:38px;height:24px;vertical-align:middle;"></span>`;
    } else {
      const rankDisplay = p.rank === 'T' ? '10' : p.rank;
      display = p.suit + rankDisplay;
      return `<span class="${cls}">${display}</span>`;
    }
  }

  function renderCardRow(cardsStr) {
    if (!cardsStr) return '';
    const parts = cardsStr.split(/\s+/).filter(s => s);
    return parts.map(p => {
      // 大小王：emoji 在 22px cell 里糊掉，用文字渲染
      if (p === '🃏') return `<span class="card-tag" style="background:rgba(212,168,67,0.25);color:var(--gold-light);">小王</span>`;
      if (p === '👑') return `<span class="card-tag" style="background:rgba(231,76,60,0.25);color:#e74c3c;">大王</span>`;
      let cls = 'card-tag';
      if (p.includes('♥') || p.includes('♦')) cls += ' red';
      return `<span class="${cls}">${p}</span>`;
    }).join('');
  }

  // ── 页面加载：恢复上次手牌 ────────────────────────────
  window.addEventListener('load', function() {
    restoreHand();
  });

  // ── 快捷键 ──────────────────────────────────────────

  document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'Enter') {
      opponentPlay();
    } else if (e.altKey && e.key === 'a') {
      e.preventDefault();
      analyzeHand();
    }
  });
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

# ═══════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║   V7 行牌决策调试器 GUI                      ║")
    print("║   浏览器打开: http://127.0.0.1:5000           ║")
    print("║   Alt+A = 组局  |  Ctrl+Enter = V7应对   ║")
    print("╚══════════════════════════════════════════════╝")
    app.run(host="127.0.0.1", port=5000, debug=False)
