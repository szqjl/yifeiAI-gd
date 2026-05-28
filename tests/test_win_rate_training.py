"""
测试胜率导向训练
"""

import torch
import torch.nn as nn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("开始胜率导向训练测试...")

# 简化的胜率导向网络
class SimpleWinRateNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Linear(512, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        self.action_head = nn.Linear(32, 512)
        self.win_rate_head = nn.Sequential(
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        features = self.features(x)
        return {
            'action_logits': self.action_head(features),
            'win_rate': self.win_rate_head(features)
        }

def test_win_rate_training():
    logger.info("测试胜率导向训练...")
    
    # 加载数据
    import sys
    sys.path.append('src/train')
    from simple_data_loader import create_simple_dataloader
    
    dataloader = create_simple_dataloader(
        data_dir="game_records",
        batch_size=16,
        max_samples=200,
        shuffle=True
    )
    
    model = SimpleWinRateNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    logger.info(f"数据加载成功，样本数: {len(dataloader.dataset)}")
    
    # 训练几个epoch
    for epoch in range(5):
        total_loss = 0
        exact_matches = 0
        total_samples = 0
        
        for state_vec, action_vec, _ in dataloader:
            optimizer.zero_grad()
            
            predictions = model(state_vec)
            
            # 动作损失
            action_probs = torch.sigmoid(predictions['action_logits'])
            action_loss = nn.functional.binary_cross_entropy(action_probs, action_vec)
            
            # 模拟胜率损失
            fake_win_rate = torch.rand(state_vec.size(0), 1)
            win_rate_loss = nn.functional.mse_loss(predictions['win_rate'], fake_win_rate)
            
            total_batch_loss = action_loss + win_rate_loss * 0.5
            
            total_batch_loss.backward()
            optimizer.step()
            
            total_loss += total_batch_loss.item()
            
            # 计算匹配率
            for i in range(action_vec.size(0)):
                true_count = int(action_vec[i].sum().item())
                
                if true_count == 0:
                    if action_probs[i].max() < 0.3:
                        exact_matches += 1
                else:
                    _, top_k_indices = torch.topk(action_probs[i], true_count)
                    pred_action = torch.zeros_like(action_vec[i])
                    pred_action[top_k_indices] = 1.0
                    
                    if torch.equal(pred_action, action_vec[i]):
                        exact_matches += 1
                
                total_samples += 1
        
        avg_loss = total_loss / len(dataloader)
        match_rate = exact_matches / total_samples
        
        logger.info(f"Epoch {epoch+1}/5 | Loss: {avg_loss:.3f} | 匹配率: {match_rate:.3f}")
    
    logger.info("胜率导向训练测试完成")
    return match_rate

if __name__ == "__main__":
    final_match_rate = test_win_rate_training()
    print(f"最终匹配率: {final_match_rate:.3f}")