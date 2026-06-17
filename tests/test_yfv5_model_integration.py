#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试yf_v5中超优化版模型的集成
"""

import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.decision.rl_decision_engine import RLDecisionEngine
import numpy as np

def test_model_integration():
    """测试模型集成"""
    print("="*80)
    print("测试yf_v5超优化版模型集成")
    print("="*80)
    
    # 1. 测试模型加载
    print("\n1. 测试模型加载...")
    try:
        engine = RLDecisionEngine()
        if engine.model_loaded:
            print("✓ 模型加载成功")
            print(f"  模型路径: {engine.model_path}")
        else:
            print("✗ 模型加载失败")
            return False
    except Exception as e:
        print(f"✗ 模型加载异常: {e}")
        return False
    
    # 2. 测试推理
    print("\n2. 测试模型推理...")
    try:
        # 创建一个简单的测试状态（前5个位置激活）
        state = np.zeros(512, dtype=np.float32)
        state[0:5] = 1.0
        
        action = engine._stage5_model_inference(state)
        
        print(f"✓ 推理成功")
        print(f"  输出维度: {len(action)}")
        print(f"  激活数量: {int(action.sum())}")
        print(f"  激活索引: {np.where(action > 0)[0][:10].tolist()}")
        
    except Exception as e:
        print(f"✗ 推理异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 测试决策引擎
    print("\n3. 测试决策引擎...")
    try:
        from src.decision.yf_v5_stage5_decision_engine import YF_V5_Stage5_DecisionEngine
        
        decision_engine = YF_V5_Stage5_DecisionEngine(player_id=0)
        print("✓ 决策引擎初始化成功")
        print(f"  使用的模型路径: {decision_engine.rl_engine.model_path}")
        
    except Exception as e:
        print(f"✗ 决策引擎初始化异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*80)
    print("✓ 所有测试通过，模型集成成功！")
    print("="*80)
    return True

if __name__ == "__main__":
    test_model_integration()

