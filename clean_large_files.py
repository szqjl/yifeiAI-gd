#!/usr/bin/env python3
"""
清理Git仓库中的大文件
"""
import os
import subprocess
import sys

def run_cmd(cmd):
    """执行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def main():
    print("=" * 60)
    print("Git仓库大文件清理工具")
    print("=" * 60)
    
    # 1. 检查当前仓库大小
    print("\n1. 检查仓库大小...")
    stdout, stderr, code = run_cmd("git count-objects -vH")
    if code == 0:
        print(stdout)
    
    # 2. 查找被跟踪的大文件
    print("\n2. 查找被跟踪的大文件（>1MB）...")
    stdout, stderr, code = run_cmd("git ls-files")
    if code == 0:
        large_files = []
        for line in stdout.split('\n'):
            if line.strip():
                filepath = line.strip()
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    if size > 1024 * 1024:  # > 1MB
                        large_files.append((filepath, size))
        
        if large_files:
            large_files.sort(key=lambda x: x[1], reverse=True)
            print(f"\n找到 {len(large_files)} 个大文件：")
            total_size = 0
            for filepath, size in large_files:
                size_mb = size / (1024 * 1024)
                total_size += size
                print(f"  {size_mb:.2f}MB - {filepath}")
            print(f"\n总计: {total_size / (1024 * 1024):.2f}MB")
        else:
            print("未找到被跟踪的大文件")
    
    # 3. 检查模型文件
    print("\n3. 检查模型文件...")
    model_files = []
    if os.path.exists("models"):
        for root, dirs, files in os.walk("models"):
            for f in files:
                if f.endswith(('.pth', '.pkl', '.h5')):
                    filepath = os.path.join(root, f)
                    if os.path.exists(filepath):
                        size = os.path.getsize(filepath)
                        if size > 1024 * 1024:  # > 1MB
                            model_files.append((filepath, size))
    
    if model_files:
        print(f"\n找到 {len(model_files)} 个模型文件（>1MB）：")
        total_size = 0
        for filepath, size in model_files[:20]:  # 只显示前20个
            size_mb = size / (1024 * 1024)
            total_size += size
            print(f"  {size_mb:.2f}MB - {filepath}")
        if len(model_files) > 20:
            print(f"  ... 还有 {len(model_files) - 20} 个文件")
        print(f"\n总计: {total_size / (1024 * 1024):.2f}MB")
    
    # 4. 检查是否被Git跟踪
    print("\n4. 检查模型文件是否被Git跟踪...")
    tracked_models = []
    stdout, stderr, code = run_cmd("git ls-files models/")
    if code == 0 and stdout:
        for line in stdout.split('\n'):
            if line.strip() and line.strip().endswith(('.pth', '.pkl', '.h5')):
                tracked_models.append(line.strip())
    
    if tracked_models:
        print(f"\n⚠️  发现 {len(tracked_models)} 个模型文件被Git跟踪：")
        for f in tracked_models[:10]:
            print(f"  - {f}")
        if len(tracked_models) > 10:
            print(f"  ... 还有 {len(tracked_models) - 10} 个文件")
    else:
        print("✓ 没有模型文件被Git跟踪")
    
    print("\n" + "=" * 60)
    print("清理建议：")
    print("=" * 60)
    print("1. 确保 .gitignore 包含模型文件规则")
    print("2. 从Git跟踪中移除大文件：git rm --cached <file>")
    print("3. 清理Git历史中的大文件（使用git filter-branch或BFG）")
    print("4. 运行 git gc --aggressive 压缩仓库")
    print("=" * 60)

if __name__ == "__main__":
    main()
