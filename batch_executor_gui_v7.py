# -*- coding: utf-8 -*-
"""
批量游戏执行系统 - V7 版本图形界面

对标 batch_executor_gui_m1.py：根目录专用入口，预填 V7 vs lalala 四客户端。
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

import tkinter as tk
from tkinter import ttk

from batch_executor_gui import BatchExecutorGUI
from src.utils.v7_paths import (
    format_client_scripts_for_gui,
    get_model_file,
    get_server_exe,
    get_v7_client_scripts,
)


class BatchExecutorGUIV7(BatchExecutorGUI):
    """V7 终极胜率导向批量对战 GUI"""

    def __init__(self, root):
        super().__init__(root)
        self.root.title("掼蛋AI批量对战系统 - V7终极胜率导向版")

    def load_default_config(self):
        """加载 V7 默认配置（对标 M1 的 yf1/yf2 + lalala3/4）"""
        self.target_games_var.set("12")

        client_scripts = get_v7_client_scripts(REPO_ROOT)
        self.clients_var.set(format_client_scripts_for_gui(client_scripts, REPO_ROOT))
        self.server_path_var.set(get_server_exe(REPO_ROOT))

        self.log_text.insert(tk.END, "=" * 60 + "\n")
        self.log_text.insert(tk.END, "V7 终极胜率导向批量对战系统\n")
        self.log_text.insert(tk.END, "=" * 60 + "\n")
        self.log_text.insert(tk.END, "配置信息:\n")
        self.log_text.insert(tk.END, "  队伍A (V7): yf1_v7 + yf2_v7\n")
        self.log_text.insert(tk.END, "  队伍B (lalala): run_lalala_client3/4\n")
        self.log_text.insert(tk.END, f"  服务器: {get_server_exe(REPO_ROOT)}\n")
        self.log_text.insert(tk.END, f"  lalala: 见 config/v7_paths.yaml\n\n")

        model_path = Path(get_model_file(REPO_ROOT))
        if model_path.is_file():
            self.log_text.insert(tk.END, f"✓ 模型: {model_path}\n")
        else:
            self.log_text.insert(tk.END, "⚠ 模型未找到，将使用规则引擎回退\n")

        self.log_text.insert(tk.END, "\n点击「开始执行」；服务器由批跑器自动拉起\n")
        self.log_text.insert(tk.END, "=" * 60 + "\n\n")
        self.log_text.see(tk.END)


def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")
    BatchExecutorGUIV7(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装依赖: pip install -r requirements.txt")
        input("按回车键退出...")
    except Exception as e:
        print(f"启动 V7 GUI 时出错: {e}")
        import traceback

        traceback.print_exc()
        input("按回车键退出...")
