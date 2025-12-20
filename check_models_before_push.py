#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查模型文件是否会被Git推送
在其他电脑上运行此脚本，确保模型文件不会被意外推送
"""
import os
import subprocess
import sys

def run_git_command(cmd):
    """执行git命令"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        return result.stdout.strip()
    except Exception as e:
        print(f"错误执行命令: {cmd}")
        print(f"错误信息: {e}")
        return ""

def check_models_in_git():
    """检查models/文件夹中的文件是否被Git跟踪"""
    print("=" * 60)
    print("检查模型文件是否会被Git推送")
    print("=" * 60)
    print()
    
    # 1. 检查.gitignore是否存在
    if not os.path.exists('.gitignore'):
        print("❌ 警告: .gitignore 文件不存在！")
        print("   请先执行: git pull origin main")
        return False
    
    print("✅ .gitignore 文件存在")
    
    # 2. 检查models/文件夹中的文件
    models_dir = 'models'
    if not os.path.exists(models_dir):
        print(f"✅ {models_dir}/ 文件夹不存在，无需检查")
        return True
    
    print(f"\n检查 {models_dir}/ 文件夹...")
    
    # 3. 检查是否有模型文件被Git跟踪
    tracked_files = run_git_command('git ls-files models/')
    if tracked_files:
        print("❌ 发现被Git跟踪的模型文件:")
        for line in tracked_files.split('\n'):
            if line.strip():
                print(f"   - {line}")
        print("\n⚠️  警告: 这些文件会被推送到远程仓库！")
        print("\n解决方案:")
        print("1. 确保已拉取最新的 .gitignore:")
        print("   git pull origin main")
        print("2. 从Git中移除这些文件（但保留本地文件）:")
        print("   git rm --cached models/*")
        print("3. 提交更改:")
        print("   git commit -m '移除模型文件跟踪'")
        return False
    else:
        print("✅ 没有模型文件被Git跟踪")
    
    # 4. 检查是否有模型文件在暂存区
    staged_files = run_git_command('git diff --cached --name-only -- models/')
    if staged_files:
        print("❌ 发现暂存区的模型文件:")
        for line in staged_files.split('\n'):
            if line.strip():
                print(f"   - {line}")
        print("\n⚠️  警告: 这些文件会被提交！")
        print("\n解决方案:")
        print("   git reset HEAD models/")
        return False
    else:
        print("✅ 没有模型文件在暂存区")
    
    # 5. 检查未跟踪的模型文件（这些应该被忽略）
    untracked_files = run_git_command('git status --porcelain models/')
    if untracked_files:
        print("\n📋 未跟踪的模型文件（这些会被.gitignore忽略，正常）:")
        for line in untracked_files.split('\n'):
            if line.strip() and line.startswith('??'):
                print(f"   - {line[3:]}")
    
    print("\n" + "=" * 60)
    print("✅ 检查完成：模型文件不会被推送")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        success = check_models_in_git()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)

