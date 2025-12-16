# -*- coding: utf-8 -*-
"""
GPU设备选择工具
自动检测并选择兼容的GPU设备，跳过不兼容的旧GPU
"""

import os
import torch


def select_compatible_device(force_cpu=False):
    """
    选择兼容的GPU设备，跳过CUDA capability < 3.7的旧GPU
    
    Args:
        force_cpu: 是否强制使用CPU
        
    Returns:
        torch.device: 选择的设备
        int or None: 兼容的GPU ID（如果使用GPU），None表示使用CPU
    """
    if force_cpu or os.environ.get('FORCE_CPU', '0') == '1':
        print("[信息] 强制使用CPU训练（FORCE_CPU=1）")
        if 'CUDA_VISIBLE_DEVICES' in os.environ:
            del os.environ['CUDA_VISIBLE_DEVICES']
        return torch.device("cpu"), None
    
    if not torch.cuda.is_available():
        print("[信息] CUDA不可用，使用CPU训练")
        return torch.device("cpu"), None
    
    compatible_gpu_id = None
    
    try:
        device_count = torch.cuda.device_count()
        print(f"[信息] 检测到 {device_count} 个GPU设备")
        
        for i in range(device_count):
            try:
                props = torch.cuda.get_device_properties(i)
                capability = props.major * 10 + props.minor
                capability_str = f"{props.major}.{props.minor}"
                
                print(f"[信息] GPU {i}: {props.name}")
                print(f"        CUDA Capability: {capability_str}")
                print(f"        显存: {props.total_memory / 1024**3:.2f} GB")
                
                if capability < 37:  # CUDA capability < 3.7
                    print(f"       [跳过] 此GPU太旧，PyTorch不支持（需要 >= 3.7）")
                else:
                    if compatible_gpu_id is None:
                        compatible_gpu_id = i
                        print(f"       [✓] 此GPU兼容，将被使用")
                    else:
                        print(f"       [备用] 此GPU也可用")
            except Exception as e:
                print(f"       [错误] 无法获取GPU {i} 的信息: {e}")
        
        if compatible_gpu_id is None:
            print("[警告] 未找到兼容的GPU（CUDA capability >= 3.7），将使用CPU训练")
            if 'CUDA_VISIBLE_DEVICES' in os.environ:
                del os.environ['CUDA_VISIBLE_DEVICES']
            return torch.device("cpu"), None
        else:
            # 直接使用兼容的GPU ID
            # 注意：如果CUDA_VISIBLE_DEVICES已经设置，这里的ID可能需要调整
            # 但为了简单，我们直接使用检测到的ID
            device = torch.device(f"cuda:{compatible_gpu_id}")
            try:
                gpu_name = torch.cuda.get_device_name(compatible_gpu_id)
                print(f"[信息] 已选择GPU {compatible_gpu_id}: {gpu_name}")
            except Exception as e:
                print(f"[信息] 已选择GPU {compatible_gpu_id}（无法获取名称: {e}）")
            return device, compatible_gpu_id
            
    except Exception as e:
        print(f"[警告] GPU检测过程中出错: {e}")
        print(f"[警告] 将使用CPU训练以避免兼容性问题")
        if 'CUDA_VISIBLE_DEVICES' in os.environ:
            del os.environ['CUDA_VISIBLE_DEVICES']
        return torch.device("cpu"), None


def get_device_info():
    """
    获取当前设备信息
    
    Returns:
        dict: 设备信息字典
    """
    info = {
        'cuda_available': torch.cuda.is_available(),
        'device_count': 0,
        'devices': []
    }
    
    if torch.cuda.is_available():
        info['cuda_version'] = torch.version.cuda
        info['cudnn_version'] = torch.backends.cudnn.version()
        info['device_count'] = torch.cuda.device_count()
        
        for i in range(torch.cuda.device_count()):
            try:
                props = torch.cuda.get_device_properties(i)
                capability = props.major * 10 + props.minor
                device_info = {
                    'id': i,
                    'name': props.name,
                    'capability': f"{props.major}.{props.minor}",
                    'capability_value': capability,
                    'memory_gb': props.total_memory / 1024**3,
                    'compatible': capability >= 37
                }
                info['devices'].append(device_info)
            except Exception as e:
                info['devices'].append({
                    'id': i,
                    'error': str(e)
                })
    
    return info

