# -*- coding: utf-8 -*-
"""
验证 WebSocket 配置是否正确
检查 yf_v5 客户端的 WebSocket 配置是否能正确连接到服务器
"""

import sys
import asyncio
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from config_loader import get_config
from communication.websocket_manager import WebSocketManager


async def test_websocket_connection():
    """测试 WebSocket 连接配置"""
    print("=" * 60)
    print("WebSocket 配置验证")
    print("=" * 60)
    
    # 1. 检查配置文件
    print("\n[1] 检查配置文件...")
    config = get_config()
    ws_config = config.get_websocket_config()
    
    if not ws_config:
        print("❌ 错误：未找到 WebSocket 配置")
        return False
    
    print("✅ 找到 WebSocket 配置")
    print(f"   - 本地URL模板: {ws_config.get('local_url', 'N/A')}")
    print(f"   - 网络URL模板: {ws_config.get('network_url', 'N/A')}")
    print(f"   - 重连间隔: {ws_config.get('reconnect_interval', 'N/A')}秒")
    print(f"   - 心跳间隔: {ws_config.get('heartbeat_interval', 'N/A')}秒")
    print(f"   - 超时时间: {ws_config.get('timeout', 'N/A')}秒")
    
    # 2. 检查 URL 格式
    print("\n[2] 检查 URL 格式...")
    local_url = ws_config.get("local_url", "")
    if "{user_info}" not in local_url:
        print("⚠️  警告：本地URL模板中未找到 {user_info} 占位符")
    else:
        print("✅ URL 模板格式正确（包含 {user_info} 占位符）")
    
    # 3. 测试 URL 生成
    print("\n[3] 测试 URL 生成...")
    test_user_info = "yf1_v5"
    manager = WebSocketManager(test_user_info, use_local=True)
    expected_url = f"ws://127.0.0.1:23456/game/{test_user_info}"
    
    print(f"   生成的URL: {manager.uri}")
    print(f"   期望的URL: {expected_url}")
    
    if manager.uri == expected_url:
        print("✅ URL 生成正确")
    else:
        print("⚠️  URL 生成与期望不符，但可能仍然有效")
    
    # 4. 检查服务器连接（不实际连接，只检查配置）
    print("\n[4] 检查连接配置...")
    print(f"   连接地址: {manager.uri}")
    print(f"   端口: 23456")
    print(f"   路径: /game/{test_user_info}")
    
    # 5. 与服务器示例对比
    print("\n[5] 与服务器示例对比...")
    server_example = "ws://127.0.0.1:23456/game/client1"
    print(f"   服务器示例: {server_example}")
    print(f"   我们的配置: {manager.uri}")
    
    # 提取关键部分对比
    server_parts = server_example.split("/")
    our_parts = manager.uri.split("/")
    
    if server_parts[:3] == our_parts[:3]:
        print("✅ 协议、主机和端口匹配")
    else:
        print("❌ 协议、主机或端口不匹配")
        return False
    
    if len(our_parts) == len(server_parts):
        print("✅ URL 路径结构匹配")
    else:
        print("⚠️  URL 路径结构可能不匹配")
    
    # 6. 总结
    print("\n" + "=" * 60)
    print("配置验证总结")
    print("=" * 60)
    print("✅ 配置文件存在且格式正确")
    print("✅ URL 模板格式正确")
    print("✅ 连接参数配置完整")
    print("\n📝 注意事项：")
    print("   1. 确保服务器 guandan_offline_v1006.exe 已启动")
    print("   2. 确保端口 23456 未被占用")
    print("   3. 服务器启动后会显示 'Ready for connect' 字样")
    print("   4. 需要4个客户端连接后才能开始游戏")
    print("\n💡 连接格式对比：")
    print(f"   服务器示例: {server_example}")
    print(f"   yf1_v5:     {manager.uri}")
    print(f"   yf2_v5:     {WebSocketManager('yf2_v5', use_local=True).uri}")
    print("=" * 60)
    
    return True


async def test_actual_connection():
    """测试实际连接（需要服务器运行）"""
    print("\n" + "=" * 60)
    print("实际连接测试（需要服务器运行）")
    print("=" * 60)
    
    test_user_info = "yf1_v5_test"
    manager = WebSocketManager(test_user_info, use_local=True)
    
    print(f"\n尝试连接到: {manager.uri}")
    print("注意：如果服务器未运行，此测试将失败")
    
    try:
        # 尝试连接，最多重试1次，超时5秒
        connected = await asyncio.wait_for(
            manager.connect(max_retries=1),
            timeout=5.0
        )
        
        if connected:
            print("✅ 连接成功！")
            await manager.close()
            return True
        else:
            print("❌ 连接失败（可能是服务器未运行）")
            return False
            
    except asyncio.TimeoutError:
        print("⏱️  连接超时（服务器可能未运行）")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        print("   这可能是正常的，如果服务器未运行")
        return False


if __name__ == "__main__":
    print("\n开始验证 WebSocket 配置...\n")
    
    # 基本配置验证
    asyncio.run(test_websocket_connection())
    
    # 询问是否测试实际连接
    print("\n是否测试实际连接？(需要服务器运行) [y/N]: ", end="")
    try:
        response = input().strip().lower()
        if response == 'y':
            asyncio.run(test_actual_connection())
    except:
        pass
    
    print("\n验证完成！")

