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
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 提取训练样本
                if 'training_data' in data:
                    for sample in data['training_data']:
                        if self._is_valid_sample(sample):
                            samples.append(sample)
                            
                            if max_samples and len(samples) >= max_samples:
                                break
                
                if max_samples and len(samples) >= max_samples:
                    break
                    
            except Exception as e:
                logger.warning(f"跳过文件 {json_file}: {e}")
                continue
        
        if not samples:
            raise ValueError("未找到有效的训练样本")
        
        # 数据清洗和过滤
        samples = self._clean_samples(samples)
        
        return samples
    
    def _is_valid_sample(self, sample: Dict) -> bool:
        """检查样本是否有效"""
        required_keys = ['state_vec', 'action_vec', 'strategy_type']
        
        for key in required_keys:
            if key not in sample:
                return False
        
        # 检查向量维度
        state_vec = sample['state_vec']
        action_vec = sample['action_vec']
        
        if not isinstance(state_vec, list) or len(state_vec) != 512:
            return False
        
        if not isinstance(action_vec, list) or len(action_vec) != 512:
            return False
        
        # 检查数值有效性
        try:
            state_array = np.array(state_vec, dtype=np.float32)
            action_array = np.array(action_vec, dtype=np.float32)
            
            # 检查是否有NaN或无穷大
            if np.any(np.isnan(state_array)) or np.any(np.isinf(state_array)):
                return False
            
            if np.any(np.isnan(action_array)) or np.any(np.isinf(action_array)):
                return False
            
            # 检查action_vec是否为二进制
            if not np.all(np.isin(action_array, [0, 1])):
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    def _clean_samples(self, samples: List[Dict]) -> List[Dict]:
        """清洗样本数据"""
        cleaned_samples = []
        
        for sample in samples:
            try:
                # 标准化策略类型
                strategy_type = sample.get('strategy_type', 'unknown')
                if strategy_type not in self.strategy_mapping:
                    strategy_type = 'unknown'
                
                sample['strategy_type'] = strategy_type
                
                # 检查动作向量的合理性
                action_vec = np.array(sample['action_vec'])
                action_count = np.sum(action_vec)
                
                # 过滤异常样本（动作数量过多或过少）
                if 0 <= action_count <= 20:  # 合理的动作数量范围
                    cleaned_samples.append(sample)
                
            except Exception as e:
                logger.debug(f"清洗样本时出错: {e}")
                continue
        
        logger.info(f"数据清洗: {len(samples)} -> {len(cleaned_samples)} 样本")
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