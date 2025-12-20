# -*- coding: utf-8 -*-
"""
启动GUI的Python脚本
如果无法打开.bat文件，可以使用这个脚本启动GUI
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from batch_executor_gui import BatchExecutorGUI
    import tkinter as tk
    
    print("正在启动GUI...")
    root = tk.Tk()
    app = BatchExecutorGUI(root)
    print("GUI窗口已打开")
    root.mainloop()
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    input("按回车键退出...")
except Exception as e:
    print(f"启动GUI时出错: {e}")
    import traceback
    traceback.print_exc()
    input("按回车键退出...")

