# -*- coding: utf-8 -*-
"""
GUA-223 Phase 1 第 3 项 lalala ETL pytest — game_records_v8 → 训练样本

关联：
  - GUA-223（母条目）/ GUA-223-card-counting-warning-flag（上一行 Phase 0 ETL）
  - CardCountingNetwork-训练方案.md §8 Phase 1
  - scripts/etl/game_records_to_counting_dataset.py（lalala 牌谱 ETL）

测试覆盖：
  ① extract_game_samples 从单局 JSON 提取正确步数
  ② 落盘 .npz 含 ground_truth / hand_self / cur_rank / decision_act_*
  ③ ground_truth 3 类守恒（MY_HAND+PLAYED+REST=108）
  ④ hand_self 严格单调递减（出牌逐步减少）
  ⑤ 真实磁盘 lalala_*.npz 数量一致（3860 样本已写入 data/training/card_counting_v1/）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.etl.game_records_to_counting_dataset import (  # noqa: E402
    extract_game_samples,
    verify_lalala_samples,
)


GAME_RECORDS_DIR = Path("game_records_v8")
DATA_DIR = Path("data/training/card_counting_v1")
TOTAL_SLOTS = 108  # 54 slots × 2 decks


@pytest.fixture(scope="module")
def one_game_sample():
    """挑第一个真实 lalala 牌谱文件，extract_game_samples write=False 内存版样本。"""
    candidates = sorted(GAME_RECORDS_DIR.glob("*.json"))
    if not candidates:
        pytest.skip(f"未找到 {GAME_RECORDS_DIR}（先跑 RUN_V8_VS_LALALA.bat）")
    for f in candidates:
        text = f.read_text(encoding="utf-8")
        data = json.loads(text)
        if len(data.get("initial_hand", [])) == 27 and data.get("my_decisions"):
            samples = extract_game_samples(f, output_dir=Path("tmp/_test_lalala_etl"), write=False)
            if samples:
                return samples, f, data
    pytest.skip("无有效 lalala 牌谱（initial_hand=27 且 my_decisions 非空）")


class TestExtractGameSamples:
    """extract_game_samples 单局 JSON → 回合级样本列表"""

    def test_extract_returns_steps_consistent_with_my_decisions(self, one_game_sample):
        samples, _game_path, raw = one_game_sample
        expected_steps = len(raw["my_decisions"])
        assert len(samples) == expected_steps, (
            f"extract 返回 {len(samples)} 步 ≠ my_decisions {expected_steps} 步"
        )

    def test_extract_first_step_hand_len_27(self, one_game_sample):
        samples, _game_path, _raw = one_game_sample
        # 第一步应为初始手牌 27 张（即使首动作 PASS 也应反映手牌）
        first_hand_len = len(samples[0]["hand_self"])
        assert first_hand_len == 27, f"第一步手牌数 {first_hand_len} ≠ 27"

    def test_extract_cur_rank_matches_context(self, one_game_sample):
        samples, _game_path, raw = one_game_sample
        # 验证 cur_rank 与原始 my_decisions[i].context.curRank 一致
        decisions = raw["my_decisions"]
        for i, s in enumerate(samples[: min(len(samples), len(decisions))]):
            expected = decisions[i].get("context", {}).get("curRank")
            assert s["cur_rank"] == expected, (
                f"step={i} cur_rank={s['cur_rank']} ≠ context={expected}"
            )


class TestGroundTruthConservation:
    """5 项硬门槛 ① 手算对账 — ground_truth 守恒"""

    def test_per_step_my_plus_played_plus_rest_equals_108(self, one_game_sample):
        samples, _game_path, _raw = one_game_sample
        for s in samples:
            gt = s["ground_truth"]
            n_my = int(gt[:, 0].sum())
            n_played = int(gt[:, 1].sum())
            n_rest = int(gt[:, 2].sum())
            assert n_my + n_played + n_rest == TOTAL_SLOTS, (
                f"step={s['step_id']} 守恒失败 {n_my}+{n_played}+{n_rest} ≠ {TOTAL_SLOTS}"
            )

    def test_per_step_my_count_equals_hand_self_len(self, one_game_sample):
        samples, _game_path, _raw = one_game_sample
        for s in samples:
            gt = s["ground_truth"]
            n_my = int(gt[:, 0].sum())
            hand_len = len(s["hand_self"])
            assert n_my == hand_len, (
                f"step={s['step_id']} MY_HAND={n_my} ≠ hand_self={hand_len}"
            )


class TestHandProgression:
    """手牌单调递减（每步出牌后手牌数 ≤ 上一步）"""

    def test_hand_len_monotonic_non_increasing(self, one_game_sample):
        samples, _game_path, _raw = one_game_sample
        prev_len = None
        for s in samples:
            cur_len = len(s["hand_self"])
            if prev_len is not None:
                # lalala 数据偶尔有缺步或不一致，允许相等但不允许增加
                assert cur_len <= prev_len, (
                    f"step={s['step_id']} 手牌 {prev_len} → {cur_len} 不应增加"
                )
            prev_len = cur_len

    def test_verify_lalala_samples_passes(self, one_game_sample):
        samples, _game_path, _raw = one_game_sample
        assert verify_lalala_samples(samples) is True


class TestDiskNpzArtifacts:
    """已落盘的 lalala_*.npz 数据完整性"""

    def test_lalala_npz_count_on_disk(self):
        if not DATA_DIR.exists():
            pytest.skip(f"未找到 {DATA_DIR}（先跑 ETL）")
        lalala_npz = list(DATA_DIR.glob("lalala_*.npz"))
        # 当前 148 局 × 平均 26 步 ≈ 3860；阈值取下限 3500 保留增量缓冲
        assert len(lalala_npz) >= 3500, f"lalala 样本数 {len(lalala_npz)} 过少（≥3500）"
        assert len(lalala_npz) <= 5000, f"lalala 样本数 {len(lalala_npz)} 异常多（≤5000）"

    def test_lalala_npz_has_required_fields(self):
        npz_path = next(DATA_DIR.glob("lalala_*.npz"), None) if DATA_DIR.exists() else None
        if npz_path is None:
            pytest.skip("无 lalala 样本")
        d = np.load(npz_path, allow_pickle=True)
        required = {
            "ground_truth", "hand_self", "cur_rank", "history_raw",
            "done", "global_state", "stage",
            "decision_act_index", "decision_act_type", "decision_act_cards",
            "match_id", "step_id", "has_warning", "warning_cards",
        }
        missing = required - set(d.files)
        assert not missing, f"{npz_path.name} 缺少字段: {missing}"

    def test_lalala_npz_ground_truth_shape_and_dtype(self):
        npz_path = next(DATA_DIR.glob("lalala_*.npz"), None) if DATA_DIR.exists() else None
        if npz_path is None:
            pytest.skip("无 lalala 样本")
        d = np.load(npz_path, allow_pickle=True)
        gt = d["ground_truth"]
        assert gt.shape == (TOTAL_SLOTS, 3), f"ground_truth shape 错: {gt.shape}"
        assert gt.dtype == np.int8, f"ground_truth dtype 错: {gt.dtype}"

    def test_lalala_npz_history_raw_is_empty_placeholder(self):
        """lalala 数据无 history 字段，落盘时 history_raw 应为空占位 [4 个空 list]。"""
        npz_path = next(DATA_DIR.glob("lalala_*.npz"), None) if DATA_DIR.exists() else None
        if npz_path is None:
            pytest.skip("无 lalala 样本")
        d = np.load(npz_path, allow_pickle=True)
        history = d["history_raw"]
        # lalala 占位空：history_raw 应是 4 个空 list
        assert len(history) == 4, f"history_raw 长度 {len(history)} ≠ 4"
        for sub in history:
            assert len(sub) == 0, f"history_raw 子项非空（lalala 占位应为空）: {list(sub)}"

    def test_lalala_npz_iterable_via_helper(self):
        """iter_clean_samples 应能加载 lalala 样本且无 TypeError（验证 GUA-223 lalala 0-d 修复）"""
        from scripts.etl.botzone_to_counting_dataset import iter_clean_samples
        if not DATA_DIR.exists():
            pytest.skip(f"未找到 {DATA_DIR}")
        lalala_count = 0
        for s in iter_clean_samples(DATA_DIR, drop_warnings=True):
            if s["match_id"].startswith("lalala_"):
                lalala_count += 1
                # decision_act_cards 必须可迭代
                assert isinstance(s["decision_act_cards"], list), (
                    f"decision_act_cards 不是 list: {type(s['decision_act_cards'])}"
                )
                if lalala_count >= 5:
                    break
        assert lalala_count >= 1, "iter_clean_samples 未加载到任何 lalala 样本"
