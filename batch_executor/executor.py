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
from pathlib import Path
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
        enable_signal_handler: bool = True,
        visible_server: bool = False
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
            visible_server: 是否在Windows上显示服务器控制台窗口
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
        self.visible_server = visible_server
        
        # 保存项目根目录（用于路径解析）
        self.project_root = Path(__file__).parent.parent
        self.logger.debug(f"项目根目录: {self.project_root}")
        self.logger.debug(f"当前工作目录: {os.getcwd()}")
        
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
        self.restart_manager = RestartManager(self.process_monitor, self.project_root)
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
        
        # 清空之前的战绩，开始新的对战
        self.tracker.team_a_wins = 0
        self.tracker.team_b_wins = 0
        self.tracker.total_games = 0
        self.logger.info("已清空之前的战绩，开始新的对战")
        
        # 主执行循环
        try:
            self.logger.info("=" * 80)
            self.logger.info("🚀 开始批量执行循环")
            self.logger.info(f"🎯 目标：{state.target_games} 场游戏")
            self.logger.info(f"📏 单批次限制：{self.validator.single_run_limit} 场")
            self.logger.info(f"🔢 预计批次数：{self.validator.calculate_restart_count(state.target_games) + 1}")
            self.logger.info("=" * 80)

            while state.completed_games < state.target_games and self._running:
                self.logger.info("=" * 80)
                self.logger.info(f"🔄 循环检查：{state.completed_games} < {state.target_games} and {self._running}")
                self.logger.info("=" * 80)

                if self.signal_handler and self.signal_handler.is_shutdown_requested():
                    self.logger.info("🛑 检测到关闭请求，停止执行")
                    break
                
                # 显示进度
                self.display_progress(state)
                
                # 计算本批次要执行的场数
                remaining = state.target_games - state.completed_games
                batch_games = min(remaining, self.validator.single_run_limit)
                
                self.logger.info("=" * 60)
                self.logger.info(f"开始批次 {state.current_batch}，执行 {batch_games} 场游戏")
                self.logger.info("=" * 60)
                
                # 清理之前的进程（确保没有残留）
                # 注意：第一轮时，这里会清理；后续轮次在上一轮结束时已清理
                self.logger.info("清理之前的进程（确保没有残留）...")
                self.restart_manager.cleanup()
                # 等待一小段时间，确保清理完成
                import time
                time.sleep(1)
                self.logger.info("✓ 清理完成")
                
                # 启动服务器
                server_process = self.restart_manager.restart_server(
                    self.server_path,
                    batch_games,
                    visible_server=self.visible_server
                )
                
                if server_process is None:
                    self.logger.error("服务器启动失败，停止执行")
                    break
                
                # restart_manager.restart_server() 已经等待服务器就绪
                # 检测到 "ready for connect" 后会立即返回
                # 这里只需要额外等待2秒确保端口完全监听
                self.logger.info("服务器已就绪，等待2秒确保端口完全监听...")
                import time
                time.sleep(2)
                
                # 验证服务器进程仍在运行
                if server_process.poll() is not None:
                    self.logger.error(f"服务器进程已退出，返回码: {server_process.returncode}")
                    self.logger.error("请检查服务器窗口或日志，查看启动失败原因")
                    break
                
                self.logger.info("✓ 服务器端口就绪，开始启动客户端...")

                from batch_executor.client_ready import clear_all_ready, client_id_from_script

                clear_all_ready()
                self.logger.info("已清空 clients_ready.json，准备按序连入四席")
                
                # 启动客户端（客户端内部有延迟：yf1_m1=5s, client3=10s, yf2_m1=15s, client4=20s）
                # restart_clients 会根据每个客户端类型智能等待，确保连接顺序
                self.logger.info("开始启动客户端（按顺序启动，智能等待确保连接顺序）...")
                self.logger.info(
                    "客户端内部延迟：yf1_v7=2s, client3=3s, yf2_v7=4s, client4=11s；"
                    "末席门闩稳定等待 7s（GUA-044）"
                )
                self.logger.info("预计四席连入：约 25–35 秒（末席连上后平台才开局）")
                client_processes = self.restart_manager.restart_clients(
                    self.client_scripts,
                    wait_between=8  # 默认等待时间（实际会根据客户端类型调整）
                )
                
                if not client_processes:
                    self.logger.error("没有客户端成功启动，停止执行")
                    break
                
                expected_client_count = len(self.client_scripts)
                expected_client_ids = [
                    cid
                    for script in self.client_scripts
                    if (cid := client_id_from_script(script))
                ]
                connect_wait_timeout = 90
                self.logger.info(
                    f"等待四席 WebSocket 就绪（最多 {connect_wait_timeout} 秒，末席就绪后平台开局）..."
                )
                clients_connected = self.restart_manager.wait_for_clients_connected(
                    expected_count=expected_client_count,
                    timeout=connect_wait_timeout,
                    expected_client_ids=expected_client_ids or None,
                )
                
                if not clients_connected:
                    self.logger.error("四席未全部就绪，本批次中止（避免未连齐即开局）")
                    self.logger.error("请检查各客户端窗口：前序就绪门闩 / 连接错误")
                    break
                self.logger.info("✓ 四席已全部连上，平台可安全开局")
                
                # 验证连接顺序和组队信息
                self.logger.info("=" * 60)
                self.logger.info("连接顺序验证")
                self.logger.info("=" * 60)
                self.logger.info("预期连接顺序:")
                self.logger.info("  1. yf1_v7 → 0号位 (Team A)")
                self.logger.info("  2. run_lalala_client3 → 1号位 (Team B)")
                self.logger.info("  3. yf2_v7 → 2号位 (Team A)")
                self.logger.info("  4. run_lalala_client4 → 3号位 (Team B)")
                self.logger.info("")
                self.logger.info("组队规则:")
                self.logger.info("  Team A: 0号(yf1_v7) + 2号(yf2_v7)")
                self.logger.info("  Team B: 1号(client3) + 3号(client4)")
                self.logger.info("=" * 60)
                
                # 额外等待并检测游戏是否开始
                # 所有客户端连接后，等待服务器输出比赛信息
                self.logger.info("=" * 60)
                self.logger.info("等待服务器输出比赛信息...")
                self.logger.info("所有客户端已连接，等待服务器开始游戏...")
                self.logger.info("=" * 60)
                import time
                game_start_timeout = 30  # 游戏开始超时时间（增加等待时间）
                start_check_time = time.time()
                game_started = False
                
                # 尝试读取服务器输出，检测游戏开始
                # 注意：如果服务器窗口可见（visible_server=True），输出可能不在stdout中
                if server_process.stdout and not self.visible_server:
                    try:
                        import threading
                        import queue
                        
                        # 使用队列在后台线程中读取输出
                        output_queue = queue.Queue()
                        
                        def read_output():
                            """在后台线程中读取服务器输出"""
                            try:
                                for line in server_process.stdout:
                                    if line:
                                        output_queue.put(line.strip())
                            except Exception:
                                pass
                        
                        # 启动后台读取线程
                        read_thread = threading.Thread(target=read_output, daemon=True)
                        read_thread.start()
                        
                        # 轮询队列，检测游戏开始
                        while time.time() - start_check_time < game_start_timeout:
                            try:
                                line = output_queue.get(timeout=1)
                                if line:
                                    self.logger.info(f"[服务器] {line}")
                                    # 检测游戏开始的关键词
                                    if any(keyword in line.lower() for keyword in [
                                        "游戏开始", "gamestart", "game start", 
                                        "开始游戏", "第.*局", "round.*start",
                                        "ready", "all players connected"
                                    ]):
                                        self.logger.info("✓ 检测到游戏开始!")
                                        game_started = True
                                        break
                            except queue.Empty:
                                # 超时，继续等待
                                pass
                            
                            time.sleep(0.5)
                    except Exception as e:
                        self.logger.debug(f"读取服务器输出检测游戏开始时出错: {e}")
                else:
                    # 服务器窗口可见，无法从stdout读取，直接等待
                    self.logger.info("服务器窗口可见，无法从stdout读取输出")
                    self.logger.info("等待 10 秒让游戏有时间开始...")
                    time.sleep(10)
                    game_started = True  # 假设已开始
                
                if game_started:
                    self.logger.info("✓ 游戏已开始或正在开始，继续监控...")
                else:
                    self.logger.warning("⚠️ 未检测到游戏开始消息，但继续执行")
                    self.logger.warning("   可能原因:")
                    self.logger.warning("   1. 服务器输出格式不同")
                    self.logger.warning("   2. 游戏已开始但未输出检测关键词")
                    self.logger.warning("   3. 服务器窗口可见，输出在窗口中显示")
                    self.logger.warning("   建议: 检查服务器窗口确认游戏是否已开始")
                
                # 等待服务器完成
                server_name = os.path.basename(self.server_path)
                self.logger.info(f"等待服务器完成 {batch_games} 场游戏...")

                # 检查是否使用无限运行模式（不传递游戏次数参数）
                infinite_mode = (batch_games == self.validator.single_run_limit)
                if infinite_mode:
                    self.logger.info("使用无限运行模式：将通过游戏计数器监控进度")
                    self.logger.info(f"目标：完成 {batch_games} 场游戏后停止服务器")
                else:
                    self.logger.info("等待服务器输出完成提示: '达到设定游戏次数，若想再次训练请按照使用说明重新运行'")

                # 等待服务器进程结束并读取输出
                server_output = []
                game_completed = False
                completion_message = "达到设定游戏次数，若想再次训练请按照使用说明重新运行"

                # 记录初始游戏数量（用于无限模式下的进度监控）
                initial_games = self.tracker.total_games
                
                try:
                    # 尝试读取输出（即使服务器窗口可见，也尝试读取stdout）
                    # 注意：使用CREATE_NEW_CONSOLE时，stdout可能仍然可用
                    if server_process.stdout:
                        self.logger.info("开始读取服务器输出（实时监控完成提示）...")
                        try:
                            for line in server_process.stdout:
                                line_stripped = line.strip()
                                server_output.append(line_stripped)
                                # 实时打印服务器输出
                                if line_stripped:
                                    self.logger.info(f"[服务器] {line_stripped}")
                                
                                # 检测完成提示
                                if completion_message in line_stripped or "达到设定游戏次数" in line_stripped:
                                    self.logger.info("=" * 60)
                                    self.logger.info("✓ 检测到服务器完成提示!")
                                    self.logger.info(f"  提示内容: {line_stripped}")
                                    self.logger.info("=" * 60)
                                    game_completed = True
                                    
                                    # 检测到完成提示后，立即主动终止服务器进程
                                    self.logger.info("主动终止服务器进程...")
                                    try:
                                        if server_process.poll() is None:
                                            server_process.terminate()
                                            self.logger.info("已发送终止信号，等待进程结束（最多5秒）...")
                                            try:
                                                server_process.wait(timeout=5)
                                                self.logger.info("✓ 服务器进程已正常终止")
                                            except subprocess.TimeoutExpired:
                                                self.logger.warning("服务器进程未响应终止信号，强制结束")
                                                server_process.kill()
                                                server_process.wait(timeout=2)
                                                self.logger.info("✓ 服务器进程已强制终止")
                                    except Exception as e:
                                        self.logger.error(f"终止服务器进程时出错: {e}")
                                        try:
                                            server_process.kill()
                                            server_process.wait(timeout=2)
                                        except:
                                            pass
                                    
                                    # 退出读取循环，继续执行后续逻辑
                                    break

                                # 在无限运行模式下，通过游戏计数器检测完成
                                if infinite_mode and not game_completed:
                                    current_games = self.tracker.total_games
                                    games_completed_this_batch = current_games - initial_games
                                    if games_completed_this_batch >= batch_games:
                                        self.logger.info("=" * 60)
                                        self.logger.info("✓ 检测到无限运行模式下游戏完成!")
                                        self.logger.info(f"  本批次已完成: {games_completed_this_batch}/{batch_games} 场")
                                        self.logger.info(f"  累计游戏总数: {current_games} 场")
                                        self.logger.info("主动终止服务器进程...")
                                        self.logger.info("=" * 60)
                                        game_completed = True

                                        # 立即终止服务器进程
                                        try:
                                            if server_process.poll() is None:
                                                server_process.terminate()
                                                try:
                                                    server_process.wait(timeout=5)
                                                    self.logger.info("✓ 服务器进程已正常终止")
                                                except subprocess.TimeoutExpired:
                                                    self.logger.warning("服务器进程未响应终止信号，强制结束")
                                                    server_process.kill()
                                        except Exception as e:
                                            self.logger.error(f"终止服务器进程时出错: {e}")
                                            try:
                                                server_process.kill()
                                            except:
                                                pass
                        except Exception as read_error:
                            # 如果无法读取stdout（例如CREATE_NEW_CONSOLE模式下），记录警告但继续
                            self.logger.warning(f"无法从stdout读取服务器输出: {read_error}")
                            self.logger.warning("将等待服务器进程结束（请检查服务器窗口确认完成提示）")
                    else:
                        self.logger.warning("服务器stdout不可用，无法读取输出")
                    
                    # 如果已经检测到完成提示并已终止服务器，跳过等待
                    if game_completed and server_process.poll() is not None:
                        self.logger.info("✓ 服务器进程已终止，跳过等待")
                    else:
                        # 等待进程结束（增加超时时间，确保有足够时间完成所有游戏）
                        # 每场游戏大约需要1-2分钟，3场游戏需要3-6分钟，加上缓冲时间，设置10分钟超时
                        timeout_seconds = max(600, batch_games * 120)  # 至少10分钟，或每场游戏2分钟
                        
                        if self.visible_server:
                            # 服务器窗口可见
                            if game_completed:
                                self.logger.info(f"已检测到完成提示，等待服务器进程结束（超时时间: {timeout_seconds}秒）...")
                            else:
                                self.logger.info(f"等待服务器进程结束（超时时间: {timeout_seconds}秒）...")
                                self.logger.info("请检查服务器窗口，确认显示完成提示: '达到设定游戏次数，若想再次训练请按照使用说明重新运行'")
                                self.logger.info("提示：如果服务器窗口显示完成提示，进程将自动结束")
                        else:
                            self.logger.info(f"等待服务器进程结束（超时时间: {timeout_seconds}秒）...")
                        
                        # 等待服务器进程结束
                        try:
                            server_process.wait(timeout=timeout_seconds)
                            self.logger.info("✓ 服务器进程已正常结束")
                            # 如果之前没有检测到完成提示，但进程已结束，认为已完成
                            if not game_completed:
                                self.logger.info("服务器进程已结束，认为本批次已完成")
                                game_completed = True
                        except subprocess.TimeoutExpired:
                            # 如果超时，但已经检测到完成提示，继续执行
                            if game_completed:
                                self.logger.warning(f"服务器进程未在 {timeout_seconds} 秒内结束，但已检测到完成提示，继续执行")
                                # 强制终止服务器进程
                                try:
                                    if server_process.poll() is None:
                                        server_process.terminate()
                                        server_process.wait(timeout=5)
                                except:
                                    server_process.kill()
                            else:
                                raise
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"⚠️ 服务器未在 {timeout_seconds} 秒内终止")
                    # 检查是否已经检测到完成提示
                    if game_completed:
                        self.logger.info("但已检测到完成提示，继续执行")
                    else:
                        self.logger.warning("未检测到完成提示，强制结束服务器")
                        server_process.kill()
                except Exception as e:
                    self.logger.error(f"读取服务器输出时出错: {e}")
                    # 如果已经检测到完成提示，继续执行
                    if not game_completed:
                        raise
                
                # 确保服务器进程已完全结束
                self.logger.info("=" * 60)
                self.logger.info("等待服务器进程完全结束...")
                self.logger.info("=" * 60)
                if server_process.poll() is None:
                    self.logger.warning("服务器进程仍在运行，等待3秒...")
                    import time
                    time.sleep(3)
                    if server_process.poll() is None:
                        self.logger.warning("强制终止服务器进程...")
                        server_process.kill()
                        server_process.wait(timeout=5)
                
                self.logger.info("✓ 服务器进程已完全结束")
                
                # 更新状态
                old_completed = state.completed_games
                state.completed_games += batch_games
                state.last_update = datetime.now()
                self.logger.info("=" * 60)
                self.logger.info(f"📊 状态更新：")
                self.logger.info(f"  本批次游戏数: {batch_games}")
                self.logger.info(f"  之前完成: {old_completed} 场")
                self.logger.info(f"  现在完成: {state.completed_games} 场")
                self.logger.info(f"  目标游戏: {state.target_games} 场")
                self.logger.info(f"  剩余: {state.target_games - state.completed_games} 场")
                self.logger.info("=" * 60)
                
                # 从共享文件或游戏记录文件中读取本批次战绩
                # victoryNum 格式: [0, 3, 0, 3]
                # 表示: [0号位胜利次数, 1号位胜利次数, 2号位胜利次数, 3号位胜利次数]
                # 注意：服务器每批重置计数，所以 victoryNum 是本批的局级结果，不是累计值
                try:
                    import time
                    # 等待游戏记录文件保存完成（客户端可能在游戏结束后才保存）
                    time.sleep(2)
                    
                    victory_num = None
                    latest_file = None
                    data_source = None
                    
                    # 方法1: 优先从共享文件读取（客户端保存的 latest_victory_num.json）
                    shared_file = self.project_root / "batch_executor" / "latest_victory_num.json"
                    if shared_file.exists():
                        try:
                            with open(shared_file, 'r', encoding='utf-8') as f:
                                shared_data = json.load(f)
                            if "victoryNum" in shared_data and shared_data["victoryNum"]:
                                victory_num = shared_data["victoryNum"]
                                latest_file = shared_file
                                data_source = "共享文件"
                                self.logger.info(f"✓ 从共享文件读取 victoryNum: {shared_file}")
                        except Exception as e:
                            self.logger.debug(f"读取共享文件失败: {e}")
                    
                    # 方法2: 如果共享文件没有，从游戏记录文件中读取
                    if not victory_num:
                        game_records_dir = self.project_root / "game_records"
                        if game_records_dir.exists():
                            # 查找包含 victoryNum 的最新游戏记录文件
                            record_files = (
                                list(game_records_dir.glob("*yf*m1*.json"))
                                + list(game_records_dir.glob("*yf*m3*.json"))
                                + list(game_records_dir.glob("*yf*v7*.json"))
                            )
                            if not record_files:
                                record_files = list(game_records_dir.glob("*.json"))
                            
                            # 按修改时间排序，最新的在前
                            record_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                            
                            for record_file in record_files[:10]:  # 只检查最新的10个文件
                                try:
                                    with open(record_file, 'r', encoding='utf-8') as f:
                                        record_data = json.load(f)
                                    
                                    # 检查是否有 result.victoryNum
                                    result = record_data.get("result", {})
                                    if isinstance(result, dict) and "victoryNum" in result:
                                        victory_num = result.get("victoryNum", [])
                                        latest_file = record_file
                                        data_source = "游戏记录文件"
                                        break
                                    # 兼容直接包含 victoryNum 的情况
                                    elif "victoryNum" in record_data:
                                        victory_num = record_data.get("victoryNum", [])
                                        latest_file = record_file
                                        data_source = "游戏记录文件"
                                        break
                                except Exception as e:
                                    self.logger.debug(f"读取游戏记录文件失败 {record_file}: {e}")
                                    continue

                    if victory_num and len(victory_num) >= 4:
                        # victoryNum 格式: [0号位胜利, 1号位胜利, 2号位胜利, 3号位胜利]
                        # 这是本批的局级结果，需要直接累加到 tracker
                        wins = {
                            0: int(victory_num[0]) if victory_num[0] is not None else 0,
                            1: int(victory_num[1]) if victory_num[1] is not None else 0,
                            2: int(victory_num[2]) if victory_num[2] is not None else 0,
                            3: int(victory_num[3]) if victory_num[3] is not None else 0,
                        }

                        self.logger.info("=" * 60)
                        self.logger.info(f"从{data_source or '游戏记录文件'}读取胜负结果")
                        if latest_file:
                            self.logger.info(f"  数据来源: {latest_file.name}")
                        self.logger.info("=" * 60)
                        self.logger.info(f"  0号位胜利: {wins[0]}次")
                        self.logger.info(f"  1号位胜利: {wins[1]}次")
                        self.logger.info(f"  2号位胜利: {wins[2]}次")
                        self.logger.info(f"  3号位胜利: {wins[3]}次")
                        self.logger.info("")

                        # 计算本批各队胜场（同队席位胜利数应一致，取最大值）
                        if wins[0] == wins[2]:
                            batch_team_a = wins[0]
                        else:
                            batch_team_a = max(wins[0], wins[2])

                        if wins[1] == wins[3]:
                            batch_team_b = wins[1]
                        else:
                            batch_team_b = max(wins[1], wins[3])

                        self.logger.info("本批组队胜负统计:")
                        self.logger.info(f"  Team A (0号+2号): {batch_team_a}胜 (0号位{wins[0]}次, 2号位{wins[2]}次)")
                        self.logger.info(f"  Team B (1号+3号): {batch_team_b}胜 (1号位{wins[1]}次, 3号位{wins[3]}次)")
                        self.logger.info("=" * 60)

                        # 直接累加本批胜场（不是增量计算）
                        for _ in range(batch_team_a):
                            self.tracker.record_game("team_a")
                        for _ in range(batch_team_b):
                            self.tracker.record_game("team_b")

                        self.logger.info(f"本批次新增: Team A +{batch_team_a}, Team B +{batch_team_b}")
                        self.logger.info(f"累计战绩: Team A {self.tracker.team_a_wins}胜, Team B {self.tracker.team_b_wins}胜")
                    else:
                        self.logger.warning("⚠ 未能读取 victoryNum 数据")
                        import re
                        for line in reversed(server_output):
                            if "达到设定场次" in line or ("其中" in line and "胜利" in line):
                                matches = re.findall(r'(\d+)号位胜利(\d+)次', line)
                                if matches:
                                    wins = {int(pos): int(count) for pos, count in matches}
                                    batch_team_a = wins.get(0, 0) + wins.get(2, 0)
                                    batch_team_b = wins.get(1, 0) + wins.get(3, 0)
                                    for _ in range(batch_team_a):
                                        self.tracker.record_game("team_a")
                                    for _ in range(batch_team_b):
                                        self.tracker.record_game("team_b")
                                    self.logger.info(f"从服务器输出解析: Team A +{batch_team_a}, Team B +{batch_team_b}")
                                    break
                except Exception as e:
                    self.logger.warning(f"读取战绩失败: {e}")
                    import traceback
                    traceback.print_exc()
                
                # 保存战绩和状态
                try:
                    self.tracker.save()
                    state.save(self.state_file)
                except Exception as e:
                    self.logger.error(f"保存数据失败: {e}", exc_info=True)
                
                # 一次实战（3场比赛）结束后，等待15秒再清理进程
                self.logger.info("=" * 60)
                self.logger.info(f"⏳ 一次实战（{batch_games}场比赛）已结束，等待15秒后再清理进程...")
                self.logger.info("=" * 60)
                import time
                time.sleep(15)
                self.logger.info("✓ 等待完成，开始清理进程")
                
                # 检查是否需要重启
                self.logger.info("=" * 80)
                self.logger.info(f"🔍 检查循环条件：")
                self.logger.info(f"  completed_games: {state.completed_games}")
                self.logger.info(f"  target_games: {state.target_games}")
                self.logger.info(f"  _running: {self._running}")
                self.logger.info(f"  条件: {state.completed_games} < {state.target_games} and {self._running}")
                self.logger.info("=" * 80)

                if state.completed_games < state.target_games:
                    self.logger.info("=" * 60)
                    self.logger.info(f"✅ 本批次完成！已完成 {state.completed_games}/{state.target_games} 场")
                    self.logger.info("🔄 准备启动下一批次...")
                    self.logger.info("=" * 60)

                    state.restart_count += 1
                    state.current_batch += 1

                    # 重要：在启动下一轮之前，先清理所有进程
                    # 这确保没有残留的客户端或服务器进程
                    self.logger.info("🧹 清理所有进程，准备下一轮...")
                    self.restart_manager.cleanup()
                    # 额外等待2秒，确保所有进程完全清理
                    time.sleep(2)
                    self.logger.info("✅ 清理完成，准备启动下一轮")

                    # 明确记录循环将继续
                    self.logger.info("=" * 80)
                    self.logger.info(f"🔄 循环将继续执行下一批次")
                    self.logger.info(f"  已完成: {state.completed_games}/{state.target_games} 场")
                    self.logger.info(f"  下一批次: batch {state.current_batch}")
                    self.logger.info(f"  已重启: {state.restart_count} 次")
                    self.logger.info("=" * 80)
                    # 循环会继续，因为 while 条件仍然满足
                else:
                    self.logger.info("=" * 60)
                    self.logger.info("🎉 所有游戏已完成!")
                    self.logger.info(f"📊 最终统计：{state.completed_games}/{state.target_games} 场游戏完成")
                    self.logger.info("=" * 60)
                    
                    # 最后一次实战结束后，等待15秒再清理进程
                    self.logger.info("=" * 60)
                    self.logger.info(f"⏳ 最后一次实战（{batch_games}场比赛）已结束，等待15秒后再清理进程...")
                    self.logger.info("=" * 60)
                    import time
                    time.sleep(15)
                    self.logger.info("✓ 等待完成，开始清理进程")
                    
                    # 清理所有进程
                    self.logger.info("🧹 清理所有进程...")
                    self.restart_manager.cleanup()
                    self.logger.info("✅ 清理完成")
                    
                    # 所有游戏完成，退出循环
            
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
