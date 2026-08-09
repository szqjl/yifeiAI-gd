# -*- coding: utf-8 -*-
"""
GUA-223 / CardCountingNetwork-训练方案 §8 Phase 0 ③
规则记牌 baseline 推理精度测量

> 真源：docs/guandan-brain/CardCountingNetwork-训练方案.md §8 Phase 0 ③
> 数据：data/training/card_counting_v1/（581 样本）

输出指标（与 NN 训练后对比）：
  - trivial baseline：全部预测 REST（最常见类）
  - per-sample history-only baseline：PLAYED=当前 step history 累计 / REST=其余
  - 与 NN 的对比将作为"NN 是否超越 baseline"的硬门槛

用法：
    python scripts/bench_rule_card_counting.py
    python scripts/bench_rule_card_counting.py --drop-warnings  # 仅干净样本
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np


sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.etl.botzone_to_counting_dataset import (
    TOTAL_SLOTS,
    bz_int_to_v8,
    iter_clean_samples,
    parse_history_entries,
    v8_to_slot,
)


def trivial_baseline_acc(samples: List[dict]) -> Dict[str, float]:
    """全部预测 REST（最常见类）。"""
    n_total = 0
    n_correct = 0
    for s in samples:
        gt = s["ground_truth"]
        pred = np.zeros_like(gt)
        pred[:, 2] = 1
        n_correct += int((pred * gt).sum())
        n_total += TOTAL_SLOTS
    return {
        "name": "trivial-REST",
        "val_acc": n_correct / n_total if n_total > 0 else 0,
        "n_total": n_total,
    }


def history_only_baseline_acc(samples: List[dict]) -> Dict[str, float]:
    """仅用当前 step history 的 baseline（模拟"模型只能看到当前步请求"）。

    注：单 step history 不含前面 step 的累计——这是对"模型推理能力"
    的合理 baseline。如果 NN 只能输出与单 step history 一致的结果，它
    仍然在做一个有意义的"按 history 分类"任务；如果能复现 ETL 全 match
    累计的 ground truth，说明 NN 在做时序整合。
    """
    n_total = 0
    n_correct = 0
    n_my_correct = 0
    n_my_total = 0
    n_played_correct = 0
    n_played_total = 0
    n_rest_correct = 0
    n_rest_total = 0
    for s in samples:
        gt = s["ground_truth"]  # (108, 3) one-hot
        # 从当前 step history 累计（不含前面 step）
        history = s["history_raw"]
        played_counter = [0] * 54
        parsed = parse_history_entries(history)
        for _player_id, action_cards, _claim in parsed:
            for ci in action_cards:
                try:
                    v8 = bz_int_to_v8(int(ci))
                except (TypeError, ValueError):
                    continue
                slot = v8_to_slot(v8)
                if played_counter[slot] < 2:
                    played_counter[slot] += 1
        # 我方手牌
        my_counter = [0] * 54
        for v8 in s["hand_self"]:
            slot = v8_to_slot(v8)
            if my_counter[slot] < 2:
                my_counter[slot] += 1
        # 构造 baseline pred（贪心：先 MY_HAND 后 PLAYED 后 REST）
        pred = np.zeros((TOTAL_SLOTS, 3), dtype=np.int8)
        for slot in range(54):
            for deck in range(2):
                idx = slot + deck * 54
                if my_counter[slot] > 0:
                    pred[idx] = [1, 0, 0]
                    my_counter[slot] -= 1
                elif played_counter[slot] > 0:
                    pred[idx] = [0, 1, 0]
                    played_counter[slot] -= 1
                else:
                    pred[idx] = [0, 0, 1]
        # 评估
        match = (pred == gt).all(axis=1)
        n_correct += int(match.sum())
        n_total += TOTAL_SLOTS
        # 分项 recall
        n_my_correct += int(((pred[:, 0] == 1) & (gt[:, 0] == 1)).sum())
        n_my_total += int((gt[:, 0] == 1).sum())
        n_played_correct += int(((pred[:, 1] == 1) & (gt[:, 1] == 1)).sum())
        n_played_total += int((gt[:, 1] == 1).sum())
        n_rest_correct += int(((pred[:, 2] == 1) & (gt[:, 2] == 1)).sum())
        n_rest_total += int((gt[:, 2] == 1).sum())
    return {
        "name": "history-only",
        "val_acc": n_correct / n_total if n_total > 0 else 0,
        "n_total": n_total,
        "my_recall": n_my_correct / n_my_total if n_my_total > 0 else 0,
        "played_recall": n_played_correct / n_played_total if n_played_total > 0 else 0,
        "rest_recall": n_rest_correct / n_rest_total if n_rest_total > 0 else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="规则记牌 baseline 推理精度测量")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/training/card_counting_v1"),
        help="样本目录",
    )
    parser.add_argument(
        "--drop-warnings",
        action="store_true",
        help="跳过 has_warning=True 样本",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("bench_rule_card_counting")

    if not args.data_dir.exists():
        logger.error("❌ %s 不存在，先跑 ETL: python scripts/etl/botzone_to_counting_dataset.py --all-matches", args.data_dir)
        sys.exit(1)

    samples = iter_clean_samples(args.data_dir, drop_warnings=args.drop_warnings)
    logger.info("样本数: %d（drop_warnings=%s）", len(samples), args.drop_warnings)

    trivial = trivial_baseline_acc(samples)
    logger.info("=" * 60)
    logger.info("Baseline 1: %s → val_acc=%.4f (n_total=%d)",
                trivial["name"], trivial["val_acc"], trivial["n_total"])

    hist = history_only_baseline_acc(samples)
    logger.info("Baseline 2: %s → val_acc=%.4f", hist["name"], hist["val_acc"])
    logger.info("  MY_HAND recall: %.4f", hist["my_recall"])
    logger.info("  PLAYED recall:  %.4f", hist["played_recall"])
    logger.info("  REST recall:    %.4f", hist["rest_recall"])

    logger.info("=" * 60)
    logger.info("NN 目标：val_acc > %.4f（history-only baseline）才视为超越规则",
                hist["val_acc"])
    logger.info("NN 目标（修订）：当前 577 样本下，val_acc > trivial=%.4f 即视为形式可行",
                trivial["val_acc"])


if __name__ == "__main__":
    main()