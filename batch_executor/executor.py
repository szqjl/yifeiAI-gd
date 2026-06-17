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

try:
    import psutil
except ImportError:
    psutil = None


# game_records 文件名示例：「<game_id> [yf1_m3]-[opponent]-[round]-[level].json」
# 台账 completed_games = 平台批次数累计（每批 += batch_games）；落盘副数见 match_key 诊断。
# match key 与 GUA-025 / game_recorder.parse_record_filename 一致：(opponent, round, level)。
_GAME_RECORD_PAIR_PATTERN = re.compile(r"^(\d+) \[(yf[12]_(m[123]|v[4-7]))\]")
_GAME_RECORD_MATCH_KEY_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)


@dataclass
class GameRecordsStats:
    """本 Run 相对 baseline 的落盘诊断计数（不驱动 completed_games）。"""
    paired_game_id: int = 0
    paired_match_key: int = 0
    legacy_round_only_pairs: int = 0


def _scan_game_records_stats(
    records_dir: Path,
    baseline_files: Set[str],
    player_prefix: str = "yf1_",
    teammate_prefix: str = "yf2_",
) -> GameRecordsStats:
    """扫描新增 JSON：成对 game_id、GUA-025 match key、旧 round-only 口径（仅诊断）。"""
    if not records_dir.is_dir():
        return GameRecordsStats()
    by_id_p1: Set[str] = set()
    by_id_p2: Set[str] = set()
    by_round_p1: Set[str] = set()
    by_round_p2: Set[str] = set()
    match_sides: dict = {}
    try:
        for p in records_dir.glob("*.json"):
            if p.name in baseline_files:
                continue
            m = _GAME_RECORD_PAIR_PATTERN.match(p.name)
            if m:
                gid, tag = m.group(1), m.group(2)
                if tag.startswith(player_prefix):
                    by_id_p1.add(gid)
                elif tag.startswith(teammate_prefix):
                    by_id_p2.add(gid)
            mk = _GAME_RECORD_MATCH_KEY_RE.match(p.name)
            if mk:
                player_name = mk.group(2)
                key = (mk.group(3), mk.group(4), mk.group(5))
                if player_name.startswith(player_prefix):
                    match_sides.setdefault(key, set()).add("p1")
                    by_round_p1.add(mk.group(4))
                elif player_name.startswith(teammate_prefix):
                    match_sides.setdefault(key, set()).add("p2")
                    by_round_p2.add(mk.group(4))
    except OSError as e:
        logging.getLogger("batch_executor").warning(
            "扫描 game_records 失败: %s: %s", records_dir, e
        )
        return GameRecordsStats()
    paired_match_key = sum(
        1 for sides in match_sides.values() if "p1" in sides and "p2" in sides
    )
    return GameRecordsStats(
        paired_game_id=len(by_id_p1 & by_id_p2),
        paired_match_key=paired_match_key,
        legacy_round_only_pairs=len(by_round_p1 & by_round_p2),
    )


def _count_new_paired_games(
    records_dir: Path,
    baseline_files: Set[str],
    player_prefix: str = "yf1_",
    teammate_prefix: str = "yf2_",
) -> int:
    """旧 max(game_id, round) 口径，仅保留供测试对比；不得写入 completed_games。"""
    stats = _scan_game_records_stats(
        records_dir, baseline_files, player_prefix, teammate_prefix
    )
    return max(stats.paired_game_id, stats.legacy_round_only_pairs)


def _increment_completed_after_batch(
    state: "ExecutionState",
    batch_games: int,
    *,
    server_terminated_by_kill: bool,
) -> int:
    """方案 A：正常结束的批次按 batch_games 累加台账；强杀批次不加。"""
    if server_terminated_by_kill or batch_games <= 0:
        return 0
    added = min(batch_games, state.target_games - state.completed_games)
    state.completed_games += added
    state.last_update = datetime.now()
    return added


def _count_new_paired_m1_games(
    records_dir: Path,
    baseline_files: Set[str],
) -> int:
    """本 Run 新增成对 M1 局数（yf1_m1 / yf2_m1）。"""
    return _count_new_paired_games(records_dir, baseline_files, "yf1_m1", "yf2_m1")


def _paired_m1_game_ids(game_records_dir: Path) -> Set[str]:
    """返回「成对」的 M1 game_id 集合。"""
    if not game_records_dir.is_dir():
        return set()
    yf1: Set[str] = set()
    yf2: Set[str] = set()
    try:
        for p in game_records_dir.glob("*.json"):
            m = _GAME_RECORD_PAIR_PATTERN.match(p.name)
            if not m:
                continue
            gid, tag = m.group(1), m.group(2)
            if tag.startswith("yf1_m1"):
                yf1.add(gid)
            elif tag.startswith("yf2_m1"):
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
            on_before_save: 保存状态前回调（例如刷新 game_records 诊断日志）
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


def _session_games_from_victory_file(project_root: Path) -> int:
    """从 latest_victory_num.json 读取本局累计局数（[0]+[1]，同队口径）。"""
    shared_file = project_root / "batch_executor" / "latest_victory_num.json"
    if not shared_file.exists():
        return 0
    try:
        with open(shared_file, encoding="utf-8") as f:
            data = json.load(f)
        victory_num = data.get("victoryNum") or []
        if len(victory_num) < 4:
            return 0
        return int(victory_num[0] or 0) + int(victory_num[1] or 0)
    except Exception:
        return 0


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
        # 本 Run 开始时 game_records 文件名快照（用于统计新增成对局）
        self._game_records_files_baseline: Optional[Set[str]] = None
        self._run_lock_path: Optional[Path] = None
        
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
    
    def _get_game_records_stats(self) -> GameRecordsStats:
        if self._game_records_files_baseline is None:
            return GameRecordsStats()
        return _scan_game_records_stats(
            self.project_root / "game_records",
            self._game_records_files_baseline,
        )

    def _log_game_records_diagnostics(
        self,
        state: ExecutionState,
        *,
        batch_games: Optional[int] = None,
        batch_start_stats: Optional[GameRecordsStats] = None,
    ) -> None:
        """方案 C：落盘诊断（match key / game_id），不写入 completed_games。"""
        stats = self._get_game_records_stats()
        state.last_update = datetime.now()
        batch_new_match_keys = None
        if batch_start_stats is not None:
            batch_new_match_keys = stats.paired_match_key - batch_start_stats.paired_match_key
        self.logger.info(
            "game_records 诊断：成对 game_id=%d，成对 match_key(opponent+round+level)=%d，"
            "legacy_round_only=%d；台账 completed_games=%d/%d",
            stats.paired_game_id,
            stats.paired_match_key,
            stats.legacy_round_only_pairs,
            state.completed_games,
            state.target_games,
        )
        if batch_games is not None and batch_new_match_keys is not None:
            self.logger.info(
                "本批落盘：batch_games=%d，新增 match_key=%d",
                batch_games,
                batch_new_match_keys,
            )
            if batch_games > 0 and batch_new_match_keys > batch_games * 3:
                self.logger.warning(
                    "本批 match_key 增量(%d) 远大于 batch_games(%d)；"
                    "落盘副数不等于平台批次数，分析 PASS/胜率时请区分口径。",
                    batch_new_match_keys,
                    batch_games,
                )

    def _write_current_batch_context(self, state: ExecutionState, batch_games: int) -> None:
        """供 M3 客户端读取本批 batch_games（GUA-033）。"""
        payload = {
            "batch": state.current_batch,
            "batch_games": batch_games,
            "timestamp": datetime.now().isoformat(),
        }
        path = self.project_root / "batch_executor" / "current_batch.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.environ["BATCH_GAMES"] = str(batch_games)

    def _validate_batch_victory_num(self, batch_games: int) -> None:
        """批末交叉验证：latest_victory_num.json 与 batch_games / RAW gameResult 口径。"""
        shared = self.project_root / "batch_executor" / "latest_victory_num.json"
        if not shared.exists():
            self.logger.warning(
                "批末未找到 latest_victory_num.json，无法交叉验证 victoryNum（batch_games=%d）",
                batch_games,
            )
            return
        try:
            payload = json.loads(shared.read_text(encoding="utf-8"))
            vn = payload.get("victoryNum", [])
            if not isinstance(vn, list) or len(vn) < 4:
                self.logger.warning("latest_victory_num.json 格式无效: %s", payload)
                return
            team_total = int(vn[0]) + int(vn[1])
            raw = payload.get("server_vn_raw")
            if raw and isinstance(raw, list) and len(raw) >= 4:
                raw_sum = int(raw[0]) + int(raw[1])
                if raw_sum != team_total:
                    self.logger.info(
                        "批末对账：采用 vn=%s (vn_source=%s)，服务器 RAW=%s",
                        vn,
                        payload.get("vn_source", "?"),
                        raw,
                    )
            if team_total != batch_games:
                self.logger.warning(
                    "批末 victoryNum 与 batch_games 不一致: vn=%s [0]+[1]=%d, batch_games=%d；"
                    "本批队胜不计入 tracker",
                    vn,
                    team_total,
                    batch_games,
                )
                return
            if int(vn[0]) != int(vn[2]) or int(vn[1]) != int(vn[3]):
                self.logger.warning("批末 victoryNum 同队不一致: %s", vn)
                return
            self.logger.info(
                "批末 victoryNum 校验通过: vn=%s, batch_games=%d, Team0=%d Team1=%d",
                vn,
                batch_games,
                int(vn[0]),
                int(vn[1]),
            )
        except (json.JSONDecodeError, TypeError, ValueError, OSError) as e:
            self.logger.warning("读取 latest_victory_num.json 失败: %s", e)

    def _sync_state_before_persist(self) -> None:
        """供信号处理 / stop 前调用：刷新诊断日志，不改动 completed_games。"""
        if self._current_state is not None:
            self._log_game_records_diagnostics(self._current_state)
    
    def _acquire_run_lock(self) -> None:
        """防止多个 batch_executor 同时抢占端口 23456 并互相杀进程。"""
        lock_dir = self.project_root / "tmp"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_path = lock_dir / ".batch_executor.lock"
        stale_root_lock = self.project_root / ".batch_executor.lock"
        if stale_root_lock.exists():
            stale_root_lock.unlink(missing_ok=True)
        if lock_path.exists():
            try:
                old_pid = int(lock_path.read_text(encoding="utf-8").strip())
                if psutil is not None and psutil.pid_exists(old_pid):
                    raise RuntimeError(
                        f"已有 batch_executor 在运行 (PID {old_pid})。"
                        "请先 Ctrl+C 停止该进程，或删除 stale lock 后再试。"
                    )
            except ValueError:
                pass
            lock_path.unlink(missing_ok=True)
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
        self._run_lock_path = lock_path
    
    def _release_run_lock(self) -> None:
        if self._run_lock_path is None:
            return
        try:
            if self._run_lock_path.exists():
                if self._run_lock_path.read_text(encoding="utf-8").strip() == str(os.getpid()):
                    self._run_lock_path.unlink()
        except OSError:
            pass
        self._run_lock_path = None
    
    def _count_live_client_processes(self) -> int:
        """统计当前仍在运行的客户端 Python 进程数（按脚本名匹配，去重 PID）。"""
        from .restart_manager import _count_live_client_scripts
        return _count_live_client_scripts(self.client_scripts)
    
    def run(self) -> None:
        """执行批量游戏"""
        self._acquire_run_lock()
        try:
            self._run_impl()
        finally:
            self.logger.info("清理进程...")
            self.restart_manager.cleanup()
            self._release_run_lock()
            self._running = False
    
    def _run_impl(self) -> None:
        """run() 主体逻辑（由 run() 包装 lock/cleanup）。"""
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
        self._game_records_files_baseline = {
            p.name for p in records_dir.glob("*.json")
        } if records_dir.is_dir() else set()
        self.logger.info(
            "game_records 基线文件数: %d（目录: %s）",
            len(self._game_records_files_baseline),
            records_dir,
        )
        
        max_no_progress_restarts = int(
            os.environ.get("BATCH_EXECUTOR_MAX_NO_PROGRESS_RESTARTS", "3")
        )
        max_total_restarts = int(
            os.environ.get(
                "BATCH_EXECUTOR_MAX_TOTAL_RESTARTS",
                str(max(state.target_games * 5, 15)),
            )
        )
        client_monitor_grace_seconds = int(
            os.environ.get("BATCH_EXECUTOR_CLIENT_MONITOR_GRACE", "60")
        )
        consecutive_no_progress_restarts = 0
        last_completed_games = 0
        
        # 主执行循环
        try:
            while state.completed_games < state.target_games and self._running:
                if state.restart_count >= max_total_restarts:
                    self.logger.error(
                        "已达最大重启次数 %d（completed=%d/%d），停止执行。"
                        "请确认无其他 test_t9/batch_executor 在并行运行。",
                        max_total_restarts,
                        state.completed_games,
                        state.target_games,
                    )
                    break
                if self.signal_handler and self.signal_handler.is_shutdown_requested():
                    self.logger.info("检测到关闭请求，停止执行")
                    break
                
                # 显示进度
                self.display_progress(state)
                
                # 计算本批次要执行的场数
                remaining = state.target_games - state.completed_games
                batch_games = min(remaining, self.validator.single_run_limit)
                
                self.logger.info(f"开始批次 {state.current_batch}，执行 {batch_games} 场游戏")
                self._write_current_batch_context(state, batch_games)
                
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
                
                # 验证服务器进程仍在运行（或端口已开放）
                # NOTE: 掼蛋 exe 会启动 tornado 服务端后作为孤儿进程退出父进程，
                #       因此直接检查 process.poll() 会误杀仍在运行的背景服务器。
                #       改为检查端口 23456 是否开放 —— 如果开放说明服务端在运行。
                if server_process.poll() is not None:
                    self.logger.warning(
                        f"服务器主进程已退出（返回码 {server_process.returncode}），"
                        f"检查端口 23456 是否仍开放..."
                    )
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    port_open = sock.connect_ex(('127.0.0.1', 23456)) == 0
                    sock.close()
                    if port_open:
                        self.logger.info(
                            "✓ 端口 23456 已开放，孤儿服务端进程正常运行，"
                            "继续执行"
                        )
                    else:
                        self.logger.error(
                            f"服务器进程已退出（返回码: {server_process.returncode}），"
                            "且端口 23456 未开放"
                        )
                        self.logger.error("请检查服务器窗口或日志，查看启动失败原因")
                        break
                
                self.logger.info("✓ 服务器端口就绪，开始启动客户端...")

                from batch_executor.client_ready import (
                    clear_all_ready,
                    client_id_from_script,
                    wait_for_all_clients_game_ready,
                )

                clear_all_ready()
                self.logger.info("已清空 clients_ready.json，准备按序连入四席")
                
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
                    self.logger.error("四席未全部就绪，本批次中止（避免未连齐即开局）")
                    self.logger.error("请检查各客户端窗口：前序就绪门闩 / 连接错误")
                    break
                self.logger.info("✓ 四席已全部连上，平台可安全开局")
                
                # 等待所有客户端处理首条游戏消息（game_ready）
                self.logger.info("等待所有客户端处理首条游戏消息...")
                game_ready = wait_for_all_clients_game_ready(
                    expected_client_ids,
                    timeout=60,
                )
                if not game_ready:
                    self.logger.warning("部分客户端 game_ready 超时，继续执行（可能开局延迟）")
                else:
                    self.logger.info("✓ 所有客户端已收到首条游戏消息")
                
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
                client_monitor_ready_at = start_time + client_monitor_grace_seconds
                server_terminated_by_kill = False  # 超时强杀则不计入 completed_games（见下方）
                low_client_strikes = 0
                batch_start_stats = self._get_game_records_stats()
                
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
                        "达到设定",
                        "游戏结束",
                        "gameover",
                        "gameresult",
                        "setting",
                        "curtimes",
                    )
                    
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
                    expected_clients = len(self.client_scripts)
                    while True:
                        # 客户端启动后需等待一段时间再监控，避免误判导致每批立即重启
                        if time.time() >= client_monitor_ready_at:
                            live_clients = self._count_live_client_processes()
                            if live_clients < expected_clients:
                                low_client_strikes += 1
                                if low_client_strikes >= 2:
                                    self.logger.error(
                                        "连续检测到客户端进程不足（%d/%d），"
                                        "可能已手动关闭客户端窗口，终止本批次",
                                        live_clients,
                                        expected_clients,
                                    )
                                    server_terminated_by_kill = True
                                    if server_process.poll() is None:
                                        try:
                                            server_process.terminate()
                                            server_process.wait(timeout=5)
                                        except Exception:
                                            try:
                                                server_process.kill()
                                            except Exception:
                                                pass
                                    break
                                self.logger.warning(
                                    "客户端进程不足（%d/%d），等待下次确认（%d/2）",
                                    live_clients,
                                    expected_clients,
                                    low_client_strikes,
                                )
                            else:
                                low_client_strikes = 0
                        
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
                
                # 方案 A：按平台批次累加台账；强杀批次不加
                if server_terminated_by_kill:
                    self.logger.warning(
                        "本批次因超时强杀或客户端异常结束，不增加 completed_games。"
                    )
                else:
                    added = _increment_completed_after_batch(
                        state,
                        batch_games,
                        server_terminated_by_kill=False,
                    )
                    self.logger.info(
                        "本批台账：batch_games=%d，本批计入=%d，completed_games=%d/%d",
                        batch_games,
                        added,
                        state.completed_games,
                        state.target_games,
                    )
                time.sleep(1.5)
                self._log_game_records_diagnostics(
                    state,
                    batch_games=batch_games,
                    batch_start_stats=batch_start_stats,
                )
                if not server_terminated_by_kill:
                    self._validate_batch_victory_num(batch_games)
                
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
                    if state.completed_games <= last_completed_games:
                        consecutive_no_progress_restarts += 1
                        self.logger.warning(
                            "本批次未产生新进度（completed_games=%d），"
                            "连续无进度重启 %d/%d",
                            state.completed_games,
                            consecutive_no_progress_restarts,
                            max_no_progress_restarts,
                        )
                        if consecutive_no_progress_restarts >= max_no_progress_restarts:
                            self.logger.error(
                                "连续 %d 次重启仍无进度，停止执行。"
                                "请检查：是否重复启动了 test_t9/batch_executor、"
                                "客户端是否异常退出、端口 23456 是否被占用。",
                                max_no_progress_restarts,
                            )
                            break
                    else:
                        consecutive_no_progress_restarts = 0
                    last_completed_games = state.completed_games
                    state.restart_count += 1
                    state.current_batch += 1
                    state.last_update = datetime.now()
                    try:
                        state.save(self.state_file)
                    except Exception as e:
                        self.logger.error(f"保存数据失败: {e}", exc_info=True)
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
