"""
自动游戏运行器
自动运行M1客户端与client对战，生成游戏记录用于评估
"""

import subprocess
import time
import logging
import sys
import os
import threading
import queue
from pathlib import Path
from typing import Optional, Dict
import json

logger = logging.getLogger(__name__)


class AutoGameRunner:
    """自动游戏运行器"""
    
    def __init__(
        self,
        server_path: str = None,
        num_games: int = 50,
        client1: str = "src/communication/yf1_m1.py",  # 0号位 (Team A) - 延迟3秒连接
        client2: str = "src/communication/run_lalala_client3.py",  # 1号位 (Team B) - 延迟8秒连接
        client3: str = "src/communication/yf2_m1.py",  # 2号位 (Team A) - 延迟9秒连接
        client4: str = "src/communication/run_lalala_client4.py"  # 3号位 (Team B) - 延迟18秒连接
    ):
        """
        初始化游戏运行器
        
        Args:
            server_path: 游戏服务器路径
            num_games: 目标游戏场数
            client1: 0号位客户端（Team A）- yf1_m1
            client2: 1号位客户端（Team B）- client3
            client3: 2号位客户端（Team A）- yf2_m1
            client4: 3号位客户端（Team B）- client4
            
        注意：客户端位置按连接顺序分配：
        - 第1个连接 → 0号位
        - 第2个连接 → 1号位
        - 第3个连接 → 2号位
        - 第4个连接 → 3号位
        
        位置分配规则：
        - 0号位和2号位是一队（Team A）
        - 1号位和3号位是一队（Team B）
        """
        self.server_path = server_path or self._find_server_path()
        self.num_games = num_games
        # 注意：客户端位置按连接顺序分配（第1个连接→0号位，第2个连接→1号位，第3个连接→2号位，第4个连接→3号位）
        # 为了确保M1和M2在0号和2号位，需要调整顺序：
        # - yf1_m1 (延迟3秒) → 第1个连接 → 0号位 ✅
        # - run_lalala_client3 (延迟8秒) → 第2个连接 → 1号位 ✅
        # - yf2_m1 (延迟3秒) → 第3个连接 → 2号位 ✅
        # - run_lalala_client4 (延迟18秒) → 第4个连接 → 3号位 ✅
        self.clients = [client1, client2, client3, client4]
        self.game_records_dir = Path("game_records")
        
        # 验证客户端路径是否存在，如果不存在则尝试查找
        for i, client_path in enumerate(self.clients, 1):
            client_file = Path(client_path)
            if not client_file.exists():
                # 尝试查找客户端文件
                possible_paths = [
                    client_path,
                    f"src/communication/{Path(client_path).name}",
                    Path(client_path).name
                ]
                found = False
                for possible_path in possible_paths:
                    if Path(possible_path).exists():
                        self.clients[i-1] = possible_path
                        found = True
                        logger.info(f"✅ 找到客户端{i}路径: {possible_path}")
                        break
                if not found:
                    logger.warning(f"⚠️ 客户端{i}路径不存在: {client_path}，可能无法启动")
        
    def _find_server_path(self) -> Optional[str]:
        """查找游戏服务器路径"""
        # 常见的服务器路径（按优先级排序）
        common_paths = [
            r"D:\GDAI\server\windows\guandan_offline_v1006.exe",  # 用户提供的路径（最新）
            r"D:\GDAI\离线平台\windows\guandan_offline_v1006.exe",  # 用户提供的路径（旧）
            r"D:\guandan_offline_v1006\windows\guandan_offline_v1006.exe",
            r"C:\guandan_offline_v1006\windows\guandan_offline_v1006.exe",
            r"D:\GDAI\server\guandan_offline_v1006.exe",
            r"D:\GDAI\离线平台\guandan_offline_v1006.exe",
            "guandan_offline_v1006.exe"  # 系统PATH中的可执行文件
        ]
        
        for path in common_paths:
            if Path(path).exists():
                logger.info(f"✅ 找到游戏服务器: {path}")
                return path
        
        logger.warning("⚠️ 未找到游戏服务器，请手动指定server_path")
        logger.info("提示：可以在工作流启动时使用 --server_path 参数指定")
        return None
    
    def run_games(self, timeout: int = 7200) -> Dict:  # 增加到2小时，确保50场比赛有足够时间
        """
        运行游戏对战
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            运行结果字典
        """
        if not self.server_path:
            # 尝试再次查找服务器路径
            found_path = self._find_server_path()
            if found_path:
                self.server_path = found_path
                logger.info(f"✅ 自动找到服务器路径: {self.server_path}")
            else:
                return {
                    "success": False, 
                    "error": "服务器路径未设置，且无法自动找到。请使用 --server_path 参数指定服务器路径"
                }
        
        logger.info(f"开始运行 {self.num_games} 场游戏对战")
        logger.info(f"服务器: {self.server_path}")
        logger.info(f"客户端配置（按连接顺序分配位置）：")
        logger.info(f"  0号位 (Team A): {Path(self.clients[0]).name}")
        logger.info(f"  1号位 (Team B): {Path(self.clients[1]).name}")
        logger.info(f"  2号位 (Team A): {Path(self.clients[2]).name}")
        logger.info(f"  3号位 (Team B): {Path(self.clients[3]).name}")
        logger.info(f"完整路径: {', '.join(self.clients)}")
        
        # 说明自动重启机制
        import math
        single_run_limit = 3  # 服务器每次启动只运行3场
        total_runs = math.ceil(self.num_games / single_run_limit)
        restart_count = total_runs - 1
        logger.info(f"")
        logger.info(f"📋 自动重启说明：")
        logger.info(f"  - 服务器每次启动只运行 {single_run_limit} 场比赛")
        logger.info(f"  - 目标场数: {self.num_games} 场")
        logger.info(f"  - 预计需要 {total_runs} 次运行（{restart_count} 次自动重启）")
        logger.info(f"  - batch_executor会自动重启服务器，直到完成所有 {self.num_games} 场比赛")
        logger.info(f"  - 无需手动操作，请耐心等待...")
        logger.info(f"")
        
        # 清理残留进程（重要：确保可以重新启动）
        logger.info("🧹 清理残留进程...")
        self._cleanup_residual_processes()
        
        # 记录开始前的游戏记录数量
        initial_count = len(list(self.game_records_dir.glob("*.json"))) if self.game_records_dir.exists() else 0
        
        try:
            # 使用batch_executor运行游戏
            cmd = [
                "python", "-m", "batch_executor",
                "--server-path", self.server_path,
                "--target-games", str(self.num_games),
                "--clients"
            ] + self.clients
            
            logger.info(f"执行命令: {' '.join(cmd)}")
            logger.info(f"")
            logger.info(f"📋 batch_executor自动重启说明：")
            logger.info(f"  - 服务器每次启动只运行 3 场比赛（平台限制）")
            logger.info(f"  - 目标场数: {self.num_games} 场")
            logger.info(f"  - 预计需要 {math.ceil(self.num_games / 3)} 次服务器启动")
            logger.info(f"  - batch_executor会自动重启服务器，直到完成所有 {self.num_games} 场比赛")
            logger.info(f"  - 请耐心等待，您将看到服务器重启的实时日志...")
            logger.info(f"")
            
            # Windows上使用GBK编码，其他系统使用UTF-8
            encoding = 'gbk' if sys.platform == 'win32' else 'utf-8'
            
            # 使用实时输出模式，可以看到batch_executor的实时日志和服务器重启过程
            logger.info("🚀 开始执行batch_executor（实时输出模式，可以看到服务器重启过程）...")
            logger.info("="*60)
            
            # 启动batch_executor进程（使用Popen以便监控）
            import time as time_module
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,  # 需要捕获输出以监控进度
                stderr=subprocess.PIPE,
                encoding=encoding,
                errors='replace'
            )
            
            # 进度监控：检查游戏记录增量
            check_interval = 30  # 每30秒检查一次
            last_record_count = initial_count
            no_progress_count = 0  # 连续无进度次数
            max_no_progress = 6  # 最多6次无进度（3分钟）则认为卡住
            start_time = time_module.time()
            
            logger.info(f"📊 开始监控batch_executor进度（每{check_interval}秒检查一次游戏记录增量）...")
            
            # 实时输出和进度监控
            import threading
            import queue
            output_queue = queue.Queue()
            
            def read_output():
                """读取进程输出"""
                try:
                    if process.stdout:
                        for line in process.stdout:
                            line = line.strip()
                            if line:
                                output_queue.put(('stdout', line))
                                # 实时打印到控制台
                                print(f"[batch_executor] {line}")
                    if process.stderr:
                        for line in process.stderr:
                            line = line.strip()
                            if line:
                                output_queue.put(('stderr', line))
                                # 实时打印到控制台
                                print(f"[batch_executor ERROR] {line}", file=sys.stderr)
                except Exception as e:
                    logger.debug(f"读取输出异常: {e}")
            
            # 启动输出读取线程
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            # 主循环：监控进程和进度
            while True:
                # 检查进程是否已结束
                return_code = process.poll()
                if return_code is not None:
                    logger.info(f"batch_executor进程已结束，返回码: {return_code}")
                    break
                
                # 检查超时
                elapsed = time_module.time() - start_time
                if elapsed >= timeout:
                    logger.error(f"batch_executor执行超时（{elapsed//60:.1f} 分钟）")
                    process.kill()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.error("无法终止batch_executor进程")
                    # 获取当前游戏记录数量
                    current_count = len(list(self.game_records_dir.glob("*.json"))) if self.game_records_dir.exists() else 0
                    return {
                        "success": False,
                        "new_games": current_count - initial_count,
                        "target_games": self.num_games,
                        "error": f"执行超时（{timeout}秒）"
                    }
                
                # 检查进度（游戏记录增量）
                current_count = len(list(self.game_records_dir.glob("*.json"))) if self.game_records_dir.exists() else 0
                if current_count > last_record_count:
                    logger.info(f"✅ 检测到进度：游戏记录从 {last_record_count} 增加到 {current_count}（+{current_count - last_record_count}）")
                    last_record_count = current_count
                    no_progress_count = 0
                else:
                    no_progress_count += 1
                    if no_progress_count >= max_no_progress:
                        elapsed_minutes = elapsed / 60
                        logger.warning(f"⚠️ 检测到batch_executor可能卡住：")
                        logger.warning(f"  - 已执行 {elapsed_minutes:.1f} 分钟")
                        logger.warning(f"  - 游戏记录数量: {current_count}（目标: {initial_count + self.num_games}）")
                        logger.warning(f"  - 连续 {no_progress_count * check_interval} 秒无新记录")
                        logger.warning(f"  - 可能原因：服务器卡住、客户端连接失败、batch_executor内部错误")
                        
                        # 检查进程是否真的在运行
                        if process.poll() is None:
                            logger.warning("batch_executor进程仍在运行，但无进度，尝试终止并重试...")
                            process.kill()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                logger.error("无法终止batch_executor进程")
                            
                            # 清理残留进程
                            self._cleanup_residual_processes()
                            
                            return {
                                "success": False,
                                "new_games": current_count - initial_count,
                                "target_games": self.num_games,
                                "error": f"检测到卡住（{elapsed_minutes:.1f}分钟无进度），已终止进程",
                                "suggestion": "建议检查服务器和客户端状态后重试"
                            }
                        else:
                            # 进程已结束，但可能异常退出
                            break
                
                # 等待一段时间再检查
                time_module.sleep(check_interval)
            
            # 等待输出线程完成
            output_thread.join(timeout=2)
            
            logger.info("="*60)
            logger.info(f"batch_executor执行完成，返回码: {return_code}")
            
            # 检查结束后的游戏记录数量
            final_count = len(list(self.game_records_dir.glob("*.json"))) if self.game_records_dir.exists() else 0
            new_games = final_count - initial_count
            logger.info(f"")
            logger.info(f"📊 游戏记录统计:")
            logger.info(f"  开始前: {initial_count} 场")
            logger.info(f"  结束后: {final_count} 场")
            logger.info(f"  新增: {new_games} 场（目标: {self.num_games} 场）")
            logger.info(f"")
            
            # 由于使用实时输出模式（stdout=None），无法从result.stdout获取输出
            # 但可以通过游戏记录数量判断是否成功
            # 服务器信息可以从batch_executor的日志文件中获取（如果需要）
            server_info = None
            
            if result.returncode == 0:
                if new_games >= self.num_games * 0.8:  # 至少完成80%的目标
                    logger.info(f"✅ 游戏对战完成，新增 {new_games} 场游戏记录（目标: {self.num_games} 场）")
                    return {
                        "success": True,
                        "new_games": new_games,
                        "target_games": self.num_games,
                        "server_info": server_info
                    }
                else:
                    logger.warning(f"⚠️ 游戏对战完成，但新增记录数不足: {new_games}/{self.num_games}")
                    logger.warning("可能原因：服务器重启失败，或游戏记录生成异常")
                    return {
                        "success": False,
                        "new_games": new_games,
                        "target_games": self.num_games,
                        "error": f"新增记录数不足: {new_games}/{self.num_games}",
                        "server_info": server_info
                    }
            else:
                logger.warning(f"⚠️ batch_executor返回非零退出码: {result.returncode}")
                logger.warning(f"新增游戏记录: {new_games} 场")
                return {
                    "success": new_games >= self.num_games * 0.5,  # 至少完成50%才认为部分成功
                    "new_games": new_games,
                    "target_games": self.num_games,
                    "error": f"batch_executor退出码: {result.returncode}",
                    "server_info": server_info
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"游戏对战超时（{timeout}秒）")
            # 超时后清理进程
            logger.info("清理超时后的残留进程...")
            self._cleanup_residual_processes()
            return {"success": False, "error": "超时"}
        except Exception as e:
            logger.error(f"运行游戏对战失败: {e}")
            # 出错后清理进程
            logger.info("清理出错后的残留进程...")
            self._cleanup_residual_processes()
            return {"success": False, "error": str(e)}
        finally:
            # 无论成功或失败，都清理残留进程
            logger.info("🧹 清理残留进程（确保可以再次运行）...")
            self._cleanup_residual_processes()
    
    def check_game_records(self, min_games: int = 50) -> bool:
        """
        检查是否有足够的游戏记录
        
        Args:
            min_games: 最少需要的游戏记录数
            
        Returns:
            是否有足够的记录
        """
        if not self.game_records_dir.exists():
            return False
        
        # 统计M1相关的游戏记录
        m1_records = list(self.game_records_dir.glob("*yf1_m1*.json"))
        count = len(m1_records)
        
        logger.info(f"当前M1游戏记录数: {count} (需要: {min_games})")
        return count >= min_games
    
    def _cleanup_residual_processes(self):
        """清理残留的服务器和客户端进程"""
        try:
            if sys.platform == 'win32':
                # Windows: 使用taskkill命令
                process_names = [
                    'guandan_offline_v1006.exe',  # 服务器进程
                ]
                
                for process_name in process_names:
                    try:
                        # 尝试终止进程
                        result = subprocess.run(
                            ['taskkill', '/F', '/IM', process_name, '/T'],
                            capture_output=True,
                            timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        )
                        if result.returncode == 0:
                            logger.info(f"✅ 已清理残留进程: {process_name}")
                        else:
                            # 检查错误信息（可能是进程不存在）
                            error_msg = result.stderr.decode('gbk', errors='replace') if result.stderr else ''
                            if "找不到进程" in error_msg or "not found" in error_msg.lower():
                                logger.debug(f"进程 {process_name} 不存在，无需清理")
                            else:
                                logger.debug(f"清理进程 {process_name} 时返回码: {result.returncode}")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"⚠️ 清理进程 {process_name} 超时")
                    except Exception as e:
                        logger.debug(f"清理进程 {process_name} 时出错（可能进程不存在）: {e}")
                
                # 等待进程完全终止
                time.sleep(2)
                
                # 检查端口是否被占用（23456）
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('127.0.0.1', 23456))
                    sock.close()
                    if result == 0:
                        logger.warning("⚠️ 端口23456仍被占用，可能需要手动关闭相关进程")
                    else:
                        logger.debug("✅ 端口23456已释放")
                except Exception as e:
                    logger.debug(f"检查端口时出错: {e}")
            else:
                # Linux/Mac: 使用kill命令
                try:
                    subprocess.run(['pkill', '-f', 'guandan_offline'], timeout=5, capture_output=True)
                    logger.info("✅ 已清理残留服务器进程")
                except Exception as e:
                    logger.debug(f"清理进程时出错: {e}")
        except Exception as e:
            logger.warning(f"清理残留进程时出错: {e}")


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description="自动游戏运行器")
    parser.add_argument("--num_games", type=int, default=50, help="目标游戏场数")
    parser.add_argument("--server_path", type=str, default=None, help="服务器路径")
    parser.add_argument("--check_only", action="store_true", help="仅检查游戏记录")
    
    args = parser.parse_args()
    
    runner = AutoGameRunner(
        server_path=args.server_path,
        num_games=args.num_games
    )
    
    if args.check_only:
        has_enough = runner.check_game_records(args.num_games)
        print(f"游戏记录检查: {'✅ 足够' if has_enough else '❌ 不足'}")
    else:
        result = runner.run_games()
        print(f"\n运行结果: {'✅ 成功' if result.get('success') else '❌ 失败'}")
        if result.get('new_games'):
            print(f"新增游戏记录: {result['new_games']}")
