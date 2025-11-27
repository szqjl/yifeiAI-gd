"""
批量游戏执行系统 - 图形界面

提供简单易用的GUI界面来配置和运行批量游戏执行。
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from batch_executor.main import BatchExecutor
from batch_executor.logging_config import setup_logging


class BatchExecutorGUI:
    """批量游戏执行系统图形界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("掼蛋AI批量对战系统 v1.0")
        self.root.geometry("950x750")
        self.root.resizable(True, True)
        
        # 设置窗口图标（如果有的话）
        try:
            # self.root.iconbitmap('icon.ico')
            pass
        except:
            pass
        
        # 执行器实例
        self.executor = None
        self.executor_thread = None
        self.is_running = False
        
        # 配置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
        # 加载默认配置
        self.load_default_config()
    
    def setup_styles(self):
        """配置界面样式"""
        style = ttk.Style()
        
        # 配置按钮样式
        style.configure('Start.TButton', foreground='green', font=('Arial', 10, 'bold'))
        style.configure('Stop.TButton', foreground='red', font=('Arial', 10, 'bold'))
    
    def create_widgets(self):
        """创建界面组件"""
        
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="保存日志", command=self.save_log)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        
        # 标题
        title_frame = ttk.Frame(self.root, padding="10")
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            title_frame,
            text="掼蛋AI批量对战系统",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        # 配置区域
        config_frame = ttk.LabelFrame(self.root, text="配置参数", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 目标场数
        ttk.Label(config_frame, text="目标场数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.target_games_var = tk.StringVar(value="100")
        target_games_entry = ttk.Entry(config_frame, textvariable=self.target_games_var, width=20)
        target_games_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(config_frame, text="场", foreground="gray").grid(row=0, column=2, sticky=tk.W)
        
        # 服务器路径
        ttk.Label(config_frame, text="服务器路径:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.server_path_var = tk.StringVar()
        server_path_entry = ttk.Entry(config_frame, textvariable=self.server_path_var, width=50)
        server_path_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        browse_btn = ttk.Button(config_frame, text="浏览...", command=self.browse_server)
        browse_btn.grid(row=1, column=2, sticky=tk.W, padx=5)
        ttk.Label(config_frame, text="(必须是可执行文件，如 .exe)", foreground="gray", font=("Arial", 8)).grid(row=1, column=3, sticky=tk.W)
        
        # 客户端脚本
        ttk.Label(config_frame, text="客户端脚本:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.clients_var = tk.StringVar()
        clients_entry = ttk.Entry(config_frame, textvariable=self.clients_var, width=50)
        clients_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(config_frame, text="(4个脚本，逗号分隔)", foreground="gray").grid(row=2, column=2, sticky=tk.W)
        
        # 添加说明标签
        help_text = "提示: 前2个是您的AI（一队），后2个是对手AI（另一队）"
        ttk.Label(config_frame, text=help_text, foreground="blue", font=("Arial", 8)).grid(
            row=3, column=1, sticky=tk.W, pady=(0, 5), padx=5
        )
        
        # 诊断模式
        self.diagnose_only_var = tk.BooleanVar(value=False)
        diagnose_check = ttk.Checkbutton(
            config_frame,
            text="仅诊断模式（不执行游戏）",
            variable=self.diagnose_only_var
        )
        diagnose_check.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 控制按钮区域
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X, padx=10)
        
        self.start_btn = ttk.Button(
            control_frame,
            text="▶ 开始执行",
            command=self.start_execution,
            style="Start.TButton"
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="⏹ 停止",
            command=self.stop_execution,
            state=tk.DISABLED,
            style="Stop.TButton"
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = ttk.Button(
            control_frame,
            text="清空日志",
            command=self.clear_log
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(self.root, text="执行状态", padding="10")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # 状态信息
        status_info_frame = ttk.Frame(status_frame)
        status_info_frame.pack(fill=tk.X)
        
        ttk.Label(status_info_frame, text="已完成:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.completed_label = ttk.Label(status_info_frame, text="0 / 0", foreground="blue")
        self.completed_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(status_info_frame, text="重启次数:").grid(row=0, column=2, sticky=tk.W, padx=20)
        self.restart_label = ttk.Label(status_info_frame, text="0", foreground="orange")
        self.restart_label.grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(status_info_frame, text="战绩:").grid(row=0, column=4, sticky=tk.W, padx=20)
        self.score_label = ttk.Label(status_info_frame, text="0 胜 / 0 负", foreground="green")
        self.score_label.grid(row=0, column=5, sticky=tk.W)
        
        # 日志显示区域
        log_frame = ttk.LabelFrame(self.root, text="执行日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=20,
            font=("Consolas", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志文本标签
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("SUCCESS", foreground="green")
    
    def load_default_config(self):
        """加载默认配置"""
        # 尝试找到服务器可执行文件
        possible_paths = [
            "guandan_offline_v1006.exe",
            "../guandan_offline_v1006.exe",
            "server/guandan_offline_v1006.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.server_path_var.set(os.path.abspath(path))
                break
        
        # 默认客户端脚本（您的AI vs lalala一等奖AI）
        default_clients = [
            "src/communication/Test1.py",                    # 您的AI - 队友1
            "src/communication/Test2.py",                    # 您的AI - 队友2
            "src/communication/run_lalala_client3.py",       # lalala对手1
            "src/communication/run_lalala_client4.py"        # lalala对手2
        ]
        
        # 检查哪些客户端存在
        existing_clients = [c for c in default_clients if os.path.exists(c)]
        if existing_clients:
            self.clients_var.set(", ".join(existing_clients))
        else:
            # 如果默认路径不存在，给出提示
            self.clients_var.set("请输入4个客户端脚本路径（逗号分隔）")
    
    def browse_server(self):
        """浏览选择服务器文件"""
        filename = filedialog.askopenfilename(
            title="选择服务器可执行文件",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if filename:
            self.server_path_var.set(filename)
    
    def log_message(self, message, level="INFO"):
        """在日志区域显示消息（线程安全）"""
        def _log():
            self.log_text.insert(tk.END, message + "\n", level)
            self.log_text.see(tk.END)
        
        # 使用after确保在主线程中执行
        self.root.after(0, _log)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def validate_config(self):
        """验证配置"""
        try:
            target_games = int(self.target_games_var.get())
            if target_games <= 0:
                raise ValueError("目标场数必须大于0")
        except ValueError as e:
            messagebox.showerror("配置错误", f"目标场数无效: {e}")
            return False
        
        server_path = self.server_path_var.get().strip()
        if not server_path:
            messagebox.showerror("配置错误", "请指定服务器路径")
            return False
        
        if not os.path.exists(server_path):
            messagebox.showerror("配置错误", f"服务器文件不存在: {server_path}")
            return False
        
        clients = [c.strip() for c in self.clients_var.get().split(",") if c.strip()]
        if not clients and not self.diagnose_only_var.get():
            messagebox.showerror("配置错误", "请指定至少一个客户端脚本")
            return False
        
        for client in clients:
            if not os.path.exists(client):
                messagebox.showwarning("配置警告", f"客户端文件不存在: {client}")
        
        return True
    
    def start_execution(self):
        """开始执行"""
        if not self.validate_config():
            return
        
        if self.is_running:
            messagebox.showwarning("警告", "系统正在运行中")
            return
        
        # 更新UI状态
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 清空日志
        self.clear_log()
        self.log_message("=" * 60, "INFO")
        self.log_message("开始批量游戏执行", "SUCCESS")
        self.log_message("=" * 60, "INFO")
        
        # 在新线程中运行执行器
        self.executor_thread = threading.Thread(target=self.run_executor, daemon=True)
        self.executor_thread.start()
        
        # 启动进度更新定时器
        self.update_progress_timer()
    
    def run_executor(self):
        """运行执行器（在后台线程中）"""
        try:
            # 获取配置
            target_games = int(self.target_games_var.get())
            server_path = self.server_path_var.get().strip()
            clients = [c.strip() for c in self.clients_var.get().split(",") if c.strip()]
            diagnose_only = self.diagnose_only_var.get()
            
            self.log_message(f"目标场数: {target_games}", "INFO")
            self.log_message(f"服务器: {server_path}", "INFO")
            self.log_message(f"客户端: {', '.join(clients)}", "INFO")
            self.log_message(f"诊断模式: {'是' if diagnose_only else '否'}", "INFO")
            self.log_message("-" * 60, "INFO")
            
            # 设置日志系统，将日志输出到GUI
            import logging
            
            # 创建自定义处理器，将日志输出到GUI
            class GUIHandler(logging.Handler):
                def __init__(self, gui_callback):
                    super().__init__()
                    self.gui_callback = gui_callback
                
                def emit(self, record):
                    try:
                        msg = self.format(record)
                        level = record.levelname
                        if level == "WARNING":
                            self.gui_callback(msg, "WARNING")
                        elif level == "ERROR" or level == "CRITICAL":
                            self.gui_callback(msg, "ERROR")
                        else:
                            self.gui_callback(msg, "INFO")
                    except Exception:
                        pass
            
            # 配置根日志记录器，捕获所有模块的日志
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.INFO)
            
            # 移除现有的处理器
            root_logger.handlers.clear()
            
            # 添加GUI处理器
            gui_handler = GUIHandler(self.log_message)
            gui_handler.setFormatter(logging.Formatter('%(message)s'))
            root_logger.addHandler(gui_handler)
            
            # 同时配置batch_executor的logger
            logger = logging.getLogger("batch_executor")
            logger.setLevel(logging.INFO)
            
            # 创建执行器（禁用信号处理器，因为在后台线程中）
            self.executor = BatchExecutor(
                target_games=target_games,
                server_path=server_path,
                client_scripts=clients,
                diagnose_only=diagnose_only,
                enable_signal_handler=False
            )
            
            if diagnose_only:
                self.log_message("正在诊断服务器配置...", "INFO")
                # 执行诊断
                report = self.executor.run_diagnostic()
                
                if report:
                    self.log_message("\n诊断报告:", "SUCCESS")
                    self.log_message(f"发现配置文件: {', '.join(report.config_files_found) if report.config_files_found else '无'}", "INFO")
                    self.log_message(f"期望游戏次数: {report.expected_count}", "INFO")
                    self.log_message(f"实际游戏次数: {report.actual_count if report.actual_count else '未检测到'}", "INFO")
                    
                    if report.mismatch_detected:
                        self.log_message("\n检测到参数不匹配！", "WARNING")
                        self.log_message("可能原因:", "WARNING")
                        for cause in report.possible_causes:
                            self.log_message(f"  - {cause}", "WARNING")
                        self.log_message("\n建议:", "INFO")
                        for rec in report.recommendations:
                            self.log_message(f"  - {rec}", "INFO")
                    else:
                        self.log_message("\n参数配置正常", "SUCCESS")
                    
                    self.log_message("\n诊断完成", "SUCCESS")
                else:
                    self.log_message("\n诊断失败，请检查服务器路径和配置", "ERROR")
            else:
                self.log_message("开始执行游戏...", "INFO")
                
                try:
                    import time
                    
                    # 直接在当前线程运行执行器（因为已经在后台线程中了）
                    self.executor.run()
                
                except RuntimeError as e:
                    self.log_message(f"\n执行失败: {e}", "ERROR")
                    self.log_message("\n请检查:", "WARNING")
                    self.log_message("  1. 服务器路径是否正确", "WARNING")
                    self.log_message("  2. 服务器文件是否存在", "WARNING")
                    self.log_message("  3. 是否有执行权限", "WARNING")
                    self.log_message("\n建议: 先使用'仅诊断模式'检查配置", "INFO")
        
        except Exception as e:
            import traceback
            error_msg = f"执行出错: {e}"
            self.log_message(f"\n{error_msg}", "ERROR")
            self.log_message(traceback.format_exc(), "ERROR")
        
        finally:
            # 恢复UI状态
            self.root.after(0, self.execution_finished)
    
    def update_progress_timer(self):
        """定时更新进度（每秒调用一次）"""
        if not self.is_running:
            return
        
        # 获取当前状态并更新显示
        if self.executor:
            state = self.executor.get_state()
            if state:
                completed = state.completed_games
                total = state.target_games
                restarts = state.restart_count
                progress = (completed / total * 100) if total > 0 else 0
                
                self.progress_var.set(progress)
                self.completed_label.config(text=f"{completed} / {total}")
                self.restart_label.config(text=str(restarts))
                
                # 更新战绩
                if self.executor.tracker:
                    tracker = self.executor.tracker
                    score_text = f"{tracker.team_a_wins} 胜 / {tracker.team_b_wins} 负"
                    self.score_label.config(text=score_text)
        
        # 1秒后再次调用
        if self.is_running:
            self.root.after(1000, self.update_progress_timer)
    
    def update_progress(self, completed, total, progress, restarts=0):
        """更新进度显示（手动调用）"""
        self.progress_var.set(progress)
        self.completed_label.config(text=f"{completed} / {total}")
        self.restart_label.config(text=str(restarts))
        
        # 更新战绩
        if self.executor and self.executor.tracker:
            tracker = self.executor.tracker
            score_text = f"{tracker.team_a_wins} 胜 / {tracker.team_b_wins} 负"
            self.score_label.config(text=score_text)
    
    def stop_execution(self):
        """停止执行"""
        if not self.is_running:
            return
        
        if messagebox.askyesno("确认", "确定要停止执行吗？当前进度将被保存。"):
            self.is_running = False
            self.log_message("正在停止执行...", "WARNING")
            
            if self.executor:
                try:
                    self.executor.stop()
                    self.log_message("执行已停止，状态已保存", "INFO")
                except Exception as e:
                    self.log_message(f"停止时出错: {e}", "ERROR")
    
    def execution_finished(self):
        """执行完成后的清理"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log_message("=" * 60, "INFO")
        self.log_message("执行结束", "INFO")
    
    def save_log(self):
        """保存日志到文件"""
        filename = filedialog.asksaveasfilename(
            title="保存日志",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("成功", f"日志已保存到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"保存日志失败: {e}")
    
    def show_help(self):
        """显示使用说明"""
        help_text = """
掼蛋AI批量对战系统 - 使用说明

1. 配置参数
   - 目标场数: 设置要执行的游戏总场数
   - 服务器路径: 选择服务器可执行文件
   - 客户端脚本: 输入客户端脚本路径（逗号分隔）
   - 诊断模式: 仅诊断服务器配置

2. 开始执行
   - 点击"开始执行"按钮启动
   - 观察进度条和日志信息
   - 可随时点击"停止"按钮中断

3. 查看结果
   - 执行状态区域显示实时进度
   - 日志区域显示详细信息
   - 完成后显示最终战绩

更多信息请查看 GUI_使用说明.md
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("500x400")
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=("Arial", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, help_text)
        text.config(state=tk.DISABLED)
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
掼蛋AI批量对战系统 v1.0

一个用于批量执行掼蛋AI对战的自动化工具

功能特点:
• 自动重启服务器和客户端
• 战绩跟踪和统计
• 进度保存和恢复
• 服务器配置诊断

开发: YiFeiAI Team
版本: 1.0.0
        """
        messagebox.showinfo("关于", about_text)


def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    # 创建GUI
    app = BatchExecutorGUI(root)
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()
