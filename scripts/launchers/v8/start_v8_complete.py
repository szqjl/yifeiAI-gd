#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 完整系统启动脚本 (OpenGuanDan 新平台)
从 v7 complete 复制而来，适配房间模型启动
"""

import subprocess
import time
import sys
import os
import socket
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

# V8: 默认路径
_V8_SERVER = REPO_ROOT / "offline_platform" / "openguandan_latest" / "guandan.exe"
_V8_PORT = 8181


def check_port_listening(port, timeout=30):
    """检查端口是否在监听"""
    print(f"检查端口 {port} 是否监听...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                print(f"✓ 端口 {port} 已监听")
                return True
        except OSError:
            pass
        time.sleep(1)
    print(f"✗ 端口 {port} 在 {timeout} 秒内未监听")
    return False


def start_server():
    """启动 V8 服务器（无命令行参数，局数由 CREATE_ROOM 传递）"""
    server_path = os.environ.get("SERVER_EXE", str(_V8_SERVER))
    if not os.path.exists(server_path):
        print(f"✗ 服务器文件不存在: {server_path}")
        return None

    print("🚀 启动服务器 (OpenGuanDan)...")
    print(f"服务器路径: {server_path}")

    process = subprocess.Popen(
        [server_path],
        cwd=os.path.dirname(server_path),
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    print(f"✓ 服务器已启动，PID: {process.pid}")

    if check_port_listening(_V8_PORT, timeout=30):
        print("✓ 服务器就绪 (端口 8181)，可以连接客户端")
        return process

    print("✗ 服务器启动失败或未监听端口")
    process.terminate()
    return None


def start_client(script_path, extra_args="", delay=0, window_title="客户端"):
    """启动客户端（V8: room-based）"""
    if delay > 0:
        print(f"⏳ 等待 {delay} 秒后启动 {window_title}...")
        time.sleep(delay)

    print(f"🚀 启动 {window_title}: {script_path}")

    if not os.path.exists(script_path):
        print(f"✗ 客户端文件不存在: {script_path}")
        return None

    rel = Path(script_path).relative_to(REPO_ROOT)
    if sys.platform == "win32":
        if extra_args:
            cmd_line = f'start "{window_title}" cmd /k "cd /d {REPO_ROOT} && python {rel.as_posix()} {extra_args}"'
        else:
            cmd_line = f'start "{window_title}" cmd /k "cd /d {REPO_ROOT} && python {rel.as_posix()}"'
        process = subprocess.Popen(
            cmd_line,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        process = subprocess.Popen(["python", str(script_path)], cwd=str(REPO_ROOT))

    print(f"✓ {window_title} 已启动，PID: {process.pid}")
    return process


def main():
    """主函数 — V8 房间模型启动"""
    print("=" * 60)
    print("V8 终极胜率导向系统完整启动 (OpenGuanDan)")
    print("=" * 60)

    # 检查必要文件
    required_files = [
        str(_V8_SERVER),
        "src/communication/yf1_v8.py",
        "src/communication/yf2_v8.py",
        "src/communication/v8_lalala_adapter.py",
    ]

    print("检查必要文件...")
    all_exists = True
    for file_path in required_files:
        path = Path(file_path) if not file_path.startswith(str(REPO_ROOT)) else Path(file_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        exists = path.exists()
        mark = "✓" if exists else "✗"
        print(f"{mark} {path}")
        if not exists:
            all_exists = False

    if not all_exists:
        print("\n✗ 必要客户端/服务器文件缺失，无法启动")
        return

    print("\n" + "=" * 60)
    print("启动序列 (房间模型: CREATE_ROOM → JOIN_ROOM)")
    print("=" * 60)

    server_process = start_server()
    if not server_process:
        print("✗ 服务器启动失败，终止启动")
        return

    print("\n等待 3 秒，确保服务器完全就绪...")
    time.sleep(3)

    clients = []

    try:
        # 1. yf1_v8 — CREATE_ROOM, seat 0, 10 局
        client1 = start_client(
            "src/communication/yf1_v8.py",
            extra_args="--platform openguandan --role creator --games 10",
            delay=0,
            window_title="yf1_v8 (Creator)"
        )
        if client1:
            clients.append(client1)

        print("⏳ 等待 5 秒让 yf1_v8 创建房间并写入 roomId...")
        time.sleep(5)

        # 2. yf2_v8 — JOIN_ROOM, seat 2
        client2 = start_client(
            "src/communication/yf2_v8.py",
            extra_args="--platform openguandan --role joiner",
            delay=0,
            window_title="yf2_v8 (Seat 2)"
        )
        if client2:
            clients.append(client2)

        time.sleep(2)

        # 3. lalala client3 — JOIN_ROOM, seat 1
        client3 = start_client(
            "src/communication/v8_lalala_adapter.py",
            extra_args="client3 --platform openguandan --role joiner",
            delay=0,
            window_title="lalala_client3 (Seat 1)"
        )
        if client3:
            clients.append(client3)

        time.sleep(2)

        # 4. lalala client4 — JOIN_ROOM, seat 3
        client4 = start_client(
            "src/communication/v8_lalala_adapter.py",
            extra_args="client4 --platform openguandan --role joiner",
            delay=0,
            window_title="lalala_client4 (Seat 3)"
        )
        if client4:
            clients.append(client4)

        print("\n" + "=" * 60)
        print("V8 启动完成")
        print("=" * 60)
        print(f"✓ 服务器进程: PID {server_process.pid}")
        print(f"✓ 客户端进程: {len(clients)} 个")
        print("\n预期队伍分配:")
        print("队伍A (0+2): yf1_v8 + yf2_v8")
        print("队伍B (1+3): lalala client3 + client4")
        print(f"\n房间协调: tmp/.v8_room_id")
        print("按 Ctrl+C 退出")

        while True:
            time.sleep(1)
            if server_process.poll() is not None:
                print(f"\n⚠️ 服务器进程已退出，返回码: {server_process.returncode}")
                break

    except KeyboardInterrupt:
        print("\n\n收到退出信号，正在清理进程...")
        for i, client in enumerate(clients):
            try:
                if client.poll() is None:
                    print(f"终止客户端 {i + 1}...")
                    client.terminate()
            except Exception:
                pass
        try:
            if server_process.poll() is None:
                print("终止服务器...")
                server_process.terminate()
        except Exception:
            pass
        print("✓ 清理完成")


if __name__ == "__main__":
    main()
