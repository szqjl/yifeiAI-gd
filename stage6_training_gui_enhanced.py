#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段6-游戏导向训练GUI工具（增强版）
整合1312数据转换器，包含完整的数据加载、转换、训练、监控、评估功能

核心功能：
1. 数据加载和格式转换 - 自动检测并转换1312格式数据
2. 数据统计分析 - 显示数据集的统计信息
3. 数据质量检查 - 验证数据完整性和有效性
4. 训练配置管理 - 保存/加载训练配置
5. 训练进度监控 - 实时显示训练指标
6. 训练评估 - 多维度评估模型效果
7. 训练报告生成 - 自动生成训练报告
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import json
import queue
import numpy as np
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.train.pretrain import train_bc
from src.train.game_oriented_evaluator import GameOrientedEvaluator
from src.train.game_oriented_validation import GameOrientedValidator
from src.knowledge_processor.replay_parser import ReplayParser
from src.utils.device_selector import select_compatible_device, get_device_info

# 导入1312转换器
try:
    import importlib.util
    converter_path = os.path.join(os.path.dirname(__file__), 'src', 'knowledge_processor', '1312_replay_converter.py')
    if os.path.exists(converter_path):
        spec = importlib.util.spec_from_file_location("replay_1312_converter", converter_path)
        converter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(converter_module)
        Replay1312Converter = converter_module.Replay1312Converter
    else:
        Replay1312Converter = None
except Exception as e:
    Replay1312Converter = None
    print(f"警告: 无法导入1312转换器: {e}")

import torch


class EnhancedStage6TrainingGUI:
    """阶段6游戏导向训练GUI（增强版）"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎯 阶段6-游戏导向训练工具（增强版）")
        self.root.geometry("1400x1000")

        # 训练监控数据
        self.training_metrics = {
            'epochs': [],
            'action_accuracy': [],
            'strategy_accuracy': [],
            'strategy_understanding': [],
            'reason_accuracy': [],
            'win_rate_loss': [],
            'strategy_consistency': [],
            'prediction_threshold': [],
            'probability_calibration': []
        }

        # 数据统计信息
        self.data_stats = {
            'total_files': 0,
            'total_samples': 0,
            'converted_files': 0,
            'valid_files': 0,
            'invalid_files': 0
        }

        # 训练日志队列
        self.log_queue = queue.Queue()
        
        # 训练状态
        self.training_active = False
        self.training_thread = None
        
        # 进度状态
        self.current_epoch = 0
        self.total_epochs = 0
        self.data_loading_progress = 0
        self.data_loading_total = 0

        # 创建界面
        self.create_widgets()

        # 启动日志处理
        self.process_log_queue()

    def create_widgets(self):
        """创建GUI组件"""
        # 创建Notebook（标签页）
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标签页1: 数据管理
        data_frame = ttk.Frame(notebook, padding="10")
        notebook.add(data_frame, text="📊 数据管理")
        self.create_data_tab(data_frame)

        # 标签页2: 训练配置
        config_frame = ttk.Frame(notebook, padding="10")
        notebook.add(config_frame, text="⚙️ 训练配置")
        self.create_config_tab(config_frame)

        # 标签页3: 训练监控
        monitor_frame = ttk.Frame(notebook, padding="10")
        notebook.add(monitor_frame, text="📈 训练监控")
        self.create_monitor_tab(monitor_frame)

        # 标签页4: 训练评估
        eval_frame = ttk.Frame(notebook, padding="10")
        notebook.add(eval_frame, text="🎯 训练评估")
        self.create_eval_tab(eval_frame)

        # 状态栏
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="🎯 阶段6训练工具就绪")
        ttk.Label(self.status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        self.progress_var = tk.StringVar(value="")
        ttk.Label(self.status_frame, textvariable=self.progress_var).pack(side=tk.RIGHT)

    def create_data_tab(self, parent):
        """创建数据管理标签页"""
        # 数据目录选择
        dir_frame = ttk.LabelFrame(parent, text="数据目录", padding="10")
        dir_frame.pack(fill=tk.X, pady=5)

        ttk.Label(dir_frame, text="训练数据目录:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.data_dir_var = tk.StringVar(value="game_records")
        ttk.Entry(dir_frame, textvariable=self.data_dir_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(dir_frame, text="浏览", command=self.browse_data_dir).grid(row=0, column=2, padx=5)
        ttk.Button(dir_frame, text="加载数据", command=self.load_and_analyze_data).grid(row=0, column=3, padx=5)
        dir_frame.columnconfigure(1, weight=1)

        # 数据转换
        convert_frame = ttk.LabelFrame(parent, text="数据格式转换", padding="10")
        convert_frame.pack(fill=tk.X, pady=5)

        ttk.Label(convert_frame, text="1312格式转换:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Button(convert_frame, text="检查并转换1312格式", command=self.convert_1312_data).grid(row=0, column=1, padx=5)
        ttk.Button(convert_frame, text="验证数据质量", command=self.validate_data_quality).grid(row=0, column=2, padx=5)
        
        self.convert_status_var = tk.StringVar(value="未检查")
        ttk.Label(convert_frame, textvariable=self.convert_status_var).grid(row=0, column=3, padx=10)

        # 数据统计
        stats_frame = ttk.LabelFrame(parent, text="数据统计", padding="10")
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.stats_text = scrolledtext.ScrolledText(
            stats_frame, height=15, width=80, wrap=tk.WORD,
            font=("Consolas", 9), bg="#f8f8f8"
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        self.stats_text.insert(tk.END, "点击'加载数据'按钮开始分析数据...\n")

    def create_config_tab(self, parent):
        """创建训练配置标签页"""
        # 基本参数
        basic_frame = ttk.LabelFrame(parent, text="基本参数", padding="10")
        basic_frame.pack(fill=tk.X, pady=5)
        basic_frame.columnconfigure(1, weight=1)

        ttk.Label(basic_frame, text="训练轮数:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.epochs_var = tk.StringVar(value="80")
        ttk.Entry(basic_frame, textvariable=self.epochs_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(basic_frame, text="批次大小:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.batch_size_var = tk.StringVar(value="64")
        ttk.Entry(basic_frame, textvariable=self.batch_size_var, width=15).grid(row=0, column=3, padx=5)

        ttk.Label(basic_frame, text="学习率:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.lr_var = tk.StringVar(value="0.0002")
        ttk.Entry(basic_frame, textvariable=self.lr_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(basic_frame, text="最大样本数:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.max_samples_var = tk.StringVar(value="15000")
        ttk.Entry(basic_frame, textvariable=self.max_samples_var, width=15).grid(row=1, column=3, padx=5)

        # 模型路径
        model_frame = ttk.LabelFrame(parent, text="模型路径", padding="10")
        model_frame.pack(fill=tk.X, pady=5)
        model_frame.columnconfigure(1, weight=1)

        ttk.Label(model_frame, text="模型保存路径:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.model_path_var = tk.StringVar(value="models/bc_model_stage6_enhanced.pth")
        ttk.Entry(model_frame, textvariable=self.model_path_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(model_frame, text="浏览", command=self.browse_model_path).grid(row=0, column=2, padx=5)

        # 阶段6特色配置
        feature_frame = ttk.LabelFrame(parent, text="🎯 阶段6特色配置", padding="10")
        feature_frame.pack(fill=tk.X, pady=5)

        self.enable_reason_learning_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(feature_frame, text="启用策略原因学习 (26类原因类型)",
                       variable=self.enable_reason_learning_var).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5)

        self.enable_win_rate_loss_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(feature_frame, text="启用胜率导向损失 (学习有效策略)",
                       variable=self.enable_win_rate_loss_var).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5)

        self.enable_dynamic_threshold_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(feature_frame, text="启用动态阈值调整 (局面自适应)",
                       variable=self.enable_dynamic_threshold_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5)

        self.auto_evaluate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(feature_frame, text="训练完成后自动进行游戏导向评估",
                       variable=self.auto_evaluate_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5)

        # 阶段6优化版：两阶段训练选项
        ttk.Separator(feature_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.enable_two_stage_var = tk.BooleanVar(value=True)
        # 使用tk.Checkbutton以支持font参数，或移除font参数使用ttk.Checkbutton
        two_stage_check = ttk.Checkbutton(feature_frame, text="✅ 启用两阶段训练（阶段6优化版，提升稳定性）",
                       variable=self.enable_two_stage_var)
        two_stage_check.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        two_stage_info_frame = ttk.Frame(feature_frame)
        two_stage_info_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=20, pady=5)
        
        # 使用tk.Label以支持font和foreground参数
        tk.Label(two_stage_info_frame, text="第一阶段：冻结主干（fc1, fc2），只训练决策头", 
                 font=("Arial", 8), fg="gray").pack(anchor=tk.W)
        tk.Label(two_stage_info_frame, text="第二阶段：全量微调，混合原始数据+成功轨迹", 
                 font=("Arial", 8), fg="gray").pack(anchor=tk.W)
        
        # 两阶段训练配置
        two_stage_config_frame = ttk.Frame(feature_frame)
        two_stage_config_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=20, pady=5)
        
        ttk.Label(two_stage_config_frame, text="第一阶段轮数:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.stage1_epochs_var = tk.StringVar(value="30")
        ttk.Entry(two_stage_config_frame, textvariable=self.stage1_epochs_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(two_stage_config_frame, text="第二阶段轮数:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.stage2_epochs_var = tk.StringVar(value="50")
        ttk.Entry(two_stage_config_frame, textvariable=self.stage2_epochs_var, width=10).grid(row=0, column=3, padx=5)

        # 配置管理
        config_mgmt_frame = ttk.LabelFrame(parent, text="配置管理", padding="10")
        config_mgmt_frame.pack(fill=tk.X, pady=5)

        ttk.Button(config_mgmt_frame, text="💾 保存配置", command=self.save_config).grid(row=0, column=0, padx=5)
        ttk.Button(config_mgmt_frame, text="📂 加载配置", command=self.load_config).grid(row=0, column=1, padx=5)
        ttk.Button(config_mgmt_frame, text="🔄 重置为默认", command=self.reset_config).grid(row=0, column=2, padx=5)

        # 训练进度显示
        progress_frame = ttk.LabelFrame(parent, text="训练进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=5)
        
        # 进度条
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # 进度文本
        self.progress_text_var = tk.StringVar(value="等待开始训练...")
        ttk.Label(progress_frame, textvariable=self.progress_text_var, font=("Arial", 9)).pack(pady=5)
        
        # 详细进度信息
        self.progress_detail_var = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.progress_detail_var, font=("Arial", 8), foreground="gray").pack(pady=2)

        # 控制按钮
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=10)

        ttk.Button(control_frame, text="🚀 开始训练", command=self.start_training,
                  style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🛑 停止训练", command=self.stop_training).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="⏸️ 暂停训练", command=self.pause_training).pack(side=tk.LEFT, padx=5)

    def create_monitor_tab(self, parent):
        """创建训练监控标签页"""
        # 核心指标
        metrics_frame = ttk.LabelFrame(parent, text="核心指标", padding="10")
        metrics_frame.pack(fill=tk.X, pady=5)

        self.metrics_vars = {}
        metrics = [
            ("训练轮次", "epoch"),
            ("动作准确率", "action_acc"),
            ("策略准确率", "strategy_acc"),
            ("策略理解率", "strategy_understanding"),
            ("策略原因准确率", "reason_acc"),
            ("胜率导向损失", "win_rate_loss"),
            ("策略一致性", "consistency"),
            ("预测阈值", "threshold"),
            ("概率校准", "calibration")
        ]

        for i, (label, key) in enumerate(metrics):
            row = i // 3
            col = (i % 3) * 2
            ttk.Label(metrics_frame, text=f"{label}:").grid(row=row, column=col, sticky=tk.W, padx=5, pady=2)
            self.metrics_vars[key] = tk.StringVar(value="--")
            ttk.Label(metrics_frame, textvariable=self.metrics_vars[key], width=15).grid(row=row, column=col+1, sticky=tk.W, padx=5, pady=2)

        # 训练日志
        log_frame = ttk.LabelFrame(parent, text="训练日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=25, width=100, wrap=tk.WORD,
            font=("Consolas", 9), bg="#f8f8f8"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log("🎯 阶段6游戏导向训练工具（增强版）已启动")
        self.log(f"📊 PyTorch版本: {torch.__version__}")
        
        # 显示设备信息
        device_info = get_device_info()
        if device_info['cuda_available']:
            self.log(f"🖥️ 检测到 {device_info['device_count']} 个GPU设备:")
            for dev in device_info['devices']:
                if 'error' in dev:
                    self.log(f"   GPU {dev['id']}: 无法获取信息 ({dev['error']})")
                else:
                    status = "✓ 兼容" if dev['compatible'] else "✗ 不兼容（太旧）"
                    self.log(f"   GPU {dev['id']}: {dev['name']} (Capability {dev['capability']}, {dev['memory_gb']:.1f}GB) [{status}]")
            
            # 选择兼容的设备
            device, gpu_id = select_compatible_device(force_cpu=False)
            if gpu_id is not None:
                self.log(f"✓ 已选择GPU {gpu_id}: {torch.cuda.get_device_name(0)}")
            else:
                self.log("⚠ 未找到兼容的GPU，将使用CPU训练")
        else:
            self.log("🖥️ CUDA不可用，将使用CPU训练")

    def create_eval_tab(self, parent):
        """创建训练评估标签页"""
        # 评估配置
        eval_config_frame = ttk.LabelFrame(parent, text="评估配置", padding="10")
        eval_config_frame.pack(fill=tk.X, pady=5)

        ttk.Label(eval_config_frame, text="模型路径:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.eval_model_path_var = tk.StringVar(value="models/bc_model_stage6_enhanced.pth")
        ttk.Entry(eval_config_frame, textvariable=self.eval_model_path_var, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(eval_config_frame, text="浏览", command=self.browse_eval_model_path).grid(row=0, column=2, padx=5)
        ttk.Button(eval_config_frame, text="🔍 自动检测最新", command=self.auto_detect_latest_model).grid(row=0, column=3, padx=5)
        ttk.Button(eval_config_frame, text="📊 开始评估", command=self.evaluate_model).grid(row=0, column=4, padx=5)
        eval_config_frame.columnconfigure(1, weight=1)
        
        # 模型输出分布分析
        analysis_frame = ttk.LabelFrame(parent, text="模型输出分布分析", padding="10")
        analysis_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(analysis_frame, text="分析轮数:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.analysis_rounds_var = tk.StringVar(value="10")
        ttk.Entry(analysis_frame, textvariable=self.analysis_rounds_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(analysis_frame, text="🔍 分析输出分布", command=self.analyze_model_outputs).grid(row=0, column=2, padx=5)
        ttk.Label(analysis_frame, text="（用于诊断胜率为0的轮次问题）", font=("", 8)).grid(row=0, column=3, sticky=tk.W, padx=5)

        # 评估结果
        eval_result_frame = ttk.LabelFrame(parent, text="评估结果", padding="10")
        eval_result_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.eval_text = scrolledtext.ScrolledText(
            eval_result_frame, height=30, width=100, wrap=tk.WORD,
            font=("Consolas", 9), bg="#f8f8f8"
        )
        self.eval_text.pack(fill=tk.BOTH, expand=True)
        self.eval_text.insert(tk.END, "等待评估开始...\n")

    # ========== 数据管理方法 ==========

    def browse_data_dir(self):
        """浏览数据目录"""
        path = filedialog.askdirectory(title="选择训练数据目录")
        if path:
            self.data_dir_var.set(path)

    def load_and_analyze_data(self):
        """加载并分析数据"""
        data_dir = self.data_dir_var.get()
        if not data_dir or not os.path.exists(data_dir):
            messagebox.showerror("错误", "请选择有效的训练数据目录")
            return

        self.log(f"📊 开始分析数据目录: {data_dir}")
        self.status_var.set("🔄 正在分析数据...")
        
        # 重置进度条
        self.progress_bar['value'] = 0
        self.progress_text_var.set("正在分析数据...")
        self.progress_detail_var.set("")

        def analyze_thread():
            try:
                # 统计文件
                json_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
                total_files = len(json_files)
                
                # 更新进度：统计文件完成
                self.root.after(0, lambda: self.update_progress(10, f"已找到 {total_files} 个文件，正在加载...", ""))
                
                # 分析数据
                parser = ReplayParser(data_dir)
                
                # 更新进度：开始加载replay
                self.root.after(0, lambda: self.update_progress(30, "正在加载replay文件...", f"文件数: {total_files}"))
                
                replays = parser.load_replays()
                
                # 更新进度：开始提取数据
                self.root.after(0, lambda: self.update_progress(60, "正在提取训练数据...", f"已加载 {len(replays)} 个replay"))
                
                dataset = parser.extract_training_data(replays)
                
                # 统计信息
                stats = {
                    'total_files': total_files,
                    'valid_files': len(replays),
                    'total_samples': len(dataset),
                    'avg_samples_per_file': len(dataset) / len(replays) if replays else 0
                }
                
                # 更新UI
                self.root.after(0, self.update_data_stats, stats)
                self.root.after(0, lambda: self.update_progress(100, "数据分析完成", f"{stats['total_files']} 个文件, {stats['total_samples']} 个样本"))
                self.log(f"✅ 数据分析完成: {stats['total_files']} 个文件, {stats['total_samples']} 个样本")
                self.status_var.set("✅ 数据分析完成")
                
            except Exception as e:
                self.log(f"❌ 数据分析失败: {e}", "ERROR")
                self.status_var.set("❌ 数据分析失败")

        threading.Thread(target=analyze_thread, daemon=True).start()

    def update_data_stats(self, stats):
        """更新数据统计显示"""
        self.stats_text.delete(1.0, tk.END)
        stats_text = f"""数据统计信息
{'=' * 60}

📁 文件统计:
  总文件数: {stats['total_files']}
  有效文件数: {stats['valid_files']}
  无效文件数: {stats['total_files'] - stats['valid_files']}

📊 样本统计:
  总样本数: {stats['total_samples']}
  平均每文件样本数: {stats['avg_samples_per_file']:.2f}

💡 提示: 点击"检查并转换1312格式"按钮可以自动转换1312格式的数据
"""
        self.stats_text.insert(tk.END, stats_text)

    def convert_1312_data(self):
        """转换1312格式数据"""
        if Replay1312Converter is None:
            messagebox.showwarning("警告", "1312转换器不可用")
            return

        data_dir = self.data_dir_var.get()
        if not data_dir or not os.path.exists(data_dir):
            messagebox.showerror("错误", "请选择有效的训练数据目录")
            return

        self.log("🔍 检查1312格式数据...")
        self.status_var.set("🔄 正在转换数据...")

        def convert_thread():
            try:
                converter = Replay1312Converter()
                json_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
                converted_count = 0
                
                for json_file in json_files:
                    file_path = os.path.join(data_dir, json_file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        needs_conversion = False
                        if 'game_info' not in data or 'all_players_hands' not in data:
                            if 'player_id' in data and 'initial_hand' in data and 'actions' in data:
                                needs_conversion = True
                        
                        if needs_conversion:
                            self.log(f"🔄 转换1312格式文件: {json_file}")
                            converter.convert_file(file_path, file_path)
                            converted_count += 1
                    except Exception as e:
                        self.log(f"⚠️ 检查文件失败 {json_file}: {e}", "WARNING")
                
                self.root.after(0, lambda: self.convert_status_var.set(f"已转换 {converted_count} 个文件"))
                if converted_count > 0:
                    self.log(f"✅ 已转换 {converted_count} 个1312格式文件")
                    self.status_var.set(f"✅ 已转换 {converted_count} 个文件")
                else:
                    self.log("ℹ️ 未发现需要转换的1312格式文件")
                    self.status_var.set("ℹ️ 未发现需要转换的文件")
                    
            except Exception as e:
                self.log(f"❌ 转换失败: {e}", "ERROR")
                self.status_var.set("❌ 转换失败")

        threading.Thread(target=convert_thread, daemon=True).start()

    def validate_data_quality(self):
        """验证数据质量"""
        data_dir = self.data_dir_var.get()
        if not data_dir or not os.path.exists(data_dir):
            messagebox.showerror("错误", "请选择有效的训练数据目录")
            return

        self.log("🔍 开始验证数据质量...")
        self.status_var.set("🔄 正在验证数据质量...")

        def validate_thread():
            try:
                parser = ReplayParser(data_dir)
                replays = parser.load_replays()
                
                issues = []
                valid_count = 0
                
                for replay in replays:
                    # 检查必要字段
                    if 'player_id' not in replay:
                        issues.append("缺少player_id字段")
                    if 'initial_hand' not in replay:
                        issues.append("缺少initial_hand字段")
                    elif len(replay['initial_hand']) != 26:
                        issues.append(f"手牌数量不正确: {len(replay['initial_hand'])} (应为26)")
                    if 'actions' not in replay:
                        issues.append("缺少actions字段")
                    else:
                        valid_count += 1
                
                result_text = f"""数据质量验证结果
{'=' * 60}

✅ 有效文件数: {valid_count}
❌ 问题文件数: {len(replays) - valid_count}

"""
                if issues:
                    result_text += "发现的问题:\n"
                    for issue in set(issues):
                        result_text += f"  • {issue}\n"
                else:
                    result_text += "✅ 所有文件格式正确！\n"
                
                self.root.after(0, lambda: self.stats_text.insert(tk.END, "\n" + result_text))
                self.log(f"✅ 数据质量验证完成: {valid_count} 个有效文件")
                self.status_var.set("✅ 数据质量验证完成")
                
            except Exception as e:
                self.log(f"❌ 验证失败: {e}", "ERROR")
                self.status_var.set("❌ 验证失败")

        threading.Thread(target=validate_thread, daemon=True).start()

    # ========== 配置管理方法 ==========

    def save_config(self):
        """保存训练配置"""
        config_path = filedialog.asksaveasfilename(
            title="保存训练配置",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not config_path:
            return

        config = {
            'data_dir': self.data_dir_var.get(),
            'epochs': self.epochs_var.get(),
            'batch_size': self.batch_size_var.get(),
            'lr': self.lr_var.get(),
            'max_samples': self.max_samples_var.get(),
            'model_path': self.model_path_var.get(),
            'enable_reason_learning': self.enable_reason_learning_var.get(),
            'enable_win_rate_loss': self.enable_win_rate_loss_var.get(),
            'enable_dynamic_threshold': self.enable_dynamic_threshold_var.get(),
            'auto_evaluate': self.auto_evaluate_var.get(),
            'save_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self.log(f"✅ 配置已保存: {config_path}")
            messagebox.showinfo("成功", f"配置已保存到:\n{config_path}")
        except Exception as e:
            self.log(f"❌ 保存配置失败: {e}", "ERROR")
            messagebox.showerror("错误", f"保存配置失败:\n{e}")

    def load_config(self):
        """加载训练配置"""
        config_path = filedialog.askopenfilename(
            title="加载训练配置",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not config_path:
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.data_dir_var.set(config.get('data_dir', 'game_records'))
            self.epochs_var.set(config.get('epochs', '80'))
            self.batch_size_var.set(config.get('batch_size', '64'))
            self.lr_var.set(config.get('lr', '0.0002'))
            self.max_samples_var.set(config.get('max_samples', '15000'))
            self.model_path_var.set(config.get('model_path', 'models/bc_model_stage6_enhanced.pth'))
            self.enable_reason_learning_var.set(config.get('enable_reason_learning', True))
            self.enable_win_rate_loss_var.set(config.get('enable_win_rate_loss', True))
            self.enable_dynamic_threshold_var.set(config.get('enable_dynamic_threshold', True))
            self.auto_evaluate_var.set(config.get('auto_evaluate', True))
            
            self.log(f"✅ 配置已加载: {config_path}")
            messagebox.showinfo("成功", f"配置已从以下文件加载:\n{config_path}")
        except Exception as e:
            self.log(f"❌ 加载配置失败: {e}", "ERROR")
            messagebox.showerror("错误", f"加载配置失败:\n{e}")

    def reset_config(self):
        """重置为默认配置"""
        if messagebox.askyesno("确认", "确定要重置为默认配置吗？"):
            self.data_dir_var.set("game_records")
            self.epochs_var.set("80")
            self.batch_size_var.set("64")
            self.lr_var.set("0.0002")
            self.max_samples_var.set("15000")
            self.model_path_var.set("models/bc_model_stage6_enhanced.pth")
            self.enable_reason_learning_var.set(True)
            self.enable_win_rate_loss_var.set(True)
            self.enable_dynamic_threshold_var.set(True)
            self.auto_evaluate_var.set(True)
            self.log("🔄 配置已重置为默认值")

    def browse_model_path(self):
        """浏览模型保存路径"""
        path = filedialog.asksaveasfilename(
            title="保存阶段6模型",
            defaultextension=".pth",
            filetypes=[("PyTorch models", "*.pth"), ("All files", "*.*")]
        )
        if path:
            self.model_path_var.set(path)

    def browse_eval_model_path(self):
        """浏览评估模型路径"""
        path = filedialog.askopenfilename(
            title="选择评估模型",
            filetypes=[("PyTorch models", "*.pth"), ("All files", "*.*")]
        )
        if path:
            self.eval_model_path_var.set(path)
    
    def auto_detect_latest_model(self):
        """自动检测最新的模型文件"""
        import glob
        import os
        
        model_dir = "models"
        if not os.path.exists(model_dir):
            messagebox.showwarning("警告", "models目录不存在")
            return
        
        # 查找所有stage6相关的模型文件
        patterns = [
            "bc_model_stage6_stage2_*.pth",  # 两阶段训练的最终模型
            "bc_model_stage6_enhanced*.pth",  # 增强版模型
            "bc_model_stage6*.pth",  # 其他阶段6模型
        ]
        
        latest_model = None
        latest_time = 0
        
        for pattern in patterns:
            files = glob.glob(os.path.join(model_dir, pattern))
            for file in files:
                mtime = os.path.getmtime(file)
                if mtime > latest_time:
                    latest_time = mtime
                    latest_model = file
        
        if latest_model:
            self.eval_model_path_var.set(latest_model)
            self.log(f"✅ 已自动检测到最新模型: {latest_model}")
            messagebox.showinfo("成功", f"已自动选择最新模型:\n{os.path.basename(latest_model)}")
        else:
            messagebox.showwarning("警告", "未找到阶段6模型文件")
            self.log("⚠️ 未找到阶段6模型文件", "WARNING")

    # ========== 训练方法 ==========

    def start_training(self):
        """开始训练"""
        if self.training_active:
            messagebox.showwarning("警告", "训练正在进行中")
            return

        data_dir = self.data_dir_var.get()
        model_path = self.model_path_var.get()

        if not data_dir or not os.path.exists(data_dir):
            messagebox.showerror("错误", "请选择有效的训练数据目录")
            return

        json_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
        if not json_files:
            messagebox.showerror("错误", f"训练目录中没有找到JSON数据文件: {data_dir}")
            return

        self.training_active = True
        
        # 重置进度条
        self.progress_bar['maximum'] = 100
        self.progress_bar['value'] = 0
        self.progress_text_var.set("准备开始训练...")
        self.progress_detail_var.set("")
        self.current_epoch = 0
        self.total_epochs = int(self.epochs_var.get()) if self.epochs_var.get().isdigit() else 80
        
        self.log("🚀 开始阶段6游戏导向训练...")
        self.log(f"📁 训练数据: {data_dir}")
        self.log(f"💾 模型保存: {model_path}")
        self.log(f"🎯 启用策略原因学习: {self.enable_reason_learning_var.get()}")
        self.log(f"🎯 启用胜率导向损失: {self.enable_win_rate_loss_var.get()}")
        self.log(f"🎯 启用动态阈值调整: {self.enable_dynamic_threshold_var.get()}")

        # 重置监控数据
        for key in self.training_metrics:
            self.training_metrics[key].clear()

        def training_thread():
            try:
                # 重置进度
                self.root.after(0, lambda: self.update_progress(0, "正在初始化训练...", ""))
                self.root.after(0, lambda: self.status_var.set("🔄 正在初始化训练..."))
                self.root.after(0, lambda: self.log("📦 正在加载训练模块..."))
                
                import io
                from contextlib import redirect_stdout

                stdout_capture = io.StringIO()
                
                # 更新状态，显示正在加载数据
                self.root.after(0, lambda: self.status_var.set("🔄 正在加载训练数据（可能需要一些时间）..."))
                self.root.after(0, lambda: self.update_progress(5, "正在加载训练数据...", "这可能需要几分钟，请稍候..."))
                self.root.after(0, lambda: self.log("📂 正在从数据目录加载replay文件..."))
                self.root.after(0, lambda: self.log(f"📁 数据目录: {data_dir}"))

                with redirect_stdout(stdout_capture):
                    # 添加进度提示
                    print("[INFO] 🚀 开始阶段6游戏导向训练...")
                    print(f"[INFO] 📁 训练数据目录: {data_dir}")
                    print(f"[INFO] 💾 模型保存路径: {model_path}")
                    print(f"[INFO] 🎯 训练轮次: {self.epochs_var.get()}")
                    print(f"[INFO] 📊 批次大小: {self.batch_size_var.get()}")
                    print(f"[INFO] 🎓 学习率: {self.lr_var.get()}")
                    print(f"[INFO] 📈 最大样本数: {self.max_samples_var.get()}")
                    print("[INFO] ⏳ 正在加载数据，请稍候...")
                    print("[INFO] 💡 数据加载包括：ReplayParser初始化 + 文件加载 + 训练数据提取")
                    print("[INFO] 💡 预计需要5-15秒，取决于数据量（4000+文件约需6秒）")
                    print("[INFO] 💡 如果长时间无响应，请耐心等待，不要关闭窗口")
                    
                    # 阶段6优化版：两阶段训练
                    if self.enable_two_stage_var.get():
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        
                        # 第一阶段：冻结主干
                        stage1_model_path = model_path.replace('.pth', f'_stage1_{timestamp}.pth')
                        self.root.after(0, lambda: self.log("="*60))
                        self.root.after(0, lambda: self.log("🔒 第一阶段：冻结主干，训练决策头"))
                        self.root.after(0, lambda: self.log("="*60))
                        
                        train_bc(
                            data_dir=data_dir,
                            epochs=int(self.stage1_epochs_var.get()),
                            batch_size=32,  # 第一阶段：较小批次
                            lr=0.0002,  # 第一阶段：决策头学习率
                            model_path=stage1_model_path,
                            max_samples=int(self.max_samples_var.get()),
                            enable_strategy_head=True,
                            action_loss_weight=1.5,
                            strategy_loss_weight=0.1,
                            use_improved_model=False,
                            enable_strategy_pattern=True,
                            strategy_pattern_weight=0.05,
                            enable_opponent_modeling=True,
                            opponent_model_weight=0.05,
                            enable_dynamic_strategy=True,
                            dynamic_strategy_weight=0.05,
                            freeze_backbone=True,  # 阶段6优化版：冻结主干
                        )
                        
                        self.root.after(0, lambda: self.log(f"✅ 第一阶段完成，模型: {stage1_model_path}"))
                        
                        # 轨迹收集（简化版，实际应该从游戏记录中收集）
                        self.root.after(0, lambda: self.log("📊 轨迹收集阶段（简化版）..."))
                        trajectory_path = None  # 暂时不收集轨迹
                        
                        # 第二阶段：全量微调
                        stage2_model_path = model_path.replace('.pth', f'_stage2_{timestamp}.pth')
                        self.root.after(0, lambda: self.log("="*60))
                        self.root.after(0, lambda: self.log("🔄 第二阶段：全量微调"))
                        self.root.after(0, lambda: self.log("="*60))
                        
                        train_bc(
                            data_dir=data_dir,
                            epochs=int(self.stage2_epochs_var.get()),
                            batch_size=int(self.batch_size_var.get()),
                            lr=0.0001,  # 第二阶段：全量微调学习率（更低）
                            model_path=stage2_model_path,
                            max_samples=int(self.max_samples_var.get()) + 4000,  # 第二阶段：更多样本
                            enable_strategy_head=True,
                            action_loss_weight=1.5,
                            strategy_loss_weight=0.1,
                            use_improved_model=False,
                            enable_strategy_pattern=True,
                            strategy_pattern_weight=0.05,
                            enable_opponent_modeling=True,
                            opponent_model_weight=0.05,
                            enable_dynamic_strategy=True,
                            dynamic_strategy_weight=0.05,
                            freeze_backbone=False,  # 第二阶段：解冻所有层
                            load_pretrained_model=stage1_model_path,  # 加载第一阶段模型
                            trajectory_data=trajectory_path,  # 轨迹数据（如果有）
                        )
                        
                        self.root.after(0, lambda: self.log(f"✅ 第二阶段完成，最终模型: {stage2_model_path}"))
                        
                        # 复制第二阶段模型到最终路径
                        import shutil
                        if os.path.exists(stage2_model_path):
                            shutil.copy(stage2_model_path, model_path)
                            self.root.after(0, lambda: self.log(f"✅ 最终模型已保存到: {model_path}"))
                            # 阶段6优化版：自动更新评估模型路径
                            self.root.after(0, lambda: self.eval_model_path_var.set(model_path))
                            self.root.after(0, lambda: self.log(f"📊 评估模型路径已自动更新为: {model_path}"))
                    else:
                        # 单阶段训练（原方式）
                        train_bc(
                            data_dir=data_dir,
                            epochs=int(self.epochs_var.get()),
                            batch_size=int(self.batch_size_var.get()),
                            lr=float(self.lr_var.get()),
                            model_path=model_path,
                            max_samples=int(self.max_samples_var.get()),
                            enable_strategy_head=True,
                            action_loss_weight=1.0,
                            strategy_loss_weight=0.3,
                            use_improved_model=True,
                            attention_heads=8,
                            enable_strategy_pattern=True,
                            strategy_pattern_weight=0.1,
                            enable_opponent_modeling=True,
                            opponent_model_weight=0.1,
                            enable_dynamic_strategy=True,
                            dynamic_strategy_weight=0.1
                        )

                # 实时处理输出（逐行处理，避免一次性处理大量输出导致卡顿）
                training_output = stdout_capture.getvalue()
                lines = training_output.split('\n')
                for i, line in enumerate(lines):
                    if line.strip():
                        # 使用after方法确保GUI更新在主线程
                        self.root.after(0, lambda l=line: self.parse_training_output(l))
                        # 每100行更新一次GUI，避免过于频繁
                        if i % 100 == 0:
                            self.root.update_idletasks()

                # 训练完成
                self.root.after(0, lambda: self.update_progress(100, "训练完成！", ""))
                self.status_var.set("✅ 阶段6训练完成")
                self.training_active = False
                
                # 阶段6优化版：如果使用单阶段训练，也自动更新评估模型路径
                if not self.enable_two_stage_var.get():
                    self.root.after(0, lambda: self.eval_model_path_var.set(model_path))
                    self.root.after(0, lambda: self.log(f"📊 评估模型路径已自动更新为: {model_path}"))

                if self.auto_evaluate_var.get():
                    self.log("📊 开始游戏导向评估...")
                    self.evaluate_model()

            except Exception as e:
                self.root.after(0, lambda: self.update_progress(0, "训练失败", str(e)))
                self.log(f"❌ 训练失败: {str(e)}", "ERROR")
                self.status_var.set("❌ 训练失败")
                self.training_active = False
                import traceback
                traceback.print_exc()

        # 确保GUI界面更新
        self.root.update()
        
        self.training_thread = threading.Thread(target=training_thread, daemon=True)
        self.training_thread.start()
        
        # 添加提示信息
        self.log("⏳ 训练线程已启动，正在后台初始化...")
        self.log("💡 提示：如果长时间无响应，可能是数据加载中（4000+文件需要时间）")

    def stop_training(self):
        """停止训练"""
        if not self.training_active:
            messagebox.showinfo("提示", "当前没有正在进行的训练")
            return
        
        if messagebox.askyesno("确认", "确定要停止训练吗？"):
            self.log("🛑 训练停止请求已发送")
            self.status_var.set("🛑 正在停止训练...")
            self.training_active = False

    def pause_training(self):
        """暂停训练"""
        messagebox.showinfo("提示", "暂停功能开发中")

    def update_progress(self, value, text="", detail=""):
        """更新进度条"""
        self.progress_bar['value'] = value
        self.progress_text_var.set(text)
        if detail:
            self.progress_detail_var.set(detail)
        else:
            self.progress_detail_var.set("")
        self.root.update_idletasks()
    
    def parse_training_output(self, output_line):
        """解析训练输出"""
        try:
            import re
            
            # 解析数据加载进度
            if "正在初始化ReplayParser" in output_line:
                self.root.after(0, lambda: self.update_progress(2, "正在初始化数据解析器...", ""))
            
            if "正在加载replay文件" in output_line or "正在加载数据" in output_line:
                self.root.after(0, lambda: self.update_progress(5, "正在加载训练数据...", "这可能需要几分钟，请稍候..."))
            
            if "已加载" in output_line and "个replay文件" in output_line:
                # 提取replay数量
                match = re.search(r'已加载 (\d+) 个replay文件', output_line)
                if match:
                    count = match.group(1)
                    self.root.after(0, lambda c=count: self.update_progress(15, f"已加载 {c} 个replay文件", "正在提取训练数据..."))
            
            if "正在提取训练数据" in output_line:
                self.root.after(0, lambda: self.update_progress(20, "正在提取训练数据...", "处理中..."))
            
            if "已提取" in output_line and "个训练样本" in output_line:
                # 提取样本数量
                match = re.search(r'已提取 (\d+) 个训练样本', output_line)
                if match:
                    count = match.group(1)
                    self.root.after(0, lambda c=count: self.update_progress(25, f"已提取 {c} 个训练样本", "正在初始化模型..."))
            
            if "Using device:" in output_line or "Model:" in output_line:
                self.root.after(0, lambda: self.update_progress(28, "模型初始化完成", "准备开始训练..."))
            
            # 解析epoch进度 - 匹配多种格式
            epoch_match = None
            # 格式1: "Epoch X/Y"
            epoch_match = re.search(r'Epoch\s+(\d+)\s*/\s*(\d+)', output_line)
            # 格式2: "Epoch X of Y"
            if not epoch_match:
                epoch_match = re.search(r'Epoch\s+(\d+)\s+of\s+(\d+)', output_line)
            # 格式3: "Epoch: X/Y"
            if not epoch_match:
                epoch_match = re.search(r'Epoch:\s*(\d+)\s*/\s*(\d+)', output_line)
            
            if epoch_match:
                current = int(epoch_match.group(1))
                total = int(epoch_match.group(2))
                self.current_epoch = current
                self.total_epochs = total
                # 计算训练进度：数据加载和初始化占30%，训练占70%
                training_progress = 30 + (current / total) * 70
                self.root.after(0, lambda c=current, t=total, p=training_progress: 
                               self.update_progress(p, f"训练中: Epoch {c}/{t}", f"进度: {c}/{t} ({p:.1f}%)"))
                
                # 更新指标
                if current not in self.training_metrics['epochs']:
                    self.training_metrics['epochs'].append(current)
                    self.metrics_vars['epoch'].set(str(current))

            if "Action Accuracy - Exact:" in output_line:
                if "Card:" in output_line:
                    card_acc = float(output_line.split("Card:")[1].split("%")[0].strip())
                    self.training_metrics['action_accuracy'].append(card_acc)
                    self.metrics_vars['action_acc'].set(f"{card_acc:.2f}%")

            if "Strategy Accuracy - Overall:" in output_line:
                strategy_acc = float(output_line.split("Overall:")[1].split("%")[0].strip())
                self.training_metrics['strategy_accuracy'].append(strategy_acc)
                self.metrics_vars['strategy_acc'].set(f"{strategy_acc:.2f}%")

            if "Understanding Rate:" in output_line:
                understanding = float(output_line.split("Understanding Rate:")[1].split("%")[0].strip())
                self.training_metrics['strategy_understanding'].append(understanding)
                self.metrics_vars['strategy_understanding'].set(f"{understanding:.2f}%")

            if "Win Rate Loss:" in output_line:
                win_rate_loss = float(output_line.split("Win Rate Loss:")[1].strip())
                self.training_metrics['win_rate_loss'].append(win_rate_loss)
                self.metrics_vars['win_rate_loss'].set(f"{win_rate_loss:.4f}")
            
            # 如果检测到训练循环开始但没有epoch信息，显示大概进度
            if "Training Loop" in output_line or "开始训练" in output_line:
                if self.current_epoch == 0:
                    self.root.after(0, lambda: self.update_progress(30, "训练循环已开始", "等待epoch信息..."))

            self.log(output_line)

        except (ValueError, IndexError) as e:
            pass

    # ========== 评估方法 ==========

    def evaluate_model(self):
        """评估模型"""
        model_path = self.eval_model_path_var.get()
        data_dir = self.data_dir_var.get()

        if not os.path.exists(model_path):
            messagebox.showwarning("警告", f"模型文件不存在: {model_path}")
            return

        self.log("📊 开始阶段6游戏导向评估...")
        self.eval_text.delete(1.0, tk.END)
        self.eval_text.insert(tk.END, "正在评估...\n")
        self.status_var.set("🔄 正在评估模型...")

        def evaluate_thread():
            try:
                import io
                from contextlib import redirect_stdout
                
                # 加载游戏记录
                parser = ReplayParser(data_dir)
                game_records = parser.load_replays()
                
                if not game_records:
                    self.root.after(0, lambda: self.eval_text.insert(tk.END, "❌ 未找到游戏记录数据\n"))
                    self.log("❌ 未找到游戏记录数据", "ERROR")
                    self.status_var.set("❌ 评估失败：无数据")
                    return
                
                self.log(f"📊 已加载 {len(game_records)} 条游戏记录")
                
                # 捕获评估输出
                stdout_capture = io.StringIO()
                
                with redirect_stdout(stdout_capture):
                    validator = GameOrientedValidator(model_path=model_path)
                    results = validator.comprehensive_validation(game_records, player_id=0)
                
                # 获取评估输出
                eval_output = stdout_capture.getvalue()
                
                # 构建结果文本
                eval_result = results.get('evaluation', {})
                result_text = f"""评估结果
{'=' * 60}

🎯 胜率: {eval_result.get('win_rate', 0):.2%} (95% CI: {eval_result.get('win_rate_ci', (0, 0))[0]:.2%} - {eval_result.get('win_rate_ci', (0, 0))[1]:.2%})
📊 策略适应性: {eval_result.get('strategy_adaptability', 0):.2%}
🎲 决策质量: {eval_result.get('decision_quality', 0):.2%}
📈 预测准确性: {eval_result.get('prediction_accuracy', 0):.2%}
⭐ 综合评估分数: {eval_result.get('total_score', 0):.2%}

"""
                
                # 添加稳定性测试结果
                stability = results.get('stability', {})
                if stability.get('is_stable') is not None:
                    result_text += f"\n稳定性测试: {'✅ 通过' if stability.get('is_stable') else '❌ 未通过'}\n"
                
                # 添加适应性测试结果
                adaptability = results.get('adaptability', {})
                if adaptability.get('is_adaptive') is not None:
                    result_text += f"适应性测试: {'✅ 通过' if adaptability.get('is_adaptive') else '❌ 未通过'}\n"
                
                # 添加综合结论
                summary = results.get('summary', {})
                if summary:
                    result_text += f"\n综合结论:\n"
                    result_text += f"  胜率提升: {'✅ 是' if summary.get('is_improved') else '❌ 否'}\n"
                    result_text += f"  稳定性: {'✅ 良好' if summary.get('is_stable') else '❌ 需改进'}\n"
                    result_text += f"  适应性: {'✅ 良好' if summary.get('is_adaptive') else '❌ 需改进'}\n"
                    result_text += f"  总体评估: {'✅ 通过' if summary.get('overall_pass') else '❌ 未通过'}\n"
                
                # 添加详细输出
                result_text += f"\n详细输出:\n{'-' * 60}\n{eval_output}\n"

                # 保存评估结果到JSON文件
                try:
                    os.makedirs("training_logs", exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    log_filename = f"training_logs/stage6_evaluation_{timestamp}.json"
                    
                    # 准备保存的数据（转换为可序列化的格式）
                    save_data = {
                        'timestamp': timestamp,
                        'model_path': model_path,
                        'data_dir': data_dir,
                        'evaluation': {
                            'win_rate': float(eval_result.get('win_rate', 0)),
                            'win_rate_ci': [float(eval_result.get('win_rate_ci', (0, 0))[0]), 
                                          float(eval_result.get('win_rate_ci', (0, 0))[1])],
                            'strategy_adaptability': float(eval_result.get('strategy_adaptability', 0)),
                            'decision_quality': float(eval_result.get('decision_quality', 0)),
                            'prediction_accuracy': float(eval_result.get('prediction_accuracy', 0)),
                            'total_score': float(eval_result.get('total_score', 0))
                        },
                        'stability': {
                            'is_stable': bool(stability.get('is_stable', False)),
                            'statistics': {
                                'mean_win_rate': float(stability.get('statistics', {}).get('mean_win_rate', 0)),
                                'std_win_rate': float(stability.get('statistics', {}).get('std_win_rate', 0)),
                                'cv_win_rate': float(stability.get('statistics', {}).get('cv_win_rate', 0)),
                                'mean_total_score': float(stability.get('statistics', {}).get('mean_total_score', 0)),
                                'std_total_score': float(stability.get('statistics', {}).get('std_total_score', 0)),
                                'cv_total_score': float(stability.get('statistics', {}).get('cv_total_score', 0))
                            },
                            'round_results': [
                                {
                                    'round': int(r['round']),
                                    'win_rate': float(r['win_rate']),
                                    'total_score': float(r['total_score']),
                                    'num_games': int(r['num_games'])
                                }
                                for r in stability.get('round_results', [])
                            ]
                        },
                        'adaptability': {
                            'is_adaptive': bool(adaptability.get('is_adaptive', False)),
                            'statistics': adaptability.get('statistics', {})
                        },
                        'summary': {
                            'is_improved': bool(summary.get('is_improved', False)),
                            'is_stable': bool(summary.get('is_stable', False)),
                            'is_adaptive': bool(summary.get('is_adaptive', False)),
                            'overall_pass': bool(summary.get('overall_pass', False))
                        },
                        'raw_output': eval_output
                    }
                    
                    with open(log_filename, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, ensure_ascii=False, indent=2)
                    
                    self.log(f"💾 评估结果已保存到: {log_filename}")
                    result_text += f"\n💾 评估结果已保存到: {log_filename}\n"
                except Exception as save_error:
                    self.log(f"⚠️ 保存评估结果失败: {save_error}", "WARNING")

                self.root.after(0, lambda: self.eval_text.insert(tk.END, result_text))
                self.log("✅ 评估完成")
                self.status_var.set("✅ 评估完成")

            except Exception as e:
                self.log(f"❌ 评估失败: {str(e)}", "ERROR")
                self.status_var.set("❌ 评估失败")
                self.root.after(0, lambda: self.eval_text.insert(tk.END, f"\n评估失败: {str(e)}\n"))

        threading.Thread(target=evaluate_thread, daemon=True).start()
    
    def analyze_model_outputs(self):
        """分析模型输出分布"""
        model_path = self.eval_model_path_var.get()
        data_dir = self.data_dir_var.get()
        
        if not os.path.exists(model_path):
            messagebox.showwarning("警告", f"模型文件不存在: {model_path}")
            return
        
        try:
            num_rounds = int(self.analysis_rounds_var.get())
        except ValueError:
            messagebox.showwarning("警告", "分析轮数必须是整数")
            return
        
        self.log("🔍 开始模型输出分布分析...")
        self.eval_text.insert(tk.END, "\n" + "="*60 + "\n")
        self.eval_text.insert(tk.END, "模型输出分布分析\n")
        self.eval_text.insert(tk.END, "="*60 + "\n\n")
        self.status_var.set("🔄 正在分析模型输出分布...")
        
        def analyze_thread():
            try:
                from src.train.analyze_model_output_distribution import analyze_model_outputs
                
                # 生成输出文件路径
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"training_logs/model_output_analysis_{timestamp}.json"
                
                # 运行分析
                results = analyze_model_outputs(
                    model_path=model_path,
                    data_dir=data_dir,
                    player_id=0,
                    num_rounds=num_rounds,
                    output_path=output_path
                )
                
                # 显示结果
                result_text = f"\n分析完成！\n"
                result_text += f"输出文件: {output_path}\n\n"
                
                if results and 'round_results' in results:
                    result_text += "各轮次分析结果:\n"
                    result_text += "-" * 60 + "\n"
                    
                    for round_result in results['round_results']:
                        round_num = round_result.get('round', 0)
                        num_samples = round_result.get('num_samples', 0)
                        
                        if 'error' in round_result:
                            result_text += f"第{round_num}轮: 错误 - {round_result['error']}\n"
                        else:
                            stats = round_result.get('statistics', {})
                            anomalies = round_result.get('anomalies', {})
                            
                            result_text += f"\n第{round_num}轮 (样本数: {num_samples}):\n"
                            
                            if stats:
                                logits = stats.get('logits', {})
                                probs = stats.get('probs', {})
                                scaled_probs = stats.get('scaled_probs', {})
                                pred_counts = stats.get('predicted_card_counts', {})
                                
                                result_text += f"  Logits: 均值={logits.get('mean', 0):.4f}, 标准差={logits.get('std', 0):.4f}\n"
                                result_text += f"  Probs: 均值={probs.get('mean', 0):.4f}, 范围=[{probs.get('min', 0):.4f}, {probs.get('max', 0):.4f}]\n"
                                result_text += f"  Scaled Probs: 均值={scaled_probs.get('mean', 0):.4f}\n"
                                result_text += f"  预测卡牌数: 均值={pred_counts.get('mean', 0):.2f}, 范围=[{pred_counts.get('min', 0)}, {pred_counts.get('max', 0)}]\n"
                            
                            if anomalies:
                                zero_ratio = anomalies.get('zero_output_ratio', 0)
                                invalid_ratio = anomalies.get('invalid_output_ratio', 0)
                                
                                if zero_ratio > 0:
                                    result_text += f"  ⚠️ 零输出比例: {zero_ratio:.1%}\n"
                                if invalid_ratio > 0:
                                    result_text += f"  ⚠️ 无效输出比例: {invalid_ratio:.1%}\n"
                                
                                if zero_ratio > 0.1 or invalid_ratio > 0.5:
                                    result_text += f"  ❌ 该轮次输出异常，可能是导致胜率为0的原因！\n"
                    
                    result_text += "\n" + "="*60 + "\n"
                    result_text += f"详细结果已保存到: {output_path}\n"
                
                self.root.after(0, lambda: self.eval_text.insert(tk.END, result_text))
                self.log(f"✅ 模型输出分布分析完成，结果已保存到: {output_path}")
                self.status_var.set("✅ 分析完成")
                
            except Exception as e:
                error_msg = f"分析失败: {str(e)}"
                self.log(f"❌ {error_msg}", "ERROR")
                self.status_var.set("❌ 分析失败")
                self.root.after(0, lambda: self.eval_text.insert(tk.END, f"\n{error_msg}\n"))
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=analyze_thread, daemon=True).start()

    # ========== 工具方法 ==========

    def log(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"

        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        print(log_message.strip())

    def process_log_queue(self):
        """处理日志队列"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log(message['text'], message['level'])
        except queue.Empty:
            pass

        self.root.after(100, self.process_log_queue)


def main():
    """主函数"""
    root = tk.Tk()
    app = EnhancedStage6TrainingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

