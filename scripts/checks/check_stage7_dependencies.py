#!/usr/bin/env python3
"""
Stage 7 依赖检查和安装脚本
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 需要Python 3.8或更高版本")
        return False
    
    print("✅ Python版本符合要求")
    return True

def check_package(package_name, import_name=None):
    """检查包是否已安装"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        if hasattr(module, '__version__'):
            version = module.__version__
            print(f"✅ {package_name}: {version}")
        else:
            print(f"✅ {package_name}: 已安装")
        return True
    except ImportError:
        print(f"❌ {package_name}: 未安装")
        return False

def install_package(package_name):
    """安装包"""
    print(f"正在安装 {package_name}...")
    try:
        if package_name == "torch":
            # 安装CPU版本的PyTorch
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "torch", "--index-url", "https://download.pytorch.org/whl/cpu"
            ])
        else:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_name
            ])
        print(f"✅ {package_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package_name} 安装失败: {e}")
        return False

def check_directories():
    """检查必要的目录"""
    directories = ["game_records", "models", "training_logs"]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"✅ 目录 {dir_name}: 存在")
        else:
            if dir_name == "game_records":
                print(f"❌ 目录 {dir_name}: 不存在 (需要训练数据)")
                return False
            else:
                print(f"⚠️  目录 {dir_name}: 不存在，将自动创建")
                dir_path.mkdir(exist_ok=True)
                print(f"✅ 目录 {dir_name}: 已创建")
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("Stage 7 依赖检查")
    print("=" * 50)
    
    # 检查Python版本
    if not check_python_version():
        return False
    
    print("\n检查依赖包...")
    
    # 需要的包
    required_packages = [
        ("torch", "torch"),
        ("numpy", "numpy"),
    ]
    
    # 标准库包
    stdlib_packages = [
        ("json", "json"),
        ("pathlib", "pathlib"),
        ("logging", "logging"),
        ("typing", "typing"),
        ("datetime", "datetime"),
    ]
    
    missing_packages = []
    
    # 检查必需包
    for package_name, import_name in required_packages:
        if not check_package(package_name, import_name):
            missing_packages.append(package_name)
    
    # 检查标准库
    print("\n检查标准库...")
    for package_name, import_name in stdlib_packages:
        check_package(package_name, import_name)
    
    # 安装缺失的包
    if missing_packages:
        print(f"\n需要安装 {len(missing_packages)} 个包...")
        
        install_all = input("是否安装所有缺失的包? (y/n): ").lower().strip()
        
        if install_all == 'y':
            for package in missing_packages:
                if not install_package(package):
                    print(f"❌ 无法安装 {package}")
                    return False
        else:
            print("请手动安装缺失的包:")
            for package in missing_packages:
                if package == "torch":
                    print(f"  pip install torch --index-url https://download.pytorch.org/whl/cpu")
                else:
                    print(f"  pip install {package}")
            return False
    
    print("\n检查目录...")
    if not check_directories():
        return False
    
    print("\n最终验证...")
    try:
        import torch
        import numpy as np
        
        print(f"✅ PyTorch: {torch.__version__}")
        print(f"✅ NumPy: {np.__version__}")
        print(f"✅ 设备: {torch.device('cpu')}")
        
        # 测试基本功能
        x = torch.randn(2, 3)
        y = np.array([1, 2, 3])
        print("✅ 基本功能测试通过")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ 所有依赖检查通过！")
    print("✅ Stage 7 环境已就绪")
    print("=" * 50)
    
    print("\n下一步:")
    print("1. 运行训练: python src/train/stage7_robust_training.py")
    print("2. 或使用脚本: QUICK_START_STAGE7.bat")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n❌ 依赖检查失败")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)