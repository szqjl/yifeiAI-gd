"""
简化版数据加载器 for Stage 7
直接使用ReplayParser处理原始游戏记录
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys
import os

# 添加路径以导入ReplayParser
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'knowledge_processor'))

logger = logging.getLogger(__name__)


class SimpleGuandanDataset(Dataset):
    """
    简化版掼蛋数据集
    直接处理原始游戏记录
    """
    
    def __init__(self, data_dir: str, max_samples: Optional[int] = None):
        self.data_dir = Path(data_dir)
        self.samples = self._load_and_convert_samples(max_samples)
        
        # 策略类型映射
        self.strategy_mapping = {
            'group': 0,
            'follow': 1, 
            'control': 2,
            'discard': 3,
            'unknown': 4,
            'suppress': 5,
            'protect': 6,
            'bomb': 7
        }
        
        logger.info(f"加载了 {len(self.samples)} 个训练样本")
    
    def _load_and_convert_samples(self, max_samples: Optional[int]) -> List[Dict]:
        """加载并转换训练样本（优化：优先使用胜利记录）"""
        try:
            from replay_parser import ReplayParser
            
            # 创建ReplayParser
            parser = ReplayParser(str(self.data_dir))
            
            # 加载原始游戏记录（分胜利和失败两类）
            winning_replays = []
            losing_replays = []
            json_files = list(self.data_dir.glob("*.json"))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 检查是否是原始游戏记录格式
                    if 'player_id' in data and 'actions' in data:
                        # 判断是否胜利
                        is_win = self._is_winning_record(data)
                        if is_win:
                            winning_replays.append(data)
                        else:
                            losing_replays.append(data)
                            
                except Exception as e:
                    logger.debug(f"跳过文件 {json_file}: {e}")
                    continue
            
            # 优先使用胜利记录（70%胜利记录 + 30%失败记录）
            total_needed = max_samples // 20 if max_samples else len(winning_replays) + len(losing_replays)
            win_count = min(int(total_needed * 0.7), len(winning_replays))
            loss_count = min(total_needed - win_count, len(losing_replays))
            
            replays = winning_replays[:win_count] + losing_replays[:loss_count]
            
            logger.info(f"加载了 {len(replays)} 个游戏记录（胜利: {win_count}, 失败: {loss_count}）")
            
            # 提取训练数据
            training_data = parser.extract_training_data(replays)
            logger.info(f"提取了 {len(training_data)} 个原始训练样本")
            
            # 转换为向量格式
            samples = []
            skipped_empty = 0
            for state_dict, action_cards in training_data:
                try:
                    # 跳过空action_cards的样本（这些是PASS动作，对训练帮助不大）
                    if not action_cards or len(action_cards) == 0:
                        skipped_empty += 1
                        continue
                    
                    state_vec = self._state_to_vector(state_dict)
                    action_vec = self._action_to_vector(action_cards)
                    
                    # 验证action_vec不为全0
                    if sum(action_vec) == 0:
                        skipped_empty += 1
                        continue
                    
                    sample = {
                        'state_vec': state_vec,
                        'action_vec': action_vec,
                        'strategy_type': state_dict.get('strategy_type', 'unknown')
                    }
                    
                    samples.append(sample)
                    
                    if max_samples and len(samples) >= max_samples:
                        break
                        
                except Exception as e:
                    logger.debug(f"转换样本失败: {e}")
                    continue
            
            if skipped_empty > 0:
                logger.info(f"跳过了 {skipped_empty} 个空action_cards样本（PASS动作）")
            
            logger.info(f"成功转换了 {len(samples)} 个训练样本")
            return samples
            
        except ImportError as e:
            logger.error(f"无法导入ReplayParser: {e}")
            return []
        except Exception as e:
            logger.error(f"加载数据时出错: {e}")
            return []
    
    def _is_winning_record(self, record: Dict) -> bool:
        """判断记录是否为胜利记录"""
        player_id = record.get('player_id', 0)
        
        # 方法1: 从game_info获取
        game_info = record.get('game_info', {})
        game_result = game_info.get('game_result', '')
        if game_result == 'win':
            return True
        elif game_result == 'loss':
            return False
        
        # 方法2: 从result.victoryNum获取
        result = record.get('result', {})
        victory_num = result.get('victoryNum', [])
        if victory_num and len(victory_num) > player_id:
            return victory_num[player_id] > 0
        
        # 默认返回False（保守策略）
        return False
    
    def _state_to_vector(self, state_dict: Dict) -> List[float]:
        """将状态字典转换为512维向量"""
        vector = [0.0] * 512
        
        # 手牌信息（前54维）
        hand_cards = state_dict.get('hand', [])
        card_mapping = self._get_card_mapping()
        
        for card in hand_cards:
            if card in card_mapping:
                idx = card_mapping[card]
                if idx < 54:
                    vector[idx] = 1.0
        
        # 游戏阶段（54-56维）
        game_phase = state_dict.get('game_phase', 1)
        if 54 + game_phase < 57 and game_phase >= 0:
            vector[54 + game_phase] = 1.0
        
        # 当前级牌（57-69维）
        cur_rank = state_dict.get('cur_rank', '2')
        rank_mapping = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
        if cur_rank in rank_mapping:
            idx = 57 + rank_mapping[cur_rank]
            if idx < 70:
                vector[idx] = 1.0
        
        # 玩家剩余牌数（70-73维）
        player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
        for i, count in enumerate(player_rest_cards[:4]):
            if 70 + i < 74:
                vector[70 + i] = min(count / 27.0, 1.0)  # 归一化
        
        return vector
    
    def _action_to_vector(self, action_cards: List[str]) -> List[int]:
        """将动作卡牌转换为512维向量"""
        vector = [0] * 512
        
        card_mapping = self._get_card_mapping()
        
        for card in action_cards:
            if card in card_mapping:
                idx = card_mapping[card]
                if idx < 512:
                    vector[idx] = 1
        
        return vector
    
    def _get_card_mapping(self) -> Dict[str, int]:
        """获取卡牌到索引的映射"""
        cards = []
        
        # 标准52张牌
        suits = ['C', 'D', 'H', 'S']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
        
        for suit in suits:
            for rank in ranks:
                cards.append(suit + rank)
        
        # 大小王
        cards.extend(['HR', 'BR'])
        
        return {card: idx for idx, card in enumerate(cards)}
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        
        # 获取数据
        state_vec = sample['state_vec']
        action_vec = sample['action_vec']
        strategy_type = sample['strategy_type']
        
        # 映射策略类型
        strategy_idx = self.strategy_mapping.get(strategy_type, self.strategy_mapping['unknown'])
        
        # 转换为tensor
        state_tensor = torch.tensor(state_vec, dtype=torch.float32)
        action_tensor = torch.tensor(action_vec, dtype=torch.float32)
        strategy_tensor = torch.tensor(strategy_idx, dtype=torch.long)
        
        return state_tensor, action_tensor, strategy_tensor


def create_simple_dataloader(
    data_dir: str = "game_records",
    batch_size: int = 32,
    max_samples: Optional[int] = None,
    shuffle: bool = True,
    num_workers: int = 0
) -> DataLoader:
    """
    创建简化版数据加载器
    """
    
    # 创建数据集
    dataset = SimpleGuandanDataset(
        data_dir=data_dir,
        max_samples=max_samples
    )
    
    if len(dataset) == 0:
        raise ValueError("数据集为空，无法创建数据加载器")
    
    # 创建数据加载器
    dataloader = DataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers
    )
    
    return dataloader


if __name__ == "__main__":
    # 测试简化版数据加载器
    logging.basicConfig(level=logging.INFO)
    
    try:
        dataloader = create_simple_dataloader(
            data_dir="../../game_records",
            batch_size=16,
            max_samples=100,
            shuffle=True
        )
        
        logger.info(f"数据加载器创建成功，批次数: {len(dataloader)}")
        
        # 测试一个批次
        for batch_idx, (state_vec, action_vec, strategy_type) in enumerate(dataloader):
            logger.info(f"批次 {batch_idx + 1}:")
            logger.info(f"  状态向量形状: {state_vec.shape}")
            logger.info(f"  动作向量形状: {action_vec.shape}")
            logger.info(f"  策略类型形状: {strategy_type.shape}")
            logger.info(f"  策略类型分布: {torch.bincount(strategy_type)}")
            
            if batch_idx >= 2:  # 只测试前3个批次
                break
        
        logger.info("简化版数据加载器测试完成")
        
    except Exception as e:
        logger.error(f"数据加载器测试失败: {e}")
        raise