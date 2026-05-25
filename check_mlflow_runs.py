"""
检查MLflow运行记录
"""

import mlflow
from mlflow.tracking import MlflowClient
from pathlib import Path
import sys

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_mlflow_runs():
    """检查MLflow运行记录"""
    print("="*60)
    print("MLflow运行记录检查")
    print("="*60)
    
    # 设置tracking URI
    mlruns_path = Path("logs/mlruns").absolute()
    if not mlruns_path.exists():
        print(f"\n❌ MLflow数据目录不存在: {mlruns_path}")
        return
    
    uri = mlruns_path.as_uri()
    print(f"\nTracking URI: {uri}")
    mlflow.set_tracking_uri(uri)
    
    client = MlflowClient()
    
    # 获取所有实验
    try:
        experiments = client.search_experiments()
        print(f"\n找到 {len(experiments)} 个实验:")
        
        for exp in experiments:
            print(f"\n实验: {exp.name} (ID: {exp.experiment_id})")
            
            # 获取该实验的运行
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=10,
                order_by=["start_time DESC"]
            )
            
            print(f"  运行数量: {len(runs)}")
            
            if runs:
                for i, run in enumerate(runs[:5], 1):
                    print(f"\n  运行 {i}:")
                    print(f"    名称: {run.info.run_name}")
                    print(f"    状态: {run.info.status}")
                    print(f"    开始时间: {run.info.start_time}")
                    
                    # 显示指标
                    if run.data.metrics:
                        print(f"    指标数量: {len(run.data.metrics)}")
                        print(f"    主要指标:")
                        for key in list(run.data.metrics.keys())[:5]:
                            print(f"      {key}: {run.data.metrics[key]}")
                    else:
                        print(f"    指标: 无")
                    
                    # 显示参数
                    if run.data.params:
                        print(f"    参数数量: {len(run.data.params)}")
                        print(f"    主要参数:")
                        for key in list(run.data.params.keys())[:5]:
                            print(f"      {key}: {run.data.params[key]}")
                    else:
                        print(f"    参数: 无")
            else:
                print(f"  ⚠️ 该实验没有运行记录")
        
        # 特别检查m1-vs-client实验
        print(f"\n{'='*60}")
        print("检查 m1-vs-client 实验:")
        print("="*60)
        
        try:
            exp = client.get_experiment_by_name("m1-vs-client")
            if exp:
                print(f"实验ID: {exp.experiment_id}")
                runs = client.search_runs(
                    experiment_ids=[exp.experiment_id],
                    max_results=10,
                    order_by=["start_time DESC"]
                )
                print(f"运行数量: {len(runs)}")
                
                if runs:
                    for run in runs:
                        print(f"\n运行: {run.info.run_name}")
                        print(f"  状态: {run.info.status}")
                        print(f"  指标: {len(run.data.metrics)} 个")
                        print(f"  参数: {len(run.data.params)} 个")
                else:
                    print("⚠️ 该实验还没有运行记录")
            else:
                print("⚠️ m1-vs-client 实验不存在")
        except Exception as e:
            print(f"检查失败: {e}")
            
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("检查完成")
    print("="*60)
    print("\n提示:")
    print("1. 如果运行状态是'RUNNING'，说明训练正在进行中")
    print("2. 如果运行状态是'FINISHED'但没有指标，可能是训练刚完成，数据还在写入")
    print("3. 刷新MLflow UI页面查看最新数据")

if __name__ == "__main__":
    check_mlflow_runs()
