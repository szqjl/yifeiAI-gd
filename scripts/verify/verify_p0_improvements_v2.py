#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0改进验证脚本 v2 - 捕获平台和客户端输出进行诊断
"""

import subprocess
import time
import sys
import os
import threading
from pathlib import Path
from queue import Queue

REPO_ROOT = Path(__file__).resolve().parents[2]

def monitor_output(proc, name, output_queue):
    """监听进程输出"""
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                line = line.strip()
                output_queue.put((name, line))
                if name == "[PLATFORM]":
                    print(f"{name} {line}")
                elif any(keyword in line for keyword in ["act", "play", "decision", "P0改进", "【"]):
                    print(f"{name} {line}")
    except Exception as e:
        print(f"Error monitoring {name}: {e}")

def kill_existing_server():
    """杀死任何现有的服务器进程"""
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] and 'guandan_offline_v1006.exe' in proc.info['name']:
                    print(f"[清理] 结束残留服务器进程 PID={proc.pid}")
                    proc.kill()
                    proc.wait(timeout=3)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass
    except ImportError:
        os.system('taskkill /F /IM guandan_offline_v1006.exe 2>nul')
    time.sleep(2)

def wait_for_server_ready(server_process, timeout=30):
    """等待服务器就绪"""
    start_time = time.time()
    print("[等待] 监听服务器输出，等待'Ready for connect'消息...")

    while time.time() - start_time < timeout:
        try:
            line = server_process.stdout.readline()
            if line:
                line = line.strip()
                print(f"[服务器] {line}")
                if "ready for connect" in line.lower():
                    print("✓ 检测到服务器就绪消息!")
                    return True

            if server_process.poll() is not None:
                print(f"❌ 服务器进程已退出，返回码: {server_process.returncode}")
                return False
        except Exception as e:
            print(f"[读取错误] {e}")

        time.sleep(0.1)

    print(f"❌ 超时：{timeout}秒后仍未检测到服务器就绪")
    return False

def main():
    project_dir = REPO_ROOT
    os.chdir(project_dir)

    print("="*70)
    print("掼蛋P0改进验证脚本 v2 - 诊断版本（捕获平台输出）")
    print("="*70)

    # [1] 清理残留进程
    print("\n[步骤1] 清理残留的服务器进程...")
    kill_existing_server()
    print("✓ 清理完成")

    # [2] 启动平台
    print("\n[步骤2] 启动掼蛋平台...")
    exe_path = project_dir / "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"
    if not exe_path.exists():
        print(f"❌ 平台未找到: {exe_path}")
        return 1

    server_dir = exe_path.parent
    print(f"    工作目录: {server_dir}")
    print(f"    启动命令: {exe_path.name} 10")

    try:
        server_process = subprocess.Popen(
            [str(exe_path), "10"],
            cwd=str(server_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        print(f"✓ 服务器进程已启动，PID: {server_process.pid}")
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")
        return 1

    # [3] 等待服务器就绪
    print("\n[步骤3] 等待服务器就绪（最多30秒）...")
    if not wait_for_server_ready(server_process, timeout=30):
        print("❌ 服务器未能就绪，停止")
        server_process.terminate()
        return 1

    print("✓ 服务器已就绪")

    # [4] 额外等待
    print("\n[步骤4] 等待2秒确保端口完全监听...")
    time.sleep(2)
    print("✓ 完成")

    # [5] 启动客户端
    print("\n[步骤5] 启动客户端（位置0,1,2,3 需全部连接）...")
    clients = []
    output_queue = Queue()

    try:
        # yf1_m1
        yf1_proc = subprocess.Popen(
            [sys.executable, "src/communication/yf1_m1.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        clients.append(yf1_proc)
        yf1_thread = threading.Thread(target=monitor_output, args=(yf1_proc, "[YF1]", output_queue), daemon=True)
        yf1_thread.start()
        print(f"✓ yf1_m1 (位置0) 已启动，PID: {yf1_proc.pid}")
        time.sleep(1)

        # client1
        client1_script = project_dir / "offline_platform/guandan_offline_v1006/clients/client1.py"
        if client1_script.exists():
            client1_proc = subprocess.Popen(
                [sys.executable, str(client1_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(client1_script.parent)
            )
            clients.append(client1_proc)
            c1_thread = threading.Thread(target=monitor_output, args=(client1_proc, "[C1]", output_queue), daemon=True)
            c1_thread.start()
            print(f"✓ client1 (位置1) 已启动，PID: {client1_proc.pid}")
            time.sleep(1)

        # yf2_m1
        yf2_proc = subprocess.Popen(
            [sys.executable, "src/communication/yf2_m1.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        clients.append(yf2_proc)
        yf2_thread = threading.Thread(target=monitor_output, args=(yf2_proc, "[YF2]", output_queue), daemon=True)
        yf2_thread.start()
        print(f"✓ yf2_m1 (位置2) 已启动，PID: {yf2_proc.pid}")
        time.sleep(1)

        # client3
        client3_script = project_dir / "offline_platform/guandan_offline_v1006/clients/client3.py"
        if client3_script.exists():
            client3_proc = subprocess.Popen(
                [sys.executable, str(client3_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(client3_script.parent)
            )
            clients.append(client3_proc)
            c3_thread = threading.Thread(target=monitor_output, args=(client3_proc, "[C3]", output_queue), daemon=True)
            c3_thread.start()
            print(f"✓ client3 (位置3) 已启动，PID: {client3_proc.pid}")
            time.sleep(1)

    except Exception as e:
        print(f"❌ 启动客户端失败: {e}")
        for proc in clients:
            proc.terminate()
        server_process.terminate()
        return 1

    # [6] 等待游戏运行（300秒，每30秒输出进度）
    print("\n[步骤6] 游戏运行中（300秒）...")
    try:
        for i in range(30):
            time.sleep(10)
            if i % 3 == 0:
                elapsed = (i+1)*10
                print(f"    已运行 {elapsed}秒... (平台进程活跃: {server_process.poll() is None})")
    except KeyboardInterrupt:
        print("\n⚠ 被中断")

    # [7] 终止进程
    print("\n[步骤7] 终止进程...")
    for proc in clients:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    server_process.terminate()
    time.sleep(1)

    # [8] 检查日志
    print("\n[步骤8] 检查日志...")
    logs_dir = project_dir / "logs"
    yf1_logs = sorted(logs_dir.glob("yf1_m1_*.log"))[-1] if logs_dir.exists() else None

    if not yf1_logs:
        print("❌ 未找到日志文件")
        return 1

    print(f"✓ 读取日志: {yf1_logs.name}\n")
    print("="*70)

    with open(yf1_logs, encoding='utf-8', errors='replace') as f:
        content = f.read()

        # 查找关键日志
        keywords = ['【P0改进', '【决策入口】', '【决策出口】', 'act', 'play', 'beginning', 'decision']
        found_keywords = False

        for line in content.split('\n'):
            if any(keyword in line for keyword in keywords):
                print(line)
                found_keywords = True

        print("="*70)

        if found_keywords:
            print("\n✅ SUCCESS: 检测到关键日志！")
            if '【P0改进' in content:
                print("   P0改进代码被执行!")
            if '【决策' in content:
                print("   决策逻辑被触发!")
            return 0
        else:
            print("\n⚠️ 未检测到关键日志")
            print("\n【完整日志】:")
            print(content)
            return 1

if __name__ == "__main__":
    sys.exit(main())
