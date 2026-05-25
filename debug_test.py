#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的调试测试脚本
"""
import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(r"C:\yifeGDBOT")
SERVER_PATH = PROJECT_ROOT / "offline_platform/guandan_offline_v1006/windows/guandan_offline_v1006.exe"

def test_server_directly():
    """直接测试服务器启动"""
    print("Testing server startup...")
    cmd = [str(SERVER_PATH), "1"]  # 只运行1局
    try:
        result = subprocess.run(cmd, cwd=str(SERVER_PATH.parent), 
                              capture_output=True, text=True, timeout=30)
        print(f"Server exit code: {result.returncode}")
        print(f"Server stdout: {result.stdout}")
        if result.stderr:
            print(f"Server stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running server: {e}")
        return False

def main():
    print("=== Debug Test ===")
    success = test_server_directly()
    if success:
        print("✓ Server startup test passed")
    else:
        print("✗ Server startup test failed")
    
    # Check if server executable exists
    if SERVER_PATH.exists():
        print(f"✓ Server executable found: {SERVER_PATH}")
    else:
        print(f"✗ Server executable not found: {SERVER_PATH}")

if __name__ == "__main__":
    main()