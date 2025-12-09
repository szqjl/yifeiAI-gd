import sys
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np

# **修复**：设置Windows控制台编码为UTF-8
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    # 如果导入失败，使用备用方案
    if sys.platform == 'win32':
        try:
            import io
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'buffer'):
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        except:
            pass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.knowledge_processor.replay_parser import ReplayParser
from src.rl_agent.model import GuandanPolicyNet


def identify_card_pattern_type(action_cards, state_dict=None):
    """
    识别卡牌模式类型（阶段3任务2.6方案D改进版：渐进式课程学习）
    
    按照人类学习语言的思路，将卡牌模式分为基础元素：
    1. Pass（过）
    2. 单牌（Single）
    3. 对子（Pair）
    4. 三张（Triple）
    5. 三带二（ThreeWithTwo）
    6. 顺子（Sequence）
    7. 炸弹（Bomb）
    8. 其他复杂组合（Complex）
    
    改进：支持级牌和红桃级牌（百搭、红心配）的特殊处理
    
    Args:
        action_cards: 动作卡牌列表
        state_dict: 状态字典（可选，用于获取级牌信息）
    
    Returns:
        pattern_type: 卡牌模式类型字符串
    """
    # 检查是否是PASS动作
    if state_dict is not None:
        action_type = state_dict.get('action_type', '')
        if action_type in ['PASS', 'pass', 'Pass'] or (not action_cards and action_type):
            return "Pass"
    
    if not action_cards:
        return "Empty"
    
    num_cards = len(action_cards)
    
    # 获取级牌信息（用于识别级牌和红桃级牌的特殊性）
    cur_rank = None
    if state_dict is not None:
        cur_rank = state_dict.get('cur_rank', None)
    
    # 统计卡牌点数分布
    rank_map = {
        '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
        'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
        'B': 13, 'R': 14
    }
    
    ranks = []
    level_cards = []  # 级牌（所有花色的级牌）
    red_heart_level_cards = []  # 红桃级牌（百搭、红心配）
    normal_cards = []  # 普通卡牌
    
    for card in action_cards:
        if len(card) >= 2:
            suit = card[0]  # 花色
            rank = card[1]  # 点数
            
            # 检查是否是红桃级牌（百搭、红心配）- 优先级最高
            if cur_rank is not None and suit == 'H' and rank == cur_rank:
                red_heart_level_cards.append(card)
                # 红桃级牌可以作为任意点数使用，暂时不加入ranks，后续处理
            
            # 检查是否是级牌（所有花色的级牌）
            elif cur_rank is not None and rank == cur_rank:
                level_cards.append(card)
                # 级牌可以作为任意点数使用，暂时不加入ranks，后续处理
            
            # 普通卡牌
            elif rank in rank_map:
                ranks.append(rank_map[rank])
                normal_cards.append(card)
    
    # 统计普通卡牌的点数分布
    rank_counts = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    # 级牌和红桃级牌的数量
    num_level_cards = len(level_cards)
    num_red_heart_level_cards = len(red_heart_level_cards)
    num_wildcards = num_level_cards + num_red_heart_level_cards  # 百搭牌总数
    
    # 如果没有普通卡牌，只有级牌和红桃级牌
    if not ranks and num_wildcards > 0:
        # 如果只有级牌或红桃级牌，按单牌、对子等处理
        if num_wildcards == 1:
            return "Single"
        elif num_wildcards == 2:
            return "Pair"
        elif num_wildcards == 3:
            return "Triple"
        elif num_wildcards == 4:
            return "Bomb"
        else:
            return "Complex"
    
    if not ranks and num_wildcards == 0:
        return "Unknown"
    
    max_count = max(rank_counts.values()) if rank_counts else 0
    
    # 识别基础牌型（考虑级牌和红桃级牌作为百搭）
    if num_cards == 1:
        return "Single"  # 单牌
    elif num_cards == 2:
        # 检查是否是对子（考虑级牌和红桃级牌）
        if max_count == 2:
            return "Pair"  # 对子
        elif max_count == 1 and num_wildcards >= 1:
            # 1张普通卡牌 + 1张百搭牌 = 对子
            return "Pair"
        else:
            return "Complex"  # 其他2张组合
    elif num_cards == 3:
        # 检查是否是三张（考虑级牌和红桃级牌）
        if max_count == 3:
            return "Triple"  # 三张
        elif max_count == 2 and num_wildcards >= 1:
            # 2张相同 + 1张百搭 = 三张
            return "Triple"
        elif max_count == 1 and num_wildcards >= 2:
            # 1张普通卡牌 + 2张百搭 = 三张
            return "Triple"
        else:
            return "Complex"  # 其他3张组合
    elif num_cards == 4:
        # 检查是否是炸弹（考虑级牌和红桃级牌）
        if max_count == 4:
            return "Bomb"  # 炸弹（四张相同）
        elif max_count == 3 and num_wildcards >= 1:
            # 3张相同 + 1张百搭 = 炸弹
            return "Bomb"
        elif max_count == 2 and num_wildcards >= 2:
            # 2张相同 + 2张百搭 = 炸弹
            return "Bomb"
        elif max_count == 1 and num_wildcards >= 3:
            # 1张普通卡牌 + 3张百搭 = 炸弹
            return "Bomb"
        else:
            return "Complex"  # 其他4张组合
    elif num_cards == 5:
        # 检查是否是三带二（考虑级牌和红桃级牌）
        if max_count == 3 and len(rank_counts) == 2:
            return "ThreeWithTwo"  # 三带二
        elif max_count == 2 and len(rank_counts) == 2 and num_wildcards >= 1:
            # 2+2+1（百搭补成3+2）= 三带二
            return "ThreeWithTwo"
        else:
            # 检查是否是顺子（考虑级牌和红桃级牌作为百搭）
            sorted_ranks = sorted(set(ranks))
            
            # 尝试使用百搭牌来形成顺子
            if len(sorted_ranks) + num_wildcards >= 5:
                # 尝试不同的百搭牌使用方式
                for use_wildcards in range(min(num_wildcards + 1, 3)):  # 最多使用2张百搭
                    # 尝试用百搭牌填补顺子的空缺
                    test_ranks = sorted_ranks.copy()
                    gaps = []
                    for i in range(len(test_ranks) - 1):
                        gap = test_ranks[i+1] - test_ranks[i] - 1
                        if gap > 0:
                            gaps.extend(range(test_ranks[i] + 1, test_ranks[i+1]))
                    
                    # 如果空缺数 <= 可用百搭数，可以形成顺子
                    if len(gaps) <= use_wildcards:
                        # 检查是否能形成连续5张
                        all_ranks = sorted(set(test_ranks + gaps[:use_wildcards]))
                        if len(all_ranks) >= 5:
                            # 检查是否有连续5张
                            for start_idx in range(len(all_ranks) - 4):
                                test_sequence = all_ranks[start_idx:start_idx+5]
                                is_sequence = True
                                for i in range(len(test_sequence) - 1):
                                    if test_sequence[i+1] - test_sequence[i] != 1:
                                        is_sequence = False
                                        break
                                if is_sequence:
                                    return "Sequence"  # 5张顺子（含百搭）
            
            # 检查是否是5张顺子（无百搭）
            if len(sorted_ranks) == 5:
                is_sequence = True
                for i in range(len(sorted_ranks) - 1):
                    if sorted_ranks[i+1] - sorted_ranks[i] != 1:
                        is_sequence = False
                        break
                if is_sequence:
                    return "Sequence"  # 5张顺子
            
            # 检查是否是"顺子+单牌"（4张顺子+1张单牌或百搭）
            elif len(sorted_ranks) == 4:
                # 尝试找出4张顺子
                for start_idx in range(len(sorted_ranks) - 3):
                    test_sequence = sorted_ranks[start_idx:start_idx+4]
                    is_sequence = True
                    for i in range(len(test_sequence) - 1):
                        if test_sequence[i+1] - test_sequence[i] != 1:
                            is_sequence = False
                            break
                    if is_sequence:
                        return "Sequence"  # 4张顺子+1张单牌/百搭，归类为Sequence
            
            return "Complex"  # 其他5张组合
    elif num_cards >= 6:
        # 检查是否是顺子（考虑级牌和红桃级牌作为百搭）
        sorted_ranks = sorted(set(ranks))
        
        # 尝试使用百搭牌来形成顺子
        if len(sorted_ranks) + num_wildcards >= num_cards:
            # 检查是否已经是完整顺子（无百搭）
            if len(sorted_ranks) == num_cards:
                is_sequence = True
                for i in range(len(sorted_ranks) - 1):
                    if sorted_ranks[i+1] - sorted_ranks[i] != 1:
                        is_sequence = False
                        break
                if is_sequence:
                    return "Sequence"  # 长顺子（无百搭）
            
            # 尝试用百搭牌填补顺子的空缺
            gaps = []
            for i in range(len(sorted_ranks) - 1):
                gap = sorted_ranks[i+1] - sorted_ranks[i] - 1
                if gap > 0:
                    gaps.extend(range(sorted_ranks[i] + 1, sorted_ranks[i+1]))
            
            # 如果空缺数 <= 可用百搭数，可以形成顺子
            if len(gaps) <= num_wildcards:
                all_ranks = sorted(set(sorted_ranks + gaps[:num_wildcards]))
                if len(all_ranks) >= 5:
                    # 检查是否有连续5张或更多
                    for start_idx in range(len(all_ranks) - 4):
                        test_sequence = all_ranks[start_idx:start_idx+5]
                        is_sequence = True
                        for i in range(len(test_sequence) - 1):
                            if test_sequence[i+1] - test_sequence[i] != 1:
                                is_sequence = False
                                break
                        if is_sequence:
                            return "Sequence"  # 长顺子（含百搭）
        
        # 检查是否是"顺子+单牌"的组合（改进：识别顺子带单牌，考虑百搭）
        # 尝试移除一些卡牌后是否能形成顺子
        for remove_count in range(1, min(3, num_cards - 5) + 1):  # 最多移除2张，至少保留5张形成顺子
            # 尝试移除出现次数最少的点数
            rank_counts_sorted = sorted(rank_counts.items(), key=lambda x: x[1])
            test_ranks = ranks.copy()
            for rank, count in rank_counts_sorted[:remove_count]:
                # 移除该点数的所有卡牌
                test_ranks = [r for r in test_ranks if r != rank]
            
            if len(test_ranks) >= 5:
                sorted_test_ranks = sorted(set(test_ranks))
                # 尝试用百搭牌填补
                if len(sorted_test_ranks) + num_wildcards >= 5:
                    gaps = []
                    for i in range(len(sorted_test_ranks) - 1):
                        gap = sorted_test_ranks[i+1] - sorted_test_ranks[i] - 1
                        if gap > 0:
                            gaps.extend(range(sorted_test_ranks[i] + 1, sorted_test_ranks[i+1]))
                    
                    if len(gaps) <= num_wildcards:
                        all_ranks = sorted(set(sorted_test_ranks + gaps[:num_wildcards]))
                        if len(all_ranks) >= 5:
                            for start_idx in range(len(all_ranks) - 4):
                                test_sequence = all_ranks[start_idx:start_idx+5]
                                is_sequence = True
                                for i in range(len(test_sequence) - 1):
                                    if test_sequence[i+1] - test_sequence[i] != 1:
                                        is_sequence = False
                                        break
                                if is_sequence:
                                    return "Sequence"  # 顺子带单牌，仍归类为Sequence
        
        # 检查是否是炸弹（考虑级牌和红桃级牌）
        if max_count >= 4:
            return "Bomb"  # 多张炸弹
        elif max_count == 3 and num_wildcards >= 1:
            return "Bomb"  # 3张相同+1张百搭=炸弹
        elif max_count == 2 and num_wildcards >= 2:
            return "Bomb"  # 2张相同+2张百搭=炸弹
        return "Complex"  # 其他复杂组合
    
    return "Complex"


def evaluate_sample_curriculum_stage(state_dict, action_cards):
    """
    评估样本应该属于哪个课程学习阶段（阶段3任务2.6方案D改进版：渐进式课程学习）
    
    按照人类学习语言的思路，分为4个阶段：
    阶段1（基础元素）：学习单牌、对子、三张、三带二、顺子、炸弹等基础牌型
    阶段2（组合策略）：学习组牌、拆牌等组合策略
    阶段3（基本规则）：学习按规则出牌、简单组牌等基本规则
    阶段4（实战）：完整对局，所有复杂情况
    
    Args:
        state_dict: 状态字典
        action_cards: 动作卡牌列表
    
    Returns:
        stage: 课程阶段（1-4）
    """
    if not action_cards:
        return 1  # 空动作归为阶段1
    
    # 识别卡牌模式类型（传入state_dict以支持级牌和PASS识别）
    pattern_type = identify_card_pattern_type(action_cards, state_dict)
    
    # 获取策略类型
    strategy_type = state_dict.get('strategy_type', 'unknown')
    
    # 阶段划分逻辑（改进版：更合理的划分，考虑卡牌数量和复杂度）
    num_cards = len(action_cards) if action_cards else 0
    
    # 阶段1：基础元素（单牌、对子、三张、三带二、顺子、炸弹、Pass）- 简单出牌和跟牌
    if pattern_type in ["Pass", "Single", "Pair", "Triple", "ThreeWithTwo", "Sequence", "Bomb"]:
        # 如果策略类型是discard（顺牌/出牌）或follow（跟牌），说明是基础操作，归为阶段1
        if strategy_type in ['discard', 'follow', 'unknown']:
            return 1
        # 其他策略类型（组牌、控牌等）归为阶段2
        else:
            return 2
    
    # 阶段2：组合策略（组牌、拆牌等）- 需要组合操作的策略
    elif strategy_type in ['group', 'control']:
        return 2
    
    # 阶段3：基本规则（按规则出牌、简单组牌）- 需要策略判断的操作
    elif strategy_type in ['suppress', 'protect']:
        return 3
    
    # 阶段划分：Complex类型按卡牌数量和策略类型划分
    elif pattern_type == "Complex":
        # 如果卡牌数量少（<=3张），且策略类型是follow或discard，归为阶段2（简单组合）
        if num_cards <= 3 and strategy_type in ['follow', 'discard']:
            return 2
        # 如果卡牌数量中等（4-5张），且策略类型是follow或discard，归为阶段3（中等复杂度）
        elif num_cards <= 5 and strategy_type in ['follow', 'discard']:
            return 3
        # 如果卡牌数量多（>=6张），或策略类型复杂，归为阶段4（高复杂度）
        elif num_cards >= 6 or strategy_type not in ['follow', 'discard']:
            return 4
        # 其他情况归为阶段3
        else:
            return 3
    
    # 默认归为阶段1
    return 1


def evaluate_sample_difficulty(state_dict, action_cards):
    """
    评估样本难度（阶段3任务2.6方案D：课程学习 - 改进版）
    
    难度评估标准（从简单到复杂）：
    1. 单牌（最简单，难度1.0）
    2. 对子（难度2.0）
    3. 三张（难度3.0）
    4. 三带二（难度4.0）
    5. 顺子（难度5.0-7.0，根据长度）
    6. 炸弹（最复杂，难度9.0-10.0）
    
    改进点：
    - 更准确地识别牌型
    - 考虑卡牌数量、牌型复杂度、是否包含大小王
    - 使用更细粒度的难度评分
    
    Args:
        state_dict: 状态字典
        action_cards: 动作卡牌列表
    
    Returns:
        difficulty: 难度分数（0-10，0最简单，10最复杂）
    """
    if not action_cards:
        return 0.0
    
    num_cards = len(action_cards)
    
    # 统计卡牌点数分布
    rank_map = {
        '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
        'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
        'B': 13, 'R': 14
    }
    
    ranks = []
    for card in action_cards:
        if len(card) >= 2:
            rank = card[1]
            if rank in rank_map:
                ranks.append(rank_map[rank])
    
    if not ranks:
        return 0.0
    
    rank_counts = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    max_count = max(rank_counts.values()) if rank_counts else 0
    
    # 难度评估（改进版：更准确的牌型识别）
    difficulty = 0.0
    
    # 1. 识别基本牌型
    if num_cards == 1:
        difficulty = 1.0  # 单牌：最简单
    elif num_cards == 2:
        if max_count == 2:
            difficulty = 2.0  # 对子
        else:
            difficulty = 2.5  # 其他2张组合
    elif num_cards == 3:
        if max_count == 3:
            difficulty = 3.0  # 三张
        else:
            difficulty = 3.5  # 其他3张组合
    elif num_cards == 4:
        if max_count == 4:
            difficulty = 9.0  # 炸弹（四张相同）
        else:
            difficulty = 4.0  # 其他4张组合
    elif num_cards == 5:
        if max_count == 3:
            # 检查是否是三带二
            if len(rank_counts) == 2:  # 只有两种点数
                difficulty = 4.0  # 三带二
            else:
                difficulty = 4.5  # 其他组合
        else:
            # 检查是否是顺子
            sorted_ranks = sorted(set(ranks))
            if len(sorted_ranks) == 5:
                is_sequence = True
                for i in range(len(sorted_ranks) - 1):
                    if sorted_ranks[i+1] - sorted_ranks[i] != 1:
                        is_sequence = False
                        break
                if is_sequence:
                    difficulty = 5.0  # 5张顺子
                else:
                    difficulty = 6.0  # 其他5张组合
            else:
                difficulty = 6.0
    elif num_cards >= 6:
        # 检查是否是顺子
        sorted_ranks = sorted(set(ranks))
        if len(sorted_ranks) == num_cards:
            is_sequence = True
            for i in range(len(sorted_ranks) - 1):
                if sorted_ranks[i+1] - sorted_ranks[i] != 1:
                    is_sequence = False
                    break
            if is_sequence:
                # 长顺子：6张=5.5, 7张=6.0, 8张=6.5, 9张=7.0, 10张=7.5
                difficulty = 5.0 + (num_cards - 5) * 0.5
            else:
                # 其他长组合：6张=6.5, 7张=6.8, 8张=7.1, ...
                difficulty = 6.0 + (num_cards - 5) * 0.3
        else:
            # 混合牌型：更复杂
            difficulty = 7.0 + (num_cards - 5) * 0.2
    
    # 2. 检查是否是炸弹（炸弹最复杂，优先级最高）
    if max_count >= 4:
        # 炸弹：4张=9.0, 5张=9.5, 6张=10.0
        if num_cards == 4:
            difficulty = 9.0  # 普通炸弹
        elif num_cards == 5:
            difficulty = 9.5  # 5张炸弹（如5个2）
        else:
            difficulty = 10.0  # 6张及以上炸弹
    
    # 3. 检查是否包含大小王（增加难度）
    has_joker = any(card[1] in ['B', 'R'] for card in action_cards if len(card) >= 2)
    if has_joker:
        difficulty += 0.3  # 包含大小王增加难度
    
    # 4. 考虑卡牌数量（数量越多，难度越高）
    if num_cards > 5 and difficulty < 7.0:
        difficulty += (num_cards - 5) * 0.1
    
    # 限制在0-10范围内
    difficulty = min(max(difficulty, 0.0), 10.0)
    
    return difficulty


class FocalLoss(nn.Module):
    """
    Focal Loss for addressing class imbalance in action prediction.
    
    Focal Loss公式: FL(p_t) = -α(1-p_t)^γ log(p_t)
    
    Args:
        alpha: 平衡因子，用于平衡正负样本（默认0.25）
        gamma: 聚焦参数，用于关注难分类样本（默认2.0）
        reduction: 损失归约方式（'mean'或'sum'）
    """
    def __init__(self, alpha=0.25, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
    
    def forward(self, inputs, targets):
        """
        计算Focal Loss
        
        Args:
            inputs: 模型输出的logits (batch_size, num_classes)
            targets: 真实标签 (batch_size, num_classes)
        
        Returns:
            Focal Loss值
        """
        # 将logits转换为概率
        probs = torch.sigmoid(inputs)
        
        # 计算BCE损失
        bce_loss = F.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        
        # 计算p_t（预测概率）
        # 对于正样本，p_t = probs
        # 对于负样本，p_t = 1 - probs
        p_t = probs * targets + (1 - probs) * (1 - targets)
        
        # 计算(1-p_t)^γ
        focal_weight = (1 - p_t) ** self.gamma
        
        # 应用alpha权重（正样本用alpha，负样本用1-alpha）
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        
        # 计算Focal Loss
        focal_loss = alpha_t * focal_weight * bce_loss
        
        # 归约
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

class GuandanDataset(Dataset):
    def __init__(self, data):
        self.data = data
        
    def __len__(self):
        return len(self.data)
        
    def __getitem__(self, idx):
        """
        获取训练样本
        
        数据格式：
        - state_dict: 状态字典，包含：
          - hand: 手牌列表
          - history: 历史动作
          - current_player: 当前玩家
          - hands: 所有玩家的手牌
          - last_action: 上一步动作
          - action_type: 当前动作类型
          - game_phase: 游戏阶段
          - cur_rank: 当前级牌
          - player_rest_cards: 玩家剩余牌数
          - strategy_type: 策略类型（新增）
          - strategy_reason: 策略原因（新增）
          - strategy_effectiveness: 策略效果（新增）
        - action_cards: 动作卡牌列表
        """
        state_dict, action_cards = self.data[idx]
        
        # **关键修复**：使用与推理代码相同的编码方式
        # 必须与 rl_decision_engine.py 中的 _card_to_index 保持一致！
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
        
        # Convert state_dict to vector (512维，增强版：包含策略特征)
        state_vec = np.zeros(512, dtype=np.float32)
        
        # 1. Encode Hand (0-59维) - 使用与推理代码相同的编码
        for card in state_dict['hand']:
            card_idx = card_to_index(card)
            if card_idx < 60:
                state_vec[card_idx] = 1.0
        
        # 2. 编码游戏阶段（120-122维）
        # 从历史数据中可能没有游戏阶段信息，使用默认值（中期）
        game_phase = state_dict.get('game_phase', 1)  # 0=开局, 1=中期, 2=残局
        if game_phase < 3:
            state_vec[120 + game_phase] = 1.0
        else:
            state_vec[121] = 1.0  # 默认中期
        
        # 3. 编码玩家剩余牌数（123-126维）
        # 从历史数据中可能没有这些信息，使用默认值
        player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
        for i, card_count in enumerate(player_rest_cards[:4]):
            state_vec[123 + i] = card_count / 27.0  # 归一化
        
        # 4. 编码上一步动作（127-151维）
        last_action = state_dict.get('last_action', {})
        if last_action:
            action_type = last_action.get('type', '')
            last_action_cards = last_action.get('cards', [])  # **修复**：重命名避免覆盖action_cards
            
            # 动作类型编码（127-136维）
            action_type_map = {
                'PASS': 0, 'Single': 1, 'Pair': 2, 'Trips': 3,
                'Straight': 4, 'ThreeWithTwo': 5, 'Bomb': 6,
                'StraightFlush': 7, 'ThreePair': 8, 'TwoTrips': 9
            }
            action_type_idx = action_type_map.get(action_type, 0)
            if action_type_idx < 10:
                state_vec[127 + action_type_idx] = 1.0
            
            # 动作牌点编码（137-151维）
            if last_action_cards:
                first_card = last_action_cards[0]
                rank_map = {
                    '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                    'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
                    'B': 13, 'R': 14
                }
                if len(first_card) >= 2:
                    rank = first_card[1] if len(first_card) == 2 else first_card[1:2]
                    rank_idx = rank_map.get(rank, 0)
                    if rank_idx < 15:
                        state_vec[137 + rank_idx] = 1.0
        
        # 5. 编码策略特征（152-154维）
        # 从历史数据中可能没有这些信息，使用默认值
        state_vec[152] = state_dict.get('can_follow', 0.0)  # 是否能顺牌
        state_vec[153] = state_dict.get('can_followup', 0.0)  # 是否能跟牌
        state_vec[154] = state_dict.get('need_control', 0.0)  # 是否需要控牌
        
        # 6. 编码策略类型（155-162维）- 新增：支持策略信息
        # 策略类型：bomb, suppress, protect, control, group, follow, discard, unknown
        strategy_type = state_dict.get('strategy_type', 'unknown')
        strategy_type_map = {
            'bomb': 0, 'suppress': 1, 'protect': 2, 'control': 3,
            'group': 4, 'follow': 5, 'discard': 6, 'unknown': 7
        }
        strategy_type_idx = strategy_type_map.get(strategy_type, 7)
        if strategy_type_idx < 8 and (155 + strategy_type_idx) < 512:
            state_vec[155 + strategy_type_idx] = 1.0
        
        # 7. 编码策略效果（163维）- 新增：支持策略效果信息
        # 策略效果分数归一化（假设最大值为30，归一化到0-1）
        strategy_effectiveness = state_dict.get('strategy_effectiveness', 0.0)
        if 163 < 512:
            state_vec[163] = min(strategy_effectiveness / 30.0, 1.0)  # 归一化到[0, 1]
            
        # Convert action_cards to vector (Target)
        # 注意：动作空间是512维（与状态空间一致），不是108维
        action_vec = np.zeros(512, dtype=np.float32)
        # **调试**：检查action_cards格式
        if not isinstance(action_cards, list):
            import warnings
            warnings.warn(f"action_cards不是列表！类型: {type(action_cards)}, 值: {action_cards}")
            action_cards = [] if action_cards is None else [str(action_cards)]
        for card in action_cards:
            if not isinstance(card, str):
                import warnings
                warnings.warn(f"卡牌不是字符串！类型: {type(card)}, 值: {card}")
                continue
            card_idx = card_to_index(card)
            if card_idx < 512:
                action_vec[card_idx] = 1.0
            # **调试**：如果card_idx >= 512，记录警告
            elif card_idx >= 512:
                import warnings
                warnings.warn(f"card_idx({card_idx}) >= 512，卡牌: {card}")
            
        # 8. 提取策略标签（用于多任务学习）- 阶段2任务2新增
        # 策略类型：bomb, suppress, protect, control, group, follow, discard, unknown
        strategy_type = state_dict.get('strategy_type', 'unknown')
        strategy_type_map = {
            'bomb': 0, 'suppress': 1, 'protect': 2, 'control': 3,
            'group': 4, 'follow': 5, 'discard': 6, 'unknown': 7
        }
        strategy_type_idx = strategy_type_map.get(strategy_type, 7)
        # 返回策略类型索引（0-7），7表示unknown，在损失计算中会被忽略
        
        # **阶段3改进**: 返回牌型信息用于样本权重
        pattern_type = identify_card_pattern_type(action_cards, state_dict)
        pattern_type_map = {
            'Single': 0, 'Pair': 1, 'Triple': 2, 'ThreeWithTwo': 3,
            'Sequence': 4, 'Bomb': 5, 'SteelPlate': 6, 'WoodPlate': 7,
            'Complex': 8, 'Pass': 9, 'Empty': 10, 'Unknown': 11
        }
        pattern_type_idx = pattern_type_map.get(pattern_type, 11)
        
        return torch.FloatTensor(state_vec), torch.FloatTensor(action_vec), strategy_type_idx, pattern_type_idx

def train_bc(data_dir="game_records", epochs=30, batch_size=64, lr=0.0003, model_path="models/bc_model_v1.pth", 
             dropout_rate=0.1, enable_strategy_head=True, action_loss_weight=1.5, strategy_loss_weight=0.3,
             max_samples=None, use_dynamic_weight=False, weight_adjust_interval=5, use_separated_features=False,
             use_curriculum_learning=False, curriculum_stages=3):
    """
    行为克隆预训练（支持多任务学习）
    
    **最优配置（基于历次训练效果汇总.md）**:
    - epochs: 30-50（根据数据量选择，大数据量用50）
    - batch_size: 64（最优批次大小）
    - lr: 0.0003（稳定学习率，配合学习率衰减）
    - dropout_rate: 0.1（平衡过拟合和输出概率）
    - 学习率衰减: StepLR(step_size=10, gamma=0.5)（每10轮衰减50%）
    - 损失函数: 加权BCE(pos_weight=2.0)（惩罚预测过少）
    
    **阶段2新增（多任务学习）**:
    - enable_strategy_head: 是否启用策略分类头（默认True）
    - action_loss_weight: 动作预测损失权重（阶段3调整为1.5，原1.0）
    - strategy_loss_weight: 策略分类损失权重（阶段3调整为0.3，原0.5）
    
    Args:
        data_dir: 训练数据目录
        epochs: 训练轮数（推荐30-50）
        batch_size: 批次大小（推荐64）
        lr: 学习率（推荐0.0003）
        model_path: 模型保存路径
        dropout_rate: Dropout比率（推荐0.1）
        enable_strategy_head: 是否启用策略分类头（阶段2新增）
        action_loss_weight: 动作预测损失权重α（阶段2新增，阶段3任务2.5方案B支持动态调整）
        strategy_loss_weight: 策略分类损失权重β（阶段2新增，阶段3任务2.5方案B支持动态调整）
        use_dynamic_weight: 是否使用动态损失权重调整（阶段3任务2.5方案B）
        weight_adjust_interval: 权重调整间隔（每N个epoch调整一次，默认5）
        use_separated_features: 是否使用分离的特征提取层（阶段3任务2.5方案C）
        use_curriculum_learning: 是否使用课程学习（阶段3任务2.6方案D）
        curriculum_stages: 课程学习阶段数（默认3：简单、中等、困难）
    """
    print("Starting Behavior Cloning Pre-training...")
    print(f"Data directory: {data_dir}")
    print(f"Epochs: {epochs}, Batch size: {batch_size}, Learning rate: {lr}")
    print(f"[最优配置] 学习率衰减: StepLR(step_size=10, gamma=0.5), 损失函数: 加权BCE(pos_weight=2.0)")
    if enable_strategy_head:
        if use_dynamic_weight:
            print(f"[阶段2多任务学习] 策略分类头: 启用, 初始损失权重: α={action_loss_weight}, β={strategy_loss_weight}")
            print(f"[阶段3任务2.5方案B] 动态损失权重调整: 启用, 调整间隔: 每{weight_adjust_interval}个epoch")
        else:
            print(f"[阶段2多任务学习] 策略分类头: 启用, 损失权重: α={action_loss_weight}, β={strategy_loss_weight}")
    else:
        print(f"[阶段2多任务学习] 策略分类头: 禁用（单任务学习）")
    
    # 1. Load Data
    parser = ReplayParser(data_dir)
    replays = parser.load_replays()
    raw_data = parser.extract_training_data(replays)
    print(f"Loaded {len(raw_data)} samples.")
    
    # 限制数据量（用于测试）
    if max_samples is not None and len(raw_data) > max_samples:
        raw_data = raw_data[:max_samples]
        print(f"Limited to {len(raw_data)} samples for testing.")
    
    if len(raw_data) == 0:
        print("No data found. Exiting.")
        return

    # **阶段3任务2.6方案D改进版**: 渐进式课程学习（类似人类学习语言）
    if use_curriculum_learning:
        print(f"[阶段3任务2.6方案D改进版] 渐进式课程学习：启用，阶段数={curriculum_stages}")
        print("课程设计思路（类似人类学习语言）：")
        print("  阶段1：学习基础元素（单牌、对子、三张、三带二、顺子、炸弹等基础牌型）")
        print("  阶段2：学习组合策略（组牌、拆牌等组合策略）")
        print("  阶段3：学习基本规则（按规则出牌、简单组牌等基本规则）")
        print("  阶段4：实战（完整对局，所有复杂情况）")
        
        # 评估每个样本应该属于哪个阶段
        print("评估样本课程阶段...")
        sample_stages = []
        pattern_type_counts = {}
        strategy_type_counts = {}
        
        for i, (state_dict, action_cards) in enumerate(raw_data):
            stage = evaluate_sample_curriculum_stage(state_dict, action_cards)
            sample_stages.append((i, stage))
            
            # 统计牌型和策略类型分布（传入state_dict以支持级牌和PASS识别）
            pattern_type = identify_card_pattern_type(action_cards, state_dict)
            pattern_type_counts[pattern_type] = pattern_type_counts.get(pattern_type, 0) + 1
            
            strategy_type = state_dict.get('strategy_type', 'unknown')
            strategy_type_counts[strategy_type] = strategy_type_counts.get(strategy_type, 0) + 1
            
            if (i + 1) % 1000 == 0:
                print(f"  已评估 {i+1}/{len(raw_data)} 个样本")
        
        # 按阶段分组样本
        stage_groups = {stage: [] for stage in range(1, curriculum_stages + 1)}
        for idx, stage in sample_stages:
            # 确保阶段在有效范围内
            actual_stage = min(max(stage, 1), curriculum_stages)
            stage_groups[actual_stage].append(idx)
        
        # 打印统计信息
        print(f"\n牌型分布：{pattern_type_counts}")
        print(f"策略类型分布：{strategy_type_counts}")
        print(f"\n阶段样本分布：")
        for stage in range(1, curriculum_stages + 1):
            print(f"  阶段{stage}: {len(stage_groups[stage])}个样本")
        
        # 构建课程阶段数据（改进版：确保每个阶段都有足够的样本，并且难度递增合理）
        curriculum_stage_data = []
        min_samples_per_stage = max(50, len(raw_data) // (curriculum_stages * 3))  # 每个阶段至少50个样本或总数的1/9
        
        # 第一步：合并样本太少的阶段
        merged_stage_groups = {}
        for stage in range(1, curriculum_stages + 1):
            stage_indices = stage_groups[stage]
            
            # 如果阶段样本太少，合并到前一个阶段或下一个阶段
            if len(stage_indices) < min_samples_per_stage:
                if stage > 1:
                    # 合并到前一个阶段
                    prev_stage = stage - 1
                    if prev_stage not in merged_stage_groups:
                        merged_stage_groups[prev_stage] = []
                    merged_stage_groups[prev_stage].extend(stage_indices)
                    print(f"  警告：阶段{stage}样本太少({len(stage_indices)}个)，合并到阶段{prev_stage}")
                elif stage < curriculum_stages:
                    # 合并到下一个阶段
                    next_stage = stage + 1
                    if next_stage not in merged_stage_groups:
                        merged_stage_groups[next_stage] = []
                    merged_stage_groups[next_stage].extend(stage_indices)
                    print(f"  警告：阶段{stage}样本太少({len(stage_indices)}个)，合并到阶段{next_stage}")
                else:
                    # 最后一个阶段，合并到前一个阶段
                    if curriculum_stages > 1:
                        prev_stage = curriculum_stages - 1
                        if prev_stage not in merged_stage_groups:
                            merged_stage_groups[prev_stage] = []
                        merged_stage_groups[prev_stage].extend(stage_indices)
                        print(f"  警告：阶段{stage}样本太少({len(stage_indices)}个)，合并到阶段{prev_stage}")
            else:
                # 样本足够，保留
                if stage not in merged_stage_groups:
                    merged_stage_groups[stage] = []
                merged_stage_groups[stage].extend(stage_indices)
        
        # 第二步：按阶段顺序构建课程数据
        for stage in sorted(merged_stage_groups.keys()):
            stage_indices = merged_stage_groups[stage]
            
            if not stage_indices:
                print(f"  警告：阶段{stage}没有样本，将跳过")
                continue
            
            stage_data = [raw_data[idx] for idx in stage_indices]
            
            # 统计该阶段的牌型和策略类型（传入state_dict以支持级牌和PASS识别）
            stage_pattern_types = {}
            stage_strategy_types = {}
            for idx in stage_indices:
                state_dict, action_cards = raw_data[idx]
                pattern_type = identify_card_pattern_type(action_cards, state_dict)
                stage_pattern_types[pattern_type] = stage_pattern_types.get(pattern_type, 0) + 1
                strategy_type = state_dict.get('strategy_type', 'unknown')
                stage_strategy_types[strategy_type] = stage_strategy_types.get(strategy_type, 0) + 1
            
            curriculum_stage_data.append({
                'data': stage_data,
                'stage': stage,
                'pattern_types': stage_pattern_types,
                'strategy_types': stage_strategy_types
            })
            print(f"  阶段{stage}: {len(stage_data)}个样本")
            print(f"    牌型分布: {stage_pattern_types}")
            print(f"    策略类型分布: {stage_strategy_types}")
    else:
        curriculum_stage_data = None
        print(f"[阶段3任务2.6方案D] 课程学习：禁用")

    # 创建数据集（如果使用课程学习，会在训练循环中动态切换）
    if not use_curriculum_learning:
        dataset = GuandanDataset(raw_data)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    else:
        # 课程学习：初始使用最简单阶段的数据
        dataset = GuandanDataset(curriculum_stage_data[0]['data'])
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # 2. Setup Model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # **关键修复**：模型输入输出维度必须与推理代码一致
    # 输入：512维状态向量
    # 输出：512维动作向量（每个维度表示是否选择对应的卡牌索引）
    # **优化**: 使用降低的dropout_rate (0.1)，减少过拟合，提高输出概率
    # **阶段2新增**: 启用策略分类头（多任务学习）
    # **阶段3任务2回退**: 隐藏层维度回退到256（512在796样本上效果差，完全匹配准确率0.00%）
    # **阶段3任务2.5方案C**: 分离的特征提取层（共享底层特征，分离高层特征）
    model = GuandanPolicyNet(
        input_dim=512, 
        hidden_dim=256,  # 阶段3任务2回退：从512回退到256，任务1配置（24.62%准确率）
        output_dim=512, 
        dropout_rate=dropout_rate,
        strategy_num_classes=7,
        enable_strategy_head=enable_strategy_head,
        use_separated_features=use_separated_features  # 阶段3任务2.5方案C
    ).to(device)
    if use_separated_features:
        print(f"Model: input_dim=512, hidden_dim=256, output_dim=512, dropout_rate={dropout_rate}, strategy_head={enable_strategy_head} (阶段3任务2.5方案C：分离特征提取层)")
    else:
        print(f"Model: input_dim=512, hidden_dim=256, output_dim=512, dropout_rate={dropout_rate}, strategy_head={enable_strategy_head} (阶段3任务2回退：恢复任务1配置)")
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # **阶段3任务2.5回退**: 回退到BCE Loss（Focal Loss效果不理想）
    # 使用加权BCE Loss，增加对预测过少的惩罚
    # 权重策略：对于正样本（应该选择的卡牌），给予更高权重（2.0倍）
    # **阶段3任务2.7改进**: 根据dropout_rate调整pos_weight以提高输出概率
    if dropout_rate == 0.01:
        pos_weight = torch.tensor(8.0).to(device)  # 正样本权重：8.0（极大增加对预测过少的惩罚，提高正样本概率）
        print(f"[阶段3任务2.7版本2] 使用加权BCE Loss (pos_weight=8.0, dropout_rate=0.01)，进一步提高卡牌识别率")
    elif dropout_rate == 0.05:
        pos_weight = torch.tensor(4.0).to(device)  # 正样本权重：4.0（大幅增加对预测过少的惩罚，提高正样本概率）
        print(f"[阶段3任务2.7] 使用加权BCE Loss (pos_weight=4.0, dropout_rate=0.05)，提高卡牌识别率")
    else:
        pos_weight = torch.tensor(2.0).to(device)  # 正样本权重：2.0（增加对预测过少的惩罚）
        print(f"[阶段3任务2.5回退] 使用加权BCE Loss (pos_weight=2.0)，恢复任务1配置")
    action_criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # 动作预测损失（加权BCE）
    
    # **阶段2新增**: 策略分类损失（交叉熵损失）
    # 注意：CrossEntropyLoss内部会应用Softmax，所以不需要在模型输出上应用Softmax
    strategy_criterion = nn.CrossEntropyLoss(ignore_index=7) if enable_strategy_head else None  # 忽略unknown类别（索引7）
    
    # **优化**：添加学习率衰减
    # 每10轮衰减50%，帮助模型更稳定地收敛
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)
    
    # 3. Training Loop
    # **阶段2任务3新增**: 评估指标记录
    training_history = {
        'epochs': [],
        'total_loss': [],
        'action_loss': [],
        'strategy_loss': [],
        'action_exact_accuracy': [],
        'action_card_accuracy': [],
        'strategy_accuracy': [],
        'strategy_accuracy_by_class': {i: [] for i in range(7)},  # 7个策略类别
        'strategy_understanding_rate': []  # 策略理解率（动作预测和策略分类都正确）
    }
    
    # **阶段3任务2.5方案B**: 动态损失权重调整
    # 初始化当前权重（用于动态调整）
    current_action_weight = action_loss_weight
    current_strategy_weight = strategy_loss_weight
    
    # **阶段3任务2.6方案D改进版**: 渐进式课程学习 - 初始化当前阶段
    current_curriculum_stage = 1 if use_curriculum_learning else None
    epochs_per_stage = epochs // len(curriculum_stage_data) if use_curriculum_learning and curriculum_stage_data else None
    if use_curriculum_learning and curriculum_stage_data:
        actual_stages = len(curriculum_stage_data)
        epochs_per_stage = epochs // actual_stages
        print(f"[阶段3任务2.6方案D改进版] 渐进式课程学习：共{actual_stages}个阶段，每个阶段训练约 {epochs_per_stage} 个epoch")
    
    for epoch in range(epochs):
        # **阶段3任务2.6方案D改进版**: 渐进式课程学习 - 检查是否需要切换到下一个阶段
        if use_curriculum_learning and curriculum_stage_data and epochs_per_stage:
            # 计算应该切换到哪个阶段（从阶段1开始，索引0）
            stage_index = min(epoch // epochs_per_stage, len(curriculum_stage_data) - 1)
            if stage_index != (current_curriculum_stage - 1 if current_curriculum_stage else -1):
                current_curriculum_stage = stage_index + 1
                stage_info = curriculum_stage_data[stage_index]
                # 切换到新阶段的数据
                dataset = GuandanDataset(stage_info['data'])
                dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                                       generator=torch.Generator().manual_seed(42) if torch.cuda.is_available() else None)
                print(f"[阶段3任务2.6方案D改进版] 渐进式课程学习：切换到阶段{current_curriculum_stage}/{len(curriculum_stage_data)} "
                      f"(样本数={len(stage_info['data'])})")
                print(f"    牌型分布: {stage_info.get('pattern_types', {})}")
                print(f"    策略类型分布: {stage_info.get('strategy_types', {})}")
        
        total_loss = 0
        total_action_loss = 0
        total_strategy_loss = 0
        strategy_loss_count = 0  # 统计有效策略损失样本数
        
        # **阶段2任务3新增**: 评估指标统计
        total_samples = 0
        correct_action_predictions = 0  # 完全匹配的动作预测数
        total_action_cards = 0
        matched_action_cards = 0  # 匹配的卡牌数
        
        total_strategy_samples = 0  # 有效策略样本数（排除unknown）
        correct_strategy_predictions = 0  # 正确的策略分类数
        strategy_correct_by_class = {i: {'correct': 0, 'total': 0} for i in range(7)}  # 各类别统计
        
        strategy_understanding_count = 0  # 策略理解正确数（动作和策略都正确）
        
        model.train()  # 确保模型处于训练模式
        
        for batch in dataloader:
            # 处理数据：支持多任务学习（返回策略标签和牌型信息）
            if enable_strategy_head and len(batch) == 4:
                # 新版本：返回4个值（state, action, strategy, pattern）
                states, actions, strategy_labels, pattern_types = batch
                strategy_labels = strategy_labels.to(device)
                pattern_types = pattern_types.to(device)
            elif enable_strategy_head and len(batch) == 3:
                # 旧版本：返回3个值（state, action, strategy）
                states, actions, strategy_labels = batch
                strategy_labels = strategy_labels.to(device)
                pattern_types = None
            else:
                # 向后兼容：如果数据集不返回策略标签，只使用动作预测
                states, actions = batch[0], batch[1]
                strategy_labels = None
                pattern_types = None
            
            states, actions = states.to(device), actions.to(device)
            
            optimizer.zero_grad()
            
            # 前向传播
            if enable_strategy_head and strategy_labels is not None:
                # 多任务学习：同时返回动作预测和策略分类
                action_logits, strategy_logits = model(states, return_strategy=True)
                
                # 计算动作预测损失（逐样本计算，支持样本权重）
                batch_size = actions.size(0)
                sample_losses = []
                
                # **阶段3改进**: 根据牌型给予不同权重
                # 三带二权重最高（3.0），其他复杂牌型次之（1.5），简单牌型正常（1.0）
                pattern_weights = {
                    3: 3.0,   # ThreeWithTwo: 3.0
                    4: 2.0,   # Sequence: 2.0
                    5: 1.5,   # Bomb: 1.5
                    6: 2.0,   # SteelPlate: 2.0
                    7: 2.0,   # WoodPlate: 2.0
                    8: 1.2,   # Complex: 1.2
                }
                
                for i in range(batch_size):
                    sample_logits = action_logits[i:i+1]
                    sample_actions = actions[i:i+1]
                    
                    # 计算单个样本的损失
                    sample_loss = action_criterion(sample_logits, sample_actions)
                    
                    # 应用牌型权重
                    if pattern_types is not None:
                        pattern_idx = pattern_types[i].item()
                        weight = pattern_weights.get(pattern_idx, 1.0)
                        sample_loss = sample_loss * weight
                    
                    sample_losses.append(sample_loss)
                
                # 平均所有样本的损失
                action_loss = torch.stack(sample_losses).mean()
                
                # **阶段3任务2.7改进**: 添加额外的正样本概率提升损失
                # 鼓励模型为正样本输出更高的概率
                if dropout_rate == 0.01 or dropout_rate == 0.05:
                    action_probs = torch.sigmoid(action_logits)
                    # 计算正样本的平均概率
                    positive_mask = actions > 0.5
                    if positive_mask.sum() > 0:
                        positive_probs = action_probs[positive_mask]
                        # 添加损失：鼓励正样本概率接近1.0
                        positive_prob_loss = torch.mean((1.0 - positive_probs) ** 2) * 0.1  # 权重0.1
                        action_loss = action_loss + positive_prob_loss
                
                # 计算策略分类损失（忽略unknown类别，即索引7）
                # 只计算非unknown样本的损失
                valid_mask = (strategy_labels < 7)  # 排除unknown（索引7）
                if valid_mask.sum() > 0:
                    valid_strategy_labels = strategy_labels[valid_mask]
                    valid_strategy_logits = strategy_logits[valid_mask]
                    strategy_loss = strategy_criterion(valid_strategy_logits, valid_strategy_labels)
                    strategy_loss_count += valid_mask.sum().item()
                else:
                    strategy_loss = torch.tensor(0.0, device=device)
                
                # 组合损失（使用当前动态权重）
                total_batch_loss = current_action_weight * action_loss + current_strategy_weight * strategy_loss
                
                total_action_loss += action_loss.item()
                total_strategy_loss += strategy_loss.item()
            else:
                # 单任务学习：只使用动作预测（也支持样本权重）
                action_logits = model(states, return_strategy=False)
                
                # 计算动作预测损失（逐样本计算，支持样本权重）
                batch_size = actions.size(0)
                sample_losses = []
                
                # **阶段3改进**: 根据牌型给予不同权重
                pattern_weights = {
                    3: 3.0,   # ThreeWithTwo: 3.0
                    4: 2.0,   # Sequence: 2.0
                    5: 1.5,   # Bomb: 1.5
                    6: 2.0,   # SteelPlate: 2.0
                    7: 2.0,   # WoodPlate: 2.0
                    8: 1.2,   # Complex: 1.2
                }
                
                for i in range(batch_size):
                    sample_logits = action_logits[i:i+1]
                    sample_actions = actions[i:i+1]
                    
                    # 计算单个样本的损失
                    sample_loss = action_criterion(sample_logits, sample_actions)
                    
                    # 应用牌型权重
                    if pattern_types is not None:
                        pattern_idx = pattern_types[i].item()
                        weight = pattern_weights.get(pattern_idx, 1.0)
                        sample_loss = sample_loss * weight
                    
                    sample_losses.append(sample_loss)
                
                # 平均所有样本的损失
                action_loss = torch.stack(sample_losses).mean()
                total_batch_loss = action_loss
                total_action_loss += action_loss.item()
            
            # 反向传播
            total_batch_loss.backward()
            optimizer.step()
            
            total_loss += total_batch_loss.item()
            
            # **阶段2任务3新增**: 计算评估指标（在训练模式下，使用阈值预测）
            with torch.no_grad():
                # 动作预测准确率
                # **基线评估参数**：使用阶段0验证的标准参数作为统一标尺
                # 所有阶段的模型评估必须使用此基线参数，不能为了提升准确率而调整
                action_probs = torch.sigmoid(action_logits)
                action_probs = action_probs * 5.0  # 基线缩放因子（阶段0基线参数）
                action_probs = torch.clamp(action_probs, 0, 1)
                action_predictions = (action_probs > 0.3).float()  # 基线阈值（阶段0基线参数）
                
                # 确保action_predictions和actions维度一致
                if action_predictions.shape != actions.shape:
                    min_dim = min(action_predictions.shape[1], actions.shape[1])
                    action_predictions = action_predictions[:, :min_dim]
                    actions = actions[:, :min_dim]
                
                # 完全匹配准确率
                exact_match = (action_predictions == actions).all(dim=1)
                batch_correct = exact_match.sum().item()
                correct_action_predictions += batch_correct
                total_samples += len(states)
                
                # 卡牌级别准确率
                batch_matched_cards = (action_predictions == actions).sum().item()
                batch_total_cards = actions.numel()
                matched_action_cards += batch_matched_cards
                total_action_cards += batch_total_cards
                
                # 策略分类准确率（如果启用策略分类头）
                if enable_strategy_head and strategy_labels is not None:
                    strategy_preds = torch.argmax(strategy_logits, dim=1)
                    valid_mask = (strategy_labels < 7)  # 排除unknown
                    
                    if valid_mask.sum() > 0:
                        valid_strategy_labels = strategy_labels[valid_mask]
                        valid_strategy_preds = strategy_preds[valid_mask]
                        
                        # 整体策略分类准确率
                        strategy_correct = (valid_strategy_preds == valid_strategy_labels)
                        correct_strategy_predictions += strategy_correct.sum().item()
                        total_strategy_samples += valid_mask.sum().item()
                        
                        # 各类别策略分类准确率
                        for label_idx in range(7):
                            class_mask = (valid_strategy_labels == label_idx)
                            if class_mask.sum() > 0:
                                strategy_correct_by_class[label_idx]['total'] += class_mask.sum().item()
                                class_correct = (valid_strategy_preds[class_mask] == valid_strategy_labels[class_mask])
                                strategy_correct_by_class[label_idx]['correct'] += class_correct.sum().item()
                        
                        # 策略理解率（动作预测和策略分类都正确）
                        if total_samples > 0:
                            # 对于有效策略样本，检查动作和策略是否都正确
                            # exact_match是(batch_size,)形状，valid_mask也是(batch_size,)形状
                            # 需要确保维度匹配
                            if exact_match.dim() == 1 and valid_mask.dim() == 1:
                                valid_exact_match = exact_match[valid_mask]
                                valid_strategy_correct = strategy_correct
                                # 确保两个tensor都是1维且长度相同
                                if valid_exact_match.shape == valid_strategy_correct.shape:
                                    both_correct = (valid_exact_match & valid_strategy_correct)
                                    strategy_understanding_count += both_correct.sum().item()
            
        avg_loss = total_loss / len(dataloader)
        avg_action_loss = total_action_loss / len(dataloader)
        avg_strategy_loss = total_strategy_loss / strategy_loss_count if strategy_loss_count > 0 else 0.0
        current_lr = optimizer.param_groups[0]['lr']
        
        # **阶段2任务3新增**: 计算评估指标
        action_exact_accuracy = correct_action_predictions / total_samples if total_samples > 0 else 0.0
        action_card_accuracy = matched_action_cards / total_action_cards if total_action_cards > 0 else 0.0
        strategy_accuracy = correct_strategy_predictions / total_strategy_samples if total_strategy_samples > 0 else 0.0
        strategy_understanding_rate = strategy_understanding_count / total_strategy_samples if total_strategy_samples > 0 else 0.0
        
        # 记录训练历史
        training_history['epochs'].append(epoch + 1)
        training_history['total_loss'].append(avg_loss)
        training_history['action_loss'].append(avg_action_loss)
        training_history['strategy_loss'].append(avg_strategy_loss)
        training_history['action_exact_accuracy'].append(action_exact_accuracy)
        training_history['action_card_accuracy'].append(action_card_accuracy)
        training_history['strategy_accuracy'].append(strategy_accuracy)
        training_history['strategy_understanding_rate'].append(strategy_understanding_rate)
        
        for label_idx in range(7):
            if strategy_correct_by_class[label_idx]['total'] > 0:
                class_accuracy = strategy_correct_by_class[label_idx]['correct'] / strategy_correct_by_class[label_idx]['total']
                training_history['strategy_accuracy_by_class'][label_idx].append(class_accuracy)
            else:
                training_history['strategy_accuracy_by_class'][label_idx].append(0.0)
        
        # **阶段2任务3新增**: 详细日志输出
        if enable_strategy_head and strategy_loss_count > 0:
            print(f"Epoch {epoch+1}/{epochs}:")
            print(f"  Loss - Total: {avg_loss:.4f}, Action: {avg_action_loss:.4f}, Strategy: {avg_strategy_loss:.4f}, LR: {current_lr:.6f}")
            print(f"  Action Accuracy - Exact: {action_exact_accuracy:.2%}, Card: {action_card_accuracy:.2%}")
            print(f"  Strategy Accuracy - Overall: {strategy_accuracy:.2%}, Understanding Rate: {strategy_understanding_rate:.2%}")
            
            # 各类别策略准确率（只显示有样本的类别）
            strategy_type_names = ['bomb', 'suppress', 'protect', 'control', 'group', 'follow', 'discard']
            class_accuracies = []
            for label_idx in range(7):
                if strategy_correct_by_class[label_idx]['total'] > 0:
                    class_acc = strategy_correct_by_class[label_idx]['correct'] / strategy_correct_by_class[label_idx]['total']
                    class_accuracies.append(f"{strategy_type_names[label_idx]}: {class_acc:.2%}")
            if class_accuracies:
                print(f"  Strategy Accuracy by Class - {', '.join(class_accuracies)}")
        else:
            print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_loss:.4f}, Action Exact Accuracy: {action_exact_accuracy:.2%}, Action Card Accuracy: {action_card_accuracy:.2%}, LR: {current_lr:.6f}")
        
        # **阶段3任务2.5方案B**: 动态损失权重调整
        if use_dynamic_weight and enable_strategy_head and (epoch + 1) % weight_adjust_interval == 0 and epoch > 0:
            # 根据任务准确率动态调整权重
            # 如果动作预测准确率低，增加动作预测权重
            # 如果策略分类准确率高，可以适当降低策略分类权重
            
            # 获取最近N个epoch的平均准确率（用于稳定性）
            lookback = min(weight_adjust_interval, len(training_history['action_exact_accuracy']))
            if lookback > 0:
                recent_action_acc = np.mean(training_history['action_exact_accuracy'][-lookback:])
                recent_strategy_acc = np.mean(training_history['strategy_accuracy'][-lookback:]) if len(training_history['strategy_accuracy']) >= lookback else strategy_accuracy
                
                # 调整策略：
                # 1. 如果动作预测准确率 < 20%，增加动作预测权重（最多增加到2.0倍）
                # 2. 如果策略分类准确率 > 95%，可以适当降低策略分类权重（最多降低到0.1）
                # 3. 权重调整幅度：每次调整10%
                
                old_action_weight = current_action_weight
                old_strategy_weight = current_strategy_weight
                
                if recent_action_acc < 0.20:  # 动作预测准确率低
                    # 增加动作预测权重
                    current_action_weight = min(current_action_weight * 1.1, action_loss_weight * 2.0)
                    print(f"  [动态权重调整] 动作预测准确率低({recent_action_acc:.2%})，增加动作预测权重: {old_action_weight:.3f} → {current_action_weight:.3f}")
                
                if recent_strategy_acc > 0.95:  # 策略分类准确率高
                    # 可以适当降低策略分类权重
                    current_strategy_weight = max(current_strategy_weight * 0.9, strategy_loss_weight * 0.1)
                    print(f"  [动态权重调整] 策略分类准确率高({recent_strategy_acc:.2%})，降低策略分类权重: {old_strategy_weight:.3f} → {current_strategy_weight:.3f}")
                
                # 如果权重发生变化，打印当前权重
                if abs(current_action_weight - old_action_weight) > 0.001 or abs(current_strategy_weight - old_strategy_weight) > 0.001:
                    print(f"  [动态权重调整] 当前权重: α={current_action_weight:.3f}, β={current_strategy_weight:.3f}")
        
        # **阶段2任务3新增**: 保存模型检查点（每10个epoch保存一次）
        if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
            checkpoint_path = model_path.replace('.pth', f'_epoch_{epoch+1}.pth')
            checkpoint_dir = os.path.dirname(checkpoint_path)
            if checkpoint_dir:
                os.makedirs(checkpoint_dir, exist_ok=True)
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'scheduler_state_dict': scheduler.state_dict(),
                'training_history': training_history,
                'loss': avg_loss,
                'action_exact_accuracy': action_exact_accuracy,
                'strategy_accuracy': strategy_accuracy,
            }, checkpoint_path)
            print(f"  [Checkpoint] Model saved to {checkpoint_path}")
        
        # 更新学习率
        scheduler.step()
        
    # 4. Save Model
    model_dir = os.path.dirname(model_path)
    if model_dir:
        os.makedirs(model_dir, exist_ok=True)
    
    # **阶段2任务3新增**: 保存最终模型和训练历史
    final_model_data = {
        'model_state_dict': model.state_dict(),
        'training_history': training_history,
        'final_epoch': epochs,
        'final_loss': training_history['total_loss'][-1] if training_history['total_loss'] else 0.0,
        'final_action_exact_accuracy': training_history['action_exact_accuracy'][-1] if training_history['action_exact_accuracy'] else 0.0,
        'final_strategy_accuracy': training_history['strategy_accuracy'][-1] if training_history['strategy_accuracy'] else 0.0,
        'final_strategy_understanding_rate': training_history['strategy_understanding_rate'][-1] if training_history['strategy_understanding_rate'] else 0.0,
    }
    torch.save(final_model_data, model_path)
    print(f"Model saved to {model_path}")
    
    # **阶段2任务3新增**: 保存训练历史到JSON文件
    import json
    history_file = model_path.replace('.pth', '_training_history.json')
    try:
        # 转换numpy类型为Python原生类型
        history_for_json = {
            'epochs': training_history['epochs'],
            'total_loss': [float(x) for x in training_history['total_loss']],
            'action_loss': [float(x) for x in training_history['action_loss']],
            'strategy_loss': [float(x) for x in training_history['strategy_loss']],
            'action_exact_accuracy': [float(x) for x in training_history['action_exact_accuracy']],
            'action_card_accuracy': [float(x) for x in training_history['action_card_accuracy']],
            'strategy_accuracy': [float(x) for x in training_history['strategy_accuracy']],
            'strategy_understanding_rate': [float(x) for x in training_history['strategy_understanding_rate']],
            'strategy_accuracy_by_class': {
                str(k): [float(x) for x in v] for k, v in training_history['strategy_accuracy_by_class'].items()
            }
        }
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_for_json, f, indent=2, ensure_ascii=False)
        print(f"Training history saved to {history_file}")
    except Exception as e:
        print(f"[WARNING] Failed to save training history: {e}")
    
    # **阶段2任务3新增**: 输出最终训练结果摘要
    print("\n" + "="*60)
    print("训练完成摘要")
    print("="*60)
    if training_history['action_exact_accuracy']:
        print(f"最终动作预测准确率 - 完全匹配: {training_history['action_exact_accuracy'][-1]:.2%}, 卡牌级别: {training_history['action_card_accuracy'][-1]:.2%}")
    if training_history['strategy_accuracy']:
        print(f"最终策略分类准确率: {training_history['strategy_accuracy'][-1]:.2%}")
        print(f"最终策略理解率: {training_history['strategy_understanding_rate'][-1]:.2%}")
    print("="*60)

if __name__ == "__main__":
    # 阶段3任务2.6方案D：测试课程学习效果（796样本，50 epochs，3个阶段）
    import random
    import numpy as np
    import torch
    
    # 固定随机种子，确保训练可复现
    seed = 42
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    
    # 阶段3任务2.7：提高卡牌识别率到99%+
    # 改进：降低dropout到0.05，增加pos_weight到4.0，增加训练轮数到100
    train_bc(epochs=100, max_samples=796, use_dynamic_weight=False, use_separated_features=False,
             use_curriculum_learning=False, dropout_rate=0.05)  # 暂时禁用课程学习，专注于提高输出概率
