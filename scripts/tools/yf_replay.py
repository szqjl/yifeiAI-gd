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
python scripts/tools/yf_replay.py [游戏记录文件路径]
"""

import sys
import os
import re
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

RECORD_NAME_RE = re.compile(r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$")

# 显示用 rank 大小顺序（左→右，大→小）：大王 R、小王 B、A、K、Q、J、10、9...2
RANK_DISPLAY_ORDER = ['R', 'B', 'A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
# 1312 手牌列序：级牌抽出后，其余牌从 A 往 2 排
RANK_ORDER_AFTER_LEVEL = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
SUIT_ORDER_IDX = {'H': 0, 'S': 1, 'D': 2, 'C': 3}
SUIT_DISPLAY = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
RANK_DISPLAY = {'T': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A',
                '2': '2', 'B': 'B', 'R': 'R', '1': 'A'}

REPO_ROOT = Path(__file__).resolve().parents[2]
JOKER_SMALL_IMG = REPO_ROOT / "assets" / "replay" / "joker_small.png"
JOKER_BIG_IMG = REPO_ROOT / "assets" / "replay" / "joker_big.png"
sys.path.insert(0, str(REPO_ROOT / "src"))
os.environ['PYTHONPATH'] = str(REPO_ROOT / "src")

from communication.game_recorder import GameRecorder, normalize_cards_to_string_list
from communication.server_log_parser import ServerLogParser


def _canonical_replay_card(card):
    """单张牌 → 大写 'S2'（与 yf1_m3 录牌一致）。"""
    normalized = normalize_cards_to_string_list([card])
    if not normalized:
        return None
    raw = normalized[0]
    if isinstance(raw, str) and len(raw) >= 2:
        return raw[0].upper() + raw[1:].upper()
    return raw


def _cards_from_tribute_back_action(action):
    if len(action) < 3 or not isinstance(action[2], list):
        return []
    out = []
    for card in action[2]:
        canonical = _canonical_replay_card(card)
        if canonical:
            out.append(canonical)
    return out


def apply_tribute_back_to_hand(hand, my_decisions, player_id):
    """
    将 JSON 中贡前 initial_hand 按 my_decisions 调整为出牌前有效手牌。

    - act·tribute / 无 source 的 tribute：移除进贡牌（outgoing）
    - notify·tribute 且 receive_tribute_pos==player_id：加入收进贡牌
    - act·back / 无 source 的 back：移除还贡牌（outgoing）
    - notify·back 且 receive_back_pos==player_id：加入收还贡牌
    """
    result = list(hand or [])
    pid = int(player_id)
    for md in my_decisions or []:
        action = md.get("action") or []
        ctx = md.get("context") or {}
        if len(action) < 3:
            continue
        kind = str(action[0]).lower()
        if kind not in ("tribute", "back"):
            continue
        source = ctx.get("source", "act")
        cards = _cards_from_tribute_back_action(action)
        if not cards:
            continue
        if kind == "tribute":
            if source == "notify" and ctx.get("receive_tribute_pos") == pid:
                result.extend(cards)
            elif source != "notify":
                for card in cards:
                    if card in result:
                        result.remove(card)
        elif kind == "back":
            if source == "notify" and ctx.get("receive_back_pos") == pid:
                result.extend(cards)
            elif source != "notify":
                for card in cards:
                    if card in result:
                        result.remove(card)
    return result


def _context_has_rank_fields(ctx):
    if not ctx:
        return False
    return bool(ctx.get("curRank") or ctx.get("selfRank") or ctx.get("oppoRank"))


def resolve_episode_levels(data, filename=None):
    """本副 selfRank / oppoRank / curRank，优先级对齐 guandan-platform-v1006.mdc §curRank 真值。

    1. my_decisions · stage=play（优先 source=act）
    2. my_decisions · tribute/back（优先 source=act）
    3. result.curRank（episodeOver 落盘）
    4. actions[].context（notify 缓存，可靠性低）
    5. game_info（进贡前快照，常滞后）
    6. 文件名 [level]（仅 curRank 兜底索引）
    """
    play_act = None
    play_any = None
    tb_act = None
    tb_any = None

    for d in data.get("my_decisions") or []:
        ctx = d.get("context") or {}
        if not _context_has_rank_fields(ctx):
            continue
        stage = str(ctx.get("stage") or "").lower()
        source = str(ctx.get("source") or "act").lower()
        if stage == "play":
            if source == "act" and play_act is None:
                play_act = ctx
            elif play_any is None:
                play_any = ctx
        elif stage in ("tribute", "back"):
            if source == "act" and tb_act is None:
                tb_act = ctx
            elif tb_any is None:
                tb_any = ctx

    ctx = play_act or play_any or tb_act or tb_any

    if not ctx:
        result = data.get("result") or {}
        if result.get("curRank"):
            ctx = {"curRank": result.get("curRank")}

    if not ctx:
        for action in data.get("actions") or []:
            act_ctx = action.get("context") or {}
            if _context_has_rank_fields(act_ctx):
                ctx = act_ctx
                break

    if not ctx:
        gi = data.get("game_info") or {}
        if _context_has_rank_fields(gi):
            ctx = gi

    levels = {
        "curRank": str((ctx or {}).get("curRank") or ""),
        "selfRank": str((ctx or {}).get("selfRank") or ""),
        "oppoRank": str((ctx or {}).get("oppoRank") or ""),
    }

    if (not levels["curRank"] or levels["curRank"].lower() == "unknown") and filename:
        match = RECORD_NAME_RE.match(str(filename))
        if match and match.group(5):
            levels["curRank"] = str(match.group(5))

    for key, default in (("curRank", "2"), ("selfRank", "2"), ("oppoRank", "2")):
        if not levels[key] or levels[key].lower() == "unknown":
            levels[key] = default

    return levels


class YiFeiReplayGUI:
    """YiFei AI 掼蛋回放系统 - 整合版"""
    
    def __init__(self, root, game_file=None):
        """初始化GUI"""
        self.root = root
        self.root.title("YiFei AI 掼蛋回放系统 - 整合版")
        self.root.geometry("1280x920")
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

        # 玩家名字（来自 JSON / 文件名，避免硬编码）
        self.my_name = ""
        self.teammate_name = ""
        self.opp_label_pair = ("对手", "对手")

        # 级数（当前等级/本方/对方），来自 act·play context；缺失时默认 '2'
        self.cur_rank = '2'
        self.self_level = '2'
        self.opp_level = '2'

        # 牌面贴图缓存（PhotoImage 须保持引用，防 GC）
        self._card_image_cache = {}
        
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
        # 拖动窗口时同步重绘（按 canvas 当前尺寸重新计算布局）
        self.card_canvas.bind("<Configure>", lambda e: self._draw_current_step())

        # 右下角：可复制的本步出牌信息（宽 160px）
        self.step_copy_frame = tk.Frame(
            card_frame, width=160, height=68, bg="#f8f8f8",
            highlightthickness=1, highlightbackground="#555555",
        )
        self.step_copy_frame.pack_propagate(False)
        self.step_copy_text = tk.Text(
            self.step_copy_frame,
            width=1,
            height=4,
            wrap=tk.WORD,
            font=("Consolas", 9),
            relief=tk.FLAT,
            bg="#f8f8f8",
            padx=6,
            pady=4,
            borderwidth=0,
            cursor="xterm",
        )
        self.step_copy_text.pack(fill=tk.BOTH, expand=True)
        self.step_copy_text.bind("<Key>", self._step_copy_block_edit)
        self.step_copy_frame.place(relx=1.0, rely=1.0, anchor=tk.SE, x=-10, y=-10)
        self._update_step_copy_panel()
        
        # 4. 底部信息区
        info_frame = ttk.LabelFrame(main_frame, text="游戏信息", padding="5")
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 可复制游戏信息（文件名 / 路径）
        self.game_info_text = tk.Text(
            info_frame,
            height=1,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 9),
            relief=tk.FLAT,
            padx=4,
            pady=2,
            borderwidth=0,
            cursor="xterm",
        )
        self.game_info_text.pack(fill=tk.X, padx=5, pady=5)
        self.game_info_text.bind("<Key>", self._step_copy_block_edit)
        self._set_game_info_text("请选择一个游戏记录开始回放")
        
        # 状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _load_game_records(self):
        """加载游戏记录列表（支持 JSON 和 Pickle 格式）"""
        self.status_bar.config(text="正在加载游戏记录...")
        
        # 查找所有JSON和.data文件
        json_files = list(Path("game_records").glob("*.json"))
        data_files = list(Path("game_records").glob("*.data"))
        
        # 合并文件列表
        game_files = json_files + data_files
        
        # 过滤掉增强版文件，只显示原始记录
        self.game_records = [f for f in game_files if not f.name.startswith("enhanced_")]

        # 倒序排列：最新的在最上面（按文件修改时间 desc）
        self.game_records.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        # 更新下拉列表
        game_names = [f.name for f in self.game_records]
        self.game_combobox['values'] = game_names
        
        # 默认选择第一个
        if game_names:
            self.game_combobox.current(0)
            self._on_game_selected(None)
        
        json_count = len([f for f in self.game_records if f.suffix == '.json'])
        data_count = len([f for f in self.game_records if f.suffix == '.data'])
        self.status_bar.config(text=f"加载完成，共找到 {len(self.game_records)} 个游戏记录（JSON: {json_count}, Pickle: {data_count}）")
    
    def _load_file(self):
        """加载指定的游戏文件（支持 JSON 和 Pickle 格式）"""
        file_path = filedialog.askopenfilename(
            title="选择游戏记录文件",
            filetypes=[
                ("所有支持格式", "*.json;*.data"),
                ("JSON文件", "*.json"),
                ("Pickle文件", "*.data"),
                ("所有文件", "*.*")
            ],
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
        self._set_game_info_text(self._format_game_info_text())
        
        # 清空画布，准备渲染
        self.card_canvas.delete("all")
        self._draw_current_step()
        self._update_step_copy_panel()
        
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
        self._set_game_info_text(self._format_game_info_text())
        
        # 清空画布，准备渲染
        self.card_canvas.delete("all")
        self._draw_current_step()
        self._update_step_copy_panel()
        
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
        self.teammate_record_data = None
        
        # 保存初始手牌（所有玩家）
        self.initial_hands = {}

        # 1. 从initial_hand获取当前玩家的初始手牌（贡前快照，27 张）
        if 'initial_hand' in self.current_game_data:
            self.initial_hands[str(self.player_id)] = self.current_game_data['initial_hand'].copy()

        # 2. 从all_players_hands获取所有玩家的初始手牌
        if 'all_players_hands' in self.current_game_data:
            for pos, cards in self.current_game_data['all_players_hands'].items():
                pos_str = str(pos)
                if isinstance(cards, list):
                    self.initial_hands[pos_str] = cards.copy()
                else:
                    self.initial_hands[pos_str] = []

        self.tribute_info = {}
        self.back_info = {}
        try:
            server_log_path = Path("src/communication/Testscore/服务端")
            if server_log_path.exists():
                parser = ServerLogParser()
                server_data = parser.parse_log_file(str(server_log_path))
                
                # ⚠️ 重要：只在游戏记录中完全没有该玩家手牌时才使用服务器日志补充
                # 优先使用游戏记录中的手牌（更准确），避免服务器日志解析错误导致显示错误
                if 'initial_hands' in server_data:
                    for pos, cards in server_data['initial_hands'].items():
                        pos_str = str(pos)
                        # 只有在游戏记录中完全没有该玩家手牌时才补充
                        if pos_str not in self.initial_hands or not self.initial_hands[pos_str]:
                            # 只接受合理数量的初始手牌（27张左右）
                            if isinstance(cards, list) and len(cards) > 10 and len(cards) <= 27:
                                # 验证卡牌格式
                                valid_cards = []
                                for card in cards:
                                    if isinstance(card, str) and len(card) >= 2:
                                        valid_cards.append(card)
                                if len(valid_cards) > 10:
                                    self.initial_hands[pos_str] = valid_cards
                                    self.status_bar.config(text=f"从服务器日志补充玩家{pos_str}的手牌: {len(valid_cards)}张")
        except Exception as e:
            self.status_bar.config(text=f"补充初始手牌失败: {e}")
        
        # 4. 确保所有4个玩家都有初始手牌字段
        for pos in range(4):
            pos_str = str(pos)
            if pos_str not in self.initial_hands or not self.initial_hands[pos_str]:
                self.initial_hands[pos_str] = []

        # 5. 解析当前玩家 / 对手名字并合并队友（同一局另一份 JSON）的初始手牌
        self._resolve_player_labels()
        self._try_load_teammate_record()
        self._resolve_levels()

        # 6. 所有手牌来源合并后，再按 my_decisions 调整贡/还（本家 + 已合并队友）
        self._apply_tribute_back_to_initial_hands()

        # 7. 计算当前所有玩家的手牌
        self.player_hands = self._calculate_current_hands()
        status = f"游戏数据加载完成，共 {self.total_steps} 个动作，初始手牌: {len(self.initial_hands)} 个玩家"
        if self.current_game_data.get("_actions_synthesized"):
            status += "（由 my_decisions 合成，缺对手出牌步）"
        elif self.total_steps == 0:
            duration = self.current_game_data.get("duration")
            if duration is not None and duration < 1.0:
                status = "本副几乎无打牌即结束（空壳牌谱），请选同批较大 JSON（如 round 6/8/11）"
            else:
                status = "无 actions：未按 M3 契约录 notify 出牌，请用更新后 V7 重跑或选含 my_decisions 的牌谱"
        self.status_bar.config(text=status)
    
    def _resolve_player_labels(self):
        """从 JSON player_name + 文件名 opponent_* 解析 4 个玩家的显示名。"""
        self.my_name = self.current_game_data.get('player_name', '') or ''

        # 文件名形如 "<ts> [yf1_m1]-[opponent_1_3]-[20]-[None].json"
        # opponent_X_Y 通常表示对手在 pos X 和 Y
        m = RECORD_NAME_RE.match(self.current_game.name)
        if m:
            opp_field = m.group(3)
            # 解析对手位置（pos 1 + pos 3 之类）
            opp_positions = []
            for part in opp_field.replace('opponent_', '').split('_'):
                if part.isdigit():
                    opp_positions.append(int(part))
            if len(opp_positions) == 2:
                self.opp_label_pair = (f"对手@{opp_positions[0]}", f"对手@{opp_positions[1]}")

    def _try_load_teammate_record(self):
        """同一局 round 的队友（yf1↔yf2）JSON 合并进 initial_hands，让对面/边上能看到我方两人手牌。"""
        m = RECORD_NAME_RE.match(self.current_game.name)
        if not m:
            return
        my_name = m.group(2)
        round_num = m.group(4)
        suffix = m.group(5)

        # 推断队友名（仅当前命名约定：yf1 ↔ yf2）
        if 'yf1' in my_name:
            teammate_name = my_name.replace('yf1', 'yf2', 1)
        elif 'yf2' in my_name:
            teammate_name = my_name.replace('yf2', 'yf1', 1)
        else:
            return

        # 同目录下找匹配文件（不能用 Path.glob — 文件名含 [...] 会被当字符类匹配）
        candidates = []
        for sibling in self.current_game.parent.iterdir():
            if not sibling.is_file() or sibling.suffix != '.json':
                continue
            sm = RECORD_NAME_RE.match(sibling.name)
            if not sm:
                continue
            if sm.group(2) == teammate_name and sm.group(4) == round_num and sm.group(5) == suffix:
                candidates.append(sibling)
        if not candidates:
            return

        # 与当前文件时间戳最接近的那份（兼容同 round 跨批次）
        my_ts = int(self.current_game.name.split(' ', 1)[0])
        teammate_file = min(candidates, key=lambda p: abs(int(p.name.split(' ', 1)[0]) - my_ts))

        try:
            teammate_data = GameRecorder.load_game(teammate_file)
        except Exception as e:
            self.status_bar.config(text=f"队友记录加载失败 {teammate_file.name}: {e}")
            return

        teammate_pos = teammate_data.get('player_id')
        teammate_hand = teammate_data.get('initial_hand', [])

        # 队友名字：哪怕手牌已被 GameRecorder.load_game 预填进 all_players_hands，名字也要落到 self.teammate_name 上
        self.teammate_name = teammate_data.get('player_name', teammate_name) or teammate_name
        self.teammate_record_data = teammate_data

        if teammate_pos is None or not isinstance(teammate_hand, list) or not teammate_hand:
            return

        pos_str = str(teammate_pos)
        # 仅在尚无该位置手牌时合并（不覆盖 GameRecorder 已合并好的数据）
        if not self.initial_hands.get(pos_str):
            self.initial_hands[pos_str] = list(teammate_hand)
            self.status_bar.config(text=f"已合并队友 {self.teammate_name} 初始手牌 ({len(teammate_hand)}张) from {teammate_file.name}")

    def _build_player_labels(self):
        """返回长度 4 的玩家显示名列表，按位置 0..3。"""
        labels = [f"玩家{i}" for i in range(4)]
        if self.my_name:
            labels[self.player_id] = f"玩家{self.player_id} ({self.my_name})"
        teammate_pos = (self.player_id + 2) % 4
        if self.teammate_name:
            labels[teammate_pos] = f"玩家{teammate_pos} ({self.teammate_name})"
        opp_positions = [p for p in range(4) if p != self.player_id and p != teammate_pos]
        for idx, p in enumerate(opp_positions):
            opp_name = self.opp_label_pair[idx] if idx < len(self.opp_label_pair) else f"对手@{p}"
            labels[p] = f"玩家{p} ({opp_name})"
        return labels

    def _normalize_rank_char(self, rank_str):
        r = str(rank_str or '2').strip().upper()
        if r in ('10', 'T'):
            return 'T'
        if r == '1':
            return 'A'
        return r

    def _hand_column_rank_order(self):
        """1312 列序：R、B、级牌、A…2（级牌列在小王之后）。"""
        level = self._normalize_rank_char(self.cur_rank)
        order = ['R', 'B']
        if level and level not in ('R', 'B'):
            order.append(level)
        for rank in RANK_ORDER_AFTER_LEVEL:
            if rank != level:
                order.append(rank)
        return order

    def _resolve_levels(self):
        """读级数：resolve_episode_levels（play 优先，不用 beginning/game_info 快照）。"""
        fname = self.current_game.name if self.current_game else None
        levels = resolve_episode_levels(self.current_game_data or {}, fname)
        self.cur_rank = levels["curRank"]
        self.self_level = levels["selfRank"]
        self.opp_level = levels["oppoRank"]

    def _organize_hand_columns(self, cards):
        """把手牌按 rank 分组，返回按显示顺序排好的 [(rank, [cards])]。"""
        by_rank = {}
        for card in cards or []:
            if not isinstance(card, str) or len(card) < 2:
                continue
            rank = card[1:]
            if rank == '1':  # 兼容遗留 '1' → 'A'
                rank = 'A'
                card = card[0] + 'A'
            by_rank.setdefault(rank, []).append(card)
        cols = []
        display_order = self._hand_column_rank_order()
        for rank in display_order:
            if rank in by_rank:
                group = sorted(by_rank[rank], key=lambda c: SUIT_ORDER_IDX.get(c[0], 99))
                cols.append((rank, group))
        # 兜底：未在 display_order 出现的（不应该有，但保险）
        for rank in sorted(by_rank.keys() - set(display_order)):
            cols.append((rank, by_rank[rank]))
        return cols

    def _apply_tribute_back_to_initial_hands(self):
        """贡前 initial_hand 按 my_decisions 调整为出牌前有效手牌（本家 + 队友 JSON）。"""
        self._apply_tribute_back_for_player(
            str(self.player_id),
            self.my_decisions,
            self.player_id,
        )
        teammate_data = getattr(self, "teammate_record_data", None)
        if teammate_data:
            teammate_pos = teammate_data.get("player_id")
            if teammate_pos is not None:
                self._apply_tribute_back_for_player(
                    str(teammate_pos),
                    teammate_data.get("my_decisions", []),
                    teammate_pos,
                )
        self._refresh_tribute_back_info()

    def _apply_tribute_back_for_player(self, pos_str, my_decisions, player_id):
        if pos_str not in self.initial_hands or not self.initial_hands[pos_str]:
            return
        self.initial_hands[pos_str] = apply_tribute_back_to_hand(
            self.initial_hands[pos_str],
            my_decisions,
            player_id,
        )

    def _refresh_tribute_back_info(self):
        """从 my_decisions 提取贡/还牌摘要，供界面展示。"""
        self.tribute_info = {}
        self.back_info = {}
        for decision in self.my_decisions or []:
            action = decision.get("action") or []
            ctx = decision.get("context") or {}
            if len(action) < 3 or not isinstance(action[2], list):
                continue
            kind = str(action[0]).lower()
            cards = _cards_from_tribute_back_action(action)
            if not cards:
                continue
            if kind == "tribute":
                self.tribute_info.setdefault(self.player_id, []).extend(cards)
            elif kind == "back":
                self.back_info.setdefault(self.player_id, []).extend(cards)

    def _calculate_current_hands(self):
        """计算所有玩家的当前手牌（到当前步骤为止）"""
        # 从 initial_hands 开始（本家已在 _load_game_data 中按贡/还牌调整）
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
                    
                    # ⚠️ 重要：规范化卡牌格式，确保正确移除
                    normalized_played_cards = []
                    for card in played_cards:
                        if isinstance(card, str) and len(card) >= 2:
                            normalized_played_cards.append(card)
                        elif isinstance(card, list) and len(card) >= 2:
                            # 处理["C", "8"]格式，转换为"C8"
                            suit = str(card[0])
                            rank = str(card[1])
                            normalized_played_cards.append(f"{suit}{rank}")
                    
                    # 移除打出的牌
                    removed_count = 0
                    for card in normalized_played_cards:
                        if card in player_cards:
                            player_cards.remove(card)
                            removed_count += 1
                    
                    current_hands[pos_str] = player_cards
                    
                    # 验证移除数量（仅在调试模式下）
                    if removed_count != len(normalized_played_cards):
                        import logging
                        logger = logging.getLogger("YiFeiReplayGUI")
                        logger.debug(f"回放系统：卡牌移除数量不匹配，期望移除{len(normalized_played_cards)}张，实际移除{removed_count}张，玩家{pos_str}")
        
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
        self._update_step_copy_panel()

    def _step_copy_block_edit(self, event):
        """只读：允许选择与复制，禁止改字。"""
        if event.state & 0x4 and event.keysym.lower() in ("c", "a", "insert"):
            return
        if event.keysym in (
            "Left", "Right", "Up", "Down", "Home", "End",
            "Shift_L", "Shift_R", "Control_L", "Control_R",
        ):
            return
        return "break"

    def _format_game_info_text(self):
        if not self.current_game:
            return "请选择一个游戏记录开始回放"
        return f"游戏: {self.current_game.name}"

    def _set_game_info_text(self, text):
        if not hasattr(self, "game_info_text"):
            return
        self.game_info_text.config(state=tk.NORMAL)
        self.game_info_text.delete("1.0", tk.END)
        self.game_info_text.insert("1.0", text)
        self.game_info_text.config(state=tk.NORMAL)

    def _format_card_display_name(self, card):
        if not isinstance(card, str) or len(card) < 2:
            return str(card)
        suit = card[0]
        rank = card[1:]
        if rank == "1":
            rank = "A"
        display_rank = RANK_DISPLAY.get(rank, rank)
        display_suit = SUIT_DISPLAY.get(suit, suit)
        return f"{display_suit}{display_rank}"

    def _short_player_name(self, pos):
        """复制块用短名：yf1_m3 / client3 / 对手@1 …"""
        try:
            pos = int(pos)
        except (TypeError, ValueError):
            return f"pos{pos}"
        labels = self._build_player_labels()
        if not (0 <= pos < len(labels)):
            return f"pos{pos}"
        label = labels[pos]
        if "(" in label and label.endswith(")"):
            return label.split("(", 1)[1][:-1]
        return label

    def _format_step_play_copy_text(self):
        """本步出牌可复制文本：n/total + 玩家名 + 牌名。"""
        total = self.total_steps or 0
        n = self.current_step
        line1 = f"{n}/{total}"
        if n <= 0 or not self.actions:
            return f"{line1}\n—"
        action = self.actions[n - 1]
        player = self._short_player_name(action.get("cur_pos", -1))
        action_info = self._parse_action(action.get("cur_action"))
        if not action_info:
            raw = action.get("cur_action", "")
            return f"{line1}\n{player}\n{raw}"
        action_type, _rank, cards = action_info
        at = (action_type or "").upper()
        if at == "PASS":
            return f"{line1}\n{player}\n过"
        if isinstance(cards, list) and cards:
            names = [self._format_card_display_name(c) for c in cards]
            return f"{line1}\n{player}\n{' '.join(names)}"
        type_labels = {
            "TRIBUTE": "进贡", "BACK": "还贡",
            "DISPATCH": "发牌",
        }
        label = type_labels.get(at, action_type or "—")
        return f"{line1}\n{player}\n{label}"

    def _update_step_copy_panel(self):
        if not hasattr(self, "step_copy_text"):
            return
        text = self._format_step_play_copy_text()
        self.step_copy_text.config(state=tk.NORMAL)
        self.step_copy_text.delete("1.0", tk.END)
        self.step_copy_text.insert("1.0", text)
        self.step_copy_text.config(state=tk.NORMAL)
    
    def _draw_current_step(self):
        """绘制当前步骤的牌面（1312 大牌风格：按 rank 堆叠 + 顶部级数标签）。"""
        self.card_canvas.delete("all")
        w = self.card_canvas.winfo_width() or 1200
        h = self.card_canvas.winfo_height() or 700
        self.card_canvas.create_rectangle(0, 0, w, h, fill="#1c5b8a")

        # 顶部左上角：本方/对方级数 + 过（当前步是 PASS 时）
        self._draw_level_badges()

        if not self.actions:
            msg = "没有游戏动作数据"
            if self.current_game_data:
                if self.current_game_data.get("duration", 99) < 1.0:
                    msg = "本副为秒结束空壳记录\n（无出牌步，请换 round 6/8/11 等同批牌谱）"
                elif not (self.current_game_data.get("my_decisions") or []):
                    msg = "牌谱无 actions 且无 my_decisions\n请用对齐 M3 录制契约的 V7 客户端重跑"
                else:
                    msg = "无法合成回放步序\n请更新客户端后重跑以录制完整 notify"
            self.card_canvas.create_text(w // 2, h // 2,
                                          text=msg, fill="white",
                                          font=("Arial", 14), anchor=tk.CENTER,
                                          justify=tk.CENTER)
            return

        # 4 个玩家手牌 + 名字 + 剩余张数
        cur_action_pos = self._current_acting_pos()
        for pos in range(4):
            self._draw_player_block(pos, highlight=(pos == cur_action_pos))

        # 中央出牌区
        if 0 < self.current_step <= self.total_steps:
            self._draw_current_action(self.actions[self.current_step - 1])

        # 右上角步骤信息（继续保留）
        self._draw_step_info()
    
    # ---------------- 新版布局工具 ----------------

    def _current_acting_pos(self):
        if 0 < self.current_step <= self.total_steps:
            return self.actions[self.current_step - 1].get('cur_pos', -1)
        return -1

    def _seat_for_pos(self, pos):
        """把游戏位置（0-3）映射到 GUI 座位（bottom / right / top / left），自己永远在底。"""
        relative = (pos - self.player_id) % 4
        # 自己 → bottom；逆时针：下家(自己+1) → right；对家(自己+2) → top；上家(自己+3) → left
        return ['bottom', 'right', 'top', 'left'][relative]

    def _seat_layout(self, seat):
        w = self.card_canvas.winfo_width() or 1200
        h = self.card_canvas.winfo_height() or 720
        if seat == 'bottom':
            return dict(orientation='horizontal', x=w // 2, y=h - 230, label_y=h - 28)
        if seat == 'top':
            return dict(orientation='horizontal', x=w // 2, y=100, label_y=70)
        # 左右对手：label 上移到画布纵向中心（≈ 中央"大王/动作牌" 的高度）
        if seat == 'left':
            return dict(orientation='vertical', x=70, y=h // 2 - 20, label_y=h // 2)
        if seat == 'right':
            return dict(orientation='vertical', x=w - 105, y=h // 2 - 20, label_y=h // 2)
        return dict(orientation='horizontal', x=w // 2, y=h // 2, label_y=h // 2)

    def _draw_level_badges(self):
        """顶部左上角：当前等级 / 本方 / 对方（act·play 三字段，整副固定）。"""
        bx, by = 10, 10
        pw = 110
        self._draw_pill(bx, by, pw, 30, '当前等级', self.cur_rank)
        self._draw_pill(bx, by + 36, pw, 30, '本方', self.self_level)
        self._draw_pill(bx, by + 72, pw, 30, '对方', self.opp_level)

        if 0 < self.current_step <= self.total_steps:
            cur = self.actions[self.current_step - 1]
            ainfo = self._parse_action(cur.get('cur_action'))
            if ainfo and (ainfo[0] or '').upper() == 'PASS':
                px = bx + pw + 8
                self.card_canvas.create_rectangle(px, by, px + 56, by + 30,
                                                  fill="#fff8c8", outline="black")
                self.card_canvas.create_text(px + 28, by + 15, text="过",
                                              font=("Microsoft YaHei", 16, "bold"),
                                              fill="black", anchor=tk.CENTER)

    def _draw_pill(self, x, y, w, h, label, value):
        self.card_canvas.create_rectangle(x, y, x + w, y + h, fill="#f5f5f5", outline="black")
        self.card_canvas.create_text(x + 8, y + h // 2, anchor=tk.W,
                                      text=label, font=("Microsoft YaHei", 11, "bold"), fill="black")
        self.card_canvas.create_text(x + w - 10, y + h // 2, anchor=tk.E,
                                      text=value, font=("Arial", 16, "bold"), fill="#cc0000")

    def _played_count(self, pos):
        n = 0
        for action in self.actions[:self.current_step]:
            if action.get('cur_pos') != pos:
                continue
            ainfo = self._parse_action(action.get('cur_action'))
            if not ainfo:
                continue
            atype, _, cards = ainfo
            if (atype or '').upper() != 'PASS' and cards:
                n += len(cards)
        return n

    def _draw_player_block(self, pos, highlight=False):
        seat = self._seat_for_pos(pos)
        layout = self._seat_layout(seat)
        cards = self.player_hands.get(str(pos), [])
        # 剩余张数：有手牌走真实长度；缺源数据（对手）走 27 - 已出
        if cards:
            remaining = len(cards)
        else:
            remaining = max(0, 27 - self._played_count(pos))

        self._draw_hand_stacked(cards, layout)

        labels = self._build_player_labels()
        self._draw_player_name_label(seat, layout, labels[pos], remaining, highlight)

    def _draw_player_name_label(self, seat, layout, label, remaining, highlight):
        fill = "#FFD700" if highlight else "white"
        bg = "#cc4400" if highlight else None
        text = f"{label}\n剩余 {remaining}"
        x = layout['x']
        y = layout['label_y']
        if bg:
            # 高亮：贴一个色块衬底
            self.card_canvas.create_rectangle(x - 80, y - 18, x + 80, y + 18,
                                              fill=bg, outline="")
        self.card_canvas.create_text(x, y, text=text, fill=fill,
                                      font=("Microsoft YaHei", 11, "bold"),
                                      anchor=tk.CENTER, justify=tk.CENTER)

    def _draw_hand_stacked(self, cards, layout):
        """按 rank 分组堆叠：横排（top/bottom）列内纵向叠；竖排（left/right）行内横向叠。"""
        cols = self._organize_hand_columns(cards)
        if not cols:
            return
        cw, ch = 54, 77            # 牌张尺寸：再加 ~1/5（45×64 → 54×77）
        if layout['orientation'] == 'horizontal':
            col_w = cw + 2
            stack_dy = 26          # 同步放大：22 → 26
            total_w = len(cols) * col_w
            sx = layout['x'] - total_w // 2
            sy = layout['y']
            for ci, (_rank, group) in enumerate(cols):
                cx = sx + ci * col_w
                for ki, card in enumerate(group):
                    cy = sy + ki * stack_dy
                    self._draw_card_normal(cx, cy, cw, ch, card, False)
        else:  # vertical
            row_h = ch + 2
            stack_dx = 18          # 同步放大：16 → 18
            total_h = len(cols) * row_h
            sy = layout['y'] - total_h // 2
            sx = layout['x']
            for ri, (_rank, group) in enumerate(cols):
                cy = sy + ri * row_h
                for ki, card in enumerate(group):
                    cx = sx + ki * stack_dx
                    self._draw_card_normal(cx, cy, cw, ch, card, False)

    # ---------------- 兼容旧入口（_draw_current_step 不再调用，但保留避免外部引用）----------------

    def _draw_player_positions(self):
        pass

    def _draw_player_hand(self, player_pos):
        pass

    def _joker_rank(self, card):
        """识别大小王：HR/SB 等格式返回 'R' 或 'B'。"""
        if not isinstance(card, str) or len(card) < 2:
            return None
        rank = card[1:]
        if rank == '1':
            rank = 'A'
        if rank in ('R', 'B'):
            return rank
        return None

    def _get_joker_photo(self, img_path, cache_key, width, height):
        """加载并缩放大小王贴图。"""
        if not img_path.is_file():
            return None
        key = (cache_key, width, height)
        if key in self._card_image_cache:
            return self._card_image_cache[key]
        try:
            from PIL import Image, ImageTk
            img = Image.open(img_path).convert("RGBA")
            img = img.resize((max(1, width), max(1, height)), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._card_image_cache[key] = photo
            return photo
        except Exception:
            return None

    def _draw_joker_fallback(self, x, y, width, height, rank):
        """贴图不可用时的矢量兜底。"""
        self.card_canvas.create_rectangle(x, y, x + width, y + height,
                                          fill="#FFFFFF", outline="black", width=1)
        joker_color = "red" if rank == 'R' else "black"
        big_char = "大" if rank == 'R' else "小"
        for i, ch in enumerate("JOKER"):
            self.card_canvas.create_text(x + 5, y + 3 + i * 12, text=ch, anchor=tk.NW,
                                         font=('Arial', 9, 'bold'), fill=joker_color)
        self.card_canvas.create_text(x + width * 0.66, y + height * 0.55,
                                     text=big_char, anchor=tk.CENTER,
                                     font=('Microsoft YaHei', 20, 'bold'), fill=joker_color)
    
    def _draw_card_normal(self, x, y, width, height, card, is_back=False):
        """绘制普通水平方向的牌（小尺寸，按 rank 堆叠场景）"""
        if is_back:
            self.card_canvas.create_rectangle(x, y, x+width, y+height,
                                            fill="#8B0000", outline="#000000", width=1)
            self.card_canvas.create_text(x+width/2, y+height/2, text="?",
                                        font=('Arial', 14, 'bold'), fill="white")
            return

        if not isinstance(card, str) or len(card) < 2:
            return

        joker_rank = self._joker_rank(card)
        if joker_rank:
            img_path = JOKER_BIG_IMG if joker_rank == 'R' else JOKER_SMALL_IMG
            cache_key = 'big' if joker_rank == 'R' else 'small'
            photo = self._get_joker_photo(img_path, cache_key, width, height)
            if photo:
                self.card_canvas.create_rectangle(x, y, x + width, y + height,
                                                  fill="#FFFFFF", outline="black", width=1)
                self.card_canvas.create_image(x + width / 2, y + height / 2,
                                              image=photo, anchor=tk.CENTER)
                return
            self._draw_joker_fallback(x, y, width, height, joker_rank)
            return

        suit = card[0]
        rank = card[1:]
        if rank == '1':
            rank = 'A'

        # 边框 + 背景
        self.card_canvas.create_rectangle(x, y, x+width, y+height,
                                        fill="#FFFFFF", outline="black", width=1)

        cx_mid = x + width / 2
        cy_mid_lower = y + height * 0.66  # 中间大花色稍偏下，避免和顶部 rank 挤

        display_rank = RANK_DISPLAY.get(rank, rank)
        display_suit = SUIT_DISPLAY.get(suit, suit)
        color = "black" if suit in ('S', 'C') else "red"

        # 左上角 rank + suit 同一行（堆叠后只露顶部也能看清是什么牌）
        rank_font = ('Arial', 14, 'bold')
        suit_font = ('Arial', 14, 'bold')
        self.card_canvas.create_text(x+3, y+1, text=display_rank, anchor=tk.NW,
                                    font=rank_font, fill=color)
        suit_x = x + (24 if display_rank == '10' else 17)
        self.card_canvas.create_text(suit_x, y+1, text=display_suit, anchor=tk.NW,
                                    font=suit_font, fill=color)
        # 中间大花色（堆叠遮挡时看不到也无所谓，顶牌完整露出时增强辨识）
        self.card_canvas.create_text(cx_mid, cy_mid_lower, text=display_suit, anchor=tk.CENTER,
                                    font=('Arial', 26, 'bold'), fill=color)
    
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
            # 游戏开始，显示有效起手（已扣进贡/加收还贡）
            info = "游戏开始 - 有效起手（已处理贡/还）\n"
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
            players = self._build_player_labels()
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
        """绘制当前动作（中央出牌区）。"""
        cur_pos = action.get('cur_pos', -1)
        cur_action = action.get('cur_action', '')

        action_info = self._parse_action(cur_action)
        if not action_info:
            self.card_canvas.create_text(self.card_canvas.winfo_width() // 2, self.card_canvas.winfo_height() // 2,
                                        text=f"动作: {cur_action}", fill="white", font=("Arial", 14), anchor=tk.CENTER)
            return

        action_type, _rank, cards = action_info
        canvas_width = self.card_canvas.winfo_width() or 1200
        canvas_height = self.card_canvas.winfo_height() or 720

        # 卡牌尺寸（出牌区跟手牌区同尺寸一致）
        card_width = 54
        card_height = 77
        spacing = 6

        cards_n = len(cards) if isinstance(cards, list) else 0
        total_width = max(0, cards_n * (card_width + spacing) - spacing)
        start_x = canvas_width // 2 - total_width // 2
        start_y = canvas_height // 2 - card_height // 2

        labels = self._build_player_labels()
        player_name = labels[cur_pos] if 0 <= cur_pos < 4 else f"未知({cur_pos})"

        action_types = {
            'Single': '单牌', 'Pair': '对子', 'Trips': '三张', 'Triple': '三张',
            'ThreeWithTwo': '三带二', 'ThreePair': '三连对', 'TwoTrips': '钢板',
            'TripsPair': '三带对', 'Straight': '顺子', 'StraightFlush': '同花顺',
            'Bomb': '炸弹', 'Rocket': '王炸',
            'Pass': '过牌', 'PASS': '过牌',
            'Tribute': '进贡', 'tribute': '进贡',
            'Back': '还贡', 'back': '还贡',
            'dispatch': '发牌'
        }
        display_type = action_types.get(action_type, action_type)

        if (action_type or '').upper() == 'PASS' or display_type == '过牌':
            # 过牌：亮红 + 黄色 halo，在深蓝背景上最显眼
            cx_pass = canvas_width // 2
            cy_pass = canvas_height // 2
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2), (-2, 2), (2, 2)):
                self.card_canvas.create_text(cx_pass + dx, cy_pass + dy,
                                              text="过", fill="#FFEB3B",
                                              font=("Microsoft YaHei", 56, "bold"),
                                              anchor=tk.CENTER)
            self.card_canvas.create_text(cx_pass, cy_pass,
                                        text="过", fill="#FF1744",
                                        font=("Microsoft YaHei", 56, "bold"), anchor=tk.CENTER)
            # PASS 标签放在"过"字下方
            self.card_canvas.create_text(canvas_width // 2, cy_pass + 50,
                                        text=f"{player_name}  {display_type}",
                                        fill="#FFD700", font=("Microsoft YaHei", 11, "bold"),
                                        anchor=tk.CENTER)
        elif isinstance(cards, list) and cards:
            for i, card in enumerate(cards):
                cx = start_x + i * (card_width + spacing)
                self._draw_card_normal(cx, start_y, card_width, card_height, card, False)
            # 出牌动作标签：放在中央牌张下方（避免被玩家 0 的手牌遮挡）
            self.card_canvas.create_text(canvas_width // 2, start_y + card_height + 16,
                                        text=f"{player_name}  {display_type}",
                                        fill="#FFD700", font=("Microsoft YaHei", 11, "bold"),
                                        anchor=tk.CENTER)
        else:
            self.card_canvas.create_text(canvas_width // 2, canvas_height // 2,
                                        text=display_type, fill="#FFFFFF",
                                        font=("Microsoft YaHei", 24, "bold"), anchor=tk.CENTER)
            self.card_canvas.create_text(canvas_width // 2, canvas_height // 2 + 38,
                                        text=player_name,
                                        fill="#FFD700", font=("Microsoft YaHei", 11, "bold"),
                                        anchor=tk.CENTER)
    
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