"""
Stage 7.6: 极简训练 - 专门针对0卡牌和1卡牌情况
基于数据分析：55%是0卡牌，30%是1卡牌
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleNet(nn.Module):
    """极简网络"""
    
    def __init__(self):
        super().__init__()
        
        self.net = nn.Sequential(
            nn.Linear(512, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 512)
        )
        
    def forward(self, x):
        return self.net(x)


def simple_loss(pred_logits, target_actions):
    """极简损失函数"""
    batch_size = pred_logits.size(0)
    
    total_loss = 0
    exact_matches = 0
    
    for i in range(batch_size):
        true_action = target_actions[i]
        true_count = int(true_action.sum().item())
        
        if true_count == 0:
            # 0卡牌：惩罚任何正预测
            pred_probs = torch.sigmoid(pred_logits[i])
            loss = pred_probs.sum() * 10  # 强惩罚
            
            # 检查是否全部预测为0
            with torch.no_grad():
                if pred_probs.max() < 0.1:  # 所有概率都很低
                    exact_matches += 1
                
        elif true_count == 1:
            # 1卡牌：找到概率最高的位置
            pred_probs = torch.sigmoid(pred_logits[i])
            max_idx = pred_probs.argmax()
            
            pred_action = torch.zeros_like(true_action)
            pred_action[max_idx] = 1.0
            
            loss = nn.functional.binary_cross_entropy(pred_action, true_action) * 100
            
            with torch.no_grad():
                if torch.equal(pred_action, true_action):
                    exact_matches += 1
        else:
            # 多卡牌：使用Top-K
            _, top_k_indices = torch.topk(pred_logits[i], true_count)
            pred_action = torch.zeros_like(true_action)
            pred_action[top_k_indices] = 1.0
            
            loss = nn.functional.binary_cross_entropy(pred_action, true_action) * 100
            
            with torch.no_grad():
                if torch.equal(pred_action, true_action):
                    exact_matches += 1
        
        total_loss += loss
    
    avg_loss = total_loss / batch_size
    match_rate = exact_matches / batch_size
    
    # 精确匹配奖励
    match_bonus = -200 * match_rate
    
    return avg_loss + match_bonus, match_rate


def train_simple_model():
    """训练极简模型"""
    
    logger.info("Stage 7.6: 极简训练")
    
    # 数据加载
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=32,
        max_samples=1000,
        shuffle=True
    )
    
    model = SimpleNet()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    best_match_rate = 0
    
    for epoch in range(30):
        model.train()
        total_loss = 0
        total_match_rate = 0
        
        for state_vec, action_vec, _ in dataloader:
            optimizer.zero_grad()
            
            pred_logits = model(state_vec)
            loss, match_rate = simple_loss(pred_logits, action_vec)
            
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            total_match_rate += match_rate
        
        avg_loss = total_loss / len(dataloader)
        avg_match_rate = total_match_rate / len(dataloader)
        
        logger.info(f"Epoch {epoch+1:2d}/30 | Loss: {avg_loss:.2f} | 匹配率: {avg_match_rate:.3f}")
        
        if avg_match_rate > best_match_rate:
            best_match_rate = avg_match_rate
            torch.save(model.state_dict(), "models/bc_model_stage7_simple.pth")
            if avg_match_rate > 0:
                logger.info(f"★ 匹配率: {avg_match_rate:.3f}")
    
    logger.info(f"最佳匹配率: {best_match_rate:.3f}")
    
    # 快速测试
    model.eval()
    test_match_rate = 0
    test_batches = 0
    
    with torch.no_grad():
        for state_vec, action_vec, _ in dataloader:
            if test_batches >= 5:  # 只测试5个批次
                break
            
            pred_logits = model(state_vec)
            _, match_rate = simple_loss(pred_logits, action_vec)
            test_match_rate += match_rate
            test_batches += 1
    
    final_match_rate = test_match_rate / test_batches
    logger.info(f"测试匹配率: {final_match_rate:.3f}")
    
    return model


if __name__ == "__main__":
    model = train_simple_model()