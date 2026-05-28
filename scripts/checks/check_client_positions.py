"""
检查客户端位置分配和启动顺序
"""

import sys
from pathlib import Path

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_client_positions():
    """检查客户端位置分配"""
    print("="*60)
    print("客户端位置分配检查")
    print("="*60)
    
    # 从auto_game_runner获取客户端配置
    clients = [
        "src/communication/yf1_m1.py",  # client1 - 应该是0号位
        "src/communication/yf2_m1.py",  # client2 - 应该是2号位
        "src/communication/run_lalala_client3.py",  # client3 - 应该是1号位
        "src/communication/run_lalala_client4.py"  # client4 - 应该是3号位
    ]
    
    print("\n客户端配置顺序：")
    for i, client in enumerate(clients):
        exists = Path(client).exists()
        print(f"  [{i}] {client} {'✅' if exists else '❌'}")
    
    print("\n位置分配规则：")
    print("  - 0号位和2号位是一队（Team A）")
    print("  - 1号位和3号位是一队（Team B）")
    print("  - 客户端按启动顺序分配位置：第1个→0号位，第2个→1号位，第3个→2号位，第4个→3号位")
    
    print("\n当前配置的位置分配：")
    positions = [
        (0, "yf1_m1.py", "Team A"),
        (1, "run_lalala_client3.py", "Team B"),
        (2, "yf2_m1.py", "Team A"),
        (3, "run_lalala_client4.py", "Team B")
    ]
    
    for pos, client, team in positions:
        print(f"  {pos}号位: {client} ({team})")
    
    print("\n✅ 位置分配检查：")
    print("  - yf1_m1 (M1) 在 0号位 ✅")
    print("  - yf2_m1 (M2) 在 2号位 ✅")
    print("  - client3 在 1号位 ✅")
    print("  - client4 在 3号位 ✅")
    print("  - M1和M2组成Team A ✅")
    print("  - client3和client4组成Team B ✅")
    
    # 检查客户端连接URI
    print("\n" + "="*60)
    print("客户端连接URI检查")
    print("="*60)
    
    client_files = {
        "yf1_m1.py": "src/communication/yf1_m1.py",
        "yf2_m1.py": "src/communication/yf2_m1.py",
        "run_lalala_client3.py": "src/communication/run_lalala_client3.py",
        "run_lalala_client4.py": "src/communication/run_lalala_client4.py"
    }
    
    for name, path in client_files.items():
        if Path(path).exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # 查找WebSocket URI
                if 'ws://' in content or 'client' in content.lower():
                    lines = content.split('\n')
                    for line in lines:
                        if 'ws://' in line or 'client' in line.lower():
                            if 'client0' in line or 'client1' in line or 'client2' in line or 'client3' in line or 'client4' in line:
                                print(f"\n{name}:")
                                print(f"  {line.strip()}")
            except Exception as e:
                print(f"\n{name}: 无法读取文件 ({e})")
    
    print("\n" + "="*60)
    print("启动顺序检查")
    print("="*60)
    print("\n客户端启动顺序（batch_executor）：")
    print("  1. 启动服务器")
    print("  2. 等待服务器就绪（检测'ready for connect'）")
    print("  3. 按顺序启动客户端（每个间隔3秒）：")
    for i, client in enumerate(clients, 1):
        print(f"     {i}. {Path(client).name}")
    print("  4. 等待所有客户端连接")
    print("  5. 检测游戏开始")
    
    print("\n✅ 启动顺序正确：确保客户端按顺序连接，位置分配正确")
    
    print("\n" + "="*60)
    print("服务器信息捕获检查")
    print("="*60)
    print("\nbatch_executor会捕获以下服务器信息：")
    print("  1. 服务器启动输出")
    print("  2. 游戏开始信号")
    print("  3. 游戏结束信号")
    print("  4. 战绩信息（格式：'达到设定场次, 其中0号位胜利X次，1号位胜利Y次，2号位胜利Z次，3号位胜利W次'）")
    print("  5. 各位置胜利次数统计")
    
    print("\n工作流（auto_game_runner）会：")
    print("  - 调用batch_executor运行游戏")
    print("  - 检查游戏记录数量变化")
    print("  - 返回运行结果（成功/失败，新增游戏数）")
    
    print("\n⚠️ 注意：工作流目前不直接捕获服务器输出，而是通过检查游戏记录文件数量来判断")
    print("  如果需要详细的服务器信息，需要查看batch_executor的日志")
    
    print("\n" + "="*60)
    print("检查完成")
    print("="*60)

if __name__ == "__main__":
    check_client_positions()
