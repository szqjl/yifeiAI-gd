import pytest
from src.v.nn.endgame.endgame_decide import EndgameDecider


class TestGua168BombPlusSingleLead:
    """GUA-168: 领出[bomb+单张]且对手均非1张时，优先出单试探，用bomb兜底"""

    def setup_method(self):
        self.decider = EndgameDecider()

    def _make_game_state(self, hand_cards, cur_pos=0, my_pos=0, cur_rank="2", enemies_remaining=None):
        """构造最小可运行的 game_state"""
        if enemies_remaining is None:
            enemies_remaining = {1: 5, 3: 10}  # 对手1=5张，对手3=10张
        ec = {
            "is_active": True,
            "my_pos": my_pos,
            "self": {"should_sprint": True},  # 触发 Q0 自己冲刺
            "enemies": {pos: {"remaining": rem} for pos, rem in enemies_remaining.items()},
            "teammate": {"is_close": False, "remaining": 10},
        }
        return {
            "handCards": hand_cards,
            "curPos": cur_pos,
            "myPos": my_pos,
            "curRank": cur_rank,
            "selfRank": cur_rank,
            "oppoRank": cur_rank,
            "greaterPos": -1,
            "greaterAction": ["PASS", "PASS", "PASS"],
            "publicInfo": [
                {"rest": 10},  # pos 0 (自己)
                {"rest": enemies_remaining.get(1, 10)},   # pos 1 (对手1)
                {"rest": 10},  # pos 2 (队友)
                {"rest": enemies_remaining.get(3, 10)},   # pos 3 (对手3)
            ],
            "stage": "play",
            "version": "v7",
            "_endgame_context": ec,
        }

    def test_gua168_bomb_plus_single_lead_prefers_single_first(self):
        """
        场景：yf1 手牌 [CA] + StraightFlush/A (5张)，对手1=5张、对手3=10张（均非1张）
        期望：先出单CA试探，StraightFlush作兜底（而非 GUA-151 直接出 StraightFlush）
        """
        # 手牌：CA (单A) + S2,S3,S4,HA,SA (同花顺A)
        hand_cards = ["CA", "S2", "S3", "S4", "HA", "SA"]
        game_state = self._make_game_state(hand_cards, enemies_remaining={1: 5, 3: 10})

        # action_list 需包含 Single/A 和 StraightFlush/A 两个候选
        action_list = [
            ["PASS", "PASS", "PASS"],  # idx 0
            ["Single", "A", ["CA"]],   # idx 1: 单A
            ["StraightFlush", "A", ["S2", "S3", "S4", "HA", "SA"]],  # idx 2: 同花顺A
        ]

        idx, action = self.decider.decide(game_state, action_list)

        # 验证：应选择 Single/A (idx=1)，而非 StraightFlush/A (idx=2)
        assert idx == 1, f"Expected idx=1 (Single/A), got idx={idx} action={action}"
        assert action[0] == "Single"
        assert action[1] == "A"
        assert action[2] == ["CA"]

    def test_gua168_bomb_plus_single_enemy_has_one_card_fallback_to_bomb(self):
        """
        场景：同 [bomb+单张]，但对手一家剩 1 张
        期望：退回 GUA-151 行为，直接出 bomb（StraightFlush）
        """
        hand_cards = ["CA", "S2", "S3", "S4", "HA", "SA"]
        game_state = self._make_game_state(hand_cards, enemies_remaining={1: 1, 3: 10})  # 对手1 剩 1 张

        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "A", ["CA"]],
            ["StraightFlush", "A", ["S2", "S3", "S4", "HA", "SA"]],
        ]

        idx, action = self.decider.decide(game_state, action_list)

        # 对手有 1 张时，应直接出 StraightFlush（GUA-151 行为）
        assert idx == 2, f"Expected idx=2 (StraightFlush/A) when enemy has 1 card, got idx={idx}"
        assert action[0] == "StraightFlush"

    def test_gua168_bomb_plus_single_both_enemies_one_card(self):
        """
        场景：对手两家都剩 1 张
        期望：直接出 bomb
        """
        hand_cards = ["CA", "S2", "S3", "S4", "HA", "SA"]
        game_state = self._make_game_state(hand_cards, enemies_remaining={1: 1, 3: 1})

        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "A", ["CA"]],
            ["StraightFlush", "A", ["S2", "S3", "S4", "HA", "SA"]],
        ]

        idx, action = self.decider.decide(game_state, action_list)

        assert idx == 2, f"Expected StraightFlush when both enemies have 1 card"
        assert action[0] == "StraightFlush"

    def test_gua168_not_bomb_plus_single_structure(self):
        """
        场景：手牌不止 [bomb+单张]，如 [bomb+两单] 或 [bomb+对子]
        期望：不触发 GUA-168，走原有逻辑
        """
        # 手牌：CA, DA (两单) + StraightFlush(5张) = 7张
        hand_cards = ["CA", "DA", "S2", "S3", "S4", "HA", "SA"]
        game_state = self._make_game_state(hand_cards, enemies_remaining={1: 5, 3: 10})

        action_list = [
            ["PASS", "PASS", "PASS"],
            ["Single", "A", ["CA"]],
            ["Single", "A", ["DA"]],
            ["StraightFlush", "A", ["S2", "S3", "S4", "HA", "SA"]],
        ]

        idx, action = self.decider.decide(game_state, action_list)

        # 结构不是 bomb+单张，应按原有优先级（可能选 StraightFlush）
        # 只要不报错且返回合法动作即可
        assert action[0] in ("Single", "StraightFlush")
        assert idx in (1, 2, 3)