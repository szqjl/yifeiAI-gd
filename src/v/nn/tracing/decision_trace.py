# -*- coding: utf-8 -*-
"""
GUA-098: 决策溯源日志模块 (DecisionTracer)

设计目标:
- 每步决策记录"跑了 Layer 几、触发了哪条 IP、过滤了哪条 Guard、决策时间"
- 机械化 V5 "决策是兜底没人发现" 教训 (§4.1 + §8.1 红字第 2 条)
- 不阻塞主决策路径——纯旁路日志

使用方式 (V7 决策入口接入):
    tracer = DecisionTracer(my_pos=2, game_id="...")
    tracer.begin_step(hand_size=27, cur_rank='2', stage='stage_0_1')
    # ... 跑 Layer 1 记忆 + Layer 2 推断 ...
    tracer.record_layer2(ip_id='IP-07', delta=0.3, oppo='p3')
    # ... 跑 Layer 3 决策 (Guard 过滤) ...
    tracer.record_guard('R05', filtered_count=2, reason='teammate is greater')
    # ... 选 actIndex ...
    tracer.end_step(actIndex=12, chosen_action=['Single', 'A', ['DA']], decision_ms=15.3)

每个 game 结束:
    tracer.flush_to_jsonl()  -> 写入 game_decision_traces/{game_id}.jsonl
"""
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

ROOT = Path(__file__).resolve().parents[3]  # D:\\guandanscore\\YiFeiAI-GD
TRACE_DIR = ROOT / "game_decision_traces"


class DecisionTracer:
    def __init__(self, my_pos: int, game_id: str, enable: bool = True):
        self.my_pos = my_pos
        self.game_id = game_id
        self.enable = enable
        self._current_step: Optional[Dict[str, Any]] = None
        self._steps: List[Dict[str, Any]] = []

    def begin_step(self, hand_size: int, cur_rank: str, stage: str, cur_pos: int = -1, greater_pos: int = -1):
        if not self.enable:
            return
        self._current_step = {
            "ts_start_ms": int(time.time() * 1000),
            "hand_size": hand_size,
            "cur_rank": cur_rank,
            "stage": stage,
            "cur_pos": cur_pos,
            "greater_pos": greater_pos,
            "layer1_hits": [],
            "layer2_ips": [],
            "layer3_guards": [],
            "actIndex_chosen": None,
            "decision_ms": None,
        }

    def record_layer1(self, source: str, payload: Any):
        if not self.enable or self._current_step is None:
            return
        self._current_step["layer1_hits"].append({"source": source, "payload": str(payload)[:200]})

    def record_layer2(self, ip_id: str, delta: float, oppo: str = "", comment: str = ""):
        if not self.enable or self._current_step is None:
            return
        self._current_step["layer2_ips"].append({
            "ip_id": ip_id,
            "delta": delta,
            "oppo": oppo,
            "comment": comment,
        })

    def record_guard(self, rule_id: str, filtered_count: int, reason: str = ""):
        if not self.enable or self._current_step is None:
            return
        self._current_step["layer3_guards"].append({
            "rule_id": rule_id,
            "filtered_count": filtered_count,
            "reason": reason,
        })

    def end_step(self, actIndex: int, chosen_action: Any):
        if not self.enable or self._current_step is None:
            return
        self._current_step["ts_end_ms"] = int(time.time() * 1000)
        self._current_step["decision_ms"] = self._current_step["ts_end_ms"] - self._current_step["ts_start_ms"]
        self._current_step["actIndex_chosen"] = actIndex
        self._current_step["chosen_action"] = str(chosen_action)[:200]
        self._steps.append(self._current_step)
        self._current_step = None

    def flush_to_jsonl(self):
        if not self.enable or not self._steps:
            return None
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        fp = TRACE_DIR / (self.game_id + ".jsonl")
        try:
            with open(fp, "w", encoding="utf-8") as f:
                for step in self._steps:
                    f.write(json.dumps(step, ensure_ascii=False) + "\n")
            return fp
        except Exception as e:
            print("[DecisionTracer] flush 失败:", e)
            return None

    def get_summary(self) -> Dict[str, Any]:
        n = len(self._steps)
        if n == 0:
            return {"steps": 0}
        stages = {}
        ip_counter = {}
        guard_counter = {}
        total_ms = 0
        for s in self._steps:
            stages[s.get("stage", "?")] = stages.get(s.get("stage", "?"), 0) + 1
            for ip in s.get("layer2_ips", []):
                ip_counter[ip["ip_id"]] = ip_counter.get(ip["ip_id"], 0) + 1
            for g in s.get("layer3_guards", []):
                guard_counter[g["rule_id"]] = guard_counter.get(g["rule_id"], 0) + 1
            total_ms += s.get("decision_ms", 0) or 0
        return {
            "steps": n,
            "stages": stages,
            "ip_counter": ip_counter,
            "guard_counter": guard_counter,
            "total_ms": total_ms,
            "avg_ms": total_ms / n if n else 0,
        }
