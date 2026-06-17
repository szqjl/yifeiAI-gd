"""
胜率导向训练包装脚本 - 用于M1工作流
优化：优先使用胜利记录，胜负加权学习
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """训练胜率导向模型并保存到工作流期望的路径"""
    try:
        from advanced_win_rate_training import train_advanced_win_rate_model
        
        logger.info("=" * 80)
        logger.info("启动胜率导向训练（M1工作流优化版）")
        logger.info("=" * 80)
        logger.info("优化策略:")
        logger.info("  1. 优先使用胜利记录（70%胜利 + 30%失败）")
        logger.info("  2. 胜负加权学习（胜利动作2x权重，失败动作0.5x权重）")
        logger.info("  3. 胜率预测与动作预测联合优化")
        logger.info("=" * 80)
        
        # 训练模型
        model, score = train_advanced_win_rate_model()
        
        if model is None:
            logger.error("训练失败，模型为None")
            return 1
        
        # 保存到工作流期望的路径
        workflow_model_path = Path("models/bc_model_stage7_optimized.pth")
        workflow_model_path.parent.mkdir(parents=True, exist_ok=True)
        
        import torch
        torch.save({
            'model_state_dict': model.state_dict(),
            'advanced_score': score,
            'training_type': 'advanced_win_rate',
            'optimization': 'victory_record_prioritized'
        }, str(workflow_model_path))
        
        logger.info(f"✅ 模型已保存到工作流路径: {workflow_model_path}")
        logger.info(f"✅ 训练完成，先进评分: {score:.3f}")
        
        return 0
        
    except Exception as e:
        logger.error(f"训练过程出错: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
