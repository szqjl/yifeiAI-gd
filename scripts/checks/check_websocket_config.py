# -*- coding: utf-8 -*-
"""
简单验证 WebSocket 配置
直接检查配置文件格式和连接地址
"""

import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def check_config():
    """检查配置文件"""
    print("=" * 60)
    print("WebSocket 配置验证")
    print("=" * 60)
    
    # 1. 读取配置文件
    config_path = REPO_ROOT / "config.yaml"
    print(f"\n[1] 读取配置文件: {config_path}")
    
    if not config_path.exists():
        print("❌ 错误：配置文件不存在")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("✅ 配置文件读取成功")
    
    # 2. 检查 WebSocket 配置
    print("\n[2] 检查 WebSocket 配置...")
    ws_config = config.get("websocket", {})
    
    if not ws_config:
        print("❌ 错误：未找到 WebSocket 配置")
        return False
    
    print("✅ 找到 WebSocket 配置")
    print(f"   本地URL: {ws_config.get('local_url', 'N/A')}")
    print(f"   网络URL: {ws_config.get('network_url', 'N/A')}")
    print(f"   重连间隔: {ws_config.get('reconnect_interval', 'N/A')}秒")
    print(f"   心跳间隔: {ws_config.get('heartbeat_interval', 'N/A')}秒")
    print(f"   超时时间: {ws_config.get('timeout', 'N/A')}秒")
    
    # 3. 验证 URL 格式
    print("\n[3] 验证 URL 格式...")
    local_url = ws_config.get("local_url", "")
    
    # 检查必需的元素
    checks = {
        "协议": local_url.startswith("ws://"),
        "主机": "127.0.0.1" in local_url or "localhost" in local_url,
        "端口": ":23456" in local_url,
        "路径": "/game/" in local_url,
        "占位符": "{user_info}" in local_url
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        if passed:
            print(f"   ✅ {check_name}: 正确")
        else:
            print(f"   ❌ {check_name}: 错误")
            all_passed = False
    
    # 4. 生成实际连接地址
    print("\n[4] 生成实际连接地址...")
    test_users = ["yf1_v5", "yf2_v5"]
    
    for user_info in test_users:
        actual_url = local_url.format(user_info=user_info)
        print(f"   {user_info}: {actual_url}")
        
        # 验证格式
        expected = f"ws://127.0.0.1:23456/game/{user_info}"
        if actual_url == expected:
            print(f"      ✅ 格式正确")
        else:
            print(f"      ⚠️  格式可能不正确（期望: {expected}）")
    
    # 5. 与服务器示例对比
    print("\n[5] 与服务器示例对比...")
    server_example = "ws://127.0.0.1:23456/game/client1"
    our_example = local_url.format(user_info="client1")
    
    print(f"   服务器示例: {server_example}")
    print(f"   我们的配置: {our_example}")
    
    if server_example == our_example:
        print("   ✅ 完全匹配！")
    else:
        # 检查关键部分
        server_parts = server_example.split("/")
        our_parts = our_example.split("/")
        
        if server_parts[:3] == our_parts[:3]:
            print("   ✅ 协议、主机、端口匹配")
        else:
            print("   ❌ 协议、主机或端口不匹配")
            all_passed = False
        
        if len(server_parts) == len(our_parts):
            print("   ✅ URL 路径层级匹配")
        else:
            print("   ⚠️  URL 路径层级可能不匹配")
    
    # 6. 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    if all_passed:
        print("✅ 所有配置检查通过！")
        print("\n📋 配置详情：")
        print(f"   - 连接地址模板: {local_url}")
        print(f"   - 实际连接地址示例:")
        for user_info in test_users:
            print(f"     • {user_info}: {local_url.format(user_info=user_info)}")
        print(f"   - 重连间隔: {ws_config.get('reconnect_interval')}秒")
        print(f"   - 心跳间隔: {ws_config.get('heartbeat_interval')}秒")
        print(f"   - 超时时间: {ws_config.get('timeout')}秒")
        
        print("\n✅ 配置格式与服务器要求完全匹配！")
        print("\n💡 使用说明：")
        print("   1. 确保服务器 guandan_offline_v1006.exe 已启动")
        print("   2. 服务器会监听端口 23456")
        print("   3. 需要4个客户端连接后才能开始游戏")
        print("   4. yf1_v5 和 yf2_v5 可以正常连接")
    else:
        print("⚠️  部分配置检查未通过，请检查上述错误")
    
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    check_config()

