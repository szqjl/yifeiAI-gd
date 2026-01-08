"""
通用训练监控接口
支持多种监控后端：TensorBoard、MLflow、wandb（可选）

使用示例:
    monitor = TrainingMonitor(backend="tensorboard")
    monitor.log({"loss": 0.5, "accuracy": 0.9})
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class TrainingMonitor:
    """
    通用训练监控类
    支持多种后端：tensorboard, mlflow, wandb
    """
    
    def __init__(
        self,
        backend: str = "tensorboard",  # tensorboard, mlflow, wandb, none
        project_name: str = "yifei-ai-gd",
        run_name: str = None,
        log_dir: str = "logs",
        **kwargs
    ):
        """
        初始化训练监控器
        
        Args:
            backend: 监控后端类型
            project_name: 项目名称
            run_name: 运行名称
            log_dir: 日志目录
            **kwargs: 后端特定参数
        """
        self.backend = backend.lower()
        self.project_name = project_name
        self.run_name = run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.writer = None
        self.mlflow_run = None
        self.wandb_run = None
        
        self._init_backend(**kwargs)
    
    def _init_backend(self, **kwargs):
        """初始化选定的后端"""
        if self.backend == "tensorboard":
            self._init_tensorboard(**kwargs)
        elif self.backend == "mlflow":
            self._init_mlflow(**kwargs)
        elif self.backend == "wandb":
            self._init_wandb(**kwargs)
        elif self.backend == "none":
            logger.info("训练监控已禁用")
        else:
            logger.warning(f"未知的后端类型: {self.backend}，使用 TensorBoard")
            self.backend = "tensorboard"
            self._init_tensorboard(**kwargs)
    
    def _init_tensorboard(self, **kwargs):
        """初始化 TensorBoard"""
        try:
            from torch.utils.tensorboard import SummaryWriter
            tensorboard_dir = self.log_dir / "tensorboard" / self.run_name
            self.writer = SummaryWriter(log_dir=str(tensorboard_dir))
            logger.info(f"✅ TensorBoard 已启动: {tensorboard_dir}")
            logger.info(f"   查看方式: tensorboard --logdir {tensorboard_dir.parent}")
        except ImportError:
            logger.warning("⚠️ TensorBoard 未安装，运行 'pip install tensorboard' 启用")
            self.backend = "none"
    
    def _init_mlflow(self, **kwargs):
        """初始化 MLflow"""
        try:
            import mlflow
            import mlflow.pytorch
            
            # 设置跟踪 URI（本地文件系统）
            tracking_uri = kwargs.get("tracking_uri", f"file://{self.log_dir.absolute()}/mlruns")
            mlflow.set_tracking_uri(tracking_uri)
            
            # 创建或获取实验
            experiment_name = kwargs.get("experiment_name", self.project_name)
            try:
                experiment_id = mlflow.create_experiment(experiment_name)
            except Exception:
                experiment = mlflow.get_experiment_by_name(experiment_name)
                experiment_id = experiment.experiment_id if experiment else mlflow.create_experiment(experiment_name)
            
            mlflow.set_experiment(experiment_name)
            
            # 开始运行
            self.mlflow_run = mlflow.start_run(run_name=self.run_name)
            logger.info(f"✅ MLflow 已启动: {experiment_name}/{self.run_name}")
            logger.info(f"   Tracking URI: {tracking_uri}")
        except ImportError:
            logger.warning("⚠️ MLflow 未安装，运行 'pip install mlflow' 启用")
            self.backend = "none"
    
    def _init_wandb(self, **kwargs):
        """初始化 wandb"""
        try:
            import wandb
            wandb.init(
                project=self.project_name,
                name=self.run_name,
                dir=str(self.log_dir / "wandb"),
                **kwargs
            )
            self.wandb_run = wandb.run
            logger.info(f"✅ Wandb 已启动: {self.project_name}/{self.run_name}")
        except ImportError:
            logger.warning("⚠️ Wandb 未安装，运行 'pip install wandb' 启用")
            self.backend = "none"
        except Exception as e:
            logger.warning(f"⚠️ Wandb 初始化失败: {e}，切换到 TensorBoard")
            self.backend = "tensorboard"
            self._init_tensorboard()
    
    def log(self, metrics: Dict[str, Any], step: Optional[int] = None):
        """
        记录指标
        
        Args:
            metrics: 指标字典
            step: 步骤数（epoch 或 batch）
        """
        if self.backend == "none":
            return
        
        if step is None:
            step = getattr(self, '_current_step', 0)
        
        if self.backend == "tensorboard" and self.writer:
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    self.writer.add_scalar(key, value, step)
                elif isinstance(value, dict):
                    # 嵌套字典，使用斜杠分隔
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            self.writer.add_scalar(f"{key}/{sub_key}", sub_value, step)
        
        elif self.backend == "mlflow" and self.mlflow_run:
            import mlflow
            # MLflow 只接受标量值，需要展平嵌套字典
            scalar_metrics = {}
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    scalar_metrics[key] = value
                elif isinstance(value, dict):
                    # 嵌套字典，使用斜杠分隔
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            scalar_metrics[f"{key}/{sub_key}"] = sub_value
            if scalar_metrics:
                mlflow.log_metrics(scalar_metrics, step=step)
        
        elif self.backend == "wandb" and self.wandb_run:
            import wandb
            wandb.log(metrics, step=step)
        
        self._current_step = step
    
    def log_config(self, config: Dict[str, Any]):
        """
        记录配置参数
        
        Args:
            config: 配置字典
        """
        if self.backend == "none":
            return
        
        if self.backend == "tensorboard" and self.writer:
            # TensorBoard 使用文本记录配置
            config_text = "\n".join([f"{k}: {v}" for k, v in config.items()])
            self.writer.add_text("config", config_text, 0)
        
        elif self.backend == "mlflow" and self.mlflow_run:
            import mlflow
            mlflow.log_params(config)
        
        elif self.backend == "wandb" and self.wandb_run:
            import wandb
            wandb.config.update(config)
    
    def save_model(self, model_path: str, metadata: Optional[Dict] = None):
        """
        保存模型
        
        Args:
            model_path: 模型文件路径
            metadata: 模型元数据
        """
        if self.backend == "none":
            return
        
        if self.backend == "mlflow" and self.mlflow_run:
            try:
                import mlflow.pytorch
                mlflow.pytorch.log_model(model_path, "model")
                if metadata:
                    import mlflow
                    mlflow.log_dict(metadata, "model_metadata.json")
            except Exception as e:
                logger.warning(f"MLflow 保存模型失败: {e}")
        
        elif self.backend == "wandb" and self.wandb_run:
            try:
                import wandb
                wandb.save(model_path)
            except Exception as e:
                logger.warning(f"Wandb 保存模型失败: {e}")
    
    def finish(self):
        """结束监控"""
        if self.backend == "tensorboard" and self.writer:
            self.writer.close()
            logger.info("✅ TensorBoard 已关闭")
        
        elif self.backend == "mlflow" and self.mlflow_run:
            import mlflow
            mlflow.end_run()
            logger.info("✅ MLflow 运行已结束")
        
        elif self.backend == "wandb" and self.wandb_run:
            import wandb
            wandb.finish()
            logger.info("✅ Wandb 运行已结束")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.finish()


# 便捷函数
def create_monitor(backend: str = "tensorboard", **kwargs) -> TrainingMonitor:
    """
    创建训练监控器的便捷函数
    
    Args:
        backend: 后端类型
        **kwargs: 其他参数
        
    Returns:
        TrainingMonitor 实例
    """
    return TrainingMonitor(backend=backend, **kwargs)
