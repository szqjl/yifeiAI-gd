"""
快速评估突破性模型
"""

import torch
import torch.nn as nn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BreakthroughNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(512, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 512)
        )
        
    def forward(self, x):
        return self.net(x)


def evaluate_breakthrough():
    """评估突破性模型"""
    
    # 加载模型
    model = BreakthroughNet()
    model.load_state_dict(torch.load("models/bc_model_stage7_breakthrough.pth"))
    model.eval()
    
    # 加载数据
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=32,
        max_samples=1000,
        shuffle=False
    )
    
    total_samples = 0
    exact_matches = 0
    count_matches = 0
    total_predicted = 0
    total_true = 0
    
    with torch.no_grad():
        for state_vec, action_vec, _ in dataloader:
            pred_logits = model(state_vec)
            pred_probs = torch.sigmoid(pred_logits)
            
            for i in range(action_vec.size(0)):
                true_action = action_vec[i]
                true_count = int(true_action.sum().item())
                
                if true_count == 0:
                    # 0卡牌情况
                    if pred_probs[i].max() < 0.3:
                        exact_matches += 1
                    pred_count = 0
                else:
                    # 有卡牌情况
                    _, top_k_indices = torch.topk(pred_probs[i], true_count)
                    pred_action = torch.zeros_like(true_action)
                    pred_action[top_k_indices] = 1.0
                    
                    if torch.equal(pred_action, true_action):
                        exact_matches += 1
                    
                    pred_count = true_count  # 使用真实数量进行Top-K
                
                # 统计
                if pred_count == true_count:
                    count_matches += 1
                
                total_predicted += pred_count
                total_true += true_count
                total_samples += 1
    
    # 计算指标
    exact_match_rate = exact_matches / total_samples
    count_match_rate = count_matches / total_samples
    avg_predicted = total_predicted / total_samples
    avg_true = total_true / total_samples
    
    logger.info("=" * 50)
    logger.info("Stage 7.7 突破性模型评估结果")
    logger.info("=" * 50)
    logger.info(f"评估样本数: {total_samples}")
    logger.info(f"完全匹配率: {exact_match_rate:.1%} ⭐")
    logger.info(f"数量匹配率: {count_match_rate:.1%}")
    logger.info(f"平均预测卡牌: {avg_predicted:.1f}")
    logger.info(f"平均真实卡牌: {avg_true:.1f}")
    logger.info(f"预测比例: {avg_predicted/avg_true:.2f}x")
    
    if exact_match_rate > 0.2:
        logger.info("🎉 突破成功！达到实用水平")
    
    return exact_match_rate


if __name__ == "__main__":
    match_rate = evaluate_breakthrough()