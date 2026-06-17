#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7连接问题诊断脚本
"""

import socket
import subprocess
import os
import time
import sys

def check_port_status(port):
    """检查端口状态"""
    print(f"检查端口 {port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print(f"✓ 端口 {port} 正在监听")
            return True
        else:
            print(f"✗ 端口 {port} 未监听 (错误码: {result})")
            return False
    except Exception as e:
        print(f"✗ 端口 {port} 检查失败: {e}")
        return False

def check_server_process():
    """检查服务器进程"""
    print("检查服务器进程...")
    
    try:
        if sys.platform == 'win32':
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq guandan_offline_v1006.exe'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if 'guandan_offline_v1006.exe' in result.stdout:
                print("✓ 服务器进程正在运行")
                return True
            else:
                print("✗ 服务器进程未运行")
                return False
        else:
            # Linux/Mac
            result = subprocess.run(['pgrep', '-f', 'guandan_offline'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✓ 服务器进程正在运行")
                return True
            else:
                print("✗ 服务器进程未运行")
                return False
    except Exception as e:
        print(f"✗ 检查服务器进程失败: {e}")
        return False

def check_files():
    """检查必要文件"""
    print("检查必要文件...")
    
    files = {
        "服务器": "D:\\guandanscore\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe",
        "yf1_v7": "src/communication/yf1_v7.py",
        "client3": "D:\\NYGD\\lalala\\client3.py",
        "yf2_v7": "src/communication/yf2_v7.py",
        "client4": "D:\\NYGD\\lalala\\client4.py",
        "终极胜率模型": "models/bc_model_ultimate_win_rate.pth"
    }
    
    all_exist = True
    for name, path in files.items():
        if os.path.exists(path):
            print(f"✓ {name}: {path}")
        else:
            print(f"✗ {name}: {path} - 文件不存在")
            all_exist = False
    
    return all_exist

def test_websocket_connection():
    """测试WebSocket连接"""
    print("测试WebSocket连接...")
    
    try:
        import websockets
        import asyncio
        
        async def test_connect():
            try:
                uri = "ws://127.0.0.1:23456/game/test"
                async with websockets.connect(uri, timeout=5) as websocket:
                    print("✓ WebSocket连接成功")
                    return True
            except Exception as e:
                print(f"✗ WebSocket连接失败: {e}")
                return False
        
        return asyncio.run(test_connect())
    except ImportError:
        print("⚠️ websockets库未安装，跳过WebSocket测试")
        return None
    except Exception as e:
        print(f"✗ WebSocket测试失败: {e}")
        return False

def diagnose_client_error():
    """诊断客户端连接错误"""
    print("诊断客户端连接错误...")
    
    error_msg = """
    Traceback (most recent call last):
    File "D:\\NYGD\\lalala\\client4.py", line 43, in <module>
    ws.connect()
    File "...\\ws4py\\client\\__init__.py", line 225, in connect
    self.sock.connect(self.bind_addr)
    """
    
    print("错误分析:")
    print("- client4.py 试图连接到 ws://127.0.0.1:23456/game/client4")
    print("- 连接被拒绝，说明服务器未启动或端口未监听")
    print("- 这是典型的'服务器未就绪'错误")
    
    print("\n解决方案:")
    print("1. 确保服务器先启动")
    print("2. 等待服务器完全就绪后再启动客户端")
    print("3. 检查端口23456是否被其他程序占用")
    print("4. 按正确顺序启动客户端")

def main():
    """主诊断函数"""
    print("=" * 60)
    print("V7系统连接问题诊断")
    print("=" * 60)
    
    # 1. 检查文件
    print("\n1. 文件检查")
    print("-" * 30)
    files_ok = check_files()
    
    # 2. 检查服务器进程
    print("\n2. 服务器进程检查")
    print("-" * 30)
    server_running = check_server_process()
    
    # 3. 检查端口
    print("\n3. 端口检查")
    print("-" * 30)
    port_listening = check_port_status(23456)
    
    # 4. WebSocket连接测试
    print("\n4. WebSocket连接测试")
    print("-" * 30)
    websocket_ok = test_websocket_connection()
    
    # 5. 错误诊断
    print("\n5. 错误诊断")
    print("-" * 30)
    diagnose_client_error()
    
    # 6. 总结和建议
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    if not files_ok:
        print("❌ 文件缺失 - 请检查文件路径")
    
    if not server_running:
        print("❌ 服务器未运行 - 请先启动服务器")
    elif not port_listening:
        print("❌ 服务器运行但端口未监听 - 服务器可能启动失败")
    else:
        print("✅ 服务器状态正常")
    
    print("\n推荐操作:")
    if not server_running:
        print("1. 手动启动服务器:")
        print("   D:\\guandanscore\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe")
        print("2. 等待服务器显示就绪消息")
        print("3. 使用 START_V7_COMPLETE.bat 启动完整系统")
    else:
        print("1. 服务器已运行，可以启动客户端")
        print("2. 按顺序启动: yf1_v7 -> client3 -> yf2_v7 -> client4")
        print("3. 每个客户端之间等待足够时间")

if __name__ == "__main__":
    main()