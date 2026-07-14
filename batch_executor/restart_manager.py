"""
重启管理模块

管理服务器和客户端的重启，包括启动、等待和清理功能。
"""

import subprocess
import sys
import time
import logging
import os
import socket
from typing import List, Optional
from pathlib import Path

from .process_monitor import ProcessMonitor

# 用于强制清理残留服务器进程
try:
    import psutil
except ImportError:
    psutil = None


logger = logging.getLogger(__name__)


def _pids_for_client_script(script_basename: str) -> List[int]:
    """按脚本文件名查找仍在运行的客户端 Python 进程 PID。"""
    if psutil is None:
        return []
    target = script_basename.lower()
    own_pid = os.getpid()
    pids: List[int] = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            pid = proc.info["pid"]
            if pid == own_pid:
                continue
            name = (proc.info.get("name") or "").lower()
            if "python" not in name:
                continue
            cmdline = proc.cmdline()
            cmd_str = " ".join(cmdline).lower()
            # batch_executor --clients  argv 也含脚本名，须排除以免批次间 cleanup 自杀
            if "batch_executor" in cmd_str:
                continue
            if target not in cmd_str:
                continue
            # 只认「python …/script.py」式启动，排除仅被引用的路径
            if not any(arg.lower().endswith(target) for arg in cmdline):
                continue
            pids.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return pids


def _wait_port_free(port: int = 23456, timeout: float = 20.0) -> bool:
    """等待本地端口释放（批次间避免旧服/旧连接占坑）。"""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return True
        finally:
            sock.close()
        time.sleep(0.5)
    return False


def _kill_all_client_script_processes(client_scripts: List[str]) -> None:
    """按脚本名结束全部匹配的 Python 客户端（含 start 壳未跟踪到的残留）。"""
    if psutil is None:
        return
    for script in client_scripts:
        basename = os.path.basename(script)
        for pid in _pids_for_client_script(basename):
            try:
                psutil.Process(pid).kill()
                logger.info("已结束客户端 Python PID=%s (%s)", pid, basename)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass


def _count_live_client_scripts(client_scripts: List[str]) -> int:
    """统计仍在运行的客户端进程数（按脚本名去重 PID）。"""
    if psutil is None:
        return len(client_scripts)
    seen: set = set()
    for script in client_scripts:
        for pid in _pids_for_client_script(os.path.basename(script)):
            seen.add(pid)
    return len(seen)


class TrackedClientProcess:
    """
    Windows start/cmd 模式下跟踪真实客户端 Python 进程。
    VirtualProcess 只跟踪 start 壳进程，会导致误判客户端已退出并触发无限重启。
    """

    def __init__(self, script_basename: str, window_title: str):
        self.script_basename = script_basename
        self.window_title = window_title
        self.pid: Optional[int] = None
        self.returncode: Optional[int] = None

    def resolve_pid(
        self,
        wait_seconds: float = 8.0,
        exclude_pids: Optional[set] = None,
    ) -> Optional[int]:
        exclude = set(exclude_pids or [])
        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            pids = _pids_for_client_script(self.script_basename)
            candidates = [p for p in pids if p not in exclude]
            if candidates:
                if psutil is not None:
                    def _create_time(pid: int) -> float:
                        try:
                            return psutil.Process(pid).create_time()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            return 0.0
                    self.pid = max(candidates, key=_create_time)
                else:
                    self.pid = candidates[-1]
                return self.pid
            time.sleep(0.5)
        return None

    def poll(self) -> Optional[int]:
        if self.returncode is not None:
            return self.returncode
        if self.pid is None:
            self.resolve_pid(wait_seconds=0)
        if self.pid is None:
            # 尚未解析到 PID：可能仍在启动，不视为已退出
            return None
        if psutil is None:
            return None
        try:
            if psutil.pid_exists(self.pid):
                return None
        except Exception:
            return None
        self.returncode = -1
        return self.returncode

    def terminate(self) -> None:
        if self.pid is not None and psutil is not None:
            try:
                psutil.Process(self.pid).terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        try:
            subprocess.run(
                ["taskkill", "/F", "/FI", f"WINDOWTITLE eq {self.window_title}*"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass

    def kill(self) -> None:
        if self.pid is not None and psutil is not None:
            try:
                psutil.Process(self.pid).kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        self.terminate()

    def wait(self, timeout=None):
        return self.returncode


class RestartManager:
    """管理服务器和客户端的重启"""
    
    def __init__(self, process_monitor: Optional[ProcessMonitor] = None, project_root: Optional[Path] = None):
        """
        初始化重启管理器
        
        Args:
            process_monitor: 进程监控器实例，如果未提供则创建新实例
            project_root: 项目根目录（用于路径解析）
        """
        self.process_monitor = process_monitor or ProcessMonitor()
        self.server_process: Optional[subprocess.Popen] = None
        self.client_processes: List[subprocess.Popen] = []
        # 如果没有提供项目根目录，使用默认值（batch_executor的父目录）
        if project_root is None:
            project_root = Path(__file__).parent.parent
        self.project_root = project_root
    
    def restart_server(
        self,
        server_path: str,
        game_count: int,
        visible_server: bool = False,  # Add this parameter
        max_retries: int = 3,
        wait_time: int = 15,
        platform: str = "v1006",  # V8: 平台类型
        server_port: int = None,  # V8: 服务器端口，None 时根据 platform 自动推导
    ) -> Optional[subprocess.Popen]:
        """
        重启服务器
        
        构建服务器启动命令，使用subprocess.Popen启动，
        等待服务器就绪，实现重试逻辑。
        
        Args:
            server_path: 服务器可执行文件路径
            game_count: 游戏场数（v1006 有效，openguandan 忽略）
            max_retries: 最大重试次数，默认3次
            wait_time: 等待服务器就绪的时间（秒），默认15秒
            platform: 平台类型（v1006/openguandan）
            server_port: 服务器 WebSocket 端口（None 时自动：8181 for openguandan, 23456 for v1006）
            
        Returns:
            成功启动的服务器进程，如果失败返回None
        """
        # 端口推导
        if server_port is None:
            server_port = 8181 if platform == "openguandan" else 23456

        # V8: 同时清理新旧平台服务器进程
        _SERVER_PROC_NAMES = ("guandan_offline_v1006", "guandan")
        for attempt in range(max_retries):
            # 强制清理残留的旧服务器进程，确保端口释放（解决 WinError 10048 端口占用）
            if psutil is not None:
                for proc in psutil.process_iter(['name']):
                    try:
                        name = proc.info['name'] or ""
                        if any(pat in name for pat in _SERVER_PROC_NAMES):
                            logger.warning(f"强制结束残留服务器进程 PID={proc.pid} name={name}，确保端口释放")
                            proc.kill()
                            proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        pass
            else:
                # 降级方案：使用 PowerShell 命令清理
                os.system(
                    'powershell -Command '
                    '"Get-Process guandan_offline_v1006,guandan -ErrorAction SilentlyContinue '
                    '| Stop-Process -Force -ErrorAction SilentlyContinue"'
                )

            try:
                logger.info(f"尝试启动服务器 (尝试 {attempt + 1}/{max_retries})")
                logger.info(f"服务器路径: {server_path}")
                logger.info(f"游戏场数: {game_count}")
                
                # 检查服务器文件是否存在
                if not os.path.exists(server_path):
                    logger.error(f"服务器文件不存在: {server_path}")
                    return None
                
                # 构建启动命令
                # V8 (openguandan): guandan.exe/jar 不含 game_count 参数，局数由 CREATE_ROOM 传递
                if platform == "openguandan":
                    if str(server_path).endswith(".jar"):
                        command = ["java", "-jar", server_path]
                    else:
                        command = [server_path]
                else:
                    command = [server_path, str(game_count)]
                
                # 获取服务器所在目录作为工作目录
                server_dir = os.path.dirname(server_path) or "."
                logger.info(f"工作目录: {server_dir}")
                
                # 启动服务器进程
                # 捕获输出以便读取战绩，但不阻塞
                creationflags = 0
                if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                    creationflags = subprocess.CREATE_NO_WINDOW

                stdout_dest = subprocess.PIPE
                if visible_server and sys.platform == 'win32':
                    if hasattr(subprocess, 'CREATE_NEW_CONSOLE'):
                        creationflags = subprocess.CREATE_NEW_CONSOLE
                    else:
                        # Fallback for older Python versions
                        creationflags = 0  # Let it create default window
                    # CREATE_NEW_CONSOLE 下子进程 stdout 进弹窗不进 PIPE，强读 PIPE 会拖到进程结束才批量 dump（GUA-048）
                    stdout_dest = subprocess.DEVNULL
                    logger.info("可见窗口模式：服务端输出仅在弹窗显示，批跑主日志不镜像 stdout")

                process = subprocess.Popen(
                    command,
                    cwd=server_dir,  # 设置工作目录
                    stdout=stdout_dest,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,  # 设置创建标志
                    text=True,
                    bufsize=1  # 行缓冲
                )
                
                logger.info(f"服务器进程已启动，PID: {process.pid}")
                
                # --- 服务器就绪等待（平台自适应）---
                check_interval = 2
                elapsed = 0
                server_output_lines = []

                logger.info(f"服务器窗口已启动，PID: {process.pid}")

                if platform == "openguandan":
                    # OpenGuanDan 不输出 v1006 风格的 "ready for connect" 等关键词；
                    # 直接轮询其 WebSocket 端口确认服务已监听
                    logger.info("等待 OpenGuanDan 服务器端口 %d 就绪...", server_port)
                    port_ready = False

                    while elapsed < wait_time:
                        time.sleep(min(check_interval, wait_time - elapsed))
                        elapsed += check_interval

                        # 检查进程存活
                        return_code = process.poll()
                        if return_code is not None:
                            logger.warning(f"服务器进程在 {elapsed} 秒后退出，返回码: {return_code}")
                            try:
                                if process.stdout:
                                    remaining = process.stdout.read()
                                    if remaining:
                                        for line in remaining.splitlines():
                                            line = line.strip()
                                            if line:
                                                server_output_lines.append(line)
                                                logger.info("[服务器] %s", line)
                            except Exception:
                                pass
                            break

                        # 尝试连接端口
                        try:
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(1)
                            result = sock.connect_ex(('127.0.0.1', server_port))
                            sock.close()
                            if result == 0:
                                logger.info("✓ 检测到 OpenGuanDan 服务器端口 %d 已监听!", server_port)
                                port_ready = True
                                break
                        except Exception:
                            pass

                        # 同时读取 stdout 日志（非阻塞，仅记录）
                        try:
                            if process.stdout:
                                while True:
                                    line = process.stdout.readline()
                                    if not line:
                                        break
                                    line = line.strip()
                                    if line:
                                        server_output_lines.append(line)
                                        logger.info("[服务器] %s", line)
                        except Exception:
                            pass

                    if not port_ready:
                        if process.poll() is None:
                            logger.warning(
                                "端口 %d 未检测到监听，但进程仍在运行（启动可能较慢）。"
                                "若客户端连接失败，请增大 wait_time 或检查 guandan.exe 运行状态。",
                                server_port,
                            )
                else:
                    # v1006: 原有逻辑——等待 stdout 就绪关键词
                    logger.info("等待服务器输出 'ready for connect' 或类似就绪消息...")

                    while elapsed < wait_time:
                        time.sleep(min(check_interval, wait_time - elapsed))
                        elapsed += check_interval

                        try:
                            if process.stdout:
                                while True:
                                    line = process.stdout.readline()
                                    if not line:
                                        break
                                    line = line.strip()
                                    if line:
                                        server_output_lines.append(line)
                                        logger.info("[服务器] %s", line)
                                        if any(keyword in line.lower() for keyword in ["ready for connect", "server started", "listening", "waiting for players", "ready"]):
                                            logger.info("✓ 检测到服务器就绪消息!")
                                            elapsed = wait_time  # Force exit loop
                                            break
                        except Exception as read_error:
                            logger.debug("读取服务器输出时出错 (正常在可见窗口模式): %s", read_error)

                        return_code = process.poll()
                        if return_code is not None:
                            logger.warning("服务器进程在 %d 秒后退出，返回码: %d", elapsed, return_code)
                            try:
                                if process.stdout:
                                    remaining = process.stdout.read()
                                    if remaining:
                                        remaining_lines = [line.strip() for line in remaining.splitlines() if line.strip()]
                                        server_output_lines.extend(remaining_lines)
                                        for line in remaining_lines[-5:]:
                                            logger.info("[服务器最终输出] %s", line)
                            except Exception:
                                pass
                            break

                    # visible_server 端口兜底检测（使用正确的端口，不再硬编码 23456）
                    if visible_server and sys.platform == 'win32':
                        logger.info("服务端窗口已可见，检查端口 %d 是否监听...", server_port)
                        port_ready = False
                        for _ in range(5):
                            try:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(1)
                                result = sock.connect_ex(('127.0.0.1', server_port))
                                sock.close()
                                if result == 0:
                                    logger.info("✓ 检测到服务器端口 %d 已监听!", server_port)
                                    port_ready = True
                                    break
                            except Exception:
                                pass
                            time.sleep(1)

                        if not port_ready:
                            logger.warning("未能检测到端口监听，但继续执行（服务器可能需要更多时间）")
                        logger.info("如果连接失败，请检查服务器窗口输出")

                # --- 输出摘要 + 最终判定 ---
                if server_output_lines:
                    logger.info("捕获到服务器输出 %d 行 (最后5行):", len(server_output_lines))
                    for line in server_output_lines[-5:]:
                        logger.info("  %s", line)
                else:
                    if visible_server:
                        logger.info("无捕获输出 (正常，可见窗口模式)，请查看弹出的服务端窗口")
                    else:
                        logger.warning("无服务器输出，服务器可能未正常启动")

                # Final check
                if process.poll() is None:
                    logger.info("✓ 服务器启动成功，进程正在运行")
                    self.server_process = process
                    return process
                else:
                    return_code = process.returncode
                    logger.error("✗ 服务器进程已终止，返回码: %d", return_code)
                    if server_output_lines:
                        logger.error("服务器错误输出 (最后10行):")
                        for line in server_output_lines[-10:]:
                            logger.error("  %s", line)
                    else:
                        logger.error("提示: 服务器可能启动失败，请检查服务器路径、参数和权限")
                    
            except FileNotFoundError:
                logger.error(f"服务器可执行文件不存在: {server_path}")
                return None
            except PermissionError:
                logger.error(f"没有权限执行服务器: {server_path}")
                return None
            except Exception as e:
                logger.error(f"启动服务器时发生错误: {e}", exc_info=True)
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                logger.info("等待5秒后重试...")
                time.sleep(5)
        
        logger.error(f"服务器启动失败，已重试{max_retries}次")
        return None
    
    def restart_clients(
        self,
        client_scripts: List[str],
        wait_between: int = 3,  # 3 seconds between clients to ensure connection order
        platform: str = "v1006",
        games: int = 1,  # V8: 局数，传给 yf1_v8 CREAT_ROOM.round
    ) -> List[subprocess.Popen]:
        """
        重启所有客户端
        
        按顺序启动所有客户端，每个客户端之间等待指定时间。
        处理启动失败，继续启动其他客户端。
        
        Args:
            client_scripts: 客户端脚本路径列表
            wait_between: 每个客户端之间的等待时间（秒），默认3秒
            platform: 平台类型（v1006/openguandan），V8: openguandan 时自动追加 --platform/--role
            games: V8 局数（仅 platform=openguandan 时用于 yf1_v8 --games 参数）
            
        Returns:
            成功启动的客户端进程列表
        """
        processes = []
        self._last_client_scripts = list(client_scripts)
        assigned_pids: set = set()
        # V8: 统计 v8_lalala_adapter.py 出现次数，用于区分 client3/client4
        _lalala_seen = 0

        for i, script_path in enumerate(client_scripts):
            try:
                script_path = script_path.strip()  # 去除前后空格
                
                # 将相对路径转换为绝对路径
                if not os.path.isabs(script_path):
                    # 如果是相对路径，先尝试相对于当前工作目录
                    abs_script_path = os.path.abspath(script_path)
                    
                    # 如果当前工作目录下的路径不存在，尝试相对于项目根目录
                    if not os.path.exists(abs_script_path):
                        abs_script_path = self.project_root / script_path
                        abs_script_path = str(abs_script_path.resolve())
                else:
                    abs_script_path = script_path
                
                # 验证文件是否存在
                if not os.path.exists(abs_script_path):
                    logger.error(f"客户端脚本不存在: {script_path}")
                    logger.error(f"  尝试的绝对路径: {abs_script_path}")
                    logger.error(f"  当前工作目录: {os.getcwd()}")
                    logger.error(f"  项目根目录: {self.project_root}")
                    continue
                
                logger.info(f"启动客户端 {i + 1}/{len(client_scripts)}: {script_path}")
                logger.info(f"  绝对路径: {abs_script_path}")
                
                # 确定如何启动客户端（Python脚本）— 与 test_t9 使用同一解释器
                python_exe = sys.executable.replace("/", "\\")
                
                # V8: 为 openguandan 平台构建客户端参数
                platform_args: list[str] = []
                script_basename = os.path.basename(abs_script_path)
                if platform == "openguandan":
                    if script_basename == "yf1_v8.py":
                        platform_args = ["--platform", "openguandan", "--role", "creator", "--games", str(games)]
                    elif script_basename == "yf2_v8.py":
                        platform_args = ["--platform", "openguandan", "--role", "joiner"]
                    elif script_basename == "v8_lalala_adapter.py":
                        _lalala_seen += 1
                        client_name = "client3" if _lalala_seen == 1 else "client4"
                        platform_args = [client_name, "--platform", "openguandan", "--role", "joiner"]
                    logger.info(f"  平台参数: {platform_args}")

                command = [python_exe, abs_script_path] + platform_args
                
                # 启动客户端进程
                # 不捕获输出，让输出显示在控制台窗口中
                # Windows上使用start命令创建新窗口，其他平台使用默认方式
                if sys.platform == 'win32':
                    # Windows: 使用start命令创建新的控制台窗口显示客户端输出
                    # start命令会打开新窗口并执行命令
                    # 使用start命令在新窗口中启动，窗口标题包含脚本名便于识别
                    window_title = f"客户端{i+1}: {os.path.basename(abs_script_path)}"
                    # 确保工作目录是项目根目录，这样相对导入才能正常工作
                    work_dir = str(self.project_root.resolve())
                    # 计算相对于项目根目录的路径（与CMD文件格式一致）
                    try:
                        rel_path = os.path.relpath(abs_script_path, work_dir)
                        rel_path_normalized = rel_path.replace('/', '\\')
                    except ValueError:
                        # 如果无法计算相对路径，使用绝对路径
                        rel_path_normalized = abs_script_path.replace('/', '\\')
                    # cmd /c：客户端脚本结束后自动关闭窗口；/k 会留下空 CMD（批跑 cleanup 后仍可见）
                    # 注意：python_exe 不加引号（路径无空格），否则 cmd 内层引号与外层冲突导致秒退
                    platform_args_str = " ".join(platform_args) if platform_args else ""
                    start_command = (
                        f'start "{window_title}" cmd /c "cd /d {work_dir} && '
                        f'{python_exe} {rel_path_normalized} {platform_args_str}"'
                    )
                    process = subprocess.Popen(
                        start_command,
                        shell=True,  # 使用shell=True来执行start命令
                        cwd=work_dir,  # 设置工作目录
                        creationflags=subprocess.CREATE_NO_WINDOW  # 隐藏启动命令本身的窗口
                    )
                    # 注意：使用start命令时，返回的process是start命令的进程，不是客户端进程
                    # 实际客户端会在新窗口中运行
                    logger.info(f"客户端 {i + 1} 已在新窗口中启动")
                    logger.info(f"  原始路径: {script_path}")
                    logger.info(f"  绝对路径: {abs_script_path}")
                    logger.info(f"  相对路径: {rel_path_normalized}")
                    logger.info(f"  工作目录: {work_dir}")
                    logger.info(f"  窗口标题: {window_title}")
                    logger.info(f"  启动命令: {start_command}")
                    logger.info(f"  提示: 如果看不到窗口，请检查任务栏或使用 Alt+Tab 切换")
                    process = TrackedClientProcess(
                        os.path.basename(abs_script_path),
                        window_title,
                    )
                    process.resolve_pid(wait_seconds=6.0, exclude_pids=assigned_pids)
                    if process.pid:
                        assigned_pids.add(process.pid)
                        logger.info(f"  已解析客户端 Python PID: {process.pid}")
                    else:
                        logger.warning(
                            f"  暂未解析到 {os.path.basename(abs_script_path)} 的 Python PID，"
                            "后续将按脚本名继续检测"
                        )
                else:
                    # Linux/Mac: 使用默认方式
                    process = subprocess.Popen(command)
                
                logger.info(f"客户端 {i + 1} 已启动，PID: {process.pid}")
                processes.append(process)
                
                # 等待后再启动下一个客户端 (确保顺序连接)
                if i < len(client_scripts) - 1:
                    logger.info(f"等待 {wait_between} 秒后启动下一个客户端（确保连接顺序）...")
                    time.sleep(wait_between)
                    
                    # 验证当前客户端进程仍在运行
                    if process.poll() is None:
                        logger.info(f"✓ 客户端 {i + 1} 进程运行正常")
                    else:
                        logger.warning(f"⚠ 客户端 {i + 1} 进程已退出，返回码: {process.returncode}")
                    
            except FileNotFoundError:
                logger.error(f"客户端脚本不存在: {script_path}")
                # 继续启动其他客户端
                continue
            except PermissionError:
                logger.error(f"没有权限执行客户端: {script_path}")
                # 继续启动其他客户端
                continue
            except Exception as e:
                logger.error(f"启动客户端时发生错误: {e}", exc_info=True)
                # 继续启动其他客户端
                continue
        
        self.client_processes = processes
        logger.info(f"成功启动 {len(processes)}/{len(client_scripts)} 个客户端")
        return processes
    
    def wait_for_clients_connected(
        self,
        expected_count: int = 4,
        timeout: int = 30,
        check_interval: int = 2,
        expected_client_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        等待所有客户端连接到服务器
        
        通过检测服务器端口连接数或WebSocket连接状态来判断客户端是否已连接。
        
        Args:
            expected_count: 期望连接的客户端数量，默认4个
            timeout: 超时时间（秒），默认30秒
            check_interval: 检查间隔（秒），默认2秒
            
        Returns:
            四席全部登记就绪返回 True
        """
        logger.info(f"等待 {expected_count} 个客户端连接到服务器...")
        logger.info(f"超时时间: {timeout} 秒，检查间隔: {check_interval} 秒")
        
        import socket
        import time
        
        start_time = time.time()
        elapsed = 0
        active_clients = 0
        
        while elapsed < timeout:
            try:
                # 方法1: 尝试连接到服务器端口，检测是否有监听
                # 注意：这只能检测服务器是否在监听，不能检测客户端连接数
                # 但我们可以通过多次尝试连接来间接判断
                
                # 方法2: 按脚本名检查真实 Python 客户端（避免 VirtualProcess 误报）
                if psutil is not None and self.client_processes:
                    script_paths = getattr(self, "_last_client_scripts", [])
                    if script_paths:
                        active_clients = _count_live_client_scripts(script_paths)
                    else:
                        active_clients = sum(
                            1 for p in self.client_processes if p.poll() is None
                        )
                else:
                    active_clients = 0
                    for i, process in enumerate(self.client_processes):
                        if process.poll() is None:
                            active_clients += 1
                        else:
                            logger.warning(
                                f"客户端 {i+1} 进程已退出，返回码: {process.returncode}"
                            )
                
                if active_clients >= expected_count:
                    logger.info(f"✓ 检测到 {active_clients} 个客户端进程正在运行")
                    # 额外等待几秒，确保连接建立
                    logger.info("等待 5 秒确保所有连接完全建立...")
                    time.sleep(5)
                    return True
                
                # 方法3: 尝试检测服务器端口连接数（需要服务器支持）
                # 这里我们简化处理，只检查进程状态
                
                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                if remaining > 0:
                    logger.info(f"已等待 {elapsed:.1f} 秒，剩余 {remaining:.1f} 秒... (活跃客户端: {active_clients}/{expected_count})")
                    time.sleep(check_interval)
                
            except Exception as e:
                logger.warning(f"检测客户端连接状态时出错: {e}")
                time.sleep(check_interval)
                elapsed = time.time() - start_time
        
        logger.warning(f"⚠️ 等待客户端连接超时 ({timeout} 秒)")
        logger.warning(f"   活跃客户端进程数: {active_clients}/{expected_count}")
        logger.warning("   可能原因:")
        logger.warning("   1. 客户端连接失败")
        logger.warning("   2. 服务器未正确启动")
        logger.warning("   3. 网络连接问题")
        logger.warning("   4. 客户端脚本执行错误")
        logger.warning("   建议: 检查客户端窗口的输出日志")
        
        return False
    
    def cleanup(self) -> None:
        """
        清理所有进程
        
        终止所有服务器和客户端进程，释放资源。
        """
        logger.info("开始清理所有进程...")

        # 先按脚本名强杀全部客户端，避免批次间 yf1/yf2 残留占 1/3 号位
        if getattr(self, "_last_client_scripts", None):
            _kill_all_client_script_processes(self._last_client_scripts)
        
        # 终止所有客户端进程
        for i, process in enumerate(self.client_processes):
            try:
                if process.poll() is None:  # 进程仍在运行
                    logger.info(f"终止客户端进程 {i + 1}, PID: {process.pid}")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"客户端进程 {process.pid} 未响应终止信号，强制结束")
                        process.kill()
            except Exception as e:
                logger.error(f"终止客户端进程时发生错误: {e}")
        
        # 终止服务器进程
        if self.server_process is not None:
            try:
                if self.server_process.poll() is None:  # 进程仍在运行
                    logger.info(f"终止服务器进程, PID: {self.server_process.pid}")
                    self.server_process.terminate()
                    try:
                        self.server_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"服务器进程 {self.server_process.pid} 未响应终止信号，强制结束")
                        self.server_process.kill()
            except Exception as e:
                logger.error(f"终止服务器进程时发生错误: {e}")
        
        # 使用进程监控器确保服务器进程已终止
        # 注意：不要杀死所有python.exe进程，因为GUI本身也是Python进程
        process_names = ['guandan_offline_v1006.exe']
        self.process_monitor.kill_all(process_names)
        
        # 清理由 start 启动的残留 Python 客户端（按脚本名匹配）
        if psutil is not None and getattr(self, "_last_client_scripts", None):
            _kill_all_client_script_processes(self._last_client_scripts)
        
        # 额外清理由 start "客户端X: ..." 打开的残留 cmd 窗口
        # 仅匹配窗口标题前缀“客户端”，避免误杀普通终端
        if sys.platform == 'win32':
            try:
                subprocess.run(
                    ['taskkill', '/F', '/FI', 'WINDOWTITLE eq 客户端*'],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                logger.info("已执行客户端 cmd 窗口清理（标题: 客户端*）")
            except Exception as e:
                logger.debug(f"清理客户端 cmd 窗口失败（可忽略）: {e}")
        
        # 清空进程列表
        self.client_processes = []
        self.server_process = None

        if not _wait_port_free():
            logger.warning("端口 23456 仍被占用，下一批连接可能失败")
        else:
            logger.info("端口 23456 已释放")
        time.sleep(2)
        
        logger.info("清理完成")
