# -*- coding: utf-8 -*-
"""
检查GUI配置的路径是否正确
"""

import os
from pathlib import Path

def check_paths():
    """检查路径配置"""
    print("=" * 60)
    print("GUI 路径配置检查")
    print("=" * 60)
    
    # 当前工作目录
    cwd = os.getcwd()
    print(f"\n当前工作目录: {cwd}")
    
    # 检查客户端路径
    print("\n[1] 检查客户端脚本路径...")
    clients = [
        "src/communication/yf1_v5.py",
        "src/communication/run_lalala_client3.py",
        "src/communication/yf2_v5.py",
        "src/communication/run_lalala_client4.py"
    ]
    
    for i, client in enumerate(clients, 1):
        # 相对路径
        rel_exists = os.path.exists(client)
        # 绝对路径
        abs_path = os.path.abspath(client)
        abs_exists = os.path.exists(abs_path)
        
        print(f"\n客户端 {i}: {client}")
        print(f"  相对路径存在: {'✅' if rel_exists else '❌'}")
        print(f"  绝对路径: {abs_path}")
        print(f"  绝对路径存在: {'✅' if abs_exists else '❌'}")
        
        if not rel_exists and not abs_exists:
            print(f"  ⚠️  文件不存在！")
        elif not rel_exists:
            print(f"  💡 建议使用绝对路径: {abs_path}")
    
    # 检查服务器路径
    print("\n[2] 检查服务器路径...")
    server_paths = [
        "D:\\GDAI源程序\\离线平台\\windows\\guandan_offline_v1006.exe",
        "guandan_offline_v1006.exe",
        os.path.join(cwd, "guandan_offline_v1006.exe")
    ]
    
    print("\n可能的服务器路径:")
    for server_path in server_paths:
        exists = os.path.exists(server_path)
        print(f"  {server_path}")
        print(f"    存在: {'✅' if exists else '❌'}")
        if exists:
            print(f"    绝对路径: {os.path.abspath(server_path)}")
    
    # 检查常见问题
    print("\n[3] 常见问题检查...")
    
    # 检查路径分隔符
    print("\n路径格式建议:")
    print("  Windows路径可以使用:")
    print("    - 正斜杠: src/communication/yf1_v5.py")
    print("    - 反斜杠: src\\communication\\yf1_v5.py")
    print("    - 绝对路径: D:\\YiFeiAI-GD\\src\\communication\\yf1_v5.py")
    
    # 生成正确的配置
    print("\n[4] 推荐的配置格式...")
    print("\n客户端脚本（逗号分隔）:")
    valid_clients = []
    for client in clients:
        if os.path.exists(client):
            abs_path = os.path.abspath(client)
            valid_clients.append(abs_path)
            print(f"  {abs_path}")
    
    if valid_clients:
        print(f"\n完整配置字符串:")
        print(f"  {', '.join(valid_clients)}")
    
    # 检查服务器
    print("\n服务器路径:")
    for server_path in server_paths:
        if os.path.exists(server_path):
            abs_server = os.path.abspath(server_path)
            print(f"  {abs_server}")
            break
    else:
        print("  ⚠️  未找到服务器文件，请手动选择")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)
    
    print("\n💡 使用建议:")
    print("1. 如果相对路径不工作，尝试使用绝对路径")
    print("2. 确保所有路径中的文件都存在")
    print("3. 在GUI中使用'浏览...'按钮选择服务器文件")
    print("4. 客户端路径可以用逗号分隔，支持混合使用相对和绝对路径")


if __name__ == "__main__":
    check_paths()

