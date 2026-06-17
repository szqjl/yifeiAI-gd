#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V7完整系统启动脚本
确保服务器先启动，然后按正确顺序启动客户端
"""

import subprocess
import time
import sys
import os
import socket
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from src.utils.v7_paths import (
    get_model_file,
    get_server_argv,
    get_server_exe,
    get_v7_client_scripts,
)


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

def _resolve_path(key, default, env_var=""):
    """从 v7_paths.yaml 解析路径，优先级：环境变量 > config > 默认值"""
    import yaml
    # 1) 环境变量
    if env_var:
        val = os.environ.get(env_var, "")
        if val:
            return val
    # 2) config/v7_paths.yaml
    cfg_path = Path(__file__).resolve().parents[2] / "config" / "v7_paths.yaml"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        val = cfg.get(key, "")
        if val:
            return val.replace("%REPO_ROOT%", str(Path(__file__).resolve().parents[2]))
    # 3) 默认值
    return default

def start_server():
    """启动服务器"""
    _default_exe = str(Path(__file__).resolve().parents[2] / "offline_platform" / "guandan_offline_v1006" / "windows" / "guandan_offline_v1006.exe")
    server_path = _resolve_path("server_exe", _default_exe, "SERVER_EXE")
    
    if not os.path.exists(server_path):
        print(f"✗ 服务器文件不存在: {server_path}")
        return None

    print("🚀 启动服务器...")
    print(f"服务器路径: {server_path} {server_argv}")

    process = subprocess.Popen(
        [server_path, server_argv],
        cwd=os.path.dirname(server_path),
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )

    print(f"✓ 服务器已启动，PID: {process.pid}")

    if check_port_listening(23456, timeout=30):
        print("✓ 服务器就绪，可以连接客户端")
        return process

    print("✗ 服务器启动失败或未监听端口")
    process.terminate()
    return None


def start_client(script_path, delay=0, window_title="客户端"):
    """启动客户端"""
    if delay > 0:
        print(f"⏳ 等待 {delay} 秒后启动 {window_title}...")
        time.sleep(delay)

    print(f"🚀 启动 {window_title}: {script_path}")

    if not os.path.exists(script_path):
        print(f"✗ 客户端文件不存在: {script_path}")
        return None

    rel = Path(script_path).relative_to(REPO_ROOT)
    if sys.platform == "win32":
        cmd = (
            f'start "{window_title}" cmd /k '
            f'"cd /d {REPO_ROOT} && python {rel.as_posix()}"'
        )
        process = subprocess.Popen(
            cmd,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        process = subprocess.Popen(["python", str(script_path)], cwd=str(REPO_ROOT))

    print(f"✓ {window_title} 已启动，PID: {process.pid}")
    return process


def main():
    """主函数"""
    print("=" * 60)
    print("V7终极胜率导向系统完整启动")
    print("=" * 60)
    
    # 检查必要文件
    _default_lalala = str(Path(__file__).resolve().parents[2] / "reference" / "lalala")
    _lalala_dir = _resolve_path("lalala_dir", _default_lalala, "LALALA_DIR")
    _default_exe = str(Path(__file__).resolve().parents[2] / "offline_platform" / "guandan_offline_v1006" / "windows" / "guandan_offline_v1006.exe")
    required_files = [
        _resolve_path("server_exe", _default_exe, "SERVER_EXE"),
        "src/communication/yf1_v7.py",
        os.path.join(_lalala_dir, "client3.py"),
        "src/communication/yf2_v7.py",
        os.path.join(_lalala_dir, "client4.py")
    ]
    
    print("检查必要文件...")
    all_exists = True
    for file_path in required_files:
        path = Path(file_path)
        exists = path.is_file() or path.is_dir()
        mark = "✓" if exists else "✗"
        print(f"{mark} {file_path}")
        if not exists and path.suffix == ".py":
            all_exists = False

    model_path = Path(get_model_file(REPO_ROOT))
    if not model_path.is_file():
        print("⚠ 模型文件缺失，V7 将使用规则引擎回退")

    if not all_exists:
        print("\n✗ 必要客户端/服务器文件缺失，无法启动")
        return

    print("\n" + "=" * 60)
    print("启动序列")
    print("=" * 60)

    server_process = start_server()
    if not server_process:
        print("✗ 服务器启动失败，终止启动")
        return

    print("\n等待3秒，确保服务器完全就绪...")
    time.sleep(3)

    clients = []
    titles = [
        "yf1_v7 (Pos 0)",
        "lalala_client3 (Pos 1)",
        "yf2_v7 (Pos 2)",
        "lalala_client4 (Pos 3)",
    ]
    delays = [0, 3, 3, 3]

    try:
        # 2. 按顺序启动客户端
        clients = []
        
        # yf1_v7 (3秒内部延迟)
        client1 = start_client("src/communication/yf1_v7.py", delay=0, window_title="yf1_v7")
        if client1:
            clients.append(client1)
        
        # client3 (10秒内部延迟) - 等待yf1_v7连接后启动
        _lalala_dir = _resolve_path("lalala_dir", _default_lalala, "LALALA_DIR")
        client2 = start_client(os.path.join(_lalala_dir, "client3.py"), delay=4, window_title="client3")
        if client2:
            clients.append(client2)
        
        # yf2_v7 (9秒内部延迟) - 等待client3连接后启动
        client3 = start_client("src/communication/yf2_v7.py", delay=11, window_title="yf2_v7")
        if client3:
            clients.append(client3)
        
        # client4 (20秒内部延迟) - 等待yf2_v7连接后启动
        client4 = start_client(os.path.join(_lalala_dir, "client4.py"), delay=10, window_title="client4")
        if client4:
            clients.append(client4)
        
        print("\n" + "=" * 60)
        print("启动完成")
        print("=" * 60)
        print(f"✓ 服务器进程: PID {server_process.pid}")
        print(f"✓ 客户端进程: {len(clients)} 个")
        print("\n预期队伍分配:")
        print("队伍A (0+2): yf1_v7 + yf2_v7")
        print("队伍B (1+3): lalala client3 + client4")
        print("\n请查看服务器窗口确认客户端连接状态")
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
