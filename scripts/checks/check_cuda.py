# -*- coding: utf-8 -*-
"""检查CUDA是否可用"""
import torch

print("="*60)
print("PyTorch CUDA 检查")
print("="*60)
print(f"PyTorch版本: {torch.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA版本: {torch.version.cuda}")
    print(f"cuDNN版本: {torch.backends.cudnn.version()}")
    print(f"GPU数量: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"  显存: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
else:
    print("CUDA不可用，将使用CPU训练")
print("="*60)
