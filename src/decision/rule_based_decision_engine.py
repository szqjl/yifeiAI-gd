# -*- coding: utf-8 -*-
"""
基于规则的决策引擎 (Rule-Based Decision Engine)
功能：
- 整合StageRouter和所有阶段处理器
- 提供统一的决策接口
- 实现硬编码规则引擎
"""

from typing import Dict
from .stage_router import StageRouter
from .phase_handlers import (
    OpeningActiveHandler, OpeningPassiveHandler,
    MidEarlyActiveHandler, MidEarlyPassiveHandler,
    MidLateActiveHandler, MidLatePassiveHandler,
    EndgameEarlyActiveHandler, EndgameEarlyPassiveHandler,
    EndgameLateActiveHandler, EndgameLatePassiveHandler,
    TributeHandler, BackHandler
)


class RuleBasedDecisionEngine:
    """基于规则的决策引擎（主入口）"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 创建阶段路由器
        self.router = StageRouter(self.config)
        
        # 初始化各阶段处理器
        self._init_phase_handlers()
        
        # 设置处理器到路由器
        self._setup_router()
    
    def _init_phase_handlers(self):
        """初始化各阶段处理器"""
        self.handlers = {
            'opening_active': OpeningActiveHandler(self.config),
            'opening_passive': OpeningPassiveHandler(self.config),
            'mid_early_active': MidEarlyActiveHandler(self.config),
            'mid_early_passive': MidEarlyPassiveHandler(self.config),
            'mid_late_active': MidLateActiveHandler(self.config),
            'mid_late_passive': MidLatePassiveHandler(self.config),
            'endgame_early_active': EndgameEarlyActiveHandler(self.config),
            'endgame_early_passive': EndgameEarlyPassiveHandler(self.config),
            'endgame_late_active': EndgameLateActiveHandler(self.config),
            'endgame_late_passive': EndgameLatePassiveHandler(self.config),
        }
        
        self.tribute_handler = TributeHandler(self.config)
        self.back_handler = BackHandler(self.config)
    
    def _setup_router(self):
        """设置路由器"""
        self.router.set_handlers(self.handlers)
        self.router.set_special_handlers(
            tribute_handler=self.tribute_handler,
            back_handler=self.back_handler
        )
    
    def decide(self, message: Dict) -> int:
        """
        核心决策方法
        
        Args:
            message: 游戏状态消息
        
        Returns:
            决策结果索引
        """
        return self.router.route(message)

