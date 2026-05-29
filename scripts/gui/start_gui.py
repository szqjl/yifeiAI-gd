# -*- coding: utf-8 -*-
"""启动通用批跑 GUI（V4/V5 等，见 batch_executor_gui.py）。"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

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
