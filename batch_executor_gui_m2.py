"""
批量游戏执行系统 - M2版本图形界面

M2版本：重构硬编码规则引擎，无分数累积+阈值保护
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from batch_executor.executor import BatchExecutor
from batch_executor.logging_config import setup_logging


class BatchExecutorGUIM2:
    """批量游戏执行系统图形界面 - M2版本"""

    def __init__(self, root):
        self.root = root
        self.root.title("掼蛋AI批量对战系统 - M2版本 v1.0")
        self.root.geometry("950x750")
        self.root.resizable(True, True)

        self.executor = None
        self.executor_thread = None
        self.is_running = False

        self.setup_styles()
        self.create_widgets()
        self.load_default_config()

    def setup_styles(self):
        """配置界面样式"""
        style = ttk.Style()
        style.configure('Start.TButton', foreground='green', font=('Arial', 10, 'bold'))
        style.configure('Stop.TButton', foreground='red', font=('Arial', 10, 'bold'))

    def create_widgets(self):
        """创建界面组件"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="保存日志", command=self.save_log)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)

        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            title_frame,
            text="掼蛋AI批量对战系统 - M2版本",
            font=('Arial', 16, 'bold')
        )
        title_label.pack()

        subtitle_label = ttk.Label(
            title_frame,
            text="M2：重构硬编码规则引擎（无分数累积+阈值保护）",
            font=('Arial', 10)
        )
        subtitle_label.pack()

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 配置区域
        config_frame = ttk.LabelFrame(main_frame, text="配置", padding="10")
        config_frame.pack(fill=tk.X, pady=5)

        # 服务器路径
        server_frame = ttk.Frame(config_frame)
        server_frame.pack(fill=tk.X, pady=5)
        ttk.Label(server_frame, text="服务器路径:").pack(side=tk.LEFT)
        self.server_path_var = tk.StringVar()
        server_entry = ttk.Entry(server_frame, textvariable=self.server_path_var, width=60)
        server_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(server_frame, text="浏览", command=self.browse_server).pack(side=tk.RIGHT)

        # 客户端脚本
        client_frame = ttk.Frame(config_frame)
        client_frame.pack(fill=tk.X, pady=5)
        ttk.Label(client_frame, text="客户端脚本:").pack(side=tk.LEFT)
        self.clients_var = tk.StringVar()
        clients_entry = ttk.Entry(client_frame, textvariable=self.clients_var, width=60)
        clients_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 目标场次
        games_frame = ttk.Frame(config_frame)
        games_frame.pack(fill=tk.X, pady=5)
        ttk.Label(games_frame, text="目标场次:").pack(side=tk.LEFT)
        self.target_games_var = tk.StringVar(value="10")
        games_spinbox = ttk.Spinbox(games_frame, from_=1, to=100, textvariable=self.target_games_var, width=10)
        games_spinbox.pack(side=tk.LEFT, padx=5)

        # 版本信息
        version_frame = ttk.LabelFrame(main_frame, text="版本信息", padding="5")
        version_frame.pack(fill=tk.X, pady=5)

        info_text = tk.Text(version_frame, height=6, wrap=tk.WORD, font=('Arial', 9))
        info_text.pack(fill=tk.X)
        info_text.insert(tk.END,
            "M2核心改进（对比M1）：\n"
            "• 保护逻辑内联在按牌型分发的处理器中（lalala风格）\n"
            "• 不加载共享TeammateProtectionStrategy（去掉分数累积+阈值）\n"
            "• PASS次数降级链完整（pass_num>=5 → special, >=7 → bomb）\n"
            "• 队友剩牌≤4时只出刚好大1（精确边界控制）\n"
            "• 开局主动恢复一手出完检查\n"
            "• 所有改动限制在M2专用文件，不碰共用层"
        )
        info_text.config(state=tk.DISABLED)

        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.start_button = ttk.Button(
            button_frame,
            text="开始对战",
            style='Start.TButton',
            command=self.start_batch,
            width=15
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_frame,
            text="停止",
            style='Stop.TButton',
            command=self.stop_batch,
            state=tk.DISABLED,
            width=15
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            button_frame,
            text="清空日志",
            command=self.clear_log,
            width=15
        ).pack(side=tk.RIGHT, padx=5)

        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=('Courier New', 9),
            height=15
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志标签
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('WARNING', foreground='orange')
        self.log_text.tag_config('ERROR', foreground='red')
        self.log_text.tag_config('SUCCESS', foreground='green')

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding="5"
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def load_default_config(self):
        """加载默认配置（M2版本）"""
        possible_paths = [
            "../GDAI/离线平台/windows/guandan_offline_v1006.exe",
            "D:/GDAI/server/windows/guandan_offline_v1006.exe",
            "D:/GDAI/离线平台/windows/guandan_offline_v1006.exe",
            "guandan_offline_v1006.exe",
            "../guandan_offline_v1006.exe",
            "server/guandan_offline_v1006.exe"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                self.server_path_var.set(os.path.abspath(path))
                break

        # M2版本默认客户端脚本
        default_clients_m2 = [
            "src/communication/yf1_m2.py",                   # 0号位 - YiFei M2
            "src/communication/run_lalala_client3.py",       # 1号位 - 对手1
            "src/communication/yf2_m2.py",                   # 2号位 - YiFei M2
            "src/communication/run_lalala_client4.py"        # 3号位 - 对手2
        ]
        # 队伍A（YiFei M2队）：0号(yf1_m2) + 2号(yf2_m2)
        # 队伍B（对手队）：1号(client3) + 3号(client4)

        existing_clients = [c for c in default_clients_m2 if os.path.exists(c)]
        if existing_clients:
            self.clients_var.set(", ".join(existing_clients))
        else:
            self.clients_var.set("请输入4个客户端脚本路径（逗号分隔）")
            self.log_message("警告：M2客户端文件不存在", "WARNING")

    def browse_server(self):
        """浏览服务器文件"""
        filename = filedialog.askopenfilename(
            title="选择服务器可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.server_path_var.set(filename)

    def log_message(self, message, level="INFO"):
        """添加日志消息"""
        self.log_text.insert(tk.END, message + "\n", level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    def save_log(self):
        """保存日志"""
        filename = filedialog.asksaveasfilename(
            title="保存日志",
            defaultextension=".log",
            filetypes=[("日志文件", "*.log"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log_message("日志已保存: {}".format(filename), "SUCCESS")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

    def show_help(self):
        """显示使用说明"""
        help_text = (
            "M2版本使用说明：\n\n"
            "1. 选择服务器可执行文件路径\n"
            "2. 确认客户端脚本路径（默认yf1_m2/yf2_m2 + lalala）\n"
            "3. 设置目标场次数\n"
            "4. 点击「开始对战」启动批量对战\n\n"
            "M2核心改进：\n"
            "- 保护逻辑内联在按牌型分发的处理器中\n"
            "- 不加载共享TeammateProtectionStrategy\n"
            "- PASS次数降级链完整\n"
            "- 队友剩牌≤4时只出刚好大1\n"
            "- 开局主动恢复一手出完检查\n\n"
            "注意：所有改动限制在M2专用文件，不碰共用层"
        )
        messagebox.showinfo("使用说明", help_text)

    def show_about(self):
        """显示关于信息"""
        about_text = (
            "掼蛋AI批量对战系统 - M2版本 v1.0\n\n"
            "M2：重构硬编码规则引擎\n"
            "基于M1架构重构，去掉分数累积+阈值保护\n"
            "保护逻辑内联在按牌型分发的处理器中"
        )
        messagebox.showinfo("关于", about_text)

    def start_batch(self):
        """开始批量对战"""
        if self.is_running:
            return

        server_path = self.server_path_var.get().strip()
        if not server_path or not os.path.exists(server_path):
            messagebox.showerror("错误", "请选择有效的服务器可执行文件路径")
            return

        clients_str = self.clients_var.get().strip()
        if not clients_str:
            messagebox.showerror("错误", "请输入客户端脚本路径")
            return

        clients = [c.strip() for c in clients_str.split(",")]

        try:
            target_games = int(self.target_games_var.get())
        except ValueError:
            messagebox.showerror("错误", "目标场次必须是整数")
            return

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_var.set("运行中...")
        self.log_message("=" * 50, "INFO")
        self.log_message("开始M2批量对战", "INFO")
        self.log_message("服务器: {}".format(server_path), "INFO")
        self.log_message("客户端: {}".format(clients), "INFO")
        self.log_message("目标场次: {}".format(target_games), "INFO")
        self.log_message("=" * 50, "INFO")

        self.executor_thread = threading.Thread(
            target=self._run_batch,
            args=(server_path, clients, target_games),
            daemon=True
        )
        self.executor_thread.start()

    def _run_batch(self, server_path, clients, target_games):
        """在后台线程中运行批量对战"""
        try:
            self.executor = BatchExecutor(
                server_path=server_path,
                clients=clients,
                target_games=target_games,
                callback=self._update_progress
            )
            self.executor.run()
        except Exception as e:
            self.log_message("运行错误: {}".format(e), "ERROR")
        finally:
            self.root.after(0, self._on_batch_complete)

    def _update_progress(self, current, total, message):
        """更新进度"""
        progress = (current / total) * 100 if total > 0 else 0
        self.progress_var.set(progress)
        self.log_message("[{}/{}] {}".format(current, total, message), "INFO")
        self.status_var.set("已完成 {}/{} 场".format(current, total))

    def _on_batch_complete(self):
        """批量对战完成"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("完成")
        self.log_message("批量对战完成！", "SUCCESS")

    def stop_batch(self):
        """停止批量对战"""
        if self.executor and self.is_running:
            self.executor.stop()
            self.is_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_var.set("已停止")
            self.log_message("批量对战已停止", "WARNING")


def main():
    root = tk.Tk()
    app = BatchExecutorGUIM2(root)
    root.mainloop()


if __name__ == "__main__":
    main()
