# -*- coding: utf-8 -*-
"""
检查RL模型是否已正确加载
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.decision.rl_decision_engine import RLDecisionEngine
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

def check_model_loading():
    """检查模型是否已正确加载"""
    print("="*60)
    print("检查RL模型加载状态")
    print("="*60)
    
    # 1. 检查模型文件是否存在
    model_path = "models/bc_model_v1.pth"
    model_file = Path(model_path)
    
    if not model_file.exists():
        print(f"❌ 模型文件不存在: {model_path}")
        return False
    
    model_size = model_file.stat().st_size / (1024 * 1024)  # MB
    print(f"✓ 模型文件存在: {model_path}")
    print(f"✓ 模型大小: {model_size:.2f} MB")
    
    # 2. 尝试加载模型
    print("\n尝试加载RL引擎...")
    try:
        rl_engine = RLDecisionEngine(model_path=model_path)
        
        if rl_engine.model_loaded:
            print("="*60)
            print("✅ 模型加载成功！")
            print("="*60)
            print(f"✓ 模型路径: {rl_engine.model_path}")
            print(f"✓ 模型状态: 已加载")
            print(f"✓ 预测阈值: {rl_engine.agent.prediction_threshold}")
            print(f"✓ 输入维度: {rl_engine.agent.policy.input_dim}")
            print(f"✓ 输出维度: {rl_engine.agent.policy.output_dim}")
            return True
        else:
            print("="*60)
            print("❌ 模型加载失败！")
            print("="*60)
            print("⚠ 使用随机权重（不推荐用于生产环境）")
            return False
            
    except Exception as e:
        print("="*60)
        print("❌ 加载过程中发生错误！")
        print("="*60)
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_model_loading()
    sys.exit(0 if success else 1)
