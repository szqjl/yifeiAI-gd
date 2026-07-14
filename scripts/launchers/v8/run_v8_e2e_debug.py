#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7端到端测试 - 调试版本
添加详细的日志记录和错误处理
"""

import subprocess
import time
import sys
import os
import socket
import json
import signal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.utils.v7_paths import get_model_file, get_server_exe, get_server_argv, get_v7_client_scripts

GAMES_COUNT = 12
DELAY_BETWEEN_CLIENTS = 3
MAX_WAIT_TIME = GAMES_COUNT * 90 + 60  # 每局约90秒 + 60秒缓冲

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
    print(f"V7端到端测试 - {GAMES_COUNT}局")
    print("队伍A: yf1_v7 (0) + yf2_v7 (2)")
    print("队伍B: lalala_client3 (1) + lalala_client4 (3)")
    print("="*60)
    
    server_exe = get_server_exe(REPO_ROOT)
    server_argv = get_server_argv(REPO_ROOT)
    client_scripts = get_v7_client_scripts(REPO_ROOT)

    required_files = [
        server_exe,
        *client_scripts,
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
        print("\n✗ 部分文件缺失")
        return

    model_path = Path(get_model_file(REPO_ROOT))
    if not model_path.is_file():
        print(f"⚠ 模型未找到: {model_path}（将使用规则回退）")
    
    # 启动服务器
    print("\n🚀 启动服务器...")
    server = subprocess.Popen(
        [server_exe, server_argv],
        cwd=os.path.dirname(server_exe),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务器启动
    print("⏳ 等待服务器启动...")
    if not check_port(23456, timeout=45):
        print("✗ 服务器启动失败")
        server.terminate()
        return
    
    print("✓ 服务器已启动")
    
    clients = []
    titles = ["yf1_v7", "lalala_client3", "yf2_v7", "lalala_client4"]

    for title, script in zip(titles, client_scripts):
        rel = Path(script).relative_to(REPO_ROOT).as_posix()
        print(f"\n🚀 启动 {title}...")
        proc = subprocess.Popen(
            ["python", rel],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        clients.append((title, proc))
        time.sleep(DELAY_BETWEEN_CLIENTS)
    
    print("\n" + "="*60)
    print("所有客户端已启动，开始对局...")
    print("="*60)
    
    # 等待游戏结束
    start_time = time.time()
    try:
        while True:
            # 检查服务器状态
            server_status = server.poll()
            if server_status is not None:
                print(f"\n✓ 服务器已退出，返回码: {server_status}")
                # 获取服务器输出
                stdout, stderr = server.communicate()
                if stdout:
                    print("服务器标准输出:")
                    print(stdout[:2000])
                if stderr:
                    print("服务器错误输出:")
                    print(stderr[:2000])
                break
            
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > MAX_WAIT_TIME:
                print(f"\n⚠️ 超时，强制结束 (已运行 {elapsed/60:.1f} 分钟)")
                break
            
            # 检查客户端状态
            for name, client in clients:
                status = client.poll()
                if status is not None:
                    print(f"\n⚠️ {name} 已退出，返回码: {status}")
                    stdout, stderr = client.communicate()
                    if stdout:
                        print(f"{name} 标准输出: {stdout[:500]}")
                    if stderr:
                        print(f"{name} 错误输出: {stderr[:500]}")
            
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

if __name__ == "__main__":
    main()
