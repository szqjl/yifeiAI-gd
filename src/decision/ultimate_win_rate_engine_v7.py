# -*- coding: utf-8 -*-
"""
Ultimate Win Rate Decision Engine V7
终极胜率导向决策引擎 V7版本
基于终极胜率导向训练模型的决策引擎
"""

import os
import torch
import torch.nn as nn
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import sys

from src.contracts.decision_provider import ActMessage, assert_v_integration_gate

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27

class UltimateWinRateEngineV7:
    """
    终极胜率导向决策引擎 V7
    使用训练好的终极胜率导向模型进行决策
    """
    
    def __init__(self, player_id: int = 0):
        self.player_id = player_id
        self.logger = logging.getLogger(f"UltimateWinRateEngineV7.{player_id}")

        # 批跑四进程并行时避免每进程占满 CPU（可用 V7_TORCH_THREADS 覆盖）
        thread_count = int(os.environ.get("V7_TORCH_THREADS", "1"))
        torch.set_num_threads(max(1, thread_count))
        
        # 模型路径（config/v7_paths.yaml + 环境变量）
        from src.utils.v7_paths import get_model_file
        self.model_path = Path(get_model_file())
        
        # 初始化模型
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载模型
        self._load_model()
        
        # 决策统计
        self.decision_count = 0
        self.model_decisions = 0
        self.fallback_decisions = 0

        assert_v_integration_gate(self, label="UltimateWinRateEngineV7")
        
    def _load_model(self):
        """加载终极胜率导向模型"""
        try:
            if not self.model_path.exists():
                self.logger.warning(f"[警告] 终极胜率导向模型未找到！模型路径: {self.model_path}")
                self.logger.warning("将使用规则引擎作为回退")
                return False
            
            # 加载模型
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 创建模型架构（与训练时一致的UltimateWinRateNet）
            from src.train.ultimate_win_rate_training import UltimateWinRateNet
            self.model = UltimateWinRateNet().to(self.device)
            
            # 加载权重
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            
            self.model.eval()
            
            self.logger.info(f"✓ 终极胜率导向模型加载成功: {self.model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ 模型加载失败: {e}")
            self.model = None
            return False
    
    def decide(self, message: ActMessage) -> int:
        """
        做出决策（IDecisionProvider v1.0）
        
        Args:
            message: 平台 act 消息（含 actionList 等）
            
        Returns:
            选择的 actionList 下标
        """
        game_state = message
        self.decision_count += 1
        
        action_list = game_state.get("actionList", [])
        if not action_list:
            return 0
        
        try:
            # 如果模型可用，使用模型决策
            if self.model is not None:
                action_index = self._model_decision(game_state, action_list)
                if action_index is not None:
                    self.model_decisions += 1
                    return action_index
            
            # 回退到规则引擎
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)
            
        except Exception as e:
            self.logger.error(f"✗ 决策失败: {e}")
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)
    
    def _model_decision(self, game_state: Dict[str, Any], action_list: List) -> Optional[int]:
        """
        使用模型进行决策
        
        Args:
            game_state: 游戏状态
            action_list: 可选动作列表
            
        Returns:
            动作索引，如果失败返回None
        """
        try:
            # 提取特征
            features = self._extract_features(game_state, action_list)
            if features is None:
                return None
            
            # 转换为张量
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)
            
            # 模型预测
            with torch.no_grad():
                predictions = self.model(features_tensor)
                action_logits = predictions['action_logits']
                probabilities = torch.softmax(action_logits, dim=-1)
            
            # 选择最佳动作
            action_probs = probabilities[0][:len(action_list)]
            best_action_idx = torch.argmax(action_probs).item()
            
            # 验证动作索引
            if 0 <= best_action_idx < len(action_list):
                confidence = action_probs[best_action_idx].item()
                self.logger.debug(f"模型决策: 动作{best_action_idx}, 置信度: {confidence:.3f}")
                return best_action_idx
            else:
                self.logger.warning(f"模型返回无效动作索引: {best_action_idx}")
                return None
                
        except Exception as e:
            self.logger.error(f"模型决策失败: {e}")
            return None
    
    def _extract_features(self, game_state: Dict[str, Any], action_list: List) -> Optional[np.ndarray]:
        """
        从游戏状态中提取特征
        
        Args:
            game_state: 游戏状态
            action_list: 可选动作列表
            
        Returns:
            特征向量，如果失败返回None
        """
        try:
            features = []
            
            # 基本游戏信息
            my_pos = game_state.get("myPos", self.player_id)
            cur_pos = game_state.get("curPos", -1)
            greater_pos = game_state.get("greaterPos", -1)
            
            # 位置特征 (4维)
            pos_features = [0] * 4
            if 0 <= my_pos < 4:
                pos_features[my_pos] = 1
            features.extend(pos_features)
            
            # 当前出牌者特征 (4维)
            cur_pos_features = [0] * 4
            if 0 <= cur_pos < 4:
                cur_pos_features[cur_pos] = 1
            features.extend(cur_pos_features)
            
            # 最大动作者特征 (4维)
            greater_pos_features = [0] * 4
            if 0 <= greater_pos < 4:
                greater_pos_features[greater_pos] = 1
            features.extend(greater_pos_features)
            
            # 手牌信息
            hand_cards = game_state.get("handCards", [])
            features.append(len(hand_cards))  # 手牌数量
            
            # 公共信息
            public_info = game_state.get("publicInfo", [])
            for i in range(4):
                if i < len(public_info) and isinstance(public_info[i], dict):
                    rest_cards = public_info[i].get("rest", DEFAULT_REST_CARDS)
                    features.append(rest_cards)
                else:
                    features.append(DEFAULT_REST_CARDS)
            
            # 等级信息
            cur_rank = game_state.get("curRank", "2")
            self_rank = game_state.get("selfRank", "2")
            oppo_rank = game_state.get("oppoRank", "2")
            
            # 将等级转换为数值
            rank_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, 
                       "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
            
            features.append(rank_map.get(cur_rank, 2))
            features.append(rank_map.get(self_rank, 2))
            features.append(rank_map.get(oppo_rank, 2))
            
            # 动作列表特征
            features.append(len(action_list))  # 可选动作数量
            
            # 当前动作和最大动作特征
            cur_action = game_state.get("curAction", [])
            greater_action = game_state.get("greaterAction", [])
            
            # 简化的动作编码
            features.append(len(cur_action) if cur_action else 0)
            features.append(len(greater_action) if greater_action else 0)
            
            # 填充到固定长度 (512维)
            target_size = 512
            current_size = len(features)
            
            if current_size < target_size:
                # 用0填充
                features.extend([0] * (target_size - current_size))
            elif current_size > target_size:
                # 截断
                features = features[:target_size]
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            self.logger.error(f"特征提取失败: {e}")
            return None
    
    def _rule_based_decision(self, game_state: Dict[str, Any], action_list: List) -> int:
        """
        基于规则的回退决策
        
        Args:
            game_state: 游戏状态
            action_list: 可选动作列表
            
        Returns:
            动作索引
        """
        try:
            # 简单的规则：优先选择非PASS动作
            for i, action in enumerate(action_list):
                if action and len(action) > 0:
                    if isinstance(action, list) and action[0] != "PASS":
                        return i
                    elif isinstance(action, str) and action.upper() != "PASS":
                        return i
            
            # 如果都是PASS，返回第一个
            return 0
            
        except Exception as e:
            self.logger.error(f"规则决策失败: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        return {
            "total_decisions": self.decision_count,
            "model_decisions": self.model_decisions,
            "fallback_decisions": self.fallback_decisions,
            "model_usage_rate": self.model_decisions / max(1, self.decision_count),
            "model_available": self.model is not None
        }