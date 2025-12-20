#!/usr/bin/env python3
"""
验证.gitignore配置，确保大文件不会被推送
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

def check_file_ignored(filepath):
    """检查文件是否被.gitignore忽略"""
    stdout, stderr, code = run_cmd(f'git check-ignore -v "{filepath}"')
    return code == 0, stdout

def main():
    print("=" * 60)
    print("验证.gitignore配置 - 确保大文件不会被推送")
    print("=" * 60)
    
    issues = []
    warnings = []
    
    # 1. 检查模型文件
    print("\n1. 检查模型文件...")
    model_files = []
    if os.path.exists("models"):
        for root, dirs, files in os.walk("models"):
            for f in files:
                if f.endswith(('.pth', '.pkl', '.h5')):
                    filepath = os.path.join(root, f).replace('\\', '/')
                    model_files.append(filepath)
    
    if model_files:
        ignored_count = 0
        not_ignored = []
        for f in model_files[:10]:  # 检查前10个
            is_ignored, rule = check_file_ignored(f)
            if is_ignored:
                ignored_count += 1
            else:
                not_ignored.append(f)
        
        if not_ignored:
            issues.append(f"⚠️  发现 {len(not_ignored)} 个模型文件未被忽略: {not_ignored[:3]}")
        else:
            print(f"  ✅ 所有检查的模型文件都被忽略 ({ignored_count}/{min(10, len(model_files))})")
    
    # 2. 检查日志文件
    print("\n2. 检查日志文件...")
    log_files = []
    if os.path.exists("logs"):
        for f in os.listdir("logs"):
            if f.endswith('.log'):
                filepath = f"logs/{f}"
                log_files.append(filepath)
    
    if log_files:
        ignored_count = 0
        not_ignored = []
        for f in log_files[:10]:  # 检查前10个
            is_ignored, rule = check_file_ignored(f)
            if is_ignored:
                ignored_count += 1
            else:
                not_ignored.append(f)
        
        if not_ignored:
            issues.append(f"⚠️  发现 {len(not_ignored)} 个日志文件未被忽略: {not_ignored[:3]}")
        else:
            print(f"  ✅ 所有检查的日志文件都被忽略 ({ignored_count}/{min(10, len(log_files))})")
    
    # 3. 检查Testscore目录
    print("\n3. 检查Testscore目录...")
    if os.path.exists("Testscore"):
        is_ignored, rule = check_file_ignored("Testscore/")
        if is_ignored:
            print(f"  ✅ Testscore目录被忽略 (规则: {rule})")
        else:
            issues.append("⚠️  Testscore目录未被忽略")
    
    # 4. 检查game_records目录
    print("\n4. 检查game_records目录...")
    if os.path.exists("game_records"):
        is_ignored, rule = check_file_ignored("game_records/")
        if is_ignored:
            print(f"  ✅ game_records目录被忽略 (规则: {rule})")
        else:
            warnings.append("⚠️  game_records目录未被忽略（如果包含大文件）")
    
    # 5. 检查当前暂存区
    print("\n5. 检查Git暂存区...")
    stdout, stderr, code = run_cmd("git diff --cached --name-only")
    if code == 0 and stdout:
        staged_files = stdout.split('\n')
        large_staged = []
        for f in staged_files:
            if f and os.path.exists(f):
                size = os.path.getsize(f)
                if size > 1024 * 1024:  # > 1MB
                    large_staged.append((f, size / (1024 * 1024)))
        
        if large_staged:
            issues.append(f"⚠️  暂存区中有 {len(large_staged)} 个大文件: {[f[0] for f in large_staged[:3]]}")
        else:
            print("  ✅ 暂存区中没有大文件")
    
    # 6. 检查工作区大文件
    print("\n6. 检查工作区大文件...")
    stdout, stderr, code = run_cmd("git status --porcelain")
    if code == 0 and stdout:
        untracked = []
        for line in stdout.split('\n'):
            if line.startswith('??'):
                filepath = line[3:].strip()
                if os.path.exists(filepath):
                    size = os.path.getsize(filepath)
                    if size > 1024 * 1024:  # > 1MB
                        is_ignored, rule = check_file_ignored(filepath)
                        if not is_ignored:
                            untracked.append((filepath, size / (1024 * 1024)))
        
        if untracked:
            warnings.append(f"⚠️  工作区中有 {len(untracked)} 个未跟踪的大文件（未被忽略）: {[f[0] for f in untracked[:3]]}")
        else:
            print("  ✅ 工作区中的大文件都被正确忽略")
    
    # 总结
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    
    if issues:
        print("\n❌ 发现问题：")
        for issue in issues:
            print(f"  {issue}")
        print("\n建议：更新.gitignore文件")
    else:
        print("\n✅ 所有检查通过！大文件配置正确")
    
    if warnings:
        print("\n⚠️  警告：")
        for warning in warnings:
            print(f"  {warning}")
    
    print("\n" + "=" * 60)
    print("推送前检查清单：")
    print("=" * 60)
    print("1. 运行此脚本验证配置")
    print("2. 检查 git status 确认没有大文件")
    print("3. 检查 git diff --cached 确认暂存区没有大文件")
    print("4. 确认 .gitignore 规则正确")
    print("=" * 60)

if __name__ == "__main__":
    main()

