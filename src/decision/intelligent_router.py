# -*- coding: utf-8 -*-
"""
智能路由器 (Intelligent Router)
基于 Agentic Design Patterns 路由模式优化

功能：
- 智能路由决策（多因素路由）
- 路由缓存机制（LRU缓存）
- 动态路由策略
- 路由性能优化
"""

from typing import Dict, Optional, List
from collections import OrderedDict
import hashlib
import json
import logging
from datetime import datetime
try:
    from game_logic.guandan_constants import CARDS_PER_PLAYER, DEFAULT_REST_CARDS
except ImportError:
    CARDS_PER_PLAYER = 27
    DEFAULT_REST_CARDS = 27


class RouteCache:
    """路由缓存（LRU缓存机制）"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化路由缓存
        
        Args:
            max_size: 最大缓存条目数
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.hit_count = 0
        self.miss_count = 0
        self.logger = logging.getLogger("RouteCache")
    
    def get_route(self, context_hash: str) -> Optional[int]:
        """
        获取缓存的路由
        
        Args:
            context_hash: 上下文哈希值
            
        Returns:
            缓存的路由索引，如果不存在返回None
        """
        if context_hash in self.cache:
            # 移动到末尾（LRU）
            self.cache.move_to_end(context_hash)
            self.hit_count += 1
            return self.cache[context_hash]
        
        self.miss_count += 1
        return None
    
    def cache_route(self, context_hash: str, route: int):
        """
        缓存路由结果
        
        Args:
            context_hash: 上下文哈希值
            route: 路由索引
        """
        if len(self.cache) >= self.max_size:
            # LRU淘汰：删除最旧的条目
            self._evict_lru()
        
        self.cache[context_hash] = route
        # 移动到末尾
        self.cache.move_to_end(context_hash)
    
    def _evict_lru(self):
        """淘汰最久未使用的条目"""
        if self.cache:
            # 删除第一个（最旧的）条目
            self.cache.popitem(last=False)
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0.0
        
        return {
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate
        }
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0


class IntelligentStageRouter:
    """智能阶段路由器（基于 Agentic Design Patterns 路由模式）"""
    
    def __init__(self, config: Dict, base_router=None):
        """
        初始化智能路由器
        
        Args:
            config: 配置字典
            base_router: 基础路由器（StageRouter实例）
        """
        self.config = config
        self.base_router = base_router
        self.route_cache = RouteCache(max_size=config.get('route_cache_size', 1000))
        self.logger = logging.getLogger("IntelligentRouter")
        
        # 路由权重配置
        self.route_weights = {
            'phase': 0.4,           # 阶段因素权重
            'threat': 0.25,         # 威胁因素权重
            'teammate': 0.2,        # 队友因素权重
            'hand_structure': 0.15,  # 手牌结构因素权重
        }
    
    def route(self, message: Dict) -> int:
        """
        智能路由决策
        
        Args:
            message: 游戏状态消息
            
        Returns:
            路由决策结果（actionList索引）
        """
        # 1. 构建路由上下文
        context = self._build_routing_context(message)
        
        # 2. 生成上下文哈希（用于缓存）
        context_hash = self._hash_context(context)
        
        # 3. 尝试从缓存获取
        cached_route = self.route_cache.get_route(context_hash)
        if cached_route is not None:
            self.logger.debug(f"Route cache hit: {context_hash[:8]}")
            return cached_route
        
        # 4. 智能路由决策
        route_result = self._intelligent_route(context, message)
        
        # 5. 缓存结果
        self.route_cache.cache_route(context_hash, route_result)
        
        return route_result
    
    def _build_routing_context(self, message: Dict) -> Dict:
        """构建路由上下文"""
        handcards = message.get("handCards", [])
        public_info = message.get("publicInfo", [])
        my_pos = message.get("myPos", 0)
        
        # 计算剩余牌数
        my_remain = len(handcards) if handcards else CARDS_PER_PLAYER
        cards_left = {}
        opponent_rest_cards_list = []
        teammate_rest_cards = DEFAULT_REST_CARDS
        
        if public_info and len(public_info) == 4:
            for i, info in enumerate(public_info):
                rest = info.get("rest", DEFAULT_REST_CARDS)
                cards_left[i] = rest
                if i != my_pos:
                    opponent_rest_cards_list.append(rest)
                    # 队友位置：第1个和第3个为一队，第2个和第4个为一队
                    if (my_pos in [0, 2] and i in [0, 2]) or (my_pos in [1, 3] and i in [1, 3]):
                        teammate_rest_cards = rest
        
        # 判断游戏阶段
        game_phase = self._get_game_phase(my_remain)
        
        # 判断是否被动出牌
        is_passive = self._is_passive_play(message)
        
        # 计算威胁度
        threat_level = self._calculate_threat_level(opponent_rest_cards_list, my_remain)
        
        # 分析手牌结构
        hand_structure_score = self._analyze_hand_structure(handcards)
        
        return {
            'my_remain': my_remain,
            'game_phase': game_phase,
            'is_passive': is_passive,
            'cards_left': cards_left,
            'opponent_rest_cards_list': opponent_rest_cards_list,
            'teammate_rest_cards': teammate_rest_cards,
            'threat_level': threat_level,
            'hand_structure_score': hand_structure_score,
            'my_pos': my_pos,
        }
    
    def _intelligent_route(self, context: Dict, message: Dict) -> int:
        """
        智能路由决策（多因素路由）
        
        Args:
            context: 路由上下文
            message: 游戏状态消息
            
        Returns:
            路由决策结果
        """
        # 如果基础路由器可用，先尝试基础路由
        if self.base_router:
            base_route = self.base_router.route(message)
            if base_route is not None and base_route >= 0:
                # 评估基础路由的质量
                base_route_score = self._evaluate_route_quality(base_route, context, message)
                
                # 如果基础路由质量足够高，直接使用
                if base_route_score > 0.7:
                    return base_route
        
        # 多因素路由决策
        route_scores = self._calculate_route_scores(context, message)
        
        # 选择最佳路由
        best_route = self._select_best_route(route_scores, context, message)
        
        return best_route
    
    def _calculate_route_scores(self, context: Dict, message: Dict) -> Dict[str, float]:
        """
        计算各路由因素的得分
        
        Args:
            context: 路由上下文
            message: 游戏状态消息
            
        Returns:
            各因素的得分字典
        """
        scores = {}
        
        # 因素1: 阶段因素（基础因素）
        scores['phase'] = self._score_by_phase(context)
        
        # 因素2: 威胁因素
        scores['threat'] = self._score_by_threat(context)
        
        # 因素3: 队友因素
        scores['teammate'] = self._score_by_teammate(context)
        
        # 因素4: 手牌结构因素
        scores['hand_structure'] = self._score_by_hand_structure(context)
        
        return scores
    
    def _score_by_phase(self, context: Dict) -> float:
        """根据阶段评分"""
        game_phase = context.get('game_phase', 'opening')
        my_remain = context.get('my_remain', DEFAULT_REST_CARDS)
        
        # 阶段评分：残局阶段评分更高（需要更精确的路由）
        phase_scores = {
            'opening': 0.3,
            'mid_early': 0.5,
            'mid_late': 0.7,
            'endgame_early': 0.9,
            'endgame_late': 1.0,
        }
        
        return phase_scores.get(game_phase, 0.5)
    
    def _score_by_threat(self, context: Dict) -> float:
        """根据威胁度评分"""
        threat_level = context.get('threat_level', 0.5)
        opponent_cards = context.get('opponent_rest_cards_list', [])
        
        if not opponent_cards:
            return 0.5
        
        # 对手牌数越少，威胁越大
        min_opponent_cards = min(opponent_cards)
        if min_opponent_cards <= 3:
            return 1.0  # 高威胁
        elif min_opponent_cards <= 5:
            return 0.8
        elif min_opponent_cards <= 10:
            return 0.6
        else:
            return 0.4
    
    def _score_by_teammate(self, context: Dict) -> float:
        """根据队友状态评分"""
        teammate_rest_cards = context.get('teammate_rest_cards', DEFAULT_REST_CARDS)
        my_remain = context.get('my_remain', DEFAULT_REST_CARDS)
        
        # 队友牌数很少，需要更精确的路由
        if teammate_rest_cards <= 3:
            return 1.0
        elif teammate_rest_cards <= 5:
            return 0.8
        elif teammate_rest_cards <= 10:
            return 0.6
        else:
            return 0.4
    
    def _score_by_hand_structure(self, context: Dict) -> float:
        """根据手牌结构评分"""
        hand_structure_score = context.get('hand_structure_score', 0.5)
        return hand_structure_score
    
    def _select_best_route(self, route_scores: Dict[str, float], context: Dict, message: Dict) -> int:
        """
        选择最佳路由
        
        Args:
            route_scores: 路由得分
            context: 路由上下文
            message: 游戏状态消息
            
        Returns:
            最佳路由索引
        """
        # 加权综合得分
        total_score = sum(
            route_scores.get(factor, 0.5) * self.route_weights.get(factor, 0.25)
            for factor in self.route_weights.keys()
        )
        
        # 如果综合得分高，使用更精确的路由策略
        # 否则使用基础路由
        if self.base_router:
            return self.base_router.route(message)
        else:
            # 降级：返回默认路由
            action_list = message.get("actionList", [])
            if action_list:
                return 0
            return 0
    
    def _evaluate_route_quality(self, route: int, context: Dict, message: Dict) -> float:
        """评估路由质量"""
        # 简化实现：基于上下文评估
        action_list = message.get("actionList", [])
        if route < 0 or route >= len(action_list):
            return 0.0
        
        # 基础质量评分
        quality = 0.5
        
        # 根据阶段调整
        game_phase = context.get('game_phase', 'opening')
        if game_phase in ['endgame_early', 'endgame_late']:
            quality += 0.2
        
        # 根据威胁度调整
        threat_level = context.get('threat_level', 0.5)
        quality += threat_level * 0.3
        
        return min(1.0, quality)
    
    def _get_game_phase(self, my_remain: int) -> str:
        """获取游戏阶段"""
        if my_remain > 20:
            return "opening"
        elif my_remain > 15:
            return "mid_early"
        elif my_remain > 10:
            return "mid_late"
        elif my_remain > 5:
            return "endgame_early"
        else:
            return "endgame_late"
    
    def _is_passive_play(self, message: Dict) -> bool:
        """判断是否为被动出牌"""
        cur_action = message.get("curAction")
        cur_pos = message.get("curPos", -1)
        greater_pos = message.get("greaterPos", -1)
        
        if not cur_action:
            return False
        
        if isinstance(cur_action, str):
            try:
                import ast
                cur_action = ast.literal_eval(cur_action)
            except (ValueError, SyntaxError):
                return False
        
        if isinstance(cur_action, list) and len(cur_action) > 0:
            first_elem = cur_action[0]
            if first_elem is None or first_elem == "PASS":
                if cur_pos == -1 or greater_pos == -1:
                    return False
            elif isinstance(first_elem, str) and first_elem in ["Single", "Pair", "Trips", "ThreeWithTwo", "ThreePair", "TwoTrips", "Straight", "StraightFlush", "Bomb"]:
                return True
        
        return cur_pos != -1 and greater_pos != -1
    
    def _calculate_threat_level(self, opponent_rest_cards_list: List[int], my_remain: int) -> float:
        """计算威胁度"""
        if not opponent_rest_cards_list:
            return 0.5
        
        min_opponent_cards = min(opponent_rest_cards_list)
        
        # 对手牌数越少，威胁越大
        if min_opponent_cards <= 2:
            return 1.0
        elif min_opponent_cards <= 5:
            return 0.8
        elif min_opponent_cards <= 10:
            return 0.6
        else:
            return 0.4
    
    def _analyze_hand_structure(self, handcards: List) -> float:
        """分析手牌结构"""
        if not handcards:
            return 0.5
        
        # 简化实现：基于手牌数量
        card_count = len(handcards)
        
        # 手牌结构评分：牌数适中时评分较高
        if 10 <= card_count <= 20:
            return 0.8
        elif 5 <= card_count < 10:
            return 0.9
        elif card_count < 5:
            return 1.0
        else:
            return 0.6
    
    def _hash_context(self, context: Dict) -> str:
        """生成上下文哈希值"""
        # 选择关键字段进行哈希
        key_fields = {
            'my_remain': context.get('my_remain', 0),
            'game_phase': context.get('game_phase', 'opening'),
            'is_passive': context.get('is_passive', False),
            'threat_level': round(context.get('threat_level', 0.5), 1),
        }
        
        # 转换为JSON字符串并哈希
        context_str = json.dumps(key_fields, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        return self.route_cache.get_cache_stats()
    
    def clear_cache(self):
        """清空缓存"""
        self.route_cache.clear()

