# -*- coding: utf-8 -*-
"""
训练GUI工具
用于导入平台数据、转换、训练模型，并显示训练日志
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import json
from datetime import datetime
import queue

# **修复**：设置Windows控制台编码为UTF-8
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.knowledge_processor.platform_replay_converter import (
    convert_rep_directory, 
    convert_rep_to_training_format,
    convert_to_replay_parser_format
)
from src.knowledge_processor.replay_parser import ReplayParser
from src.train.pretrain import train_bc
import torch


class TrainingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("掼蛋AI训练工具")
        self.root.geometry("1000x700")
        
        # 训练日志队列（用于线程间通信）
        self.log_queue = queue.Queue()
        
        # 创建界面
        self.create_widgets()
        
        # 启动日志处理
        self.process_log_queue()
        
    def create_widgets(self):
        """创建GUI组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # 1. 数据导入区域
        data_frame = ttk.LabelFrame(main_frame, text="1. 数据导入", padding="10")
        data_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        data_frame.columnconfigure(1, weight=1)
        
        ttk.Label(data_frame, text=".rep文件/目录:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.rep_path_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.rep_path_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(data_frame, text="浏览", command=self.browse_rep_file).grid(row=0, column=2, padx=5)
        
        ttk.Label(data_frame, text="输出目录:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_dir_var = tk.StringVar(value="game_records")
        ttk.Entry(data_frame, textvariable=self.output_dir_var, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(data_frame, text="浏览", command=self.browse_output_dir).grid(row=1, column=2, padx=5)
        
        ttk.Label(data_frame, text="目标玩家ID (seat):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.target_player_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.target_player_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(data_frame, text="(留空=所有玩家)").grid(row=2, column=1, sticky=tk.W, padx=(150, 5))
        
        self.prefer_winner_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(data_frame, text="优先选择获胜玩家", variable=self.prefer_winner_var).grid(row=2, column=2, sticky=tk.W, padx=5)
        ttk.Label(data_frame, text="(推荐：学习胜利策略)", font=("", 8)).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # 转换按钮
        button_frame = ttk.Frame(data_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(button_frame, text="转换数据", command=self.convert_data).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="批量转换", command=self.batch_convert_data).grid(row=0, column=1, padx=5)
        
        # 2. 训练配置区域
        train_frame = ttk.LabelFrame(main_frame, text="2. 训练配置", padding="10")
        train_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        train_frame.columnconfigure(1, weight=1)
        
        ttk.Label(train_frame, text="训练类型:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.train_type_var = tk.StringVar(value="pretrain")
        ttk.Radiobutton(train_frame, text="预训练 (Behavior Cloning)", variable=self.train_type_var, value="pretrain").grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(train_frame, text="强化学习 (Self-Play)", variable=self.train_type_var, value="self_play").grid(row=0, column=2, sticky=tk.W, padx=5)
        
        ttk.Label(train_frame, text="训练轮数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.epochs_var = tk.StringVar(value="50")
        ttk.Entry(train_frame, textvariable=self.epochs_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(train_frame, text="(推荐: 50轮)", font=("", 8), foreground="gray").grid(row=1, column=2, sticky=tk.W, padx=5)
        
        ttk.Label(train_frame, text="批次大小:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.batch_size_var = tk.StringVar(value="64")
        ttk.Entry(train_frame, textvariable=self.batch_size_var, width=10).grid(row=1, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(train_frame, text="学习率:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.lr_var = tk.StringVar(value="0.0003")
        ttk.Entry(train_frame, textvariable=self.lr_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(train_frame, text="(推荐: 0.0003)", font=("", 8), foreground="gray").grid(row=2, column=2, sticky=tk.W, padx=5)
        
        ttk.Label(train_frame, text="模型保存路径:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_path_var = tk.StringVar(value="models/bc_model_v1.pth")
        ttk.Entry(train_frame, textvariable=self.model_path_var, width=40).grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(train_frame, text="浏览", command=self.browse_model_path).grid(row=3, column=3, padx=5)
        
        # **优化**：添加训练完成后自动评估选项
        self.auto_evaluate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(train_frame, text="训练完成后自动评估模型效果", 
                        variable=self.auto_evaluate_var).grid(row=4, column=0, columnspan=4, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(train_frame, text="开始训练", command=self.start_training).grid(row=5, column=0, columnspan=4, pady=10)
        
        # 3. 训练进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="3. 训练进度", padding="10")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(1, weight=1)
        
        ttk.Label(progress_frame, text="训练进度:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.grid(row=0, column=2, padx=5)
        
        self.progress_detail_var = tk.StringVar(value="等待开始训练...")
        ttk.Label(progress_frame, textvariable=self.progress_detail_var).grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)
        
        # 4. 训练日志区域
        log_frame = ttk.LabelFrame(main_frame, text="4. 训练日志", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 5. 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(1, weight=1)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_frame, text="状态:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        self.progress_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.progress_var).grid(row=0, column=2, sticky=tk.E)
        
        # 初始化日志
        self.log("训练工具已启动")
        self.log(f"PyTorch版本: {torch.__version__}")
        self.log(f"CUDA可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            self.log(f"CUDA设备: {torch.cuda.get_device_name(0)}")
        
    def browse_rep_file(self):
        """浏览.rep文件或目录"""
        path = filedialog.askopenfilename(
            title="选择.rep文件或目录",
            filetypes=[("Replay files", "*.rep"), ("All files", "*.*")]
        )
        if not path:
            # 如果取消，尝试选择目录
            path = filedialog.askdirectory(title="选择包含.rep文件的目录")
        if path:
            self.rep_path_var.set(path)
            
    def browse_output_dir(self):
        """浏览输出目录"""
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir_var.set(path)
            
    def browse_model_path(self):
        """浏览模型保存路径"""
        path = filedialog.asksaveasfilename(
            title="保存模型",
            defaultextension=".pth",
            filetypes=[("PyTorch models", "*.pth"), ("All files", "*.*")]
        )
        if path:
            self.model_path_var.set(path)
            
    def log(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # 同时输出到控制台（用于调试）
        print(log_message.strip())
        
    def process_log_queue(self):
        """处理日志队列（用于线程间通信）"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log(message["text"], message.get("level", "INFO"))
        except queue.Empty:
            pass
        finally:
            # 每100ms检查一次
            self.root.after(100, self.process_log_queue)
            
    def convert_data(self):
        """转换数据（在后台线程中运行）"""
        rep_path = self.rep_path_var.get()
        output_dir = self.output_dir_var.get()
        target_player = self.target_player_var.get()
        
        if not rep_path:
            messagebox.showerror("错误", "请选择.rep文件或目录")
            return
            
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return
            
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 在后台线程中运行
        def convert_thread():
            try:
                self.log_queue.put({"text": "开始转换数据...", "level": "INFO"})
                self.status_var.set("转换中...")
                
                target_player_id = int(target_player) if target_player.strip() else None
                prefer_winner = self.prefer_winner_var.get()
                
                if os.path.isfile(rep_path) and rep_path.endswith(".rep"):
                    # 单个文件
                    self.log_queue.put({"text": f"转换单个文件: {rep_path}", "level": "INFO"})
                    if prefer_winner and target_player_id is None:
                        self.log_queue.put({"text": "自动识别获胜玩家...", "level": "INFO"})
                    training_data = convert_rep_to_training_format(rep_path, target_player_id, prefer_winner)
                    
                    if training_data and len(training_data.get("training_samples", [])) > 0:
                        # 转换为ReplayParser格式
                        replays = convert_to_replay_parser_format(training_data)
                        
                        # 保存每个玩家的数据
                        for replay in replays:
                            output_file = os.path.join(output_dir, f"replay_player{replay['player_id']}_{os.path.basename(rep_path).replace('.rep', '')}.json")
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(replay, f, ensure_ascii=False, indent=2)
                            self.log_queue.put({"text": f"已保存: {output_file} ({len(replay.get('actions', []))} 个动作)", "level": "INFO"})
                        
                        self.log_queue.put({"text": f"转换完成: {len(training_data['training_samples'])} 个训练样本", "level": "INFO"})
                    else:
                        self.log_queue.put({"text": "未提取到训练样本", "level": "WARNING"})
                else:
                    # 目录
                    self.log_queue.put({"text": f"转换目录: {rep_path}", "level": "INFO"})
                    if prefer_winner and target_player_id is None:
                        self.log_queue.put({"text": "自动识别每个对局的获胜玩家...", "level": "INFO"})
                    convert_rep_directory(
                        rep_dir=rep_path,
                        output_dir=output_dir,
                        target_player_id=target_player_id,
                        format="replay_parser",
                        prefer_winner=prefer_winner
                    )
                    self.log_queue.put({"text": "目录转换完成", "level": "INFO"})
                
                self.status_var.set("转换完成")
                self.log_queue.put({"text": "数据转换完成！", "level": "INFO"})
                
            except Exception as e:
                error_msg = f"转换失败: {str(e)}"
                self.log_queue.put({"text": error_msg, "level": "ERROR"})
                import traceback
                self.log_queue.put({"text": traceback.format_exc(), "level": "ERROR"})
                self.status_var.set("转换失败")
                
        threading.Thread(target=convert_thread, daemon=True).start()
    
    def batch_convert_data(self):
        """批量转换数据（在后台线程中运行）"""
        rep_dir = self.rep_path_var.get()
        output_dir = self.output_dir_var.get()
        prefer_winner = self.prefer_winner_var.get()
        
        # 如果路径是文件，使用其目录
        if rep_dir and os.path.isfile(rep_dir):
            rep_dir = os.path.dirname(rep_dir)
        
        # 如果未指定目录，使用默认目录
        if not rep_dir or not os.path.isdir(rep_dir):
            rep_dir = r"C:\Program Files (x86)\gdgame\MobileGD\replay"
            if not os.path.exists(rep_dir):
                messagebox.showerror("错误", f"请选择.rep文件目录\n默认目录不存在: {rep_dir}")
                return
        
        if not output_dir:
            messagebox.showerror("错误", "请选择输出目录")
            return
        
        # 询问转换数量
        from tkinter import simpledialog
        max_files = simpledialog.askinteger(
            "批量转换",
            "请输入要转换的文件数量（留空表示全部）:",
            initialvalue=1000,
            minvalue=1
        )
        
        if max_files is None:
            return  # 用户取消
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 在后台线程中运行
        def batch_convert_thread():
            try:
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                self.log_queue.put({"text": "开始批量转换数据...", "level": "INFO"})
                self.log_queue.put({"text": f"源目录: {rep_dir}", "level": "INFO"})
                self.log_queue.put({"text": f"输出目录: {output_dir}", "level": "INFO"})
                self.log_queue.put({"text": f"最大文件数: {max_files if max_files > 0 else '全部'}", "level": "INFO"})
                self.log_queue.put({"text": f"优先选择获胜玩家: {prefer_winner}", "level": "INFO"})
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                
                self.status_var.set("批量转换中...")
                
                # 导入批量转换器
                from src.knowledge_processor.batch_convert_replays import BatchReplayConverter
                
                # 创建转换器
                converter = BatchReplayConverter(
                    rep_dir=rep_dir,
                    output_dir=output_dir,
                    prefer_winner=prefer_winner
                )
                
                # 重定向日志到GUI
                import logging
                class GUILogHandler(logging.Handler):
                    def __init__(self, log_queue):
                        super().__init__()
                        self.log_queue = log_queue
                    
                    def emit(self, record):
                        msg = self.format(record)
                        self.log_queue.put({"text": msg, "level": record.levelname})
                
                # 添加GUI日志处理器
                gui_handler = GUILogHandler(self.log_queue)
                gui_handler.setLevel(logging.INFO)
                formatter = logging.Formatter('%(message)s')
                gui_handler.setFormatter(formatter)
                
                logger = logging.getLogger('batch_convert')
                logger.addHandler(gui_handler)
                logger.setLevel(logging.INFO)
                
                # 开始转换
                converter.convert_batch(
                    max_files=max_files if max_files > 0 else None,
                    skip_existing=True
                )
                
                # 输出统计
                stats = converter.stats
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                self.log_queue.put({"text": "批量转换完成！", "level": "INFO"})
                self.log_queue.put({"text": f"总文件数: {stats['total_files']}", "level": "INFO"})
                self.log_queue.put({"text": f"成功转换: {stats['converted']}", "level": "INFO"})
                self.log_queue.put({"text": f"跳过文件: {stats['skipped']}", "level": "INFO"})
                self.log_queue.put({"text": f"失败文件: {stats['failed']}", "level": "INFO"})
                self.log_queue.put({"text": f"总训练样本: {stats['total_samples']} 个", "level": "INFO"})
                
                elapsed = stats['end_time'] - stats['start_time'] if stats['end_time'] else 0
                self.log_queue.put({"text": f"总耗时: {elapsed/60:.1f} 分钟", "level": "INFO"})
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                
                self.status_var.set("批量转换完成")
                
                # 提示用户
                messagebox.showinfo(
                    "批量转换完成",
                    f"转换完成！\n\n"
                    f"成功转换: {stats['converted']} 个文件\n"
                    f"总训练样本: {stats['total_samples']} 个\n"
                    f"耗时: {elapsed/60:.1f} 分钟"
                )
                
            except Exception as e:
                error_msg = f"批量转换失败: {str(e)}"
                self.log_queue.put({"text": error_msg, "level": "ERROR"})
                import traceback
                self.log_queue.put({"text": traceback.format_exc(), "level": "ERROR"})
                self.status_var.set("批量转换失败")
                messagebox.showerror("错误", error_msg)
        
        threading.Thread(target=batch_convert_thread, daemon=True).start()
        
    def start_training(self):
        """开始训练（在后台线程中运行）"""
        output_dir = self.output_dir_var.get()
        model_path = self.model_path_var.get()
        train_type = self.train_type_var.get()
        
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showerror("错误", "请先转换数据或选择有效的输出目录")
            return
            
        # 检查是否有训练数据
        json_files = [f for f in os.listdir(output_dir) if f.endswith(".json")]
        if not json_files:
            messagebox.showerror("错误", f"输出目录中没有找到JSON训练数据文件: {output_dir}")
            return
            
        # 创建模型目录
        model_dir = os.path.dirname(model_path)
        if model_dir:
            os.makedirs(model_dir, exist_ok=True)
            
        # 在后台线程中运行
        def training_thread():
            try:
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                self.log_queue.put({"text": f"开始{('预训练' if train_type == 'pretrain' else '强化学习训练')}...", "level": "INFO"})
                self.log_queue.put({"text": f"训练数据目录: {output_dir}", "level": "INFO"})
                self.log_queue.put({"text": f"模型保存路径: {model_path}", "level": "INFO"})
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                
                self.status_var.set("训练中...")
                
                # 重定向训练输出到日志
                import io
                from contextlib import redirect_stdout, redirect_stderr
                
                # 创建字符串缓冲区
                stdout_buffer = io.StringIO()
                stderr_buffer = io.StringIO()
                
                # 修改训练参数（通过环境变量或修改pretrain.py）
                # 这里我们直接调用训练函数，但需要修改pretrain.py以接受参数
                if train_type == "pretrain":
                    # 调用预训练
                    from src.train.pretrain import train_bc
                    
                    # 获取训练参数
                    epochs = int(self.epochs_var.get())
                    batch_size = int(self.batch_size_var.get())
                    lr = float(self.lr_var.get())
                    
                    # 初始化进度条
                    self.progress_bar['maximum'] = epochs
                    self.progress_bar['value'] = 0
                    self.progress_label.config(text="0%")
                    self.progress_detail_var.set(f"准备开始训练... (共 {epochs} 轮)")
                    self.root.update_idletasks()
                    
                    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                        train_bc(
                            data_dir=output_dir,
                            epochs=epochs,
                            batch_size=batch_size,
                            lr=lr,
                            model_path=model_path
                        )
                else:
                    # 调用强化学习训练
                    from src.train.self_play import train_self_play
                    
                    # 初始化进度条（不确定模式）
                    self.progress_bar['mode'] = 'indeterminate'
                    self.progress_bar.start()
                    self.progress_label.config(text="训练中...")
                    self.progress_detail_var.set("强化学习训练中...")
                    self.root.update_idletasks()
                    
                    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                        train_self_play()
                
                # 获取输出
                stdout_output = stdout_buffer.getvalue()
                stderr_output = stderr_buffer.getvalue()
                
                # 输出到日志并更新进度
                if stdout_output:
                    for line in stdout_output.split('\n'):
                        if line.strip():
                            self.log_queue.put({"text": line, "level": "INFO"})
                            # 解析训练进度（仅预训练）
                            if train_type == "pretrain":
                                epochs = int(self.epochs_var.get())
                                self._parse_training_line(line, epochs)
                if stderr_output:
                    for line in stderr_output.split('\n'):
                        if line.strip():
                            self.log_queue.put({"text": line, "level": "ERROR"})
                
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                self.log_queue.put({"text": "训练完成！", "level": "INFO"})
                self.status_var.set("训练完成")
                
                # 更新进度条到100%
                if train_type == "pretrain":
                    epochs = int(self.epochs_var.get())
                    self.progress_bar['value'] = epochs
                    self.progress_label.config(text="100%")
                    self.progress_detail_var.set("训练完成！")
                else:
                    # 强化学习训练，停止不确定模式
                    self.progress_bar.stop()
                    self.progress_bar['mode'] = 'determinate'
                    self.progress_bar['value'] = 100
                    self.progress_label.config(text="100%")
                    self.progress_detail_var.set("训练完成！")
                
                # 保存训练日志到文件
                self.save_training_log(model_path)
                
                # **优化**：训练完成后自动评估（如果启用）
                if self.auto_evaluate_var.get():
                    self.log_queue.put({"text": "="*60, "level": "INFO"})
                    self.log_queue.put({"text": "开始自动评估模型效果...", "level": "INFO"})
                    self.log_queue.put({"text": "="*60, "level": "INFO"})
                    self.evaluate_model_after_training(model_path)
                else:
                    self.log_queue.put({"text": "提示：可以运行 evaluate_after_training.bat 手动评估模型效果", "level": "INFO"})
                
            except Exception as e:
                error_msg = f"训练失败: {str(e)}"
                self.log_queue.put({"text": error_msg, "level": "ERROR"})
                import traceback
                self.log_queue.put({"text": traceback.format_exc(), "level": "ERROR"})
                self.status_var.set("训练失败")
                
        threading.Thread(target=training_thread, daemon=True).start()
        
    def _parse_training_line(self, line: str, total_epochs: int):
        """解析训练日志行，更新进度条"""
        import re
        # 匹配 "Epoch 1/5, Loss: 0.1234" 格式
        epoch_match = re.search(r'Epoch\s+(\d+)/(\d+).*Loss:\s+([\d.]+)', line)
        if epoch_match:
            current_epoch = int(epoch_match.group(1))
            epochs = int(epoch_match.group(2))
            loss = float(epoch_match.group(3))
            
            # 更新进度条
            progress = (current_epoch / epochs) * 100
            self.progress_bar['value'] = current_epoch
            self.progress_label.config(text=f"{progress:.1f}%")
            self.progress_detail_var.set(f"训练中... 第 {current_epoch}/{epochs} 轮, 损失: {loss:.4f}")
            self.root.update_idletasks()
    
    def _parse_training_output(self, output: str, total_epochs: int):
        """解析训练输出，更新最终进度"""
        import re
        # 查找最后一个epoch
        epoch_matches = re.findall(r'Epoch\s+(\d+)/(\d+)', output)
        if epoch_matches:
            last_match = epoch_matches[-1]
            current_epoch = int(last_match[0])
            epochs = int(last_match[1])
            
            # 更新进度条到100%
            self.progress_bar['value'] = epochs
            self.progress_label.config(text="100%")
            self.progress_detail_var.set(f"训练完成！共完成 {epochs} 轮")
    
    def save_training_log(self, model_path):
        """保存训练日志到文件"""
        try:
            log_dir = "training_logs"
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"training_log_{timestamp}.txt")
            
            # 获取所有日志内容
            log_content = self.log_text.get("1.0", tk.END)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("掼蛋AI训练日志\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"模型路径: {model_path}\n")
                f.write("="*60 + "\n\n")
                f.write(log_content)
            
            self.log_queue.put({"text": f"训练日志已保存: {log_file}", "level": "INFO"})
            
        except Exception as e:
            self.log_queue.put({"text": f"保存日志失败: {str(e)}", "level": "WARNING"})
    
    def evaluate_model_after_training(self, model_path):
        """训练完成后自动评估模型效果"""
        def evaluate_thread():
            try:
                import subprocess
                import sys
                
                # 1. 验证训练结果
                self.log_queue.put({"text": "[1/3] 验证训练结果...", "level": "INFO"})
                try:
                    result = subprocess.run(
                        [sys.executable, "src/train/check_training_completion.py"],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',  # **修复**：使用错误替换策略处理编码问题
                        timeout=60
                    )
                    if result.stdout:
                        for line in result.stdout.split('\n'):
                            if line.strip():
                                self.log_queue.put({"text": line, "level": "INFO"})
                    if result.stderr:
                        for line in result.stderr.split('\n'):
                            if line.strip():
                                self.log_queue.put({"text": line, "level": "WARNING"})
                except subprocess.TimeoutExpired:
                    self.log_queue.put({"text": "[警告] 验证超时", "level": "WARNING"})
                except Exception as e:
                    self.log_queue.put({"text": f"[错误] 验证失败: {str(e)}", "level": "ERROR"})
                
                self.log_queue.put({"text": "", "level": "INFO"})
                
                # 2. 评估模型效果
                self.log_queue.put({"text": "[2/3] 评估模型效果...", "level": "INFO"})
                try:
                    result = subprocess.run(
                        [sys.executable, "src/train/evaluate_model.py"],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',  # **修复**：使用错误替换策略处理编码问题
                        timeout=120
                    )
                    if result.stdout:
                        for line in result.stdout.split('\n'):
                            if line.strip():
                                self.log_queue.put({"text": line, "level": "INFO"})
                    if result.stderr:
                        for line in result.stderr.split('\n'):
                            if line.strip():
                                self.log_queue.put({"text": line, "level": "WARNING"})
                except subprocess.TimeoutExpired:
                    self.log_queue.put({"text": "[警告] 评估超时", "level": "WARNING"})
                except Exception as e:
                    self.log_queue.put({"text": f"[错误] 评估失败: {str(e)}", "level": "ERROR"})
                
                self.log_queue.put({"text": "", "level": "INFO"})
                
                # 3. 分析训练效果
                self.log_queue.put({"text": "[3/3] 分析训练效果...", "level": "INFO"})
                try:
                    result = subprocess.run(
                        [sys.executable, "src/train/analyze_training_effectiveness.py"],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='replace',  # **修复**：使用错误替换策略处理编码问题
                        timeout=120
                    )
                    if result.stdout:
                        for line in result.stdout.split('\n'):
                            if line.strip():
                                self.log_queue.put({"text": line, "level": "INFO"})
                    if result.stderr:
                        for line in result.stderr.split('\n'):
                            if line.strip():
                                self.log_queue.put({"text": line, "level": "WARNING"})
                except subprocess.TimeoutExpired:
                    self.log_queue.put({"text": "[警告] 分析超时", "level": "WARNING"})
                except Exception as e:
                    self.log_queue.put({"text": f"[错误] 分析失败: {str(e)}", "level": "ERROR"})
                
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                self.log_queue.put({"text": "模型评估完成！", "level": "INFO"})
                self.log_queue.put({"text": "="*60, "level": "INFO"})
                
            except Exception as e:
                self.log_queue.put({"text": f"评估过程出错: {str(e)}", "level": "ERROR"})
                import traceback
                self.log_queue.put({"text": traceback.format_exc(), "level": "ERROR"})
        
        threading.Thread(target=evaluate_thread, daemon=True).start()


def main():
    root = tk.Tk()
    app = TrainingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

