"""测试V7 GUI路径验证"""
import os
from pathlib import Path

# 测试服务器路径
server_path = "D:\\guandanscore\\guandan_offline_v1006\\windows\\guandan_offline_v1006.exe 10"
print("=" * 60)
print("测试服务器路径")
print("=" * 60)
print(f"原始路径: {server_path}")

server_parts = server_path.split()
actual_server_path = server_parts[0]
print(f"分离后的可执行文件路径: {actual_server_path}")
print(f"文件是否存在: {os.path.exists(actual_server_path)}")

if os.path.exists(actual_server_path):
    print("✓ 服务器文件存在")
else:
    print("✗ 服务器文件不存在")
    # 尝试其他可能的路径
    alt_path = actual_server_path.replace("\\\\", "\\")
    print(f"尝试替代路径: {alt_path}")
    print(f"替代路径是否存在: {os.path.exists(alt_path)}")

print()

# 测试客户端路径
client_paths = [
    "python src/communication/yf1_v7.py",
    "python D:\\NYGD\\lalala\\client3.py",
    "python src/communication/yf2_v7.py",
    "python D:\\NYGD\\lalala\\client4.py"
]

print("=" * 60)
print("测试客户端路径")
print("=" * 60)

for i, client_path in enumerate(client_paths, 1):
    print(f"\n客户端 {i}:")
    print(f"原始命令: {client_path}")
    
    script_parts = client_path.split()
    if len(script_parts) > 1 and script_parts[0].lower() in ['python', 'python.exe', 'py']:
        actual_script_path = ' '.join(script_parts[1:])
        print(f"提取的脚本路径: {actual_script_path}")
        
        # 检查绝对路径
        if os.path.isabs(actual_script_path):
            print(f"是绝对路径")
            print(f"文件是否存在: {os.path.exists(actual_script_path)}")
            if os.path.exists(actual_script_path):
                print("✓ 客户端脚本存在")
            else:
                print("✗ 客户端脚本不存在")
        else:
            # 相对路径
            print(f"是相对路径")
            abs_path = os.path.abspath(actual_script_path)
            print(f"转换为绝对路径: {abs_path}")
            print(f"文件是否存在: {os.path.exists(abs_path)}")
            if os.path.exists(abs_path):
                print("✓ 客户端脚本存在")
            else:
                print("✗ 客户端脚本不存在")

print("\n" + "=" * 60)
print("当前工作目录:", os.getcwd())
print("=" * 60)
