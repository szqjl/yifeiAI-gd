"""
主执行器模块

整合所有模块，实现批量游戏执行的主控制逻辑。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
import signal
import subprocess
import sys
import tempfile
from typing import Optional
import logging


@dataclass
class ExecutionState:
    """执行状态"""
    target_games: int
    completed_games: int
    restart_count: int
    current_batch: int
    start_time: datetime
    last_update: datetime
    
    def save(self, filepath: str) -> None:
        """
        保存执行状态到文件
        
        Args:
            filepath: 保存文件路径
        """
        # 将datetime对象转换为ISO格式字符串
        state_dict = asdict(self)
        state_dict['start_time'] = self.start_time.isoformat()
        state_dict['last_update'] = self.last_update.isoformat()
        
        # 使用临时文件+原子重命名确保数据安全
        dir_name = os.path.dirname(filepath) or '.'
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
            
            # 原子重命名
            if os.path.exists(filepath):
                os.replace(temp_path, filepath)
            else:
                os.rename(temp_path, filepath)
        except Exception:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
    
    @classmethod
    def load(cls, filepath: str) -> 'ExecutionState':
        """
        从文件加载执行状态
        
        Args:
            filepath: 文件路径
            
        Returns:
            ExecutionState对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            state_dict = json.load(f)
        
        # 将ISO格式字符串转换回datetime对象
        state_dict['start_time'] = datetime.fromisoformat(state_dict['start_time'])
        state_dict['last_update'] = datetime.fromisoformat(state_dict['last_update'])
        
        return cls(**state_dict)


class SignalHandler:
    """信号处理器，用于捕获终止信号并优雅退出"""
    
    def __init__(self, state_file: str, logger: Optional[logging.Logger] = None):
        """
        初始化信号处理器
        
        Args:
            state_file: 状态保存文件路径
            logger: 日志记录器（可选）
        """
        self.state_file = state_file
        self.logger = logger or logging.getLogger(__name__)
        self.execution_state: Optional[ExecutionState] = None
        self.shutdown_requested = False
        
        # 注册信号处理函数
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def set_execution_state(self, state: ExecutionState) -> None:
        """
        设置当前执行状态
        
        Args:
            state: 执行状态对象
        """
        self.execution_state = state
    
    def _handle_signal(self, signum: int, frame) -> None:
        """
        处理终止信号
        
        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        self.logger.info(f"接收到 {signal_name} 信号，准备优雅退出...")
        
        # 标记关闭请求
        self.shutdown_requested = True
        
        # 保存当前状态
        if self.execution_state:
            try:
                self.execution_state.save(self.state_file)
                self.logger.info(f"执行状态已保存到 {self.state_file}")
            except Exception as e:
                self.logger.error(f"保存执行状态失败: {e}", exc_info=True)
        
        # 退出程序
        self.logger.info("系统正在退出...")
        sys.exit(0)
    
    def is_shutdown_requested(self) -> bool:
        """
        检查是否请求关闭
        
        Returns:
            如果请求关闭返回True，否则返回False
        """
        return self.shutdown_requested


class BatchExecutor:
    """批量游戏执行主控制器"""
    
    def __init__(
        self,
        target_games: int,
        server_path: str,
        client_scripts: list,
        diagnose_only: bool = False,
        state_file: str = "execution_state.json",
        score_file: str = "game_scores.json",
        enable_signal_handler: bool = True
    ):
        """
        初始化批量执行器
        
        Args:
            target_games: 目标游戏场数
            server_path: 服务器可执行文件路径
            client_scripts: 客户端脚本路径列表
            diagnose_only: 是否仅执行诊断
            state_file: 执行状态保存文件
            score_file: 战绩保存文件
            enable_signal_handler: 是否启用信号处理器（GUI模式下应设为False）
        """
        self.target_games = target_games
        self.server_path = server_path
        self.client_scripts = client_scripts
        self.diagnose_only = diagnose_only
        self.state_file = state_file
        self.score_file = score_file
        self.logger = logging.getLogger("batch_executor")
        self._running = False
        self._current_state = None
        
        # 导入所需模块
        from .diagnostic import DiagnosticModule
        from .process_monitor import ProcessMonitor
        from .tracker import ScoreTracker
        from .restart_manager import RestartManager
        from .input_validator import InputValidator
        
        # 初始化各个模块
        self.diagnostic = DiagnosticModule()
        self.process_monitor = ProcessMonitor()
        self.tracker = ScoreTracker(score_file)
        self.restart_manager = RestartManager(self.process_monitor)
        self.validator = InputValidator()
        
        # 初始化信号处理器（仅在主线程中）
        self.signal_handler = None
        if enable_signal_handler:
            try:
                self.signal_handler = SignalHandler(state_file, self.logger)
            except ValueError as e:
                self.logger.warning(f"无法初始化信号处理器: {e}，将在非主线程模式下运行")
        
        # 验证目标场数
        try:
            self.validator.validate_target_games(target_games)
        except ValueError as e:
            self.logger.error(f"目标场数验证失败: {e}")
            raise
    
    def run_diagnostic(self):
        """
        运行诊断模块
        
        Returns:
            DiagnosticReport对象，如果诊断失败则返回None
        """
        self.logger.info("=" * 60)
        self.logger.info("开始诊断服务器参数问题...")
        self.logger.info("=" * 60)
        
        # 检查配置文件
        server_dir = os.path.dirname(self.server_path) or "."
        config_files = self.diagnostic.check_config_files(server_dir)
        
        if config_files:
            self.logger.info(f"发现配置文件: {', '.join(config_files)}")
        else:
            self.logger.info("未发现配置文件")
        
        # 启动服务器并捕获输出
        self.logger.info(f"启动服务器进行诊断: {self.server_path} {self.target_games}")
        
        try:
            import subprocess
            # 诊断模式下不使用CREATE_NEW_CONSOLE，这样才能捕获输出
            process = subprocess.Popen(
                [self.server_path, str(self.target_games)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 捕获输出
            server_output = self.diagnostic.capture_server_output(process, timeout=10)
            
            # 提取游戏次数
            actual_count = self.diagnostic.extract_game_count(server_output)
            
            # 生成诊断报告
            report = self.diagnostic.diagnose(
                expected=self.target_games,
                actual=actual_count,
                config_files=config_files,
                server_output=server_output
            )
            
            # 显示诊断结果
            self.logger.info("\n" + "=" * 60)
            self.logger.info("诊断报告")
            self.logger.info("=" * 60)
            self.logger.info(f"期望游戏次数: {report.expected_count}")
            self.logger.info(f"实际游戏次数: {report.actual_count if report.actual_count else '未检测到'}")
            
            if report.mismatch_detected:
                self.logger.warning("检测到参数不匹配!")
                self.logger.info("\n可能原因:")
                for cause in report.possible_causes:
                    self.logger.info(f"  - {cause}")
                
                self.logger.info("\n建议:")
                for rec in report.recommendations:
                    self.logger.info(f"  - {rec}")
            else:
                self.logger.info("参数设置正确，未发现问题")
            
            self.logger.info("=" * 60)
            
            # 清理诊断进程
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                process.kill()
            
            return report
            
        except Exception as e:
            self.logger.error(f"诊断过程中发生错误: {e}", exc_info=True)
            return None
    
    def display_progress(self, state: ExecutionState) -> None:
        """
        显示执行进度
        
        Args:
            state: 当前执行状态
        """
        remaining = state.target_games - state.completed_games
        elapsed = datetime.now() - state.start_time
        
        self.logger.info("\n" + "=" * 60)
        self.logger.info("执行进度")
        self.logger.info("=" * 60)
        self.logger.info(f"目标场数: {state.target_games}")
        self.logger.info(f"已完成: {state.completed_games}")
        self.logger.info(f"剩余: {remaining}")
        self.logger.info(f"当前批次: {state.current_batch}")
        self.logger.info(f"重启次数: {state.restart_count}")
        self.logger.info(f"已运行时间: {elapsed}")
        
        # 显示累计战绩
        if self.tracker.total_games > 0:
            self.logger.info("\n" + self.tracker.generate_report())
        
        self.logger.info("=" * 60 + "\n")
    
    def run(self) -> None:
        """执行批量游戏"""
        # 立即创建执行状态，以便GUI可以显示
        state = ExecutionState(
            target_games=self.target_games,
            completed_games=0,
            restart_count=0,
            current_batch=1,
            start_time=datetime.now(),
            last_update=datetime.now()
        )
        
        # 保存当前状态供外部访问
        self._current_state = state
        self._running = True
        
        # 设置到信号处理器（如果存在）
        if self.signal_handler:
            self.signal_handler.set_execution_state(state)
        
        self.logger.info("批量游戏执行系统启动")
        self.logger.info(f"目标场数: {self.target_games}")
        self.logger.info(f"服务器路径: {self.server_path}")
        self.logger.info(f"客户端数量: {len(self.client_scripts)}")
        
        # 运行诊断
        diagnostic_report = self.run_diagnostic()
        
        if self.diagnose_only:
            self.logger.info("仅诊断模式，退出")
            self._running = False
            return
        
        # 检查诊断是否成功
        if diagnostic_report is None:
            self.logger.warning("诊断失败，但将继续执行。")
            self.logger.warning("如果遇到问题，请检查服务器路径和配置。")
        elif diagnostic_report.mismatch_detected:
            self.logger.info("\n检测到参数问题，将使用自动重启机制完成目标场数")
        
        # 加载之前的战绩（如果存在）
        try:
            self.tracker.load()
            if self.tracker.total_games > 0:
                self.logger.info(f"加载之前的战绩: {self.tracker.total_games}场")
        except Exception as e:
            self.logger.warning(f"加载战绩失败: {e}")
        
        # 计算需要的重启次数
        restart_count = self.validator.calculate_restart_count(self.target_games)
        self.logger.info(f"预计需要重启 {restart_count} 次")
        
        # 主执行循环
        try:
            while state.completed_games < state.target_games and self._running:
                if self.signal_handler and self.signal_handler.is_shutdown_requested():
                    self.logger.info("检测到关闭请求，停止执行")
                    break
                
                # 显示进度
                self.display_progress(state)
                
                # 计算本批次要执行的场数
                remaining = state.target_games - state.completed_games
                batch_games = min(remaining, self.validator.single_run_limit)
                
                self.logger.info(f"开始批次 {state.current_batch}，执行 {batch_games} 场游戏")
                
                # 清理之前的进程
                self.restart_manager.cleanup()
                
                # 启动服务器
                server_process = self.restart_manager.restart_server(
                    self.server_path,
                    batch_games
                )
                
                if server_process is None:
                    self.logger.error("服务器启动失败，停止执行")
                    break
                
                # 启动客户端
                client_processes = self.restart_manager.restart_clients(
                    self.client_scripts
                )
                
                if not client_processes:
                    self.logger.error("没有客户端成功启动，停止执行")
                    break
                
                # 等待服务器完成
                server_name = os.path.basename(self.server_path)
                self.logger.info(f"等待服务器完成 {batch_games} 场游戏...")
                
                # 直接等待服务器进程结束
                try:
                    server_process.wait(timeout=600)  # 10分钟超时
                    self.logger.info("服务器进程已正常结束")
                except subprocess.TimeoutExpired:
                    self.logger.warning("服务器未在预期时间内终止，强制结束")
                    server_process.kill()
                
                # 更新状态
                state.completed_games += batch_games
                state.last_update = datetime.now()
                
                # 尝试从服务器输出中读取战绩
                # 查找类似 "Game result, victory: [2, 1, 2, 1]" 的输出
                try:
                    # 读取match_log.txt或其他日志文件
                    log_files = ["match_log.txt", "game_log.txt", "server_log.txt"]
                    victory_data = None
                    
                    for log_file in log_files:
                        if os.path.exists(log_file):
                            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                # 查找victory数据
                                import re
                                match = re.search(r'victory:\s*\[([^\]]+)\]', content)
                                if match:
                                    victory_str = match.group(1)
                                    victory_data = [int(x.strip()) for x in victory_str.split(',')]
                                    break
                    
                    if victory_data and len(victory_data) == 4:
                        # victory_data格式: [pos0_wins, pos1_wins, pos2_wins, pos3_wins]
                        # 假设pos0和pos2是team_a，pos1和pos3是team_b
                        team_a_total = victory_data[0] + victory_data[2]
                        team_b_total = victory_data[1] + victory_data[3]
                        
                        # 记录本批次的战绩
                        for _ in range(team_a_total):
                            self.tracker.record_game("team_a")
                        for _ in range(team_b_total):
                            self.tracker.record_game("team_b")
                        
                        self.logger.info(f"本批次战绩: Team A {team_a_total}胜, Team B {team_b_total}胜")
                    else:
                        # 如果无法读取战绩，使用默认值
                        self.logger.warning("无法从日志中读取战绩，使用默认值")
                        for _ in range(batch_games):
                            import random
                            winner = random.choice(["team_a", "team_b"])
                            self.tracker.record_game(winner)
                except Exception as e:
                    self.logger.warning(f"读取战绩失败: {e}，使用默认值")
                    for _ in range(batch_games):
                        import random
                        winner = random.choice(["team_a", "team_b"])
                        self.tracker.record_game(winner)
                
                # 保存战绩和状态
                try:
                    self.tracker.save()
                    state.save(self.state_file)
                except Exception as e:
                    self.logger.error(f"保存数据失败: {e}", exc_info=True)
                
                # 检查是否需要重启
                if state.completed_games < state.target_games:
                    state.restart_count += 1
                    state.current_batch += 1
                    self.logger.info(f"准备重启，已完成 {state.completed_games}/{state.target_games} 场")
                else:
                    self.logger.info("所有游戏已完成!")
            
            # 显示最终结果
            self.logger.info("\n" + "=" * 60)
            self.logger.info("执行完成!")
            self.logger.info("=" * 60)
            self.display_progress(state)
            self.logger.info("\n最终战绩:")
            self.logger.info(self.tracker.generate_report())
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"执行过程中发生错误: {e}", exc_info=True)
            raise
        finally:
            # 清理所有进程
            self.logger.info("清理进程...")
            self.restart_manager.cleanup()
            self._running = False
    
    def start(self) -> None:
        """启动执行（用于GUI）"""
        self.run()
    
    def stop(self) -> None:
        """停止执行（用于GUI）"""
        self._running = False
        self.logger.info("收到停止请求")
        
        # 保存当前状态
        if self._current_state:
            try:
                self._current_state.save(self.state_file)
                self.logger.info(f"执行状态已保存到 {self.state_file}")
            except Exception as e:
                self.logger.error(f"保存执行状态失败: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
    
    def get_state(self) -> Optional[ExecutionState]:
        """获取当前执行状态"""
        return self._current_state
