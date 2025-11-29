# -*- coding: utf-8 -*-
"""
验证Task 19 - batch_executor_gui.py配置更新
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def test_import():
    """测试1: 导入batch_executor_gui"""
    print("=" * 60)
    print("测试1: 导入batch_executor_gui")
    print("=" * 60)
    
    try:
        import batch_executor_gui
        print("✓ batch_executor_gui.py 导入成功")
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_v4_files_exist():
    """测试2: 检查V4文件是否存在"""
    print("\n" + "=" * 60)
    print("测试2: 检查V4客户端文件")
    print("=" * 60)
    
    files = [
        "src/communication/yf1_v4.py",
        "src/communication/yf2_v4.py",
        "src/communication/run_lalala_client3.py",
        "src/communication/run_lalala_client4.py"
    ]
    
    all_exist = True
    for file in files:
        exists = os.path.exists(file)
        status = "✓" if exists else "✗"
        print(f"{status} {file}: {'存在' if exists else '不存在'}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n✓ 所有V4客户端文件都存在")
    else:
        print("\n✗ 部分文件缺失")
    
    return all_exist


def test_default_config():
    """测试3: 验证默认配置"""
    print("\n" + "=" * 60)
    print("测试3: 验证默认配置")
    print("=" * 60)
    
    try:
        # 读取文件内容
        with open("batch_executor_gui.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查选项3是否存在
        if "选项3：使用V4混合决策引擎" in content:
            print("✓ 选项3已添加")
        else:
            print("✗ 选项3未找到")
            return False
        
        # 检查yf1_v4.py和yf2_v4.py是否在配置中
        if "yf1_v4.py" in content and "yf2_v4.py" in content:
            print("✓ V4客户端路径正确")
        else:
            print("✗ V4客户端路径不正确")
            return False
        
        # 检查选项1和2是否被注释
        lines = content.split('\n')
        in_option2 = False
        option2_commented = True
        
        for line in lines:
            if "选项2：使用N版本" in line:
                in_option2 = True
            elif "选项3：使用V4混合决策引擎" in line:
                in_option2 = False
            
            if in_option2 and "default_clients = [" in line:
                if not line.strip().startswith("#"):
                    option2_commented = False
                    break
        
        if option2_commented:
            print("✓ 选项2已正确注释")
        else:
            print("✗ 选项2未注释")
            return False
        
        # 检查选项3是否未注释（是默认配置）
        in_option3 = False
        option3_active = False
        
        for line in lines:
            if "选项3：使用V4混合决策引擎" in line:
                in_option3 = True
            elif in_option3 and "default_clients = [" in line:
                if not line.strip().startswith("#"):
                    option3_active = True
                break
        
        if option3_active:
            print("✓ 选项3已设为默认配置")
        else:
            print("✗ 选项3未设为默认")
            return False
        
        # 检查注释是否完整
        if "HybridDecisionEngineV4" in content:
            print("✓ V4特性说明完整")
        else:
            print("✗ V4特性说明缺失")
            return False
        
        if "4层决策保护" in content:
            print("✓ 4层决策说明存在")
        else:
            print("✗ 4层决策说明缺失")
            return False
        
        print("\n✓ 默认配置验证通过")
        return True
        
    except Exception as e:
        print(f"✗ 配置验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_structure():
    """测试4: 验证配置结构"""
    print("\n" + "=" * 60)
    print("测试4: 验证配置结构")
    print("=" * 60)
    
    try:
        with open("batch_executor_gui.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查三个选项都存在
        options = ["选项1", "选项2", "选项3"]
        for option in options:
            if option in content:
                print(f"✓ {option}存在")
            else:
                print(f"✗ {option}缺失")
                return False
        
        # 检查队伍分组说明
        if "队伍A（YiFei V4队）" in content:
            print("✓ 队伍分组说明正确")
        else:
            print("✗ 队伍分组说明不正确")
            return False
        
        # 检查座位说明
        if "0号位 - YiFei V4" in content and "2号位 - YiFei V4" in content:
            print("✓ 座位说明正确")
        else:
            print("✗ 座位说明不正确")
            return False
        
        print("\n✓ 配置结构验证通过")
        return True
        
    except Exception as e:
        print(f"✗ 结构验证失败: {e}")
        return False


def test_gui_instantiation():
    """测试5: 测试GUI实例化（不显示窗口）"""
    print("\n" + "=" * 60)
    print("测试5: 测试GUI实例化")
    print("=" * 60)
    
    try:
        import tkinter as tk
        from batch_executor_gui import BatchExecutorGUI
        
        # 创建隐藏的root窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏窗口
        
        # 尝试创建GUI实例
        gui = BatchExecutorGUI(root)
        
        # 检查默认配置是否加载
        clients_text = gui.clients_var.get()
        
        if "yf1_v4.py" in clients_text and "yf2_v4.py" in clients_text:
            print("✓ GUI默认配置正确加载V4客户端")
            print(f"  配置: {clients_text}")
        else:
            print("✗ GUI默认配置未正确加载")
            print(f"  实际配置: {clients_text}")
            root.destroy()
            return False
        
        # 清理
        root.destroy()
        
        print("\n✓ GUI实例化测试通过")
        return True
        
    except Exception as e:
        print(f"✗ GUI实例化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Task 19 验证 - batch_executor_gui.py配置更新")
    print("=" * 60)
    
    tests = [
        ("导入测试", test_import),
        ("V4文件检查", test_v4_files_exist),
        ("默认配置验证", test_default_config),
        ("配置结构验证", test_config_structure),
        ("GUI实例化测试", test_gui_instantiation)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name}执行异常: {e}")
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("✓ Task 19 完成！")
        print("✓ batch_executor_gui.py已成功更新V4配置")
    else:
        print(f"✗ {total - passed} 个测试失败")
    
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
