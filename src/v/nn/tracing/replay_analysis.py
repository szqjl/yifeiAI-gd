# -*- coding: utf-8 -*-
"""YF_REPLAY 的 A/B/C 决策链路离线分析。"""
from __future__ import annotations

import copy
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from scripts.tools.wf12_find_decision_at_step import (
    action_key,
    find_decision_at_step,
    is_play_decision,
)


GUA_RE = re.compile(r"GUA-\d+")


class _ReplayLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.lines: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if (
            GUA_RE.search(message)
            or "残局" in message
            or "Guard" in message
            or "过滤" in message
            or "heuristic" in message
            or "推荐" in message
        ):
            self.lines.append(message)


def _sample_to_actions(sample: Any) -> List[List[Any]]:
    if not isinstance(sample, list):
        return []
    actions: List[List[Any]] = []
    for item in sample:
        if isinstance(item, dict):
            actions.append([
                item.get("type", ""),
                item.get("rank", ""),
                item.get("cards", []) or [],
            ])
    return actions


def _trace_event(trace: Dict[str, Any], stage: str) -> Optional[Dict[str, Any]]:
    for event in trace.get("pipeline", []):
        if event.get("stage") == stage:
            return event
    return None


def _match_action_indices(actions: Iterable[Any], originals: List[Any]) -> List[int]:
    used = set()
    indices: List[int] = []
    for action in actions:
        key = action_key(action)
        matched = -1
        for index, original in enumerate(originals):
            if index not in used and action_key(original) == key:
                matched = index
                used.add(index)
                break
        indices.append(matched)
    return indices


def _gua_entries(
    recorded_layer: Any,
    b_trace: Optional[Dict[str, Any]],
    pipeline: List[Dict[str, Any]],
    log_lines: List[str],
) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    seen = set()

    def add(gua_id: str, source: str, payload: Any) -> None:
        marker = (gua_id, source, json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
        if marker in seen:
            return
        seen.add(marker)
        entries.append({"gua_id": gua_id, "source": source, "payload": payload})

    for gua_id in GUA_RE.findall(str(recorded_layer or "")):
        add(gua_id, "recorded_layer", str(recorded_layer))
    if b_trace:
        for item in b_trace.get("layer2_ips", []) or []:
            for gua_id in GUA_RE.findall(str(item.get("ip_id", ""))):
                add(gua_id, "B.layer2", item)
        intent = b_trace.get("decision_intent") or {}
        for gua_id in GUA_RE.findall(str(intent)):
            add(gua_id, "B.intent", intent)
    for event in pipeline:
        gua_ids = []
        if event.get("gua_id"):
            gua_ids.append(event["gua_id"])
        gua_ids.extend(event.get("gua_ids") or [])
        for gua_id in gua_ids:
            add(str(gua_id), f"C.pipeline.{event.get('stage', '?')}", event)
    for line in log_lines:
        for gua_id in GUA_RE.findall(line):
            add(gua_id, "C.offline_log", line)
    return entries


class ReplayDecisionAnalyzer:
    """从牌谱某一步生成 A/B/C 三颗粒度决策分析。"""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        engine_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.repo_root = repo_root or Path(__file__).resolve().parents[4]
        self.trace_dir = self.repo_root / "game_decision_traces"
        self.engine_factory = engine_factory

    def _new_engine(self, player_id: int) -> Any:
        if self.engine_factory is not None:
            return self.engine_factory(player_id=player_id, use_grouping_engine=True)
        from src.v.nn.ultimate_win_rate_engine_v7 import UltimateWinRateEngineV7

        return UltimateWinRateEngineV7(
            player_id=player_id,
            use_grouping_engine=True,
        )

    def _load_b_trace(self, game_id: str, play_ordinal: int) -> Optional[Dict[str, Any]]:
        path = self.trace_dir / f"{game_id}.jsonl"
        if not path.exists():
            return None
        lines = path.read_text(encoding="utf-8").splitlines()
        if not 0 <= play_ordinal < len(lines):
            return None
        try:
            return json.loads(lines[play_ordinal])
        except json.JSONDecodeError:
            return None

    def analyze(self, game_data: Dict[str, Any], step_num: int) -> Dict[str, Any]:
        decision, play = find_decision_at_step(game_data, step_num)
        play_decisions = [
            item for item in game_data.get("my_decisions") or [] if is_play_decision(item)
        ]
        play_ordinal = next(
            index for index, item in enumerate(play_decisions) if item is decision
        )
        context = decision.get("context") or {}
        recorded_action = decision.get("action") or []
        recorded_index = int(decision.get("action_index", -1))
        replay_state = context.get("replay_state")
        has_full_input = (
            context.get("replay_schema") == "yf-replay-decision-v1"
            and isinstance(replay_state, dict)
            and isinstance(replay_state.get("actionList"), list)
            and len(replay_state.get("actionList") or []) == int(context.get("actionList_size", 0))
        )
        action_list = (
            list(replay_state.get("actionList") or [])
            if has_full_input
            else _sample_to_actions(context.get("actionList_sample"))
        )
        b_trace = self._load_b_trace(str(game_data.get("game_id", "")), play_ordinal)

        result: Dict[str, Any] = {
            "schema": "yf-replay-abc-v1",
            "coverage": "full" if has_full_input else "legacy_limited",
            "step_num": step_num,
            "play_ordinal": play_ordinal,
            "A": {
                "timestamp": decision.get("timestamp"),
                "player_id": game_data.get("player_id"),
                "cur_pos": play.get("cur_pos"),
                "greater_pos": context.get("greaterPos", play.get("greater_pos")),
                "greater_action": (
                    replay_state.get("greaterAction")
                    if has_full_input
                    else play.get("greater_action")
                ),
                "hand_cards": context.get("handCards") or [],
                "curRank": context.get("curRank"),
                "stage": context.get("stage"),
                "actual_actIndex": recorded_index,
                "actual_action": recorded_action,
                "actionList_size": context.get("actionList_size", len(action_list)),
                "raw_state": replay_state if has_full_input else context,
            },
            "B": {
                "recorded_layer": decision.get("layer"),
                "recorded_score": decision.get("score"),
                "recorded_candidates_count": decision.get("candidates_count"),
                "production_trace": b_trace,
                "offline_layer": None,
                "offline_actIndex": None,
                "offline_matches_actual": None,
                "pipeline": [],
            },
            "C": {
                "candidate_rows": [],
                "guard_trace": [],
                "memory_snapshot": {
                    "hand": context.get("handCards") or [],
                    "curRank": context.get("curRank"),
                    "role": context.get("role"),
                    "card_mask": context.get("card_mask") or {},
                    "group_type_map": context.get("group_type_map") or {},
                },
                "gua_traces": _gua_entries(decision.get("layer"), b_trace, [], []),
                "offline_logs": [],
            },
            "warnings": [],
        }

        if not has_full_input:
            result["warnings"].append(
                "旧牌谱未保存完整 actionList/publicInfo/greaterAction；A 与 B 可用，C 仅展示已落盘字段。"
            )
            result["C"]["candidate_rows"] = [
                {
                    "original_index": index,
                    "action": action,
                    "actual": index == recorded_index,
                    "guard_kept": None,
                    "group_kept": None,
                    "heuristic_score": None,
                }
                for index, action in enumerate(action_list)
            ]
            return result

        engine = self._new_engine(int(game_data.get("player_id", 0)))
        if hasattr(engine, "on_game_start"):
            engine.on_game_start(
                my_pos=int(game_data.get("player_id", 0)),
                game_id=str(game_data.get("game_id", "")),
            )
        if hasattr(engine, "_decision_tracer"):
            engine._decision_tracer = None

        target_state: Optional[Dict[str, Any]] = None
        offline_index: Optional[int] = None
        log_handler = _ReplayLogHandler()
        root_logger = logging.getLogger()
        old_level = root_logger.level

        for index, item in enumerate(play_decisions[:play_ordinal + 1]):
            item_context = item.get("context") or {}
            item_state = item_context.get("replay_state")
            if not isinstance(item_state, dict):
                result["warnings"].append(
                    f"第 {index + 1} 个 play 决策缺 replay_state，跨步记忆可能不完整。"
                )
                continue
            state = copy.deepcopy(item_state)
            state["_replay_trace"] = {}
            state["_replay_guard_trace"] = []
            if index == play_ordinal:
                root_logger.addHandler(log_handler)
                root_logger.setLevel(logging.DEBUG)
            try:
                offline_index = int(engine.decide(state))
            finally:
                if index == play_ordinal:
                    root_logger.removeHandler(log_handler)
                    root_logger.setLevel(old_level)
            if index == play_ordinal:
                target_state = state

        if target_state is None or offline_index is None:
            result["warnings"].append("离线决策器未能运行到目标步骤。")
            return result

        replay_trace = target_state.get("_replay_trace") or {}
        pipeline = replay_trace.get("pipeline", []) or []
        result["B"].update({
            "offline_layer": getattr(engine, "_last_decision_layer", None),
            "offline_actIndex": offline_index,
            "offline_matches_actual": (
                offline_index == recorded_index
                and 0 <= offline_index < len(action_list)
                and action_key(action_list[offline_index]) == action_key(recorded_action)
            ),
            "pipeline": pipeline,
        })

        guard_trace = target_state.get("_replay_guard_trace") or []
        removed_by: Dict[int, List[str]] = {}
        final_guard_event = None
        for event in guard_trace:
            if event.get("rule_id") == "final_order":
                final_guard_event = event
            for original_index in event.get("removed_indices", []) or []:
                removed_by.setdefault(int(original_index), []).append(str(event.get("rule_id")))
        guard_kept = set(
            (final_guard_event or {}).get("order_indices", list(range(len(action_list))))
        )

        candidate_order_event = _trace_event(replay_trace, "candidate_order") or {}
        scoring_actions = list(candidate_order_event.get("actions") or action_list)
        actual_heuristic_event = _trace_event(replay_trace, "heuristic_scores")
        score_source = "actual_path" if actual_heuristic_event else "offline_reference"
        if actual_heuristic_event:
            score_pairs = actual_heuristic_event.get("scores") or []
        else:
            active_trace = getattr(engine, "_active_replay_trace", None)
            engine._active_replay_trace = None
            try:
                engine._heuristic_select(target_state, scoring_actions)
            finally:
                engine._active_replay_trace = active_trace
            score_pairs = getattr(engine, "_last_heuristic_scores", []) or []
        score_indices = _match_action_indices(scoring_actions, action_list)
        heuristic_scores: Dict[int, float] = {}
        for local_index, score in score_pairs:
            if 0 <= int(local_index) < len(score_indices):
                original_index = score_indices[int(local_index)]
                if original_index >= 0:
                    heuristic_scores[original_index] = float(score)
        model_scores: Dict[int, float] = {}
        model_score_event = _trace_event(replay_trace, "model_scores") or {}
        for local_index, score in model_score_event.get("scores", []) or []:
            if 0 <= int(local_index) < len(score_indices):
                original_index = score_indices[int(local_index)]
                if original_index >= 0:
                    model_scores[original_index] = float(score)

        group_original_indices = set(score_indices)
        group_original_indices.discard(-1)
        candidate_rows = []
        for original_index, action in enumerate(action_list):
            candidate_rows.append({
                "original_index": original_index,
                "action": action,
                "actual": original_index == recorded_index,
                "offline_chosen": original_index == offline_index,
                "guard_kept": original_index in guard_kept,
                "guard_removed_by": removed_by.get(original_index, []),
                "group_kept": original_index in group_original_indices,
                "model_score": model_scores.get(original_index),
                "heuristic_score": heuristic_scores.get(original_index),
                "score_source": score_source if original_index in heuristic_scores else None,
            })
        candidate_rows.sort(
            key=lambda row: (
                row["heuristic_score"] is None,
                -(row["heuristic_score"] or 0.0),
                row["original_index"],
            )
        )

        tracker = getattr(engine, "_tracker", None)
        hand_counts = list(getattr(tracker, "hand_counts", []) or [])
        my_pos = int(game_data.get("player_id", 0))
        teammate_pos = (my_pos + 2) % 4
        belief = target_state.get("_belief") or {}
        phase_relation = target_state.get("_phase_relation") or {}
        memory_snapshot = {
            "hand": target_state.get("handCards") or [],
            "curRank": target_state.get("curRank"),
            "role": getattr(engine, "_current_role", None),
            "phase": target_state.get("_current_stage"),
            "hand_counts": hand_counts,
            "teammate_hands_est": (
                hand_counts[teammate_pos] if len(hand_counts) > teammate_pos else None
            ),
            "opponent_sprint_capable": phase_relation.get("sprint_fire_ready"),
            "belief": belief,
            "phase_relation": phase_relation,
            "card_mask": target_state.get("_card_mask") or {},
            "group_type_map": target_state.get("_group_gid_type_map") or {},
        }
        result["C"].update({
            "candidate_rows": candidate_rows,
            "guard_trace": guard_trace,
            "memory_snapshot": memory_snapshot,
            "offline_logs": log_handler.lines,
            "gua_traces": _gua_entries(
                decision.get("layer"),
                b_trace,
                pipeline,
                log_handler.lines,
            ),
        })
        if not result["B"]["offline_matches_actual"]:
            result["warnings"].append(
                "离线复算与实战动作不一致；请检查代码版本、模型版本或跨步输入完整性。"
            )
        return result


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def format_analysis_sections(result: Dict[str, Any]) -> Dict[str, str]:
    """将结构化分析格式化为 YF_REPLAY 三个页签的文本。"""
    a = result["A"]
    b = result["B"]
    c = result["C"]
    warnings = "\n".join(f"⚠ {item}" for item in result.get("warnings", []))

    a_text = (
        f"覆盖级别: {result.get('coverage')}\n"
        f"步骤: {result.get('step_num')}  YF第{result.get('play_ordinal', 0) + 1}次出牌\n"
        f"实际 actIndex: {a.get('actual_actIndex')}\n"
        f"实际动作: {_json_text(a.get('actual_action'))}\n"
        f"手牌数: {len(a.get('hand_cards') or [])}  curRank: {a.get('curRank')}\n"
        f"greaterPos: {a.get('greater_pos')}  greaterAction: {_json_text(a.get('greater_action'))}\n"
        f"actionList_size: {a.get('actionList_size')}\n\n"
        f"{warnings}\n\n平台原始状态:\n{_json_text(a.get('raw_state'))}"
    )

    b_text = (
        f"实战决策层: {b.get('recorded_layer')}\n"
        f"实战评分: {b.get('recorded_score')}\n"
        f"离线决策层: {b.get('offline_layer')}\n"
        f"离线 actIndex: {b.get('offline_actIndex')}\n"
        f"与实战一致: {b.get('offline_matches_actual')}\n\n"
        f"生产 B trace:\n{_json_text(b.get('production_trace'))}\n\n"
        f"离线管线:\n{_json_text(b.get('pipeline'))}"
    )

    candidate_lines = [
        "排名 | 原idx | 实战 | 复算 | Guard | 组牌 | model | heuristic | 评分来源 | 动作",
        "-" * 136,
    ]
    for rank, row in enumerate(c.get("candidate_rows") or [], 1):
        action = row.get("action") or []
        action_text = "/".join(str(part) for part in action[:2])
        cards = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        score = row.get("heuristic_score")
        score_text = "-" if score is None else f"{score:.2f}"
        model_score = row.get("model_score")
        model_score_text = "-" if model_score is None else f"{model_score:.5f}"
        guard_text = "保留" if row.get("guard_kept") is True else (
            "剔除:" + ",".join(row.get("guard_removed_by") or [])
            if row.get("guard_kept") is False else "未知"
        )
        candidate_lines.append(
            f"{rank:>4} | {row.get('original_index'):>5} | "
            f"{'★' if row.get('actual') else ' ':^4} | "
            f"{'★' if row.get('offline_chosen') else ' ':^4} | "
            f"{guard_text:<15} | "
            f"{str(row.get('group_kept')):<4} | {model_score_text:>7} | "
            f"{score_text:>9} | {str(row.get('score_source') or '-'):>17} | "
            f"{action_text} {cards}"
        )
    c_text = (
        f"Memory / 信念快照:\n{_json_text(c.get('memory_snapshot'))}\n\n"
        f"GUA trace:\n{_json_text(c.get('gua_traces'))}\n\n"
        f"Guard trace:\n{_json_text(c.get('guard_trace'))}\n\n"
        f"候选逐层去留与排序:\n" + "\n".join(candidate_lines) + "\n\n"
        f"离线诊断日志:\n" + "\n".join(c.get("offline_logs") or [])
    )
    return {"A 实战事实": a_text, "B 决策路径": b_text, "C 深度分析": c_text}
