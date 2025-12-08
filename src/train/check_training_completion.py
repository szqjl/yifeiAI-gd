# -*- coding: utf-8 -*-
"""
检查训练是否正常完成
"""

import os
import sys
import torch
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.rl_agent.model import GuandanPolicyNet


def check_training_completion():
    """检查训练是否正常完成"""
    print("="*60)
    print("训练完成检查")
    print("="*60)
    
    # 1. 检查模型文件
    model_path = "models/bc_model_v1.pth"
    if not os.path.exists(model_path):
        print(f"\n[ERROR] 模型文件不存在: {model_path}")
        return False
    
    model_size = os.path.getsize(model_path) / (1024 * 1024)
    model_time = os.path.getmtime(model_path)
    model_time_str = datetime.fromtimestamp(model_time).strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"\n模型文件信息:")
    print(f"  文件路径: {model_path}")
    print(f"  文件大小: {model_size:.2f} MB")
    print(f"  最后修改: {model_time_str}")
    
    # 2. 检查模型结构
    try:
        checkpoint = torch.load(model_path, map_location='cpu')
        
        # 处理不同的模型保存格式
        if isinstance(checkpoint, dict):
            # 新格式：包含 model_state_dict 键的字典
            if 'model_state_dict' in checkpoint:
                model_dict = checkpoint['model_state_dict']
            # 旧格式：直接是 state_dict
            elif any(key.startswith('fc') or key.startswith('strategy') for key in checkpoint.keys()):
                model_dict = checkpoint
            else:
                # 如果字典中没有模型相关的键，尝试使用整个字典
                model_dict = checkpoint
        else:
            # 直接是 state_dict
            model_dict = checkpoint
        
        param_count = sum(p.numel() for p in model_dict.values() if hasattr(p, 'numel'))
        print(f"  参数数量: {param_count:,}")
        print(f"  模型键数量: {len(model_dict)}")
        
        # 检查是否有Dropout层
        has_dropout = 'dropout.weight' in model_dict or any('dropout' in k for k in model_dict.keys())
        print(f"  包含Dropout: {'是' if has_dropout else '否'}")
        
        # 检查是否有策略分类头
        has_strategy_head = 'fc_strategy.weight' in model_dict
        print(f"  包含策略分类头: {'是' if has_strategy_head else '否'}")
        
        print(f"  [OK] 模型文件结构正常")
    except Exception as e:
        print(f"  [ERROR] 模型加载失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False
    
    # 3. 检查训练日志
    log_dir = "training_logs"
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.txt')]
        if log_files:
            # 找到最新的日志文件
            log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
            latest_log = os.path.join(log_dir, log_files[0])
            
            print(f"\n训练日志信息:")
            print(f"  最新日志: {log_files[0]}")
            
            with open(latest_log, 'r', encoding='utf-8') as f:
                log_content = f.read()
                log_lines = log_content.splitlines()
                
            print(f"  日志行数: {len(log_lines)}")
            
            # 检查是否有训练过程输出
            has_epoch = any('Epoch' in line for line in log_lines)
            has_loss = any('Loss' in line for line in log_lines)
            has_model_saved = any('Model saved' in line or '模型已保存' in line for line in log_lines)
            
            print(f"  包含Epoch信息: {'是' if has_epoch else '否'}")
            print(f"  包含Loss信息: {'是' if has_loss else '否'}")
            print(f"  包含保存信息: {'是' if has_model_saved else '否'}")
            
            if has_epoch and has_loss:
                print(f"  [OK] 训练日志包含完整的训练过程")
            elif has_model_saved:
                print(f"  [WARNING] 训练日志显示模型已保存，但缺少训练过程详情")
            else:
                print(f"  [WARNING] 训练日志可能不完整，缺少训练过程信息")
            
            # 显示最后几行
            print(f"\n  日志最后10行:")
            for line in log_lines[-10:]:
                if line.strip():
                    print(f"    {line}")
        else:
            print(f"\n[WARNING] 训练日志目录为空")
    else:
        print(f"\n[WARNING] 训练日志目录不存在")
    
    # 4. 测试模型输出
    print(f"\n模型输出测试:")
    try:
        # 检查是否有策略分类头
        has_strategy_head = 'fc_strategy.weight' in model_dict
        
        model = GuandanPolicyNet(
            input_dim=512,
            hidden_dim=256,
            output_dim=512,
            enable_strategy_head=has_strategy_head
        )
        
        # 加载模型状态，允许部分匹配以兼容不同格式
        try:
            model.load_state_dict(model_dict, strict=True)
        except RuntimeError:
            model.load_state_dict(model_dict, strict=False)
        
        model.eval()
        
        x = torch.randn(1, 512)
        with torch.no_grad():
            y = model(x)
            probs = torch.sigmoid(y)
        
        print(f"  输出概率范围: [{probs.min():.4f}, {probs.max():.4f}]")
        print(f"  输出概率平均: {probs.mean():.4f}")
        print(f"  阈值0.3预测卡牌数: {(probs > 0.3).sum().item()}")
        print(f"  阈值0.2预测卡牌数: {(probs > 0.2).sum().item()}")
        print(f"  阈值0.1预测卡牌数: {(probs > 0.1).sum().item()}")
        
        if probs.mean() < 0.01:
            print(f"  [WARNING] 模型输出概率值非常低，可能训练未完成或有问题")
        elif probs.mean() < 0.1:
            print(f"  [WARNING] 模型输出概率值偏低，可能需要调整阈值")
        else:
            print(f"  [OK] 模型输出概率值正常")
            
    except Exception as e:
        print(f"  [ERROR] 模型测试失败: {e}")
        return False
    
    # 5. 总结
    print(f"\n" + "="*60)
    print("检查总结")
    print("="*60)
    
    if has_epoch and has_loss:
        print("\n[OK] 训练正常完成")
        print("  - 模型文件存在且正常")
        print("  - 训练日志包含完整的训练过程")
        print("  - 模型可以正常加载和运行")
    elif has_model_saved:
        print("\n[WARNING] 训练可能完成，但日志不完整")
        print("  - 模型文件存在且正常")
        print("  - 训练日志显示模型已保存")
        print("  - 但缺少训练过程的详细信息")
        print("  - 建议：检查训练输出是否被正确捕获")
    else:
        print("\n[WARNING] 训练可能未正常完成")
        print("  - 模型文件存在，但训练日志不完整")
        print("  - 缺少训练过程的详细信息")
        print("  - 建议：重新训练并检查训练输出")
    
    print(f"\n" + "="*60)
    
    return has_epoch and has_loss


if __name__ == "__main__":
    check_training_completion()

