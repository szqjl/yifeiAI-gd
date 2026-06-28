# -*- coding: utf-8 -*-
"""
残局预处理模块 + 决策引擎
=========================
在 decide() 入口统一注入，设置残局上下文供 Guard / 推荐引擎 / heuristic 读取。
EndgameDecider 读取 _endgame_context 执行 Q0→Q3 四级决策。
"""
from .endgame_preprocessor import EndgamePreprocessor, endgame_preprocess
from .endgame_decide import EndgameDecider

__all__ = ["EndgamePreprocessor", "EndgameDecider", "endgame_preprocess"]
