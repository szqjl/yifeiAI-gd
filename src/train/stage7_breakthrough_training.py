"""
Stage 7.7: 突破性训练 - 基于21.5%匹配率的成功基础
"""

import torch
import torch.nn as nn
import torch.optim as optim
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


def breakthrough_loss(pred_logits, target_actions):
    """突破性损失函数"""
    pred_probs = torch.sigmoid(pred_logits)
    
    # 基础BCE损失
    bce_loss = nn.functional.binary_cross_entropy(pred_probs, target_actions, reduction='mean')
    
    # 精确匹配奖励
    exact_matches = 0
    batch_size = pred_logits.size(0)
    
    for i in range(batch_size):
        true_count = int(target_actions[i].sum().item())
        
        if true_count == 0:
            # 0卡牌情况
            if pred_probs[i].max() < 0.3:
                exact_matches += 1
        else:
            # 有卡牌情况：Top-K
            _, top_k_indices = torch.topk(pred_probs[i], true_count)
            pred_action = torch.zeros_like(target_actions[i])
            pred_action[top_k_indices] = 1.0
            
            if torch.equal(pred_action, target_actions[i]):
                exact_matches += 1
    
    match_rate = exact_matches / batch_size
    match_bonus = -10 * match_rate  # 匹配奖励
    
    return bce_loss + match_bonus, match_rate


def train_breakthrough_model():
    """训练突破性模型"""
    
    logger.info("Stage 7.7: 突破性训练")
    
    # 数据加载
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=32,
        max_samples=1500,
        shuffle=True
    )
    
    model = BreakthroughNet()
    optimizer = optim.Adam(model.parameters(), lr=0.005)
    
    best_match_rate = 0
    
    for epoch in range(25):
        model.train()
        total_loss = 0
        total_match_rate = 0
        
        for state_vec, action_vec, _ in dataloader:
            optimizer.zero_grad()
            
            pred_logits = model(state_vec)
            loss, match_rate = breakthrough_loss(pred_logits, action_vec)
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            total_match_rate += match_rate
        
        avg_loss = total_loss / len(dataloader)
        avg_match_rate = total_match_rate / len(dataloader)
        
        logger.info(f"Epoch {epoch+1:2d}/25 | Loss: {avg_loss:.3f} | 匹配率: {avg_match_rate:.3f}")
        
        if avg_match_rate > best_match_rate:
            best_match_rate = avg_match_rate
            torch.save(model.state_dict(), "models/bc_model_stage7_breakthrough.pth")
            if avg_match_rate > 0.2:
                logger.info(f"★ 突破性匹配率: {avg_match_rate:.3f}")
    
    logger.info(f"最终匹配率: {best_match_rate:.3f}")
    return model, best_match_rate


if __name__ == "__main__":
    model, match_rate = train_breakthrough_model()
    
    if match_rate > 0.2:
        logger.info("🎉 突破成功！匹配率超过20%")
    else:
        logger.info("需要进一步优化")