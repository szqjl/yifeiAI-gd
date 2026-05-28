#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速单局测试 - 验证P0改进③是否被执行
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def main():
    project_dir = Path(__file__).resolve().parents[1]
    os.chdir(project_dir)
    
    # Kill any existing processes
    os.system("taskkill /F /IM guandan_offline_v1006.exe 2>/dev/null")
    os.system("taskkill /F /IM python.exe 2>/dev/null")
    time.sleep(2)
    
    # Start platform
    print("[1/3] 启动掼蛋平台...")
    exe_path = project_dir / "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"
    if not exe_path.exists():
        print(f"ERROR: Platform not found at {exe_path}")
        return 1
    
    platform_proc = subprocess.Popen(str(exe_path), 
                                     stdout=subprocess.DEVNULL, 
                                     stderr=subprocess.DEVNULL)
    time.sleep(3)
    
    print("[2/3] 启动M1客户端...")
    try:
        # Start yf1
        yf1_proc = subprocess.Popen(
            [sys.executable, "src/communication/yf1_m1.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        time.sleep(1)
        
        # Start yf2
        yf2_proc = subprocess.Popen(
            [sys.executable, "src/communication/yf2_m1.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        time.sleep(1)
        
        print("[3/3] 等待游戏完成（35秒）...")
        time.sleep(35)
        
        # Terminate clients
        yf1_proc.terminate()
        yf2_proc.terminate()
        yf1_proc.wait(timeout=5)
        yf2_proc.wait(timeout=5)
        
        # Read logs
        logs_dir = project_dir / "logs"
        yf1_logs = sorted(logs_dir.glob("yf1_m1_*.log"))[-1]
        
        print(f"\n【日志输出】 {yf1_logs.name}:\n" + "="*60)
        with open(yf1_logs, encoding='utf-8', errors='replace') as f:
            content = f.read()
            # Filter for P0 and decision logs
            for line in content.split('\n'):
                if 'P0改进' in line or '【' in line or 'Error' in line or 'decision' in line:
                    print(line)
        
        print("\n" + "="*60)
        if 'P0改进' in content:
            print("✅ SUCCESS: P0改进代码被执行！")
            return 0
        else:
            print("❌ FAILED: 未找到P0改进的日志，代码可能未被执行")
            print("\n【完整日志】:")
            print(content)
            return 1
            
    finally:
        yf1_proc.terminate()
        yf2_proc.terminate()
        platform_proc.terminate()
        time.sleep(1)

if __name__ == "__main__":
    sys.exit(main())
