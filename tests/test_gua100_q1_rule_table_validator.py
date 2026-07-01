# -*- coding: utf-8 -*-
"""GUA-100：Q1 规则表静态校验脚手架。"""

from src.v.nn.endgame.endgame_preprocessor import (
    format_q1_rule_table_validation_errors,
    validate_q1_rule_table_consistency,
)


def test_q1_rule_table_validator_passes_current_tables():
    """当前主表应静态自洽。"""
    assert validate_q1_rule_table_consistency() == []


def test_q1_rule_table_validator_catches_endgame_overlap():
    """推荐牌型映射后若与 banned_types 冲突，应被静态拦截。"""
    errors = validate_q1_rule_table_consistency(
        endgame_rules={3: ("高", ["单张", "对子"], ["Single", "Trips"])},
        baoshu_rules={},
    )

    assert any(
        error["table"] == "endgame_rule"
        and error["remaining"] == 3
        and error["code"] == "recommended_banned_overlap"
        and error["overlap"] == ["Single"]
        for error in errors
    )


def test_q1_rule_table_validator_catches_baoshu_overlap():
    """BAOSHU 的 block_with / never_play 若打架，也应被静态拦截。"""
    errors = validate_q1_rule_table_consistency(
        endgame_rules={},
        baoshu_rules={1: ("单张(听牌)", ["Bomb", "Single"], ["Single"])},
    )

    assert any(
        error["table"] == "BAOSHU_RULE"
        and error["remaining"] == 1
        and error["code"] == "block_with_never_play_overlap"
        and error["overlap"] == ["Single"]
        for error in errors
    )


def test_q1_rule_table_validator_formats_errors_for_cli():
    """CLI 输出应包含 remaining/table/code 关键信息。"""
    errors = validate_q1_rule_table_consistency(
        endgame_rules={3: ("高", ["单张"], ["Single"])},
        baoshu_rules={},
    )

    rendered = format_q1_rule_table_validation_errors(errors)

    assert "[endgame_rule][remaining=3][recommended_banned_overlap]" in rendered
    assert "overlap: Single" in rendered
