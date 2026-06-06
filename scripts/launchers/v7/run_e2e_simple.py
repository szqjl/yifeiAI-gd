#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7端到端测试 - 简化版本
队伍A: yf1_v7 (玩家0) + yf2_v7 (玩家2)
队伍B: lalala_client3 (玩家1) + lalala_client4 (玩家3)
"""

import subprocess
import time
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.utils.v7_paths import get_server_exe, get_server_argv, get_v7_client_scripts

GAMES_COUNT = 12
DELAY_BETWEEN_CLIENTS = 3


def main():
    server_exe = get_server_exe(REPO_ROOT)
    server_argv = get_server_argv(REPO_ROOT)
    client_scripts = get_v7_client_scripts(REPO_ROOT)
    print("="*60)
    print(f"V7端到端测试 - {GAMES_COUNT}局")
    print("="*60)
    print("队伍A: yf1_v7 (0) + yf2_v7 (2)")
    print("队伍B: lalala_client3 (1) + lalala_client4 (3)")
    print("="*60)
    
    # 启动服务器
    print("\n🚀 启动服务器...")
    server = subprocess.Popen(
        [server_exe, server_argv],
        cwd=os.path.dirname(server_exe),
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
    )
    
    # 等待服务器启动
    print("⏳ 等待服务器就绪...")
    time.sleep(10)
    
    clients = []
    titles = ["yf1_v7", "lalala_client3", "yf2_v7", "lalala_client4"]

    for title, script in zip(titles, client_scripts):
        print(f"\n🚀 启动 {title}...")
        time.sleep(DELAY_BETWEEN_CLIENTS)
        proc = subprocess.Popen(
            ["python", script],
            cwd=str(REPO_ROOT),
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )
        clients.append((title, proc))
    
    print("\n" + "="*60)
    print("所有客户端已启动，开始对局...")
    print("="*60)
    
    # 等待服务器结束
    try:
        server.wait()
        print("\n✓ 服务器已结束")
    except KeyboardInterrupt:
        print("\n收到退出信号")
    
    # 清理客户端
    print("\n清理客户端进程...")
    for name, client in clients:
        try:
            if client.poll() is None:
                client.terminate()
                print(f"已终止 {name}")
        except:
            pass
    
    print("✓ 测试完成")

if __name__ == "__main__":
    main()
