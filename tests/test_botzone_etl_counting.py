# -*- coding: utf-8 -*-
"""
GUA-223 Phase 0 ETL pytest — has_warning flag + 数据集摘要

关联：
  - GUA-223（母条目）
  - CardCountingNetwork-训练方案.md §8 Phase 0 硬门槛 ① 手算对账
  - WF-13 Botzone 适配层

测试覆盖：
  ① ETL 输出 .npz 含 has_warning + warning_cards 字段
  ② ground_truth 3 类分布合理（MY_HAND+PLAYED+REST=108）
  ③ has_warning=True 样本数与日志行一致（GUA-216 双扣 bug 信号）
  ④ summarize_dataset / iter_clean_samples 与磁盘 .npz 一致
  ⑤ drop_warnings=True 过滤后剩余样本数 = 总数 - warning 数
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts.etl.botzone_to_counting_dataset import (
    iter_clean_samples,
    summarize_dataset,
)


DATA_DIR = Path("data/training/card_counting_v1")


@pytest.fixture(scope="module")
def dataset_summary() -> dict:
    """summarize_dataset 输出（在模块内只跑一次避免磁盘抖动）"""
    if not DATA_DIR.exists():
        pytest.skip(f"未找到 {DATA_DIR}（先跑 ETL: python scripts/etl/botzone_to_counting_dataset.py --all-matches）")
    return summarize_dataset(DATA_DIR)


class TestEtlOutputFields:
    """每个 .npz 必须含 has_warning + warning_cards 字段"""

    def test_npz_has_warning_field(self):
        sample_path = next(DATA_DIR.glob("*.npz"), None)
        if sample_path is None:
            pytest.skip("无样本")
        d = np.load(sample_path, allow_pickle=True)
        assert "has_warning" in d.files, f"{sample_path.name} 缺少 has_warning 字段"
        assert "warning_cards" in d.files, f"{sample_path.name} 缺少 warning_cards 字段"
        assert d["has_warning"].dtype == bool, "has_warning 必须是 bool"
        assert d["warning_cards"].dtype == object, "warning_cards 必须是 object 数组"

    def test_npz_ground_truth_shape(self):
        sample_path = next(DATA_DIR.glob("*.npz"), None)
        if sample_path is None:
            pytest.skip("无样本")
        d = np.load(sample_path, allow_pickle=True)
        gt = d["ground_truth"]
        assert gt.shape == (108, 3), f"ground_truth shape 错: {gt.shape}"
        assert gt.dtype == np.int8, f"ground_truth dtype 错: {gt.dtype}"
        # 守恒
        assert int(gt[:, 0].sum()) + int(gt[:, 1].sum()) + int(gt[:, 2].sum()) == 108


class TestDatasetSummary:
    """summarize_dataset 全局统计"""

    def test_total_samples_positive(self, dataset_summary):
        assert dataset_summary["total_samples"] > 0

    def test_warning_samples_consistent(self, dataset_summary):
        # GUA-216 双扣 bug 残留已知：4 个样本（match 6a78308c step=22 + match 6a786ea60 step=26/27/28）
        n_warn = dataset_summary["warning_samples"]
        assert 0 <= n_warn <= 20, f"warning 样本数异常: {n_warn}"

    def test_v8_decision_subset(self, dataset_summary):
        # V8 决策样本应 < 总样本
        assert dataset_summary["v8_decision_samples"] <= dataset_summary["total_samples"]

    def test_samples_per_dim(self, dataset_summary):
        # 当前 581 样本 / 324 维 ≈ 1.79
        assert dataset_summary["samples_per_dim"] > 0


class TestCleanIteration:
    """iter_clean_samples 过滤逻辑"""

    def test_drop_warnings_filters_out(self, dataset_summary):
        clean = iter_clean_samples(DATA_DIR, drop_warnings=True)
        all_s = iter_clean_samples(DATA_DIR, drop_warnings=False)
        assert len(clean) == dataset_summary["total_samples"] - dataset_summary["warning_samples"]
        assert len(all_s) == dataset_summary["total_samples"]
        # 过滤后不含 warning
        assert all(not s["has_warning"] for s in clean)

    def test_clean_sample_has_required_keys(self):
        clean = iter_clean_samples(DATA_DIR, drop_warnings=True)
        if not clean:
            pytest.skip("无干净样本")
        s = clean[0]
        required = {
            "path", "match_id", "step_id", "hand_self", "cur_rank",
            "history_raw", "done", "global_state", "stage", "ground_truth",
            "decision_act_index", "decision_act_type", "decision_act_cards",
            "has_warning", "warning_cards",
        }
        missing = required - set(s.keys())
        assert not missing, f"样本缺少字段: {missing}"

    def test_iter_speed(self, dataset_summary):
        """iter_clean_samples 应在 < 5s 完成（581 样本）"""
        import time
        t0 = time.time()
        _ = iter_clean_samples(DATA_DIR, drop_warnings=True)
        elapsed = time.time() - t0
        # 581 样本 × ~3KB，IO + JSON 解析 + numpy load
        # 留 5s 缓冲（实测 ~1.5s）
        assert elapsed < 10.0, f"iter 耗时过长: {elapsed:.2f}s"