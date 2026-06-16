# -*- coding: utf-8 -*-
"""
掼蛋规则常量（一）牌张与基本概念 + 胜负与目标

规则依据：
- 牌张：docs/archive/rules/牌张与基本概念.md
- 胜负与目标：docs/archive/rules/胜负与目标.md（决策/策略/RL 须据此做目标对齐）
代码中涉及牌数、人数、默认手牌/剩余牌数、局目标时，应优先使用本模块常量。
"""

# ---------- 牌张 ----------
# 使用牌数：两副扑克牌，共 108 张
TOTAL_CARDS = 108

# 每副牌 54 张（52 张花色 + 2 张王），两副 108 张
CARDS_PER_DECK = 54
DECKS = 2
assert TOTAL_CARDS == CARDS_PER_DECK * DECKS, "108 = 54 * 2"

# 分配方式：四位牌手，每人 27 张
NUM_PLAYERS = 4
CARDS_PER_PLAYER = 27
assert TOTAL_CARDS == NUM_PLAYERS * CARDS_PER_PLAYER, "108 = 4 * 27"

# 默认剩余牌数（未从服务器获取时使用）
DEFAULT_REST_CARDS = CARDS_PER_PLAYER

# 默认“其他玩家”剩余牌数列表（3 人，每人 DEFAULT_REST_CARDS，用于 opponent_rest_cards_list 等）
DEFAULT_OTHERS_REST_LIST = [DEFAULT_REST_CARDS] * (NUM_PLAYERS - 1)

# 默认“全部玩家”剩余牌数列表（4 个位置，用于按位置索引的 rest 列表）
DEFAULT_ALL_REST_LIST = [DEFAULT_REST_CARDS] * NUM_PLAYERS

# ---------- 牌面编码（与协议一致） ----------
# 花色单字符：S 黑桃, H 红心, D 方块, C 梅花
SUIT_SPADE = "S"
SUIT_HEART = "H"
SUIT_DIAMOND = "D"
SUIT_CLUB = "C"
# 王：R 大王, B 小王（如 RJ/BJ 或 R/B）
SUIT_RED_JOKER = "R"
SUIT_BLACK_JOKER = "B"

# 花色中文名（用于展示/日志）
SUIT_NAMES = {
    "S": "黑桃",
    "H": "红心",
    "D": "方块",
    "C": "梅花",
    "B": "小王",
    "R": "大王",
}

# ---------- 胜负与目标（决策引擎必须遵循） ----------
# 每副牌的目标：己方有人争头游，且尽量二游也是己方；头游+二游同方即该方获胜。
GAME_OBJECTIVE = "每副牌争头游，己方头游+二游即获胜；牌力强主攻冲刺，牌力弱助攻掩护。"
# 强化赢的意识：一切出牌与配合均围绕「己方赢」
WIN_FIRST_PRIORITY = "本局唯一目标：己方赢（头游+二游）；一切出牌围绕争头游、保二游，不赢则无意义。"

# 名次（1=最先出完 … 4=最后出完）
RANK_FIRST = 1   # 头游
RANK_SECOND = 2  # 二游
RANK_THIRD = 3   # 三游
RANK_LAST = 4    # 末游
RANK_NAMES = {
    RANK_FIRST: "头游",
    RANK_SECOND: "二游",
    RANK_THIRD: "三游",
    RANK_LAST: "末游",
}
# 头游+二游为获胜方（同一队）
WINNING_RANKS = (RANK_FIRST, RANK_SECOND)

# ---------- 概念说明（与规则文档对应，仅作注释） ----------
# 一副牌（episode）：108 张发完 →（第二副起进贡/还贡或抗贡）→ 多圈出牌 → 四人完牌顺序确定 → 升级
# 代码对应：game_recorder start_game ~ end_game / episodeOver（变量名 game 指一副，勿与「一局」混淆）
# 一手牌：牌手一次打出的一组牌 → 代码中 actionList 的一个元素
# 一圈牌：四人依次出牌直到连续三人过牌 → 代码中由 curAction、greater_pos 及 act 流程体现
