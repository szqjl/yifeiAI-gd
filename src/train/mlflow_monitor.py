"""
MLflow实时监控器
从MLflow Tracking Server读取实时训练指标，用于自动优化
"""

import mlflow
from mlflow.tracking import MlflowClient
from typing import Dict, List, Optional
import logging
import time

logger = logging.getLogger(__name__)


class MLflowMonitor:
    """MLflow实时监控器"""
    
    def __init__(self, tracking_uri: str = None, experiment_name: str = "m1-vs-client"):
        """
        初始化MLflow监控器
        
        Args:
            tracking_uri: MLflow tracking URI
            experiment_name: 实验名称
        """
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        else:
            # 使用默认路径（必须使用绝对路径才能转换为URI）
            from pathlib import Path
            mlruns_path = Path("logs/mlruns").absolute()
            if mlruns_path.exists():
                mlflow.set_tracking_uri(mlruns_path.as_uri())
            else:
                # 如果目录不存在，创建它
                mlruns_path.mkdir(parents=True, exist_ok=True)
                mlflow.set_tracking_uri(mlruns_path.as_uri())
        
        self.client = MlflowClient()
        self.experiment_name = experiment_name
        
        # 获取或创建实验
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
            else:
                experiment_id = experiment.experiment_id
            self.experiment_id = experiment_id
        except Exception as e:
            logger.error(f"获取实验失败: {e}")
            self.experiment_id = None
    
    def get_latest_run_metrics(self, run_id: str = None) -> Dict:
        """
        获取最新运行的指标
        
        Args:
            run_id: 运行ID，如果为None则获取最新的运行
            
        Returns:
            指标字典
        """
        try:
            if run_id is None:
                # 获取最新的运行
                runs = self.client.search_runs(
                    experiment_ids=[self.experiment_id],
                    max_results=1,
                    order_by=["start_time DESC"]
                )
                if not runs:
                    return {}
                run = runs[0]
                run_id = run.info.run_id
            else:
                run = self.client.get_run(run_id)
            
            # 获取指标
            metrics = {}
            for key, value in run.data.metrics.items():
                metrics[key] = value
            
            # 获取参数
            params = {}
            for key, value in run.data.params.items():
                params[key] = value
            
            return {
                "run_id": run_id,
                "status": run.info.status,
                "metrics": metrics,
                "params": params,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time
            }
        except Exception as e:
            logger.error(f"获取运行指标失败: {e}")
            return {}
    
    def get_latest_metrics(self) -> Dict:
        """获取最新运行的指标（简化接口）"""
        return self.get_latest_run_metrics()
    
    def get_metric_history(self, run_id: str, metric_key: str) -> List[Dict]:
        """
        获取指标的完整历史
        
        Args:
            run_id: 运行ID
            metric_key: 指标键名
            
        Returns:
            指标历史列表
        """
        try:
            history = self.client.get_metric_history(run_id, metric_key)
            return [
                {
                    "step": m.step,
                    "value": m.value,
                    "timestamp": m.timestamp
                }
                for m in history
            ]
        except Exception as e:
            logger.error(f"获取指标历史失败: {e}")
            return []
    
    def analyze_training_progress(self, run_id: str = None) -> Dict:
        """
        分析训练进度，用于自动优化
        
        Args:
            run_id: 运行ID
            
        Returns:
            分析结果字典
        """
        run_data = self.get_latest_run_metrics(run_id)
        if not run_data:
            return {"error": "无法获取运行数据"}
        
        metrics = run_data.get("metrics", {})
        analysis = {
            "status": run_data.get("status"),
            "issues": [],
            "recommendations": {}
        }
        
        # 分析预测比例
        predicted_cards = metrics.get("metrics/predicted_cards", 0)
        true_cards = metrics.get("metrics/true_cards", 0)
        if true_cards > 0:
            prediction_ratio = predicted_cards / true_cards
            analysis["prediction_ratio"] = prediction_ratio
            
            if prediction_ratio > 2.0:
                analysis["issues"].append("预测过度严重")
                analysis["recommendations"]["over_prediction_penalty"] = "increase"
                analysis["recommendations"]["loss_alpha"] = "decrease"
            elif prediction_ratio < 0.5:
                analysis["issues"].append("预测不足")
                analysis["recommendations"]["over_prediction_penalty"] = "decrease"
                analysis["recommendations"]["loss_alpha"] = "increase"
        
        # 分析损失趋势
        if run_id:
            loss_history = self.get_metric_history(run_id, "loss/total")
            if len(loss_history) >= 10:
                recent_losses = [h["value"] for h in loss_history[-10:]]
                early_losses = [h["value"] for h in loss_history[:10]]
                
                recent_avg = sum(recent_losses) / len(recent_losses)
                early_avg = sum(early_losses) / len(early_losses)
                
                if recent_avg > early_avg * 1.1:
                    analysis["issues"].append("损失上升")
                    analysis["recommendations"]["learning_rate"] = "decrease"
                elif recent_avg < early_avg * 0.9:
                    analysis["loss_trend"] = "decreasing"
                else:
                    analysis["loss_trend"] = "stable"
        
        # 分析预测质量
        quality_score = metrics.get("quality/prediction_quality_score", 0)
        if quality_score < 0.3:
            analysis["issues"].append("预测质量分数过低")
            analysis["recommendations"]["sparsity_reward"] = "increase"
        
        return analysis
    
    def wait_for_run_completion(self, run_id: str, timeout: int = 3600, check_interval: int = 10):
        """
        等待运行完成
        
        Args:
            run_id: 运行ID
            timeout: 超时时间（秒）
            check_interval: 检查间隔（秒）
            
        Returns:
            是否成功完成
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                run = self.client.get_run(run_id)
                if run.info.status in ["FINISHED", "FAILED", "KILLED"]:
                    return run.info.status == "FINISHED"
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"检查运行状态失败: {e}")
                time.sleep(check_interval)
        
        return False


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="MLflow实时监控")
    parser.add_argument("--run_id", type=str, default=None, help="运行ID")
    parser.add_argument("--analyze", action="store_true", help="分析训练进度")
    
    args = parser.parse_args()
    
    monitor = MLflowMonitor()
    
    if args.analyze:
        analysis = monitor.analyze_training_progress(args.run_id)
        print("\n训练进度分析:")
        print(f"  状态: {analysis.get('status')}")
        print(f"  问题: {analysis.get('issues', [])}")
        print(f"  建议: {analysis.get('recommendations', {})}")
    else:
        metrics = monitor.get_latest_metrics()
        print("\n最新指标:")
        for key, value in metrics.get("metrics", {}).items():
            print(f"  {key}: {value}")
