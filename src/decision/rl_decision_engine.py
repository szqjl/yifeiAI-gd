import torch
import numpy as np
from typing import List, Dict, Optional
import logging
from src.rl_agent.agent import PPOAgent
# Assuming we have a base class or interface, but for now standalone
# from .base_decision_engine import BaseDecisionEngine 

class RLDecisionEngine:
    def __init__(self, model_path="models/bc_model_stage5_ultra_optimized.pth", use_stage5_model=True):
        """
        RL决策引擎 - 支持阶段5增强模型

        Args:
            model_path: 模型路径
            use_stage5_model: 是否使用阶段5增强模型 (ImprovedGuandanPolicyNet)
        """
        self.logger = logging.getLogger("RLDecisionEngine")
        self.use_stage5_model = use_stage5_model
        self.model_loaded = False
        self.model_path = model_path

        if use_stage5_model:
            # 使用阶段5增强模型 (ImprovedGuandanPolicyNet)
            try:
                from src.rl_agent.model import ImprovedGuandanPolicyNet
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                self.policy_net = ImprovedGuandanPolicyNet(
                    input_dim=512, hidden_dim=256, output_dim=512,
                    dropout_rate=0.1, enable_strategy_head=True, attention_heads=8
                ).to(self.device)

                # 尝试加载阶段5模型
                try:
                    checkpoint = torch.load(model_path, map_location='cpu')
                    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
                        self.policy_net.load_state_dict(checkpoint['model_state_dict'], strict=False)
                    else:
                        self.policy_net.load_state_dict(checkpoint, strict=False)

                    self.model_loaded = True
                    self.logger.info(f"✓ RL Engine loaded Ultra Optimized model from {model_path}")
                    print(f"RL Engine loaded Ultra Optimized model from {model_path}")
                    
                    # 输出模型信息（如果有）
                    if isinstance(checkpoint, dict):
                        if 'final_action_exact_accuracy' in checkpoint:
                            print(f"  Model performance - Exact match: {checkpoint['final_action_exact_accuracy']:.2%}")
                        if 'final_strategy_understanding_rate' in checkpoint:
                            print(f"  Model performance - Strategy understanding: {checkpoint['final_strategy_understanding_rate']:.2%}")

                except Exception as e:
                    # 如果阶段5模型加载失败，回退到PPOAgent
                    self.logger.warning(f"Failed to load Stage5 model: {e}. Falling back to PPOAgent.")
                    print(f"Failed to load Stage5 model: {e}. Falling back to PPOAgent.")
                    self._init_ppo_fallback()

            except ImportError as e:
                self.logger.warning(f"Stage5 model not available: {e}. Using PPOAgent fallback.")
                print(f"Stage5 model not available: {e}. Using PPOAgent fallback.")
                self._init_ppo_fallback()

        else:
            # 使用传统PPOAgent
            self._init_ppo_fallback()

    def _init_ppo_fallback(self):
        """初始化PPOAgent作为回退方案"""
        from src.rl_agent.agent import PPOAgent
        self.agent = PPOAgent(input_dim=512, action_dim=512, prediction_threshold=0.3)
        self.use_stage5_model = False

        try:
            self.agent.load(self.model_path)
            self.model_loaded = True
            self.logger.info(f"✓ RL Engine loaded PPO model from {self.model_path}")
            print(f"RL Engine loaded PPO model from {self.model_path}")
        except Exception as e:
            error_msg = f"Failed to load RL model: {e}. Using random weights (Not recommended for production)."
            self.logger.warning(error_msg)
            print(error_msg)
            self.model_loaded = False

    def _stage5_model_inference(self, state_vec: np.ndarray, context: Optional[Dict] = None) -> np.ndarray:
        """
        超优化版模型推理（支持阶段6动态阈值和概率校准）

        Args:
            state_vec: 预处理的状态向量 (512维)
            context: 上下文信息（用于动态阈值调整）

        Returns:
            二进制动作向量
        """
        try:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state_vec).unsqueeze(0).to(self.device)
                action_logits = self.policy_net(state_tensor)

                # **阶段6新增**：如果提供了上下文，使用动态阈值和概率校准
                if context is not None:
                    try:
                        from src.decision.prediction_optimizer import get_prediction_optimizer
                        optimizer = get_prediction_optimizer()
                        result = optimizer.optimize_prediction(action_logits, context)
                        action_binary = result['predictions'].squeeze(0).cpu().numpy()
                        self.logger.debug(f"Dynamic threshold: {result['threshold']:.3f}, Confidence: {result['confidence']:.3f}")
                        return action_binary
                    except Exception as e:
                        self.logger.warning(f"Failed to use prediction optimizer: {e}, falling back to baseline")
                
                # **阶段6修复**：使用Top-K选择替代固定阈值，解决预测卡牌数量过多问题
                prediction_threshold = 0.3  # 基线阈值（用于初步筛选）
                scaling_factor = 5.0  # 基线缩放因子（阶段0基线参数）
                
                # 对于行为克隆模型，我们使用sigmoid + 缩放 + 阈值来获取二进制动作
                probs = torch.sigmoid(action_logits)
                probs = probs * scaling_factor  # 应用缩放因子
                probs = torch.clamp(probs, 0, 1)  # 限制在[0,1]范围内
                
                # **Top-K选择策略**：优先使用阈值，如果结果不合理则使用Top-K
                probs_squeezed = probs.squeeze(0)
                action_threshold = (probs_squeezed > prediction_threshold).float()
                num_selected = action_threshold.sum().item()
                
                if 2 <= num_selected <= 7:
                    # 阈值选择的结果在合理范围内，使用阈值
                    action_binary = action_threshold.cpu().numpy()
                else:
                    # 阈值选择的结果不合理，使用Top-K选择
                    # K值在2-7之间，根据概率分布自适应选择
                    k_min, k_max = 2, 7
                    
                    # 计算Top-K
                    sorted_probs, _ = torch.sort(probs_squeezed, descending=True)
                    if len(sorted_probs) > k_max:
                        # 找到概率明显下降的点
                        prob_diffs = sorted_probs[:-1] - sorted_probs[1:]
                        k = k_min
                        for i in range(k_min-1, min(k_max, len(prob_diffs))):
                            if prob_diffs[i] > 0.15:
                                k = i + 1
                                break
                        k = min(k, k_max)
                    else:
                        k = min(len(sorted_probs), k_max)
                    
                    # Top-K选择
                    _, top_k_indices = torch.topk(probs_squeezed, k=k, dim=0)
                    action_binary = torch.zeros_like(probs_squeezed)
                    action_binary[top_k_indices] = 1.0
                    action_binary = action_binary.cpu().numpy()
                
                return action_binary

        except Exception as e:
            self.logger.error(f"Ultra optimized model inference failed: {e}")
            # 回退到随机动作
            return np.zeros(512, dtype=int)

    def decide(self, data: Dict) -> int:
        """
        Main interface for the client.
        data: Server message containing 'actionList', 'handCards', etc.
        Returns: Index of the selected action in actionList.
        """
        action_list = data.get("actionList", [])
        if not action_list:
            return 0
        
        # 如果只有PASS动作，直接返回PASS，不需要调用模型
        if len(action_list) == 1:
            first_action = action_list[0]
            is_pass = False
            if first_action == 'PASS':
                is_pass = True
            elif isinstance(first_action, list):
                if all(item == 'PASS' for item in first_action) or (len(first_action) > 0 and first_action[0] == 'PASS'):
                    is_pass = True
            if is_pass:
                print("[RL Debug] Only PASS available, returning PASS without model call")
                return 0
            
        # 处理两种不同的action_list格式
        # 格式1: ['PASS', 'PASS', 'PASS'] - 简单字符串列表
        # 格式2: [['PASS', 'PASS', 'PASS'], ['Single', 'Q', ['SQ']], ...] - 嵌套列表，包含动作对象
        
        # 简化格式识别逻辑：
        # 如果第一个元素是字符串，那么就是格式1
        # 如果第一个元素是列表，那么就是格式2
        if len(action_list) > 0 and isinstance(action_list[0], str):
            # 格式1，直接使用
            pass
        elif len(action_list) > 0 and isinstance(action_list[0], list):
            # 格式2，直接使用原始的action_list
            pass
              
        # Parse state from data
        hand_cards = data.get('handCards', [])
        state_info = {
            'hand': hand_cards,
            'table': [],
            'history': []
        }
        
        # Debug: Print hand cards for troubleshooting
        if not hand_cards:
            print(f"[RL Debug] WARNING: handCards is empty! Available keys: {list(data.keys())}")
        else:
            print(f"[RL Debug] Hand cards ({len(hand_cards)}): {hand_cards[:10]}...")  # 只显示前10张
        
        # 检查是否只有PASS动作（在调用模型之前）
        only_pass = True
        for action in action_list:
            if action == 'PASS':
                continue
            elif isinstance(action, list):
                if len(action) > 0 and action[0] == 'PASS':
                    continue
                elif all(item == 'PASS' for item in action):
                    continue
            only_pass = False
            break
        
        if only_pass:
            print("[RL Debug] Only PASS actions available, skipping model call and returning PASS")
            return 0
        
        # Get desired cards from RL
        desired_cards = self.get_action(state_info)
        desired_set = set(desired_cards)
        
        # Debug: Print actionList for troubleshooting
        if desired_cards:
            print(f"[RL Debug] Desired cards: {desired_cards}")
            print(f"[RL Debug] Available actions: {action_list[:5]}...")  # 只显示前5个，避免输出过多
        else:
            print(f"[RL Debug] WARNING: get_action() returned empty list! Hand: {hand_cards[:5] if hand_cards else 'EMPTY'}...")
        
        # Find matching action in actionList
        best_idx = 0
        best_match_score = -1
        
        for i, action in enumerate(action_list):
            # Handle PASS action - check for different PASS formats
            is_pass_action = False
            if action == 'PASS':
                is_pass_action = True
            elif isinstance(action, list):
                # Check if it's a PASS-only action like ['PASS', 'PASS', 'PASS']
                if all(item == 'PASS' for item in action):
                    is_pass_action = True
                # Check if it's a structured action with PASS as type
                elif len(action) > 0 and action[0] == 'PASS':
                    is_pass_action = True
            
            if is_pass_action:
                if not desired_cards: # RL wants to pass
                    return i
                continue
                
            # Extract cards from action - handle different formats
            action_cards = []
            
            # Format 1: ['PASS', ['SQ', 'HQ', 'DQ', 'H5'], ['S4', 'H4', 'C4', 'C4', 'H5']]
            if isinstance(action, list):
                # Format 2: [Type, Rank, [Cards]]
                if len(action) >= 3:
                    if isinstance(action[2], list):
                        action_cards = action[2]
                    elif isinstance(action[2], str):
                        action_cards = [action[2]]
                # Format 3: [Cards]
                elif all(isinstance(card, str) for card in action):
                    action_cards = action
            # Format 4: Single card string
            elif isinstance(action, str):
                action_cards = [action]
            
            # Skip if no cards
            if not action_cards:
                continue
            
            # Debug: Print action cards for troubleshooting (only for first few actions to avoid spam)
            if i < 3:
                print(f"[RL Debug] Action {i}: {action}, extracted cards: {action_cards}")
            
            # Extract ranks from desired cards and action cards
            desired_ranks = set(card[1:] if len(card) > 1 else card for card in desired_cards)
            action_ranks = set(card[1:] if len(card) > 1 else card for card in action_cards)
            
            # Debug: Print ranks for troubleshooting (only if desired_cards is not empty)
            if desired_cards and i < 3:
                print(f"[RL Debug] Desired ranks: {desired_ranks}, Action ranks: {action_ranks}")
            
            # Check if ranks match exactly (e.g., S8 and D8 both have rank '8')
            if desired_ranks == action_ranks and len(desired_ranks) > 0:
                # 添加索引范围检查，防止返回无效索引
                if i >= len(action_list):
                    print(f"[RL Debug] ERROR: Found exact rank match but index {i} >= action_list length {len(action_list)}")
                    break
                print(f"[RL Debug] Found exact rank match at index {i}: desired_ranks={desired_ranks}, action_ranks={action_ranks}")
                return i
            
            # Calculate match scores for this action
            rank_match_score = 0.0
            card_match_score = 0.0
            
            # Check if there's any rank overlap (partial rank match)
            # This handles cases where model wants rank '3' but only pair/triple of '3' is available
            if desired_ranks and action_ranks:
                rank_overlap = desired_ranks & action_ranks
                if rank_overlap:
                    # Calculate overlap score: how many desired ranks are in this action
                    rank_match_score = len(rank_overlap) / len(desired_ranks)
                    if i < 3:
                        print(f"[RL Debug] Found rank overlap {rank_overlap} at index {i} (score: {rank_match_score:.2f})")
            
            # Partial match scoring (exact card match)
            if desired_cards:
                match_count = len(set(action_cards) & desired_set)
                if len(action_cards) > 0 or len(desired_cards) > 0:
                    card_match_score = match_count / max(len(action_cards), len(desired_cards))
            
            # Use the better of rank match or card match
            combined_score = max(rank_match_score, card_match_score)
            if combined_score > best_match_score:
                best_match_score = combined_score
                best_idx = i
                    
        # If we found a partial match, use it (lower threshold for rank matches)
        if best_match_score > 0.3:  # Lowered from 0.5 to allow rank-based matches
            # 添加索引范围检查
            if best_idx >= len(action_list):
                print(f"[RL Debug] ERROR: best_idx {best_idx} >= action_list length {len(action_list)}, falling back to PASS")
                return 0
            print(f"RL desired {desired_cards} - using match (score: {best_match_score:.2f}) at index {best_idx}")
            return best_idx
            
        # If no match, fallback to PASS (index 0)
        if desired_cards:
            print(f"RL desired {desired_cards} but not found in actionList. Falling back to 0 (PASS).")
        return 0

    def get_action(self, state_info: Dict) -> List[str]:
        """
        Decide action based on state.
        state_info: Dict containing 'hand', 'table', etc. from the main client.
        Returns: List of card codes (e.g. ['H2', 'S3'])
        """
        hand = state_info.get('hand', [])
        if not hand:
            print(f"[RL Debug] get_action: hand is empty!")
            return []
        
        # 1. Preprocess State
        # We need to convert the rich state_info into the 512-dim vector expected by the model
        state_vec = self._preprocess_state(state_info)
        
        # Debug: Check state vector
        active_indices = np.where(state_vec > 0)[0]
        print(f"[RL Debug] State vector: {len(active_indices)} active indices (hand size: {len(hand)})")
        
        # 2. Query Agent/Model
        if self.use_stage5_model and self.model_loaded:
            # 使用阶段5增强模型推理
            # **阶段6新增**：构建上下文信息用于动态阈值调整
            context = self._build_context(data, state_info)
            action_binary = self._stage5_model_inference(state_vec, context)
        else:
            # 使用传统PPOAgent推理
            action_binary, _ = self.agent.select_action(state_vec)
        
        # 3. Decode Action
        # Convert binary vector back to card indices, then to card codes
        selected_indices = [i for i, x in enumerate(action_binary) if x == 1]
        
        # 调试：输出概率统计信息（仅在模型加载且空动作时）
        if self.model_loaded and len(active_indices) > 0 and len(selected_indices) == 0:
            if self.use_stage5_model:
                # 阶段5模型调试信息
                with torch.no_grad():
                    state_tensor = torch.FloatTensor(state_vec).unsqueeze(0).to(self.device)
                    logits = self.policy_net(state_tensor)
                    probs = torch.sigmoid(logits)

                    # 只统计手牌对应索引的概率
                    hand_probs = probs[0, active_indices].cpu().numpy()
                    max_prob = float(hand_probs.max()) if len(hand_probs) > 0 else 0.0
                    mean_prob = float(hand_probs.mean()) if len(hand_probs) > 0 else 0.0
                    above_threshold = int((hand_probs > 0.3).sum())  # 阶段5使用0.3阈值

                    print(f"[RL Debug] Stage5 model - Probability stats: max={max_prob:.4f}, mean={mean_prob:.4f}, "
                          f"above_threshold(0.3)={above_threshold}/{len(active_indices)}")
            else:
                # PPOAgent调试信息
                with torch.no_grad():
                    state_tensor = torch.FloatTensor(state_vec).to(self.agent.device)
                    logits = self.agent.policy_old(state_tensor)
                    probs = torch.sigmoid(logits)
                    scaled_probs = probs * 5.0  # 与agent.py保持一致
                    scaled_probs = torch.clamp(scaled_probs, 0, 1)

                    # 只统计手牌对应索引的概率
                    hand_probs = scaled_probs[active_indices].cpu().numpy()
                    max_prob = float(hand_probs.max()) if len(hand_probs) > 0 else 0.0
                    mean_prob = float(hand_probs.mean()) if len(hand_probs) > 0 else 0.0
                    above_threshold = int((hand_probs > self.agent.prediction_threshold).sum())

                    # 也检查原始概率（未缩放）
                    original_hand_probs = probs[active_indices].cpu().numpy()
                    original_max = float(original_hand_probs.max()) if len(original_hand_probs) > 0 else 0.0
                    original_mean = float(original_hand_probs.mean()) if len(original_hand_probs) > 0 else 0.0

                    print(f"[RL Debug] PPO model - Probability stats: max={max_prob:.4f}, mean={mean_prob:.4f}, "
                          f"above_threshold({self.agent.prediction_threshold})={above_threshold}/{len(active_indices)}")
                    print(f"[RL Debug] Original probs (before scaling): max={original_max:.4f}, mean={original_mean:.4f}")
                
                # 如果缩放后仍然没有超过阈值的，建议进一步降低阈值或增加缩放因子
                if above_threshold == 0:
                    print(f"[RL Debug] WARNING: No probabilities above threshold {self.agent.prediction_threshold}!")
                    print(f"[RL Debug] Suggestion: Try lowering threshold to 0.05 or 0.01, or increase scale factor to 15.0 or 20.0")
        
        # 过滤无效索引（超出编码范围的索引）
        # 我们的编码范围是0-59（4 suits * 15 ranks），但模型可能输出更大的索引
        valid_index_range = 60  # 0-59是有效范围
        valid_indices = [idx for idx in selected_indices if idx < valid_index_range]
        invalid_indices = [idx for idx in selected_indices if idx >= valid_index_range]
        
        # 只在有无效索引时输出警告（减少日志）
        if invalid_indices and len(invalid_indices) > 0:
            print(f"[RL Debug] Filtered out {len(invalid_indices)} invalid indices (>= {valid_index_range}): {invalid_indices[:3]}...")
        
        # 只在有有效索引时输出详细信息
        if valid_indices:
            print(f"[RL Debug] Model selected {len(selected_indices)} indices ({len(valid_indices)} valid): {valid_indices[:5]}...")
        elif len(selected_indices) > 0:
            # 所有索引都无效
            print(f"[RL Debug] Model selected {len(selected_indices)} indices, all invalid (>= {valid_index_range}): {selected_indices[:3]}...")
        else:
            print(f"[RL Debug] Model selected 0 indices (empty action)")
        
        # Warn if model is using random weights and outputting empty actions frequently
        if not self.model_loaded and len(valid_indices) == 0:
            if len(selected_indices) > 0:
                print(f"[RL Debug] WARNING: Model not loaded (using random weights) and output invalid indices. This is expected.")
            else:
                print(f"[RL Debug] WARNING: Model not loaded (using random weights) and output empty action. This is expected.")
        
        # 只使用有效索引进行映射
        selected_cards = self._indices_to_cards(valid_indices, hand)
        if len(selected_cards) == 0 and len(valid_indices) > 0:
            # 只在有有效索引但映射失败时输出警告
            print(f"[RL Debug] WARNING: Model selected {len(valid_indices)} valid indices but mapped to 0 cards!")
            print(f"[RL Debug] Valid indices: {valid_indices[:5]}...")
            
            # 计算手牌中实际可用的索引
            hand_indices = {self._card_to_index(card) for card in hand}
            missing_indices = [idx for idx in valid_indices if idx not in hand_indices]
            if missing_indices:
                print(f"[RL Debug] Missing indices in hand: {missing_indices[:5]}...")
                print(f"[RL Debug] Available indices in hand: {sorted(hand_indices)[:10]}...")
            
            print(f"[RL Debug] This usually means the model selected cards not in hand (model may not be trained or using random weights)")
            print(f"[RL Debug] FALLBACK: Returning empty list, will use rule-based decision")
        elif len(selected_cards) > 0:
            # 只在成功映射时输出（减少日志）
            print(f"[RL Debug] Mapped to {len(selected_cards)} cards: {selected_cards}")
        
        # 4. Validation / Fallback
        # If the model outputs cards we don't have, or an invalid combination
        # We should probably filter or fallback to a rule-based approach.
        # For V5.0, let's just return what the model thinks, but filter for ownership.
        
        # Filter: Only play cards we actually have
        my_hand_set = set(hand)
        valid_cards = [c for c in selected_cards if c in my_hand_set]
        
        if len(valid_cards) != len(selected_cards):
            print(f"[RL Debug] Filtered: {len(selected_cards)} -> {len(valid_cards)} valid cards")
        
        # 如果模型输出无效，返回空列表，让上层决策引擎使用规则引擎
        if len(valid_cards) == 0 and len(valid_indices) > 0:
            print(f"[RL Debug] Model output invalid, falling back to rule-based decision")
        
        return valid_cards

    def _preprocess_state(self, state_info):
        """
        Convert client state to RL state vector (增强版：包含策略特征)
        必须与 GuandanEnv._encode_state 保持一致！
        """
        obs = np.zeros(512, dtype=np.float32)
        
        # 1. Encode Hand (0-59维) - track which indices are used to detect collisions
        # 使用字典记录每个索引对应的卡牌，处理冲突
        index_to_cards = {}
        for card in state_info['hand']:
            idx = self._card_to_index(card)
            if idx < 60:
                if idx not in index_to_cards:
                    index_to_cards[idx] = []
                index_to_cards[idx].append(card)
                obs[idx] = 1.0
        
        # 统计冲突（多个卡牌映射到同一个索引）
        # 注意：在掼蛋中，两副牌108张，每个玩家27张，可能拿到重复的卡牌（如两个D5）
        # 这种情况下，相同的卡牌会映射到同一个索引，这是正常的，不是真正的"冲突"
        collision_count = sum(1 for cards in index_to_cards.values() if len(cards) > 1)
        if collision_count > 0:
            print(f"[RL Debug] Warning: {collision_count} indices have multiple cards mapped")
            # 打印冲突详情（仅前3个，避免输出过多）
            collision_details = []
            for idx, cards in index_to_cards.items():
                if len(cards) > 1:
                    # 检查是否是重复卡牌（相同卡牌代码）还是真正的编码冲突（不同卡牌映射到同一索引）
                    unique_cards = set(cards)
                    if len(unique_cards) == 1:
                        # 相同卡牌重复，这是正常的（两副牌）
                        collision_details.append(f"Index {idx}: {cards} (duplicate cards, normal in 2-deck game)")
                    else:
                        # 不同卡牌映射到同一索引，这是真正的编码冲突
                        collision_details.append(f"Index {idx}: {cards} (ENCODING COLLISION!)")
                    if len(collision_details) >= 3:
                        break
            if collision_details:
                print(f"[RL Debug] Collision details: {collision_details}")
            
        # 2. 编码游戏阶段（120-122维）
        # 根据剩余牌数判断阶段
        hand_count = len(state_info['hand'])
        opponent_rest_cards_list = state_info.get('opponent_rest_cards_list', [27, 27, 27])
        min_opponent_cards = min(opponent_rest_cards_list) if opponent_rest_cards_list else 27
        
        # 判断游戏阶段
        if min_opponent_cards >= 20:
            game_phase = 0  # 开局
        elif min_opponent_cards >= 10:
            game_phase = 1  # 中期
        else:
            game_phase = 2  # 残局
        
        obs[120 + game_phase] = 1.0
        
        # 3. 编码玩家剩余牌数（123-126维，归一化到0-1）
        my_rest_cards = hand_count
        teammate_rest_cards = state_info.get('teammate_rest_cards', 27)
        opponent_rest_cards = opponent_rest_cards_list[1] if len(opponent_rest_cards_list) > 1 else 27
        opponent2_rest_cards = opponent_rest_cards_list[2] if len(opponent_rest_cards_list) > 2 else 27
        
        obs[123] = my_rest_cards / 27.0
        obs[124] = teammate_rest_cards / 27.0
        obs[125] = opponent_rest_cards / 27.0
        obs[126] = opponent2_rest_cards / 27.0
        
        # 4. 编码上一步动作（127-151维）
        greater_action = state_info.get('greater_action', [])
        if greater_action and len(greater_action) > 0:
            action_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
            action_cards = greater_action[2] if len(greater_action) > 2 and isinstance(greater_action[2], list) else []
            
            # 动作类型编码（127-136维）
            action_type_map = {
                'PASS': 0, 'Single': 1, 'SINGLE': 1, 'Pair': 2, 'PAIR': 2,
                'Trips': 3, 'TRIPS': 3, 'Straight': 4, 'STRAIGHT': 4,
                'THREE_WITH_TWO': 5, 'ThreeWithTwo': 5,
                'Bomb': 6, 'BOMB': 6, 'StraightFlush': 7,
                'ThreePair': 8, 'TwoTrips': 9
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
        # 是否能顺牌（上家出单，自己能跟）
        can_follow = 0.0
        greater_pos = state_info.get('greater_pos', -1)
        my_pos = state_info.get('my_pos', -1)
        if greater_pos != -1 and my_pos != -1:
            # 判断是否是上家
            upper_hand_pos = (my_pos - 1) % 4
            if greater_pos == upper_hand_pos and greater_action:
                action_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
                if action_type in ['Single', 'SINGLE']:
                    can_follow = 1.0 if hand_count > 0 else 0.0
        obs[152] = can_follow
        
        # 是否能跟牌（对手出牌，自己能跟）
        can_followup = 0.0
        if greater_action and len(greater_action) > 0:
            action_type = greater_action[0] if isinstance(greater_action, list) else str(greater_action)
            if action_type not in ['PASS', 'pass']:
                can_followup = 1.0 if hand_count > 0 else 0.0
        obs[153] = can_followup
        
        # 是否需要控牌（对手快走完）
        need_control = 1.0 if min_opponent_cards <= 5 else 0.0
        obs[154] = need_control
        
        # 检查手牌数量
        total_cards_in_hand = len(state_info['hand'])
        unique_indices = len(index_to_cards)
        print(f"[RL Debug] Hand stats: {total_cards_in_hand} total cards, {unique_indices} unique indices")
        if total_cards_in_hand != unique_indices:
            print(f"[RL Debug] Note: {total_cards_in_hand - unique_indices} cards share indices (may be duplicates or collisions)")
        return obs

    def _card_to_index(self, card_code):
        """
        Convert card code to index in state vector.
        Improved hash to reduce collisions.
        Card format: 'H2', 'S3', 'CT', etc.
        """
        # Map suit to number: S=0, H=1, C=2, D=3
        suit_map = {'S': 0, 'H': 1, 'C': 2, 'D': 3}
        # Map rank to number: 2-9, T, J, Q, K, A, B (小王), R (大王)
        rank_map = {
            '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
            'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
            'B': 13,  # 小王
            'R': 14   # 大王
        }
        
        if len(card_code) >= 2:
            suit = card_code[0]
            rank = card_code[1]
            # Use a better encoding: suit * 15 + rank
            suit_val = suit_map.get(suit, 0)
            rank_val = rank_map.get(rank, 0)
            idx = suit_val * 15 + rank_val
            # Ensure it fits in 512-dim vector (max 60 for 4 suits * 15 ranks)
            # 但是要确保索引在有效范围内，避免冲突
            return min(idx, 59)  # 最大60个不同的卡牌索引（4 suits * 15 ranks）
        else:
            # Fallback to simple hash for unexpected formats
            return sum(ord(c) for c in card_code) % 54

    def _indices_to_cards(self, indices, current_hand):
        """
        Map indices back to actual cards in hand.
        Since our hash is lossy (modulo 54), this is tricky.
        We need to find a card in hand that matches the index.
        """
        result = []
        hand_copy = list(current_hand)
        
        # 预先计算手牌中每张卡的索引，用于调试
        hand_indices = {self._card_to_index(card): card for card in current_hand}
        
        for idx in indices:
            # Find a card in hand that maps to this index
            found = False
            for card in hand_copy:
                if self._card_to_index(card) == idx:
                    result.append(card)
                    hand_copy.remove(card) # Consume card
                    found = True
                    break
            
            if not found:
                # Model asked for a card we don't have
                # 计算这个索引对应的卡牌（用于调试）
                expected_card = self._index_to_card_code(idx)
                available_indices = sorted(hand_indices.keys())
                # 只在调试模式下输出详细信息（减少日志）
                # 如果有很多无效索引，只输出前几个
                if len([i for i in indices if i not in hand_indices]) <= 3:
                    print(f"[RL Debug] Index {idx} (expected: {expected_card}) not found in hand. Available indices: {available_indices[:10]}...")
                # 不重复输出手牌信息（已经在其他地方输出）
                
        return result
    
    def _index_to_card_code(self, idx):
        """
        反向计算：从索引推断卡牌代码（用于调试）
        """
        suit_map = {0: 'S', 1: 'H', 2: 'C', 3: 'D'}
        rank_map = {
            0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7', 6: '8', 7: '9',
            8: 'T', 9: 'J', 10: 'Q', 11: 'K', 12: 'A', 13: 'B', 14: 'R'
        }
        
        if idx <= 59:  # 使用新编码 (suit * 15 + rank)
            suit_val = idx // 15
            rank_val = idx % 15
            suit = suit_map.get(suit_val, '?')
            rank = rank_map.get(rank_val, '?')
            return f"{suit}{rank}"
        elif idx < 512:  # 在512维向量范围内，但超出新编码范围
            # 可能是旧编码或其他编码方式
            # 尝试用旧编码方式计算
            return f"OutOfRange({idx})"
        else:
            return f"Invalid({idx})"
