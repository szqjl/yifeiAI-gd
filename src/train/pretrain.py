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
from src.rl_agent.model import GuandanPolicyNet, ImprovedGuandanPolicyNet
from src.rl_agent.strategy_pattern_recognizer import StrategyPatternRecognizer
from src.rl_agent.opponent_model import OpponentModel
from src.rl_agent.dynamic_strategy_adjuster import DynamicStrategyAdjuster


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
    评估样本应该属于哪个课程学习阶段（阶段0：基础验证与数据验证）
    
    按照阶段0文档要求，分为4个阶段（按牌型划分）：
    阶段1：简单牌型（单张、对子、三张）
    阶段2：中等牌型（三带二、顺子）
    阶段3：复杂牌型（炸弹、复杂组合）
    阶段4：所有牌型混合训练
    
    Args:
        state_dict: 状态字典
        action_cards: 动作卡牌列表
    
    Returns:
        stage: 课程阶段（1-4）
    """
    if not action_cards:
        return 1  # Pass动作归为阶段1
    
    # 识别卡牌模式类型（传入state_dict以支持级牌和PASS识别）
    pattern_type = identify_card_pattern_type(action_cards, state_dict)
    
    # 阶段1：简单牌型（单张、对子、三张、Pass）
    if pattern_type in ["Pass", "Single", "Pair", "Triple"]:
        return 1
    
    # 阶段2：中等牌型（三带二、顺子）
    elif pattern_type in ["ThreeWithTwo", "Sequence"]:
        return 2
    
    # 阶段3：复杂牌型（炸弹、复杂组合）
    elif pattern_type in ["Bomb", "Complex", "SteelPlate", "WoodPlate"]:
        return 3
    
    # 阶段4：所有牌型混合（在训练时使用，这里不会返回4）
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


def compute_top_k_loss(logits, targets, k_values, reduction='mean'):
    """
    计算Top-K损失：只允许模型预测前K个高概率卡牌

    Args:
        logits: 模型输出的logits (batch_size, num_classes)
        targets: 真实标签 (batch_size, num_classes)
        k_values: 每个样本的K值 (batch_size,) - 基于真实卡牌数
        reduction: 损失归约方式 ('mean' 或 'sum')

    Returns:
        Top-K损失值
    """
    batch_size = logits.shape[0]

    # 计算概率
    probs = torch.sigmoid(logits)

    total_loss = 0.0
    valid_samples = 0

    for i in range(batch_size):
        sample_logits = logits[i:i+1]  # (1, num_classes)
        sample_targets = targets[i:i+1]  # (1, num_classes)
        sample_probs = probs[i:i+1]  # (1, num_classes)
        k = int(k_values[i].item()) if hasattr(k_values[i], 'item') else int(k_values[i])

        if k <= 0:
            continue

        # 确保k不超过总类别数
        k = min(k, sample_logits.shape[1])

        # 获取Top-K概率最高的索引
        topk_values, topk_indices = torch.topk(sample_probs, k, dim=1)

        # 创建Top-K掩码：只有Top-K位置允许预测
        topk_mask = torch.zeros_like(sample_targets)
        topk_mask.scatter_(1, topk_indices, 1.0)

        # 计算Top-K约束损失
        # 对于Top-K之外的位置，如果模型预测概率过高，给予惩罚
        non_topk_mask = 1.0 - topk_mask

        # 计算非Top-K位置的预测概率（应该接近0）
        non_topk_probs = sample_probs * non_topk_mask
        non_topk_loss = torch.mean(non_topk_probs ** 2)  # MSE损失，鼓励非Top-K概率为0

        # 计算Top-K位置的BCE损失
        topk_logits = sample_logits * topk_mask
        topk_targets = sample_targets * topk_mask
        topk_bce_loss = F.binary_cross_entropy_with_logits(
            topk_logits, topk_targets, reduction='mean'
        )

        # 组合损失：Top-K BCE损失 + 非Top-K惩罚
        sample_loss = topk_bce_loss + 0.1 * non_topk_loss
        total_loss += sample_loss
        valid_samples += 1

    if valid_samples == 0:
        return torch.tensor(0.0, device=logits.device)

    if reduction == 'mean':
        return total_loss / valid_samples
    else:
        return total_loss

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
        # 从游戏状态中计算这些标志，而不是依赖state_dict
        hand = state_dict.get('hand', [])
        hand_count = len(hand) if hand else 0
        last_action = state_dict.get('last_action', {})
        player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
        current_player = state_dict.get('current_player', 0)
        
        # can_follow: 是否能顺牌（上家出单，自己能跟）
        can_follow = 0.0
        if last_action:
            last_action_type = last_action.get('type', '')
            # 简化判断：如果上一步是单牌，且自己有手牌，可能能跟
            if last_action_type == 'Single' and hand_count > 0:
                can_follow = 1.0
        state_vec[152] = can_follow
        
        # can_followup: 是否能跟牌（对手出牌，自己能跟）
        can_followup = 0.0
        if last_action:
            last_action_type = last_action.get('type', '')
            # 如果上一步不是PASS，且自己有手牌，可能能跟
            if last_action_type not in ['PASS', 'pass', ''] and hand_count > 0:
                can_followup = 1.0
        state_vec[153] = can_followup
        
        # need_control: 是否需要控牌（对手快走完，剩余牌数<=5）
        need_control = 0.0
        if len(player_rest_cards) >= 4:
            # 计算对手（非当前玩家）的最小剩余牌数
            opponent_cards = [player_rest_cards[i] for i in range(4) if i != current_player]
            if opponent_cards:
                min_opponent_cards = min(opponent_cards)
                if min_opponent_cards <= 5:
                    need_control = 1.0
        state_vec[154] = need_control
        
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
        # 注意：如果strategy_effectiveness不存在或为0，保持为0.0（这是正常的，因为只有部分动作有策略效果）
        strategy_effectiveness = state_dict.get('strategy_effectiveness', 0.0)
        if 163 < 512:
            # 归一化到[0, 1]，最大值30
            normalized_effectiveness = min(strategy_effectiveness / 30.0, 1.0) if strategy_effectiveness > 0 else 0.0
            state_vec[163] = normalized_effectiveness
        
        # 8. 编码历史动作（164-511维，348个维度）- 新增：实现历史动作编码
        # 每个历史动作编码为17维：动作类型（10维）+ 动作牌点（15维）+ 动作玩家（2维）
        # 最多编码20个历史动作（20 * 17 = 340维），剩余8维保留
        history = state_dict.get('history', [])
        if history:
            # 动作类型映射（与last_action编码保持一致）
            action_type_map = {
                'PASS': 0, 'Single': 1, 'Pair': 2, 'Trips': 3,
                'Straight': 4, 'ThreeWithTwo': 5, 'Bomb': 6,
                'StraightFlush': 7, 'ThreePair': 8, 'TwoTrips': 9
            }
            # 牌点映射（与last_action编码保持一致）
            rank_map = {
                '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7,
                'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12,
                'B': 13, 'R': 14
            }
            
            # 取最近20个历史动作（从新到旧）
            max_history = min(20, len(history))
            for hist_idx in range(max_history):
                hist_action = history[-(hist_idx + 1)]  # 从最新到最旧
                
                # 计算起始维度：164 + hist_idx * 17
                base_dim = 164 + hist_idx * 17
                if base_dim + 17 > 512:
                    break  # 超出范围，停止编码
                
                # 编码动作类型（10维，base_dim到base_dim+9）
                action_type = hist_action.get('action_type', 'PASS')
                if isinstance(action_type, str):
                    action_type_idx = action_type_map.get(action_type, 0)
                else:
                    action_type_idx = 0
                if action_type_idx < 10:
                    state_vec[base_dim + action_type_idx] = 1.0
                
                # 编码动作牌点（15维，base_dim+10到base_dim+24）
                action_cards = hist_action.get('action', [])
                if action_cards and len(action_cards) > 0:
                    # 取第一张卡牌的点数
                    first_card = action_cards[0]
                    if isinstance(first_card, str) and len(first_card) >= 2:
                        rank = first_card[1] if len(first_card) == 2 else first_card[1:2]
                        rank_idx = rank_map.get(rank, 0)
                        if rank_idx < 15:
                            state_vec[base_dim + 10 + rank_idx] = 1.0
                
                # 编码动作玩家（2维，base_dim+25到base_dim+26，使用二进制编码）
                # 玩家0: 00, 玩家1: 01, 玩家2: 10, 玩家3: 11
                player = hist_action.get('player', 0)
                if isinstance(player, int) and 0 <= player <= 3:
                    player_binary = player
                    state_vec[base_dim + 25] = float((player_binary >> 1) & 1)  # 高位
                    state_vec[base_dim + 26] = float(player_binary & 1)  # 低位
                # 注意：base_dim+27到base_dim+33（7维）保留未使用
            
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
        
        # **阶段5新增**：生成策略模式标签
        # 基于策略类型和游戏状态推断策略模式
        strategy_pattern_idx = self._infer_strategy_pattern(state_dict, strategy_type)
        # 确保索引在有效范围内（0-7）
        strategy_pattern_idx = self._clamp_strategy_pattern_idx(strategy_pattern_idx)
        
        # **新增**：提取6个策略学习任务标签
        strategy_tasks = state_dict.get('strategy_tasks', {})
        grouping_label = strategy_tasks.get('grouping', 0)
        role_label = strategy_tasks.get('role', 2)
        power_score = strategy_tasks.get('power', 5.0)
        protect_suppress_label = strategy_tasks.get('protect_suppress', 2)
        bomb_timing_label = strategy_tasks.get('bomb_timing', 4)
        red_heart_label = strategy_tasks.get('red_heart', 3)
        
        # **新增**：提取策略原因标签（任务7：策略原因学习）
        # 策略原因类型映射（26类，根据strategy_reason_extractor.py）
        strategy_reason = state_dict.get('strategy_reason', {})
        reason_type = strategy_reason.get('reason_type', 'unknown')
        reason_type_map = {
            'bomb_urgent': 0, 'bomb_endgame': 1, 'bomb_counter': 2, 'bomb_opportunity': 3,
            'suppress_urgent': 4, 'suppress_combo': 5, 'suppress_block': 6, 'suppress_general': 7,
            'protect_teammate_urgent': 8, 'protect_teammate': 9, 'protect_advantage': 10, 'protect_general': 11,
            'control_urgent': 12, 'control_endgame': 13, 'control_general': 14,
            'group_reduce_hands': 15, 'group_reduce_singles': 16, 'group_optimize': 17, 'group_general': 18,
            'follow_counter': 19, 'follow_single': 20, 'follow_general': 21,
            'discard_opening': 22, 'discard_endgame': 23, 'discard_general': 24,
            'unknown': 25
        }
        reason_label = reason_type_map.get(reason_type, 25)  # 默认unknown=25

        return torch.FloatTensor(state_vec), torch.FloatTensor(action_vec), strategy_type_idx, pattern_type_idx, strategy_pattern_idx, \
               torch.tensor(grouping_label, dtype=torch.long), torch.tensor(role_label, dtype=torch.long), \
               torch.tensor(power_score, dtype=torch.float32), torch.tensor(protect_suppress_label, dtype=torch.long), \
               torch.tensor(bomb_timing_label, dtype=torch.long), torch.tensor(red_heart_label, dtype=torch.long), \
               torch.tensor(reason_label, dtype=torch.long)  # 新增：策略原因标签

    def _infer_strategy_pattern(self, state_dict, strategy_type):
        """
        基于策略类型和游戏状态推断策略模式

        Args:
            state_dict: 状态字典
            strategy_type: 策略类型字符串

        Returns:
            strategy_pattern_idx: 策略模式索引 (0-7)
        """
        # 简化的策略模式推断逻辑
        # 基于策略类型映射到策略模式

        strategy_pattern_map = {
            'bomb': 0,      # bomb_strategy
            'suppress': 4,  # suppress_strategy
            'protect': 4,   # protect_strategy (暂时映射到suppress)
            'control': 1,   # control_strategy
            'group': 5,     # group_strategy
            'follow': 2,    # follow_strategy
            'discard': 6,   # discard_strategy
        }

        # 基于策略类型确定策略模式
        if strategy_type in strategy_pattern_map:
            return strategy_pattern_map[strategy_type]
        else:
            # 基于游戏状态进行更复杂的推断
            game_phase = state_dict.get('game_phase', 1)
            player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])

            # 开局阶段，倾向于follow_strategy
            if game_phase == 0:
                return 2  # follow_strategy
            # 残局阶段，倾向于control_strategy
            elif game_phase == 2:
                return 1  # control_strategy
            # 中局阶段，基于剩余牌数判断
            else:
                current_player_idx = state_dict.get('current_player', 0)
                if current_player_idx < len(player_rest_cards):
                    current_cards = player_rest_cards[current_player_idx]
                    if current_cards < 10:
                        return 6  # discard_strategy (残牌阶段)
                    elif current_cards > 20:
                        return 2  # follow_strategy (多牌阶段)
                    else:
                        return 1  # control_strategy (中等牌数)

        return 7  # unknown_strategy
    
    def _clamp_strategy_pattern_idx(self, idx):
        """
        确保策略模式索引在有效范围内（0-7）
        
        Args:
            idx: 策略模式索引
            
        Returns:
            clamped_idx: 限制在0-7范围内的索引
        """
        return max(0, min(7, int(idx)))


def train_bc(data_dir="game_records", epochs=30, batch_size=64, lr=0.0003, model_path="models/bc_model_v1.pth", 
             dropout_rate=0.1, enable_strategy_head=True, action_loss_weight=1.5, strategy_loss_weight=0.3,
             max_samples=None, use_dynamic_weight=False, weight_adjust_interval=5, use_separated_features=False,
             use_curriculum_learning=False, curriculum_stages=3, use_improved_model=False, attention_heads=8,
             enable_strategy_pattern=True, strategy_pattern_weight=0.2,
             enable_opponent_modeling=True, opponent_model_weight=0.15,
             enable_dynamic_strategy=True, dynamic_strategy_weight=0.1):
    """
    行为克隆预训练（支持多任务学习）

    **数据平衡权重**: 降低高频动作权重，提高低频动作权重
    """
    # 定义数据平衡权重（函数级别变量）
    action_frequency_weights = {
        0: 0.3,   # 索引0过于频繁，降低权重
        45: 0.2,  # 索引45过于频繁，降低权重
        46: 0.5,  # 索引46较频繁，降低权重
        57: 0.2,  # 索引57过于频繁，降低权重
    }
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
        use_improved_model: 是否使用改进的模型架构（阶段4：包含注意力机制）
        attention_heads: 注意力头数（仅在改进模型中有效，默认8）
        enable_strategy_pattern: 是否启用策略模式识别（阶段5：高级策略学习）
        strategy_pattern_weight: 策略模式识别损失权重（阶段5，默认0.2）
        enable_opponent_modeling: 是否启用对手建模（阶段5，默认True）
        opponent_model_weight: 对手建模损失权重（阶段5，默认0.15）
        enable_dynamic_strategy: 是否启用动态策略调整（阶段5，默认True）
        dynamic_strategy_weight: 动态策略调整损失权重（阶段5，默认0.1）
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
        print("课程设计思路（按牌型从简单到复杂）：")
        print("  阶段1：简单牌型（单张、对子、三张）- 约25个epoch")
        print("  阶段2：中等牌型（三带二、顺子）- 约25个epoch")
        print("  阶段3：复杂牌型（炸弹、复杂组合）- 约25个epoch")
        print("  阶段4：所有牌型混合训练 - 约25个epoch")
        
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
        
        # 第二步：按阶段顺序构建课程数据（阶段1-3）
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
        
        # 第三步：添加阶段4（所有牌型混合训练）
        if curriculum_stage_data:
            all_stage_data = raw_data  # 使用全部数据
            all_pattern_types = pattern_type_counts.copy()
            all_strategy_types = strategy_type_counts.copy()
            
            curriculum_stage_data.append({
                'data': all_stage_data,
                'stage': 4,
                'pattern_types': all_pattern_types,
                'strategy_types': all_strategy_types
            })
            print(f"  阶段4（混合训练）: {len(all_stage_data)}个样本（所有牌型混合）")
            print(f"    牌型分布: {all_pattern_types}")
            print(f"    策略类型分布: {all_strategy_types}")
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
    # **修复**: 支持强制使用CPU训练（解决旧GPU兼容性问题）
    # 如果环境变量FORCE_CPU=1，强制使用CPU
    force_cpu = os.environ.get('FORCE_CPU', '0') == '1'
    if force_cpu:
        device = torch.device("cpu")
        print(f"[警告] 强制使用CPU训练（FORCE_CPU=1）")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # **关键修复**：模型输入输出维度必须与推理代码一致
    # 输入：512维状态向量
    # 输出：512维动作向量（每个维度表示是否选择对应的卡牌索引）
    # **优化**: 使用降低的dropout_rate (0.1)，减少过拟合，提高输出概率
    # **阶段2新增**: 启用策略分类头（多任务学习）
    # **阶段3任务2回退**: 隐藏层维度回退到256（512在796样本上效果差，完全匹配准确率0.00%）
    # **阶段3任务2.5方案C**: 分离的特征提取层（共享底层特征，分离高层特征）
    # **阶段4新增**: 改进模型架构（注意力机制 + 残差连接）
    # **新增**：启用7个策略学习任务（包含策略原因学习）
    enable_strategy_tasks = True  # 默认启用7个策略任务
    strategy_tasks_weight = 0.5  # 7个策略任务的总权重（平均每个任务约0.071，阶段6支持动态调整）
    
    if use_improved_model:
        model = ImprovedGuandanPolicyNet(
            input_dim=512,
            hidden_dim=256,
            output_dim=512,
            dropout_rate=dropout_rate,
            strategy_num_classes=7,
            enable_strategy_head=enable_strategy_head,
            attention_heads=attention_heads,
            enable_strategy_tasks=enable_strategy_tasks  # 新增：启用6个策略任务
        ).to(device)
        print(f"Model: ImprovedGuandanPolicyNet, input_dim=512, hidden_dim=256, output_dim=512, dropout_rate={dropout_rate}, strategy_head={enable_strategy_head}, attention_heads={attention_heads}, strategy_tasks={enable_strategy_tasks} (阶段4：注意力机制 + 残差连接 + 6个策略任务)")
    else:
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
            print(f"Model: GuandanPolicyNet, input_dim=512, hidden_dim=256, output_dim=512, dropout_rate={dropout_rate}, strategy_head={enable_strategy_head} (阶段3任务2.5方案C：分离特征提取层)")
        else:
            print(f"Model: GuandanPolicyNet, input_dim=512, hidden_dim=256, output_dim=512, dropout_rate={dropout_rate}, strategy_head={enable_strategy_head} (阶段3任务2回退：恢复任务1配置)")

    # **阶段5新增**: 高级策略学习组件
    strategy_pattern_recognizer = None
    opponent_model = None
    dynamic_strategy_adjuster = None

    if enable_strategy_pattern:
        strategy_pattern_recognizer = StrategyPatternRecognizer(
            input_dim=512,
            pattern_types=8,  # 8种策略模式
            hidden_dim=256
        ).to(device)
        print(f"Strategy Pattern Recognizer: enabled, pattern_types=8, hidden_dim=256 (阶段5：策略模式识别)")

    if enable_opponent_modeling:
        opponent_model = OpponentModel(
            state_dim=512,
            action_dim=512,
            opponent_types=5  # 5种对手类型
        ).to(device)
        print(f"Opponent Model: enabled, opponent_types=5, feature_dim=128 (阶段5：对手建模)")

    if enable_dynamic_strategy:
        dynamic_strategy_adjuster = DynamicStrategyAdjuster(
            state_dim=512,
            strategy_count=7  # 7种策略
        ).to(device)
        print(f"Dynamic Strategy Adjuster: enabled, strategy_count=7, feature_dim=128 (阶段5：动态策略调整)")

    # 收集所有需要训练的参数
    all_params = list(model.parameters())

    if enable_strategy_pattern and strategy_pattern_recognizer is not None:
        all_params.extend(strategy_pattern_recognizer.parameters())

    if enable_opponent_modeling and opponent_model is not None:
        all_params.extend(opponent_model.parameters())

    if enable_dynamic_strategy and dynamic_strategy_adjuster is not None:
        all_params.extend(dynamic_strategy_adjuster.parameters())

    optimizer = optim.Adam(all_params, lr=lr)
    
    # **阶段3任务2.5回退**: 回退到BCE Loss（Focal Loss效果不理想）
    # 使用加权BCE Loss，增加对预测过少的惩罚
    # 权重策略：对于正样本（应该选择的卡牌），给予更高权重（2.0倍）
    # **阶段3任务2.7改进**: 根据dropout_rate调整pos_weight以提高输出概率
    # **阶段0方案C（基于历史经验）**: 针对预测过多问题，降低pos_weight并增加Dropout
    if dropout_rate == 0.2:
        pos_weight = torch.tensor(1.5).to(device)  # 正样本权重：1.5（降低以解决预测过多问题，基于历史经验）
        print(f"[阶段0方案C] 使用加权BCE Loss (pos_weight=1.5, dropout_rate=0.2)，基于历史经验解决预测过多问题")
    elif dropout_rate == 0.01:
        pos_weight = torch.tensor(8.0).to(device)  # 正样本权重：8.0（极大增加对预测过少的惩罚，提高正样本概率）
        print(f"[阶段3任务2.7版本2] 使用加权BCE Loss (pos_weight=8.0, dropout_rate=0.01)，进一步提高卡牌识别率")
    elif dropout_rate == 0.05:
        pos_weight = torch.tensor(4.0).to(device)  # 正样本权重：4.0（大幅增加对预测过少的惩罚，提高正样本概率）
        print(f"[阶段3任务2.7] 使用加权BCE Loss (pos_weight=4.0, dropout_rate=0.05)，提高卡牌识别率")
    else:
        pos_weight = torch.tensor(2.0).to(device)  # 正样本权重：2.0（增加对预测过少的惩罚）
        print(f"[阶段3任务2.5回退] 使用加权BCE Loss (pos_weight=2.0)，恢复任务1配置")
    # **阶段0方案D（改进损失函数）**: 使用改进的损失函数解决预测过多问题
    # 包含：预测数量惩罚 + 加权BCE + Top-K损失
    use_improved_loss = True  # 是否使用改进的损失函数
    use_top_k_loss = True  # 重新启用Top-K损失（阶段1紧急修复）
    if use_improved_loss:
        if use_top_k_loss:
            print(f"[阶段0方案D] 使用改进的损失函数（预测数量惩罚 + 加权BCE + Top-K损失）")
        else:
            print(f"[阶段0方案D] 使用改进的损失函数（预测数量惩罚 + 加权BCE，Top-K损失禁用）")
        action_criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # 基础BCE损失
    else:
        action_criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)  # 动作预测损失（加权BCE）
    
    # **阶段2新增**: 策略分类损失（交叉熵损失）
    # 注意：CrossEntropyLoss内部会应用Softmax，所以不需要在模型输出上应用Softmax
    strategy_criterion = nn.CrossEntropyLoss(ignore_index=7) if enable_strategy_head else None  # 忽略unknown类别（索引7）
    
    # **阶段0方案I-1**：修复学习率调度，避免学习停止
    # 使用Cosine Annealing避免学习率过早降到0
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    
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
        total_strategy_pattern_loss = 0  # 阶段5新增：策略模式识别损失
        total_opponent_model_loss = 0    # 阶段5新增：对手建模损失
        total_dynamic_strategy_loss = 0  # 阶段5新增：动态策略调整损失
        total_strategy_tasks_loss = 0    # 新增：6个策略任务损失
        
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
            # 处理数据：支持多任务学习和策略模式识别 + 7个策略任务（新增策略原因学习）
            if len(batch) == 12:
                # **新增**：返回12个值（state, action, strategy, pattern, strategy_pattern, 
                #          grouping, role, power, protect_suppress, bomb_timing, red_heart, reason）
                states, actions, strategy_labels, pattern_types, strategy_pattern_labels, \
                grouping_labels, role_labels, power_scores, protect_suppress_labels, \
                bomb_timing_labels, red_heart_labels, reason_labels = batch
                strategy_labels = strategy_labels.to(device)
                pattern_types = pattern_types.to(device)
                strategy_pattern_labels = strategy_pattern_labels.to(device)
                grouping_labels = grouping_labels.to(device)
                role_labels = role_labels.to(device)
                power_scores = power_scores.to(device)
                protect_suppress_labels = protect_suppress_labels.to(device)
                bomb_timing_labels = bomb_timing_labels.to(device)
                red_heart_labels = red_heart_labels.to(device)
                reason_labels = reason_labels.to(device)  # 新增：策略原因标签
            elif len(batch) == 11:
                # **新增**：返回11个值（state, action, strategy, pattern, strategy_pattern, 
                #          grouping, role, power, protect_suppress, bomb_timing, red_heart）
                states, actions, strategy_labels, pattern_types, strategy_pattern_labels, \
                grouping_labels, role_labels, power_scores, protect_suppress_labels, \
                bomb_timing_labels, red_heart_labels = batch
                strategy_labels = strategy_labels.to(device)
                pattern_types = pattern_types.to(device)
                strategy_pattern_labels = strategy_pattern_labels.to(device)
                grouping_labels = grouping_labels.to(device)
                role_labels = role_labels.to(device)
                power_scores = power_scores.to(device)
                protect_suppress_labels = protect_suppress_labels.to(device)
                bomb_timing_labels = bomb_timing_labels.to(device)
                red_heart_labels = red_heart_labels.to(device)
                reason_labels = None  # 旧数据没有策略原因标签
            elif len(batch) == 5:
                # 阶段5：返回5个值（state, action, strategy, pattern, strategy_pattern）
                states, actions, strategy_labels, pattern_types, strategy_pattern_labels = batch
                strategy_labels = strategy_labels.to(device)
                pattern_types = pattern_types.to(device)
                strategy_pattern_labels = strategy_pattern_labels.to(device)
                grouping_labels = None
                role_labels = None
                power_scores = None
                protect_suppress_labels = None
                bomb_timing_labels = None
                red_heart_labels = None
            elif enable_strategy_head and len(batch) == 4:
                # 新版本：返回4个值（state, action, strategy, pattern）
                states, actions, strategy_labels, pattern_types = batch
                strategy_labels = strategy_labels.to(device)
                pattern_types = pattern_types.to(device)
                strategy_pattern_labels = None
                grouping_labels = None
                role_labels = None
                power_scores = None
                protect_suppress_labels = None
                bomb_timing_labels = None
                red_heart_labels = None
            elif enable_strategy_head and len(batch) == 3:
                # 旧版本：返回3个值（state, action, strategy）
                states, actions, strategy_labels = batch
                strategy_labels = strategy_labels.to(device)
                pattern_types = None
                strategy_pattern_labels = None
                grouping_labels = None
                role_labels = None
                power_scores = None
                protect_suppress_labels = None
                bomb_timing_labels = None
                red_heart_labels = None
            else:
                # 向后兼容：如果数据集不返回策略标签，只使用动作预测
                states, actions = batch[0], batch[1]
                strategy_labels = None
                pattern_types = None
                strategy_pattern_labels = None
                grouping_labels = None
                role_labels = None
                power_scores = None
                protect_suppress_labels = None
                bomb_timing_labels = None
                red_heart_labels = None
            
            states, actions = states.to(device), actions.to(device)
            
            optimizer.zero_grad()
            
            # 前向传播
            if enable_strategy_head and strategy_labels is not None:
                # 多任务学习：同时返回动作预测、策略分类和6个策略任务
                if enable_strategy_tasks and grouping_labels is not None:
                    # 返回动作预测、策略分类和6个策略任务
                    outputs = model(states, return_strategy=True, return_strategy_tasks=True)
                    if len(outputs) == 3:
                        action_logits, strategy_logits, strategy_tasks_outputs = outputs
                    else:
                        action_logits, strategy_logits = outputs[:2]
                        strategy_tasks_outputs = None
                else:
                    # 只返回动作预测和策略分类
                    action_logits, strategy_logits = model(states, return_strategy=True)
                    strategy_tasks_outputs = None

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

                # 数据平衡权重已在函数开头定义

                for i in range(batch_size):
                    sample_logits = action_logits[i:i+1]
                    sample_actions = actions[i:i+1]

                    # 计算单个样本的损失
                    sample_loss = action_criterion(sample_logits, sample_actions)

                    # **阶段0方案D（改进损失函数）**: 添加预测数量惩罚
                    if use_improved_loss:
                        # 预测数量惩罚：惩罚预测过多或过少
                        sample_probs = torch.sigmoid(sample_logits)
                        pred_card_count = (sample_probs > 0.3).sum().item()  # 使用阈值0.3计算预测卡牌数
                        true_card_count = sample_actions.sum().item()

                        if pred_card_count > true_card_count:
                            # 预测过多：惩罚（权重大幅增加以更有效约束）
                            # **最终优化**: 从1.0增加到2.0，更严格约束预测过多问题
                            over_predict_penalty = (pred_card_count - true_card_count) / 27.0 * 3.0  # 归一化并加权（从2.0增加到3.0，超优化）
                            sample_loss = sample_loss + over_predict_penalty
                        elif pred_card_count < true_card_count:
                            # 预测过少：轻微惩罚
                            under_predict_penalty = (true_card_count - pred_card_count) / 27.0 * 0.05
                            sample_loss = sample_loss + under_predict_penalty

                        # **阶段1紧急修复：重新启用Top-K损失**
                        if use_top_k_loss:
                            # 基于真实卡牌数动态设置K值，进一步放宽约束以提升准确率
                            true_card_counts = sample_actions.sum(dim=1)  # (batch_size,)
                            # 放宽预测空间：K = max(真实卡牌数 + 3, 真实卡牌数 * 2.0)
                            k_values = torch.max(true_card_counts + 3, torch.ceil(true_card_counts * 2.0).long())
                            top_k_loss = compute_top_k_loss(sample_logits, sample_actions, k_values)
                            sample_loss = sample_loss + 0.3 * top_k_loss  # Top-K损失权重0.3（进一步降低）

                    # 应用牌型权重 + 数据平衡权重
                    weight = 1.0
                    if pattern_types is not None:
                        pattern_idx = pattern_types[i].item()
                        weight *= pattern_weights.get(pattern_idx, 1.0)

                    # 应用数据平衡权重（基于动作频率）
                    if sample_actions is not None:
                        # 找到样本中激活的动作索引
                        active_indices = (sample_actions.squeeze(0) > 0.5).nonzero(as_tuple=True)[0]
                        if len(active_indices) > 0:
                            # 对每个激活的索引应用频率权重
                            freq_weights = [action_frequency_weights.get(idx.item(), 1.0) for idx in active_indices]
                            avg_freq_weight = sum(freq_weights) / len(freq_weights)
                            weight *= avg_freq_weight

                        sample_loss = sample_loss * weight

                    sample_losses.append(sample_loss)
                
                # 平均所有样本的损失
                action_loss = torch.stack(sample_losses).mean()

                # **方案G-1：增强预测数量惩罚**
                # 计算每个样本的预测卡牌数和真实卡牌数
                action_probs = torch.sigmoid(action_logits)
                predicted_counts = (action_probs > 0.3).sum(dim=1).float()  # 使用0.3作为基准阈值
                true_counts = actions.sum(dim=1)

                # L1损失：惩罚预测数量偏差
                # **最终优化**: 从0.1增加到0.3，更严格约束预测数量
                # **超优化**: 从0.3增加到0.5，进一步严格约束预测数量偏差
                prediction_count_loss = torch.nn.functional.l1_loss(
                    predicted_counts, true_counts, reduction='mean'
                ) * 0.5  # 增强权重，更有效约束预测过多问题（从0.3增加到0.5）

                # 将预测数量惩罚添加到动作损失
                action_loss = action_loss + prediction_count_loss
                
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
                
                # **新增**：计算6个策略学习任务的损失
                strategy_tasks_loss = torch.tensor(0.0, device=device)
                # **新增**：策略一致性损失（鼓励动作预测和策略分类一致）
                strategy_consistency_loss = torch.tensor(0.0, device=device)
                
                if enable_strategy_tasks and strategy_tasks_outputs is not None and grouping_labels is not None:
                    # 任务1: 组牌策略分类（交叉熵）
                    grouping_loss = nn.CrossEntropyLoss()(strategy_tasks_outputs['grouping'], grouping_labels)
                    
                    # 任务2: 角色判断（交叉熵）
                    role_loss = nn.CrossEntropyLoss()(strategy_tasks_outputs['role'], role_labels)
                    
                    # 任务3: 牌力评估（回归，MSE）
                    power_loss = nn.MSELoss()(strategy_tasks_outputs['power'].squeeze(), power_scores)
                    
                    # 任务4: 保护/压制判断（交叉熵）
                    protect_suppress_loss = nn.CrossEntropyLoss()(strategy_tasks_outputs['protect_suppress'], protect_suppress_labels)
                    
                    # 任务5: 炸弹出炸时机（交叉熵）
                    bomb_timing_loss = nn.CrossEntropyLoss()(strategy_tasks_outputs['bomb_timing'], bomb_timing_labels)
                    
                    # 任务6: 红心配策略（交叉熵）
                    red_heart_loss = nn.CrossEntropyLoss()(strategy_tasks_outputs['red_heart'], red_heart_labels)
                    
                    # 任务7: 策略原因学习（交叉熵）- 新增：学习"为什么这样选择"
                    reason_loss = torch.tensor(0.0, device=device)
                    if reason_labels is not None and 'reason' in strategy_tasks_outputs:
                        # 忽略unknown类别（索引25）
                        valid_reason_mask = (reason_labels < 25)  # 排除unknown（索引25）
                        if valid_reason_mask.sum() > 0:
                            valid_reason_labels = reason_labels[valid_reason_mask]
                            valid_reason_logits = strategy_tasks_outputs['reason'][valid_reason_mask]
                            reason_loss = nn.CrossEntropyLoss()(valid_reason_logits, valid_reason_labels)
                    
                    # 总策略任务损失（平均每个任务权重约0.071，7个任务）
                    # **阶段6新增**：使用动态调整的策略任务权重
                    current_weight = current_strategy_tasks_weight if 'current_strategy_tasks_weight' in locals() else strategy_tasks_weight
                    strategy_tasks_loss = (grouping_loss + role_loss + power_loss * 0.1 + 
                                          protect_suppress_loss + bomb_timing_loss + red_heart_loss + reason_loss) / 7.0 * current_weight
                    
                    # **新增**：策略一致性损失 + 联合损失
                    # 1. 策略一致性损失：鼓励动作预测和策略分类在语义上一致
                    # 2. 联合损失：直接鼓励动作和策略同时正确
                    
                    # 计算动作预测的卡牌级别匹配率
                    action_probs_for_consistency = torch.sigmoid(action_logits)
                    action_probs_for_consistency = action_probs_for_consistency * 5.0
                    action_probs_for_consistency = torch.clamp(action_probs_for_consistency, 0, 1)
                    action_preds_for_consistency = (action_probs_for_consistency > 0.3).float()
                    
                    if action_preds_for_consistency.shape == actions.shape and strategy_labels is not None:
                        # 计算每个样本的卡牌级别匹配率
                        card_match_rates = (action_preds_for_consistency == actions).float().mean(dim=1)  # (batch_size,)
                        
                        # 策略一致性损失：如果动作预测基本正确（匹配率>0.9），策略分类也应该正确
                        action_correct_mask = (card_match_rates > 0.9)  # (batch_size,)
                        valid_strategy_mask = (strategy_labels < 7) & action_correct_mask
                        
                        if valid_strategy_mask.sum() > 0:
                            valid_strategy_labels_consistency = strategy_labels[valid_strategy_mask]
                            valid_strategy_logits_consistency = strategy_logits[valid_strategy_mask]
                            
                            # 策略分类应该正确
                            strategy_consistency_loss = nn.CrossEntropyLoss()(
                                valid_strategy_logits_consistency, valid_strategy_labels_consistency
                            ) * 0.2  # 权重0.2，鼓励一致性
                        
                        # **新增**：联合损失 - 直接鼓励动作和策略同时正确
                        # 使用卡牌匹配率作为权重，匹配率越高，策略分类损失权重越大
                        valid_strategy_mask_joint = (strategy_labels < 7)  # (batch_size,)
                        if valid_strategy_mask_joint.sum() > 0:
                            valid_strategy_labels_joint = strategy_labels[valid_strategy_mask_joint]
                            valid_strategy_logits_joint = strategy_logits[valid_strategy_mask_joint]
                            valid_card_match_rates = card_match_rates[valid_strategy_mask_joint]
                            
                            # 计算策略分类损失
                            strategy_ce_loss = nn.CrossEntropyLoss(reduction='none')(
                                valid_strategy_logits_joint, valid_strategy_labels_joint
                            )  # (valid_samples,)
                            
                            # 使用卡牌匹配率作为权重：匹配率越高，策略损失权重越大
                            # 这样鼓励模型在动作预测正确时，策略分类也要正确
                            weighted_strategy_loss = (strategy_ce_loss * (1.0 + valid_card_match_rates * 2.0)).mean()
                            
                            # 联合损失 = 加权策略损失（鼓励动作和策略同时正确）
                            joint_loss = weighted_strategy_loss * 0.3  # 权重0.3
                            strategy_consistency_loss = strategy_consistency_loss + joint_loss
                
                # **阶段5新增**: 计算高级策略学习损失
                strategy_pattern_loss = torch.tensor(0.0, device=device)
                opponent_model_loss = torch.tensor(0.0, device=device)
                dynamic_strategy_loss = torch.tensor(0.0, device=device)

                # 策略模式识别损失
                if enable_strategy_pattern and strategy_pattern_recognizer is not None and strategy_pattern_labels is not None:
                    pattern_logits, pattern_confidence = strategy_pattern_recognizer(states)
                    # 确保标签在有效范围内（0-7），策略模式有8种（0-7），unknown_strategy是7
                    # 使用ignore_index=7来忽略unknown_strategy，但需要确保标签值不超过7
                    # **修复**: 确保标签是long类型，并严格限制在0-7范围内
                    strategy_pattern_labels_long = strategy_pattern_labels.long()
                    strategy_pattern_labels_clamped = torch.clamp(strategy_pattern_labels_long, 0, 7)
                    strategy_pattern_criterion = nn.CrossEntropyLoss(ignore_index=7)
                    strategy_pattern_loss = strategy_pattern_criterion(pattern_logits, strategy_pattern_labels_clamped)

                # 对手建模损失（简化版：预测对手类型）
                if enable_opponent_modeling and opponent_model is not None:
                    # 这里需要对手的历史动作数据，暂时使用简化实现
                    # 在实际应用中，需要从游戏历史中提取对手动作序列
                    opponent_actions = actions  # 简化：使用当前动作作为对手动作的代理
                    opponent_results = opponent_model(states, opponent_actions.unsqueeze(1))

                    # 对手类型分类损失（假设我们知道对手类型，这里使用随机标签作为示例）
                    # 在实际应用中，需要真实的对手类型标签
                    dummy_opponent_labels = torch.randint(0, 5, (batch_size,), device=device)
                    opponent_criterion = nn.CrossEntropyLoss()
                    opponent_model_loss = opponent_criterion(opponent_results['opponent_type_logits'], dummy_opponent_labels)

                # 动态策略调整损失
                if enable_dynamic_strategy and dynamic_strategy_adjuster is not None:
                    strategy_results = dynamic_strategy_adjuster(states)
                    # 使用当前策略标签作为目标（简化实现）
                    # 动态策略调整器输出7种策略（0-6），需要排除unknown（索引7）
                    if strategy_labels is not None:
                        # 只计算非unknown样本的损失
                        # **修复**: 确保标签是long类型，并严格限制在0-6范围内
                        strategy_labels_long = strategy_labels.long()
                        valid_mask = (strategy_labels_long >= 0) & (strategy_labels_long < 7)  # 只接受0-6
                        if valid_mask.sum() > 0:
                            valid_strategy_labels = strategy_labels_long[valid_mask]
                            # **修复**: 再次确保标签值在有效范围内（0-6）
                            valid_strategy_labels = torch.clamp(valid_strategy_labels, 0, 6)
                            valid_switch_logits = strategy_results['switch_logits'][valid_mask]
                            dynamic_strategy_criterion = nn.CrossEntropyLoss()
                            dynamic_strategy_loss = dynamic_strategy_criterion(valid_switch_logits, valid_strategy_labels)
                        else:
                            dynamic_strategy_loss = torch.tensor(0.0, device=device)
                    else:
                        dynamic_strategy_loss = torch.tensor(0.0, device=device)
                
                # **阶段6新增**: 胜率导向损失函数（学习"什么有效"）
                # 基于策略有效性调整损失权重：策略有效性越高，损失权重越大（鼓励学习有效策略）
                win_rate_oriented_loss = torch.tensor(0.0, device=device)
                win_rate_weight = 0.3  # 胜率导向损失权重
                
                # 从状态中提取策略有效性（如果可用）
                # 策略有效性越高，说明这个决策越有效，应该给予更高的学习权重
                if hasattr(states, 'strategy_effectiveness'):
                    # 如果states包含策略有效性信息，使用它来调整损失权重
                    strategy_effectiveness = states.strategy_effectiveness  # (batch_size,)
                    # 归一化策略有效性到[0.5, 2.0]范围，作为损失权重
                    # 有效性越高，权重越大，鼓励模型学习有效策略
                    effectiveness_weights = 0.5 + 1.5 * strategy_effectiveness  # 归一化到[0.5, 2.0]
                    # 对动作损失和策略损失应用有效性权重
                    weighted_action_loss = action_loss * effectiveness_weights.mean()
                    weighted_strategy_loss = strategy_loss * effectiveness_weights.mean()
                    # 胜率导向损失 = 加权后的损失差异
                    win_rate_oriented_loss = (weighted_action_loss + weighted_strategy_loss) * win_rate_weight
                else:
                    # 如果没有策略有效性信息，使用策略效果分数（从state_dict中提取）
                    # 注意：这需要在数据加载时提取strategy_effectiveness
                    # 暂时使用策略一致性损失作为代理
                    win_rate_oriented_loss = strategy_consistency_loss * win_rate_weight * 0.5
                
                # **阶段5更新**: 组合损失（包含所有高级策略学习组件 + 7个策略任务 + 策略一致性损失 + 胜率导向损失）
                total_batch_loss = (current_action_weight * action_loss +
                                  current_strategy_weight * strategy_loss +
                                  strategy_pattern_weight * strategy_pattern_loss +
                                  opponent_model_weight * opponent_model_loss +
                                  dynamic_strategy_weight * dynamic_strategy_loss +
                                  strategy_tasks_loss +  # 新增：7个策略任务损失（包含策略原因学习）
                                  strategy_consistency_loss +  # 新增：策略一致性损失
                                  win_rate_oriented_loss)  # 新增：胜率导向损失（阶段6）
                
                total_action_loss += action_loss.item()
                total_strategy_loss += strategy_loss.item()
                total_strategy_pattern_loss += strategy_pattern_loss.item()
                total_opponent_model_loss += opponent_model_loss.item()
                total_dynamic_strategy_loss += dynamic_strategy_loss.item()
                # 新增：统计策略任务损失
                if enable_strategy_tasks and strategy_tasks_outputs is not None:
                    total_strategy_tasks_loss += strategy_tasks_loss.item()
                
                total_loss += total_batch_loss.item()
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
                    
                    # **阶段0方案D（改进损失函数）**: 添加预测数量惩罚
                    if use_improved_loss:
                        # 预测数量惩罚：惩罚预测过多或过少
                        sample_probs = torch.sigmoid(sample_logits)
                        pred_card_count = (sample_probs > 0.3).sum().item()  # 使用阈值0.3计算预测卡牌数
                        true_card_count = sample_actions.sum().item()

                        if pred_card_count > true_card_count:
                            # 预测过多：惩罚（权重大幅增加以更有效约束）
                            # **最终优化**: 从1.0增加到2.0，更严格约束预测过多问题
                            over_predict_penalty = (pred_card_count - true_card_count) / 27.0 * 3.0  # 归一化并加权（从2.0增加到3.0，超优化）
                            sample_loss = sample_loss + over_predict_penalty
                        elif pred_card_count < true_card_count:
                            # 预测过少：轻微惩罚
                            under_predict_penalty = (true_card_count - pred_card_count) / 27.0 * 0.05
                            sample_loss = sample_loss + under_predict_penalty

                        # **阶段1紧急修复：重新启用Top-K损失**
                        if use_top_k_loss:
                            # 基于真实卡牌数动态设置K值，进一步放宽约束以提升准确率
                            true_card_counts = sample_actions.sum(dim=1)  # (batch_size,)
                            # 放宽预测空间：K = max(真实卡牌数 + 3, 真实卡牌数 * 2.0)
                            k_values = torch.max(true_card_counts + 3, torch.ceil(true_card_counts * 2.0).long())
                            top_k_loss = compute_top_k_loss(sample_logits, sample_actions, k_values)
                            sample_loss = sample_loss + 0.3 * top_k_loss  # Top-K损失权重0.3（进一步降低）
                    
                    # 应用牌型权重 + 数据平衡权重
                    weight = 1.0
                    if pattern_types is not None:
                        pattern_idx = pattern_types[i].item()
                        weight *= pattern_weights.get(pattern_idx, 1.0)

                    # 应用数据平衡权重（基于动作频率）
                    if sample_actions is not None:
                        # 找到样本中激活的动作索引
                        active_indices = (sample_actions.squeeze(0) > 0.5).nonzero(as_tuple=True)[0]
                        if len(active_indices) > 0:
                            # 对每个激活的索引应用频率权重
                            freq_weights = [action_frequency_weights.get(idx.item(), 1.0) for idx in active_indices]
                            avg_freq_weight = sum(freq_weights) / len(freq_weights)
                            weight *= avg_freq_weight

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
                        
                        # **改进**：策略理解率（动作预测和策略分类都正确）
                        # 使用更宽松的匹配标准：卡牌级别匹配率>90% 且 策略分类正确
                        if total_samples > 0:
                            # 计算卡牌级别匹配率（更宽松的标准）
                            if action_predictions.shape == actions.shape:
                                card_match_rates = (action_predictions == actions).float().mean(dim=1)  # (batch_size,)
                                # 使用90%匹配率作为"动作基本正确"的标准（而不是100%完全匹配）
                                action_basically_correct = (card_match_rates > 0.9)  # (batch_size,)
                                
                                # 对于有效策略样本，检查动作和策略是否都正确
                                if valid_mask.dim() == 1 and action_basically_correct.dim() == 1:
                                    valid_action_correct = action_basically_correct[valid_mask]
                                    valid_strategy_correct = strategy_correct
                                    
                                    # 确保两个tensor都是1维且长度相同
                                    if valid_action_correct.shape == valid_strategy_correct.shape:
                                        both_correct = (valid_action_correct & valid_strategy_correct)
                                        strategy_understanding_count += both_correct.sum().item()
                                
                                # **保留**：完全匹配的策略理解率（用于对比）
                                # 原来的完全匹配标准（100%匹配）
                                if exact_match.dim() == 1 and valid_mask.dim() == 1:
                                    valid_exact_match = exact_match[valid_mask]
                                    if valid_exact_match.shape == valid_strategy_correct.shape:
                                        exact_both_correct = (valid_exact_match & valid_strategy_correct)
                                        # 可以单独统计，但不用于主要指标
            
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
            loss_parts = [f"Total: {avg_loss:.4f}", f"Action: {avg_action_loss:.4f}", f"Strategy: {avg_strategy_loss:.4f}"]

            if enable_strategy_pattern:
                avg_pattern_loss = total_strategy_pattern_loss / len(dataloader)
                loss_parts.append(f"Pattern: {avg_pattern_loss:.4f}")

            if enable_opponent_modeling:
                avg_opponent_loss = total_opponent_model_loss / len(dataloader)
                loss_parts.append(f"Opponent: {avg_opponent_loss:.4f}")

            if enable_dynamic_strategy:
                avg_dynamic_loss = total_dynamic_strategy_loss / len(dataloader)
                loss_parts.append(f"Dynamic: {avg_dynamic_loss:.4f}")

            loss_str = ", ".join(loss_parts)
            print(f"  Loss - {loss_str}, LR: {current_lr:.6f}")
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
        
        # **阶段3任务2.5方案B + 阶段6增强**: 动态损失权重调整（基于任务准确率和游戏表现）
        if use_dynamic_weight and enable_strategy_head and (epoch + 1) % weight_adjust_interval == 0 and epoch > 0:
            # 根据任务准确率和策略有效性动态调整权重
            # 如果动作预测准确率低，增加动作预测权重
            # 如果策略分类准确率高，可以适当降低策略分类权重
            # **阶段6新增**：根据策略有效性调整策略任务权重
            
            # 获取最近N个epoch的平均准确率（用于稳定性）
            lookback = min(weight_adjust_interval, len(training_history['action_exact_accuracy']))
            if lookback > 0:
                recent_action_acc = np.mean(training_history['action_exact_accuracy'][-lookback:])
                recent_strategy_acc = np.mean(training_history['strategy_accuracy'][-lookback:]) if len(training_history['strategy_accuracy']) >= lookback else strategy_accuracy
                
                # **阶段6新增**：获取策略理解率（如果可用）
                recent_strategy_understanding = 0.0
                if 'strategy_understanding_rate' in training_history and len(training_history['strategy_understanding_rate']) >= lookback:
                    recent_strategy_understanding = np.mean(training_history['strategy_understanding_rate'][-lookback:])
                
                # 调整策略：
                # 1. 如果动作预测准确率 < 20%，增加动作预测权重（最多增加到2.0倍）
                # 2. 如果策略分类准确率 > 95%，可以适当降低策略分类权重（最多降低到0.1）
                # 3. **阶段6新增**：如果策略理解率 < 30%，增加策略任务权重
                # 4. 权重调整幅度：每次调整10%
                
                old_action_weight = current_action_weight
                old_strategy_weight = current_strategy_weight
                old_strategy_tasks_weight = current_strategy_tasks_weight
                
                if recent_action_acc < 0.20:  # 动作预测准确率低
                    # 增加动作预测权重
                    current_action_weight = min(current_action_weight * 1.1, action_loss_weight * 2.0)
                    print(f"  [动态权重调整] 动作预测准确率低({recent_action_acc:.2%})，增加动作预测权重: {old_action_weight:.3f} → {current_action_weight:.3f}")
                
                if recent_strategy_acc > 0.95:  # 策略分类准确率高
                    # 可以适当降低策略分类权重
                    current_strategy_weight = max(current_strategy_weight * 0.9, strategy_loss_weight * 0.1)
                    print(f"  [动态权重调整] 策略分类准确率高({recent_strategy_acc:.2%})，降低策略分类权重: {old_strategy_weight:.3f} → {current_strategy_weight:.3f}")
                
                # **阶段6新增**：根据策略理解率调整策略任务权重
                if recent_strategy_understanding > 0 and recent_strategy_understanding < 0.30:
                    # 策略理解率低，增加策略任务权重（鼓励学习策略原理）
                    current_strategy_tasks_weight = min(current_strategy_tasks_weight * 1.15, 1.0)  # 最多增加到1.0
                    print(f"  [动态权重调整] 策略理解率低({recent_strategy_understanding:.2%})，增加策略任务权重: {old_strategy_tasks_weight:.3f} → {current_strategy_tasks_weight:.3f}")
                elif recent_strategy_understanding > 0.60:
                    # 策略理解率高，可以适当降低策略任务权重
                    current_strategy_tasks_weight = max(current_strategy_tasks_weight * 0.95, 0.2)  # 最少保持0.2
                    print(f"  [动态权重调整] 策略理解率高({recent_strategy_understanding:.2%})，降低策略任务权重: {old_strategy_tasks_weight:.3f} → {current_strategy_tasks_weight:.3f}")
                
                # 如果权重发生变化，打印当前权重
                if abs(current_action_weight - old_action_weight) > 0.001 or abs(current_strategy_weight - old_strategy_weight) > 0.001 or abs(current_strategy_tasks_weight - old_strategy_tasks_weight) > 0.001:
                    print(f"  [动态权重调整] 当前权重: α={current_action_weight:.3f}, β={current_strategy_weight:.3f}, 策略任务={current_strategy_tasks_weight:.3f}")
        
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
    
    # 固定随机种子，确保训练可复现
    seed = 42
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    
    # 阶段1紧急修复：完整实施阶段1方案（方案G-1 + 方案G-2 + 方案I-1）
    # 训练参数：
    # - 数据量：全部数据（33,023个样本）
    # - Epochs：50（快速测试修复效果）
    # - Dropout：0.2（保持与方案C一致）
    # - pos_weight：1.5（保持与方案C一致）
    # - 学习率：0.0003
    # - 批次大小：64
    # - 课程学习：启用，4个阶段
    # - 紧急修复（阶段1完整实施）：
    #   - ✅ 方案G-1：预测数量惩罚权重：从0.2增加到1.0
    #   - ✅ 方案G-2：重新启用Top-K损失（权重0.5）
    #   - ✅ 方案I-1：学习率调度：从StepLR改为CosineAnnealingLR
    # 目标：验证紧急修复是否能快速提升完全匹配准确率，从0%提升到5-10%
    train_bc(epochs=200, max_samples=None, use_dynamic_weight=False, use_separated_features=True, lr=0.0005,
             use_curriculum_learning=True, curriculum_stages=4, dropout_rate=0.2,
             enable_strategy_head=False)  # 阶段0只训练动作预测，不启用策略分类头
