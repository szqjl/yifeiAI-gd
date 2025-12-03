#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YiFei AI 掼蛋回放系统 - 整合版

功能：
1. 显示所有四个玩家的起始手牌
2. 清晰回放比赛全过程
3. 突出显示yf玩家的决策
4. 无需区分普通版和增强版
5. 支持播放、暂停、快进、慢放等控制

使用方法：
python yf_replay.py [游戏记录文件路径]
"""

import sys
import os
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

# 设置路径
sys.path.insert(0, str(Path(__file__).parent / "src"))
os.environ['PYTHONPATH'] = str(Path(__file__).parent / "src")

from communication.game_recorder import GameRecorder
from communication.server_log_parser import ServerLogParser

class YiFeiReplayGUI:
    """YiFei AI 掼蛋回放系统 - 整合版"""
    
    def __init__(self, root, game_file=None):
        """初始化GUI"""
        self.root = root
        self.root.title("YiFei AI 掼蛋回放系统 - 整合版")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 游戏数据
        self.game_records = []
        self.current_game = None
        self.current_game_data = None
        self.current_step = 0
        self.is_playing = False
        self.play_speed = 1.0  # 播放速度倍数
        
        # 游戏状态数据
        self.actions = []
        self.my_decisions = []
        self.player_id = 0
        self.total_steps = 0
        self.initial_hands = {}  # 所有玩家的初始手牌
        self.player_hands = {}  # 当前所有玩家的手牌
        self.played_cards = []
        
        # 初始化界面
        self._setup_ui()
        
        # 加载游戏记录
        self._load_game_records()
        
        # 如果指定了游戏文件，直接加载
        if game_file:
            self._load_specific_game(game_file)
    
    def _setup_ui(self):
        """设置UI布局"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 顶部工具栏
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 游戏选择
        ttk.Label(toolbar_frame, text="游戏记录:").pack(side=tk.LEFT, padx=(0, 5))
        self.game_combobox = ttk.Combobox(toolbar_frame, width=50, state="readonly")
        self.game_combobox.pack(side=tk.LEFT, padx=(0, 10))
        self.game_combobox.bind("<<ComboboxSelected>>", self._on_game_selected)
        
        # 加载按钮
        ttk.Button(toolbar_frame, text="加载文件", command=self._load_file).pack(side=tk.LEFT, padx=(0, 10))
        
        # 2. 中间播放控制区
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 播放控制按钮
        self.play_btn = ttk.Button(control_frame, text="播放", command=self._toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.prev_btn = ttk.Button(control_frame, text="上一步", command=self._prev_step)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_btn = ttk.Button(control_frame, text="下一步", command=self._next_step)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        ttk.Label(control_frame, text="进度:").pack(side=tk.LEFT, padx=(10, 5))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(control_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                     variable=self.progress_var, command=self._on_progress_change)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 步骤显示
        self.step_label = ttk.Label(control_frame, text="步骤: 0/0")
        self.step_label.pack(side=tk.LEFT, padx=(10, 5))
        
        # 速度控制
        ttk.Label(control_frame, text="速度:").pack(side=tk.LEFT, padx=(10, 5))
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(control_frame, from_=0.1, to=5.0, orient=tk.HORIZONTAL, 
                               variable=self.speed_var, command=self._on_speed_change, length=100)
        speed_scale.pack(side=tk.LEFT, padx=5)
        self.speed_label = ttk.Label(control_frame, text="1.0x")
        self.speed_label.pack(side=tk.LEFT, padx=(5, 10))
        
        # 3. 牌面展示区
        card_frame = ttk.Frame(main_frame)
        card_frame.pack(fill=tk.BOTH, expand=True)
        
        # 牌面Canvas
        self.card_canvas = tk.Canvas(card_frame, bg="#006400")
        self.card_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 4. 底部信息区
        info_frame = ttk.LabelFrame(main_frame, text="游戏信息", padding="5")
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 信息标签
        self.game_info_label = ttk.Label(info_frame, text="请选择一个游戏记录开始回放", justify=tk.LEFT)
        self.game_info_label.pack(fill=tk.X, padx=5, pady=5)
        
        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _load_game_records(self):
        """加载游戏记录列表"""
        self.status_bar.config(text="正在加载游戏记录...")
        
        # 查找所有JSON文件
        game_files = list(Path("game_records").glob("*.json"))
        # 过滤掉增强版文件，只显示原始记录
        self.game_records = [f for f in game_files if not f.name.startswith("enhanced_")]
        
        # 更新下拉列表
        game_names = [f.name for f in self.game_records]
        self.game_combobox['values'] = game_names
        
        # 默认选择第一个
        if game_names:
            self.game_combobox.current(0)
            self._on_game_selected(None)
        
        self.status_bar.config(text=f"加载完成，共找到 {len(self.game_records)} 个游戏记录")
    
    def _load_file(self):
        """加载指定的游戏文件"""
        file_path = filedialog.askopenfilename(
            title="选择游戏记录文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir="game_records"
        )
        if file_path:
            self._load_specific_game(file_path)
    
    def _load_specific_game(self, file_path):
        """加载指定的游戏文件"""
        self.current_game = Path(file_path)
        self.current_step = 0
        self.is_playing = False
        
        # 加载游戏数据
        self._load_game_data()
        
        # 更新UI
        self.play_btn.config(text="播放")
        self.step_label.config(text=f"步骤: {self.current_step}/{self.total_steps}")
        self.progress_var.set(0)
        
        # 显示游戏基本信息
        game_info = f"游戏: {self.current_game.name}\n"
        self.game_info_label.config(text=game_info)
        
        # 清空画布，准备渲染
        self.card_canvas.delete("all")
        self._draw_current_step()
        
        self.status_bar.config(text=f"已加载游戏: {self.current_game.name}")
    
    def _on_game_selected(self, event):
        """当选择游戏记录时"""
        selected_idx = self.game_combobox.current()
        if selected_idx < 0 or selected_idx >= len(self.game_records):
            return
        
        self.current_game = self.game_records[selected_idx]
        self.current_step = 0
        self.is_playing = False
        
        # 加载游戏数据
        self._load_game_data()
        
        # 更新UI
        self.play_btn.config(text="播放")
        self.step_label.config(text=f"步骤: {self.current_step}/{self.total_steps}")
        self.progress_var.set(0)
        
        # 显示游戏基本信息
        game_info = f"游戏: {self.current_game.name}\n"
        self.game_info_label.config(text=game_info)
        
        # 清空画布，准备渲染
        self.card_canvas.delete("all")
        self._draw_current_step()
        
        self.status_bar.config(text=f"已选择游戏: {self.current_game.name}")
    
    def _load_game_data(self):
        """加载游戏数据，自动整合所有可用信息"""
        self.status_bar.config(text=f"正在加载游戏数据: {self.current_game.name}")
        
        # 加载基础游戏数据
        self.current_game_data = GameRecorder.load_game(self.current_game)
        
        # 解析游戏数据
        self.actions = self.current_game_data.get('actions', [])
        self.my_decisions = self.current_game_data.get('my_decisions', [])
        self.player_id = self.current_game_data.get('player_id', 0)
        self.total_steps = len(self.actions)
        
        # 保存初始手牌（所有玩家）
        self.initial_hands = {}
        
        # 1. 从initial_hand获取当前玩家的初始手牌
        if 'initial_hand' in self.current_game_data:
            self.initial_hands[str(self.player_id)] = self.current_game_data['initial_hand'].copy()
        
        # 2. 从all_players_hands获取所有玩家的初始手牌
        if 'all_players_hands' in self.current_game_data:
            for pos, cards in self.current_game_data['all_players_hands'].items():
                pos_str = str(pos)
                # 添加类型检查，确保cards是列表类型
                if isinstance(cards, list):
                    self.initial_hands[pos_str] = cards.copy()
                else:
                    # 如果不是列表，跳过或使用空列表
                    self.initial_hands[pos_str] = []
        
        # 3. 尝试使用服务器日志补充初始手牌
        try:
            server_log_path = Path("src/communication/Testscore/服务端")
            if server_log_path.exists():
                parser = ServerLogParser()
                server_data = parser.parse_log_file(str(server_log_path))
                
                # 补充缺失的玩家手牌，但只在没有初始手牌时才使用，并且忽略不正确的初始手牌数量
                if 'initial_hands' in server_data:
                    for pos, cards in server_data['initial_hands'].items():
                        pos_str = str(pos)
                        if pos_str not in self.initial_hands or not self.initial_hands[pos_str]:
                            # 只接受合理数量的初始手牌（27张左右）
                            if isinstance(cards, list) and len(cards) > 10:  # 只接受10张以上的初始手牌
                                self.initial_hands[pos_str] = cards.copy()
        except Exception as e:
            self.status_bar.config(text=f"补充初始手牌失败: {e}")
        
        # 4. 确保所有4个玩家都有正确的初始手牌数量（27张）
        for pos in range(4):
            pos_str = str(pos)
            if pos_str not in self.initial_hands or not self.initial_hands[pos_str]:
                # 如果没有初始手牌或初始手牌数量不合理，初始化一个空列表
                self.initial_hands[pos_str] = []
            
        # 6. 计算当前所有玩家的手牌
        self.player_hands = self._calculate_current_hands()
        self.status_bar.config(text=f"游戏数据加载完成，共 {self.total_steps} 个动作，初始手牌: {len(self.initial_hands)} 个玩家")
    
    def _calculate_current_hands(self):
        """计算所有玩家的当前手牌（到当前步骤为止）"""
        # 从初始手牌开始，确保所有4个玩家都有初始手牌记录
        current_hands = {}
        
        # 初始化所有4个玩家的手牌，确保每个玩家都有合理的初始手牌
        for pos in range(4):
            pos_str = str(pos)
            if pos_str in self.initial_hands and self.initial_hands[pos_str]:
                current_hands[pos_str] = self.initial_hands[pos_str].copy()
            else:
                # 如果没有初始手牌，初始化一个空列表
                current_hands[pos_str] = []
        
        # 处理当前步骤之前的所有动作
        for i in range(min(self.current_step, self.total_steps)):
            action = self.actions[i]
            cur_pos = action.get('cur_pos', -1)
            cur_action = action.get('cur_action', [])
            
            # 确保cur_pos是有效的玩家位置
            if cur_pos < 0 or cur_pos > 3:
                continue
            
            pos_str = str(cur_pos)
            
            # 解析动作，获取打出的牌
            action_info = self._parse_action(cur_action)
            if not action_info:
                continue
                
            action_type, _, played_cards = action_info
            
            # 只处理实际出牌的动作，跳过Pass等不消耗手牌的动作
            # 标准化动作类型为大写，避免大小写问题
            action_type = action_type.upper() if action_type else ""
            if action_type != "PASS" and played_cards:
                # 从对应玩家手牌中移除打出的牌
                if pos_str in current_hands:
                    player_cards = current_hands[pos_str]
                    
                    # 移除打出的牌
                    for card in played_cards:
                        if card in player_cards:
                            player_cards.remove(card)
                    current_hands[pos_str] = player_cards
        
        # 确保每个玩家的手牌数量不会变为负数
        for pos_str in current_hands:
            if len(current_hands[pos_str]) < 0:
                current_hands[pos_str] = []
        
        return current_hands
    
    def _toggle_play(self):
        """切换播放/暂停状态"""
        if not self.current_game:
            messagebox.showwarning("警告", "请先选择一个游戏记录")
            return
        
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.config(text="暂停")
            self._play_next_step()
        else:
            self.play_btn.config(text="播放")
    
    def _play_next_step(self):
        """播放下一步"""
        if not self.is_playing:
            return
        
        # 检查是否已经到最后一步
        if self.current_step < self.total_steps:
            self.current_step += 1
            self._update_progress()
            
            # 继续播放
            self.root.after(int(1000 / self.play_speed), self._play_next_step)
        else:
            # 播放结束
            self.is_playing = False
            self.play_btn.config(text="播放")
            self.status_bar.config(text="播放结束")
    
    def _prev_step(self):
        """上一步"""
        if not self.current_game or not self.actions:
            return
        
        self.is_playing = False
        self.play_btn.config(text="播放")
        
        if self.current_step > 0:
            self.current_step -= 1
            self._update_progress()
    
    def _next_step(self):
        """下一步"""
        if not self.current_game or not self.actions:
            return
        
        self.is_playing = False
        self.play_btn.config(text="播放")
        
        if self.current_step < self.total_steps:
            self.current_step += 1
            self._update_progress()
    
    def _update_progress(self):
        """更新进度显示"""
        if self.total_steps == 0:
            return
        
        self.step_label.config(text=f"步骤: {self.current_step}/{self.total_steps}")
        self.progress_var.set((self.current_step / self.total_steps) * 100)
        
        # 计算当前所有玩家的手牌
        self.player_hands = self._calculate_current_hands()
        
        # 重新渲染当前步骤的牌面
        self._draw_current_step()
    
    def _draw_current_step(self):
        """绘制当前步骤的牌面"""
        # 清空画布
        self.card_canvas.delete("all")
        
        # 绘制背景
        self.card_canvas.create_rectangle(0, 0, self.card_canvas.winfo_width(), 
                                         self.card_canvas.winfo_height(), fill="#006400")
        
        # 绘制玩家位置
        self._draw_player_positions()
        
        # 绘制所有玩家的手牌
        for pos in range(4):
            self._draw_player_hand(pos)
        
        # 如果没有动作，显示初始状态
        if not self.actions:
            info = "没有游戏动作数据"
            self.card_canvas.create_text(self.card_canvas.winfo_width() // 2, self.card_canvas.winfo_height() // 2,
                                        text=info, fill="white", font=("Arial", 14), anchor=tk.CENTER)
            return
        
        # 绘制当前步骤信息
        if self.current_step <= self.total_steps:
            self._draw_step_info()
            
            # 绘制当前动作
            if self.current_step > 0:
                action = self.actions[self.current_step - 1]
                self._draw_current_action(action)
    
    def _draw_player_positions(self):
        """绘制玩家位置"""
        # 调整玩家位置，将玩家yf1_v5向上移动
        players = [f"玩家0 (yf1_v5)", "玩家1", "玩家2 (yf2_v5)", "玩家3"]
        # 调整位置，将顶部玩家向上移动，确保与中央出牌区有足够空间
        positions = [(600, 50), (1150, 400), (600, 720), (50, 400)]
        
        for i, (x, y) in enumerate(positions):
            # 对所有玩家使用统一的剩余牌数计算逻辑：初始27张减去已出牌数
            # 这是最可靠的方法，因为初始手牌加载可能不准确
            initial_hand_count = 27  # 掼蛋每个玩家初始有27张牌
            
            # 计算已出的牌数
            played_count = 0
            for action in self.actions[:self.current_step]:
                cur_pos = action.get('cur_pos', -1)
                if cur_pos == i:
                    cur_action = action.get('cur_action', [])
                    action_info = self._parse_action(cur_action)
                    if action_info:
                        action_type, _, played_cards = action_info
                        # 标准化动作类型为大写，避免大小写问题
                        action_type = action_type.upper() if action_type else ""
                        if action_type != "PASS" and played_cards:
                            played_count += len(played_cards)
            
            # 计算剩余牌数
            remaining_cards = initial_hand_count - played_count
            
            # 确保剩余牌数不会是负数或超过27
            remaining_cards = max(0, min(27, remaining_cards))
            
            if i == 2:  # 底部玩家（yf2_v5），将文本放在卡牌直接下方，间距15px
                # 玩家名称和剩余牌数放在一起，显示在卡牌下方
                # 卡牌位置：canvas_height - 200，卡牌高度：70px
                card_bottom = self.card_canvas.winfo_height() - 200 + 70
                text_y = card_bottom + 15  # 间距15px
                self.card_canvas.create_text(x, text_y, 
                                            text=f"{players[i]} 剩余: {remaining_cards}", 
                                            fill="white", font=("Arial", 12, "bold"), anchor=tk.CENTER)
            else:
                # 玩家名称 - 更大的字体，直接显示
                self.card_canvas.create_text(x, y, text=players[i], fill="white", 
                                            font=("Arial", 14, "bold"), anchor=tk.CENTER)
                # 显示剩余牌数
                if i == 0:  # 顶部玩家，剩余牌数显示在名称下方
                    self.card_canvas.create_text(x, y+30, text=f"剩余: {remaining_cards}", 
                                                fill="white", font=("Arial", 12), anchor=tk.CENTER)
                else:  # 左右玩家（1和3），剩余牌数显示在名称下方，分行显示
                    # 玩家名称
                    self.card_canvas.create_text(x, y, text=players[i], fill="white", 
                                                font=("Arial", 14, "bold"), anchor=tk.CENTER)
                    # 剩余牌数显示在玩家名称下方
                    self.card_canvas.create_text(x, y+30, text=f"剩余: {remaining_cards}", 
                                                fill="white", font=("Arial", 12), anchor=tk.CENTER)
    
    def _draw_player_hand(self, player_pos):
        """绘制指定玩家的手牌
        
        Args:
            player_pos: 玩家位置 (0-3: 上, 右, 下, 左)
        """
        pos_str = str(player_pos)
        if pos_str not in self.player_hands:
            return
        
        cards = self.player_hands[pos_str]
        if not cards:
            return
        
        # 调整牌的大小和间距，使其更美观，采用竖排重叠显示
        card_width = 50  # 竖排宽度
        card_height = 70  # 竖排高度
        overlap = 15  # 重叠距离，使卡牌部分重叠
        
        # 根据玩家位置确定布局参数
        canvas_width = self.card_canvas.winfo_width()
        canvas_height = self.card_canvas.winfo_height()
        
        num_cards = len(cards)
        
        if player_pos == 0:  # 顶部玩家 - yf1_v5，竖排，牌面向上
            # 垂直居中，水平排列，牌面向上
            start_x = canvas_width // 2 - (num_cards * (card_width - overlap) // 2)
            start_y = 100  # 向上移动20px，确保与其他元素不重叠
            
            # 绘制手牌 - 顶部玩家（yf1_v5，牌面向上）
            for i, card in enumerate(cards):
                x = start_x + i * (card_width - overlap)
                y = start_y
                self._draw_card_normal(x, y, card_width, card_height, card, False)  # 牌面向上
        elif player_pos == 1:  # 右侧玩家 - 对手，横排，牌面向右
            # 水平居中，垂直排列，牌面向右
            start_y = canvas_height // 2 - (num_cards * (card_height - overlap) // 2)
            start_x = canvas_width - 150  # 向左调整更多，给玩家信息留出空间
            
            # 绘制手牌 - 右侧玩家（对手，牌面向右）
            for i, card in enumerate(cards):
                x = start_x
                y = start_y + i * (card_height - overlap)
                self._draw_card_vertical(x, y, card_width, card_height, card, True)  # 牌面向右
        elif player_pos == 2:  # 底部玩家 - yf2_v5，竖排，牌面向上
            # 垂直居中，水平排列，牌面向上
            start_x = canvas_width // 2 - (num_cards * (card_width - overlap) // 2)
            start_y = canvas_height - 200  # 向上调整更多，确保所有玩家信息完整显示
            
            # 绘制手牌 - 底部玩家（yf2_v5，牌面向上）
            for i, card in enumerate(cards):
                x = start_x + i * (card_width - overlap)
                y = start_y
                self._draw_card_normal(x, y, card_width, card_height, card, False)  # 牌面向上
        else:  # 左侧玩家 - 对手，横排，牌面向左
            # 水平居中，垂直排列，牌面向左
            start_y = canvas_height // 2 - (num_cards * (card_height - overlap) // 2)
            start_x = 100  # 向右调整更多，给玩家信息留出空间
            
            # 绘制手牌 - 左侧玩家（对手，牌面向左）
            for i, card in enumerate(cards):
                x = start_x
                y = start_y + i * (card_height - overlap)
                self._draw_card_vertical(x, y, card_width, card_height, card, True)  # 牌面向左
        
        # 更新剩余牌数，确保准确性
        if pos_str in self.player_hands:
            # 直接根据实际显示的卡牌数量来更新剩余牌数
            self.player_hands[pos_str] = cards
    
    def _draw_card_normal(self, x, y, width, height, card, is_back=False):
        """绘制普通水平方向的牌"""
        if is_back:
            # 背面朝上
            self.card_canvas.create_rectangle(x, y, x+width, y+height, 
                                            fill="#8B0000", outline="#000000", width=2)
            self.card_canvas.create_text(x+width/2, y+height/2, text="?", 
                                        font=('Arial', 20, 'bold'), fill="white")
        else:
            # 正面朝上 - 背景色统一为白色
            bg_color = "#FFFFFF"
            
            # 绘制牌的边框和背景
            self.card_canvas.create_rectangle(x, y, x+width, y+height, 
                                            fill=bg_color, outline="black", width=2)
            
            # 绘制牌面内容
            rank_map = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A', 
                       '2': '2', 'B': 'B', 'R': 'R', '1': 'A'}  # 添加对'1'的映射，确保显示为'A'
            
            suit_map = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
            
            suit = card[0]
            rank = card[1:]
            
            display_rank = rank_map.get(rank, rank)
            display_suit = suit_map.get(suit, suit)
            
            # 绘制左上角的花色和数字 - 增大字体+2px
            self.card_canvas.create_text(x+5, y+5, text=f"{display_rank}{display_suit}", 
                                        font=('Arial', 12, 'bold'), anchor=tk.NW, 
                                        fill="black" if suit in ['S', 'C'] else "red")
            
            # 绘制中间的花色
            self.card_canvas.create_text(x+width/2, y+height/2, text=display_suit, 
                                        font=('Arial', 18, 'bold'), anchor=tk.CENTER, 
                                        fill="black" if suit in ['S', 'C'] else "red")
    
    def _draw_card_vertical(self, x, y, width, height, card, is_back=False):
        """绘制垂直方向的牌"""
        if is_back:
            # 背面朝上
            self.card_canvas.create_rectangle(x, y, x+height, y+width, 
                                            fill="#8B0000", outline="#000000", width=2)
            self.card_canvas.create_text(x+height/2, y+width/2, text="?", 
                                        font=('Arial', 20, 'bold'), fill="white")
        else:
            # 正面朝上 - 背景色统一为白色
            bg_color = "#FFFFFF"
            
            # 绘制牌的边框和背景
            self.card_canvas.create_rectangle(x, y, x+height, y+width, 
                                            fill=bg_color, outline="black", width=2)
            
            # 绘制牌面内容
            rank_map = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A', 
                       '2': '2', 'B': 'B', 'R': 'R', '1': 'A'}  # 添加对'1'的映射，确保显示为'A'
            
            suit_map = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
            
            suit = card[0]
            rank = card[1:]
            
            display_rank = rank_map.get(rank, rank)
            display_suit = suit_map.get(suit, suit)
            
            # 绘制左上角的花色和数字（旋转90度）
            self.card_canvas.create_text(x+5, y+width//2, text=f"{display_rank}{display_suit}", 
                                        font=('Arial', 10, 'bold'), anchor=tk.NW, 
                                        fill="black" if suit in ['S', 'C'] else "red")
            
            # 绘制中间的花色（旋转90度）
            self.card_canvas.create_text(x+height//2, y+width//2, text=display_suit, 
                                        font=('Arial', 18, 'bold'), anchor=tk.CENTER, 
                                        fill="black" if suit in ['S', 'C'] else "red")
    
    def _draw_step_info(self):
        """绘制步骤信息"""
        if self.current_step == 0:
            # 游戏开始，显示初始手牌信息
            info = "游戏开始 - 初始手牌信息\n"
            for pos in range(4):
                pos_str = str(pos)
                if pos_str in self.initial_hands:
                    cards = self.initial_hands[pos_str]
                    info += f"玩家{pos}: {len(cards)}张手牌\n"
        else:
            action = self.actions[self.current_step - 1]
            timestamp = action.get('timestamp', '')[:19]  # 只显示日期时间部分
            cur_pos = action.get('cur_pos', -1)
            cur_action = action.get('cur_action', '[]')
            
            # 获取玩家名称
            players = ["玩家0 (yf1_v5)", "玩家1", "玩家2 (yf2_v5)", "玩家3"]
            player_name = players[cur_pos] if 0 <= cur_pos < 4 else f"未知({cur_pos})"
            
            info = (f"步骤: {self.current_step}/{self.total_steps}\n"
                  f"时间: {timestamp}\n"
                  f"玩家: {player_name}\n"
                  f"动作: {cur_action}")
        
        # 绘制在右上角
        self.card_canvas.create_text(self.card_canvas.winfo_width() - 20, 20, 
                                    text=info, fill="white", 
                                    font=("Arial", 12), anchor=tk.NE, 
                                    width=350, justify=tk.LEFT)
    
    def _draw_current_action(self, action):
        """绘制当前动作（将打出的牌放在中央，增强视觉效果）"""
        cur_pos = action.get('cur_pos', -1)
        cur_action = action.get('cur_action', '')
        
        # 解析动作
        action_info = self._parse_action(cur_action)
        if not action_info:
            # 如果无法解析，尝试直接从action_str中提取
            action_str = str(cur_action)
            self.card_canvas.create_text(self.card_canvas.winfo_width() // 2, self.card_canvas.winfo_height() // 2,
                                        text=f"动作: {action_str}", fill="white", font=("Arial", 14), anchor=tk.CENTER)
            return
        
        action_type, rank, cards = action_info
        
        # 绘制打出的牌 - 在中央区域，放大显示
        canvas_width = self.card_canvas.winfo_width()
        canvas_height = self.card_canvas.winfo_height()
        
        card_width = 50  # 放大牌的尺寸，使其更醒目
        card_height = 70
        spacing = 8
        
        # 计算起始位置（中央）
        total_width = (len(cards) * (card_width + spacing)) - spacing
        start_x = canvas_width // 2 - total_width // 2
        start_y = canvas_height // 2 - card_height // 2
        
        # 获取玩家名称
        players = ["玩家0 (yf1_v5)", "玩家1", "玩家2 (yf2_v5)", "玩家3"]
        player_name = players[cur_pos] if 0 <= cur_pos < 4 else f"未知({cur_pos})"
        
        # 绘制动作类型标签
        action_types = {
            'Single': '单牌',
            'Pair': '对子',
            'Triple': '三张',
            'ThreeWithTwo': '三带二',
            'Straight': '顺子',
            'StraightFlush': '同花顺',
            'Bomb': '炸弹',
            'Rocket': '王炸',
            'Pass': '过牌',
            'Tribute': '进贡',
            'Back': '还贡',
            'dispatch': '发牌'
        }
        
        display_type = action_types.get(action_type, action_type)
        
        # 调整玩家名称和动作类型在同一行显示
        # 玩家名称上移5px
        combined_text = f"{player_name} 出牌 {display_type}"
        self.card_canvas.create_text(canvas_width // 2, start_y - 45,  # 上移5px
                                    text=combined_text, fill="#FFD700", 
                                    font=("Arial", 10, "bold"), anchor=tk.CENTER)
        
        # 如果是过牌，直接显示文字，不要尝试绘制卡牌
        if action_type == 'Pass' or display_type == '过牌':
            # 直接显示"过牌"文字，居中显示
            self.card_canvas.create_text(canvas_width // 2, canvas_height // 2,
                                        text="过牌", fill="#FFFFFF", 
                                        font=("Arial", 32, "bold"), anchor=tk.CENTER)  # 缩小字体
        elif isinstance(cards, list) and cards:
            # 绘制当前打出的牌
            for i, card in enumerate(cards):
                card_x = start_x + i * (card_width + spacing)
                card_y = start_y
                self._draw_card_normal(card_x, card_y, card_width, card_height, card, False)
        else:
            # 无法解析的动作，显示文字描述
            self.card_canvas.create_text(canvas_width // 2, canvas_height // 2,
                                        text=display_type, fill="#FFFFFF", 
                                        font=("Arial", 36, "bold"), anchor=tk.CENTER)
        
        # 绘制当前玩家指示 - 高亮显示
        self._highlight_current_player(cur_pos)
    
    def _highlight_current_player(self, player_pos):
        """高亮显示当前行动的玩家"""
        # 玩家位置
        positions = [(600, 80), (1150, 400), (600, 720), (50, 400)]
        
        if player_pos >= 0 and player_pos < 4:
            x, y = positions[player_pos]
            
            # 为不同玩家调整黄色小方块位置，确保都在屏幕范围内且清晰可见
            if player_pos == 2:  # 玩家2，黄色方块放在左侧
                # 黄色小方块放在玩家标签左侧
                self.card_canvas.create_rectangle(x-80, y-10, x-50, y+10, 
                                            fill="#FFFF00")
            elif player_pos == 3:  # 玩家3，黄色方块放在右侧
                # 黄色小方块放在玩家标签右侧
                self.card_canvas.create_rectangle(x+80, y-10, x+110, y+10, 
                                            fill="#FFFF00")
            else:  # 玩家0和1
                # 绘制黄色小方块作为指示，统一放在玩家标签前面
                self.card_canvas.create_rectangle(x-80, y-10, x-50, y+10, 
                                            fill="#FFFF00")
    
    def _parse_action(self, action):
        """解析动作，支持多种格式
        
        Args:
            action: 动作数据，可以是字符串或列表
            
        Returns:
            解析后的动作信息：(action_type, rank, cards)
        """
        try:
            # 如果是字符串，尝试转换为列表
            if isinstance(action, str):
                action_list = eval(action)
            elif isinstance(action, list):
                action_list = action
            else:
                # 如果是其他类型，尝试转换为字符串再处理
                action_list = eval(str(action))
            
            if not isinstance(action_list, list):
                return None
            
            # 处理不同格式的动作
            if len(action_list) >= 3:
                # 标准格式：[action_type, rank, cards]
                action_type = action_list[0]
                rank = action_list[1]
                cards = action_list[2]
                return action_type, rank, cards
            elif len(action_list) == 2:
                # 简化格式：[action_type, data]
                action_type = action_list[0]
                data = action_list[1]
                # 尝试解析数据为卡牌列表
                if isinstance(data, list):
                    return action_type, "", data
                else:
                    # 无法解析的格式，返回空卡牌列表
                    return action_type, "", []
            else:
                # 无法解析的格式
                return None
        except Exception as e:
            # 尝试直接从动作字符串中提取卡牌信息
            try:
                if isinstance(action, str):
                    # 尝试匹配卡牌格式，例如：['Single', '5', ['H5']]
                    import re
                    cards_match = re.search(r'\[\[.*?\]\]', action)
                    if cards_match:
                        cards_str = cards_match.group(0)
                        cards = eval(cards_str)
                        return "Unknown", "", cards
            except:
                pass
            
            # 所有解析尝试都失败
            return None
    
    def _on_progress_change(self, value):
        """当进度条被拖动时"""
        if not self.current_game or not self.actions:
            return
        
        self.is_playing = False
        self.play_btn.config(text="播放")
        
        # 计算当前步骤
        self.current_step = int((float(value) / 100) * self.total_steps)
        self._update_progress()
    
    def _on_speed_change(self, value):
        """当速度被调整时"""
        self.play_speed = float(value)
        self.speed_label.config(text=f"{self.play_speed:.1f}x")

def main():
    """主函数"""
    root = tk.Tk()
    
    # 检查命令行参数
    game_file = None
    if len(sys.argv) > 1:
        game_file = sys.argv[1]
    
    app = YiFeiReplayGUI(root, game_file)
    root.mainloop()

if __name__ == "__main__":
    main()