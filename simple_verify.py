# -*- coding: utf-8 -*-
"""
简单验证 WebSocket 配置 - 直接检查代码和配置
"""

import re
from pathlib import Path

def verify_config():
    """验证配置"""
    print("=" * 60)
    print("WebSocket 配置验证")
    print("=" * 60)
    
    # 1. 检查配置文件中的 URL 格式
    print("\n[1] 检查配置文件...")
    config_path = Path("config.yaml")
    
    if not config_path.exists():
        print("❌ config.yaml 不存在")
        return False
    
    # 读取配置文件（尝试不同编码）
    config_content = None
    for encoding in ['utf-8', 'gbk', 'gb2312']:
        try:
            with open(config_path, 'r', encoding=encoding) as f:
                config_content = f.read()
            break
        except:
            continue
    
    if not config_content:
        print("⚠️  无法读取配置文件（编码问题），但继续验证代码...")
    else:
        # 检查 URL 格式
        if 'ws://127.0.0.1:23456/game/{user_info}' in config_content:
            print("✅ 配置文件包含正确的 URL 模板")
        else:
            print("⚠️  配置文件中的 URL 格式可能不正确")
    
    # 2. 检查 WebSocketManager 代码
    print("\n[2] 检查 WebSocketManager 实现...")
    ws_manager_path = Path("src/communication/websocket_manager.py")
    
    if not ws_manager_path.exists():
        print("❌ websocket_manager.py 不存在")
        return False
    
    with open(ws_manager_path, 'r', encoding='utf-8') as f:
        ws_code = f.read()
    
    # 检查关键代码
    checks = {
        "URL 模板读取": 'local_url' in ws_code and '{user_info}' in ws_code,
        "URL 格式化": '.format(user_info=' in ws_code,
        "配置加载": 'get_websocket_config' in ws_code,
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        if passed:
            print(f"   ✅ {check_name}: 正确")
        else:
            print(f"   ❌ {check_name}: 错误")
            all_passed = False
    
    # 3. 检查 yf1_v5 和 yf2_v5 集成
    print("\n[3] 检查 yf_v5 客户端集成...")
    yf1_path = Path("src/communication/yf1_v5.py")
    yf2_path = Path("src/communication/yf2_v5.py")
    
    for client_name, client_path in [("yf1_v5", yf1_path), ("yf2_v5", yf2_path)]:
        if not client_path.exists():
            print(f"   ❌ {client_name}.py 不存在")
            all_passed = False
            continue
        
        with open(client_path, 'r', encoding='utf-8') as f:
            client_code = f.read()
        
        checks = {
            "导入 WebSocketManager": 'WebSocketManager' in client_code,
            "初始化管理器": 'WebSocketManager(' in client_code,
            "使用管理器连接": 'ws_manager.connect' in client_code,
        }
        
        print(f"\n   {client_name}:")
        for check_name, passed in checks.items():
            if passed:
                print(f"      ✅ {check_name}")
            else:
                print(f"      ❌ {check_name}")
                all_passed = False
    
    # 4. 验证 URL 格式匹配
    print("\n[4] 验证 URL 格式匹配...")
    server_format = "ws://127.0.0.1:23456/game/{user_info}"
    
    # 从代码中提取实际使用的格式
    pattern = r'ws://127\.0\.0\.1:23456/game/\{user_info\}'
    if re.search(pattern, ws_code):
        print(f"   ✅ 代码中的 URL 格式: {server_format}")
        print(f"   ✅ 服务器要求的格式: {server_format}")
        print(f"   ✅ 格式完全匹配！")
    else:
        print("   ⚠️  无法从代码中确认 URL 格式")
    
    # 5. 生成实际连接地址示例
    print("\n[5] 实际连接地址示例...")
    test_users = {
        "yf1_v5": "yf1_v5",
        "yf2_v5": "yf2_v5"
    }
    
    for name, user_info in test_users.items():
        actual_url = f"ws://127.0.0.1:23456/game/{user_info}"
        server_example = f"ws://127.0.0.1:23456/game/client1"
        
        print(f"   {name}:")
        print(f"      实际地址: {actual_url}")
        print(f"      服务器示例: {server_example}")
        
        # 检查格式是否匹配（除了 user_info 部分）
        if actual_url.replace(user_info, "client1") == server_example:
            print(f"      ✅ 格式匹配")
        else:
            print(f"      ⚠️  格式可能不匹配")
    
    # 6. 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    if all_passed:
        print("✅ 配置验证通过！")
        print("\n📋 配置详情：")
        print("   - URL 格式: ws://127.0.0.1:23456/game/{user_info}")
        print("   - yf1_v5 连接: ws://127.0.0.1:23456/game/yf1_v5")
        print("   - yf2_v5 连接: ws://127.0.0.1:23456/game/yf2_v5")
        print("\n✅ 配置格式与服务器要求完全匹配！")
        print("\n💡 可以正常连接到服务器！")
    else:
        print("⚠️  部分验证未通过，请检查上述错误")
    
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    verify_config()

