"""
主执行器模块

整合所有模块，实现批量游戏执行的主控制逻辑。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import threading
import queue
from pathlib import Path
from typing import Callable, Optional, Set
import logging


# game_records 文件名示例：「<game_id> [yf1_m1]-...」「<game_id> [yf2_m1]-...」
# 评测口径（GUA-022 / ITERATIONS）：一局 = 同一 game_id 下 yf1_m1 与 yf2_m1 各一份 JSON 成对出现。
_GAME_RECORD_M1_PAIR_PATTERN = re.compile(r"^(\d+) \[(yf1_m1|yf2_m1)\]")


def _paired_m1_game_ids(game_records_dir: Path) -> Set[str]:
    """
    返回「成对」的 game_id 集合：同一 id 同时存在 yf1_m1 与 yf2_m1 的 JSON。
    目录不存在或无法解析时返回空集（不抛错）。
    """
    if not game_records_dir.is_dir():
        return set()
    yf1: Set[str] = set()
    yf2: Set[str] = set()
    try:
        for p in game_records_dir.glob("*.json"):
            m = _GAME_RECORD_M1_PAIR_PATTERN.match(p.name)
            if not m:
                continue
            gid, tag = m.group(1), m.group(2)
            if tag == "yf1_m1":
                yf1.add(gid)
            else:
                yf2.add(gid)
    except OSError as e:
        logging.getLogger("batch_executor").warning(
            "扫描 game_records 失败: %s: %s", game_records_dir, e
        )
        return set()
    return yf1 & yf2


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
    
    def __init__(
        self,
        state_file: str,
        logger: Optional[logging.Logger] = None,
        on_before_save: Optional[Callable[[], None]] = None,
    ):
        """
        初始化信号处理器
        
        Args:
            state_file: 状态保存文件路径
            logger: 日志记录器（可选）
            on_before_save: 保存状态前回调（例如从 game_records 同步 completed_games）
        """
        self.state_file = state_file
        self.logger = logger or logging.getLogger(__name__)
        self.execution_state: Optional[ExecutionState] = None
        self.shutdown_requested = False
        self.on_before_save = on_before_save
        
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
        
        if self.on_before_save:
            try:
                self.on_before_save()
            except Exception as e:
                self.logger.warning(f"信号退出前回调失败: {e}")
        
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
        # 本 Run 开始时 game_records 中成对 game_id 快照（与 GUA-022 评测口径一致）
        self._game_records_baseline: Optional[Set[str]] = None
        
        # 初始化信号处理器（仅在主线程中）
        self.signal_handler = None
        if enable_signal_handler:
            try:
                self.signal_handler = SignalHandler(
                    state_file,
                    self.logger,
                    on_before_save=self._sync_state_before_persist,
                )
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
    
    def _sync_completed_from_game_records(self, state: ExecutionState) -> None:
        """
        用项目根目录下 game_records 的本 Run 新增「成对 game_id」数量更新 completed_games。
        与 ITERATIONS / GUA-022 一致：一局 = 同一 game_id 下 yf1_m1 与 yf2_m1 各一份 JSON。
        """
        if self._game_records_baseline is None:
            return
        records_dir = self.project_root / "game_records"
        paired_now = _paired_m1_game_ids(records_dir)
        new_pairs = paired_now - self._game_records_baseline
        session_done = len(new_pairs)
        capped = min(session_done, state.target_games)
        state.completed_games = capped
        state.last_update = datetime.now()
        self.logger.info(
            "game_records 台账：本 Run 新增成对 game_id %d 个，completed_games=%d（目标 %d，目录 %s）",
            session_done,
            capped,
            state.target_games,
            records_dir,
        )
    
    def _sync_state_before_persist(self) -> None:
        """供信号处理 / stop 前调用，使落盘的 completed_games 与 game_records 一致。"""
        if self._current_state is not None and self._game_records_baseline is not None:
            self._sync_completed_from_game_records(self._current_state)
    
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
        
        # 立即落盘，避免磁盘上仍为旧 target_games / completed_games（GUI 与无头共用）
        try:
            state.save(self.state_file)
        except Exception as e:
            self.logger.warning(f"保存初始执行状态失败: {e}")
        
        # 运行诊断
        diagnostic_report = self.run_diagnostic()
        
        if self.diagnose_only:
            self.logger.info("仅诊断模式，退出")
            state.last_update = datetime.now()
            try:
                state.save(self.state_file)
            except Exception as e:
                self.logger.warning(f"保存执行状态失败: {e}")
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
        
        # 记录初始战绩，用于计算增量
        initial_team_a = 0
        initial_team_b = 0
        
        records_dir = self.project_root / "game_records"
        self._game_records_baseline = _paired_m1_game_ids(records_dir)
        self.logger.info(
            "game_records 成对 game_id（yf1_m1+yf2_m1）基线: %d 个（目录: %s）",
            len(self._game_records_baseline),
            records_dir,
        )
        
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
                
                # 启动客户端
                client_processes = self.restart_manager.restart_clients(
                    self.client_scripts
                )
                
                if not client_processes:
                    self.logger.error("没有客户端成功启动，停止执行")
                    break
                
                # 等待所有客户端连接到服务器
                expected_client_count = len(self.client_scripts)
                clients_connected = self.restart_manager.wait_for_clients_connected(
                    expected_count=expected_client_count,
                    timeout=30
                )
                
                if not clients_connected:
                    self.logger.warning("⚠️ 客户端连接检测超时，但继续执行（可能连接已建立）")
                    self.logger.warning("   如果游戏未开始，请检查:")
                    self.logger.warning("   1. 客户端窗口是否有错误信息")
                    self.logger.warning("   2. 服务器窗口是否显示客户端连接")
                    self.logger.warning("   3. 网络连接是否正常")
                else:
                    self.logger.info("✓ 所有客户端已连接")
                
                # 额外等待让对局启动，避免在此阶段提前消费 stdout（会影响后续完成判定）
                self.logger.info("等待游戏开始（保留stdout给后续完成监控）...")
                import time
                game_start_wait_seconds = 10
                time.sleep(game_start_wait_seconds)
                self.logger.info(f"已等待 {game_start_wait_seconds} 秒，进入完成监控阶段...")
                
                # 等待服务器完成
                server_name = os.path.basename(self.server_path)
                self.logger.info(f"等待服务器完成 {batch_games} 场游戏...")
                
                # 掼蛋单局（含多副升级）常超过 5 分钟；过短会误杀仍在出牌的服务器。
                # 每场按 12 分钟估算，整批至少 3 分钟；可按环境变量调大（见 README）。
                _min_batch_seconds = int(os.environ.get("BATCH_EXECUTOR_MIN_BATCH_SECONDS", "180"))
                _seconds_per_game_estimate = int(
                    os.environ.get("BATCH_EXECUTOR_SECONDS_PER_GAME_ESTIMATE", str(12 * 60))
                )
                estimated_timeout = max(_min_batch_seconds, batch_games * _seconds_per_game_estimate)
                self.logger.info(
                    f"等待服务器完成（超时时间: {estimated_timeout // 60} 分钟，"
                    f"按每局约 {_seconds_per_game_estimate // 60} 分钟 × {batch_games} 局估算）..."
                )
                
                # 等待服务器进程结束并读取输出
                server_output = []
                start_time = time.time()
                server_terminated_by_kill = False  # 超时强杀则不计入 completed_games（见下方）
                
                try:
                    # 使用混合方式：同时读取stdout和监控进程状态
                    import threading
                    import queue
                    
                    output_queue = queue.Queue()
                    read_complete = threading.Event()
                    server_reported_done = False
                    done_detected_at: Optional[float] = None
                    # 兼容编码乱码与不同服务器输出：中文、英文、通知键等都可触发完成
                    done_markers = (
                        "达到设定场次",
                        "游戏结束",
                        "gameover",
                        "gameresult",
                        "setting",
                        "curtimes",
                    )
                    batch_start_completed = state.completed_games
                    
                    def read_stdout():
                        """在单独线程中读取stdout"""
                        try:
                            if server_process.stdout:
                                for line in server_process.stdout:
                                    line = line.strip()
                                    if line:
                                        output_queue.put(line)
                                        self.logger.info(f"[服务器] {line}")
                        except Exception as e:
                            self.logger.debug(f"读取stdout异常: {e}")
                        finally:
                            read_complete.set()
                    
                    # 启动stdout读取线程
                    stdout_thread = threading.Thread(target=read_stdout, daemon=True)
                    stdout_thread.start()
                    
                    # 主线程：等待进程结束，同时收集输出
                    check_interval = 5  # 每5秒检查一次进程状态
                    while True:
                        # 检查进程是否已结束
                        return_code = server_process.poll()
                        if return_code is not None:
                            self.logger.info(f"服务器进程已结束，返回码: {return_code}")
                            break
                        
                        # 收集输出队列中的内容，并检查是否已到达设定场次
                        try:
                            while True:
                                line = output_queue.get_nowait()
                                server_output.append(line)
                                line_norm = line.lower()
                                if any(marker in line_norm for marker in done_markers):
                                    server_reported_done = True
                                    if done_detected_at is None:
                                        done_detected_at = time.time()
                                        self.logger.info("检测到服务器完成标记，等待进程自行退出...")
                        except queue.Empty:
                            pass
                        
                        # game_records 已达到本批目标：即使服务端日志编码异常，也可判定完成并收尾
                        try:
                            paired_now = _paired_m1_game_ids(self.project_root / "game_records")
                            if self._game_records_baseline is not None:
                                session_done = min(
                                    len(paired_now - self._game_records_baseline), state.target_games
                                )
                                batch_done = session_done - batch_start_completed
                                if batch_done >= batch_games:
                                    server_reported_done = True
                                    if done_detected_at is None:
                                        done_detected_at = time.time()
                                        self.logger.info(
                                            "检测到 game_records 本批已达标（+%d/%d），等待进程退出...",
                                            batch_done,
                                            batch_games,
                                        )
                        except Exception as e:
                            self.logger.debug(f"按 game_records 判定批次完成失败（可忽略）: {e}")
                        
                        # 服务端已明确完成但进程不退出：给几秒缓冲后主动结束，避免 m1.bat 一直无回传
                        if server_reported_done and done_detected_at is not None:
                            if time.time() - done_detected_at >= 8:
                                self.logger.info("服务器已报告完成且超出缓冲时间，主动结束服务端进程以回传结果")
                                try:
                                    server_process.terminate()
                                    server_process.wait(timeout=5)
                                except Exception:
                                    # 这里只是让父流程尽快推进，不视作超时强杀失败
                                    try:
                                        server_process.kill()
                                        server_process.wait(timeout=3)
                                    except Exception:
                                        pass
                                break
                        
                        # 检查超时
                        elapsed = time.time() - start_time
                        if elapsed >= estimated_timeout:
                            self.logger.warning(f"等待超时（{elapsed//60:.1f} 分钟），检查进程状态...")
                            # 再次检查进程状态
                            if server_process.poll() is None:
                                self.logger.warning("服务器进程仍在运行，可能卡住")
                                # 检查是否有游戏记录生成（作为完成标志；与项目根一致，避免 cwd 不一致漏检）
                                game_records_dir = self.project_root / "game_records"
                                if game_records_dir.exists():
                                    recent_records = list(game_records_dir.glob("*.json"))
                                    if recent_records:
                                        # 检查最新记录的时间
                                        latest_record = max(recent_records, key=lambda p: p.stat().st_mtime)
                                        record_age = time.time() - latest_record.stat().st_mtime
                                        # 单局很长时，记录仍在写入；放宽到 10 分钟内有新文件则延长 10 分钟
                                        if record_age < 600:
                                            self.logger.info(f"检测到最近游戏记录（{record_age:.0f}秒前），继续等待...")
                                            estimated_timeout += 600
                                            continue
                                
                                self.logger.error("服务器长时间未响应，强制终止")
                                server_terminated_by_kill = True
                                server_process.kill()
                                try:
                                    server_process.wait(timeout=5)
                                except subprocess.TimeoutExpired:
                                    self.logger.error("无法终止服务器进程")
                                break
                            else:
                                # 进程已结束，但之前没检测到
                                break
                        
                        # 等待一段时间再检查
                        time.sleep(check_interval)
                    
                    # 等待stdout读取线程完成，并收集剩余输出
                    read_complete.wait(timeout=2)
                    try:
                        while True:
                            line = output_queue.get_nowait()
                            server_output.append(line)
                    except queue.Empty:
                        pass
                    
                    self.logger.info(f"服务器完成，共收集 {len(server_output)} 行输出")
                    
                except Exception as e:
                    self.logger.error(f"等待服务器完成时出错: {e}")
                    import traceback
                    traceback.print_exc()
                
                # completed_games 以 game_records 成对 game_id 为准（GUA-022 口径），避免与磁盘台账脱钩
                if server_terminated_by_kill:
                    self.logger.warning(
                        "本批次因超时强杀结束；completed_games 仅以 game_records 中本 Run 新增成对 game_id 为准。"
                    )
                time.sleep(1.5)
                self._sync_completed_from_game_records(state)
                
                # 从服务器输出读取本批次战绩
                # 服务器输出格式: "达到设定场次, 其中0号位胜利X次，1号位胜利Y次，2号位胜利Z次，3号位胜利W次"
                try:
                    import re
                    # 从服务器输出中查找战绩
                    for line in reversed(server_output):
                        if "达到设定场次" in line or "其中" in line:
                            # 提取各位置胜利次数
                            matches = re.findall(r'(\d+)号位胜利(\d+)次', line)
                            if matches:
                                wins = {int(pos): int(count) for pos, count in matches}
                                # 0号和2号是team_a，1号和3号是team_b
                                current_team_a = wins.get(0, 0) + wins.get(2, 0)
                                current_team_b = wins.get(1, 0) + wins.get(3, 0)
                                
                                # 计算本批次的增量
                                delta_a = current_team_a - initial_team_a
                                delta_b = current_team_b - initial_team_b
                                
                                # 累加到tracker
                                for _ in range(delta_a):
                                    self.tracker.record_game("team_a")
                                for _ in range(delta_b):
                                    self.tracker.record_game("team_b")
                                
                                # 更新初始值
                                initial_team_a = current_team_a
                                initial_team_b = current_team_b
                                
                                self.logger.info(f"本批次增量: Team A +{delta_a}, Team B +{delta_b}")
                                self.logger.info(f"累计战绩: Team A {self.tracker.team_a_wins}胜, Team B {self.tracker.team_b_wins}胜")
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
                self._sync_state_before_persist()
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
