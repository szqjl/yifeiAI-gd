# -*- coding: utf-8 -*-
"""GUA-096/097/098 pytest — 验证 3 个 helper 模块"""
import json
import sys
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_gua098_decision_tracer_basic():
    """GUA-098: DecisionTracer 基本流程"""
    from src.v.nn.tracing.decision_trace import DecisionTracer
    t = DecisionTracer(my_pos=2, game_id="test_basic_001", enable=True)
    t.begin_step(hand_size=27, cur_rank="2", stage="stage_0_1", cur_pos=2, greater_pos=2)
    t.record_layer1(source="MemoryTracker", payload="4 王已出 2")
    t.record_layer2(ip_id="IP-07", delta=0.3, oppo="p3", comment="对手无单推断")
    t.record_guard(rule_id="R05", filtered_count=2, reason="teammate is greater")
    t.end_step(actIndex=12, chosen_action=["Single", "A", ["DA"]])
    summary = t.get_summary()
    assert summary["steps"] == 1
    assert summary["stages"]["stage_0_1"] == 1
    assert summary["ip_counter"]["IP-07"] == 1
    assert summary["guard_counter"]["R05"] == 1
    assert summary["avg_ms"] >= 0


def test_gua098_decision_tracer_multi_step():
    """GUA-098: 多步阶段分布"""
    from src.v.nn.tracing.decision_trace import DecisionTracer
    t = DecisionTracer(my_pos=0, game_id="test_multi_001", enable=True)
    stages = ["stage_0_1", "stage_0_1", "stage_2", "stage_2", "stage_3"]
    for i, stg in enumerate(stages):
        t.begin_step(hand_size=27 - i * 5, cur_rank="2", stage=stg)
        t.end_step(actIndex=i, chosen_action=["Pass"])
    summary = t.get_summary()
    assert summary["steps"] == 5
    assert summary["stages"]["stage_0_1"] == 2
    assert summary["stages"]["stage_2"] == 2
    assert summary["stages"]["stage_3"] == 1


def test_gua098_decision_tracer_disabled():
    """GUA-098: enable=False 时不记录"""
    from src.v.nn.tracing.decision_trace import DecisionTracer
    t = DecisionTracer(my_pos=2, game_id="test_dis_001", enable=False)
    t.begin_step(hand_size=27, cur_rank="2", stage="stage_0_1")
    t.end_step(actIndex=0, chosen_action=["Pass"])
    assert t.get_summary()["steps"] == 0


def test_gua098_decision_tracer_flush(tmp_path):
    """GUA-098: flush_to_jsonl 落盘"""
    from src.v.nn.tracing import decision_trace
    # 临时切到 tmp_path
    orig = decision_trace.TRACE_DIR
    decision_trace.TRACE_DIR = tmp_path
    try:
        t = decision_trace.DecisionTracer(my_pos=2, game_id="flush_test", enable=True)
        t.begin_step(hand_size=27, cur_rank="2", stage="stage_0_1")
        t.end_step(actIndex=5, chosen_action=["Single", "3", ["D3"]])
        fp = t.flush_to_jsonl()
        assert fp is not None
        assert fp.exists()
        content = fp.read_text(encoding="utf-8").strip()
        assert "\n" not in content  # 一行
        data = json.loads(content)
        assert data["hand_size"] == 27
        assert data["actIndex_chosen"] == 5
    finally:
        decision_trace.TRACE_DIR = orig


def test_gua097_ip_registry_complete():
    """GUA-097: IP 注册表至少 21 条 (IP-01~IP-21)"""
    sys.path.insert(0, str(ROOT / "scripts/hooks"))
    from ip_ablation_runner import IP_REGISTRY
    assert len(IP_REGISTRY) >= 21, f"IP_REGISTRY 只有 {len(IP_REGISTRY)} 条，需 ≥21 (IP-01~IP-21)"
    for i in range(1, 22):
        key = f"IP-{i:02d}"
        assert key in IP_REGISTRY, f"缺少 {key}"


def test_gua097_list_mode_runs():
    """GUA-097: --mode list 应能跑通不报错"""
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp_path = tmp.name
    try:
        with open(tmp_path, "w", encoding="utf-8") as fout:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts/hooks/ip_ablation_runner.py"), "--mode", "list"],
                stdout=fout, stderr=subprocess.STDOUT, text=True, cwd=str(ROOT),
            )
        assert r.returncode == 0
        out = open(tmp_path, encoding="utf-8").read()
        assert "IP-01" in out
        assert "IP-21" in out
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_gua096_post_batch_log_syntax():
    """GUA-096: post_batch_log.py 至少能解析 + --help 跑通"""
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp:
        tmp_path = tmp.name
    try:
        with open(tmp_path, "w", encoding="utf-8") as fout:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts/hooks/post_batch_log.py"), "--help"],
                stdout=fout, stderr=subprocess.STDOUT, text=True, cwd=str(ROOT),
            )
        assert r.returncode == 0
        out = open(tmp_path, encoding="utf-8").read()
        assert "--gua-id" in out
        assert "--games" in out
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
