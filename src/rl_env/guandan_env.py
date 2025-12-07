import gymnasium as gym
from gymnasium import spaces
import numpy as np
from .game_engine import GameEngine

class GuandanEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(GuandanEnv, self).__init__()
        self.engine = GameEngine()
        
        # Action Space: 
        # **关键修复**：动作空间必须是512维，与状态空间一致
        # 每个维度对应一个卡牌索引位置（0-59是有效卡牌，60-511保留用于扩展）
        # 1 = 选择该索引对应的卡牌, 0 = 不选择
        self.action_space = spaces.MultiBinary(512) 
        
        # Observation Space:
        # 增强版：512维状态向量
        # - 0-59: 手牌（60维）
        # - 60-119: 桌牌/历史（60维，保留）
        # - 120-122: 游戏阶段（3维：开局/中期/残局）
        # - 123-126: 玩家剩余牌数（4维：归一化到0-1）
        # - 127-136: 上一步动作类型（10维：one-hot编码）
        # - 137-151: 上一步动作牌点（15维：one-hot编码）
        # - 152: 是否能顺牌（1维）
        # - 153: 是否能跟牌（1维）
        # - 154: 是否需要控牌（1维）
        # - 155-511: 保留扩展（357维）
        self.observation_space = spaces.Box(low=0, high=1, shape=(512,), dtype=np.float32)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        state = self.engine.reset()
        return self._encode_state(state), {}

    def step(self, action):
        # Convert MultiBinary action to card list
        # action is array of 0/1 of length 512
        # 只使用有效索引（0-59）对应的卡牌
        valid_indices = [i for i, x in enumerate(action) if x == 1 and i < 60]
        selected_cards = valid_indices  # 这里需要将索引转换为实际卡牌，暂时使用索引
        
        try:
            next_state, reward, done, info = self.engine.step(selected_cards)
            
            # Reward Shaping
            if done:
                # Check if my team won
                pass
                
            return self._encode_state(next_state), reward, done, False, info
            
        except ValueError as e:
            # Invalid move
            # Penalty for invalid move
            return self._encode_state(self.engine.get_state()), -10, False, False, {"error": str(e)}

    def _encode_state(self, state):
        """
        编码游戏状态为512维向量（增强版：包含策略特征）
        必须与 rl_decision_engine.py 中的 _preprocess_state 保持一致！
        
        状态编码结构：
        - 0-59: 手牌（60维）
        - 60-119: 桌牌/历史（60维，保留）
        - 120-122: 游戏阶段（3维：开局/中期/残局）
        - 123-126: 玩家剩余牌数（4维：归一化到0-1）
        - 127-136: 上一步动作类型（10维：one-hot编码）
        - 137-151: 上一步动作牌点（15维：one-hot编码）
        - 152: 是否能顺牌（1维）
        - 153: 是否能跟牌（1维）
        - 154: 是否需要控牌（1维）
        - 155-511: 保留扩展（357维）
        """
        obs = np.zeros(512, dtype=np.float32)
        
        # 获取当前玩家的手牌
        current_player = state.get('current_player', 0)
        hands = state.get('hands', {})
        hand_cards = hands.get(current_player, [])
        
        # 使用与推理代码相同的编码方式
        def card_to_index(card_code):
            """与 rl_decision_engine.py 中的编码方式完全一致"""
            suit_map = {'S': 0, 'H': 1, 'C': 2, 'D': 3}
            rank_map = {
                '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
                'B': 13,  # 小王
                'R': 14   # 大王
            }
            if len(card_code) >= 2:
                suit = card_code[0]
                rank = card_code[1]
                suit_val = suit_map.get(suit, 0)
                rank_val = rank_map.get(rank, 0)
                idx = suit_val * 15 + rank_val
                return min(idx, 59)  # 确保在0-59范围内
            return 0
        
        # 1. 编码手牌（0-59维）
        for card in hand_cards:
            idx = card_to_index(card)
            if idx < 60:
                obs[idx] = 1.0
        
        # 2. 编码游戏阶段（120-122维）
        # 根据剩余牌数判断阶段
        player_rest_cards = len(hand_cards)
        opponent_rest_cards = []
        for i in range(4):
            if i != current_player:
                opponent_rest_cards.append(len(hands.get(i, [])))
        min_opponent_cards = min(opponent_rest_cards) if opponent_rest_cards else 27
        
        # 判断游戏阶段
        if min_opponent_cards >= 20:
            game_phase = 0  # 开局
        elif min_opponent_cards >= 10:
            game_phase = 1  # 中期
        else:
            game_phase = 2  # 残局
        
        obs[120 + game_phase] = 1.0
        
        # 3. 编码玩家剩余牌数（123-126维，归一化到0-1）
        all_players_cards = [len(hands.get(i, [])) for i in range(4)]
        for i, card_count in enumerate(all_players_cards):
            if i < 4:
                obs[123 + i] = card_count / 27.0  # 归一化
        
        # 4. 编码上一步动作（127-151维）
        last_action = state.get('last_action', {})
        if last_action:
            action_type = last_action.get('type', '')
            action_cards = last_action.get('cards', [])
            
            # 动作类型编码（127-136维）
            action_type_map = {
                'PASS': 0, 'Single': 1, 'Pair': 2, 'Trips': 3,
                'Straight': 4, 'ThreeWithTwo': 5, 'Bomb': 6,
                'StraightFlush': 7, 'ThreePair': 8, 'TwoTrips': 9
            }
            action_type_idx = action_type_map.get(action_type, 0)
            if action_type_idx < 10:
                obs[127 + action_type_idx] = 1.0
            
            # 动作牌点编码（137-151维）
            if action_cards:
                first_card = action_cards[0]
                rank_map = {
                    '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                    'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
                    'B': 13, 'R': 14
                }
                if len(first_card) >= 2:
                    rank = first_card[1] if len(first_card) == 2 else first_card[1:2]
                    rank_idx = rank_map.get(rank, 0)
                    if rank_idx < 15:
                        obs[137 + rank_idx] = 1.0
        
        # 5. 编码策略特征（152-154维）
        # 是否能顺牌（上家出牌，自己能跟）
        can_follow = 0.0
        if last_action and last_action.get('type') == 'Single':
            # 简化判断：有能跟的单牌
            can_follow = 1.0 if len(hand_cards) > 0 else 0.0
        obs[152] = can_follow
        
        # 是否能跟牌（对手出牌，自己能跟）
        can_followup = 0.0
        if last_action and last_action.get('type') != 'PASS':
            can_followup = 1.0 if len(hand_cards) > 0 else 0.0
        obs[153] = can_followup
        
        # 是否需要控牌（对手快走完）
        need_control = 1.0 if min_opponent_cards <= 5 else 0.0
        obs[154] = need_control
        
        return obs

    def render(self, mode='human'):
        print(f"Current Player: {self.engine.current_player}")
        print(f"Table: {self.engine.table_cards}")
