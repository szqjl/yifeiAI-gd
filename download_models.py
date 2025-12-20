#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模型文件下载工具
从外部存储下载模型文件到本地
"""
import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional

try:
    import requests
except ImportError:
    print("❌ 需要安装 requests 库: pip install requests")
    sys.exit(1)


# 模型文件清单（存储在Git仓库中）
# 注意：实际使用时需要更新下载链接
MODEL_MANIFEST = {
    # 必需模型（训练/评估必需）
    "bc_model_stage5_balanced.pth": {
        "url": "",  # 需要填写实际下载链接
        "size": 2800000,  # 2.8MB
        "md5": "",  # 可选：用于校验
        "description": "Stage5平衡训练模型",
        "required": True
    },
    "bc_model_stage6_enhanced.pth": {
        "url": "",
        "size": 14480000,  # 14.5MB
        "md5": "",
        "description": "Stage6增强模型",
        "required": False
    },
    # 可以继续添加更多模型...
}

# 从配置文件加载（如果存在）
MANIFEST_FILE = "models_manifest.json"
if os.path.exists(MANIFEST_FILE):
    try:
        with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
            custom_manifest = json.load(f)
            MODEL_MANIFEST.update(custom_manifest)
    except Exception as e:
        print(f"⚠️  加载模型清单失败: {e}")


def calculate_md5(filepath: str) -> str:
    """计算文件MD5"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def verify_file(filepath: str, expected_md5: Optional[str] = None) -> bool:
    """验证文件完整性"""
    if not expected_md5:
        return True
    
    if not os.path.exists(filepath):
        return False
    
    actual_md5 = calculate_md5(filepath)
    return actual_md5.lower() == expected_md5.lower()


def download_file(url: str, filepath: Path, expected_size: Optional[int] = None) -> bool:
    """下载文件"""
    try:
        print(f"📥 下载: {filepath.name}...")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        if expected_size and total_size != expected_size:
            print(f"⚠️  警告: 文件大小不匹配 (期望: {expected_size}, 实际: {total_size})")
        
        downloaded = 0
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r   进度: {progress:.1f}% ({downloaded}/{total_size} bytes)", end='')
        
        print(f"\n✅ 下载完成: {filepath}")
        return True
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return False


def download_model(model_name: str, force: bool = False) -> bool:
    """下载单个模型文件"""
    if model_name not in MODEL_MANIFEST:
        print(f"❌ 模型 {model_name} 不在清单中")
        print(f"   可用模型: {', '.join(MODEL_MANIFEST.keys())}")
        return False
    
    model_info = MODEL_MANIFEST[model_name]
    local_path = Path("models") / model_name
    
    # 检查文件是否已存在
    if local_path.exists() and not force:
        # 验证文件完整性
        if verify_file(str(local_path), model_info.get("md5")):
            print(f"✅ 模型已存在且完整: {local_path}")
            return True
        else:
            print(f"⚠️  模型文件存在但校验失败，重新下载...")
    
    # 检查URL是否配置
    url = model_info.get("url", "")
    if not url:
        print(f"❌ 模型 {model_name} 的下载链接未配置")
        print(f"   请在 {MANIFEST_FILE} 或 download_models.py 中配置下载链接")
        return False
    
    # 下载文件
    if download_file(url, local_path, model_info.get("size")):
        # 验证文件
        if model_info.get("md5"):
            if verify_file(str(local_path), model_info["md5"]):
                print(f"✅ 文件校验通过")
                return True
            else:
                print(f"❌ 文件校验失败，可能下载不完整")
                return False
        return True
    
    return False


def download_all_models(required_only: bool = False) -> Dict[str, bool]:
    """下载所有模型文件"""
    print("=" * 60)
    print("模型文件下载工具")
    print("=" * 60)
    
    results = {}
    
    for model_name, model_info in MODEL_MANIFEST.items():
        if required_only and not model_info.get("required", False):
            continue
        
        print(f"\n[{model_name}]")
        print(f"  描述: {model_info.get('description', 'N/A')}")
        print(f"  大小: {model_info.get('size', 0) / (1024*1024):.2f} MB")
        
        results[model_name] = download_model(model_name)
    
    # 统计
    print("\n" + "=" * 60)
    success = sum(1 for v in results.values() if v)
    failed = len(results) - success
    print(f"下载完成: 成功 {success}, 失败 {failed}")
    print("=" * 60)
    
    return results


def list_models():
    """列出所有可用模型"""
    print("=" * 60)
    print("可用模型列表")
    print("=" * 60)
    
    required = []
    optional = []
    
    for model_name, model_info in MODEL_MANIFEST.items():
        info = {
            "name": model_name,
            "size": f"{model_info.get('size', 0) / (1024*1024):.2f} MB",
            "description": model_info.get('description', 'N/A'),
            "exists": os.path.exists(f"models/{model_name}")
        }
        
        if model_info.get("required", False):
            required.append(info)
        else:
            optional.append(info)
    
    if required:
        print("\n📌 必需模型:")
        for info in required:
            status = "✅" if info["exists"] else "❌"
            print(f"  {status} {info['name']} ({info['size']}) - {info['description']}")
    
    if optional:
        print("\n📦 可选模型:")
        for info in optional:
            status = "✅" if info["exists"] else "❌"
            print(f"  {status} {info['name']} ({info['size']}) - {info['description']}")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="模型文件下载工具")
    parser.add_argument("model", nargs="?", help="要下载的模型文件名（不指定则下载所有）")
    parser.add_argument("--list", action="store_true", help="列出所有可用模型")
    parser.add_argument("--required-only", action="store_true", help="只下载必需模型")
    parser.add_argument("--force", action="store_true", help="强制重新下载已存在的模型")
    
    args = parser.parse_args()
    
    if args.list:
        list_models()
    elif args.model:
        download_model(args.model, force=args.force)
    else:
        download_all_models(required_only=args.required_only)


if __name__ == "__main__":
    main()

