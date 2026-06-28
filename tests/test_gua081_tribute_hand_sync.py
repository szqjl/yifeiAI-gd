# -*- coding: utf-8 -*-
"""GUA-081: 贡还 adjust 同步 all_players_hands，卡牌验证不误报。"""

from src.communication.v7_game_recorder import GameRecorder


def test_back_add_syncs_all_players_hands_for_validation():
    rec = GameRecorder(player_id=0, player_name="yf1_v7")
    rec.start_game(["S8", "H2", "D5"], my_pos=0)

    rec.adjust_initial_hand_for_tribute_back("S5", "remove")
    rec.adjust_initial_hand_for_tribute_back("S8", "add")

    assert rec.current_game["initial_hand"].count("S8") == 2
    assert rec.current_game["all_players_hands"]["0"].count("S8") == 2

    rec._validate_action_cards(0, ["Pair", "8", ["S8", "S8"]])
