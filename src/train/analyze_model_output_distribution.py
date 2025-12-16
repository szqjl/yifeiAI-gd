# -*- coding: utf-8 -*-
"""
模型输出分布分析工具
用于检查模型在不同轮次（特别是胜率为0的轮次）的输出分布
"""

import os
import sys
import json
import numpy as np
import torch
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime

# 修复Windows控制台编码
try:
    from src.utils.encoding_fix import fix_windows_console_encoding
    fix_windows_console_encoding()
except ImportError:
    pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.knowledge_processor.replay_parser import ReplayParser
from src.rl_agent.model import ImprovedGuandanPolicyNet
from src.utils.device_selector import select_compatible_device
from src.train.pretrain import GuandanDataset
from src.train.game_oriented_validation import GameOrientedValidator


class ModelOutputAnalyzer:
    """模型输出分布分析器"""
    
    def __init__(self, model_path: str, device=None):
        """
        初始化分析器
        
        Args:
            model_path: 模型文件路径
            device: 计算设备（如果为None，自动选择）
        """
        self.model_path = model_path
        if device is None:
            self.device, _ = select_compatible_device()
        else:
            self.device = device
        
        # 加载模型
        self.model = self._load_model()
        
    def _load_model(self):
        """加载模型"""
        print(f"[信息] 正在加载模型: {self.model_path}")
        # PyTorch 2.6+ 需要设置 weights_only=False 来加载包含 numpy 对象的模型
        checkpoint = torch.load(self.model_path, map_location=self.device, weights_only=False)
        
        # 获取模型配置
        model_config = checkpoint.get('model_config', {})
        input_dim = model_config.get('input_dim', 512)
        hidden_dim = model_config.get('hidden_dim', 256)
        output_dim = model_config.get('output_dim', 512)
        dropout_rate = model_config.get('dropout_rate', 0.1)
        enable_strategy_head = model_config.get('enable_strategy_head', True)
        attention_heads = model_config.get('attention_heads', 8)
        
        # 创建模型
        model = ImprovedGuandanPolicyNet(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            output_dim=output_dim,
            dropout_rate=dropout_rate,
            enable_strategy_head=enable_strategy_head,
            attention_heads=attention_heads
        )
        
        # 加载权重
        if 'model_state_dict' in checkpoint:
            model.load_state_dict(checkpoint['model_state_dict'])
        else:
            model.load_state_dict(checkpoint)
        
        model.to(self.device)
        model.eval()
        print(f"[信息] 模型已加载到设备: {self.device}")
        
        return model
    
    def analyze_round_outputs(self, game_records: List[Dict], round_idx: int, 
                            round_records: List[Dict], player_id: int = 0) -> Dict:
        """
        分析特定轮次的模型输出分布
        
        Args:
            game_records: 所有游戏记录
            round_idx: 轮次索引（从0开始）
            round_records: 该轮次的游戏记录
            player_id: 玩家ID
            
        Returns:
            分析结果字典
        """
        print(f"\n{'='*60}")
        print(f"分析第 {round_idx + 1} 轮输出分布")
        print(f"{'='*60}")
        print(f"该轮次游戏数: {len(round_records)}")
        
        # 从游戏记录中提取训练数据
        parser = ReplayParser(None)
        try:
            # 提取训练数据
            raw_data = parser.extract_training_data(round_records)
            if len(raw_data) == 0:
                print("[警告] 该轮次没有有效训练数据")
                return {
                    'round': round_idx + 1,
                    'num_samples': 0,
                    'error': 'no_training_data'
                }
            
            # 创建数据集
            dataset = GuandanDataset(raw_data)
        except Exception as e:
            print(f"[错误] 提取训练数据失败: {e}")
            return {
                'round': round_idx + 1,
                'num_samples': 0,
                'error': f'extraction_failed: {str(e)}'
            }
        
        if len(dataset) == 0:
            print("[警告] 该轮次没有有效数据")
            return {
                'round': round_idx + 1,
                'num_samples': 0,
                'error': 'no_data'
            }
        
        # 分析模型输出
        all_logits = []
        all_probs = []
        all_scaled_probs = []
        all_actions = []
        all_predicted_actions = []
        zero_output_count = 0
        invalid_output_count = 0
        
        with torch.no_grad():
            for i in range(min(len(dataset), 1000)):  # 最多分析1000个样本
                try:
                    # 数据集返回13个值，我们只需要前两个：state_vec 和 action_vec
                    # 格式: state_vec, action_vec, strategy_type_idx, pattern_type_idx, ...
                    sample = dataset[i]
                    if isinstance(sample, (tuple, list)) and len(sample) >= 2:
                        state_vec = sample[0]
                        action_vec = sample[1]
                    else:
                        print(f"[警告] 样本 {i} 格式不正确，跳过")
                        continue
                    
                    # 确保是tensor格式
                    if not isinstance(state_vec, torch.Tensor):
                        state_vec = torch.FloatTensor(state_vec)
                    if not isinstance(action_vec, torch.Tensor):
                        action_vec = torch.FloatTensor(action_vec)
                    
                    # 确保维度正确
                    if state_vec.dim() == 1:
                        state_vec = state_vec.unsqueeze(0)
                    if action_vec.dim() == 1:
                        action_vec = action_vec.unsqueeze(0) if state_vec.size(0) > 1 else action_vec
                    
                    state_vec = state_vec.to(self.device)
                    action_vec = action_vec.to(self.device)
                    
                    # 如果state_vec是batch格式，取第一个
                    if state_vec.size(0) > 1:
                        state_vec = state_vec[0:1]
                    if action_vec.dim() > 1 and action_vec.size(0) > 1:
                        action_vec = action_vec[0]
                    
                    # 获取模型输出
                    logits = self.model(state_vec, return_strategy=False)
                    probs = torch.sigmoid(logits)
                    scaled_probs = probs * 5.0
                    scaled_probs = torch.clamp(scaled_probs, 0, 1)
                    
                    # 检查输出是否异常
                    logits_flat = logits.cpu().numpy().flatten()
                    probs_flat = probs.cpu().numpy().flatten()
                    scaled_probs_flat = scaled_probs.cpu().numpy().flatten()
                    
                    # 检查是否全为0或全为1
                    if np.all(logits_flat == 0) or np.all(probs_flat == 0):
                        zero_output_count += 1
                    if np.all(scaled_probs_flat < 0.1):  # 所有概率都很低
                        invalid_output_count += 1
                    
                    all_logits.append(logits_flat)
                    all_probs.append(probs_flat)
                    all_scaled_probs.append(scaled_probs_flat)
                    all_actions.append(action_vec.cpu().numpy())
                    
                    # 预测的动作（使用阈值0.3）
                    predicted = (scaled_probs > 0.3).cpu().numpy().flatten()
                    all_predicted_actions.append(predicted)
                    
                except Exception as e:
                    print(f"[警告] 处理样本 {i} 时出错: {e}")
                    continue
        
        if len(all_logits) == 0:
            print("[警告] 没有成功处理的样本")
            return {
                'round': round_idx + 1,
                'num_samples': 0,
                'error': 'processing_failed'
            }
        
        # 转换为numpy数组
        all_logits = np.array(all_logits)
        all_probs = np.array(all_probs)
        all_scaled_probs = np.array(all_scaled_probs)
        all_actions = np.array(all_actions)
        all_predicted_actions = np.array(all_predicted_actions)
        
        # 计算统计信息
        logits_mean = np.mean(all_logits)
        logits_std = np.std(all_logits)
        logits_min = np.min(all_logits)
        logits_max = np.max(all_logits)
        
        probs_mean = np.mean(all_probs)
        probs_std = np.std(all_probs)
        probs_min = np.min(all_probs)
        probs_max = np.max(all_probs)
        
        scaled_probs_mean = np.mean(all_scaled_probs)
        scaled_probs_std = np.std(all_scaled_probs)
        
        # 计算预测的卡牌数量分布
        predicted_card_counts = [pred.sum() for pred in all_predicted_actions]
        true_card_counts = [act.sum() for act in all_actions]
        
        # 打印统计信息
        print(f"\n输出统计:")
        print(f"  Logits: 均值={logits_mean:.4f}, 标准差={logits_std:.4f}, 范围=[{logits_min:.4f}, {logits_max:.4f}]")
        print(f"  Probs: 均值={probs_mean:.4f}, 标准差={probs_std:.4f}, 范围=[{probs_min:.4f}, {probs_max:.4f}]")
        print(f"  Scaled Probs: 均值={scaled_probs_mean:.4f}, 标准差={scaled_probs_std:.4f}")
        print(f"  预测卡牌数: 均值={np.mean(predicted_card_counts):.2f}, 范围=[{np.min(predicted_card_counts)}, {np.max(predicted_card_counts)}]")
        print(f"  真实卡牌数: 均值={np.mean(true_card_counts):.2f}, 范围=[{np.min(true_card_counts)}, {np.max(true_card_counts)}]")
        print(f"  零输出样本数: {zero_output_count}/{len(all_logits)} ({zero_output_count/len(all_logits)*100:.1f}%)")
        print(f"  无效输出样本数: {invalid_output_count}/{len(all_logits)} ({invalid_output_count/len(all_logits)*100:.1f}%)")
        
        # 返回结果
        return {
            'round': round_idx + 1,
            'num_samples': len(all_logits),
            'statistics': {
                'logits': {
                    'mean': float(logits_mean),
                    'std': float(logits_std),
                    'min': float(logits_min),
                    'max': float(logits_max)
                },
                'probs': {
                    'mean': float(probs_mean),
                    'std': float(probs_std),
                    'min': float(probs_min),
                    'max': float(probs_max)
                },
                'scaled_probs': {
                    'mean': float(scaled_probs_mean),
                    'std': float(scaled_probs_std)
                },
                'predicted_card_counts': {
                    'mean': float(np.mean(predicted_card_counts)),
                    'std': float(np.std(predicted_card_counts)),
                    'min': int(np.min(predicted_card_counts)),
                    'max': int(np.max(predicted_card_counts))
                },
                'true_card_counts': {
                    'mean': float(np.mean(true_card_counts)),
                    'std': float(np.std(true_card_counts)),
                    'min': int(np.min(true_card_counts)),
                    'max': int(np.max(true_card_counts))
                }
            },
            'anomalies': {
                'zero_output_count': zero_output_count,
                'zero_output_ratio': float(zero_output_count / len(all_logits)),
                'invalid_output_count': invalid_output_count,
                'invalid_output_ratio': float(invalid_output_count / len(all_logits))
            }
        }
    
    def analyze_stability_rounds(self, game_records: List[Dict], player_id: int = 0, 
                               num_rounds: int = 10) -> Dict:
        """
        分析稳定性测试中各轮次的输出分布
        
        Args:
            game_records: 游戏记录列表
            player_id: 玩家ID
            num_rounds: 轮次数
            
        Returns:
            所有轮次的分析结果
        """
        print("="*60)
        print("模型输出分布分析 - 稳定性测试各轮次")
        print("="*60)
        
        if len(game_records) < num_rounds:
            num_rounds = len(game_records)
        
        # 分割数据为多轮
        games_per_round = len(game_records) // num_rounds
        all_results = []
        
        for round_idx in range(num_rounds):
            start_idx = round_idx * games_per_round
            end_idx = start_idx + games_per_round if round_idx < num_rounds - 1 else len(game_records)
            round_records = game_records[start_idx:end_idx]
            
            result = self.analyze_round_outputs(
                game_records, round_idx, round_records, player_id
            )
            all_results.append(result)
        
        return {
            'num_rounds': num_rounds,
            'round_results': all_results
        }
    
    def save_analysis_results(self, results: Dict, output_path: str):
        """保存分析结果到JSON文件"""
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n[信息] 分析结果已保存到: {output_path}")


def analyze_model_outputs(model_path: str, data_dir: str = "game_records", 
                         player_id: int = 0, num_rounds: int = 10,
                         output_path: Optional[str] = None):
    """
    分析模型输出分布的主函数
    
    Args:
        model_path: 模型文件路径
        data_dir: 游戏记录目录
        player_id: 玩家ID
        num_rounds: 稳定性测试轮数
        output_path: 输出文件路径（如果为None，自动生成）
    """
    # 加载游戏记录
    parser = ReplayParser(data_dir)
    game_records = parser.load_replays()
    
    if not game_records:
        print("[错误] 未找到游戏记录")
        return
    
    print(f"[信息] 已加载 {len(game_records)} 条游戏记录")
    
    # 创建分析器
    analyzer = ModelOutputAnalyzer(model_path)
    
    # 分析各轮次
    results = analyzer.analyze_stability_rounds(game_records, player_id, num_rounds)
    
    # 添加元数据
    results['metadata'] = {
        'model_path': model_path,
        'data_dir': data_dir,
        'player_id': player_id,
        'total_games': len(game_records),
        'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
    }
    
    # 保存结果
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"training_logs/model_output_analysis_{timestamp}.json"
    
    analyzer.save_analysis_results(results, output_path)
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="分析模型输出分布")
    parser.add_argument("--model", type=str, required=True, help="模型文件路径")
    parser.add_argument("--data_dir", type=str, default="game_records", help="游戏记录目录")
    parser.add_argument("--player_id", type=int, default=0, help="玩家ID")
    parser.add_argument("--num_rounds", type=int, default=10, help="稳定性测试轮数")
    parser.add_argument("--output", type=str, default=None, help="输出文件路径")
    
    args = parser.parse_args()
    
    analyze_model_outputs(
        model_path=args.model,
        data_dir=args.data_dir,
        player_id=args.player_id,
        num_rounds=args.num_rounds,
        output_path=args.output
    )

