# -*- coding: utf-8 -*-
"""GUA-096/097/098 pytest — 验证 3 个 helper 模块"""
import json
import sys
import subprocess
import tempfile
from pathlib import Path
import logging

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_gua098_decision_tracer_basic():
    """GUA-098: DecisionTracer 基本流程"""
    from src.v.nn.tracing.decision_trace import DecisionTracer
    t = DecisionTracer(my_pos=2, game_id="test_basic_001", enable=True)
    t.begin_step(hand_size=27, cur_rank="2", stage="stage_0", cur_pos=2, greater_pos=2)
    t.record_layer1(source="MemoryTracker", payload="4 王已出 2")
    t.record_layer2(ip_id="IP-07", delta=0.3, oppo="p3", comment="对手无单推断")
    t.record_guard(rule_id="R05", filtered_count=2, reason="teammate is greater")
    t.end_step(actIndex=12, chosen_action=["Single", "A", ["DA"]])
    summary = t.get_summary()
    assert summary["steps"] == 1
    assert summary["stages"]["stage_0"] == 1
    assert summary["ip_counter"]["IP-07"] == 1
    assert summary["guard_counter"]["R05"] == 1
    assert summary["avg_ms"] >= 0


def test_gua098_decision_tracer_multi_step():
    """GUA-098: 多步阶段分布"""
    from src.v.nn.tracing.decision_trace import DecisionTracer
    t = DecisionTracer(my_pos=0, game_id="test_multi_001", enable=True)
    stages = ["stage_0", "stage_1", "stage_2", "stage_2", "stage_3"]
    for i, stg in enumerate(stages):
        t.begin_step(hand_size=27 - i * 5, cur_rank="2", stage=stg)
        t.end_step(actIndex=i, chosen_action=["Pass"])
    summary = t.get_summary()
    assert summary["steps"] == 5
    assert summary["stages"]["stage_0"] == 1
    assert summary["stages"]["stage_1"] == 1
    assert summary["stages"]["stage_2"] == 2
    assert summary["stages"]["stage_3"] == 1


def test_gua098_decision_tracer_records_stage_intent():
    """GUA-098: stage intent 应写入单步 trace。"""
    from src.v.nn.tracing.decision_trace import DecisionTracer
    t = DecisionTracer(my_pos=0, game_id="test_intent_001", enable=True)
    t.begin_step(hand_size=12, cur_rank="2", stage="stage_2")
    t.record_decision_intent("mid_block_critical_enemy", {"seat": 1})
    t.end_step(actIndex=1, chosen_action=["Single", "A", ["SA"]])
    summary = t.get_summary()
    assert summary["steps"] == 1
    assert t._steps[0]["decision_intent"]["intent"] == "mid_block_critical_enemy"


def test_gua098_decision_tracer_disabled():
    """GUA-098: enable=False 时不记录"""
    from src.v.nn.tracing.decision_trace import DecisionTracer
    t = DecisionTracer(my_pos=2, game_id="test_dis_001", enable=False)
    t.begin_step(hand_size=27, cur_rank="2", stage="stage_0")
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
        t.begin_step(hand_size=27, cur_rank="2", stage="stage_0")
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


def test_gua098_decision_tracer_records_joker_signal(tmp_path):
    """GUA-098: joker_signal 写入 trace 且 log 行可 grep。"""
    from src.v.nn.tracing import decision_trace
    from src.v.nn.tracing.decision_trace import DecisionTracer, format_joker_signal_line

    joker = {
        "HR": {"played": 1, "remain": 1, "in_my_hand": 0, "with_teammate": 1, "with_opponents": 0, "unknown": 0},
        "SB": {"played": 0, "remain": 2, "in_my_hand": 1, "with_teammate": 0, "with_opponents": 0, "unknown": 1},
        "hr_played": 1,
        "hr_remain": 1,
        "hr_in_my_hand": 0,
        "hr_with_teammate": 1,
        "hr_with_opponents": 0,
        "hr_unknown": 0,
        "sb_played": 0,
        "sb_remain": 2,
        "sb_in_my_hand": 1,
        "sb_with_teammate": 0,
        "sb_with_opponents": 0,
        "sb_unknown": 1,
    }
    line = format_joker_signal_line(joker)
    assert line.startswith("joker_signal ")
    assert "hr p=1 r=1" in line
    assert "sb p=0 r=2" in line

    orig = decision_trace.TRACE_DIR
    decision_trace.TRACE_DIR = tmp_path
    try:
        t = DecisionTracer(my_pos=0, game_id="joker_trace_test", enable=True)
        t.begin_step(hand_size=10, cur_rank="A", stage="stage_2")
        t.record_joker_signal(joker)
        t.end_step(actIndex=0, chosen_action=["PASS", "PASS", "PASS"])
        fp = t.flush_to_jsonl()
        data = json.loads(fp.read_text(encoding="utf-8").strip())
        assert data["joker_signal"]["hr_played"] == 1
        assert data["joker_signal"]["sb_in_my_hand"] == 1
    finally:
        decision_trace.TRACE_DIR = orig


def test_gua098_trace_dir_points_to_repo_root():
    """GUA-098: 生产 trace 应落到仓库根 game_decision_traces/。"""
    from src.v.nn.tracing import decision_trace

    assert decision_trace.TRACE_DIR == ROOT / "game_decision_traces"


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
        assert "GUA-091" in out
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_gua097_feature_registry_contains_gua091():
    """GUA-097: feature registry 应登记 GUA-091 stage_2 开关。"""
    sys.path.insert(0, str(ROOT / "scripts/hooks"))
    from ip_ablation_runner import FEATURE_REGISTRY, build_run_env

    assert "GUA-091" in FEATURE_REGISTRY
    env_off = build_run_env(feature_id="GUA-091", enable=False)
    env_on = build_run_env(feature_id="GUA-091", enable=True)
    assert env_off["V7_ENABLE_STAGE2_DISPATCH"] == "0"
    assert env_on["V7_ENABLE_STAGE2_DISPATCH"] == "1"


def test_gua096_097_team_win_rate_uses_victory_num_primary_slots():
    """GUA-096/097: victoryNum 应按 [0] vs [1] 计局胜，不能把镜像位重复相加。"""
    sys.path.insert(0, str(ROOT / "scripts/hooks"))
    from ip_ablation_runner import calc_team_win_rate as calc_ablation_team_win_rate
    from post_batch_log import calc_team_win_rate as calc_post_batch_team_win_rate

    vn_payload = {"victoryNum": [0, 3, 0, 3]}
    ablation_rate, ablation_ratio = calc_ablation_team_win_rate(vn_payload)
    post_rate, post_total = calc_post_batch_team_win_rate(vn_payload["victoryNum"])

    assert ablation_rate == "0/3 (0.0%)"
    assert ablation_ratio == 0.0
    assert post_rate == "0/3 (0.0%)"
    assert post_total == 3


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


def test_v7_launcher_runs_endgame_anomaly_scan_hook(monkeypatch, tmp_path):
    """批跑完整结束后，V7 launcher 应自动调用残局异常扫描脚本。"""
    sys.path.insert(0, str(ROOT))
    from scripts.launchers.v7 import run_v7_vs_lalala_games as launcher

    called = {}

    class DummyResult:
        returncode = 0
        stdout = "扫描目录: game_records_v7\n异常总数: 0\n未发现异常样本\n"
        stderr = ""

    def fake_run(cmd, cwd, capture_output, text, encoding):
        called["cmd"] = cmd
        called["cwd"] = cwd
        return DummyResult()

    monkeypatch.setattr(launcher, "ENDGAME_ANOMALY_SCAN", tmp_path / "check_endgame_anomalies.py")
    launcher.ENDGAME_ANOMALY_SCAN.write_text("# stub", encoding="utf-8")
    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    ok = launcher._run_endgame_anomaly_scan(
        logger=logging.getLogger("test_endgame_scan_hook"),
        scan_dir=ROOT / "game_records_v7",
        limit=12,
    )

    assert ok is True
    assert called["cmd"][0] == sys.executable
    assert called["cmd"][1] == str(launcher.ENDGAME_ANOMALY_SCAN)
    assert called["cmd"][-1] == "12"
