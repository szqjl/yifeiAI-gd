"""
测试GUI启动并捕获详细错误信息
"""

import sys
import traceback

print("=" * 60)
print("GUI启动测试")
print("=" * 60)

try:
    print("\n正在导入模块...")
    import tkinter as tk
    from batch_executor_gui import BatchExecutorGUI
    
    print("✅ 模块导入成功")
    
    print("\n正在创建GUI窗口...")
    root = tk.Tk()
    app = BatchExecutorGUI(root)
    
    print("✅ GUI创建成功")
    print("\n启动GUI主循环...")
    print("提示: 关闭GUI窗口以退出")
    print("=" * 60)
    
    root.mainloop()
    
    print("\nGUI已关闭")
    print("程序正常退出")
    
except Exception as e:
    print("\n" + "=" * 60)
    print("❌ 错误发生!")
    print("=" * 60)
    print(f"\n错误类型: {type(e).__name__}")
    print(f"错误信息: {e}")
    print("\n详细堆栈:")
    print("-" * 60)
    traceback.print_exc()
    print("-" * 60)
    print("\n这个错误导致GUI闪退")
    print("请将上面的错误信息发送给开发者")
    
    input("\n按Enter键退出...")
    sys.exit(1)

print("\n程序结束")
input("按Enter键退出...")
