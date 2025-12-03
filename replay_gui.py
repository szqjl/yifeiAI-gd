#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
掼蛋AI可视化回放系统 - 主程序
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

# 导入回放模块
from communication.replay_select import list_games
from communication.replay_game import replay_game_file
from communication.game_recorder import GameRecorder


class GuandanReplayGUI:
    """掼蛋AI可视化回放系统主类"""
    
    def __init__(self, root):
        """初始化GUI"""
        self.root = root
        self.root.title("掼蛋AI可视化回放系统")
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
        self.player_hands = {}
        self.played_cards = []
        
        # 初始化界面
        self._setup_ui()
        
        # 加载游戏记录
        self._load_game_records()
    
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
        
        # 刷新按钮
        ttk.Button(toolbar_frame, text="刷新列表", command=self._load_game_records).pack(side=tk.LEFT, padx=(0, 10))
        
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
        self.game_records = list_games()
        
        # 更新下拉列表
        game_names = [f"{idx+1}. {game.name}" for idx, game in enumerate(self.game_records)]
        self.game_combobox['values'] = game_names
        
        # 默认选择第一个
        if game_names:
            self.game_combobox.current(0)
            self._on_game_selected(None)
        
        self.status_bar.config(text=f"加载完成，共找到 {len(self.game_records)} 个游戏记录")
    
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
        game_info = f"游戏: {self.current_game.name}\n" \
                   f"大小: {self.current_game.stat().st_size/1024:.1f} KB\n" \
                   f"修改时间: {datetime.fromtimestamp(self.current_game.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n" \
                   f"玩家ID: {self.player_id}\n" \
                   f"动作数量: {self.total_steps}"
        self.game_info_label.config(text=game_info)
        
        # 清空画布，准备渲染
        self.card_canvas.delete("all")
        self._draw_current_step()
        
        self.status_bar.config(text=f"已选择游戏: {self.current_game.name}")
    
    def _load_game_data(self):
        """加载游戏数据"""
        self.status_bar.config(text=f"正在加载游戏数据: {self.current_game.name}")
        
        # 加载游戏数据
        self.current_game_data = GameRecorder.load_game(self.current_game)
        
        # 解析游戏数据
        self.actions = self.current_game_data.get('actions', [])
        self.my_decisions = self.current_game_data.get('my_decisions', [])
        self.player_id = self.current_game_data.get('player_id', 0)
        self.total_steps = len(self.actions)
        
        # 初始化玩家手牌
        self.player_hands = {}
        if 'all_players_hands' in self.current_game_data:
            self.player_hands = self.current_game_data['all_players_hands'].copy()
        
        # 初始化已出牌列表
        self.played_cards = []
        
        self.status_bar.config(text=f"游戏数据加载完成，共 {self.total_steps} 个动作")
    
    def _draw_initial_state(self):
        """绘制初始状态"""
        self.card_canvas.delete("all")
        
        # 绘制玩家位置标记
        players = ["玩家0 (yf1_v5)", "玩家1", "玩家2 (yf2_v5)", "玩家3"]
        positions = [(600, 50), (1100, 400), (600, 750), (100, 400)]
        
        for i, (x, y) in enumerate(positions):
            self.card_canvas.create_text(x, y, text=players[i], fill="white", font=("Arial", 12, "bold"), anchor=tk.CENTER)
            self.card_canvas.create_oval(x-40, y-20, x+40, y+20, fill="#228B22", outline="white", width=2)
    
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
        
        # 如果没有动作，显示初始状态
        if not self.actions:
            info = "没有游戏动作数据"
            self.card_canvas.create_text(600, 400, text=info, fill="white", font=("Arial", 14), anchor=tk.CENTER)
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
        players = [f"玩家0 (yf1_v5)", "玩家1", "玩家2 (yf2_v5)", "玩家3"]
        positions = [(600, 50), (1100, 400), (600, 750), (100, 400)]
        
        for i, (x, y) in enumerate(positions):
            # 玩家名称
            self.card_canvas.create_text(x, y, text=players[i], fill="white", 
                                        font=("Arial", 12, "bold"), anchor=tk.CENTER)
            # 玩家标记
            self.card_canvas.create_oval(x-40, y-20, x+40, y+20, 
                                        fill="#228B22" if i != self.player_id else "#FF8C00", 
                                        outline="white", width=2)
            
            # 显示剩余牌数
            remaining_cards = 0
            if str(i) in self.player_hands:
                remaining_cards = len(self.player_hands[str(i)])
            self.card_canvas.create_text(x, y+30, text=f"剩余: {remaining_cards}", 
                                        fill="white", font=("Arial", 10), anchor=tk.CENTER)
    
    def _draw_step_info(self):
        """绘制步骤信息"""
        if self.current_step == 0:
            info = "游戏开始 - 选择贡牌"
        else:
            action = self.actions[self.current_step - 1]
            timestamp = action.get('timestamp', '')
            cur_pos = action.get('cur_pos', -1)
            cur_action = action.get('cur_action', '[]')
            info = f"步骤: {self.current_step}\n" \
                  f"时间: {timestamp}\n" \
                  f"玩家: {cur_pos}\n" \
                  f"动作: {cur_action}"
        
        self.card_canvas.create_text(600, 600, text=info, fill="white", 
                                    font=("Arial", 12), anchor=tk.CENTER, 
                                    width=400, justify=tk.LEFT)
    
    def _draw_current_action(self, action):
        """绘制当前动作"""
        cur_pos = action.get('cur_pos', -1)
        cur_action = action.get('cur_action', '')
        
        # 解析动作
        action_info = self._parse_action(cur_action)
        if not action_info:
            return
        
        action_type, rank, cards = action_info
        
        # 绘制打出的牌
        x, y = self._get_player_position(cur_pos)
        card_width = 40
        card_height = 60
        spacing = 10
        
        # 计算起始位置
        start_x = x - (len(cards) * (card_width + spacing) - spacing) / 2
        start_y = y + 50
        
        for i, card in enumerate(cards):
            card_x = start_x + i * (card_width + spacing)
            card_y = start_y
            self._draw_card(card_x, card_y, card_width, card_height, card)
    
    def _get_player_position(self, player_id):
        """获取玩家位置坐标"""
        positions = [(600, 50), (1100, 400), (600, 750), (100, 400)]
        return positions[player_id % 4]
    
    def _parse_action(self, action_str):
        """解析动作字符串"""
        try:
            # 将字符串转换为列表
            action_list = eval(action_str)
            if not isinstance(action_list, list) or len(action_list) < 3:
                return None
            
            action_type = action_list[0]
            rank = action_list[1]
            cards = action_list[2]
            
            return action_type, rank, cards
        except Exception as e:
            return None
    
    def _draw_card(self, x, y, width, height, card):
        """绘制单张牌"""
        # 牌的背景色
        bg_color = "#FFFFFF" if card[0] in ['S', 'C'] else "#FFCCCC"
        
        # 绘制牌的边框和背景
        self.card_canvas.create_rectangle(x, y, x+width, y+height, 
                                        fill=bg_color, outline="black", width=2)
        
        # 绘制牌面内容
        rank_map = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A', 
                   '2': '2', 'B': 'B', 'R': 'R'}
        
        suit_map = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
        
        suit = card[0]
        rank = card[1:]
        
        display_rank = rank_map.get(rank, rank)
        display_suit = suit_map.get(suit, suit)
        
        # 绘制左上角的花色和数字
        self.card_canvas.create_text(x+5, y+5, text=f"{display_rank}{display_suit}", 
                                    font=("Arial", 10, "bold"), anchor=tk.NW, 
                                    fill="black" if suit in ['S', 'C'] else "red")
        
        # 绘制中间的花色
        self.card_canvas.create_text(x+width/2, y+height/2, text=display_suit, 
                                    font=("Arial", 20, "bold"), anchor=tk.CENTER, 
                                    fill="black" if suit in ['S', 'C'] else "red")
    
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
    app = GuandanReplayGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()