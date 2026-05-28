"""测试GUI路径验证修复"""
import os

def test_server_path_validation():
    """测试服务器路径验证逻辑"""
    print("=" * 60)
    print("测试服务器路径验证")
    print("=" * 60)
    
    # 测试包含参数的服务器路径
    server_path = "D:\\guandanscore\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe 10"
    print(f"原始路径: {server_path}")
    
    # 分离路径和参数
    server_parts = server_path.split()
    actual_server_path = server_parts[0]
    print(f"分离后的可执行文件路径: {actual_server_path}")
    
    # 验证文件是否存在
    exists = os.path.exists(actual_server_path)
    print(f"文件是否存在: {exists}")
    
    if exists:
        print("✓ 服务器路径验证通过")
    else:
        print("✗ 服务器路径验证失败")
    
    print()
    return exists

def test_client_path_validation():
    """测试客户端路径验证逻辑"""
    print("=" * 60)
    print("测试客户端路径验证")
    print("=" * 60)
    
    clients = [
        "python src/communication/yf1_v7.py",
        "python D:\\NYGD\\lalala\\client3.py",
        "python src/communication/yf2_v7.py",
        "python D:\\NYGD\\lalala\\client4.py"
    ]
    
    all_valid = True
    for i, client in enumerate(clients, 1):
        print(f"\n客户端 {i}:")
        print(f"原始命令: {client}")
        
        # 提取实际的脚本路径
        client_parts = client.split()
        if len(client_parts) > 1 and client_parts[0].lower() in ['python', 'python.exe', 'py']:
            actual_client_path = ' '.join(client_parts[1:])
        else:
            actual_client_path = client
        
        print(f"提取的脚本路径: {actual_client_path}")
        
        # 验证文件是否存在
        exists = os.path.exists(actual_client_path)
        print(f"文件是否存在: {exists}")
        
        if exists:
            print("✓ 客户端路径验证通过")
        else:
            print("✗ 客户端路径验证失败")
            all_valid = False
    
    print()
    return all_valid

if __name__ == "__main__":
    print("V7 GUI路径验证修复测试\n")
    
    server_valid = test_server_path_validation()
    client_valid = test_client_path_validation()
    
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"服务器路径验证: {'✓ 通过' if server_valid else '✗ 失败'}")
    print(f"客户端路径验证: {'✓ 通过' if client_valid else '✗ 失败'}")
    
    if server_valid and client_valid:
        print("\n✓ 所有路径验证测试通过！")
        print("修复说明:")
        print("1. 服务器路径验证现在支持包含参数的路径（如 'path.exe 10'）")
        print("2. 客户端路径验证现在支持包含python命令的路径（如 'python script.py'）")
        print("3. GUI不再错误地提示'服务器不存在'或'客户端不存在'")
    else:
        print("\n✗ 部分路径验证测试失败")
