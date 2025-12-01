# -*- coding: utf-8 -*-
"""
知识库规则（从YAML文件转换）

此文件由 yaml_to_python_converter.py 自动生成。
包含所有从YAML规则文件转换而来的规则。

生成时间: 2025-12-01 10:28:34
源文件:
  - advanced_rules_example.yaml (5条规则)
  - rules_card_grouping.yaml (7条规则)
  - rules_card_interactions.yaml (8条规则)
  - rules_card_language.yaml (7条规则)
  - rules_passing_skills.yaml (7条规则)
  - structured_rules_example.yaml (5条规则)
"""

# 所有规则
KNOWLEDGE_RULES = [
  {
    "id": "complex_teammate_protection",
    "name": "复杂队友保护规则",
    "description": "使用嵌套条件判断队友保护",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "type": "or",
          "conditions": [
            {
              "field": "greater_pos",
              "op": "==",
              "value": "teammate_pos"
            },
            {
              "field": "cur_pos",
              "op": "==",
              "value": "teammate_pos"
            }
          ]
        },
        {
          "field": "teammate_cards",
          "op": "<=",
          "value": 5
        },
        {
          "type": "not",
          "condition": {
            "field": "min_opponent_cards",
            "op": "<=",
            "value": 3
          }
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 120
      }
    ],
    "priority": 9,
    "game_phase": "endgame"
  },
  {
    "id": "endgame_bomb_strategy",
    "name": "残局炸弹策略",
    "description": "使用函数判断残局并使用炸弹",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "type": "function",
          "name": "is_endgame",
          "args": []
        },
        {
          "type": "function",
          "name": "has_bomb",
          "args": []
        },
        {
          "field": "min_opponent_cards",
          "op": "<=",
          "value": 3
        }
      ]
    },
    "actions": [
      {
        "action_type": "Bomb",
        "score_adjust": 200
      }
    ],
    "priority": 10,
    "game_phase": "endgame"
  },
  {
    "id": "dynamic_threshold",
    "name": "动态阈值规则",
    "description": "使用函数计算动态阈值",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": {
            "type": "function",
            "name": "min",
            "args": [
              {
                "field": "teammate_cards"
              },
              {
                "field": "min_opponent_cards"
              }
            ]
          },
          "op": "<=",
          "value": {
            "type": "function",
            "name": "max",
            "args": [
              5,
              8
            ]
          }
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 100
      }
    ],
    "priority": 7
  },
  {
    "id": "card_type_check",
    "name": "牌型检查规则",
    "description": "检查当前牌型是否在允许列表中",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "action_type",
          "op": "in",
          "value": [
            "Pair",
            "ThreeWithTwo",
            "Straight"
          ]
        },
        {
          "field": "teammate_cards",
          "op": "<=",
          "value": 5
        }
      ]
    },
    "actions": [
      {
        "action_type": "other",
        "score_adjust": 80
      }
    ],
    "priority": 6
  },
  {
    "id": "complex_opponent_suppress",
    "name": "复杂对手压制",
    "description": "使用多层嵌套条件",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "type": "or",
          "conditions": [
            {
              "field": "min_opponent_cards",
              "op": "<=",
              "value": 3
            },
            {
              "type": "and",
              "conditions": [
                {
                  "field": "min_opponent_cards",
                  "op": "==",
                  "value": 4
                },
                {
                  "type": "function",
                  "name": "has_bomb",
                  "args": []
                }
              ]
            }
          ]
        },
        {
          "type": "not",
          "condition": {
            "field": "greater_pos",
            "op": "==",
            "value": "teammate_pos"
          }
        }
      ]
    },
    "actions": [
      {
        "action_type": "Bomb",
        "score_adjust": 150
      },
      {
        "action_type": "other",
        "score_adjust": 100
      }
    ],
    "priority": 9,
    "game_phase": "endgame"
  },
  {
    "id": "bomb_max_single_min",
    "name": "炸弹越多越好，单牌越少越好",
    "description": "组牌第一原则，优先考虑单牌越少越好，同时考虑炸弹越多越好",
    "source": "组牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        }
      ]
    },
    "actions": [
      {
        "action_type": "Bomb",
        "score_adjust": 30,
        "description": "鼓励保留炸弹"
      },
      {
        "action_type": "Single",
        "score_adjust": -20,
        "description": "惩罚产生单牌"
      }
    ],
    "priority": 8,
    "game_phase": "opening"
  },
  {
    "id": "main_attack_min_rounds",
    "name": "主攻组牌轮次优先",
    "description": "主攻组牌轮次越少越好，可以拆炸弹减少轮次",
    "source": "组牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "role",
          "op": "==",
          "value": "主攻"
        },
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        }
      ]
    },
    "actions": [
      {
        "action_type": "other",
        "score_adjust": 50,
        "description": "鼓励减少轮次的组牌方式"
      }
    ],
    "priority": 7,
    "game_phase": "opening"
  },
  {
    "id": "assist_attack_keep_bomb",
    "name": "助攻保留炸弹",
    "description": "助攻组牌保留炸弹，必要时阻击对方",
    "source": "组牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "role",
          "op": "==",
          "value": "助攻"
        },
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        }
      ]
    },
    "actions": [
      {
        "action_type": "Bomb",
        "score_adjust": 40,
        "description": "鼓励保留炸弹"
      }
    ],
    "priority": 7,
    "game_phase": "opening"
  },
  {
    "id": "break_4_bomb_for_flush",
    "name": "拆4头炸组同花顺",
    "description": "拆4头炸产生赘牌不超过两张，可以组同花顺；超过两张，一般不组同花顺",
    "source": "组牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        },
        {
          "field": "can_form_straight_flush",
          "op": "==",
          "value": True
        }
      ]
    },
    "actions": [
      {
        "action_type": "StraightFlush",
        "score_adjust": 60,
        "description": "如果赘牌<=2张，鼓励组同花顺"
      }
    ],
    "priority": 6,
    "game_phase": "opening"
  },
  {
    "id": "avoid_straight_creates_two_singles",
    "name": "组顺生两单避免",
    "description": "如果由于组顺子而造出两张以上单牌，则应放弃",
    "source": "组牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        },
        {
          "field": "straight_creates_singles",
          "op": ">=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "Straight",
        "score_adjust": -30,
        "description": "惩罚产生过多单牌的组顺"
      }
    ],
    "priority": 8,
    "game_phase": "opening"
  },
  {
    "id": "main_attack_consistent_pattern",
    "name": "主攻牌型套路化",
    "description": "主攻牌型尽量一致，保持连续进攻，一种牌型有小、中、大",
    "source": "组牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "role",
          "op": "==",
          "value": "主攻"
        },
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        }
      ]
    },
    "actions": [
      {
        "action_type": "other",
        "score_adjust": 40,
        "description": "鼓励保持牌型一致性"
      }
    ],
    "priority": 6,
    "game_phase": "opening"
  },
  {
    "id": "assist_attack_diverse_pattern",
    "name": "助攻牌型多样化",
    "description": "助攻尽量保持牌型多样，关键时候送队友",
    "source": "组牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "role",
          "op": "==",
          "value": "助攻"
        },
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        }
      ]
    },
    "actions": [
      {
        "action_type": "other",
        "score_adjust": 30,
        "description": "鼓励保持牌型多样性"
      }
    ],
    "priority": 5,
    "game_phase": "opening"
  },
  {
    "id": "straight_vs_three_with_two",
    "name": "顺子与三带二相克",
    "description": "顺子和三带二相克，对手出顺子多，则三带二少；对手出三带二多，则顺子少",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_straight_count",
          "op": ">=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "ThreeWithTwo",
        "score_adjust": 80,
        "description": "对手顺子多，鼓励出三带二"
      }
    ],
    "priority": 7,
    "game_phase": "midgame"
  },
  {
    "id": "three_with_two_many_straight_few",
    "name": "三带二多顺子少",
    "description": "对手出三带二多，则顺子少，应该出顺子",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_three_with_two_count",
          "op": ">=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "Straight",
        "score_adjust": 80,
        "description": "对手三带二多，鼓励出顺子"
      }
    ],
    "priority": 7,
    "game_phase": "midgame"
  },
  {
    "id": "pair_vs_trips",
    "name": "对子与三张相克",
    "description": "对子与三张相克，对手一直在打对子，则打三张；对手首打三张，则打对子",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_pair_count",
          "op": ">=",
          "value": 3
        }
      ]
    },
    "actions": [
      {
        "action_type": "Trips",
        "score_adjust": 70,
        "description": "对手对子多，鼓励出三张"
      }
    ],
    "priority": 6,
    "game_phase": "midgame"
  },
  {
    "id": "opponent_first_trips_play_pair",
    "name": "对手首打三张打对子",
    "description": "对手首打三张，要么对子少，要么对子大，则打对子",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_first_action",
          "op": "==",
          "value": "Trips"
        },
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        }
      ]
    },
    "actions": [
      {
        "action_type": "Pair",
        "score_adjust": 70,
        "description": "对手首打三张，鼓励出对子"
      }
    ],
    "priority": 6,
    "game_phase": "opening"
  },
  {
    "id": "single_pair_complementary",
    "name": "单牌对子互补",
    "description": "单牌和对子互补，对手单牌少，一般对子多；对手对子少，一般单牌多",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_single_count",
          "op": "<=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "Pair",
        "score_adjust": 60,
        "description": "对手单牌少，鼓励出对子"
      }
    ],
    "priority": 5,
    "game_phase": "midgame"
  },
  {
    "id": "bomb_many_three_with_two_few",
    "name": "炸弹多三带二少",
    "description": "炸弹多，则三带二少，原因很简单，四个头、五个头或同花顺多，三带二自然就少",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_bomb_count",
          "op": ">=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "ThreeWithTwo",
        "score_adjust": 50,
        "description": "对手炸弹多，鼓励出三带二"
      }
    ],
    "priority": 5,
    "game_phase": "midgame"
  },
  {
    "id": "bomb_many_single_probable",
    "name": "炸弹多单张概率高",
    "description": "炸弹多则单张概率就高一些，可以根据对手炸弹数量来判断单张的概率",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_bomb_count",
          "op": ">=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "Single",
        "score_adjust": 40,
        "description": "对手炸弹多，可以出单张试探"
      }
    ],
    "priority": 4,
    "game_phase": "midgame"
  },
  {
    "id": "straight_creates_single_pair",
    "name": "组顺子形成单和对子",
    "description": "组顺子通常会形成单张和对子的局面，牌手主动出过顺子后，又套了一手顺子，则可能有对子",
    "source": "掼蛋相生相克.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_straight_count",
          "op": ">=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "Pair",
        "score_adjust": 50,
        "description": "对手顺子多，可能有对子，鼓励出对子"
      }
    ],
    "priority": 5,
    "game_phase": "midgame"
  },
  {
    "id": "opening_small_single_strong",
    "name": "首发出小单牌牌力强",
    "description": "开局首发出小单牌，是牌力强的信息，队友要配合让队友争头游",
    "source": "掼蛋牌语.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        },
        {
          "field": "is_first_action",
          "op": "==",
          "value": True
        },
        {
          "field": "action_type",
          "op": "==",
          "value": "Single"
        },
        {
          "field": "single_rank",
          "op": "<",
          "value": 10
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 80,
        "description": "队友牌力强，鼓励PASS配合"
      }
    ],
    "priority": 7,
    "game_phase": "opening"
  },
  {
    "id": "opening_pair_uncertain",
    "name": "开局出对子情况不明",
    "description": "开局出对子，情况不明对子先行，出于尝试沟通，了解队友牌力",
    "source": "掼蛋牌语.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        },
        {
          "field": "is_first_action",
          "op": "==",
          "value": True
        },
        {
          "field": "action_type",
          "op": "==",
          "value": "Pair"
        }
      ]
    },
    "actions": [
      {
        "action_type": "Pair",
        "score_adjust": 40,
        "description": "中等对子防守，不建议卡压"
      }
    ],
    "priority": 5,
    "game_phase": "opening"
  },
  {
    "id": "opening_trips_weak",
    "name": "开局出三张弱牌",
    "description": "开局出小三张，向队友表示牌力弱，一般属于捣蛋牌、干扰牌",
    "source": "掼蛋牌语.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "phase",
          "op": "==",
          "value": "opening"
        },
        {
          "field": "is_first_action",
          "op": "==",
          "value": True
        },
        {
          "field": "action_type",
          "op": "==",
          "value": "Trips"
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 60,
        "description": "队友牌力弱，鼓励让队友上手"
      }
    ],
    "priority": 6,
    "game_phase": "opening"
  },
  {
    "id": "three_with_two_straight_relation",
    "name": "三带二与顺子关系",
    "description": "队友出三带二，原则上就顺子少；队友出顺子，原则上就对子多",
    "source": "掼蛋牌语.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_last_action",
          "op": "==",
          "value": "ThreeWithTwo"
        }
      ]
    },
    "actions": [
      {
        "action_type": "ThreeWithTwo",
        "score_adjust": 100,
        "description": "鼓励送三带二，不要出顺子"
      },
      {
        "action_type": "Straight",
        "score_adjust": -50,
        "description": "惩罚出顺子"
      }
    ],
    "priority": 8,
    "game_phase": "midgame"
  },
  {
    "id": "teammate_straight_send_straight_or_pair",
    "name": "队友出顺子送顺子或对子",
    "description": "队友若出的是顺子，队友上手后就要送顺子，送不了顺子就出对子或单张",
    "source": "掼蛋牌语.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_last_action",
          "op": "==",
          "value": "Straight"
        }
      ]
    },
    "actions": [
      {
        "action_type": "Straight",
        "score_adjust": 100,
        "description": "鼓励送顺子"
      },
      {
        "action_type": "Pair",
        "score_adjust": 60,
        "description": "也可以送对子"
      },
      {
        "action_type": "ThreeWithTwo",
        "score_adjust": -50,
        "description": "不要出三带二"
      }
    ],
    "priority": 8,
    "game_phase": "midgame"
  },
  {
    "id": "opponent_pass_keep_pattern",
    "name": "对手不接牌保留牌型",
    "description": "对手不接牌，可能没有这种牌型、或不是其优势牌型、或正在保留各种牌型",
    "source": "掼蛋牌语.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "opponent_last_action",
          "op": "==",
          "value": "PASS"
        },
        {
          "field": "cur_pos",
          "op": "!=",
          "value": "my_pos"
        }
      ]
    },
    "actions": [
      {
        "action_type": "other",
        "score_adjust": 30,
        "description": "可以继续出相同牌型试探"
      }
    ],
    "priority": 4,
    "game_phase": "midgame"
  },
  {
    "id": "prev_small_single_strong",
    "name": "上家出小单张牌力强",
    "description": "上家跟出最小单张牌，表明牌力较强，需要处理一些难以出掉牌",
    "source": "掼蛋牌语.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "prev_pos_last_action",
          "op": "==",
          "value": "Single"
        },
        {
          "field": "prev_pos_single_rank",
          "op": "<",
          "value": 10
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 50,
        "description": "上家牌力强，适度让牌"
      }
    ],
    "priority": 5,
    "game_phase": "midgame"
  },
  {
    "id": "teammate_5_cards_three_with_two",
    "name": "队友剩5张判断三带二",
    "description": "队友剩5张牌，明显是三带二，应该送三带二",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_cards",
          "op": "==",
          "value": 5
        },
        {
          "field": "phase",
          "op": "==",
          "value": "endgame"
        }
      ]
    },
    "actions": [
      {
        "action_type": "ThreeWithTwo",
        "score_adjust": 150,
        "description": "强烈鼓励送三带二"
      }
    ],
    "priority": 9,
    "game_phase": "endgame"
  },
  {
    "id": "teammate_9_10_cards_send_three_with_two",
    "name": "队友剩9-10张送三带二",
    "description": "队友剩9-10张牌，尽快要送三带二",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_cards",
          "op": ">=",
          "value": 9
        },
        {
          "field": "teammate_cards",
          "op": "<=",
          "value": 10
        },
        {
          "field": "phase",
          "op": "==",
          "value": "endgame"
        }
      ]
    },
    "actions": [
      {
        "action_type": "ThreeWithTwo",
        "score_adjust": 100,
        "description": "鼓励送三带二"
      }
    ],
    "priority": 8,
    "game_phase": "endgame"
  },
  {
    "id": "teammate_followed_three_pair_send_three_pair",
    "name": "队友跟三连对送三连对",
    "description": "队友跟了一手三连对，说明队友可能需要三连对，应该配合送牌",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_last_action",
          "op": "==",
          "value": "ThreePair"
        },
        {
          "field": "greater_pos",
          "op": "==",
          "value": "teammate_pos"
        }
      ]
    },
    "actions": [
      {
        "action_type": "ThreePair",
        "score_adjust": 120,
        "description": "鼓励送三连对"
      }
    ],
    "priority": 7,
    "game_phase": "midgame"
  },
  {
    "id": "teammate_straight_then_straight_has_pair",
    "name": "队友出顺子后可能有对子",
    "description": "队友主动出过顺子后，又套了一手顺子，则可能有对子，但一定不会有太多的对子",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_straight_count",
          "op": ">=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "Pair",
        "score_adjust": 80,
        "description": "鼓励送对子"
      }
    ],
    "priority": 6,
    "game_phase": "midgame"
  },
  {
    "id": "teammate_blocked_continue_send",
    "name": "传队友被拦截的牌",
    "description": "队友出某个牌型被对手拦截，未能回收，他手中大概率还有该类牌型要出",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_last_blocked",
          "op": "==",
          "value": True
        },
        {
          "field": "teammate_blocked_type",
          "op": "!=",
          "value": None
        }
      ]
    },
    "actions": [
      {
        "action_type": "other",
        "score_adjust": 100,
        "description": "鼓励送队友被拦截的牌型"
      }
    ],
    "priority": 8,
    "game_phase": "midgame"
  },
  {
    "id": "high_single_passing",
    "name": "高单传牌",
    "description": "将较大的单牌（10、J、Q、K）传递给队友，帮助队友组成更好的牌型或压制对手",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "role",
          "op": "==",
          "value": "助攻"
        },
        {
          "field": "has_single_advantage",
          "op": "==",
          "value": True
        }
      ]
    },
    "actions": [
      {
        "action_type": "Single",
        "score_adjust": 60,
        "description": "鼓励出高单传牌"
      }
    ],
    "priority": 5,
    "game_phase": "midgame"
  },
  {
    "id": "teammate_pass_observe_need",
    "name": "队友不要观察需求",
    "description": "队友不要（PASS），说明队友可能不需要当前牌型，应该观察队友需要什么牌型",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "teammate_last_action",
          "op": "==",
          "value": "PASS"
        },
        {
          "field": "cur_pos",
          "op": "==",
          "value": "teammate_pos"
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 50,
        "description": "鼓励观察队友需求"
      }
    ],
    "priority": 4,
    "game_phase": "midgame"
  },
  {
    "id": "teammate_protection_1_2",
    "name": "队友保护-即将获胜",
    "description": "队友剩余1-2张牌，即将获胜，必须让队友走",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "greater_pos",
          "op": "==",
          "value": "teammate_pos"
        },
        {
          "field": "teammate_cards",
          "op": "<=",
          "value": 2
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 150,
        "description": "极强烈鼓励PASS，让队友走"
      },
      {
        "action_type": "other",
        "score_adjust": -80,
        "description": "严重惩罚出牌"
      }
    ],
    "priority": 10,
    "game_phase": "endgame"
  },
  {
    "id": "teammate_protection_3_5",
    "name": "队友保护-残局阶段",
    "description": "队友剩余3-5张牌，残局阶段，应该保护队友",
    "source": "传牌技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "greater_pos",
          "op": "==",
          "value": "teammate_pos"
        },
        {
          "field": "teammate_cards",
          "op": "<=",
          "value": 5
        },
        {
          "field": "teammate_cards",
          "op": ">=",
          "value": 3
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": 100,
        "description": "强烈鼓励PASS"
      },
      {
        "action_type": "other",
        "score_adjust": -50,
        "description": "惩罚出牌"
      }
    ],
    "priority": 8,
    "game_phase": "endgame"
  },
  {
    "id": "opponent_suppress_1_3",
    "name": "对手压制-即将获胜",
    "description": "对手剩余1-3张牌，必须压制",
    "source": "出炸弹要领.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "min_opponent_cards",
          "op": "<=",
          "value": 3
        }
      ]
    },
    "actions": [
      {
        "action_type": "PASS",
        "score_adjust": -100,
        "description": "严重惩罚PASS"
      },
      {
        "action_type": "other",
        "score_adjust": 150,
        "description": "极强烈鼓励出牌压制"
      }
    ],
    "priority": 10,
    "game_phase": "endgame"
  },
  {
    "id": "fire_not_four",
    "name": "火不打四",
    "description": "对手4张时可能是炸弹，不要轻易用炸弹",
    "source": "出炸弹要领.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "min_opponent_cards",
          "op": "==",
          "value": 4
        }
      ]
    },
    "actions": [
      {
        "action_type": "Bomb",
        "score_adjust": -30,
        "description": "避免用炸弹"
      }
    ],
    "priority": 7,
    "game_phase": "endgame"
  },
  {
    "id": "five_pair",
    "name": "逢五出对",
    "description": "对手5张时优先出对子",
    "source": "对子技巧.md",
    "condition": {
      "type": "and",
      "conditions": [
        {
          "field": "min_opponent_cards",
          "op": "==",
          "value": 5
        }
      ]
    },
    "actions": [
      {
        "action_type": "Pair",
        "score_adjust": 100,
        "description": "强烈鼓励出对子"
      },
      {
        "action_type": "other",
        "score_adjust": 60,
        "description": "鼓励出牌"
      }
    ],
    "priority": 8,
    "game_phase": "endgame"
  }
]
