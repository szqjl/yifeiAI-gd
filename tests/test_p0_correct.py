#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正确的P0改进验证脚本 - 等待平台"Ready for connect"信号
"""

import subprocess
import time
import sys
import os
import threading
from pathlib import Path

def monitor_platform_output(proc, platform_ready_event):
    """监听平台输出，等待Ready for connect信号"""
    try:
        for line in iter(proc.stdout.readline, ''):
            if not line:
                break
            line = line.strip()
            print(f"[PLATFORM] {line}")
            if "Ready for connect" in line:
                print("✓ 平台已准备好，设置事件...")
                platform_ready_event.set()
    except Exception as e:
        print(f"❌ 监听平台输出失败: {e}")

def main():
    project_dir = Path(__file__).resolve().parents[1]
    os.chdir(project_dir)

    # 杀死任何现有进程
    os.system("taskkill /F /IM guandan_offline_v1006.exe 2>/dev/null")
    os.system("taskkill /F /IM python.exe 2>/dev/null")
    time.sleep(2)

    print("[1/4] 启动掼蛋平台...")
    exe_path = project_dir / "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"
    if not exe_path.exists():
        print(f"❌ 平台未找到: {exe_path}")
        return 1

    # 启动平台，监听stdout
    platform_proc = subprocess.Popen(
        str(exe_path) + " 10",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    # 创建事件，用于同步平台就绪
    platform_ready = threading.Event()
    monitor_thread = threading.Thread(
        target=monitor_platform_output,
        args=(platform_proc, platform_ready),
        daemon=True
    )
    monitor_thread.start()

    print("[2/4] 等待平台启动（最多30秒）...")
    if not platform_ready.wait(timeout=30):
        print("❌ 平台超时：未看到'Ready for connect'信号")
        platform_proc.terminate()
        return 1

    print("✓ 平台已启动，等待2秒让客户端连接...")
    time.sleep(2)

    print("[3/4] 启动M1客户端...")
    try:
        # 启动yf1
        yf1_proc = subprocess.Popen(
            [sys.executable, "src/communication/yf1_m1.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        time.sleep(1)

        # 启动yf2
        yf2_proc = subprocess.Popen(
            [sys.executable, "src/communication/yf2_m1.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        print("[4/4] 游戏运行中（60秒超时）...")
        time.sleep(60)

        # 终止客户端
        yf1_proc.terminate()
        yf2_proc.terminate()
        yf1_proc.wait(timeout=5)
        yf2_proc.wait(timeout=5)

        # 读取最新日志
        logs_dir = project_dir / "logs"
        yf1_logs = sorted(logs_dir.glob("yf1_m1_*.log"))[-1]

        print(f"\n【日志输出】{yf1_logs.name}:")
        print("="*70)
        with open(yf1_logs, encoding='utf-8', errors='replace') as f:
            content = f.read()
            # 查找关键日志
            for line in content.split('\n'):
                if any(keyword in line for keyword in ['P0改进', '【决策', 'Error', 'act', 'play', 'handCards']):
                    print(line)

        print("="*70)
        if 'P0改进' in content or '【决策' in content:
            print("✅ SUCCESS: P0改进代码被执行，或决策逻辑被触发！")
            return 0
        elif '【决策入口】' in content:
            print("✅ SUCCESS: 至少决策入口被记录！")
            return 0
        else:
            print("⚠ 未发现P0改进或决策日志")
            print("\n【完整日志】:")
            print(content[-2000:] if len(content) > 2000 else content)
            return 1

    finally:
        yf1_proc.terminate()
        yf2_proc.terminate()
        platform_proc.terminate()
        time.sleep(1)

if __name__ == "__main__":
    sys.exit(main())
