#!/usr/bin/env python3
"""
清理Git历史中的大文件
使用git filter-branch清理历史记录
"""
import subprocess
import sys
import os

def run_cmd(cmd, check=True):
    """执行命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
    if check and result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    return True

def main():
    print("=" * 60)
    print("Git历史大文件清理工具")
    print("=" * 60)
    print("\n⚠️  警告：此操作会重写Git历史，需要强制推送")
    print("⚠️  建议：先备份仓库或创建新分支")
    
    response = input("\n是否继续？(yes/no): ")
    if response.lower() != 'yes':
        print("已取消")
        return
    
    # 1. 清理Testscore目录的历史
    print("\n1. 清理Testscore目录的历史...")
    if not run_cmd('git filter-branch --force --index-filter "git rm --cached --ignore-unmatch -r Testscore/" --prune-empty --tag-name-filter cat -- --all'):
        print("清理Testscore失败")
        return
    
    # 2. 清理logs目录中的大文件历史
    print("\n2. 清理logs目录中大文件的历史...")
    if not run_cmd('git filter-branch --force --index-filter "git rm --cached --ignore-unmatch logs/*.log" --prune-empty --tag-name-filter cat -- --all'):
        print("清理logs失败")
        return
    
    # 3. 清理模型文件历史（如果存在）
    print("\n3. 清理模型文件历史...")
    if not run_cmd('git filter-branch --force --index-filter "git rm --cached --ignore-unmatch models/*.pth models/*.pkl models/*.h5" --prune-empty --tag-name-filter cat -- --all'):
        print("清理模型文件失败")
        return
    
    # 4. 清理引用
    print("\n4. 清理引用...")
    run_cmd('git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin', check=False)
    
    # 5. 清理reflog
    print("\n5. 清理reflog...")
    run_cmd('git reflog expire --expire=now --all', check=False)
    
    # 6. 垃圾回收
    print("\n6. 运行垃圾回收...")
    run_cmd('git gc --prune=now --aggressive', check=False)
    
    print("\n" + "=" * 60)
    print("清理完成！")
    print("=" * 60)
    print("\n下一步：")
    print("1. 检查仓库大小: git count-objects -vH")
    print("2. 如果满意，强制推送: git push --force --all")
    print("3. 推送标签: git push --force --tags")
    print("=" * 60)

if __name__ == "__main__":
    main()

