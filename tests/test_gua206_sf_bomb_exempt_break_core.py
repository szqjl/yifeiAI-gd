# -*- coding: utf-8 -*-
"""
GUA-206 完整同花顺/炸弹不判「拆核心」 单元测试

背景（2026-08-06，match=6a74198a27e7bf01db12e8e6 step20/22）：
  组牌引擎优先组同花顺、用 H2 配子补 SF（['SA','S2','S3','S4','H2']），
  而平台 actionList 枚举完整同花顺用真实牌（['SA','S2','S3','S4','S5']）。
  两张同花顺牌面 set 不同，_action_breaks_core_structure 用 set 精确比较
  {SA,S2,S3,S4} != {SA,S2,S3,S4,H2} → 误判「拆核心」→ 强压敌炸被 PASS。

修复：同花顺/炸弹本身是最高等级核心整牌（同花顺 > 5星炸 > 4星炸，
  组牌引擎 _score_power 同花顺 +3、普通炸弹 +2 已体现），出完整炸弹类
  动作 = 用核心压敌，绝非 GUA-199 要拦的「拆核心打弱牌」，直接豁免。
"""
import pytest
from src.v.nn.endgame.endgame_decide import EndgameDecider


# 复现局（step20 残局）组牌产出：SF 用 H2 配子，S5 被分进对子组
GROUP_MEMBERS = {
    -1: ['D7'],
    0: ['C3', 'D3', 'H3', 'H3'],      # Bomb
    1: ['SA', 'S2', 'S3', 'S4', 'H2'],  # StraightFlush（H2 配子补黑桃5）
    2: ['H4', 'H4'],
    3: ['C5', 'S5'],
    4: ['C6', 'D6'],
}
GID_TYPE = {
    0: 'Bomb',
    1: 'StraightFlush',
    2: 'pair_in_three_pair',
    3: 'pair_in_three_pair',
    4: 'pair_in_three_pair',
}
GS = {'_group_members': GROUP_MEMBERS, '_group_gid_type_map': GID_TYPE}


def test_full_straight_flush_real_cards_not_break():
    """完整同花顺（真实黑桃 A2345，与组牌 H2 配子版牌面不同）不判拆核心。"""
    act = ['StraightFlush', 'A', ['SA', 'S2', 'S3', 'S4', 'S5']]
    assert EndgameDecider._action_breaks_core_structure(act, GS) is False


def test_full_straight_flush_wild_cards_not_break():
    """完整同花顺（H2 配子补黑桃5，与组牌一致）不判拆核心。"""
    act = ['StraightFlush', 'A', ['SA', 'S2', 'S3', 'S4', 'H2']]
    assert EndgameDecider._action_breaks_core_structure(act, GS) is False


def test_full_bomb_not_break():
    """完整炸弹不判拆核心。"""
    act = ['Bomb', '3', ['C3', 'D3', 'H3', 'H3']]
    assert EndgameDecider._action_breaks_core_structure(act, GS) is False


def test_gua199_pair_break_still_blocked():
    """GUA-199 场景仍拦截：444+H2 拆 H2 打 22 对子（action 是 Pair，非炸弹类）。"""
    gs = {'_group_members': {0: ['C4', 'D4', 'H4', 'H2']},
          '_group_gid_type_map': {0: 'Bomb'}}
    act = ['Pair', '2', ['H2', 'D2']]
    assert EndgameDecider._action_breaks_core_structure(act, gs) is True


def test_ordinary_straight_break_still_detected():
    """普通顺子拆核心仍应检测（非炸弹类豁免范围）。"""
    # 组牌：三带二 444+55 拆成顺子 4-5-6-7-8 会破坏 TWT 核心
    gs = {'_group_members': {0: ['C4', 'D4', 'H4'], 1: ['C5', 'S5']},
          '_group_gid_type_map': {0: 'trip_in_three_with_two', 1: 'pair_in_three_with_two'}}
    act = ['Straight', '4', ['C4', 'D4', 'S5', 'C6', 'H7']]
    # 动作含 4 两张 + 5 一张（与核心组部分重叠）→ 拆核心
    assert EndgameDecider._action_breaks_core_structure(act, gs) is True
