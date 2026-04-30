"""
M1训练工作流
自动化训练、评估、优化循环，直到M1战胜client

工作流程：
1. 训练模型
2. 分析训练结果
3. 评估M1 vs Client胜率
4. 如果胜率<50%，根据结果优化参数并重新训练
5. 重复直到胜率>50%
"""

import subprocess
import json
import logging
import time
import sys
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# 导入新增的模块
# 确保可以导入同目录下的模块
sys.path.insert(0, str(Path(__file__).parent))
try:
    from mlflow_monitor import MLflowMonitor
    from auto_game_runner import AutoGameRunner
    from code_optimizer import CodeOptimizer
    from workflow_log_monitor import WorkflowLogMonitor
except ImportError as e:
    logger.warning(f"导入模块失败: {e}，某些功能可能不可用")
    MLflowMonitor = None
    AutoGameRunner = None
    CodeOptimizer = None
    WorkflowLogMonitor = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class M1TrainingWorkflow:
    """M1训练工作流"""
    
    def __init__(
        self,
        max_iterations: int = 10,
        target_win_rate: float = 0.50,
        min_games_for_eval: int = 50,
        server_path: str = None,
        auto_optimize_code: bool = True
    ):
        """
        初始化工作流
        
        Args:
            max_iterations: 最大迭代次数
            target_win_rate: 目标胜率
            min_games_for_eval: 评估所需最少对局数
            server_path: 游戏服务器路径
            auto_optimize_code: 是否自动优化代码
        """
        self.max_iterations = max_iterations
        self.target_win_rate = target_win_rate
        self.min_games_for_eval = min_games_for_eval
        self.iteration = 0
        self.training_history = []
        self.model_path = "models/bc_model_stage7_optimized.pth"
        self.history_path = "models/bc_model_stage7_optimized_training_history.json"
        
        # 初始化组件
        try:
            self.mlflow_monitor = MLflowMonitor(experiment_name="m1-vs-client") if MLflowMonitor else None
            if self.mlflow_monitor:
                logger.info("✅ MLflow监控器已初始化")
        except Exception as e:
            logger.warning(f"⚠️ MLflow监控器初始化失败: {e}")
            self.mlflow_monitor = None
        
        try:
            # 如果没有提供server_path，尝试使用默认路径
            if not server_path:
                default_path = r"D:\GDAI\server\windows\guandan_offline_v1006.exe"
                if Path(default_path).exists():
                    server_path = default_path
                    logger.info(f"✅ 使用默认服务器路径: {server_path}")
            
            self.game_runner = AutoGameRunner(server_path=server_path, num_games=min_games_for_eval) if AutoGameRunner else None
            if self.game_runner:
                if self.game_runner.server_path:
                    logger.info(f"✅ 游戏运行器已初始化，服务器路径: {self.game_runner.server_path}")
                else:
                    logger.warning("⚠️ 游戏运行器已初始化，但服务器路径未设置")
        except Exception as e:
            logger.warning(f"⚠️ 游戏运行器初始化失败: {e}，将使用现有游戏记录")
            self.game_runner = None
        
        try:
            self.code_optimizer = CodeOptimizer() if (auto_optimize_code and CodeOptimizer) else None
            if self.code_optimizer:
                logger.info("✅ 代码优化器已初始化")
        except Exception as e:
            logger.warning(f"⚠️ 代码优化器初始化失败: {e}，将跳过自动代码优化")
            self.code_optimizer = None
        self.current_run_id = None
        
        # 初始化日志监控器（用于检测和自动修复bug）
        self.log_monitor = None
        if WorkflowLogMonitor:
            try:
                self.log_monitor = WorkflowLogMonitor()
                logger.info("✅ 工作流日志监控器已初始化")
            except Exception as e:
                logger.warning(f"⚠️ 日志监控器初始化失败: {e}，将跳过日志监控功能")
                self.log_monitor = None
        
    def run(self):
        """运行完整工作流"""
        # 设置输出编码（Windows）
        if sys.platform == 'win32':
            try:
                import io
                # 尝试设置UTF-8编码
                if hasattr(sys.stdout, 'buffer'):
                    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                if hasattr(sys.stderr, 'buffer'):
                    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
            except Exception:
                # 如果设置失败，继续使用默认编码
                pass
        
        logger.info("="*60)
        logger.info("🚀 M1训练工作流启动")
        logger.info(f"目标胜率: {self.target_win_rate:.1%}")
        logger.info(f"最大迭代次数: {self.max_iterations}")
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        logger.info("📊 工作流将自动：")
        logger.info("  1. 监控训练进度（MLflow实时指标）")
        logger.info("  2. 评估M1 vs Client胜率")
        logger.info("  3. 根据结果自动优化参数")
        logger.info("  4. 持续迭代直到达成目标")
        logger.info("  5. 达成目标时发送通知")
        logger.info("="*60)
        
        # 保存工作流启动状态
        self._save_workflow_status("running")
        
        # 启动时进行一次日志监控（检测已知bug）
        if self.log_monitor:
            logger.info("🔍 启动时检查日志，检测已知bug...")
            try:
                monitor_result = self.log_monitor.monitor_logs(lines=50)
                bugs = monitor_result.get('bugs_detected', [])
                if bugs:
                    logger.warning(f"检测到 {len(bugs)} 个潜在bug，尝试自动修复...")
                    fix_result = self.log_monitor.auto_fix_bugs(bugs)
                    if fix_result['fixed_count'] > 0:
                        logger.info(f"✅ 自动修复了 {fix_result['fixed_count']} 个bug")
                        self.log_monitor.save_fix_history()
            except Exception as e:
                logger.debug(f"启动时日志监控失败（可忽略）: {e}")
        
        try:
            for iteration in range(1, self.max_iterations + 1):
                self.iteration = iteration
                logger.info(f"\n{'='*60}")
                logger.info(f"迭代 {iteration}/{self.max_iterations}")
                logger.info(f"{'='*60}")
                
                # 保存当前迭代状态
                self._save_workflow_status("running", iteration=iteration)
                
                try:
                    # 步骤0: 检查/生成游戏记录
                    if self.game_runner:
                        try:
                            if not self.game_runner.check_game_records(self.min_games_for_eval):
                                logger.info("📊 游戏记录不足，自动运行M1与client对战生成记录...")
                                
                                # 保存状态：开始游戏对战
                                self._save_workflow_status("running", iteration=iteration, step="game_generation")
                                
                                game_result = self.game_runner.run_games()
                                
                                # 检查结果并记录
                                if not game_result.get('success'):
                                    error_msg = game_result.get('error', '未知错误')
                                    logger.warning(f"⚠️ 游戏对战失败: {error_msg}")
                                    
                                    # 如果检测到卡住，记录到工作流状态
                                    if "卡住" in error_msg or "无进度" in error_msg:
                                        logger.error("❌ 检测到batch_executor卡住，工作流自我监控机制已触发")
                                        self._save_workflow_status("error", iteration=iteration, 
                                                                  error=f"游戏对战卡住: {error_msg}",
                                                                  step="game_generation")
                                    
                                    logger.info("继续使用现有记录进行评估")
                                else:
                                    logger.info(f"✅ 游戏对战成功，新增 {game_result.get('new_games', 0)} 场记录")
                        except subprocess.TimeoutExpired as e:
                            logger.error(f"❌ 游戏对战超时: {e}")
                            self._save_workflow_status("error", iteration=iteration, 
                                                      error=f"游戏对战超时: {e}",
                                                      step="game_generation")
                            logger.info("继续使用现有记录进行评估")
                        except Exception as e:
                            logger.warning(f"⚠️ 游戏运行器执行出错: {e}")
                            self._save_workflow_status("error", iteration=iteration, 
                                                      error=f"游戏运行器异常: {e}",
                                                      step="game_generation")
                            logger.info("继续工作流，期望使用现有游戏记录")
                    else:
                        logger.warning("⚠️ 游戏运行器未初始化（可能导入失败）")
                        logger.info("将使用现有的游戏记录进行评估")
                    
                    # 步骤1: 训练模型（使用MLflow监控）
                    logger.info(f"\n📈 开始第 {iteration} 轮训练...")
                    if not self._train_model():
                        logger.error(f"❌ 迭代 {iteration} 训练失败，跳过本次迭代")
                        continue
                    logger.info(f"✅ 第 {iteration} 轮训练完成")
                    
                    # 步骤1.5: 从MLflow读取实时指标并分析
                    mlflow_analysis = None
                    if self.mlflow_monitor:
                        mlflow_analysis = self._analyze_mlflow_metrics()
                        if mlflow_analysis:
                            logger.info(f"MLflow分析: {mlflow_analysis.get('issues', [])}")
                            
                            # 根据MLflow分析自动优化代码
                            if self.code_optimizer and mlflow_analysis.get('recommendations'):
                                logger.info("根据MLflow指标自动优化训练代码...")
                                try:
                                    self.code_optimizer.optimize_from_mlflow_analysis(mlflow_analysis)
                                except Exception as e:
                                    logger.warning(f"代码优化失败: {e}")
                    else:
                        logger.warning("MLflow监控器未初始化，跳过实时指标分析")
                    
                    # 步骤2: 分析训练结果
                    training_analysis = self._analyze_training()
                    if training_analysis:
                        logger.info(f"训练分析: {training_analysis.get('issues', [])}")
                    
                    # 步骤3: 评估胜率
                    # 首先检查模型文件是否存在
                    if not Path(self.model_path).exists():
                        logger.warning(f"⚠️ 模型文件不存在: {self.model_path}")
                        logger.warning("这通常表示：")
                        logger.warning("  1. 训练脚本执行成功，但未生成模型文件（可能早停或数据不足）")
                        logger.warning("  2. 训练过程中出现错误，但脚本返回了成功状态")
                        logger.warning("  3. 模型保存路径配置不正确")
                        logger.info("跳过本次评估，继续下一轮训练...")
                        logger.info("建议：检查训练日志，确认训练是否真正完成")
                        # 记录本次迭代（模型未生成）
                        self.training_history.append({
                            'iteration': iteration,
                            'win_rate': 0.0,
                            'status': 'model_not_generated',
                            'timestamp': datetime.now().isoformat()
                        })
                        self._save_workflow_history()
                        continue
                    
                    win_rate_result = self._evaluate_win_rate()
                    if not win_rate_result or win_rate_result.get('win_rate', 0) == 0:
                        logger.warning("⚠️ 无法评估胜率")
                        
                        # 尝试使用游戏运行器生成记录
                        if self.game_runner:
                            logger.info("尝试自动运行M1与client对战生成记录...")
                            try:
                                game_result = self.game_runner.run_games()
                                if game_result.get('success'):
                                    logger.info("✅ 游戏记录生成成功，重新评估...")
                                    win_rate_result = self._evaluate_win_rate()
                                else:
                                    logger.warning(f"游戏对战失败: {game_result.get('error', '未知错误')}")
                            except Exception as e:
                                logger.warning(f"游戏运行器执行失败: {e}")
                        
                        # 如果仍然无法评估，尝试使用现有游戏记录
                        if not win_rate_result or win_rate_result.get('win_rate', 0) == 0:
                            logger.warning("⚠️ 无法获取有效的胜率评估结果")
                            logger.info("可能原因：")
                            logger.info("  1. 游戏记录不足或格式不正确")
                            logger.info("  2. 模型文件存在问题")
                            logger.info("  3. 评估器配置错误")
                            logger.info("继续下一轮训练，期望通过更多训练改善...")
                            # 记录本次迭代（评估失败）
                            self.training_history.append({
                                'iteration': iteration,
                                'win_rate': 0.0,
                                'status': 'evaluation_failed',
                                'timestamp': datetime.now().isoformat()
                            })
                            self._save_workflow_history()
                            continue
                    
                    win_rate = win_rate_result.get('win_rate', 0.0)
                    logger.info(f"当前胜率: {win_rate:.2%}")
                    
                    # 记录迭代结果
                    self.training_history.append({
                        'iteration': iteration,
                        'win_rate': win_rate,
                        'training_analysis': training_analysis,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # 步骤4: 检查是否达到目标
                    if win_rate >= self.target_win_rate:
                        logger.info("="*60)
                        logger.info("✅ 目标达成！M1已能战胜client")
                        logger.info(f"最终胜率: {win_rate:.2%}")
                        logger.info(f"迭代次数: {iteration}")
                        logger.info("="*60)
                        self._save_workflow_history()
                        # 保存成功状态
                        self._save_workflow_status("completed", success=True, win_rate=win_rate, iteration=iteration)
                        # 发送成功通知
                        self._notify_success(win_rate, iteration)
                        return True
                    
                    # 步骤5: 优化参数和代码（如果未达标）
                    if iteration < self.max_iterations:
                        logger.info(f"\n{'='*60}")
                        logger.info(f"⚠️ 胜率未达标 ({win_rate:.2%} < {self.target_win_rate:.1%})")
                        logger.info(f"继续优化参数和代码，准备下一轮训练...")
                        logger.info(f"{'='*60}\n")
                        
                        # 根据MLflow分析优化代码
                        if mlflow_analysis and self.code_optimizer:
                            logger.info("根据MLflow实时指标优化训练代码...")
                            self.code_optimizer.optimize_from_mlflow_analysis(mlflow_analysis)
                        
                        # 根据训练分析优化参数
                        self._optimize_parameters(training_analysis, win_rate, mlflow_analysis)
                        
                        # 保存当前进度
                        self._save_workflow_history()
                        
                        logger.info(f"\n准备开始第 {iteration + 1} 轮训练...")
                        time.sleep(2)  # 短暂等待
                except KeyboardInterrupt:
                    logger.warning("\n⚠️ 工作流被用户中断")
                    self._save_workflow_status("interrupted", iteration=iteration)
                    self._save_workflow_history()
                    raise
                except Exception as e:
                    logger.error(f"\n❌ 迭代 {iteration} 发生未预期的错误: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # 日志监控和自动修复
                    if self.log_monitor:
                        logger.info("🔍 检测到错误，启动日志监控和自动修复...")
                        try:
                            # 监控最近100行日志
                            monitor_result = self.log_monitor.monitor_logs(lines=100)
                            bugs = monitor_result.get('bugs_detected', [])
                            
                            if bugs:
                                logger.warning(f"检测到 {len(bugs)} 个潜在bug")
                                # 自动修复
                                fix_result = self.log_monitor.auto_fix_bugs(bugs)
                                if fix_result['fixed_count'] > 0:
                                    logger.info(f"✅ 自动修复了 {fix_result['fixed_count']} 个bug")
                                    logger.info("建议：重新运行工作流以应用修复")
                                    # 保存修复历史
                                    self.log_monitor.save_fix_history()
                        except Exception as monitor_error:
                            logger.warning(f"日志监控失败: {monitor_error}")
                    
                    # 记录错误状态
                    self.training_history.append({
                        'iteration': iteration,
                        'win_rate': 0.0,
                        'status': 'error',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    self._save_workflow_status("error", iteration=iteration, error=str(e))
                    self._save_workflow_history()
                    # 继续下一轮迭代，而不是直接退出
                    logger.info(f"继续下一轮迭代...")
                    continue
        
        except KeyboardInterrupt:
            logger.warning("\n⚠️ 工作流被用户中断")
            self._save_workflow_status("interrupted")
            self._save_workflow_history()
            raise
        except Exception as e:
            logger.error(f"\n❌ 工作流发生严重错误: {e}")
            import traceback
            traceback.print_exc()
            self._save_workflow_status("error", error=str(e))
            self._save_workflow_history()
            raise
        
        logger.warning("="*60)
        logger.warning(f"⚠️ 达到最大迭代次数 ({self.max_iterations})，但未达到目标胜率")
        if self.training_history:
            last_win_rate = self.training_history[-1].get('win_rate', 0.0)
            logger.warning(f"最后胜率: {last_win_rate:.2%}")
            logger.warning(f"距离目标: {(self.target_win_rate - last_win_rate):.2%}")
        else:
            logger.warning("最后胜率: N/A")
        logger.warning("="*60)
        self._save_workflow_status("completed", success=False)
        self._save_workflow_history()
        
        # 创建未完成标记
        try:
            incomplete_file = Path("models/M1_TARGET_NOT_ACHIEVED.txt")
            with open(incomplete_file, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("⚠️ M1训练目标未完全达成\n")
                f.write("="*60 + "\n\n")
                f.write(f"目标胜率: {self.target_win_rate:.1%}\n")
                if self.training_history:
                    last_win_rate = self.training_history[-1]['win_rate']
                    f.write(f"最后胜率: {last_win_rate:.2%}\n")
                    f.write(f"距离目标: {(self.target_win_rate - last_win_rate):.2%}\n")
                f.write(f"迭代次数: {self.max_iterations}\n")
                f.write(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("建议：增加迭代次数或调整训练参数后继续训练\n")
                f.write("="*60 + "\n")
            logger.info(f"未完成标记文件已创建: {incomplete_file}")
        except Exception as e:
            logger.warning(f"创建未完成标记失败: {e}")
        
        return False
    
    def _train_model(self) -> bool:
        """训练模型（使用胜率导向训练 + MLflow监控）"""
        logger.info("步骤1: 训练模型（胜率导向训练 + MLflow实时监控）...")
        logger.info("优化策略: 优先使用胜利记录，胜负加权学习")
        logger.info("提示: 可在新终端运行 'mlflow ui --backend-store-uri file:///d:/YiFeiAI-GD/logs/mlruns' 查看实时指标")
        
        try:
            run_name = f"m1_workflow_iter{self.iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            # 使用胜率导向训练（优化版：优先使用胜利记录）
            cmd = [
                "python", "src/train/train_win_rate_for_workflow.py"
            ]
            
            # Windows上使用GBK编码，其他系统使用UTF-8
            encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding=encoding,
                errors='replace'  # 遇到无法解码的字符时替换为占位符
            )
            
            if result.returncode == 0:
                logger.info("✅ 训练脚本执行完成（返回码: 0）")
                
                # 检查模型文件是否生成
                if Path(self.model_path).exists():
                    logger.info(f"✅ 模型文件已生成: {self.model_path}")
                else:
                    logger.warning(f"⚠️ 训练脚本返回成功，但模型文件未生成: {self.model_path}")
                    logger.warning("可能原因：")
                    logger.warning("  1. 训练过程中触发了早停，但未保存模型")
                    logger.warning("  2. 训练数据不足，未达到保存条件")
                    logger.warning("  3. 模型保存路径配置错误")
                    # 检查输出中是否有错误信息
                    if result.stderr:
                        logger.warning(f"训练脚本错误输出: {result.stderr[:500]}")  # 只显示前500字符
                
                # 获取运行ID（从输出中提取或从MLflow获取）
                self.current_run_id = self._extract_run_id_from_output(result.stdout) or self._get_latest_run_id()
                return True
            else:
                logger.error(f"❌ 训练失败（返回码: {result.returncode}）")
                logger.error(f"错误信息: {result.stderr[:1000] if result.stderr else '无错误输出'}")
                if result.stdout:
                    # 显示输出的最后几行，可能包含有用的错误信息
                    output_lines = result.stdout.split('\n')
                    if len(output_lines) > 10:
                        logger.error("训练输出（最后10行）:")
                        for line in output_lines[-10:]:
                            if line.strip():
                                logger.error(f"  {line}")
                    else:
                        logger.error(f"训练输出: {result.stdout}")
                return False
                
        except Exception as e:
            logger.error(f"训练过程出错: {e}")
            return False
    
    def _extract_run_id_from_output(self, output: str) -> Optional[str]:
        """从输出中提取运行ID"""
        import re
        match = re.search(r'run_id[:\s]+([a-f0-9-]+)', output, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _get_latest_run_id(self) -> Optional[str]:
        """获取最新的运行ID"""
        if not self.mlflow_monitor:
            return None
        try:
            run_data = self.mlflow_monitor.get_latest_metrics()
            return run_data.get("run_id")
        except:
            return None
    
    def _analyze_mlflow_metrics(self) -> Optional[Dict]:
        """从MLflow读取实时指标并分析"""
        logger.info("步骤1.5: 从MLflow读取实时训练指标...")
        
        if not self.mlflow_monitor:
            logger.warning("MLflow监控器未初始化")
            return None
        
        try:
            analysis = self.mlflow_monitor.analyze_training_progress(self.current_run_id)
            if analysis and not analysis.get("error"):
                logger.info("✅ MLflow指标分析完成")
                return analysis
            else:
                logger.warning("MLflow分析结果无效或运行未完成")
                return None
        except Exception as e:
            logger.warning(f"MLflow分析失败: {e}")
            return None
    
    def _analyze_training(self) -> Optional[Dict]:
        """分析训练结果"""
        logger.info("步骤2: 分析训练结果...")
        
        if not Path(self.history_path).exists():
            logger.warning(f"训练历史文件不存在: {self.history_path}")
            return None
        
        try:
            cmd = [
                "python", "src/train/training_optimizer.py",
                "--history", self.history_path
            ]
            
            # Windows上使用GBK编码，其他系统使用UTF-8
            encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding=encoding,
                errors='replace'  # 遇到无法解码的字符时替换为占位符
            )
            
            if result.returncode == 0:
                # 解析分析结果（简化版，实际可以从JSON输出获取）
                logger.info("✅ 训练分析完成")
                return {"status": "analyzed", "output": result.stdout}
            else:
                logger.warning(f"分析过程有警告: {result.stderr}")
                return None
                
        except Exception as e:
            logger.warning(f"分析过程出错: {e}")
            return None
    
    def _evaluate_win_rate(self) -> Optional[Dict]:
        """评估胜率"""
        logger.info("步骤3: 评估M1 vs Client胜率...")
        
        if not Path(self.model_path).exists():
            logger.warning(f"模型文件不存在: {self.model_path}")
            return None
        
        try:
            cmd = [
                "python", "src/train/m1_vs_client_evaluator.py",
                "--num_games", str(self.min_games_for_eval),
                "--opponent", "client",
                "--model_path", self.model_path
            ]
            
            # Windows上使用GBK编码，其他系统使用UTF-8
            encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                encoding=encoding,
                errors='replace'  # 遇到无法解码的字符时替换为占位符
            )
            
            if result.returncode == 0:
                # 从输出中解析胜率（简化版）
                output = result.stdout
                logger.info("✅ 胜率评估完成")
                
                # 尝试从输出中提取胜率
                win_rate = self._parse_win_rate_from_output(output)
                
                return {
                    "win_rate": win_rate,
                    "output": output
                }
            else:
                logger.warning(f"评估过程有警告: {result.stderr}")
                # 如果没有游戏记录，返回默认值
                return {"win_rate": 0.0, "message": "需要先进行对战测试"}
                
        except Exception as e:
            logger.warning(f"评估过程出错: {e}")
            return {"win_rate": 0.0}
    
    def _parse_win_rate_from_output(self, output: str) -> float:
        """从输出中解析胜率"""
        try:
            # 查找 "胜率: XX.XX%" 格式
            import re
            match = re.search(r'胜率:\s*(\d+\.?\d*)%', output)
            if match:
                return float(match.group(1)) / 100.0
        except:
            pass
        return 0.0
    
    def _optimize_parameters(self, training_analysis: Optional[Dict], win_rate: float, mlflow_analysis: Optional[Dict] = None):
        """根据结果优化参数"""
        logger.info("步骤5: 优化训练参数...")
        
        # 读取训练历史进行分析
        if Path(self.history_path).exists():
            try:
                with open(self.history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                if history:
                    last_epoch = history[-1]
                    prediction_ratio = last_epoch.get('prediction_ratio', 1.0)
                    avg_loss = last_epoch.get('total_loss', 0)
                    
                    optimizations = []
                    
                    # 根据预测比例调整
                    if prediction_ratio > 2.0:
                        optimizations.append(f"预测过度严重（{prediction_ratio:.1f}倍），需要增加过度预测惩罚")
                    elif prediction_ratio < 0.5:
                        optimizations.append(f"预测不足（{prediction_ratio:.1f}倍），需要降低过度预测惩罚")
                    
                    # 根据胜率调整
                    if win_rate < 0.3:
                        optimizations.append("胜率过低，考虑增加训练数据或调整模型架构")
                    elif win_rate < 0.4:
                        optimizations.append("胜率偏低，考虑微调学习率或损失函数权重")
                    
                    # 根据损失调整
                    if avg_loss > 1000000:
                        optimizations.append("损失过高，考虑降低学习率或增加正则化")
                    
                    if optimizations:
                        logger.info("优化建议:")
                        for opt in optimizations:
                            logger.info(f"  - {opt}")
                    else:
                        logger.info("当前参数配置合理，继续训练")
                        
            except Exception as e:
                logger.warning(f"分析训练历史失败: {e}")
        else:
            logger.info("使用默认参数继续训练")
    
    def _save_workflow_history(self):
        """保存工作流历史"""
        history_file = Path("models/m1_training_workflow_history.json")
        try:
            final_status = 'success' if self.training_history and self.training_history[-1].get('win_rate', 0) >= self.target_win_rate else 'incomplete'
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'workflow_history': self.training_history,
                    'target_win_rate': self.target_win_rate,
                    'max_iterations': self.max_iterations,
                    'final_status': final_status,
                    'last_update': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            logger.info(f"工作流历史已保存: {history_file}")
            
            # 创建状态标记文件
            status_file = Path("models/m1_workflow_status.txt")
            with open(status_file, 'w', encoding='utf-8') as f:
                f.write(f"状态: {final_status}\n")
                f.write(f"目标胜率: {self.target_win_rate:.1%}\n")
                if self.training_history:
                    last_win_rate = self.training_history[-1].get('win_rate', 0)
                    f.write(f"当前胜率: {last_win_rate:.2%}\n")
                    f.write(f"迭代次数: {len(self.training_history)}\n")
                f.write(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        except Exception as e:
            logger.error(f"保存工作流历史失败: {e}")
    
    def _save_workflow_status(self, status: str, **kwargs):
        """保存工作流状态（用于监控）"""
        status_file = Path("models/m1_workflow_status.json")
        status_file.parent.mkdir(parents=True, exist_ok=True)
        
        status_data = {
            "status": status,  # running, completed, error, interrupted
            "current_iteration": kwargs.get("iteration", self.iteration if hasattr(self, 'iteration') else 0),
            "max_iterations": self.max_iterations,
            "target_win_rate": self.target_win_rate,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        try:
            with open(status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"工作流状态已保存: {status_file} (状态: {status})")
        except Exception as e:
            logger.warning(f"保存工作流状态失败: {e}")
    
    def _notify_success(self, win_rate: float, iteration: int):
        """发送成功通知"""
        logger.info("\n" + "🎉" * 30)
        logger.info("🎉🎉🎉 目标达成！M1已能战胜client！🎉🎉🎉")
        logger.info("🎉" * 30)
        logger.info(f"\n最终胜率: {win_rate:.2%}")
        logger.info(f"迭代次数: {iteration}")
        logger.info(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("\n" + "🎉" * 30)
        
        # 创建成功标记文件
        try:
            success_file = Path("models/M1_TARGET_ACHIEVED.txt")
            with open(success_file, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("✅ M1训练目标已达成！\n")
                f.write("="*60 + "\n\n")
                f.write(f"目标胜率: {self.target_win_rate:.1%}\n")
                f.write(f"实际胜率: {win_rate:.2%}\n")
                f.write(f"迭代次数: {iteration}\n")
                f.write(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("="*60 + "\n")
            logger.info(f"✅ 成功标记文件已创建: {success_file}")
            
            # Windows系统通知（如果可用）
            try:
                if sys.platform == 'win32':
                    import subprocess
                    title = "M1训练目标达成！"
                    message = f"M1已能战胜client！\n胜率: {win_rate:.2%}\n迭代: {iteration}次"
                    # 使用PowerShell显示通知
                    ps_cmd = f'[System.Windows.Forms.MessageBox]::Show("{message}", "{title}", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)'
                    subprocess.run(['powershell', '-Command', ps_cmd], timeout=5)
            except Exception as e:
                logger.debug(f"Windows通知失败（可忽略）: {e}")
        except Exception as e:
            logger.warning(f"创建通知文件失败: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="M1训练工作流")
    parser.add_argument("--max_iterations", type=int, default=10, help="最大迭代次数")
    parser.add_argument("--target_win_rate", type=float, default=0.50, help="目标胜率")
    parser.add_argument("--min_games", type=int, default=50, help="评估所需最少对局数")
    parser.add_argument("--server_path", type=str, default=None, help="游戏服务器路径")
    parser.add_argument("--no_auto_optimize", action="store_true", help="禁用自动代码优化")
    
    args = parser.parse_args()
    
    workflow = M1TrainingWorkflow(
        max_iterations=args.max_iterations,
        target_win_rate=args.target_win_rate,
        min_games_for_eval=args.min_games,
        server_path=args.server_path,
        auto_optimize_code=not args.no_auto_optimize
    )
    
    success = workflow.run()
    exit(0 if success else 1)
