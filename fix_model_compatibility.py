#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复模型兼容性问题
解决旧模型架构与新模型架构不匹配的问题
"""

import torch
import torch.nn as nn
import sys
import os
sys.path.append('src')

from rl_agent.model import GuandanPolicyNet, ImprovedGuandanPolicyNet

def analyze_model_file(model_path):
    """分析模型文件的架构"""
    print(f"=== 分析模型文件: {model_path} ===")
    
    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return None
    
    try:
        # 加载模型状态字典（修复PyTorch 2.6安全加载问题）
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        print(f"✅ 模型文件加载成功")
        print(f"📊 检查点键: {list(checkpoint.keys())}")
        
        # 提取状态字典
        if 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
            print("📦 从检查点中提取model_state_dict")
        elif 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
            print("📦 从检查点中提取state_dict")
        elif isinstance(checkpoint, dict) and any(k.endswith('.weight') or k.endswith('.bias') for k in checkpoint.keys()):
            state_dict = checkpoint
            print("📦 检查点本身就是状态字典")
        else:
            print("❌ 无法找到有效的状态字典")
            return None
        
        print(f"📊 模型参数数量: {len(state_dict)}")
        
        # 分析模型架构
        print("\n🔍 模型层结构分析:")
        layer_types = {}
        for key in state_dict.keys():
            layer_name = key.split('.')[0]
            if layer_name not in layer_types:
                layer_types[layer_name] = []
            layer_types[layer_name].append(key)
        
        for layer_name, keys in layer_types.items():
            print(f"  {layer_name}: {len(keys)} 参数")
            if len(keys) <= 4:  # 显示详细信息
                for key in keys:
                    if hasattr(state_dict[key], 'shape'):
                        shape = state_dict[key].shape
                        print(f"    - {key}: {shape}")
                    else:
                        print(f"    - {key}: {type(state_dict[key])}")
        
        # 判断模型类型
        if 'feature_extractor.0.weight' in state_dict:
            model_type = "ImprovedGuandanPolicyNet"
        elif 'fc1.weight' in state_dict:
            model_type = "GuandanPolicyNet"
        else:
            model_type = "Unknown"
        
        print(f"\n🎯 检测到的模型类型: {model_type}")
        return model_type, state_dict
        
    except Exception as e:
        print(f"❌ 模型文件分析失败: {e}")
        return None

def create_compatible_model(model_type, state_dict):
    """根据模型类型创建兼容的模型"""
    print(f"\n=== 创建兼容模型: {model_type} ===")
    
    if model_type == "GuandanPolicyNet":
        # 创建旧架构模型
        model = GuandanPolicyNet(
            input_dim=512,
            hidden_dim=256,
            output_dim=512,
            dropout_rate=0.1,
            strategy_num_classes=7,
            enable_strategy_head=True
        )
        print("✅ 创建GuandanPolicyNet模型")
        
    elif model_type == "ImprovedGuandanPolicyNet":
        # 创建新架构模型
        model = ImprovedGuandanPolicyNet(
            input_dim=512,
            hidden_dim=256,
            output_dim=512,
            dropout_rate=0.1,
            strategy_num_classes=7,
            enable_strategy_head=True,
            attention_heads=8,
            enable_strategy_tasks=True
        )
        print("✅ 创建ImprovedGuandanPolicyNet模型")
        
    else:
        print(f"❌ 未知的模型类型: {model_type}")
        return None
    
    try:
        # 加载状态字典
        model.load_state_dict(state_dict)
        print("✅ 模型状态字典加载成功")
        return model
    except Exception as e:
        print(f"❌ 模型状态字典加载失败: {e}")
        return None

def convert_old_to_new_model(old_state_dict):
    """将旧模型转换为新模型架构"""
    print("\n=== 转换旧模型到新架构 ===")
    
    # 创建新模型
    new_model = ImprovedGuandanPolicyNet(
        input_dim=512,
        hidden_dim=256,
        output_dim=512,
        dropout_rate=0.1,
        strategy_num_classes=7,
        enable_strategy_head=True,
        attention_heads=8,
        enable_strategy_tasks=True
    )
    
    # 获取新模型的状态字典
    new_state_dict = new_model.state_dict()
    
    # 映射旧参数到新参数
    param_mapping = {
        # 特征提取层映射
        'fc1.weight': 'feature_extractor.0.weight',
        'fc1.bias': 'feature_extractor.0.bias',
        'fc2.weight': 'feature_extractor.4.weight',
        'fc2.bias': 'feature_extractor.4.bias',
        
        # 输出层映射
        'fc3.weight': 'action_head.weight',
        'fc3.bias': 'action_head.bias',
        'fc_strategy.weight': 'strategy_head.weight',
        'fc_strategy.bias': 'strategy_head.bias',
    }
    
    # 复制可映射的参数
    mapped_count = 0
    for old_key, new_key in param_mapping.items():
        if old_key in old_state_dict and new_key in new_state_dict:
            if old_state_dict[old_key].shape == new_state_dict[new_key].shape:
                new_state_dict[new_key] = old_state_dict[old_key].clone()
                mapped_count += 1
                print(f"✅ 映射参数: {old_key} -> {new_key}")
            else:
                print(f"⚠️ 参数形状不匹配: {old_key} {old_state_dict[old_key].shape} -> {new_key} {new_state_dict[new_key].shape}")
    
    print(f"📊 成功映射 {mapped_count}/{len(param_mapping)} 个参数")
    
    # 初始化未映射的参数
    unmapped_params = []
    for key in new_state_dict.keys():
        if key not in param_mapping.values():
            unmapped_params.append(key)
    
    print(f"🔧 需要初始化的新参数: {len(unmapped_params)} 个")
    for param in unmapped_params[:10]:  # 只显示前10个
        print(f"  - {param}: {new_state_dict[param].shape}")
    if len(unmapped_params) > 10:
        print(f"  ... 还有 {len(unmapped_params) - 10} 个参数")
    
    # 加载转换后的状态字典
    try:
        new_model.load_state_dict(new_state_dict)
        print("✅ 转换后的模型加载成功")
        return new_model
    except Exception as e:
        print(f"❌ 转换后的模型加载失败: {e}")
        return None

def save_converted_model(model, output_path):
    """保存转换后的模型"""
    try:
        torch.save(model.state_dict(), output_path)
        print(f"✅ 转换后的模型已保存: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 模型保存失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 模型兼容性修复工具")
    print("=" * 50)
    
    # 分析现有模型
    model_path = "models/bc_model_stage6_enhanced.pth"
    result = analyze_model_file(model_path)
    
    if result is None:
        print("❌ 无法分析模型文件，退出")
        return
    
    model_type, state_dict = result
    
    if model_type == "GuandanPolicyNet":
        print("\n🔄 检测到旧架构模型，开始转换...")
        
        # 转换模型
        new_model = convert_old_to_new_model(state_dict)
        
        if new_model is not None:
            # 保存转换后的模型
            output_path = "models/bc_model_stage6_enhanced_converted.pth"
            if save_converted_model(new_model, output_path):
                print(f"\n🎉 模型转换成功！")
                print(f"📁 原模型: {model_path}")
                print(f"📁 新模型: {output_path}")
                print(f"💡 请在GUI中使用新模型文件进行分析")
            else:
                print("❌ 模型保存失败")
        else:
            print("❌ 模型转换失败")
    
    elif model_type == "ImprovedGuandanPolicyNet":
        print("\n✅ 检测到新架构模型，无需转换")
        
        # 测试模型加载
        model = create_compatible_model(model_type, state_dict)
        if model is not None:
            print("✅ 模型可以正常加载和使用")
        else:
            print("❌ 模型加载失败，可能存在其他问题")
    
    else:
        print(f"❌ 未知的模型类型: {model_type}")

if __name__ == "__main__":
    main()