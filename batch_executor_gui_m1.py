"""
批量游戏执行系统 - M1版本图形界面

提供简单易用的GUI界面来配置和运行M1硬编码规则引擎的批量游戏执行。
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from batch_executor.executor import BatchExecutor
from batch_executor.logging_config import setup_logging


class BatchExecutorGUIM1:
    """批量游戏执行系统图形界面 - M1版本"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("掼蛋AI批量对战系统 - M1版本 v1.0")
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
        
        # 加载默认配置（M1版本）
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
            text="掼蛋AI批量对战系统 - M1硬编码规则引擎",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        # M1版本说明
        info_frame = ttk.Frame(self.root, padding="5")
        info_frame.pack(fill=tk.X, padx=10)
        
        info_text = "M1特性：5阶段细分路由 | 策略引擎集成 | 手牌结构分析器增强 | 残局策略类"
        info_label = ttk.Label(
            info_frame,
            text=info_text,
            foreground="blue",
            font=("Arial", 9)
        )
        info_label.pack()
        
        # 配置区域
        config_frame = ttk.LabelFrame(self.root, text="配置参数", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 目标场数
        ttk.Label(config_frame, text="目标场数:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.target_games_var = tk.StringVar(value="3")
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
        help_text = "提示: 前2个是M1 AI（一队），后2个是对手AI（另一队）"
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
        
        clear_btn = ttk.Button(
            control_frame,
            text="清空日志",
            command=self.clear_log
        )
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(self.root, text="执行状态", padding="10")
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # 状态信息
        info_frame = ttk.Frame(status_frame)
        info_frame.pack(fill=tk.X)
        
        self.status_label = ttk.Label(info_frame, text="就绪", font=("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_label = ttk.Label(info_frame, text="0 / 0", font=("Arial", 10))
        self.progress_label.pack(side=tk.LEFT, padx=20)
        
        self.restart_label = ttk.Label(info_frame, text="重启: 0", font=("Arial", 10))
        self.restart_label.pack(side=tk.LEFT, padx=20)
        
        self.score_label = ttk.Label(info_frame, text="战绩: 0-0", font=("Arial", 10))
        self.score_label.pack(side=tk.LEFT, padx=20)
        
        # 日志区域
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
        """加载默认配置（M1版本）"""
        # 尝试找到服务器可执行文件
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
        
        # M1版本默认客户端脚本
        # 座位分配：0号和2号是队友（一队），1号和3号是队友（一队）
        default_clients_m1 = [
            "src/communication/yf1_m1.py",                   # 0号位 - YiFei M1
            "src/communication/run_lalala_client3.py",       # 1号位 - 对手1
            "src/communication/yf2_m1.py",                   # 2号位 - YiFei M1
            "src/communication/run_lalala_client4.py"        # 3号位 - 对手2
        ]
        # 队伍分组：
        # 队伍A（YiFei M1队）：0号(yf1_m1) + 2号(yf2_m1)
        # 队伍B（对手队）：1号(client3) + 3号(client4)
        # 注：M1版本使用硬编码规则引擎，具有：
        #     - 5阶段细分路由（开局、中局前期、中局后期、残局前期、残局后期）
        #     - 主动/被动出牌分离
        #     - 策略引擎集成（队友保护、优先级系统、牌值系统）
        #     - 手牌结构分析器增强
        #     - 残局策略类（RushStrategy, DefendStrategy等）
        
        # 检查哪些客户端存在
        existing_clients = [c for c in default_clients_m1 if os.path.exists(c)]
        if existing_clients:
            self.clients_var.set(", ".join(existing_clients))
        else:
            # 如果默认路径不存在，给出提示
            self.clients_var.set("请输入4个客户端脚本路径（逗号分隔）")
            self.log_message("⚠️ 警告：M1客户端文件不存在，请检查是否在 m-dev 分支", "WARNING")
    
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
        """保存日志到文件"""
        filename = filedialog.asksaveasfilename(
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
    
    def update_progress_timer(self):
        """更新进度定时器"""
        if self.is_running and self.executor:
            try:
                # get_state() 返回 ExecutionState（dataclass），不是 dict
                state = self.executor.get_state()
                if state is None:
                    raise ValueError("state is None")
                completed = state.completed_games
                target = state.target_games
                restarts = state.restart_count
                tracker = getattr(self.executor, "tracker", None)
                if tracker is not None:
                    wins = getattr(tracker, "team_a_wins", 0)
                    losses = getattr(tracker, "team_b_wins", 0)
                else:
                    wins, losses = 0, 0
                
                # 更新进度条
                if target > 0:
                    progress = (completed / target) * 100
                    self.progress_var.set(progress)
                
                # 更新标签
                self.progress_label.config(text=f"{completed} / {target}")
                self.restart_label.config(text=f"重启: {restarts}")
                self.score_label.config(text=f"战绩: {wins}-{losses}")
                
                # 更新状态
                if completed >= target:
                    self.status_label.config(text="完成")
                else:
                    self.status_label.config(text="运行中...")
                
            except Exception:
                pass
        
        # 继续定时更新
        if self.is_running:
            self.root.after(1000, self.update_progress_timer)
    
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
        
        # 检查M1客户端文件是否存在
        m1_clients = [c for c in clients if 'm1' in c.lower()]
        for client in m1_clients:
            if not os.path.exists(client):
                messagebox.showwarning(
                    "配置警告", 
                    f"M1客户端文件不存在: {client}\n\n请确保：\n1. 已切换到 m-dev 分支\n2. 文件路径正确"
                )
        
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
        self.log_message("开始M1批量游戏执行", "SUCCESS")
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
            self.log_message(f"M1版本: 硬编码规则引擎", "INFO")
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
            
            # 创建执行器
            self.executor = BatchExecutor(
                target_games=target_games,
                server_path=server_path,
                client_scripts=clients,
                diagnose_only=diagnose_only,
                enable_signal_handler=False,
                visible_server=True
            )
            
            # 与 CLI 一致：run() 内先诊断，再按需进入批量；状态写入 execution_state.json
            if diagnose_only:
                self.log_message("正在诊断（run() → run_diagnostic）...", "INFO")
            else:
                self.log_message("开始执行批量游戏...", "INFO")
            self.executor.run()
            
            # 执行完成
            self.log_message("\n" + "=" * 60, "INFO")
            self.log_message(
                "诊断完成" if diagnose_only else "批量游戏执行完成",
                "SUCCESS",
            )
            self.log_message("=" * 60, "INFO")
            
            if not diagnose_only:
                state = self.executor.get_state()
                if state is not None:
                    completed = state.completed_games
                    tracker = getattr(self.executor, "tracker", None)
                    if tracker is not None:
                        wins = tracker.team_a_wins
                        losses = tracker.team_b_wins
                    else:
                        wins, losses = 0, 0
                else:
                    completed, wins, losses = 0, 0, 0
                
                self.log_message(f"\n完成场数: {completed}", "INFO")
                self.log_message(f"胜场: {wins}", "SUCCESS")
                self.log_message(f"负场: {losses}", "INFO")
                if completed > 0:
                    win_rate = (wins / completed) * 100
                    self.log_message(f"胜率: {win_rate:.2f}%", "SUCCESS")
        
        except Exception as e:
            self.log_message(f"执行错误: {e}", "ERROR")
            import traceback
            self.log_message(traceback.format_exc(), "ERROR")
            messagebox.showerror("错误", f"执行失败:\n{e}")
        finally:
            # 恢复UI状态
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def stop_execution(self):
        """停止执行"""
        if not self.is_running:
            return
        
        if messagebox.askyesno("确认", "确定要停止执行吗？"):
            self.log_message("正在停止执行...", "WARNING")
            if self.executor:
                self.executor.stop()
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.log_message("执行已停止", "INFO")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
M1批量对战系统使用说明

1. 配置参数
   - 目标场数：要执行的游戏总场数
   - 服务器路径：掼蛋游戏服务器可执行文件
   - 客户端脚本：4个客户端脚本（逗号分隔）
     * 前2个是M1 AI（一队）
     * 后2个是对手AI（另一队）

2. 重要提示
   - 必须在 m-dev 分支运行
   - M1是硬编码规则引擎，不是机器学习模型
   - 无需模型文件

3. 运行流程
   - 点击"开始执行"启动批量对战
   - 观察进度和日志
   - 等待完成或点击"停止"

4. 查看结果
   - 实时查看执行日志
   - 查看进度条和战绩统计
   - 保存日志到文件

详细说明请参考：
- docs/development/M1测试指南.md
- docs/training/YF硬编码完整提升计划优化版.md
        """
        messagebox.showinfo("使用说明", help_text)
    
    def show_about(self):
        """显示关于信息"""
        about_text = """
掼蛋AI批量对战系统 - M1版本

版本：v1.0
系列：M（硬编码规则引擎）

特性：
- 5阶段细分路由
- 策略引擎集成
- 手牌结构分析器增强
- 残局策略类

开发：YiFei AI Team
        """
        messagebox.showinfo("关于", about_text)


def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    # 创建GUI
    app = BatchExecutorGUIM1(root)
    
    # 运行主循环
    root.mainloop()


if __name__ == "__main__":
    main()

