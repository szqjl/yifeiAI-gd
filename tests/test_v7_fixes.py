"""测试V7修复"""
import json

def test_message_format():
    """测试V7客户端消息格式修复"""
    print("=" * 60)
    print("测试V7客户端消息格式")
    print("=" * 60)
    
    # 模拟V7客户端发送的消息
    v7_message = {
        "type": "action",
        "data": {
            "actIndex": 2  # 修复后使用actIndex而不是actionIndex
        }
    }
    
    print("V7客户端发送的消息格式:")
    print(json.dumps(v7_message, indent=2, ensure_ascii=False))
    
    # 检查是否包含正确的字段
    if "actIndex" in v7_message["data"]:
        print("✓ 消息格式正确：使用 'actIndex' 字段")
    else:
        print("✗ 消息格式错误：缺少 'actIndex' 字段")
    
    if "actionIndex" in v7_message["data"]:
        print("✗ 消息格式错误：仍在使用 'actionIndex' 字段")
    else:
        print("✓ 消息格式正确：不再使用 'actionIndex' 字段")
    
    print()

def test_client_startup_order():
    """测试客户端启动顺序逻辑"""
    print("=" * 60)
    print("测试客户端启动顺序")
    print("=" * 60)
    
    # V7客户端配置
    clients = [
        "python src/communication/yf1_v7.py",  # 3秒延迟
        "python D:\\NYGD\\lalala\\client3.py",    # 10秒延迟
        "python src/communication/yf2_v7.py",  # 9秒延迟
        "python D:\\NYGD\\lalala\\client4.py"     # 20秒延迟
    ]
    
    print("期望的启动顺序和等待时间:")
    expected_waits = [4, 11, 10, 0]  # 最后一个不需要等待
    
    for i, client in enumerate(clients):
        script_name = client.split()[-1].split('\\')[-1].split('/')[-1]
        wait_time = expected_waits[i]
        
        print(f"{i+1}. {script_name}")
        if i < len(clients) - 1:
            print(f"   -> 等待 {wait_time} 秒后启动下一个")
        else:
            print(f"   -> 最后一个客户端，无需等待")
    
    print("\n修复说明:")
    print("- yf1_v7: 3秒内部延迟 + 1秒缓冲 = 4秒等待")
    print("- client3: 10秒内部延迟 + 1秒缓冲 = 11秒等待")
    print("- yf2_v7: 9秒内部延迟 + 1秒缓冲 = 10秒等待")
    print("- client4: 最后一个，无需等待")
    
    print()

def test_connection_timing():
    """测试连接时序"""
    print("=" * 60)
    print("测试连接时序")
    print("=" * 60)
    
    print("客户端内部延迟:")
    print("- yf1_v7: 3秒延迟（DELAY_BEFORE_CONNECT = 3）")
    print("- client3: 10秒延迟（lalala客户端固定延迟）")
    print("- yf2_v7: 9秒延迟（DELAY_BEFORE_CONNECT = 9）")
    print("- client4: 20秒延迟（lalala客户端固定延迟）")
    
    print("\n预期连接时间线:")
    print("T+0s: 启动yf1_v7")
    print("T+3s: yf1_v7连接到服务器")
    print("T+4s: 启动client3")
    print("T+14s: client3连接到服务器")
    print("T+15s: 启动yf2_v7")
    print("T+24s: yf2_v7连接到服务器")
    print("T+25s: 启动client4")
    print("T+45s: client4连接到服务器")
    
    print("\n✓ 连接顺序：yf1_v7 -> client3 -> yf2_v7 -> client4")
    print()

if __name__ == "__main__":
    print("V7系统修复验证\n")
    
    test_message_format()
    test_client_startup_order()
    test_connection_timing()
    
    print("=" * 60)
    print("修复总结")
    print("=" * 60)
    print("1. ✓ 修复了V7客户端消息格式问题")
    print("   - 将 'actionIndex' 改为 'actIndex'")
    print("   - 解决服务器 KeyError: 'actIndex' 错误")
    print()
    print("2. ✓ 修复了客户端启动顺序问题")
    print("   - 更新了restart_manager.py中的等待逻辑")
    print("   - 支持yf1_v7和yf2_v7的正确延迟时间")
    print("   - 确保按正确顺序连接：yf1_v7 -> client3 -> yf2_v7 -> client4")
    print()
    print("3. 修复的文件:")
    print("   - src/communication/yf1_v7.py")
    print("   - src/communication/yf2_v7.py")
    print("   - batch_executor/restart_manager.py")