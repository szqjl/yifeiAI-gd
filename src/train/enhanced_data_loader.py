"""
增强的数据加载器 for Stage 7
支持更好的数据预处理和特征工程
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import random
import sys
import os

logger = logging.getLogger(__name__)


class EnhancedGuandanDataset(Dataset):
    """
    增强的掼蛋数据集
    
    改进点:
    1. 更好的特征标准化
    2. 数据增强技术
    3. 平衡采样
    4. 异常值处理
    """
    
    def __init__(self, data_dir: str, max_samples: Optional[int] = None, 
                 enable_augmentation: bool = True, balance_strategy: bool = True):
        self.data_dir = Path(data_dir)
        self.enable_augmentation = enable_augmentation
        self.balance_strategy = balance_strategy
        
        # 加载数据
        self.samples = self._load_samples(max_samples)
        
        # 计算统计信息用于标准化
        self._compute_statistics()
        
        # 策略类型映射
        self.strategy_mapping = {
            'group': 0,
            'follow': 1, 
            'control': 2,
            'discard': 3,
            'unknown': 4
        }
        
        logger.info(f"加载了 {len(self.samples)} 个训练样本")
        if self.enable_augmentation:
            logger.info("数据增强已启用")
        if self.balance_strategy:
            logger.info("策略平衡采样已启用")
    
    def _load_samples(self, max_samples: Optional[int]) -> List[Dict]:
        """加载训练样本"""
        samples = []
        
        # 遍历所有JSON文件
        json_files = list(self.data_dir.glob("*.json"))
        
        if not json_files:
            raise ValueError(f"在 {self.data_dir} 中未找到JSON文件")
        
        # 首先尝试加载已处理的训练数据
        processed_samples = self._load_processed_samples(json_files, max_samples)
        if processed_samples:
            logger.info(f"加载了 {len(processed_samples)} 个已处理的训练样本")
            return processed_samples
        
        # 如果没有已处理的数据，使用ReplayParser处理原始游戏记录
        logger.info("未找到已处理的训练数据，开始处理原始游戏记录...")
        raw_samples = self._load_raw_game_records(json_files, max_samples)
        
        if not raw_samples:
            raise ValueError("未找到有效的训练样本")
        
        # 先检查几个样本的有效性
        logger.info("检查前几个样本的有效性...")
        for i, sample in enumerate(raw_samples[:5]):
            is_valid = self._is_valid_sample(sample)
            logger.info(f"样本 {i+1}: 有效={is_valid}, 键={list(sample.keys())}")
            if not is_valid:
                # 详细检查失败原因
                if 'state_vec' not in sample:
                    logger.info(f"  缺少 state_vec")
                elif not isinstance(sample['state_vec'], list):
                    logger.info(f"  state_vec 不是列表: {type(sample['state_vec'])}")
                elif len(sample['state_vec']) != 512:
                    logger.info(f"  state_vec 长度错误: {len(sample['state_vec'])}")
                
                if 'action_vec' not in sample:
                    logger.info(f"  缺少 action_vec")
                elif not isinstance(sample['action_vec'], list):
                    logger.info(f"  action_vec 不是列表: {type(sample['action_vec'])}")
                elif len(sample['action_vec']) != 512:
                    logger.info(f"  action_vec 长度错误: {len(sample['action_vec'])}")
        
        # 数据清洗和过滤
        samples = self._clean_samples(raw_samples)
        
        return samples
    
    def _load_processed_samples(self, json_files: List[Path], max_samples: Optional[int]) -> List[Dict]:
        """加载已处理的训练样本"""
        samples = []
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否是已处理的训练数据格式
                if 'training_data' in data:
                    for sample in data['training_data']:
                        if self._is_valid_sample(sample):
                            samples.append(sample)
                            
                            if max_samples and len(samples) >= max_samples:
                                return samples
                
            except Exception as e:
                logger.debug(f"跳过文件 {json_file}: {e}")
                continue
        
        return samples
    
    def _load_raw_game_records(self, json_files: List[Path], max_samples: Optional[int]) -> List[Dict]:
        """使用ReplayParser处理原始游戏记录"""
        try:
            # 导入ReplayParser
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'knowledge_processor'))
            from replay_parser import ReplayParser
            
            # 创建ReplayParser实例
            parser = ReplayParser(str(self.data_dir))
            
            # 加载原始游戏记录
            replays = []
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 检查是否是原始游戏记录格式
                    if 'player_id' in data and 'actions' in data:
                        replays.append(data)
                        
                        if max_samples and len(replays) >= max_samples // 10:  # 每个replay可能产生多个样本
                            break
                            
                except Exception as e:
                    logger.debug(f"跳过文件 {json_file}: {e}")
                    continue
            
            if not replays:
                logger.warning("未找到原始游戏记录")
                return []
            
            logger.info(f"找到 {len(replays)} 个原始游戏记录，开始提取训练数据...")
            
            # 提取训练数据
            training_data = parser.extract_training_data(replays)
            
            # 转换为所需格式
            samples = []
            conversion_errors = 0
            
            for i, (state_dict, action_cards) in enumerate(training_data):
                try:
                    # 转换为向量格式
                    state_vec, action_vec = self._convert_to_vectors(state_dict, action_cards)
                    
                    if state_vec is not None and action_vec is not None:
                        sample = {
                            'state_vec': state_vec,
                            'action_vec': action_vec,
                            'strategy_type': state_dict.get('strategy_type', 'unknown')
                        }
                        samples.append(sample)
                        
                        # 记录前几个样本的信息
                        if len(samples) <= 3:
                            logger.info(f"样本 {len(samples)}: 状态向量长度={len(state_vec)}, 动作向量长度={len(action_vec)}, 动作数量={sum(action_vec)}, 策略类型={sample['strategy_type']}")
                        
                        if max_samples and len(samples) >= max_samples:
                            break
                    else:
                        conversion_errors += 1
                        if conversion_errors <= 5:  # 只记录前5个错误
                            logger.debug(f"转换失败 {conversion_errors}: state_vec={state_vec is not None}, action_vec={action_vec is not None}")
                            
                except Exception as e:
                    conversion_errors += 1
                    if conversion_errors <= 5:
                        logger.debug(f"转换样本时出错 {conversion_errors}: {e}")
                    continue
            
            if conversion_errors > 0:
                logger.info(f"转换过程中有 {conversion_errors} 个样本失败")
            
            logger.info(f"成功转换了 {len(samples)} 个训练样本")
            return samples
            
        except ImportError as e:
            logger.error(f"无法导入ReplayParser: {e}")
            return []
        except Exception as e:
            logger.error(f"处理原始游戏记录时出错: {e}")
            return []
    
    def _convert_to_vectors(self, state_dict: Dict, action_cards: List[str]) -> Tuple[Optional[List[float]], Optional[List[int]]]:
        """将状态字典和动作卡牌转换为向量格式"""
        try:
            # 导入状态编码器
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'knowledge_processor'))
            from state_encoder import StateEncoder
            
            # 创建状态编码器
            encoder = StateEncoder()
            
            # 编码状态向量
            state_vec = encoder.encode_state(state_dict)
            
            # 编码动作向量
            action_vec = encoder.encode_action(action_cards)
            
            return state_vec, action_vec
            
        except ImportError:
            # 如果无法导入状态编码器，使用简化版本
            return self._simple_convert_to_vectors(state_dict, action_cards)
        except Exception as e:
            logger.debug(f"向量转换出错: {e}")
            return None, None
    
    def _simple_convert_to_vectors(self, state_dict: Dict, action_cards: List[str]) -> Tuple[List[float], List[int]]:
        """简化版向量转换（当无法使用完整编码器时）"""
        # 创建512维状态向量（简化版）
        state_vec = [0.0] * 512
        
        # 手牌信息（前54维，每张牌一个位置）
        hand_cards = state_dict.get('hand', [])
        card_to_index = self._get_card_mapping()
        
        for card in hand_cards:
            if card in card_to_index:
                idx = card_to_index[card]
                if idx < 54:
                    state_vec[idx] = 1.0
        
        # 游戏阶段（54-56维）
        game_phase = state_dict.get('game_phase', 1)
        if game_phase < 3:
            state_vec[54 + game_phase] = 1.0
        
        # 当前级牌（57-69维，2-A + 小王大王）
        cur_rank = state_dict.get('cur_rank', '2')
        rank_mapping = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
        if cur_rank in rank_mapping:
            state_vec[57 + rank_mapping[cur_rank]] = 1.0
        
        # 玩家剩余牌数（70-73维）
        player_rest_cards = state_dict.get('player_rest_cards', [27, 27, 27, 27])
        for i, count in enumerate(player_rest_cards[:4]):
            if i < 4:
                state_vec[70 + i] = min(count / 27.0, 1.0)  # 归一化到0-1
        
        # 创建512维动作向量
        action_vec = [0] * 512
        
        # 标记出牌的卡牌
        for card in action_cards:
            if card in card_to_index:
                idx = card_to_index[card]
                if idx < 512:
                    action_vec[idx] = 1
        
        return state_vec, action_vec
    
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
        cards.extend(['HR', 'BR'])  # 红桃配（小王）、黑桃配（大王）
        
        return {card: idx for idx, card in enumerate(cards)}
    
    def _is_valid_sample(self, sample: Dict) -> bool:
        """检查样本是否有效"""
        required_keys = ['state_vec', 'action_vec', 'strategy_type']
        
        for key in required_keys:
            if key not in sample:
                logger.debug(f"样本缺少必需键: {key}")
                return False
        
        # 检查向量维度
        state_vec = sample['state_vec']
        action_vec = sample['action_vec']
        
        if not isinstance(state_vec, list) or len(state_vec) != 512:
            logger.debug(f"状态向量维度错误: {type(state_vec)}, 长度: {len(state_vec) if isinstance(state_vec, list) else 'N/A'}")
            return False
        
        if not isinstance(action_vec, list) or len(action_vec) != 512:
            logger.debug(f"动作向量维度错误: {type(action_vec)}, 长度: {len(action_vec) if isinstance(action_vec, list) else 'N/A'}")
            return False
        
        # 检查数值有效性
        try:
            state_array = np.array(state_vec, dtype=np.float32)
            action_array = np.array(action_vec, dtype=np.float32)
            
            # 检查是否有NaN或无穷大
            if np.any(np.isnan(state_array)) or np.any(np.isinf(state_array)):
                logger.debug("状态向量包含NaN或无穷大")
                return False
            
            if np.any(np.isnan(action_array)) or np.any(np.isinf(action_array)):
                logger.debug("动作向量包含NaN或无穷大")
                return False
            
            # 检查action_vec是否为二进制
            if not np.all(np.isin(action_array, [0, 1])):
                logger.debug(f"动作向量不是二进制: 唯一值 = {np.unique(action_array)}")
                return False
            
            # 允许PASS动作（动作向量全为0）
            # 这是合法的游戏动作，不应该被过滤掉
            
            return True
            
        except (ValueError, TypeError) as e:
            logger.debug(f"数值验证出错: {e}")
            return False
    
    def _clean_samples(self, samples: List[Dict]) -> List[Dict]:
        """清洗样本数据"""
        cleaned_samples = []
        filter_stats = {'total': 0, 'strategy_invalid': 0, 'action_invalid': 0, 'pass_actions': 0, 'valid': 0}
        
        for i, sample in enumerate(samples):
            filter_stats['total'] += 1
            
            try:
                # 标准化策略类型
                strategy_type = sample.get('strategy_type', 'unknown')
                original_strategy = strategy_type
                if strategy_type not in self.strategy_mapping:
                    strategy_type = 'unknown'
                    filter_stats['strategy_invalid'] += 1
                
                sample['strategy_type'] = strategy_type
                
                # 检查动作向量的合理性
                action_vec = np.array(sample['action_vec'])
                action_count = np.sum(action_vec)
                
                # 记录PASS动作
                if action_count == 0:
                    filter_stats['pass_actions'] += 1
                
                # 详细记录前几个样本的处理过程
                if i < 5:
                    logger.info(f"清洗样本 {i+1}: 原策略={original_strategy}, 新策略={strategy_type}, 动作数量={action_count}")
                
                # 调整过滤条件：允许PASS动作（action_count=0）和正常出牌动作
                if 0 <= action_count <= 20:  # 包括PASS动作（0张牌）和正常出牌（1-20张牌）
                    # 再次验证样本有效性
                    is_valid = self._is_valid_sample(sample)
                    if i < 5:
                        logger.info(f"  样本 {i+1} 验证结果: {is_valid}")
                    
                    if is_valid:
                        cleaned_samples.append(sample)
                        filter_stats['valid'] += 1
                    else:
                        logger.debug(f"样本在清洗阶段验证失败: action_count={action_count}")
                        filter_stats['action_invalid'] += 1
                else:
                    filter_stats['action_invalid'] += 1
                    logger.debug(f"动作数量超出范围: {action_count}")
                
            except Exception as e:
                logger.debug(f"清洗样本时出错: {e}")
                continue
        
        logger.info(f"数据清洗统计: 总样本={filter_stats['total']}, "
                   f"PASS动作={filter_stats['pass_actions']}, "
                   f"策略无效={filter_stats['strategy_invalid']}, "
                   f"动作无效={filter_stats['action_invalid']}, "
                   f"有效样本={filter_stats['valid']}")
        
        return cleaned_samples
    
    def _compute_statistics(self):
        """计算数据统计信息用于标准化"""
        if not self.samples:
            return
        
        # 收集所有state_vec
        state_vecs = []
        for sample in self.samples:
            state_vecs.append(sample['state_vec'])
        
        state_matrix = np.array(state_vecs, dtype=np.float32)
        
        # 计算均值和标准差
        self.state_mean = np.mean(state_matrix, axis=0)
        self.state_std = np.std(state_matrix, axis=0)
        
        # 避免除零
        self.state_std = np.where(self.state_std < 1e-8, 1.0, self.state_std)
        
        logger.info("数据统计信息计算完成")
    
    def _normalize_state(self, state_vec: np.ndarray) -> np.ndarray:
        """标准化状态向量"""
        return (state_vec - self.state_mean) / self.state_std
    
    def _augment_sample(self, state_vec: np.ndarray, action_vec: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """数据增强"""
        if not self.enable_augmentation:
            return state_vec, action_vec
        
        # 随机噪声增强
        if random.random() < 0.3:
            noise_scale = 0.01
            noise = np.random.normal(0, noise_scale, state_vec.shape)
            state_vec = state_vec + noise
        
        # 特征dropout（随机将一些特征置零）
        if random.random() < 0.2:
            dropout_mask = np.random.random(state_vec.shape) > 0.05
            state_vec = state_vec * dropout_mask
        
        return state_vec, action_vec
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[idx]
        
        # 获取数据
        state_vec = np.array(sample['state_vec'], dtype=np.float32)
        action_vec = np.array(sample['action_vec'], dtype=np.float32)
        strategy_type = self.strategy_mapping[sample['strategy_type']]
        
        # 标准化状态向量
        state_vec = self._normalize_state(state_vec)
        
        # 数据增强
        state_vec, action_vec = self._augment_sample(state_vec, action_vec)
        
        # 转换为tensor
        state_tensor = torch.tensor(state_vec, dtype=torch.float32)
        action_tensor = torch.tensor(action_vec, dtype=torch.float32)
        strategy_tensor = torch.tensor(strategy_type, dtype=torch.long)
        
        return state_tensor, action_tensor, strategy_tensor


class BalancedDataLoader:
    """
    平衡数据加载器
    确保不同策略类型的样本均衡分布
    """
    
    def __init__(self, dataset: EnhancedGuandanDataset, batch_size: int = 32, 
                 shuffle: bool = True, num_workers: int = 0):
        self.dataset = dataset
        self.batch_size = batch_size
        self.shuffle = shuffle
        self.num_workers = num_workers
        
        # 按策略类型分组样本
        self._group_samples_by_strategy()
        
        # 创建数据加载器
        self.dataloader = self._create_balanced_dataloader()
    
    def _group_samples_by_strategy(self):
        """按策略类型分组样本"""
        self.strategy_groups = {}
        
        for idx, sample in enumerate(self.dataset.samples):
            strategy = sample['strategy_type']
            if strategy not in self.strategy_groups:
                self.strategy_groups[strategy] = []
            self.strategy_groups[strategy].append(idx)
        
        # 打印分布信息
        logger.info("策略类型分布:")
        for strategy, indices in self.strategy_groups.items():
            logger.info(f"  {strategy}: {len(indices)} 样本")
    
    def _create_balanced_dataloader(self):
        """创建平衡的数据加载器"""
        if not self.dataset.balance_strategy:
            # 不使用平衡采样，直接返回标准DataLoader
            return DataLoader(
                self.dataset, 
                batch_size=self.batch_size,
                shuffle=self.shuffle,
                num_workers=self.num_workers
            )
        
        # 使用加权随机采样器
        sample_weights = self._calculate_sample_weights()
        sampler = torch.utils.data.WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(self.dataset),
            replacement=True
        )
        
        return DataLoader(
            self.dataset,
            batch_size=self.batch_size,
            sampler=sampler,
            num_workers=self.num_workers
        )
    
    def _calculate_sample_weights(self) -> List[float]:
        """计算样本权重以实现平衡采样"""
        weights = [0.0] * len(self.dataset)
        
        # 计算每个策略类型的权重（反比于样本数量）
        strategy_weights = {}
        total_samples = len(self.dataset)
        
        for strategy, indices in self.strategy_groups.items():
            strategy_count = len(indices)
            strategy_weights[strategy] = total_samples / (len(self.strategy_groups) * strategy_count)
        
        # 为每个样本分配权重
        for idx, sample in enumerate(self.dataset.samples):
            strategy = sample['strategy_type']
            weights[idx] = strategy_weights[strategy]
        
        return weights
    
    def __iter__(self):
        return iter(self.dataloader)
    
    def __len__(self):
        return len(self.dataloader)


def create_enhanced_dataloader(
    data_dir: str = "game_records",
    batch_size: int = 32,
    max_samples: Optional[int] = None,
    enable_augmentation: bool = True,
    balance_strategy: bool = True,
    shuffle: bool = True,
    num_workers: int = 0
) -> BalancedDataLoader:
    """
    创建增强的数据加载器
    
    Args:
        data_dir: 数据目录
        batch_size: 批次大小
        max_samples: 最大样本数（None表示使用全部）
        enable_augmentation: 是否启用数据增强
        balance_strategy: 是否启用策略平衡
        shuffle: 是否打乱数据
        num_workers: 数据加载进程数
    
    Returns:
        BalancedDataLoader实例
    """
    
    # 创建数据集
    dataset = EnhancedGuandanDataset(
        data_dir=data_dir,
        max_samples=max_samples,
        enable_augmentation=enable_augmentation,
        balance_strategy=balance_strategy
    )
    
    # 创建数据加载器
    dataloader = BalancedDataLoader(
        dataset=dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers
    )
    
    return dataloader


if __name__ == "__main__":
    # 测试数据加载器
    logging.basicConfig(level=logging.INFO)
    
    try:
        dataloader = create_enhanced_dataloader(
            data_dir="../../game_records",
            batch_size=16,
            max_samples=1000,
            enable_augmentation=True,
            balance_strategy=True
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
        
        logger.info("数据加载器测试完成")
        
    except Exception as e:
        logger.error(f"数据加载器测试失败: {e}")
        raise