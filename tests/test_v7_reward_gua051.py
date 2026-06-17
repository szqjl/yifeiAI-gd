# -*- coding: utf-8 -*-
"""GUA-051 稠密 Reward 信号 9 种 — 单元测试"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.v.nn.training.reward import (
    compute_step_reward,
    compute_episode_reward,
    _is_level_card,
    _is_good_bomb,
    RewardAccumulator,
    PLAY_SUCCESS_REWARD,
    WIND_CATCH_REWARD,
    GUAN_DAN_REWARD,
    LEVEL_CONTROL_REWARD,
    COORDINATION_REWARD,
    FEED_PARTNER_REWARD,
    GOOD_BOMB_REWARD,
    WASTE_BOMB_REWARD,
    SELF_UPGRADE_REWARD,
    OPPONENT_UPGRADE_REWARD,
)


def test_01_play_success():
    r = compute_step_reward(action=["Single", "3", ["S3"]], action_list=[["Single", "3", ["S3"]]], stage="play")
    assert r["play_success"] == PLAY_SUCCESS_REWARD
    assert r["total"] > 0


def test_02_play_pass_no_reward():
    r = compute_step_reward(action=["PASS"], action_list=[["Single", "3", ["S3"]], ["PASS"]], stage="play")
    assert r["play_success"] == 0.0


def test_03_wind_catch():
    r = compute_step_reward(
        action=["Pair", "33", ["S3", "H3"]],
        action_list=[["Pair", "33", ["S3", "H3"]]],
        my_pos=0, prev_greater_pos=1, greater_pos=0,
        stage="play",
    )
    assert r["wind_catch"] == WIND_CATCH_REWARD


def test_04_guan_dan():
    r = compute_step_reward(action=["Single", "K", ["SK"]], action_list=[["Single", "K", ["SK"]]], hand_count=5, stage="play")
    assert r["guan_dan"] == GUAN_DAN_REWARD


def test_05_level_control():
    r = compute_step_reward(
        action=["Single", "2", ["S2"]],
        action_list=[["Single", "2", ["S2"]]],
        cur_rank="2", self_rank="A", oppo_rank="K",
        stage="play",
    )
    assert r["level_control"] > 0


def test_06_coordination():
    r = compute_step_reward(
        action=["Pair", "33", ["S3", "H3"]],
        action_list=[["Pair", "33", ["S3", "H3"]]],
        my_pos=0, cur_pos=2, prev_greater_pos=2,
        stage="play",
    )
    assert r["coordination"] == COORDINATION_REWARD


def test_07_feed_partner():
    r = compute_step_reward(
        action=["Single", "3", ["S3"]],
        action_list=[["Single", "3", ["S3"]]],
        my_pos=0, cur_pos=2, prev_greater_pos=2,
        numofs={"numoffri": 2},
        stage="play",
    )
    assert r["feed_partner"] == FEED_PARTNER_REWARD


def test_08_good_bomb():
    r = compute_step_reward(
        action=["Bomb", "8", ["S8", "H8", "D8", "C8"]],
        action_list=[["Bomb", "8", ["S8", "H8", "D8", "C8"]]],
        bomb_used=True, hand_count=8, cur_bomb_num=1,
        stage="play",
    )
    assert r["bomb"] == GOOD_BOMB_REWARD


def test_09_episode_self_upgrade():
    r = compute_episode_reward(self_upgraded=True)
    assert r["self_upgrade"] == SELF_UPGRADE_REWARD
    assert r["total"] == SELF_UPGRADE_REWARD


def test_10_episode_opponent_upgrade():
    r = compute_episode_reward(opponent_upgraded=True)
    assert r["opponent_upgrade"] == OPPONENT_UPGRADE_REWARD
    assert r["total"] == OPPONENT_UPGRADE_REWARD


def test_11_reward_accumulator():
    acc = RewardAccumulator()
    acc.add_step_reward(compute_step_reward(action=["Single", "3", ["S3"]], action_list=[["Single", "3", ["S3"]]], stage="play"))
    acc.add_step_reward(compute_step_reward(action=["Pair", "44", ["S4", "H4"]], action_list=[["Pair", "44", ["S4", "H4"]]], stage="play"))
    acc.add_episode_reward(compute_episode_reward(self_upgraded=True))
    assert acc.total > 0
    bd = acc.breakdown
    assert bd["play_success"] == 2 * PLAY_SUCCESS_REWARD
    assert bd["self_upgrade"] == SELF_UPGRADE_REWARD
    acc.reset()
    assert acc.total == 0.0


def test_12_no_action_no_reward():
    r = compute_step_reward(action=[], action_list=[], stage="play")
    assert r["play_success"] == 0.0
    assert r["total"] == 0.0
