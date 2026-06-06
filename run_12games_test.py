#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7端到端测试 - 12局完整对战
改进版：解决编码问题，添加详细日志
"""

import subprocess
import time
import sys
import os
import socket
import signal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.utils.v7_paths import get_model_file, get_server_exe, get_server_argv, get_v7_client_scripts

GAMES_COUNT = 12
DELAY_BETWEEN_CLIENTS = 3
MAX_WAIT_TIME = GAMES_COUNT * 120 + 60  # 每局约120秒 + 60秒缓冲
PORT = 23456

def check_port(port, timeout=30):
    """检查端口是否监听"""
    for _ in range(timeout):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            if sock.connect_ex(('127.0.0.1', port)) == 0:
                sock.close()
                return True
            sock.close()
        except:
            pass
        time.sleep(1)
    return False

def main():
    print("="*60)
    print(f"V7端到端测试 - {GAMES_COUNT}局完整对战")
    print("队伍A: yf1_v7 (位置0) + yf2_v7 (位置2)")
    print("队伍B: lalala_client3 (位置1) + lalala_client4 (位置3)")
    print("="*60)
    
    server_exe = get_server_exe(REPO_ROOT)
    server_argv = get_server_argv(REPO_ROOT)
    client_scripts = get_v7_client_scripts(REPO_ROOT)

    required_files = [
        server_exe,
        *client_scripts,
        str(REPO_ROOT / "src" / "communication" / "lalala_adapter.py"),
        str(REPO_ROOT / "src" / "decision" / "ultimate_win_rate_engine_v7.py"),
    ]
    
    print("\n检查必要文件...")
    all_exists = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file}")
        else:
            print(f"✗ {file}")
            all_exists = False
    
    if not all_exists:
        print("\n✗ 部分文件缺失，退出")
        return

    model_path = Path(get_model_file(REPO_ROOT))
    if not model_path.is_file():
        print(f"⚠ 模型未找到: {model_path}（将使用规则回退）")
    
    # 清空旧日志
    log_dir = Path("logs")
    if log_dir.exists():
        for log_file in log_dir.glob("yf*_v7*.log"):
            try:
                log_file.unlink()
            except:
                pass
    
    # 启动服务器（使用shell=True避免编码问题）
    print("\n🚀 启动服务器...")
    server = subprocess.Popen(
        [server_exe, server_argv],
        cwd=os.path.dirname(server_exe),
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # 等待服务器启动
    print("⏳ 等待服务器启动...")
    if not check_port(PORT, timeout=60):
        print("✗ 服务器启动失败")
        try:
            server.terminate()
        except:
            pass
        return
    
    print("✓ 服务器已启动，端口监听中")
    
    clients = []
    titles = ["yf1_v7", "lalala_client3", "yf2_v7", "lalala_client4"]

    for title, script in zip(titles, client_scripts):
        rel = Path(script).relative_to(REPO_ROOT).as_posix()
        print(f"\n🚀 启动 {title}...")
        proc = subprocess.Popen(
            f"python {rel}",
            shell=True,
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        clients.append((title, proc))
        time.sleep(DELAY_BETWEEN_CLIENTS)
    
    print("\n" + "="*60)
    print(f"所有客户端已启动，开始 {GAMES_COUNT} 局对战...")
    print("预计等待时间: ~{:.1f} 分钟".format(MAX_WAIT_TIME/60))
    print("="*60)
    
    # 等待游戏结束
    start_time = time.time()
    last_log_check = start_time
    game_count = 0
    
    try:
        while True:
            # 检查服务器状态
            server_status = server.poll()
            if server_status is not None:
                print(f"\n✓ 服务器已退出，返回码: {server_status}")
                break
            
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > MAX_WAIT_TIME:
                print(f"\n⚠️ 超时，强制结束 (已运行 {elapsed/60:.1f} 分钟)")
                break
            
            # 每30秒检查一次日志
            if time.time() - last_log_check > 30:
                last_log_check = time.time()
                # 检查日志文件
                log_files = list(log_dir.glob("yf*_v7*.log"))
                if log_files:
                    latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
                    try:
                        with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            if lines:
                                last_line = lines[-1].strip()
                                print(f"[{time.strftime('%H:%M:%S')}] 最新日志: {last_line[:80]}")
                    except:
                        pass
            
            # 检查客户端状态
            for name, client in clients:
                status = client.poll()
                if status is not None:
                    print(f"\n⚠️ {name} 已退出，返回码: {status}")
            
            time.sleep(5)
    
    except KeyboardInterrupt:
        print("\n收到退出信号")
    
    finally:
        # 清理进程
        print("\n清理进程...")
        for name, client in clients:
            try:
                if client.poll() is None:
                    client.terminate()
                    print(f"已终止 {name}")
            except Exception as e:
                print(f"终止 {name} 时出错: {e}")
        
        try:
            if server.poll() is None:
                server.terminate()
                print("已终止服务器")
        except Exception as e:
            print(f"终止服务器时出错: {e}")
        
        print("\n✓ 测试完成")
        print("\n--- 日志文件 ---")
        log_files = sorted(log_dir.glob("yf*_v7*.log"), key=lambda x: x.stat().st_mtime)
        for log_file in log_files:
            print(f"{log_file.name}: {log_file.stat().st_size} bytes")

if __name__ == "__main__":
    main()
