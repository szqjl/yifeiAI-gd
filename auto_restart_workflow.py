"""自动重启工作流脚本
工作流结束后，自动评估、改进、重启，循环直到达成目标
"""
import json
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

def check_workflow_status():
    """检查工作流状态"""
    status_file = Path("models/m1_workflow_status.json")
    if not status_file.exists():
        return None
    
    with open(status_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_training_results():
    """分析训练结果，识别问题"""
    training_file = Path("models/bc_model_stage7_optimized_training_history.json")
    if not training_file.exists():
        return None
    
    with open(training_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    if not isinstance(history, list) or len(history) == 0:
        return None
    
    latest = history[-1]
    issues = []
    improvements = []
    
    # 检查预测卡牌数
    pred_cards = latest.get('avg_predicted_cards', 0)
    if pred_cards >= 512:
        issues.append("模型预测了所有512张卡牌，阈值设置可能无效")
        improvements.append("进一步降低阈值范围，或使用更小的阈值系数")
    
    # 检查预测比例
    pred_ratio = latest.get('prediction_ratio', 0)
    if pred_ratio > 10:
        issues.append(f"预测比例过高（{pred_ratio:.2f}倍）")
        improvements.append("增加过度预测惩罚或降低阈值")
    
    # 检查损失值
    loss = latest.get('total_loss', 0)
    if loss > 10000:
        issues.append(f"损失值仍然较高（{loss:,.2f}）")
        improvements.append("调整损失函数参数或学习率")
    
    return {
        'issues': issues,
        'improvements': improvements,
        'metrics': {
            'pred_cards': pred_cards,
            'pred_ratio': pred_ratio,
            'loss': loss,
            'true_cards': latest.get('avg_true_cards', 0)
        }
    }

def improve_training_code(analysis):
    """根据分析结果改进训练代码"""
    if not analysis or not analysis.get('issues'):
        return False
    
    print("\n" + "="*60)
    print("根据分析结果改进训练代码...")
    print("="*60)
    
    # 读取训练代码
    code_file = Path("src/train/stage7_optimized_training.py")
    if not code_file.exists():
        print("错误：找不到训练代码文件")
        return False
    
    with open(code_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    modified = False
    
    # 如果预测了所有卡牌，进一步降低阈值
    if analysis['metrics']['pred_cards'] >= 512:
        print("问题：模型预测了所有512张卡牌")
        print("改进：进一步降低阈值范围")
        
        # 查找阈值计算代码
        old_threshold = "threshold = torch.clamp(base_threshold * 0.01, 0.001, 0.1)"
        new_threshold = "threshold = torch.clamp(base_threshold * 0.001, 0.0001, 0.01)"  # 进一步缩小
        
        if old_threshold in code:
            code = code.replace(old_threshold, new_threshold)
            modified = True
            print("  [OK] 已将阈值范围从0.001-0.1缩小到0.0001-0.01")
    
    # 如果预测比例过高，增加惩罚
    if analysis['metrics']['pred_ratio'] > 10:
        print(f"问题：预测比例过高（{analysis['metrics']['pred_ratio']:.2f}倍）")
        print("改进：增加过度预测惩罚系数")
        
        # 查找惩罚参数（支持多种格式）
        penalty_patterns = [
            ("over_prediction_penalty=1000.0", "over_prediction_penalty=5000.0"),
            ("over_prediction_penalty=57665.0390625", "over_prediction_penalty=5000.0"),
            ("over_prediction_penalty=576650.390625", "over_prediction_penalty=5000.0"),
        ]
        
        for old_penalty, new_penalty in penalty_patterns:
            if old_penalty in code:
                code = code.replace(old_penalty, new_penalty)
                modified = True
                print(f"  [OK] 已将过度预测惩罚更新为5000.0")
                break
    
    # 如果损失值仍然较高，调整学习率
    if analysis['metrics']['loss'] > 10000:
        print(f"问题：损失值仍然较高（{analysis['metrics']['loss']:,.2f}）")
        print("改进：降低学习率")
        
        # 查找学习率
        old_lr = "learning_rate: float = 0.00005"
        new_lr = "learning_rate: float = 0.00001"  # 降低学习率
        
        if old_lr in code:
            code = code.replace(old_lr, new_lr)
            modified = True
            print("  [OK] 已将学习率从0.00005降低到0.00001")
    
    if modified:
        # 备份原文件
        backup_file = code_file.with_suffix('.py.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
        with open(backup_file, 'w', encoding='utf-8') as f:
            with open(code_file, 'r', encoding='utf-8') as orig:
                f.write(orig.read())
        print(f"  [OK] 已备份原文件到: {backup_file.name}")
        
        # 保存修改后的代码
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        print("  [OK] 训练代码已更新")
        return True
    else:
        print("  ⚠ 未找到需要修改的代码，可能需要手动调整")
        return False

def restart_workflow():
    """重启工作流"""
    print("\n" + "="*60)
    print("重启工作流...")
    print("="*60)
    
    cmd = [
        sys.executable,
        "src/train/m1_training_workflow.py",
        "--max_iterations", "10",
        "--target_win_rate", "0.50",
        "--min_games", "50",
        "--server_path", r"D:\GDAI\server\windows\guandan_offline_v1006.exe"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    print("工作流将在后台运行...")
    
    # 在后台启动工作流
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    print(f"工作流进程已启动，PID: {process.pid}")
    print("提示：运行 'python monitor_workflow_progress.py' 可查看进度")
    
    return process

def main():
    """主循环：检查状态 -> 分析 -> 改进 -> 重启"""
    print("="*60)
    print("M1训练工作流自动重启系统")
    print("="*60)
    print("功能：自动检测工作流状态，评估结果，改进代码，重启训练")
    print("目标：M1战胜client（胜率 > 50%）")
    print("="*60)
    
    cycle = 0
    max_cycles = 100  # 最大循环次数，防止无限循环
    
    while cycle < max_cycles:
        cycle += 1
        print(f"\n{'='*60}")
        print(f"循环 {cycle}/{max_cycles}")
        print(f"{'='*60}")
        
        # 1. 检查工作流状态
        print("\n1. 检查工作流状态...")
        status = check_workflow_status()
        
        if not status:
            print("  ⚠ 工作流状态文件不存在，可能未启动")
            print("  启动新工作流...")
            restart_workflow()
            print("\n等待工作流完成...")
            time.sleep(300)  # 等待5分钟
            continue
        
        current_status = status.get('status')
        current_iteration = status.get('current_iteration', 0)
        max_iterations = status.get('max_iterations', 10)
        success = status.get('success', False)
        
        print(f"  状态: {current_status}")
        print(f"  迭代: {current_iteration}/{max_iterations}")
        print(f"  成功: {'是' if success else '否'}")
        
        # 如果工作流还在运行，等待
        if current_status == 'running':
            print("\n工作流正在运行中，等待完成...")
            print("提示：运行 'python monitor_workflow_progress.py' 可查看实时进度")
            time.sleep(300)  # 等待5分钟后再检查
            continue
        
        # 如果工作流已完成
        if current_status == 'completed':
            print("\n2. 工作流已完成，分析训练结果...")
            
            # 检查是否成功
            if success:
                print("\n" + "=" * 60)
                print("=" * 60)
                print("目标达成！M1已能战胜client！")
                print("=" * 60)
                print("=" * 60)
                print(f"最终胜率: {status.get('win_rate', 0)*100:.2f}%")
                print(f"迭代次数: {current_iteration}")
                print("="*60)
                break
            
            # 如果未成功，分析并改进
            print("  目标未达成，分析训练结果...")
            analysis = analyze_training_results()
            
            if analysis:
                print(f"\n  发现 {len(analysis['issues'])} 个问题:")
                for i, issue in enumerate(analysis['issues'], 1):
                    print(f"    {i}. {issue}")
                
                print(f"\n  改进建议:")
                for i, improvement in enumerate(analysis['improvements'], 1):
                    print(f"    {i}. {improvement}")
                
                print("\n3. 根据分析结果改进训练代码...")
                improved = improve_training_code(analysis)
                
                if improved:
                    print("\n4. 重启工作流...")
                    restart_workflow()
                    print("\n等待工作流完成...")
                    time.sleep(300)  # 等待5分钟
                else:
                    print("\n⚠ 无法自动改进，可能需要手动调整")
                    print("请检查训练代码并手动修改后重新启动工作流")
                    break
            else:
                print("  ⚠ 无法分析训练结果，可能需要手动检查")
                break
        
        # 如果工作流出错
        elif current_status == 'error':
            print("\n⚠ 工作流发生错误")
            print("请检查日志文件了解详情")
            break
        
        # 其他状态
        else:
            print(f"\n⚠ 未知状态: {current_status}")
            print("等待一段时间后重新检查...")
            time.sleep(60)
    
    if cycle >= max_cycles:
        print(f"\n⚠ 达到最大循环次数（{max_cycles}），停止自动重启")
        print("请手动检查训练结果并决定下一步操作")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
