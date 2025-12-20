#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段6-游戏导向训练GUI工具
专门用于阶段6"从预测准确转向赢得游戏"的训练监控和控制

核心功能：
1. 策略原因学习任务监控 - 实时显示26类策略原因的学习效果
2. 胜率导向损失可视化 - 显示胜率导向损失的变化趋势
3. 游戏导向评估 - 训练完成后自动进行多维度评估
4. 动态阈值调整监控 - 显示预测阈值的自适应调整
5. 概率校准效果 - 实时显示预测概率的准确性
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import json
import queue
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from datetime import datetime
import time

# 添加项目路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.train.pretrain import train_bc
from src.train.game_oriented_evaluator import GameOrientedEvaluator
from src.train.game_oriented_validation import GameOrientedValidator
import torch


class Stage6TrainingGUI:
    """阶段6游戏导向训练GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("🎯 阶段6-游戏导向训练工具")
        self.root.geometry("1400x1000")

        # 训练监控数据
        self.training_metrics = {
            'epochs': [],
            'action_accuracy': [],
            'strategy_accuracy': [],
            'strategy_understanding': [],
            'reason_accuracy': [],  # 策略原因学习准确率
            'win_rate_loss': [],    # 胜率导向损失
            'strategy_consistency': [],  # 策略一致性损失
            'prediction_threshold': [],   # 动态预测阈值
            'probability_calibration': [] # 概率校准效果
        }

        # 训练日志队列
        self.log_queue = queue.Queue()

        # 创建界面
        self.create_widgets()

        # 启动日志处理
        self.process_log_queue()

        # 初始化图表
        self.init_plots()

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

        # 1. 阶段6核心理念展示
        concept_frame = ttk.LabelFrame(main_frame, text="🎯 阶段6核心理念", padding="10")
        concept_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        concept_text = """
从"预测卡牌的AI" → "赢得游戏的AI"
• ✅ 策略原因学习：理解"为什么这样选择"
• ✅ 胜率导向损失：学习"什么有效"
• ✅ 动态阈值调整：根据局面自适应
• ✅ 概率校准：提高预测准确性
• ✅ 综合评估：多维度验证效果
        """
        ttk.Label(concept_frame, text=concept_text, justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)

        # 2. 训练配置区域
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ 阶段6训练配置", padding="10")
        config_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        config_frame.columnconfigure(1, weight=1)

        # 训练参数配置
        ttk.Label(config_frame, text="训练数据目录:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.data_dir_var = tk.StringVar(value="game_records")
        ttk.Entry(config_frame, textvariable=self.data_dir_var, width=40).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(config_frame, text="浏览", command=self.browse_data_dir).grid(row=0, column=2, padx=5)

        ttk.Label(config_frame, text="训练轮数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.epochs_var = tk.StringVar(value="100")
        ttk.Entry(config_frame, textvariable=self.epochs_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(config_frame, text="批次大小:").grid(row=1, column=2, sticky=tk.W, padx=5)
        self.batch_size_var = tk.StringVar(value="64")
        ttk.Entry(config_frame, textvariable=self.batch_size_var, width=10).grid(row=1, column=3, padx=5)

        ttk.Label(config_frame, text="学习率:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.lr_var = tk.StringVar(value="0.0002")
        ttk.Entry(config_frame, textvariable=self.lr_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5)

        ttk.Label(config_frame, text="模型保存路径:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_path_var = tk.StringVar(value="models/bc_model_stage6_gui.pth")
        ttk.Entry(config_frame, textvariable=self.model_path_var, width=40).grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(config_frame, text="浏览", command=self.browse_model_path).grid(row=3, column=2, padx=5)

        # 阶段6特色选项
        ttk.Label(config_frame, text="🎯 阶段6特色配置:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=10)

        self.enable_reason_learning_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="启用策略原因学习 (26类原因类型)",
                       variable=self.enable_reason_learning_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5)

        self.enable_win_rate_loss_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="启用胜率导向损失 (学习有效策略)",
                       variable=self.enable_win_rate_loss_var).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5)

        self.enable_dynamic_threshold_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="启用动态阈值调整 (局面自适应)",
                       variable=self.enable_dynamic_threshold_var).grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5)

        self.auto_evaluate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="训练完成后自动进行游戏导向评估",
                       variable=self.auto_evaluate_var).grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=5)

        # 控制按钮
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=9, column=0, columnspan=3, pady=10)
        ttk.Button(button_frame, text="🚀 开始阶段6训练", command=self.start_stage6_training).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="🛑 停止训练", command=self.stop_training).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="📊 评估当前模型", command=self.evaluate_current_model).grid(row=0, column=2, padx=5)

        # 3. 实时监控区域
        monitor_frame = ttk.LabelFrame(main_frame, text="📊 阶段6实时监控", padding="10")
        monitor_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        monitor_frame.columnconfigure(0, weight=1)
        monitor_frame.rowconfigure(0, weight=1)

        # 左侧：核心指标显示
        left_frame = ttk.Frame(monitor_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # 核心指标显示
        metrics_frame = ttk.LabelFrame(left_frame, text="核心指标", padding="5")
        metrics_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

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
            ttk.Label(metrics_frame, text=f"{label}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            self.metrics_vars[key] = tk.StringVar(value="--")
            ttk.Label(metrics_frame, textvariable=self.metrics_vars[key]).grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)

        # 策略原因类型监控
        reason_frame = ttk.LabelFrame(left_frame, text="策略原因学习效果", padding="5")
        reason_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        self.reason_types = [
            'bomb_urgent', 'bomb_endgame', 'bomb_counter', 'bomb_opportunity',
            'suppress_urgent', 'suppress_combo', 'suppress_block', 'suppress_general',
            'protect_teammate_urgent', 'protect_teammate', 'protect_advantage', 'protect_general',
            'control_urgent', 'control_endgame', 'control_general',
            'group_reduce_hands', 'group_reduce_singles', 'group_optimize', 'group_general',
            'follow_counter', 'follow_single', 'follow_general',
            'discard_opening', 'discard_endgame', 'discard_general',
            'unknown'
        ]

        self.reason_vars = {}
        for i, reason_type in enumerate(self.reason_types[:10]):  # 只显示前10个
            ttk.Label(reason_frame, text=f"{reason_type}:").grid(row=i, column=0, sticky=tk.W, padx=2, pady=1)
            self.reason_vars[reason_type] = tk.StringVar(value="--")
            ttk.Label(reason_frame, textvariable=self.reason_vars[reason_type]).grid(row=i, column=1, sticky=tk.W, padx=2, pady=1)

        # 右侧：图表显示区域
        right_frame = ttk.Frame(monitor_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 创建matplotlib图表
        self.figure, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.figure, master=right_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 4. 训练日志区域
        log_frame = ttk.LabelFrame(main_frame, text="📝 训练日志", padding="10")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=15, width=120, wrap=tk.WORD,
            font=("Consolas", 9), bg="#f8f8f8"
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 5. 状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.status_var = tk.StringVar(value="🎯 阶段6训练工具就绪")
        ttk.Label(status_frame, textvariable=self.status_var).grid(row=0, column=0, sticky=tk.W)

        self.progress_var = tk.StringVar(value="")
        ttk.Label(status_frame, textvariable=self.progress_var).grid(row=0, column=1, sticky=tk.E)

        # 初始化日志
        self.log("🎯 阶段6游戏导向训练工具已启动")
        self.log(f"📊 PyTorch版本: {torch.__version__}")
        self.log(f"🖥️ CUDA可用: {torch.cuda.is_available()}")

    def init_plots(self):
        """初始化图表"""
        # 清除所有子图
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()

        # 设置图表标题
        self.ax1.set_title('准确率趋势', fontsize=10)
        self.ax2.set_title('策略学习效果', fontsize=10)
        self.ax3.set_title('损失函数变化', fontsize=10)
        self.ax4.set_title('预测质量', fontsize=10)

        # 设置标签
        self.ax1.set_xlabel('Epoch', fontsize=8)
        self.ax1.set_ylabel('Accuracy (%)', fontsize=8)
        self.ax2.set_xlabel('Epoch', fontsize=8)
        self.ax2.set_ylabel('Understanding Rate (%)', fontsize=8)
        self.ax3.set_xlabel('Epoch', fontsize=8)
        self.ax3.set_ylabel('Loss', fontsize=8)
        self.ax4.set_xlabel('Epoch', fontsize=8)
        self.ax4.set_ylabel('Quality Score', fontsize=8)

        self.figure.tight_layout()
        self.canvas.draw()

    def update_plots(self):
        """更新图表显示"""
        # 清除所有子图
        for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
            ax.clear()

        epochs = self.training_metrics['epochs']

        if not epochs:
            self.init_plots()
            return

        # 图表1：准确率趋势
        if self.training_metrics['action_accuracy']:
            self.ax1.plot(epochs, self.training_metrics['action_accuracy'], 'b-', label='Action Acc', linewidth=2)
        if self.training_metrics['strategy_accuracy']:
            self.ax1.plot(epochs, self.training_metrics['strategy_accuracy'], 'r-', label='Strategy Acc', linewidth=2)
        self.ax1.legend(fontsize=8)
        self.ax1.grid(True, alpha=0.3)

        # 图表2：策略学习效果
        if self.training_metrics['strategy_understanding']:
            self.ax2.plot(epochs, self.training_metrics['strategy_understanding'], 'g-', label='Understanding', linewidth=2)
        if self.training_metrics['reason_accuracy']:
            self.ax2.plot(epochs, self.training_metrics['reason_accuracy'], 'm-', label='Reason Acc', linewidth=2)
        self.ax2.legend(fontsize=8)
        self.ax2.grid(True, alpha=0.3)

        # 图表3：损失函数变化
        if self.training_metrics['win_rate_loss']:
            self.ax3.plot(epochs, self.training_metrics['win_rate_loss'], 'r-', label='Win Rate Loss', linewidth=2)
        if self.training_metrics['strategy_consistency']:
            self.ax3.plot(epochs, self.training_metrics['strategy_consistency'], 'b-', label='Consistency Loss', linewidth=2)
        self.ax3.legend(fontsize=8)
        self.ax3.grid(True, alpha=0.3)

        # 图表4：预测质量
        if self.training_metrics['prediction_threshold']:
            self.ax4.plot(epochs, self.training_metrics['prediction_threshold'], 'c-', label='Threshold', linewidth=2)
        if self.training_metrics['probability_calibration']:
            self.ax4.plot(epochs, self.training_metrics['probability_calibration'], 'y-', label='Calibration', linewidth=2)
        self.ax4.legend(fontsize=8)
        self.ax4.grid(True, alpha=0.3)

        # 设置标题
        self.ax1.set_title('准确率趋势', fontsize=10)
        self.ax2.set_title('策略学习效果', fontsize=10)
        self.ax3.set_title('损失函数变化', fontsize=10)
        self.ax4.set_title('预测质量', fontsize=10)

        self.figure.tight_layout()
        self.canvas.draw()

    def browse_data_dir(self):
        """浏览训练数据目录"""
        path = filedialog.askdirectory(title="选择训练数据目录")
        if path:
            self.data_dir_var.set(path)

    def browse_model_path(self):
        """浏览模型保存路径"""
        path = filedialog.asksaveasfilename(
            title="保存阶段6模型",
            defaultextension=".pth",
            filetypes=[("PyTorch models", "*.pth"), ("All files", "*.*")]
        )
        if path:
            self.model_path_var.set(path)

    def log(self, message, level="INFO"):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"

        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)

        # 同时输出到控制台
        print(log_message.strip())

    def process_log_queue(self):
        """处理日志队列"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log(message['text'], message['level'])
        except queue.Empty:
            pass

        # 继续处理队列
        self.root.after(100, self.process_log_queue)

    def parse_training_output(self, output_line):
        """解析训练输出，提取阶段6指标"""
        try:
            # 解析轮次
            if "Epoch" in output_line and "/" in output_line:
                epoch_part = output_line.split("Epoch")[1].split("/")[0].strip()
                if epoch_part.isdigit():
                    epoch = int(epoch_part)
                    if epoch not in self.training_metrics['epochs']:
                        self.training_metrics['epochs'].append(epoch)

            # 解析准确率
            if "Action Accuracy - Exact:" in output_line:
                # 提取卡牌级别准确率
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

            # 解析损失值
            if "Win Rate Loss:" in output_line:
                win_rate_loss = float(output_line.split("Win Rate Loss:")[1].strip())
                self.training_metrics['win_rate_loss'].append(win_rate_loss)
                self.metrics_vars['win_rate_loss'].set(f"{win_rate_loss:.4f}")

            # 更新图表
            self.update_plots()

        except (ValueError, IndexError) as e:
            # 解析失败，跳过
            pass

    def start_stage6_training(self):
        """开始阶段6训练"""
        data_dir = self.data_dir_var.get()
        model_path = self.model_path_var.get()

        if not data_dir or not os.path.exists(data_dir):
            messagebox.showerror("错误", "请选择有效的训练数据目录")
            return

        # 检查训练数据
        json_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
        if not json_files:
            messagebox.showerror("错误", f"训练目录中没有找到JSON数据文件: {data_dir}")
            return

        self.log("🚀 开始阶段6游戏导向训练...")
        self.log(f"📁 训练数据: {data_dir}")
        self.log(f"💾 模型保存: {model_path}")
        self.log(f"🎯 启用策略原因学习: {self.enable_reason_learning_var.get()}")
        self.log(f"🎯 启用胜率导向损失: {self.enable_win_rate_loss_var.get()}")
        self.log(f"🎯 启用动态阈值调整: {self.enable_dynamic_threshold_var.get()}")

        # 重置监控数据
        for key in self.training_metrics:
            self.training_metrics[key].clear()

        # 在后台线程中运行训练
        def training_thread():
            try:
                self.status_var.set("🔄 阶段6训练进行中...")

                # 捕获训练输出
                import io
                from contextlib import redirect_stdout

                stdout_capture = io.StringIO()

                with redirect_stdout(stdout_capture):
                    # 调用训练函数
                    train_bc(
                        data_dir=data_dir,
                        epochs=int(self.epochs_var.get()),
                        batch_size=int(self.batch_size_var.get()),
                        lr=float(self.lr_var.get()),
                        model_path=model_path,
                        max_samples=15000,
                        enable_strategy_head=True,
                        action_loss_weight=1.0,
                        strategy_loss_weight=0.3,
                        use_improved_model=True,
                        attention_heads=8,
                        # 阶段6配置
                        enable_strategy_pattern=True,
                        strategy_pattern_weight=0.1,
                        enable_opponent_modeling=True,
                        opponent_model_weight=0.1,
                        enable_dynamic_strategy=True,
                        dynamic_strategy_weight=0.1
                    )

                # 处理训练输出
                training_output = stdout_capture.getvalue()
                for line in training_output.split('\n'):
                    if line.strip():
                        self.parse_training_output(line)

                self.status_var.set("✅ 阶段6训练完成")

                # 自动评估
                if self.auto_evaluate_var.get():
                    self.log("📊 开始游戏导向评估...")
                    self.evaluate_current_model()

            except Exception as e:
                self.log(f"❌ 训练失败: {str(e)}", "ERROR")
                self.status_var.set("❌ 训练失败")
                import traceback
                traceback.print_exc()

        # 启动训练线程
        training_thread = threading.Thread(target=training_thread, daemon=True)
        training_thread.start()

    def stop_training(self):
        """停止训练"""
        self.log("🛑 训练停止请求已发送")
        self.status_var.set("🛑 正在停止训练...")

    def evaluate_current_model(self):
        """评估当前模型"""
        model_path = self.model_path_var.get()
        data_dir = self.data_dir_var.get()

        if not os.path.exists(model_path):
            messagebox.showwarning("警告", f"模型文件不存在: {model_path}")
            return

        self.log("📊 开始阶段6游戏导向评估...")

        def evaluate_thread():
            try:
                validator = GameOrientedValidator(model_path, data_dir)

                # 执行综合验证
                results = validator.validate_comprehensive()

                # 显示结果
                self.log("🎯 评估结果:")
                self.log(f"  • 胜率: {results.get('win_rate', 'N/A')}")
                self.log(f"  • 策略适应性: {results.get('strategy_adaptability', 'N/A')}")
                self.log(f"  • 决策质量: {results.get('decision_quality', 'N/A')}")
                self.log(f"  • 预测准确性: {results.get('prediction_accuracy', 'N/A')}")
                self.log(f"  • 综合评估分数: {results.get('overall_score', 'N/A')}")

                if results.get('improvement_analysis'):
                    self.log("📈 改进分析:")
                    for key, value in results['improvement_analysis'].items():
                        self.log(f"  • {key}: {value}")

                self.status_var.set("✅ 评估完成")

            except Exception as e:
                self.log(f"❌ 评估失败: {str(e)}", "ERROR")
                self.status_var.set("❌ 评估失败")

        # 启动评估线程
        eval_thread = threading.Thread(target=evaluate_thread, daemon=True)
        eval_thread.start()


def main():
    """主函数"""
    root = tk.Tk()
    app = Stage6TrainingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
