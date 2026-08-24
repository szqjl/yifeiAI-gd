# -*- coding: utf-8 -*-
"""
Ultimate Win Rate Decision Engine V7
终极胜率导向决策引擎 V7版本
基于终极胜率导向训练模型的决策引擎
"""

try:
    import torch
    import torch.nn as nn
except ImportError:
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
import numpy as np
import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from game_logic.guandan_constants import DEFAULT_REST_CARDS
except ImportError:
    DEFAULT_REST_CARDS = 27

# 特征工程（与 bc_dataset.py 训练管线对齐）
try:
    from src.v.nn.features.static_features import (
        extract_static_features, STATIC_STATE_DIM,
        extract_state_belief, BELIEF_DIM,
    )
    from src.v.nn.features.dynamic_features import extract_dynamic_features, DYNAMIC_HIDDEN_DIM
    from src.v.nn.features.memory_tracker import MemoryTracker, MEMORY_TRACKER_DIM, MEMORY_TRACKER_DIM_V061
    FEATURE_IMPORT_OK = True
except ImportError as e:
    FEATURE_IMPORT_OK = False
    print(f"[Warning] 特征工程导入失败: {e}, 使用简化特征")

# GUA-045 Guard 接入（2026-06-17 修复）
# v7_guards.py 实施完成但生产代码未接入 → GUA-045 实施不完整
# 接入点：decide() 入口 filter_action_list，模型决策后 validate_decision 二次校验
try:
    from src.v.nn.guards.v7_guards import filter_action_list, validate_decision
    GUARD_IMPORT_OK = True
except ImportError as e:
    GUARD_IMPORT_OK = False
    print(f"[Warning] Guard 导入失败: {e}, 使用规则回退（无 Guard）")

TARGET_FEATURE_DIM = 512  # 与 bc_dataset.py 一致

class UltimateWinRateEngineV7:
    """
    终极胜率导向决策引擎 V7
    使用训练好的终极胜率导向模型进行决策

    特征管线（与 bc_dataset.py 训练对齐）：
      0-123:   extract_static_features (124)
      124-187: extract_dynamic_features (64)
      188-195: extract_state_belief (8)  — GUA-050
      196-228: MemoryTracker.state_vector (33) — GUA-052 24 + GUA-054 9 (grouping_scanner)
      196-243: MemoryTracker.state_vector (48) — GUA-052 24 + GUA-061 24 (grouping_engine, v3)
    """

    def __init__(self, player_id: int = 0, use_grouping_engine: bool = False):
        self.player_id = player_id
        self.logger = logging.getLogger(f"UltimateWinRateEngineV7.{player_id}")

        # GUA-061: 组牌引擎开关（训练后用 bc_model_v3.pth 时开启）
        self.use_grouping_engine = use_grouping_engine

        # 设备（必须在 _load_model 前设置；规则栈路径仍可能用到 device）
        # GUA-208：torch 可选导入（Botzone 在线部署无 torch 环境时 model 恒为
        # None，规则栈路径完全不依赖 torch，仅保留 device 占位以兼容 _load_model）。
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if torch is not None else 'cpu'

        # ── BC 权重挂载（已停用 · 2026-07-10）──────────────────────────────
        # 战略口径：GUA-064/071 + 推荐法主路径；bc_model_v3 非必须，缺文件/挂上
        # 均走规则栈。回滚：恢复下方 model_path 赋值，并改 _load_model 为真正加载。
        # if use_grouping_engine:
        #     self.model_path = Path(__file__).parent.parent.parent.parent / "models" / "v-nn" / "bc_model_v3.pth"
        # else:
        #     self.model_path = Path(__file__).parent.parent.parent.parent / "models" / "v-nn" / "bc_model_v2.pth"
        self.model_path = None
        self.model = None  # 强制规则栈 / GUA-075 推荐 / heuristic；不加载 BC
        # self._load_model()
        self.logger.info(
            "BC 权重挂载已禁用（model=None）；决策走推荐法+规则栈。"
            " 组牌引擎 use_grouping_engine=%s",
            use_grouping_engine,
        )

        # 决策统计
        self.decision_count = 0
        self.model_decisions = 0
        self.fallback_decisions = 0
        self.heuristic_decisions = 0  # GUA-071 heuristic 选择次数
        self.heuristic_override_count = 0  # GUA-071 组局一致性强行覆盖 NN 的次数
        # GUA-045 Guard 统计（2026-06-17 接入）
        self.guard_filtered_count = 0
        self.guard_validated_count = 0
        self.guard_override_count = 0

        # GUA-052: MemoryTracker 实例（跨决策状态）
        self._tracker = None
        self._tracker_initialized = False
        self._tracker_history_replayed: int = 0

        # ── GUA-063: 组牌→出牌衔接（2026-06-18）────
        # 每次 decide() 前跑一次 enumerate_groupings()，缓存以下产物：
        self._card_mask: Optional[Dict[str, tuple]] = None   # card → (group_id, is_core, group_size)
        self._group_members: Dict[int, List[str]] = {}       # group_id → 牌列表（multiset 真源）
        self._current_role: str = "主攻"                      # 角色（主攻/助攻/超强主攻/超弱）
        self._anchor_role: Optional[str] = None               # GUA-079: 初始 role 锚（主攻以上锁定，不随重算退化）
        self._best_plan = None                                 # 最优方案 GroupingPlan
        self._all_plans: List[Any] = []                         # GUA-234 C：Top3 缓存
        self._active_plan = None                                 # GUA-234 C：当前决策 plan
        self._grouping_features: Optional[np.ndarray] = None   # 24 维组牌特征（进 NN）
        self._last_hand_hash: int = -1                         # 手牌 hash，用于判断是否需要重跑引擎
        # GUA-063 中局重分组触发标记
        self._core_broken_since_regroup: bool = False          # 核心牌型被破后标记
        # GUA-063 过滤统计
        self.group_filtered_count: int = 0
        self.group_filter_bypass_count: int = 0
        # 残局管线统计
        self._endgame_activated_count: int = 0
        self._endgame_hit_count: int = 0
        # GUA-075 记录增强: 每步决策的管线层 / 模型置信度 / 候选数
        self._last_decision_layer: Optional[str] = None
        self._last_decision_score: Optional[float] = None
        self._last_decision_candidates: int = 0
        self._last_heuristic_scores: List[Tuple[int, float]] = []
        self._last_model_scores: List[Tuple[int, float]] = []
        self._active_replay_trace: Optional[Dict[str, Any]] = None
        self._dispatch_stage_count: int = 0  # GUA-089 阶段调度次数计数
        self._last_nn_confidence: Optional[float] = None  # _model_decision 内部写入
        # GUA-063 Phase 3: 中局重分组触发追踪
        self._prev_hand_size: int = 27
        self._regroup_triggered_count: int = 0
        # 决议 8: 接风跟线 — 记忆队友末手牌型
        self._teammate_last_trick_type: Optional[str] = None   # "Pair"/"Bomb"/"StraightFlush" 等
        # GUA-234: 动态组牌门禁 + 中期队友需求观测
        self._score_tier: Optional[str] = None
        self._power_gate_tier: Optional[str] = None
        self._dynamic_regroup_enabled: bool = True
        self._mid_feed_tracker = None  # MidgameTeammateDemandTracker，lazy
        self._mid_feed_P: Optional[List[str]] = None
        self._last_greater_key: Optional[Tuple[Any, ...]] = None
        # 决议 10: 投喂策略 — 5 张反馈路径状态
        self._feed_five_card_tried: bool = False                # 是否已试探过 5 张类牌型
        # 决议 6: 组牌类型映射 — group_id → 牌型字符串
        self._group_type_map: Dict[int, str] = {}
        self._decision_tracer = None
        self._trace_game_id: Optional[str] = None
        self._last_trace_path: Optional[str] = None
        self._last_stage_intent: Optional[str] = None

    def on_game_start(self, my_pos: int = None, game_id: Optional[str] = None):
        """每局开始时清理跨副残留状态（R11记忆/R15相克锁/MemoryTracker等）。"""
        if my_pos is not None:
            # 动态座位回写（GUA-205 支线1 顺带修复）：构造时 player_id 仅为
            # 启动默认，实际座位以 deal 的 your_id 为准（Botzone 对局可能是
            # 0/1/2/3），否则 DecisionTracer / trace 文件名等会记录错误座位。
            self.player_id = my_pos
        if GUARD_IMPORT_OK:
            try:
                from src.v.nn.guards.v7_guards import _clear_r11_memory_for_game
                _clear_r11_memory_for_game(my_pos)
            except Exception:
                pass
        self._card_mask = None
        self._group_members = {}
        self._current_role = "主攻"
        self._anchor_role = None
        self._best_plan = None
        self._all_plans = []
        self._active_plan = None
        self._grouping_features = None
        self._last_hand_hash = -1
        self._core_broken_since_regroup = False
        self._prev_hand_size = 27
        self._regroup_triggered_count = 0
        self._teammate_last_trick_type = None
        self._feed_five_card_tried = False
        self._score_tier = None
        self._power_gate_tier = None
        self._dynamic_regroup_enabled = True
        self._mid_feed_P = None
        self._last_greater_key = None
        if self._mid_feed_tracker is not None:
            self._mid_feed_tracker.reset()
        self._group_type_map = {}
        self._group_members = {}
        self._tracker = None
        self._tracker_initialized = False
        self._tracker_history_replayed = 0
        self._last_stage_intent = None
        self._last_heuristic_scores = []
        self._last_model_scores = []
        self._active_replay_trace = None
        self._trace_game_id = game_id
        self._last_trace_path = None
        self._decision_tracer = None
        if self._is_decision_trace_enabled():
            try:
                from src.v.nn.tracing.decision_trace import DecisionTracer

                trace_game_id = game_id or f"trace_{int(time.time() * 1000)}_{self.player_id}"
                self._decision_tracer = DecisionTracer(
                    my_pos=self.player_id,
                    game_id=trace_game_id,
                    enable=True,
                )
                self._trace_game_id = trace_game_id
            except Exception as e:
                self.logger.debug("decision tracer init skip: %s", e)
                self._decision_tracer = None

    def flush_decision_trace(self) -> Optional[str]:
        """GUA-098：局末落盘 DecisionTracer。"""
        tracer = self._decision_tracer
        if tracer is None:
            return None
        try:
            fp = tracer.flush_to_jsonl()
        except Exception as e:
            self.logger.debug("decision tracer flush skip: %s", e)
            return None
        if fp is None:
            return None
        self._last_trace_path = str(fp)
        return self._last_trace_path

    @staticmethod
    def _is_decision_trace_enabled() -> bool:
        return os.environ.get("V7_ENABLE_DECISION_TRACE", "0").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )

    @staticmethod
    def _is_stage2_dispatch_enabled() -> bool:
        return os.environ.get("V7_ENABLE_STAGE2_DISPATCH", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )

    def _trace_begin_step(self, game_state: Dict[str, Any], action_list: List) -> None:
        tracer = self._decision_tracer
        if tracer is None:
            return
        try:
            from src.v.nn.tracing.decision_trace import format_joker_signal_line

            hand_cards = game_state.get("handCards", []) or []
            tracer.begin_step(
                hand_size=len(hand_cards) if hand_cards else 27,
                cur_rank=str(game_state.get("curRank", "2")),
                stage=str(game_state.get("_current_stage", "")),
                cur_pos=int(game_state.get("curPos", -1) or -1),
                greater_pos=int(game_state.get("greaterPos", -1) or -1),
            )
            tracer.record_layer1(
                source="MemoryTracker",
                payload={
                    "tracker_ready": self._tracker is not None,
                    "history_replayed": self._tracker_history_replayed,
                },
            )
            belief = game_state.get("_belief") or {}
            joker_signal = belief.get("joker_signal")
            if joker_signal:
                tracer.record_joker_signal(joker_signal)
                self.logger.info(
                    "%s stage=%s curPos=%s greaterPos=%s",
                    format_joker_signal_line(joker_signal),
                    game_state.get("_current_stage", ""),
                    game_state.get("curPos", -1),
                    game_state.get("greaterPos", -1),
                )
            tracer.record_layer1(
                source="belief",
                payload={
                    "opp_bomb_risks": belief.get("opp_bomb_risks", {}),
                    "hand_counts": belief.get("hand_counts", {}),
                    "can_opp_suppress_current": belief.get("can_opp_suppress_current"),
                    "hr_played": belief.get("hr_played"),
                    "hr_remain": belief.get("hr_remain"),
                    "sb_played": belief.get("sb_played"),
                    "sb_remain": belief.get("sb_remain"),
                },
            )
            phase_relation = game_state.get("_phase_relation") or {}
            if phase_relation:
                tracer.record_layer2(
                    ip_id="GUA-094.phase_relation",
                    delta=float(phase_relation.get("enemy_bomb_risk_max", 0.0) or 0.0),
                    oppo=f"p{phase_relation.get('critical_enemy_seat', '?')}",
                    comment=str(
                        {
                            "enemy_shape_hint": phase_relation.get("enemy_shape_hint"),
                            "teammate_cover_confidence": phase_relation.get(
                                "teammate_cover_confidence"
                            ),
                            "same_type_suppressor_outside": phase_relation.get(
                                "same_type_suppressor_outside"
                            ),
                            "sprint_fire_ready": phase_relation.get("sprint_fire_ready"),
                            "natural_turn_count": phase_relation.get("natural_turn_count"),
                            "single_residue": phase_relation.get("single_residue"),
                        }
                    ),
                )
            tracer.record_guard(
                rule_id="action_list_size",
                filtered_count=max(0, len(action_list) - 1),
                reason=f"candidates={len(action_list)}",
            )
        except Exception as e:
            self.logger.debug("decision trace begin skip: %s", e)

    def _prefer_stronger_same_cards_action(
        self, act_index: int, action_list: List, game_state: Optional[Dict[str, Any]] = None,
    ) -> int:
        """GUA-161：同牌同时可声明 StraightFlush 时禁止选择 Straight。

        GUA-232: 自由领出（greaterPos 为自己的新轮）时禁止升级——同花顺是炸弹，
        领出禁炸（R10）；只有跟压/残局（game_state 明确非自由领出）才允许升级。
        game_state=None 时保持旧行为（升级）以兼容既有调用。
        """
        if not 0 <= act_index < len(action_list):
            return act_index
        chosen = action_list[act_index]
        if not isinstance(chosen, list) or len(chosen) < 3:
            return act_index
        if chosen[0] != "Straight" or not isinstance(chosen[2], list):
            return act_index

        # GUA-232: 自由领出禁升级自然同花顺（同花顺=炸弹，R10 领出禁炸）。
        # 野生同花顺（含逢人配 H{cur_rank}）牌力等同自然同花顺，允许升级。
        if game_state is not None:
            my_pos = game_state.get("myPos", self.player_id)
            greater_pos = game_state.get("greaterPos", -1)
            cur_pos = game_state.get("curPos", -1)
            is_free_lead = (cur_pos == -1) or (greater_pos in (-1, my_pos))
            if is_free_lead:
                cur_rank = game_state.get("curRank", "")
                wild_card = f"H{cur_rank}" if cur_rank else ""
                chosen_has_wild = wild_card and wild_card in [str(c) for c in chosen[2]]
                if not chosen_has_wild:
                    self.logger.info(
                        "GUA-232 自由领出禁升级自然同花顺: Straight idx=%d → 保持 Straight",
                        act_index,
                    )
                    return act_index
                self.logger.info(
                    "GUA-232 野生同花顺允许升级: Straight idx=%d 含 %s，继续升级",
                    act_index, wild_card,
                )

        from collections import Counter

        chosen_cards = Counter(str(card) for card in chosen[2])
        for index, action in enumerate(action_list):
            if not isinstance(action, list) or len(action) < 3:
                continue
            if action[0] != "StraightFlush" or not isinstance(action[2], list):
                continue
            if Counter(str(card) for card in action[2]) != chosen_cards:
                continue
            self.logger.info(
                "GUA-161 同牌强声明升级: Straight idx=%d → StraightFlush idx=%d cards=%s",
                act_index, index, list(chosen_cards.elements()),
            )
            self._replay_record(
                "gua161_stronger_declaration",
                {"from_index": act_index, "to_index": index, "cards": list(chosen_cards.elements())},
            )
            return index
        return act_index
    def _trace_finalize(
        self, act_index: int, action_list: List, game_state: Optional[Dict[str, Any]] = None,
    ) -> int:
        act_index = self._prefer_stronger_same_cards_action(act_index, action_list, game_state)
        chosen_action = (
            action_list[act_index]
            if 0 <= act_index < len(action_list)
            else []
        )
        if (
            isinstance(chosen_action, list)
            and len(chosen_action) >= 3
            and isinstance(chosen_action[2], list)
            and self._group_members
        ):
            chosen_cards = [str(card) for card in chosen_action[2]]
            memberships = self._build_card_memberships(self._group_members)
            multi_memberships = {
                card: memberships[card]
                for card in sorted(set(chosen_cards))
                if card in memberships
                and (
                    len(memberships[card]) > 1
                    or sum(memberships[card].values()) > 1
                )
            }
            if multi_memberships:
                allocation, broken_group_ids = self._best_group_allocation(
                    chosen_cards,
                    self._card_mask or {},
                    self._group_type_map or {},
                    self._group_members,
                )
                trace_payload = {
                    "action": chosen_action,
                    "memberships": multi_memberships,
                    "allocation": allocation,
                    "broken_types": [
                        (self._group_type_map or {}).get(group_id, "unknown")
                        for group_id in broken_group_ids
                    ],
                }
                self.logger.info(
                    "GUA-154 多实例分配: action=%s memberships=%s allocation=%s broken=%s",
                    chosen_action[:3],
                    multi_memberships,
                    allocation,
                    trace_payload["broken_types"],
                )
                self._replay_record("gua154_memberships", trace_payload)
        self._replay_record(
            "final",
            {
                "actIndex": act_index,
                "chosen_action": chosen_action,
                "layer": self._last_decision_layer,
                "score": self._last_decision_score,
                "intent": self._last_stage_intent,
            },
        )
        tracer = self._decision_tracer
        if tracer is not None:
            try:
                if self._last_stage_intent:
                    tracer.record_decision_intent(
                        self._last_stage_intent,
                        payload={
                            "layer": self._last_decision_layer,
                            "trace_game_id": self._trace_game_id,
                        },
                    )
                tracer.end_step(actIndex=act_index, chosen_action=chosen_action)
            except Exception as e:
                self.logger.debug("decision trace finalize skip: %s", e)
        return act_index

    # ── GUA-171: 检测刚用炸弹抢到领出权 ──
    @staticmethod
    def _just_bombed_and_won_lead(game_state: Dict[str, Any]) -> bool:
        """检测上一手是否为自己用炸弹/同花顺抢到领出权。

        Returns:
            True 如果本轮是自己的领出权且上一手是自己的炸弹。
        """
        my_pos = game_state.get("myPos", 0)
        cur_pos = game_state.get("curPos", -1)
        # 领出：curPos=-1 或 curPos=myPos 且 greaterPos=-1
        is_my_lead = (
            cur_pos == my_pos
            or (cur_pos in (-1, None) and game_state.get("greaterPos", -1) in (-1, my_pos))
        )
        if not is_my_lead:
            return False

        # 从 actions 取最近一条动作
        actions = game_state.get("actions", [])
        if not actions:
            return False
        last_action_entry = actions[-1]
        if last_action_entry.get("cur_pos") != my_pos:
            return False
        last_action = last_action_entry.get("cur_action", [])
        if not last_action or last_action[0] in ("PASS", None, ""):
            return False
        # 判断是否为炸弹/同花顺
        if last_action[0] in ("Bomb", "StraightFlush"):
            return True
        # 也检查 v7 内部声明的 bomb-like
        try:
            from .endgame.endgame_decide import _is_bomb_like_action
            if _is_bomb_like_action(last_action):
                return True
        except Exception:
            pass
        return False

    def _replay_record(self, stage: str, payload: Dict[str, Any]) -> None:
        """仅供 YF_REPLAY 离线分析；实战未注入 trace 时为 no-op。"""
        trace = getattr(self, "_active_replay_trace", None)
        if trace is None:
            return
        trace.setdefault("pipeline", []).append({"stage": stage, **payload})

    def _load_model(self):
        """加载终极胜率导向模型（当前停用：不挂 bc_model_v3/v2）。

        回滚时恢复 __init__ 中 model_path + self._load_model() 调用，并还原本方法体。
        """
        self.model = None
        self.logger.info("跳过 BC 权重加载（_load_model 已禁用）")
        return False
        # --- 以下为原加载逻辑（保留备查，勿删）---
        # try:
        #     if not self.model_path or not self.model_path.exists():
        #         self.logger.warning(f"[警告] 终极胜率导向模型未找到！模型路径: {self.model_path}")
        #         self.logger.warning("将使用规则引擎作为回退")
        #         return False
        #     checkpoint = torch.load(self.model_path, map_location=self.device)
        #     from src.train.ultimate_win_rate_training import UltimateWinRateNet
        #     self.model = UltimateWinRateNet().to(self.device)
        #     if 'model_state_dict' in checkpoint:
        #         self.model.load_state_dict(checkpoint['model_state_dict'])
        #     else:
        #         self.model.load_state_dict(checkpoint)
        #     self.model.eval()
        #     self.logger.info(f"✓ 终极胜率导向模型加载成功: {self.model_path}")
        #     return True
        # except Exception as e:
        #     self.logger.error(f"✗ 模型加载失败: {e}")
        #     self.model = None
        #     return False
    
    # ── GUA-075 推荐路径统计 ──
    recommend_count: int = 0        # 推荐器尝试次数
    recommend_hit_count: int = 0    # 推荐命中次数
    recommend_valid_count: int = 0  # 推荐通过校验次数
    # 匹配失败分类计数器
    _match_fail_type_mismatch: int = 0      # 推荐 type 不在 actionList 中
    _match_fail_rank_mismatch: int = 0      # type 匹配但 rank 不匹配
    _match_fail_cards_mismatch: int = 0     # type+rank 匹配但 cards 不匹配

    def decide(self, game_state: Dict[str, Any]) -> int:
        """
        做出决策

        GUA-075 流程（2026-06-20，GUA-078 2026-06-21 修订）：
          ① 组牌引擎 → ①b MemoryTracker（decide 入口）→ ② numofplayers
          → ③ 接风记忆 → ④ MemoryTracker 注入 game_state
          ═══════════ 【NEW】主路径 ═══════════
          ⑤ _recommend_play() → 推荐方案
          ⑥ _match_actionList() → 在原始 actionList 中匹配
          ⑦ Guard 硬规则快速校验 → 通过 → return actIndex ✅
          ═══════════ 回退路径（不变）═══════════
          Guard filter → group_consistency → wind/feeding → NN → validate → heuristic → return

        Args:
            game_state: 游戏状态

        Returns:
            选择的动作索引（原始 actionList 下标）
        """
        self.decision_count += 1
        self._last_stage_intent = None
        self._last_heuristic_scores = []
        self._last_model_scores = []
        replay_trace = game_state.get("_replay_trace")
        self._active_replay_trace = replay_trace if isinstance(replay_trace, dict) else None
        if self._active_replay_trace is not None:
            self._active_replay_trace.clear()
            self._active_replay_trace["pipeline"] = []

        action_list = game_state.get("actionList", [])
        self._replay_record("input", {"candidate_count": len(action_list)})
        if not action_list:
            return self._trace_finalize(0, action_list, game_state)

        # ── ① 组牌引擎 ──
        self._run_grouping_engine(game_state)
        self._replay_record(
            "grouping",
            {
                "gua_id": "GUA-063",
                "role": self._current_role,
                "group_type_map": dict(self._group_type_map or {}),
            },
        )

        # ── GUA-XXX: 重建被平台截断的组合动作 ──
        self._reconstruct_truncated_actions(game_state, action_list)

        # ── ①b MemoryTracker（GUA-078：残局 numofplayers 须在注入前就绪）──
        self._ensure_memory_tracker_for_decide(game_state)

        # ── ② 注入 numofplayers ──
        self._inject_numofplayers(game_state)

        # ── ②b GUA-244 注入剩余池（对手残牌构成推理，校验失败回退 None）──
        self._inject_remaining_pool(game_state)

        # ── ②c GUA-072 规则记牌信念（供 heuristic / 推荐器）──
        self._inject_belief_vector(game_state)

        # ── ②d GUA-094 规则版推断层（供 stage_2 / trace 后续消费）──
        self._inject_phase_relation(game_state)
        if self._active_replay_trace is not None:
            self._replay_record(
                "memory",
                {
                    "gua_ids": ["GUA-072", "GUA-094"],
                    "belief": game_state.get("_belief") or {},
                    "phase_relation": game_state.get("_phase_relation") or {},
                    "hand_counts": list(getattr(self._tracker, "hand_counts", []) or []),
                },
            )

        # ── ②d GUA-089 阶段调度（§7.4 伪代码落地）──
        # 按当前手牌张数切 4 阶段，存入 game_state['_current_stage']
        # 与 STAGE_RULE_MAP / STAGE_ENGINE_MAP 一道，供后续 _recommend_play / 下游 GUA-090/091/092 消费
        try:
            from src.v.nn.dispatcher import _dispatch_by_stage, stage_description
            _hand_cards = game_state.get("handCards", []) or []
            _hand_size = len(_hand_cards) if _hand_cards else 27
            _cur_rank = game_state.get("curRank", "2")
            _stage = _dispatch_by_stage(_hand_size, _cur_rank)
            game_state["_current_stage"] = _stage
            self._last_decision_layer = (
                "GUA-089_" + _stage + "(" + stage_description(_stage) + ")"
            ) if not self._last_decision_layer else (
                self._last_decision_layer + "|GUA-089_" + _stage
            )
            self._dispatch_stage_count += 1
        except Exception as e:
            self.logger.warning("GUA-089 阶段调度异常: %s, 默认 stage_1", e)
            game_state["_current_stage"] = "stage_1"
        self._trace_begin_step(game_state, action_list)

        # ── ③ 接风跟线记忆 ──
        self._update_teammate_last_trick(game_state)
        # ── ③b GUA-234 中期队友需求观测（只写字段/日志，不改出牌）──
        self._update_midgame_teammate_demand(game_state)
        # ── ③c GUA-234 C：Top3 局面触发重评分（切换 active_plan / card_mask）──
        self._evaluate_replan_candidates(game_state)

        # ── ④ MemoryTracker 注入 ──
        if self._tracker is not None:
            game_state["_memory_tracker"] = self._tracker

        # ══════════════ ★ 残局管线：预处理 + Q0→Q3 决策 ══════════════
        # 注入点：_inject_numofplayers 之后，GUA-075 主路径之前
        # GUA-113: 残局 Q1 消费组牌 role（超弱/助攻让道队友控牌）
        game_state["_role"] = self._current_role or "主攻"

        # ── GUA-171: 炸后领出连续性 ──
        if self._just_bombed_and_won_lead(game_state):
            nop = game_state.get("numofplayers", [27, 27, 27, 27])
            if any(1 <= n <= 10 for n in nop):
                self.logger.info("GUA-171: 炸后领出 + 有人进残局 → 端局管线决策")
            else:
                self.logger.info("GUA-171: 炸后领出 + 无人进残局 → GUA-075 普通领出")

        # GUA-080: 注入组牌数据到 game_state，预处理器需要 _group_type_map 做冲刺判定
        if self._card_mask and self._group_type_map:
            # 转换 gid→type 为 type→count（预处理器格式）
            type_counts: Dict[str, int] = {}
            for gid, gtype in self._group_type_map.items():
                type_counts[gtype] = type_counts.get(gtype, 0) + 1
            # 散牌（gid=-1）也算一组
            scatter_count = sum(1 for v in self._card_mask.values() if v[0] == -1)
            if scatter_count > 0:
                type_counts["scatter"] = scatter_count
            game_state["_group_type_map"] = type_counts
        if self._card_mask:
            game_state["_card_mask"] = self._card_mask
        if self._group_type_map:
            game_state["_group_gid_type_map"] = dict(self._group_type_map)
        if self._group_members:
            game_state["_group_members"] = self._group_members
        # 若残局命中 → 直接返回；未命中 → 继续 GUA-075 + Guard + NN + heuristic
        try:
            from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor
            from src.v.nn.endgame.endgame_decide import EndgameDecider
            EndgamePreprocessor().preprocess(game_state)
            ec = game_state.get("_endgame_context", {})
            self._replay_record(
                "endgame",
                {"active": bool(ec.get("is_active")), "context": ec},
            )
            if ec.get("is_active"):
                try:
                    from src.v.nn.endgame.endgame_decide import (
                        _is_following_enemy_bomb_control,
                        find_latent_bomb_like_beaters_not_in_action_list,
                    )
                    if _is_following_enemy_bomb_control(game_state):
                        latent = find_latent_bomb_like_beaters_not_in_action_list(
                            game_state.get("handCards") or [],
                            str(game_state.get("curRank", "2")),
                            game_state.get("greaterAction"),
                            action_list,
                        )
                        if latent:
                            self.logger.warning(
                                "GUA-124: 组牌可压敌炸但 actionList 未枚举 latent=%s",
                                latent[:2],
                            )
                except Exception as diag_err:
                    self.logger.debug("GUA-124 诊断跳过: %s", diag_err)
                self._endgame_activated_count += 1
                decider = EndgameDecider()
                # 保存原始 action_list 用于索引映射
                original_action_list = list(action_list)
                team_small_single = decider.pick_double_second_small_single(
                    game_state, original_action_list,
                )
                if team_small_single[0] is None:
                    team_small_single = decider.pick_teammate_sprint_small_single(
                        game_state, original_action_list,
                    )
                if team_small_single[0] is not None:
                    endgame_idx, endgame_act = team_small_single
                else:
                    action_list, banned_empty = decider.apply_banned_filter(action_list, game_state)
                    if banned_empty:
                        endgame_idx, endgame_act = decider.decide(game_state, original_action_list)
                    else:
                        endgame_idx, endgame_act = decider.decide(game_state, action_list)
                # 命中 → 找原始 actionList 中的下标
                if endgame_idx is not None and endgame_act is not None:
                    for orig_i, a in enumerate(original_action_list):
                        if a == endgame_act:
                            # GUA-078: 残局管线命中后过 _group_consistency_filter
                            # 残局管线不感知 card_mask，可能拆炸弹/钢板 core
                            # 若 filter 拦截 → 不 return，继续走 GUA-075 主路径
                            _, filter_map = self._group_consistency_filter(
                                original_action_list, game_state,
                            )
                            # GUA-239：多手自由领出先单试探（拆 SF 核心）→ 消费标记并豁免
                            gua239_probe = bool(
                                game_state.pop("_gua239_single_probe", False))
                            if orig_i < len(filter_map) and filter_map[orig_i] == -1:
                                if not gua239_probe:
                                    self.logger.warning(
                                        "残局管线命中但被_group_consistency_filter拦截: actIndex=%d cards=%s → 回退GUA-075",
                                        orig_i,
                                        endgame_act[2] if len(endgame_act) >= 3 and isinstance(endgame_act[2], list) else endgame_act[:3],
                                    )
                                    break  # 跳出 for（不触发 else），不 return，继续走到 GUA-075

                            self._endgame_hit_count += 1
                            self.logger.info(
                                "残局管线命中: actIndex=%d cards=%s",
                                orig_i,
                                endgame_act[2] if len(endgame_act) >= 3 and isinstance(endgame_act[2], list) else endgame_act[:3],
                            )
                            self._last_decision_layer = "残局管线"
                            self._last_decision_score = None
                            self._last_decision_candidates = len(original_action_list)
                            self._last_stage_intent = "endgame_pipeline"
                            self._replay_record(
                                "endgame_hit",
                                {"actIndex": orig_i, "action": endgame_act},
                            )
                            return self._trace_finalize(orig_i, original_action_list, game_state)
                    else:
                        self.logger.warning("残局决策未在原始 actionList 中匹配到: %s", endgame_act[:3] if len(endgame_act) >= 3 else endgame_act)
                # 残局未命中 → 恢复 action_list（已过滤 banned）→ 继续 GUA-075
        except Exception as e:
            self.logger.warning("残局管线异常: %s，回退正常管线", e)

        # ══════════════ ⑤-⑦ GUA-075 主路径：推荐 + 匹配 + 校验 ══════════════
        try:
            recommendation = self._recommend_play(game_state, action_list)
            self._replay_record(
                "recommendation",
                {"gua_id": "GUA-075", "recommendation": recommendation},
            )
            if recommendation:
                self.recommend_count += 1
                act_index = self._match_actionList(recommendation, action_list)
                if act_index >= 0:
                    self._replay_record(
                        "recommendation_match",
                        {"gua_id": "GUA-075", "actIndex": act_index},
                    )
                    self.recommend_hit_count += 1
                    # ── ⑦ Guard 硬规则快速校验 ──
                    if self._quick_guard_validate(act_index, action_list, game_state):
                        self._replay_record(
                            "recommendation_guard",
                            {"gua_id": "GUA-075", "passed": True},
                        )
                        # GUA-075 fix: card_mask 组牌一致性保护
                        # 原路径跳过了 _group_consistency_filter，必须在此补检
                        # 推荐动作拆炸弹/同花顺 → 拦截回退
                        blocked_by_mask = False
                        if self._card_mask and self._group_type_map:
                            broken = self._get_broken_core_type(
                                action_list[act_index],
                                self._card_mask,
                                self._group_type_map,
                                self._group_members,
                            )
                            if broken in ("Bomb", "StraightFlush"):
                                from src.v.nn.endgame.endgame_decide import (
                                    should_allow_counter_bomb_core_exempt,
                                )
                                if not should_allow_counter_bomb_core_exempt(
                                    action_list[act_index], game_state,
                                ):
                                    if recommendation.get("type") in ("Bomb", "StraightFlush"):
                                        # GUA-211: 炸弹/SF 拆核心被拦 → 回退找不拆核心的同类 Bomb/SF
                                        alt_idx = self._find_alternative_core_intact_bomb(
                                            action_list, act_index,
                                            self._card_mask,
                                            self._group_type_map,
                                            self._group_members,
                                            game_state.get("greaterAction", []),
                                            str(game_state.get("curRank", "2")),
                                        )
                                        if alt_idx >= 0 and alt_idx != act_index:
                                            act_index = alt_idx
                                            rec_type = action_list[alt_idx][0] if len(action_list[alt_idx]) >= 1 else ""
                                            rec_rank = action_list[alt_idx][1] if len(action_list[alt_idx]) >= 2 else ""
                                            self.logger.info(
                                                "GUA-211: 推荐 %s/%s 拆 %s → 改出完整核心 %s/%s actIndex=%d",
                                                recommendation.get("type"), recommendation.get("rank"),
                                                broken, rec_type, rec_rank, alt_idx)
                                            self._replay_record(
                                                "recommendation_mask",
                                                {
                                                    "gua_id": "GUA-211",
                                                    "blocked": False,
                                                    "broken_type": broken,
                                                    "alt_actIndex": alt_idx,
                                                },
                                            )
                                        else:
                                            self.logger.info(
                                                "GUA-211: 推荐 %s/%s 拆 %s → 无完整核心 Bomb/SF 替代, 回退",
                                                recommendation.get("type"), recommendation.get("rank"), broken)
                                            blocked_by_mask = True
                                            self._replay_record(
                                                "recommendation_mask",
                                                {
                                                    "gua_id": "GUA-211",
                                                    "blocked": True,
                                                    "broken_type": broken,
                                                },
                                            )
                                    else:
                                        # GUA-176: 推荐非炸弹拆 Bomb/SF core → 改出其他不拆核动作
                                        alt_idx = self._find_alternative_non_core_breaking_action(
                                            action_list, act_index,
                                            self._card_mask,
                                            self._group_type_map,
                                            self._group_members,
                                            game_state.get("greaterAction", []))
                                        if alt_idx >= 0 and alt_idx != act_index:
                                            act_index = alt_idx
                                            rec_type = action_list[alt_idx][0] if len(action_list[alt_idx]) >= 1 else ""
                                            rec_rank = action_list[alt_idx][1] if len(action_list[alt_idx]) >= 2 else ""
                                            self.logger.info(
                                                "GUA-176: 推荐 %s/%s 拆 %s → 改出 %s/%s actIndex=%d",
                                                recommendation.get("type"), recommendation.get("rank"),
                                                broken, rec_type, rec_rank, alt_idx)
                                        else:
                                            self.logger.info(
                                                "GUA-176: 推荐 %s/%s 拆 %s → 无替代非炸不拆核动作, 回退",
                                                recommendation.get("type"), recommendation.get("rank"), broken)
                                            blocked_by_mask = True
                                            self._replay_record(
                                                "recommendation_mask",
                                                {
                                                    "gua_id": "GUA-176",
                                                    "blocked": True,
                                                    "broken_type": broken,
                                                },
                                            )
                        if not blocked_by_mask:
                            self.recommend_valid_count += 1
                            self.logger.info(
                                "GUA-075 主路径: recommend=%s/%s → actIndex=%d ✅",
                                recommendation.get("type"), recommendation.get("rank"), act_index)
                            self._last_decision_layer = "GUA-075推荐"
                            self._last_decision_score = None
                            self._last_decision_candidates = len(action_list)
                            return self._trace_finalize(act_index, action_list, game_state)
                        # 被拦截时继续往下走到回退路径
                    else:
                        self._replay_record(
                            "recommendation_guard",
                            {"gua_id": "GUA-075", "passed": False},
                        )
                        self.logger.info(
                            "GUA-075 推荐校验不通过: %s/%s → 回退",
                            recommendation.get("type"), recommendation.get("rank"))
                else:
                    # GUA-075 诊断：匹配失败时采样 actionList 供根因分析
                    al_sample = []
                    al_types = set()
                    r_type = recommendation.get("type", "")
                    r_rank = recommendation.get("rank", "")
                    has_same_type = False
                    has_same_type_rank = False
                    for i, a in enumerate(action_list):
                        if not a or len(a) < 2:
                            continue
                        al_types.add(a[0])
                        if a[0] == r_type:
                            has_same_type = True
                            if a[1] == r_rank:
                                has_same_type_rank = True
                        if i < 5:
                            al_sample.append(f"{a[0]}/{a[1]}")
                    # 分类计数
                    if not has_same_type:
                        self._match_fail_type_mismatch += 1
                    elif not has_same_type_rank:
                        self._match_fail_rank_mismatch += 1
                    else:
                        self._match_fail_cards_mismatch += 1
                    self.logger.info(
                        "GUA-075 匹配失败: rec=(%s/%s) cards=%s | actionList=[%s](len=%d types=%s) → 回退",
                        r_type, r_rank,
                        recommendation.get("cards", [])[:5],
                        ",".join(al_sample) if al_sample else "?",
                        len(action_list),
                        sorted(al_types))
        except Exception as e:
            self.logger.warning("GUA-075 主路径异常: %s, 回退到现有管线", e)

        # ══════════════ 回退路径：现有管线（不变）══════════════
        # ── GUA-045 Guard filter ──
        filtered_actions = action_list
        action_map = list(range(len(action_list)))
        if GUARD_IMPORT_OK:
            try:
                filtered_actions, action_map = filter_action_list(game_state)
                self._replay_record(
                    "guard_filter",
                    {
                        "input_count": len(action_list),
                        "output_count": len(filtered_actions),
                        "original_indices": list(action_map),
                    },
                )
                if len(filtered_actions) < len(action_list):
                    self.guard_filtered_count += 1
            except Exception as e:
                self.logger.warning(f"filter_action_list 失败: {e}, 用原始 actionList")
                filtered_actions = action_list
                action_map = list(range(len(action_list)))

        # ── GUA-063 Phase 2: 角色驱动前置过滤 ──
        # 在 Guard 之后、NN forward 之前插入
        group_actions = filtered_actions
        group_filter_map = list(range(len(filtered_actions)))
        try:
            group_actions, flt_map = self._group_consistency_filter(
                filtered_actions, game_state)
            group_filter_map = flt_map
            self._replay_record(
                "group_filter",
                {
                    "input_count": len(filtered_actions),
                    "output_count": len(group_actions),
                    "filter_map": list(group_filter_map),
                },
            )
        except Exception as e:
            self.logger.warning(f"_group_consistency_filter 失败: {e}")

        # ── 决议 8: 接风跟线 — 匹配队友末手牌型的动作提前 ──
        # 决议 10: 方案 C — 投喂策略（两阶段：解围 + 投喂） ──
        # 插入点：_group_consistency_filter 之后、NN forward 之前
        # 使用重排而非硬删，保持 group_filter_map 有效性
        try:
            # 接风跟线（重排，不删）
            group_actions = self._apply_wind_catch_anchor(group_actions, game_state)
            # 投喂策略（重排 PASS 到末尾或投喂动作提前，不硬删）
            group_actions = self._try_teammate_feeding(group_actions, game_state)
            self._replay_record(
                "candidate_order",
                {"actions": list(group_actions)},
            )
        except Exception as e:
            self.logger.warning(f"接风/投喂处理失败: {e}")

        try:
            # 如果模型可用，使用模型决策（在 group_filtered_actions 上）
            if self.model is not None:
                action_index = self._model_decision(game_state, group_actions)
                if action_index is not None:
                    self.model_decisions += 1
                    # GUA-045 Guard 校验（2026-06-17）：模型决策后二次校验
                    if GUARD_IMPORT_OK:
                        try:
                            safe_idx = validate_decision(
                                action_index, group_actions, game_state, action_list
                            )
                            self.guard_validated_count += 1
                            if safe_idx != action_index:
                                self.guard_override_count += 1
                                self.logger.info(
                                    "Guard 覆盖: idx %d → %d",
                                    action_index, safe_idx,
                                )
                            action_index = safe_idx
                        except Exception as e:
                            self.logger.warning(f"validate_decision 失败: {e}")
                    # ── GUA-071: 组局一致性后置检查 ──
                    # NN + Guard 返回后，如果选中动作拆了组局，
                    # 用 _heuristic_select 覆盖（组局一致性 > 一切）
                    nn_chosen = (group_actions[action_index]
                                 if action_index < len(group_actions) else None)
                    need_heuristic_override = False
                    override_reason = ""
                    if (nn_chosen and self._card_mask
                            and self._action_breaks_core(
                                nn_chosen, self._card_mask, self._group_members)):
                        need_heuristic_override = True
                        override_reason = "拆局"
                    # ── GUA-071: joker 滥用后置检查 ──
                    # NN 选了 HR 单张但有 SB 也能压对手 → 浪费大王
                    if not need_heuristic_override and nn_chosen and GUARD_IMPORT_OK:
                        try:
                            from src.v.nn.guards.v7_guards import (
                                get_action_type as _gat, get_card_rank as _gcr,
                                get_card_value as _gcv,
                                ACTION_TYPE_SINGLE as _as,
                            )
                            def _cards(a):
                                return a[2] if len(a) >= 3 and isinstance(a[2], list) else a
                            if _gat(nn_chosen) == _as:
                                c_nn = _cards(nn_chosen)
                                card_nn = c_nn[0] if c_nn else (nn_chosen[0] if len(nn_chosen) >= 1 else "")
                                if _gcr(str(card_nn)) == "HR":
                                    cur_r = str(game_state.get("curRank", "2"))
                                    # 对手 greaterAction value
                                    ga = game_state.get("greaterAction", []) or []
                                    greater_val = 0
                                    if ga and ga[0] != "PASS":
                                        ga_c = _cards(ga)
                                        ga_card = ga_c[0] if ga_c else (ga[0] if len(ga) >= 1 else "")
                                        greater_val = _gcv(str(ga_card), cur_r)
                                    # 找是否有 SB 能压对手但又不会浪费
                                    for act in group_actions:
                                        if _gat(act) == _as:
                                            c_a = _cards(act)
                                            card_a = c_a[0] if c_a else (act[0] if len(act) >= 1 else "")
                                            if _gcr(str(card_a)) == "SB" and _gcv(str(card_a), cur_r) > greater_val:
                                                need_heuristic_override = True
                                                override_reason = "joker滥用(HR有SB可用)"
                                                break
                        except Exception:
                            pass
                    # ── GUA-071: 炸弹滥用后置检查 ──
                    # NN 选了炸弹/同花顺，但 action_list 里有同型非炸弹可压对手 → 浪费炸
                    if not need_heuristic_override and nn_chosen and GUARD_IMPORT_OK:
                        try:
                            from src.v.nn.guards.v7_guards import (
                                get_action_type as _gat,
                                ACTION_TYPE_BOMB as _ab, ACTION_TYPE_STRAIGHT_FLUSH as _asf,
                            )
                            _bomb_set = {_ab, _asf}
                            if _gat(nn_chosen) in _bomb_set:
                                ga = game_state.get("greaterAction", []) or []
                                if ga and ga[0] != "PASS":
                                    ga_type = _gat(ga)
                                    if ga_type not in _bomb_set and ga_type != "PASS":
                                        for act in group_actions:
                                            if _gat(act) == ga_type and _gat(act) not in _bomb_set:
                                                need_heuristic_override = True
                                                override_reason = "炸弹滥用(有同型可压)"
                                                break
                        except Exception:
                            pass
                    if need_heuristic_override:
                        self.heuristic_decisions += 1
                        heuristic_idx = self._heuristic_select(game_state, group_actions)
                        if heuristic_idx != action_index:
                            self.heuristic_override_count += 1
                            self.logger.info(
                                "GUA-071 组局覆盖(%s): NN idx %d → heuristic idx %d",
                                override_reason, action_index, heuristic_idx,
                            )
                            action_index = heuristic_idx
                    # GUA-085: 按动作内容回查原始 actionList（勿用 flt_map[model_idx]，
                    # group_consistency_filter 删动作后 flt_map 下标与 group_actions 不对齐）
                    if 0 <= action_index < len(group_actions):
                        chosen = group_actions[action_index]
                    else:
                        chosen = group_actions[0] if group_actions else None
                    original_idx = self._match_chosen_to_original_action_list(
                        chosen, action_list)
                    if (chosen and original_idx < len(action_list)
                            and action_list[original_idx] != chosen):
                        self.logger.warning(
                            "GUA-085 内容回查未命中，回退 filter_map: chosen=%s",
                            chosen[:3] if isinstance(chosen, list) and len(chosen) >= 3 else chosen,
                        )
                        original_idx = self._fallback_group_action_index(
                            action_index, group_filter_map, action_map, len(action_list))
                    self._check_midgame_triggers(game_state, chosen)
                    self._last_decision_layer = "NN+heuristic覆盖" if need_heuristic_override else "NN"
                    self._last_decision_score = self._last_nn_confidence
                    self._last_decision_candidates = len(group_actions)
                    return self._trace_finalize(original_idx, action_list, game_state)

            # 回退到启发式规则引擎（GUA-071 _heuristic_select）
            self.heuristic_decisions += 1
            heuristic_idx = self._heuristic_select(game_state, group_actions)
            if 0 <= heuristic_idx < len(group_actions):
                chosen = group_actions[heuristic_idx]
                original_idx = self._match_chosen_to_original_action_list(
                    chosen, action_list)
                self._check_midgame_triggers(game_state, chosen)
                self._last_decision_layer = "启发式"
                self._last_decision_score = None
                self._last_decision_candidates = len(group_actions)
                return self._trace_finalize(original_idx, action_list, game_state)
            self._last_decision_layer = "规则回退"
            self._last_decision_score = None
            self._last_decision_candidates = len(group_actions)
            return self._trace_finalize(
                self._rule_based_decision(game_state, group_actions),
                action_list,
                game_state,
            )

        except Exception as e:
            self.logger.error(f"? ????: {e}")
            self.fallback_decisions += 1
            self._last_decision_layer = "????"
            self._last_decision_score = None
            safe_actions = group_actions or filtered_actions or action_list
            self._last_decision_candidates = len(safe_actions)
            safe_idx = self._rule_based_decision(game_state, safe_actions)
            chosen = (
                safe_actions[safe_idx]
                if 0 <= safe_idx < len(safe_actions)
                else (safe_actions[0] if safe_actions else None)
            )
            original_idx = self._match_chosen_to_original_action_list(
                chosen, action_list
            )
            return self._trace_finalize(original_idx, action_list, game_state)

    def _inject_belief_vector(self, game_state: Dict[str, Any]) -> None:
        """GUA-072：从 MemoryTracker 注入规则记牌信念到 game_state['_belief']。"""
        if self._tracker is None:
            game_state.pop("_belief", None)
            return
        try:
            from src.v.nn.features.rule_card_counter import (
                create_counter_from_tracker,
                extract_rule_memory_features,
            )
            game_state["_belief"] = create_counter_from_tracker(self._tracker).get_belief(
                game_state
            )
            game_state["_rule_memory_vec"] = extract_rule_memory_features(
                game_state.get("_belief") or {}
            )
        except Exception as e:
            self.logger.debug("belief inject skip: %s", e)
            game_state.pop("_belief", None)
            game_state.pop("_rule_memory_vec", None)

    def _rule_card_counter_from_state(self, game_state: Dict[str, Any]):
        """GUA-072 / P0a：从 tracker 或 game_state 取 RuleCardCounter。"""
        if self._tracker is not None:
            try:
                from src.v.nn.features.rule_card_counter import create_counter_from_tracker

                return create_counter_from_tracker(self._tracker)
            except Exception as e:
                self.logger.debug("rule counter skip: %s", e)
        tracker = game_state.get("_memory_tracker")
        if tracker is not None:
            try:
                from src.v.nn.features.rule_card_counter import create_counter_from_tracker

                return create_counter_from_tracker(tracker)
            except Exception as e:
                self.logger.debug("rule counter skip (gs): %s", e)
        return None

    def _belief_gate_counter_press(
        self,
        game_state: Dict[str, Any],
        rec: Dict[str, Any],
    ) -> bool:
        """P0a：信念门控跟压。True → 拦截推荐（上游倾向 PASS）。

        设计真源：V8-中期压顺灵活性-组牌-动态重组方案.md §3.4 P0a。
        """
        my_pos = int(game_state.get("myPos", self.player_id))
        teammate_pos = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        try:
            greater_pos = int(greater_pos)
        except (TypeError, ValueError):
            return False
        if greater_pos in (-1, my_pos, teammate_pos):
            return False

        action_type = str(rec.get("type", ""))
        press_rank = str(rec.get("rank", ""))
        if not press_rank or action_type in ("PASS", "Bomb", "StraightFlush"):
            return False

        counter = self._rule_card_counter_from_state(game_state)
        if counter is None:
            return False
        if not counter.can_opponent_form_type(
            greater_pos, action_type, press_rank, game_state
        ):
            return False

        belief = game_state.get("_belief") or {}
        hand_counts = belief.get("hand_counts") or {}
        if hand_counts:
            my_rest = hand_counts.get(my_pos)
            if my_rest is not None and int(my_rest) <= 5:
                return False
            opp_rest = hand_counts.get(greater_pos)
            if opp_rest is not None and int(opp_rest) <= 5:
                return False

        cards = rec.get("cards") or []
        broken = self._get_broken_core_type(
            [action_type, press_rank, list(cards)],
            self._card_mask or {},
            self._group_type_map or {},
            self._group_members,
        )
        if broken is not None and broken not in ("Bomb", "StraightFlush"):
            self.logger.debug(
                "P0a belief gate: breaks_core=%s type=%s rank=%s",
                broken,
                action_type,
                press_rank,
            )
        opp_risks = belief.get("opp_bomb_risks") or {}
        risk = float(opp_risks.get(greater_pos, 0) or 0)
        if risk >= 0.6 and broken is not None:
            self.logger.debug("P0a belief gate: high bomb risk %.2f", risk)
        return True

    def _apply_belief_gate_min_press(
        self,
        game_state: Dict[str, Any],
        rec: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """P0a：对 _recommend_min_press_impl 产出做信念门控。"""
        if not rec:
            return None
        if game_state.get("_belief") is None and self._tracker is not None:
            self._inject_belief_vector(game_state)
        if self._belief_gate_counter_press(game_state, rec):
            self.logger.info(
                "P0a belief gate: skip min_press type=%s rank=%s greaterPos=%s",
                rec.get("type"),
                rec.get("rank"),
                game_state.get("greaterPos"),
            )
            return None
        return rec

    def _inject_phase_relation(self, game_state: Dict[str, Any]) -> None:
        """GUA-094：从 MemoryTracker 注入中局可消费的规则版推断标签。"""
        if self._tracker is None:
            game_state.pop("_phase_relation", None)
            return
        try:
            from src.v.nn.features.rule_card_counter import create_counter_from_tracker

            phase_relation = create_counter_from_tracker(
                self._tracker
            ).infer_phase_relation(game_state)
            phase_relation.update(self._estimate_sprint_fire_signal(game_state))
            game_state["_phase_relation"] = phase_relation
        except Exception as e:
            self.logger.debug("phase relation inject skip: %s", e)
            game_state.pop("_phase_relation", None)

    def _joker_belief_from_state(self, game_state: Dict[str, Any]) -> Dict[str, int]:
        """GUA-072：从 _belief['joker_signal'] 读取大小王归属推断。"""
        joker = (game_state.get("_belief") or {}).get("joker_signal") or {}

        def _int(key: str) -> int:
            try:
                return int(joker.get(key, 0) or 0)
            except (TypeError, ValueError):
                return 0

        return {
            "hr_with_opponents": _int("hr_with_opponents"),
            "sb_with_opponents": _int("sb_with_opponents"),
            "hr_in_my_hand": _int("hr_in_my_hand"),
            "sb_in_my_hand": _int("sb_in_my_hand"),
        }

    def _recommendation_uses_joker(self, rec: Optional[Dict[str, Any]]) -> bool:
        """推荐是否为单张大小王。"""
        if not rec or rec.get("type") != "Single":
            return False
        cards = rec.get("cards") or []
        if not cards:
            return False
        from src.v.nn.guards.v7_guards import get_card_rank

        return get_card_rank(str(cards[0])) in ("HR", "SB")

    def _filter_joker_lead_singles(
        self, singles: List[str], game_state: Dict[str, Any]
    ) -> List[str]:
        """对手侧推断双 HR 时不领出王；单 HR 时不领大王。"""
        from src.v.nn.guards.v7_guards import get_card_rank

        jb = self._joker_belief_from_state(game_state)
        hr_opp = jb["hr_with_opponents"]
        if hr_opp >= 2:
            filtered = [c for c in singles if get_card_rank(str(c)) not in ("HR", "SB")]
            return filtered if filtered else singles
        if hr_opp >= 1:
            filtered = [c for c in singles if get_card_rank(str(c)) != "HR"]
            return filtered if filtered else singles
        return singles

    def _filter_joker_press_single_candidates(
        self,
        candidates: List[Tuple[Any, str, str]],
        game_state: Dict[str, Any],
    ) -> List[Tuple[Any, str, str]]:
        """跟单候选：有非 HR 可压时不用 HR；推断双 HR 时优先 SB。"""
        jb = self._joker_belief_from_state(game_state)
        hr_opp = jb["hr_with_opponents"]
        if hr_opp < 1 or not candidates:
            return candidates
        non_hr = [t for t in candidates if t[2] != "HR"]
        if non_hr:
            return non_hr
        if hr_opp >= 2:
            sb_only = [t for t in candidates if t[2] == "SB"]
            if sb_only:
                return sb_only
        return candidates

    def _estimate_sprint_fire_signal(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """GUA-102：基于组牌完备度估算“整牌冲刺点火”信号。"""
        from collections import Counter

        card_mask = self._card_mask or {}
        if not card_mask:
            return {
                "sprint_fire_ready": False,
                "bomb_count": 0,
                "natural_turn_count": 99,
                "single_residue": 99,
                "structured_ratio": 0.0,
            }

        hand_cards = game_state.get("handCards") or list(card_mask.keys())
        total_cards = len(hand_cards)
        if total_cards <= 0:
            return {
                "sprint_fire_ready": False,
                "bomb_count": 0,
                "natural_turn_count": 99,
                "single_residue": 99,
                "structured_ratio": 0.0,
            }

        type_counter = Counter(self._group_type_map.values())
        single_residue = len(self._scatter_singles(card_mask))
        bomb_count = int(type_counter.get("Bomb", 0) + type_counter.get("StraightFlush", 0))
        pair_count = int(type_counter.get("pair", 0))
        trips_count = int(type_counter.get("trips", 0))
        straight_count = int(type_counter.get("straight", 0))
        three_pair_count = (int(type_counter.get("pair_in_three_pair", 0)) + 2) // 3
        three_with_two_count = max(
            int(type_counter.get("trip_in_three_with_two", 0)),
            int(type_counter.get("pair_in_three_with_two", 0)),
        )
        two_trips_count = (int(type_counter.get("trip_in_steel_plate", 0)) + 1) // 2

        structured_turn_count = (
            bomb_count
            + pair_count
            + trips_count
            + straight_count
            + three_pair_count
            + three_with_two_count
            + two_trips_count
        )
        natural_turn_count = structured_turn_count + single_residue
        structured_ratio = max(0.0, min(1.0, (total_cards - single_residue) / float(total_cards)))
        role = self._current_role or "主攻"

        sprint_fire_ready = bool(
            role in ("主攻", "超强主攻")
            and total_cards <= 12
            and bomb_count >= 2
            and single_residue <= 2
            and structured_turn_count >= 3
            and structured_ratio >= 0.75
            and natural_turn_count <= max(6, bomb_count + 3)
        )

        return {
            "sprint_fire_ready": sprint_fire_ready,
            "bomb_count": bomb_count,
            "natural_turn_count": natural_turn_count,
            "single_residue": single_residue,
            "structured_ratio": round(structured_ratio, 4),
        }

    def _maybe_recommend_sprint_fire_bomb(
        self,
        game_state: Dict[str, Any],
        card_mask: Dict[str, tuple],
        cur_rank: str,
        *,
        teammate_pos: int,
        intent: str,
    ) -> Optional[Dict[str, Any]]:
        """GUA-102：在整牌冲刺态下允许主动点火开炸。"""
        from src.v.nn.guards.v7_guards import get_action_type

        phase_relation = game_state.get("_phase_relation") or {}
        if not phase_relation.get("sprint_fire_ready", False):
            return None
        role = self._current_role or "主攻"
        if role not in ("主攻", "超强主攻"):
            return None

        greater_pos = int(game_state.get("greaterPos", -1) or -1)
        # 席位判断统一以 game_state["myPos"] 为准（对局 V8 座位可能是 0 或 2，
        # 不能用构造时 self.player_id 硬编码，否则 your_id=2 时把「自己的牌」
        # 误判为可炸的敌方牌 → 炸自己/席位错位）。
        my_pos = int(game_state.get("myPos", self.player_id) or self.player_id)
        if greater_pos in (-1, my_pos, teammate_pos):
            return None

        greater_action = game_state.get("greaterAction", []) or []
        if not greater_action or greater_action[0] == "PASS":
            return None
        if get_action_type(greater_action) != "Single":
            return None

        teammate_cover_confidence = float(
            phase_relation.get("teammate_cover_confidence", 0.0) or 0.0
        )
        if teammate_cover_confidence >= 0.75:
            return None

        bomb = self._recommend_bomb_from_mask(card_mask, cur_rank, action_list=game_state.get("actionList") or [])
        if not bomb:
            return None

        tagged = dict(bomb)
        tagged["intent"] = intent
        return tagged

    def _ensure_memory_tracker_for_decide(self, game_state: Dict[str, Any]) -> None:
        """GUA-078/GUA-065：decide 入口就绪 MemoryTracker 与各席剩张数。

        残局 Q1/Q3 与 ``_inject_numofplayers`` 依赖准确 ``numofplayers``。
        wiki ``endgame-preprocessor-overview`` 张力4：记忆管线应先于残局激活，
        不可仅于 NN ``_extract_features`` 路径 lazy init。

        剩张数优先级：``publicInfo[i].rest``（v1006 平台真源，对齐 M3 GUA-028）
        > MemoryTracker 出牌回放 > 默认 27。
        """
        if not FEATURE_IMPORT_OK:
            return
        my_pos = game_state.get("myPos", self.player_id)
        hand_cards = game_state.get("handCards", []) or []
        cur_rank = str(game_state.get("curRank", "2"))

        if not self._tracker_initialized:
            self._tracker = MemoryTracker(
                my_pos=my_pos,
                enable_inference=False,
                max_infer_depth=0,
                use_grouping_engine=self.use_grouping_engine,
            )
            if hand_cards:
                self._tracker.init_from_hand(hand_cards)
            self._tracker.set_level_rank(cur_rank)
            self._tracker_initialized = True
            self._tracker_history_replayed = 0
        else:
            try:
                self._tracker.set_level_rank(cur_rank)
            except Exception:
                pass

        history = game_state.get("history", [])
        start = self._tracker_history_replayed
        for h in history[start:]:
            seat = h.get("pos", h.get("seat", -1))
            if seat < 0:
                continue
            action = h.get("action") or h.get("curAction") or []
            ctx = h.get("context") or {}
            if action:
                if isinstance(action, list) and str(action[0]).upper() == "PASS":
                    ga = ctx.get("greaterAction")
                    if isinstance(ga, list) and len(ga) >= 3:
                        ga_type = str(ga[0])
                        if ga_type.upper() not in ("PASS", ""):
                            self._tracker.record_pass(
                                seat,
                                ga_type,
                                greater_action=ga,
                                greater_pos=ctx.get("greaterPos"),
                            )
                else:
                    self._tracker.record_play(seat, action, context=ctx)
        self._tracker_history_replayed = len(history)

        cur_rank = str(game_state.get("curRank", "2"))
        self._tracker.sync_tribute_phase_from_state(
            tribute_result=game_state.get("tributeResult"),
            back_result=game_state.get("backResult"),
            anti_pos=game_state.get("antiPos"),
            cur_rank=cur_rank,
        )

        if hand_cards:
            self._tracker.sync_my_jokers(hand_cards)

        if not history:
            recent = game_state.get("recentPlays", [])
            for rp in recent:
                seat = rp.get("pos", -1)
                if seat < 0:
                    continue
                cards = rp.get("cards", [])
                if cards:
                    action_type = rp.get("type", "Unknown")
                    self._tracker.record_play(seat, [action_type, "", cards])

        self._sync_tracker_from_public_info(game_state)

        if self._tracker is not None:
            self._tracker.hand_counts[my_pos] = len(hand_cards)

    def _sync_tracker_from_public_info(self, game_state: Dict[str, Any]) -> None:
        """act 时用 publicInfo[].rest 对齐 MemoryTracker.hand_counts（v1006 真源）。"""
        if self._tracker is None:
            return
        public_info = game_state.get("publicInfo")
        if not isinstance(public_info, list):
            return
        for i, info in enumerate(public_info):
            if i > 3 or not isinstance(info, dict):
                continue
            rest = info.get("rest")
            if rest is None:
                continue
            try:
                n = int(rest)
            except (TypeError, ValueError):
                continue
            if 0 <= n <= 27:
                self._tracker.hand_counts[i] = n

    def _replay_history_to_tracker(self, game_state: Dict[str, Any]) -> None:
        """从 game_state 回放历史到 MemoryTracker（NN 特征路径与 decide 共用）。"""
        self._ensure_memory_tracker_for_decide(game_state)

    def _get_tracker_state(self, game_state: Optional[Dict[str, Any]] = None) -> List[float]:
        """获取 MemoryTracker 状态向量。

        GUA-063 重构：优先用 get_tracking_vector()（24 维追踪），
        组牌特征由 _run_grouping_engine() 外部提供。
        """
        if not FEATURE_IMPORT_OK or self._tracker is None:
            return [0.0] * MEMORY_TRACKER_DIM
        try:
            return self._tracker.get_tracking_vector()
        except Exception:
            # 回退：老接口可能没有 get_tracking_vector
            try:
                return self._tracker.get_state_vector(game_state=game_state)
            except Exception:
                return [0.0] * MEMORY_TRACKER_DIM

    # ── GUA-063: 一次枚举，三样产出 ──────────────────────────

    def _run_grouping_engine(self, game_state: Dict[str, Any]) -> None:
        """跑一次 enumerate_groupings()，同时产出 mask + role + features。

        缓存到 self._card_mask / self._current_role / self._grouping_features。
        通过手牌 hash 判断是否需要重新计算（中局重分组时 hash 会变）。
        """
        hand_cards = game_state.get("handCards", []) or []
        if not hand_cards:
            self._card_mask = {}
            self._group_type_map = {}
            self._group_members = {}
            self._current_role = "助攻"
            self._grouping_features = np.zeros(24, dtype=np.float32)
            return

        cur_rank = str(game_state.get("curRank", "2"))
        hand_hash = hash(tuple(sorted(hand_cards)))
        if hand_hash == self._last_hand_hash and self._card_mask is not None:
            return  # 手牌未变，复用缓存

        self._last_hand_hash = hand_hash

        try:
            from src.v.nn.features.grouping_engine import (
                enumerate_groupings, _extract_features,
            )
            best_plan, all_plans = enumerate_groupings(hand_cards, cur_rank)
            self._best_plan = best_plan
            self._all_plans = list(all_plans)
            self._active_plan = best_plan

            # 产出 1: card mask（进前置过滤）+ group_type_map + group_members
            self._card_mask, self._group_type_map, self._group_members = best_plan.to_card_mask()

            # 产出 2: role（决定过滤行为）
            raw_role = best_plan.role or "主攻"
            self._score_tier = getattr(best_plan, "score_tier", None)
            # GUA-234 §二：牌力档位门禁（冲突取更保守）
            try:
                from src.v.nn.midgame_teammate_demand import (
                    resolve_power_gate_tier,
                    dynamic_regroup_enabled,
                )
                self._power_gate_tier = resolve_power_gate_tier(
                    self._score_tier, raw_role,
                )
                self._dynamic_regroup_enabled = dynamic_regroup_enabled(
                    self._power_gate_tier,
                )
                game_state["_power_gate_tier"] = self._power_gate_tier
                game_state["_dynamic_regroup_enabled"] = self._dynamic_regroup_enabled
                game_state["_score_tier"] = self._score_tier
            except Exception as e:
                self.logger.debug("GUA-234 门禁计算失败: %s", e)
                self._dynamic_regroup_enabled = True
            # GUA-079: 初始 role 锚锁定 — 首算若为主攻以上，锁定 role；
            # 后续重算仍跑 enumerate_groupings 更新 card_mask/features，
            # 但 role 不退化，避免强牌打着打着变畏缩
            if self._anchor_role is None and raw_role in ("超强主攻", "主攻"):
                self._anchor_role = raw_role
                self.logger.info("GUA-079 锚定初始 role: %s", raw_role)
            if self._anchor_role is not None:
                self._current_role = self._anchor_role
            else:
                self._current_role = raw_role

            # GUA-178: 语义手数 ≤ 2 时角色升级为「主攻」
            # 即使 power_score 低（无炸/小牌型），两手整牌也是冲刺窗口，
            # 应走 GUA-116 主攻领出而非 GUA-117 助攻领出
            from src.v.nn.endgame.endgame_preprocessor import EndgamePreprocessor as _GUA178_EP
            _gid_to_type = dict(self._group_type_map)
            _type_counts: Dict[str, int] = {}
            for _gid, _gtype in _gid_to_type.items():
                _type_counts[_gtype] = _type_counts.get(_gtype, 0) + 1
            if self._current_role in ("助攻", "超弱") and _GUA178_EP.count_semantic_hands(_type_counts) <= 2:
                self._current_role = "主攻"
                self.logger.info("GUA-178 冲刺角色升级: semantic_hands≤2 → 主攻")

            # 产出 3: 24 维组牌特征（进 NN）
            features_24 = _extract_features(all_plans, hand_cards, cur_rank)
            self._grouping_features = np.array(features_24, dtype=np.float32)

            # 诊断：完整 group 分解（GUA-075 增强，方便日志排查）
            gid_to_cards = dict(self._group_members)
            lines = []
            for gid in sorted(gid_to_cards.keys()):
                cards = gid_to_cards[gid]
                gtype = self._group_type_map.get(gid, "scatter")
                # 区分 core 牌
                core_cards = [c for c in cards if self._card_mask[c][1] > 0.5]
                non_core = [c for c in cards if self._card_mask[c][1] <= 0.5]
                core_str = f" core={core_cards}" if core_cards else ""
                non_str = f" loose={non_core}" if non_core else ""
                lines.append(f"  G{gid}({gtype}):{cards}{core_str}{non_str}")
            bomb_gids = [gid for gid, gt in self._group_type_map.items() if gt == "Bomb"]
            self.logger.info(
                "组牌引擎: role=%s handCards=%d curRank=%s total_groups=%d bombs=%d\n%s",
                self._current_role,
                len(hand_cards),
                cur_rank,
                len(gid_to_cards) - (1 if -1 in gid_to_cards else 0),
                len(bomb_gids),
                "\n".join(lines),
            )
        except Exception as e:
            import traceback
            self.logger.warning(
                "_run_grouping_engine 失败: %s, 退化 (handCards=%d, curRank=%s)\n%s",
                e,
                len(hand_cards),
                game_state.get("curRank", "?"),
                traceback.format_exc(),
            )
            # ── 降级保护 (GUA-072): card_mask 为空但 handCards 非空时，
            #     用 _basic_classify 做简单炸弹识别，防止拆炸弹 ──
            try:
                self._card_mask, self._group_type_map, self._group_members = self._basic_classify(
                    hand_cards, cur_rank=game_state.get("curRank", "2"))
                self._current_role = "主攻"  # 降级时保守主攻，不拆炸弹
                self.logger.info(
                    "_basic_classify 降级: 识别到 %d 个 bomb group",
                    len(set(v[0] for v in self._card_mask.values() if v[0] >= 0)),
                )
            except Exception as e2:
                self.logger.warning("_basic_classify 也失败: %s，card_mask 完全退化", e2)
                self._card_mask = {}
                self._group_type_map = {}
                self._group_members = {}
                self._current_role = "助攻"
            self._grouping_features = np.zeros(24, dtype=np.float32)
            self._all_plans = []
            self._active_plan = None
            self._core_broken_since_regroup = False

    def _replan_opp_consecutive_threshold(self) -> int:
        """对手连续同型触发阈值：强牌+ / 超强 ≥3，其余 ≥2。"""
        from src.v.nn.midgame_teammate_demand import TIER_STRONG_PLUS, TIER_SUPER

        tier = self._power_gate_tier or ""
        if tier in (TIER_SUPER, TIER_STRONG_PLUS):
            return 3
        return 2

    @staticmethod
    def _plan_type_counts(plan) -> Dict[str, int]:
        """GroupingPlan → 平台牌型计数（供局面加权）。"""
        return {
            "Single": len(plan.singles or []),
            "Pair": len(plan.pairs or []),
            "Trips": len(plan.trips or []),
            "Straight": len(plan.straights or []),
            "ThreeWithTwo": len(plan.three_with_twos or []),
            "ThreePair": len(plan.three_pairs or []),
            "TwoTrips": len(plan.steel_plates or []),
        }

    def _plan_situation_bonus(
        self,
        plan,
        game_state: Dict[str, Any],
        focus_type: Optional[str] = None,
    ) -> float:
        """局面加权：对手连续牌型 / 喂牌 P 与 plan 结构对齐度。"""
        counts = self._plan_type_counts(plan)
        bonus = 0.0
        snap = game_state.get("_mid_feed_snapshot") or {}
        opp_cons = snap.get("opponent_consecutive") or {}

        if not focus_type:
            greater_action = game_state.get("greaterAction") or []
            if (
                isinstance(greater_action, list)
                and greater_action
                and greater_action[0] not in ("PASS",)
            ):
                focus_type = str(greater_action[0])
            elif opp_cons:
                focus_type = max(
                    opp_cons,
                    key=lambda k: int(opp_cons.get(k, 0) or 0),
                )

        if focus_type and focus_type in counts:
            streak = int(opp_cons.get(focus_type, 0) or 0)
            bonus += 0.04 * counts[focus_type]
            bonus += 0.025 * min(streak, 4)

        feed_p = game_state.get("_mid_feed_P") or []
        for i, ft in enumerate(feed_p[:3]):
            if ft in counts:
                bonus += (0.035 - 0.01 * i) * counts[ft]

        return bonus

    def _replan_trigger_reason(self, game_state: Dict[str, Any]) -> Optional[str]:
        """GUA-234 阶段 C：是否触发 Top3 重评分。"""
        if not self._dynamic_regroup_enabled:
            return None
        if not self._all_plans or len(self._all_plans) < 2:
            return None

        hand_cards = game_state.get("handCards") or []
        if len(hand_cards) <= 10:
            return None

        my_pos = int(game_state.get("myPos", self.player_id) or 0)
        teammate = (my_pos + 2) % 4
        nop = game_state.get("numofplayers") or []
        if isinstance(nop, (list, tuple)) and len(nop) > teammate:
            try:
                if int(nop[teammate]) <= 5:
                    return "teammate_close"
            except (TypeError, ValueError):
                pass

        snap = game_state.get("_mid_feed_snapshot") or {}
        opp_cons = snap.get("opponent_consecutive") or {}
        threshold = self._replan_opp_consecutive_threshold()
        for ptype, streak in opp_cons.items():
            if int(streak or 0) >= threshold:
                return f"opponent_consecutive_{ptype}_{streak}"

        return None

    def _apply_active_plan(
        self,
        plan,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> None:
        """切换 active_plan 并刷新 card_mask 供推荐器消费。"""
        self._active_plan = plan
        self._best_plan = plan
        self._card_mask, self._group_type_map, self._group_members = plan.to_card_mask()
        if game_state is not None:
            game_state["_active_plan_strategy"] = getattr(plan, "strategy", "")

    def _evaluate_replan_candidates(self, game_state: Dict[str, Any]) -> None:
        """GUA-234 阶段 C：局面触发时对 Top3 重评分并可选切换 plan。

        简化权衡（§8.3）：plan_loss 硬上限 + 局面 bonus；不接残手地板（阶段 E）。
        """
        reason = self._replan_trigger_reason(game_state)
        if not reason:
            return

        active = self._active_plan or self._best_plan
        if active is None or not self._all_plans:
            return

        plan_loss_limit = 0.15
        switch_margin = 0.02
        best_candidate = active
        best_ctx = active.score + self._plan_situation_bonus(active, game_state)
        scored: List[Tuple[str, float, float, float]] = []

        for plan in self._all_plans:
            delta = active.score - plan.score
            ctx = plan.score + self._plan_situation_bonus(plan, game_state)
            scored.append(
                (
                    getattr(plan, "strategy", "?"),
                    round(float(plan.score), 3),
                    round(ctx, 3),
                    round(delta, 3),
                )
            )
            if plan is active:
                continue
            if delta > plan_loss_limit:
                continue
            if ctx > best_ctx + switch_margin:
                best_ctx = ctx
                best_candidate = plan

        self.logger.info(
            "GUA-234 replan: reason=%s active=%s scored=%s pick=%s",
            reason,
            getattr(active, "strategy", "?"),
            scored,
            getattr(best_candidate, "strategy", "?"),
        )
        game_state["_replan_trigger"] = reason
        game_state["_replan_scores"] = scored

        if best_candidate is not active:
            self._apply_active_plan(best_candidate, game_state)
            game_state["_replan_switched"] = True
        else:
            game_state["_replan_switched"] = False

    def _collect_regroup_press_candidates(
        self,
        game_state: Dict[str, Any],
        card_mask: Dict[str, tuple],
        greater_action: List,
        greater_type: str,
        hand_cards: List[str],
        cur_rank: str,
    ) -> List[Dict[str, Any]]:
        """GUA-234 E：收集针对性重组压牌候选（含拆结构）。"""
        from src.v.nn.dynamic_regroup import collect_regroup_target_types, dedupe_recommendations
        from src.v.nn.guards.v7_guards import (
            get_action_rank,
            get_card_value,
            _extract_action_cards,
        )

        if not greater_action or greater_action[0] == "PASS":
            return []

        greater_rank = get_action_rank(greater_action)
        if not greater_rank:
            return []

        if greater_rank in ("B", "R"):
            greater_cards = _extract_action_cards(greater_action)
            if greater_cards:
                greater_val = get_card_value(str(greater_cards[0]), cur_rank)
            else:
                greater_val = self.RANK_ORDER.get(greater_rank, 0)
        else:
            greater_val = get_card_value(f"H{greater_rank}", cur_rank)

        candidates: List[Dict[str, Any]] = []
        targets = collect_regroup_target_types(game_state, greater_type)

        if greater_type in targets:
            rec = self._recommend_min_press_impl(
                game_state,
                card_mask,
                greater_action,
                greater_type,
                hand_cards,
                cur_rank,
                apply_belief_gate=False,
            )
            if rec:
                candidates.append(rec)

        groups = self._build_group_index(card_mask)

        def _prank(internal_rank: str) -> str:
            return self.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

        if "ThreeWithTwo" in targets:
            rec = self._build_three_with_two_press(
                hand_cards,
                greater_val,
                cur_rank,
                "min",
                card_mask=card_mask,
                group_type_map=self._group_type_map,
                group_members=self._group_members,
                allow_break_protected_core=True,
            )
            if rec:
                candidates.append(rec)

        if "ThreePair" in targets:
            rec = self._build_consecutive_structure_press(
                groups, "pair_in_three_pair", 3, greater_val, cur_rank, "min",
            )
            if rec:
                rec["rank"] = _prank(rec["rank"])
                candidates.append(rec)

        if "TwoTrips" in targets:
            rec = self._build_consecutive_structure_press(
                groups, "trip_in_steel_plate", 2, greater_val, cur_rank, "min",
            )
            if rec:
                rec["rank"] = _prank(rec["rank"])
                candidates.append(rec)

        return dedupe_recommendations(candidates)

    def _recommend_targeted_regroup_press(
        self,
        game_state: Dict[str, Any],
        card_mask: Dict[str, tuple],
        greater_action: List,
        greater_type: str,
        hand_cards: List[str],
        cur_rank: str,
    ) -> Optional[Dict[str, Any]]:
        """GUA-234 E：针对性重组跟压（残手地板 + 信念门控）。"""
        from src.v.nn.dynamic_regroup import filter_regroup_candidate
        from src.v.nn.guards.v7_guards import get_card_value, get_card_rank

        if not self._dynamic_regroup_enabled:
            return None

        raw = self._collect_regroup_press_candidates(
            game_state,
            card_mask,
            greater_action,
            greater_type,
            hand_cards,
            cur_rank,
        )
        if not raw:
            return None

        valid: List[Tuple[Dict[str, Any], str, float]] = []
        traces: List[Tuple[str, str]] = []
        for rec in raw:
            ok, reason = filter_regroup_candidate(
                self, game_state, rec, hand_cards, cur_rank,
            )
            traces.append((str(rec.get("type")), reason))
            if not ok:
                continue
            cards = rec.get("cards") or []
            val = get_card_value(str(cards[0]), cur_rank) if cards else 99
            valid.append((rec, reason, val))

        game_state["_regroup_filter_trace"] = traces
        if not valid:
            self.logger.info(
                "GUA-234 regroup: all %d candidates filtered trace=%s",
                len(raw),
                traces,
            )
            return None

        valid.sort(key=lambda x: x[2])
        best, reason, _ = valid[0]
        self.logger.info(
            "GUA-234 regroup: pick type=%s rank=%s reason=%s from %d/%d",
            best.get("type"),
            best.get("rank"),
            reason,
            len(valid),
            len(raw),
        )
        game_state["_regroup_selected"] = {
            "type": best.get("type"),
            "rank": best.get("rank"),
            "filter_reason": reason,
        }
        return best

    # ── GUA-065: 注入 numofplayers ────────────────────

    def _inject_numofplayers(self, game_state: Dict[str, Any]) -> None:
        """GUA-065+GUA-170：注入各玩家剩张数 → game_state['numofplayers']。

        优先级（高→低）：
          1. publicInfo.rest（平台 action request 实时推送，最准确）
          2. MemoryTracker.hand_counts（历史推算，可能 stale）
          3. 默认 27（每副初始值）
          myPos 始终以 handCards 实牌数为准（纠偏）。

        供 guard R07/R08/R09 及残局管线使用。
        """
        my_pos = game_state.get("myPos", self.player_id)
        hand_cards = game_state.get("handCards", []) or []

        # ── 基础值：默认 27 ──
        numofplayers = [27, 27, 27, 27]

        # ── 1. MemoryTracker 作为候选（可能有 stale 数据） ──
        if self._tracker_initialized and self._tracker is not None:
            try:
                hc = self._tracker.hand_counts
                numofplayers = [hc.get(i, 27) for i in range(4)]
            except Exception:
                pass

        # ── 2. publicInfo.rest 覆盖（GUA-170：平台实时数据 > MemoryTracker） ──
        # OpenGuanDan: publicInfo 4 项（含 curPos 自身），按绝对位置索引
        # v1006: publicInfo 3 项（仅他人），从 curPos+1 起按序映射
        public_info = game_state.get("publicInfo", [])
        if isinstance(public_info, list):
            if len(public_info) >= 4:
                for i in range(4):
                    if isinstance(public_info[i], dict):
                        rest = public_info[i].get("rest")
                        if isinstance(rest, (int, float)) and rest >= 0:
                            numofplayers[i] = int(rest)
            elif len(public_info) == 3:
                cur_pos = game_state.get("curPos", my_pos)
                for j, pi in enumerate(public_info):
                    seat = (cur_pos + 1 + j) % 4
                    if isinstance(pi, dict):
                        rest = pi.get("rest")
                        if isinstance(rest, (int, float)) and rest >= 0:
                            numofplayers[seat] = int(rest)

        # ── 3. 纠偏：myPos 以 handCards 实数为准 ──
        numofplayers[my_pos] = len(hand_cards)
        game_state["numofplayers"] = numofplayers

    # ── GUA-244: 注入剩余池（对手残牌构成推理） ──────────

    def _inject_remaining_pool(self, game_state: Dict[str, Any]) -> None:
        """GUA-244：注入 name 级剩余池 → game_state['_remaining_pool_cards']。

        数据源：adapter 的 `remainingPool`（108 ints − 各席已出 − 当前手牌，
        name 级展开列表）。供残局决策做「单/对子被接风险」推理。

        一致性校验（防污染，校验失败自动回退 None，决策层走原逻辑）：
          1. 每张牌名 ≤ 2 副本（两副牌约束）
          2. 池总张数 == 其余三家 numofplayers 之和（池 = 对手残牌全集）
        v1006 线无 remainingPool 字段 → 校验失败 → None，行为不变。
        """
        pool = game_state.get("remainingPool")
        if not isinstance(pool, list) or not pool:
            game_state["_remaining_pool_cards"] = None
            return
        try:
            from collections import Counter
            cnt = Counter(pool)
            if any(c > 2 for c in cnt.values()):
                raise ValueError("副本数 >2")
            nop = game_state.get("numofplayers", [27, 27, 27, 27])
            hand_cards = game_state.get("handCards", []) or []
            others = sum(nop) - len(hand_cards)
            if len(pool) != others:
                raise ValueError("池张数 %d != 对手剩余 %d" % (len(pool), others))
            game_state["_remaining_pool"] = dict(cnt)
            game_state["_remaining_pool_cards"] = sorted(pool)
        except Exception as _e:
            if self.logger is not None:
                self.logger.warning("GUA-244 剩余池校验失败，回退原逻辑: %s", _e)
            game_state["_remaining_pool_cards"] = None

    # ── GUA-072: 降级保护 — 组牌引擎异常时用简单规则识别炸弹 ──

    @staticmethod
    def _basic_classify(
        hand_cards: List[str],
        cur_rank: str = "2",
    ) -> tuple:
        """GUA-072：当 enumerate_groupings 失败时的降级炸弹识别。

        不依赖组牌引擎，用简单点数统计识别炸弹（4+ 同点数）和同花顺。
        返回 (card_mask, group_type_map, group_members)，格式与 to_card_mask() 一致。

        Args:
            hand_cards: 手牌列表，如 ['S2', 'CA', 'D4', ...]
            cur_rank: 当前级牌

        Returns:
            (card_mask, group_type_map, group_members)
            card_mask: card → (group_id, is_core, group_size)
            group_type_map: group_id → "Bomb" | "StraightFlush" | ...
            group_members: group_id → 该组全部牌（含重复牌串）
        """
        import re

        card_mask: Dict[str, tuple] = {}
        group_type_map: Dict[int, str] = {}
        group_members: Dict[int, List[str]] = {}

        if not hand_cards:
            return card_mask, group_type_map, group_members

        # 按点数统计（炸弹只看点数，不看花色）
        rank_counts: Dict[str, List[str]] = {}
        for c in hand_cards:
            m = re.match(r'([SHDC])(.+)', c)
            if m:
                rank = m.group(2)  # 点数部分（如 2, A, K, J, 10, ...）
                rank_counts.setdefault(rank, []).append(c)

        gid = 0

        # 识别炸弹：4 张或更多同点数
        for rank, cards in sorted(rank_counts.items(),
                                   key=lambda x: (-len(x[1]), x[0])):
            count = len(cards)
            if count >= 4:
                group_members[gid] = list(cards)
                for card in cards:
                    card_mask[card] = (gid, 1.0, count)
                group_type_map[gid] = "Bomb"
                gid += 1

        # 降级模式下不做同花顺/顺子/对子/三张识别，
        # 因为可能引入误判；仅保护炸弹不受拆解。

        return card_mask, group_type_map, group_members

    # ── GUA-XXX: 重建被平台截断的组合动作 ──────────────────────

    def _reconstruct_truncated_actions(
        self,
        game_state: Dict[str, Any],
        action_list: List,
    ) -> None:
        """平台 actionList 仅 10 项，优先单/对，截断 Trips/ThreeWithTwo/ThreePair/TwoTrips。

        组牌引擎已运行（self._card_mask / _group_type_map / _group_members 就绪）：
        遍历分组，查找应存在但 actionList 缺少的组合动作，就地追加。

        仅限领出轮（无待压 greater）重建：跟牌轮 follow actionList 由
        generate_follow_actions 保证只含能压 greater 的动作，若在此重建组合动作，
        会把无法压 greater 的 ThreeWithTwo/ThreePair/TwoTrips 混入候选，引擎选中后
        响应被平台判非法（-2）。
        """
        # 跟牌轮（存在待压 greater 且非领出）不重建，避免引入非法组合动作。
        greater = game_state.get("greaterAction")
        if greater and greater != ["PASS", "PASS", "PASS"] and greater[0] != "PASS":
            return
        if not self._group_type_map or not self._group_members or not self._card_mask:
            return
        hand_cards = game_state.get("handCards", [])
        if not hand_cards:
            return
        from src.v.nn.guards.v7_guards import get_card_rank

        existing: Set[Tuple[str, ...]] = set()
        for a in action_list:
            if isinstance(a, list) and len(a) >= 3 and isinstance(a[2], list):
                existing.add((a[0], tuple(sorted(str(c) for c in a[2]))))

        # 按类型收集分组 gid
        trip_twt_gids: List[int] = []
        pair_twt_gids: List[int] = []
        pair_tp_gids: List[int] = []
        trip_sp_gids: List[int] = []
        for gid, gtype in self._group_type_map.items():
            if gid < 0:
                continue
            if gtype == "trip_in_three_with_two":
                trip_twt_gids.append(gid)
            elif gtype == "pair_in_three_with_two":
                pair_twt_gids.append(gid)
            elif gtype == "pair_in_three_pair":
                pair_tp_gids.append(gid)
            elif gtype == "trip_in_steel_plate":
                trip_sp_gids.append(gid)

        added = 0

        # 1. ThreeWithTwo = trip_in_three_with_two + pair_in_three_with_two
        for t_gid in trip_twt_gids:
            t_cards = self._group_members.get(t_gid, [])
            if not t_cards:
                continue
            t_rank = get_card_rank(str(t_cards[0]))
            for p_gid in pair_twt_gids:
                p_cards = self._group_members.get(p_gid, [])
                if not p_cards:
                    continue
                combined = sorted(t_cards + p_cards)
                key = ("ThreeWithTwo", tuple(combined))
                if key in existing:
                    continue
                action_list.append(["ThreeWithTwo", t_rank, combined])
                existing.add(key)
                added += 1

        # 2. ThreePair = 3 × pair_in_three_pair
        if len(pair_tp_gids) >= 3:
            sorted_tp = sorted(pair_tp_gids)
            for i in range(0, len(sorted_tp), 3):
                if i + 2 >= len(sorted_tp):
                    break
                all_cards = sorted(
                    self._group_members.get(sorted_tp[i], [])
                    + self._group_members.get(sorted_tp[i + 1], [])
                    + self._group_members.get(sorted_tp[i + 2], [])
                )
                min_rank = min(
                    get_card_rank(str((self._group_members.get(sorted_tp[i]) or [""])[0])),
                    get_card_rank(str((self._group_members.get(sorted_tp[i + 1]) or [""])[0])),
                    get_card_rank(str((self._group_members.get(sorted_tp[i + 2]) or [""])[0])),
                )
                key = ("ThreePair", tuple(all_cards))
                if key in existing:
                    continue
                action_list.append(["ThreePair", min_rank, all_cards])
                existing.add(key)
                added += 1

        # 3. TwoTrips = 2 × trip_in_steel_plate
        if len(trip_sp_gids) >= 2:
            sorted_sp = sorted(trip_sp_gids)
            for i in range(0, len(sorted_sp), 2):
                if i + 1 >= len(sorted_sp):
                    break
                all_cards = sorted(
                    self._group_members.get(sorted_sp[i], [])
                    + self._group_members.get(sorted_sp[i + 1], [])
                )
                rank = get_card_rank(str((self._group_members.get(sorted_sp[i]) or [""])[0]))
                key = ("TwoTrips", tuple(all_cards))
                if key in existing:
                    continue
                action_list.append(["TwoTrips", rank, all_cards])
                existing.add(key)
                added += 1

        if added:
            self.logger.info(
                "GUA-XXX: 重建 %d 个截断的组合动作 (候选 %d → %d)",
                added, len(action_list) - added, len(action_list),
            )

    # ── GUA-063 Phase 2: 角色驱动前置过滤 ────────────────────

    def _group_consistency_filter(
        self,
        action_list: List,
        game_state: Dict[str, Any],
    ) -> Tuple[List, List[int]]:
        """角色驱动前置过滤：主攻时移除拆核心牌型的动作。

        过滤规则（设计文档 §三 第二层）：
          - 主攻/超强主攻：移除部分使用 core 组牌的动作
          - 助攻/超弱：走投喂规则条件放行
          - 安全阀：过滤后候选为空 → 全部放行
          - 硬例外（放行全部）：
            · 自己剩 ≤5 张
            · 对手剩 1-2 张
            · R16：队友剩 1 张 + 下家非 1 张（送单不卡 role filter）

        Args:
            action_list: Guard 过滤后的候选动作列表
            game_state: 游戏状态

        Returns:
            (filtered_actions, filter_map)
            filter_map[i] = 原始 action_list 中第 i 个动作在 filtered_actions 中的下标
                            （-1 表示被过滤掉）
        """
        if not action_list or self._card_mask is None or not self._card_mask:
            return action_list, list(range(len(action_list)))

        role = self._current_role or "主攻"

        # ── 决议 7: Solo 模式 — 队友已走完，强制主攻 ──
        greater_pos = game_state.get("greaterPos", -1)
        my_pos_for_filter = game_state.get("myPos", self.player_id)
        numofplayers = game_state.get("numofplayers", [])
        teammate_pos = (my_pos_for_filter + 2) % 4
        if (numofplayers and len(numofplayers) >= 4 and
                numofplayers[teammate_pos] == 0):
            role = "主攻"  # Solo 模式：强制主攻
            self.logger.debug("Solo 模式：队友已走完，role→主攻")

        # GUA-065: 队友控牌场景 → 当作助攻处理，不拆对子（队友可能接）
        # Solo 模式下不覆写（队友已走）
        elif greater_pos == teammate_pos:
            role = "助攻"

        # ── GUA-069 fix (2026-06-19): 助攻/超弱不再全部放行 ──
        # 旧行为: role in ("助攻", "超弱") → return 全部放行
        # Bug: yf2 hand 仅 1 炸+1 钢板 → power_score=1 → "超弱"
        #      4x4 炸弹被 Single C4 拆散（core 保护被跳过）
        # 新行为: 所有角色都应用 core 保护（炸弹/同花顺/顺子/三张不可拆）
        # 助攻/超弱角色继续走硬例外和安全阀，只是不能拆 core 牌组

        # 硬例外检查
        my_pos = game_state.get("myPos", self.player_id)
        hand_cards = game_state.get("handCards", []) or []

        # 自己剩 ≤5 张 → 放行全部
        if len(hand_cards) <= 5:
            self.group_filter_bypass_count += 1
            return action_list, list(range(len(action_list)))

        # 对手剩 1-2 张 → 放行全部
        opp1 = (my_pos + 1) % 4
        opp2 = (my_pos + 3) % 4
        public_info = game_state.get("publicInfo", [])
        opponent_low = False
        for opp_pos in (opp1, opp2):
            if opp_pos < len(public_info) and isinstance(public_info[opp_pos], dict):
                rest = public_info[opp_pos].get("rest", 27)
                if rest <= 2:
                    opponent_low = True
                    break
        if opponent_low:
            self.group_filter_bypass_count += 1
            return action_list, list(range(len(action_list)))

        # ── R16: 队友剩 1 张 + 下家非 1 张 → 放行全部（送单不卡 role filter）──
        # 设计文档 (2026-06-20)：队友剩 1 张，下家也剩 1 张 → 不放行
        #   → 我出单 → 下家跟 → 下家头游 ❌
        # 下家剩 ≥2 张 + 队友剩 1 张 → 放行
        #   → 我出单 → 下家跟或不跟 → 队友轮到 → 队友头游 ✅
        xia_jia_pos = (my_pos + 1) % 4
        if (numofplayers and len(numofplayers) >= 4
                and numofplayers[teammate_pos] == 1
                and numofplayers[xia_jia_pos] != 1):
            self.group_filter_bypass_count += 1
            self.logger.debug(
                "R16 放行: teammate=%d剩1张, 下家=%d剩%d张(非1) → 全部放行",
                teammate_pos, xia_jia_pos, numofplayers[xia_jia_pos],
            )
            return action_list, list(range(len(action_list)))

        # ── 过滤逻辑（角色分流） ──
        from src.v.nn.endgame.endgame_decide import (
            should_allow_counter_bomb_core_exempt,
            should_allow_gua239_single_probe,
        )

        keep_indices: List[int] = []
        removed_count = 0

        # 自由领出：禁止半组钢板 Trips / 半组三连对 Pair
        my_pos_lead = game_state.get("myPos", self.player_id)
        cur_pos_lead = game_state.get("curPos", -1)
        greater_pos_lead = game_state.get("greaterPos", -1)
        is_free_lead = (cur_pos_lead == -1) or (
            greater_pos_lead in (-1, my_pos_lead) and 0 <= my_pos_lead <= 3
        )

        # ── R12: 拆对子出单检查（有现成单张时禁止）──
        cur_rank = str(game_state.get("curRank", "2"))
        hand_cards_for_r12 = game_state.get("handCards", []) or []

        for idx, action in enumerate(action_list):
            # ── R12: 拆对子出单禁制（GUA-070，2026-06-21 修订）──
            # 有自然单张时不许拆普通对子；**例外**：级牌/大小王可拆对压牌
            action_cards_r12 = action[2] if isinstance(action, list) and len(action) >= 3 else []
            if len(action_cards_r12) == 1:
                card_info = self._card_mask.get(action_cards_r12[0])
                if card_info and card_info[2] == 2:  # 该单张从 gsize=2 的组拆出
                    from src.v.nn.guards.v7_guards import get_card_rank
                    card_rank = get_card_rank(str(action_cards_r12[0]))
                    r12_exempt = card_rank in ("HR", "SB") or card_rank == cur_rank
                    if (not r12_exempt
                            and self._has_any_natural_single(hand_cards_for_r12, cur_rank)):
                        removed_count += 1
                        continue

            if is_free_lead and self._is_partial_composite_lead(action):
                removed_count += 1
                continue

            broken_type = self._get_broken_core_type(
                action, self._card_mask, self._group_type_map, self._group_members)

            if broken_type is None:
                # 不拆任何 core → 保留
                keep_indices.append(idx)
            elif broken_type in ("Bomb", "StraightFlush"):
                # GUA-123：敌 sprint 反炸允许拆 core
                if should_allow_counter_bomb_core_exempt(
                    action, game_state, cur_rank,
                ):
                    keep_indices.append(idx)
                    continue
                # GUA-239：自由领出多手先单试探 → 拆 SF/顺子核心出最小天然单放行
                # （有意拆核心，见 _q1_multi_hand_lead_single_first 说明）
                if should_allow_gua239_single_probe(game_state):
                    keep_indices.append(idx)
                    continue
                # 炸弹/同花顺 → 永不放行（全角色）
                removed_count += 1
                continue
            # GUA-167: Straight 花色冲突（同 rank 不同花色）→ 放行
            elif (broken_type not in ("Bomb", "StraightFlush")
                  and self._is_straight_suit_only_break(
                      action, self._card_mask, self._group_type_map, self._group_members)):
                keep_indices.append(idx)
            elif role in ("主攻", "超强主攻"):
                # 主攻/超强主攻 → 一律过滤所有拆 core
                removed_count += 1
                continue
            elif role == "助攻":
                # 助攻 → 全部放行（GUA-069 之前的行为）
                keep_indices.append(idx)
            elif role == "超弱":
                # 超弱 → 投喂规则：顺子仅场景三放行，其他条件放行
                cur_rank = str(game_state.get("curRank", "2"))
                if broken_type == "straight":
                    if self._scenario_3_teammate_sprinting(game_state):
                        keep_indices.append(idx)
                    else:
                        removed_count += 1
                        continue
                else:
                    # pairs/trips/three_with_two 等 → 场景四（压牌）或场景一/二/三（喂牌）
                    action_type = str(action[0]) if isinstance(action, list) and len(action) > 0 else ""
                    action_rank = str(action[1]) if isinstance(action, list) and len(action) > 1 else ""
                    if (self._scenario_4_counter_press(game_state, action_type, action_rank)
                            or self._scenario_1_feed_single(game_state)
                            or self._scenario_2_feed_pair(game_state)
                            or self._scenario_3_teammate_sprinting(game_state)):
                        keep_indices.append(idx)
                    else:
                        removed_count += 1
                        continue
            else:
                # 未知角色 → 保守，保留
                keep_indices.append(idx)

        # 安全阀：过滤后候选为空 → 全部放行
        if not keep_indices:
            self.group_filter_bypass_count += 1
            self.logger.warning("安全阀：过滤后候选为空，全部放行 (role=%s)", role)
            return action_list, list(range(len(action_list)))

        if removed_count > 0:
            self.group_filtered_count += 1
            self.logger.info(
                "前置过滤: role=%s 移除 %d/%d 个拆核心动作, 保留 %d",
                role, removed_count, len(action_list), len(keep_indices),
            )

        # 构建 filtered_actions + filter_map
        filtered = [action_list[i] for i in keep_indices]
        # filter_map: 原始下标 → 新下标（-1 表示被过滤）
        filter_map = [-1] * len(action_list)
        for new_i, old_i in enumerate(keep_indices):
            filter_map[old_i] = new_i

        return filtered, filter_map

    @staticmethod
    def _multiset_overlap_used(action_cards: List[str], group_cards: List[str]) -> int:
        """动作牌与组内牌的多集合交集张数（重复牌串按枚计数）。"""
        from collections import Counter as _Counter
        action_c = _Counter(action_cards)
        group_c = _Counter(group_cards)
        return sum(min(action_c[c], group_c[c]) for c in group_c)

    @staticmethod
    def _build_card_memberships(
        group_members: Optional[Dict[int, List[str]]],
    ) -> Dict[str, Dict[int, int]]:
        """按牌串保留全部实例归属，值为 group_id → 实例数。"""
        memberships: Dict[str, Dict[int, int]] = {}
        for group_id, cards in (group_members or {}).items():
            for card in cards:
                card_key = str(card)
                group_counts = memberships.setdefault(card_key, {})
                group_counts[group_id] = group_counts.get(group_id, 0) + 1
        return memberships

    @staticmethod
    def _group_type_is_core(group_type: str) -> bool:
        """`pair` 是可重配普通对子，其余已登记组型按 core 处理。"""
        return bool(group_type) and group_type != "pair"

    @staticmethod
    def _group_break_cost(group_type: str) -> int:
        """实例分配时优先保留炸弹/同花顺，再保留复合结构。"""
        if group_type in ("Bomb", "StraightFlush"):
            return 1000
        if group_type in (
            "pair_in_three_pair",
            "trip_in_steel_plate",
            "trip_in_three_with_two",
            "pair_in_three_with_two",
        ):
            return 600
        if group_type in ("straight", "trips"):
            return 500
        return 700

    @staticmethod
    def _best_group_allocation(
        action_cards: List[str],
        card_mask: Dict[str, tuple],
        group_type_map: Dict[int, str],
        group_members: Dict[int, List[str]],
    ) -> Tuple[Dict[int, int], List[int]]:
        """为同名牌实例选择组归属，返回最小拆核分配及被拆 core gids。"""
        from collections import Counter as _Counter

        action_counts = _Counter(str(card) for card in action_cards)
        memberships = UltimateWinRateEngineV7._build_card_memberships(group_members)
        options_by_card: List[List[Dict[int, int]]] = []

        for card, required_count in action_counts.items():
            capacities = dict(memberships.get(card, {}))
            available_count = sum(capacities.values())
            if available_count < required_count:
                fallback_info = card_mask.get(card)
                fallback_group_id = fallback_info[0] if fallback_info else -2
                capacities[fallback_group_id] = (
                    capacities.get(fallback_group_id, 0)
                    + required_count - available_count
                )

            capacity_items = list(capacities.items())
            card_options: List[Dict[int, int]] = []

            def _enumerate_card_allocations(
                item_index: int,
                remaining_count: int,
                current: Dict[int, int],
            ) -> None:
                if item_index >= len(capacity_items):
                    if remaining_count == 0:
                        card_options.append(dict(current))
                    return
                group_id, capacity = capacity_items[item_index]
                max_take = min(capacity, remaining_count)
                for take_count in range(max_take + 1):
                    if take_count:
                        current[group_id] = take_count
                    else:
                        current.pop(group_id, None)
                    _enumerate_card_allocations(
                        item_index + 1,
                        remaining_count - take_count,
                        current,
                    )
                current.pop(group_id, None)

            _enumerate_card_allocations(0, required_count, {})
            if not card_options:
                card_options = [{-2: required_count}]
            options_by_card.append(card_options)

        allocations: List[Dict[int, int]] = [{}]
        for card_options in options_by_card:
            next_allocations: List[Dict[int, int]] = []
            for base_allocation in allocations:
                for card_allocation in card_options:
                    combined = dict(base_allocation)
                    for group_id, used_count in card_allocation.items():
                        combined[group_id] = combined.get(group_id, 0) + used_count
                    next_allocations.append(combined)
            allocations = next_allocations

        best_allocation: Dict[int, int] = {}
        best_broken: List[int] = []
        best_key: Optional[Tuple[int, int, int, int]] = None

        for allocation in allocations:
            broken_group_ids: List[int] = []
            full_core_cards = 0
            touched_group_count = 0
            for group_id, used_count in allocation.items():
                if group_id < 0 or used_count <= 0:
                    continue
                touched_group_count += 1
                total_count = len(group_members.get(group_id, []))
                group_type = group_type_map.get(group_id, "unknown")
                if not UltimateWinRateEngineV7._group_type_is_core(group_type):
                    continue
                if 0 < used_count < total_count:
                    broken_group_ids.append(group_id)
                elif total_count > 0 and used_count == total_count:
                    full_core_cards += total_count

            break_cost = sum(
                UltimateWinRateEngineV7._group_break_cost(
                    group_type_map.get(group_id, "unknown")
                )
                for group_id in broken_group_ids
            )
            allocation_key = (
                break_cost,
                len(broken_group_ids),
                -full_core_cards,
                touched_group_count,
            )
            if best_key is None or allocation_key < best_key:
                best_key = allocation_key
                best_allocation = allocation
                best_broken = broken_group_ids

        return best_allocation, best_broken

    @staticmethod
    def _group_total_size(
        gid: int,
        card_mask: Dict[str, tuple],
        group_members: Optional[Dict[int, List[str]]] = None,
    ) -> int:
        if group_members and gid in group_members:
            return len(group_members[gid])
        for info in card_mask.values():
            if info[0] == gid:
                return info[2]
        return 0

    def _is_partial_composite_lead(self, action) -> bool:
        """
        自由领出禁半组：钢板只出 Trips、三连对只出 Pair、TWT 只出 Trips/Pair。

        组牌把整型拆成子 gid 后，used==total 对单 gid 会误放行；此处按声明牌型拦截。
        """
        if not action or not isinstance(action, list) or len(action) < 3:
            return False
        declared = str(action[0] or "")
        action_cards = action[2] if isinstance(action[2], list) else []
        if not action_cards or self._card_mask is None:
            return False

        if self._group_members:
            allocation, _ = self._best_group_allocation(
                action_cards,
                self._card_mask,
                self._group_type_map or {},
                self._group_members,
            )
            touched_types = {
                (self._group_type_map or {}).get(group_id)
                for group_id, used_count in allocation.items()
                if group_id >= 0 and used_count > 0
            }
            touched_types.discard(None)

            # GUA-224: 完整复合动作豁免——声明是 TwoTrips/ThreePair/ThreeWithTwo
            # 且动作牌用满所有触及的复合子组（无部分使用）时，是完整牌型而非半组。
            # 组牌引擎常把钢板/三连对的子组归入 trip_in_three_with_two /
            # pair_in_three_with_two（如 777+888+55 中 777 被组进 TWT 子组），
            # 完整 TwoTrips(777888) 会因触及该子组被旧逻辑误拦 → 回退打低牌力 TWT
            # 被更大 TWT（如 KKK）压制。此处用 allocation 判定完整性后放行。
            if declared in ("TwoTrips", "ThreePair", "ThreeWithTwo"):
                partial = any(
                    0 < used_count < len(self._group_members.get(group_id, []))
                    for group_id, used_count in allocation.items()
                    if group_id >= 0 and used_count > 0
                )
                if not partial:
                    return False
        else:
            touched_types = set()
            for card in action_cards:
                info = self._card_mask.get(card)
                if info is None:
                    continue
                gid, is_core, _ = info
                if gid < 0 or not is_core:
                    continue
                gtype = (self._group_type_map or {}).get(gid)
                if gtype:
                    touched_types.add(gtype)

        if declared != "TwoTrips" and "trip_in_steel_plate" in touched_types:
            return True
        if declared != "ThreePair" and "pair_in_three_pair" in touched_types:
            return True
        if declared != "ThreeWithTwo" and (
            "trip_in_three_with_two" in touched_types
            or "pair_in_three_with_two" in touched_types
        ):
            return True
        return False

    def _is_straight_suit_only_break(
        self,
        action,
        card_mask: Dict[str, tuple],
        group_type_map: Dict[int, str],
        group_members: Optional[Dict[int, List[str]]] = None,
    ) -> bool:
        """Straight 是否仅因花色冲突（同 rank 不同花色）而拆核。

        GUA-167: actionList 的 Straight 使用了与 core straight 组相同的 rank 集
        但花色不同（如 D8 版 vs H8 版），且其他被拆的子组可通过花色交换修复。
        """
        if not action or not isinstance(action, list) or len(action) < 3:
            return False
        if str(action[0]) != "Straight":
            return False
        action_cards = action[2]
        if not action_cards or len(action_cards) != 5:
            return False
        if not group_members:
            return False

        from src.v.nn.guards.v7_guards import get_card_rank

        _, broken_group_ids = UltimateWinRateEngineV7._best_group_allocation(
            action_cards, card_mask, group_type_map, group_members,
        )
        if not broken_group_ids:
            return False

        for gid in broken_group_ids:
            gtype = group_type_map.get(gid, "")
            if gtype in ("Bomb", "StraightFlush"):
                return False

        action_ranks = set(get_card_rank(str(c)) for c in action_cards)
        straight_fixable = False
        for gid in broken_group_ids:
            if group_type_map.get(gid) == "straight":
                group_cards = group_members.get(gid, [])
                if len(group_cards) != 5:
                    continue
                group_ranks = set(get_card_rank(str(c)) for c in group_cards)
                if group_ranks == action_ranks:
                    straight_fixable = True
                    break

        if not straight_fixable:
            return False

        memberships = UltimateWinRateEngineV7._build_card_memberships(group_members)
        for gid in broken_group_ids:
            if group_type_map.get(gid) == "straight":
                continue

            used_from_group = [
                c for c in action_cards
                if memberships.get(str(c), {}).get(gid, 0) > 0
            ]
            if not used_from_group:
                continue

            used_rank = get_card_rank(str(used_from_group[0]))
            all_unused_same_rank = []
            for _gid, _cards in group_members.items():
                if _gid == gid:
                    for c in _cards:
                        if str(c) not in [str(ac) for ac in action_cards]:
                            all_unused_same_rank.append(c)
                elif _gid >= 0:
                    for c in _cards:
                        if (get_card_rank(str(c)) == used_rank
                                and str(c) not in [str(ac) for ac in action_cards]):
                            all_unused_same_rank.append(c)

            if not all_unused_same_rank:
                return False

        return True

    @staticmethod
    def _get_broken_core_type(
        action,
        card_mask: Dict[str, tuple],
        group_type_map: Dict[int, str],
        group_members: Optional[Dict[int, List[str]]] = None,
    ) -> Optional[str]:
        """检查一个动作破坏了哪种类型的 core 组牌。

        规则（设计文档 §八）：
          - 如果动作使用了某个 core 组的全部牌 → 不视为拆，放行
          - 如果动作使用了某个 core 组的部分牌 → 返回该组的类型字符串
          - 如果动作未使用任何 core 组牌 → 返回 None

        group_members 为 multiset 真源，支持同牌串多枚及 4~8 星炸。
        """
        if not action or (isinstance(action, list) and len(action) > 0
                          and str(action[0]).upper() == "PASS"):
            return None

        action_cards = action[2] if isinstance(action, list) and len(action) >= 3 else []
        if not action_cards:
            return None

        if group_members:
            _, broken_group_ids = UltimateWinRateEngineV7._best_group_allocation(
                action_cards,
                card_mask,
                group_type_map,
                group_members,
            )
            if broken_group_ids:
                protected_group_id = max(
                    broken_group_ids,
                    key=lambda group_id: UltimateWinRateEngineV7._group_break_cost(
                        group_type_map.get(group_id, "unknown")
                    ),
                )
                return group_type_map.get(protected_group_id, "unknown")
            return None

        touched_gids: set[int] = set()
        for card in action_cards:
            info = card_mask.get(card)
            if info is None:
                continue
            gid, is_core, _gsize = info
            if is_core >= 1.0 and gid >= 0:
                touched_gids.add(gid)

        for gid in touched_gids:
            total = UltimateWinRateEngineV7._group_total_size(gid, card_mask, group_members)
            used = sum(
                1 for card in action_cards
                if card_mask.get(card) and card_mask.get(card)[0] == gid
            )
            if 0 < used < total:
                return group_type_map.get(gid, "unknown")

        return None

    def _find_alternative_non_core_breaking_action(
        self,
        action_list: list,
        exclude_idx: int,
        card_mask: dict,
        group_type_map: dict,
        group_members: Optional[dict] = None,
        greater_action: Optional[list] = None,
    ) -> int:
        """GUA-176: 找 actionList 中第一个非炸、不拆核、非 exclude_idx 的动作。

        follow 模式（greater_action 有效且非 PASS）下，候选动作还须能合法
        压过 greater_action（同类型且 rank 更大）——否则该响应是非法牌型，
        Botzone 会判「1号玩家 undefined」并终止对局。
        """
        from src.v.nn.guards.v7_guards import CARD_RANK_ORDER

        follow = bool(
            greater_action
            and len(greater_action) >= 2
            and str(greater_action[0]).upper() != "PASS"
        )
        ga_type = str(greater_action[0]) if follow else ""
        ga_rank = str(greater_action[1]) if follow else ""
        for i, action in enumerate(action_list):
            if i == exclude_idx:
                continue
            if not action or len(action) < 2:
                continue
            if str(action[0]).upper() in ("PASS", "BOMB", "STRAIGHTFLUSH"):
                continue
            broken = self._get_broken_core_type(
                action, card_mask, group_type_map, group_members)
            if broken is not None:
                continue
            if follow:
                if str(action[0]) != ga_type:
                    continue
                a_rank = str(action[1]) if len(action) >= 2 else ""
                av = CARD_RANK_ORDER.get(a_rank, -1)
                gv = CARD_RANK_ORDER.get(ga_rank, -1)
                if av < 0 or gv < 0 or av <= gv:
                    continue
            return i
        return -1

    def _find_alternative_core_intact_bomb(
        self,
        action_list: list,
        exclude_idx: int,
        card_mask: dict,
        group_type_map: dict,
        group_members: Optional[dict] = None,
        greater_action: Optional[list] = None,
        cur_rank: str = "2",
    ) -> int:
        """GUA-211: 炸弹/同花顺推荐被组牌保护拦截后，回退找 actionList 中同是
        Bomb/SF 且不拆核心的候选。

        GUA-205 中局主动开炸时，_recommend_bomb_from_mask 按「牌点大优先」可能选中
        拆 Bomb/SF 核心的候选（如 SF/8 拆 Bomb 组 S8），GUA-075 拦截后原本直接回退
        PASS——而 actionList 里存在完整核心 SF/Bomb（如 SF/7 S3-S7、Bomb 8888）
        却不被尝试。本方法补上该回退：拦截的推荐是 Bomb/SF 时，找不拆核心的
        同类候选（follow 模式下还须能合法压过 greater_action），找不到才维持回退。

        Returns:
            候选下标；无则返回 -1。
        """
        from src.v.nn.guards.v7_guards import (
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )
        from src.v.nn.endgame.endgame_decide import _action_beats_greater

        follow = bool(
            greater_action
            and len(greater_action) >= 2
            and str(greater_action[0]).upper() != "PASS"
        )
        candidates: list = []
        for i, action in enumerate(action_list):
            if i == exclude_idx:
                continue
            if not action or len(action) < 3:
                continue
            if action[0] not in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                continue
            broken = self._get_broken_core_type(
                action, card_mask, group_type_map, group_members)
            if broken is not None:
                continue
            if follow and not _action_beats_greater(action, greater_action, cur_rank):
                continue
            candidates.append((i, action))
        if not candidates:
            return -1

        def _priority(item):
            _i, act = item
            cards = act[2] if len(act) >= 3 and isinstance(act[2], list) else []
            size = len(cards)
            strength = 9 if act[0] == ACTION_TYPE_STRAIGHT_FLUSH else size
            rank = str(act[1]) if len(act) >= 2 else ""
            return (
                -strength,
                -self.RANK_ORDER.get(rank, -1),
                tuple(sorted(str(c) for c in cards)),
            )

        best = min(candidates, key=_priority)
        return best[0]

    @staticmethod
    def _action_breaks_core(
        action,
        card_mask: Dict[str, tuple],
        group_members: Optional[Dict[int, List[str]]] = None,
        group_type_map: Optional[Dict[int, str]] = None,
    ) -> bool:
        """检查一个动作是否拆核心牌型。"""
        if group_type_map is None:
            group_type_map = {}
        return UltimateWinRateEngineV7._get_broken_core_type(
            action, card_mask, group_type_map, group_members
        ) is not None

    def _build_group_index(self, card_mask: Dict[str, tuple]) -> Dict[int, dict]:
        """从 group_members（优先）或 card_mask 构建 gid→组信息索引。"""
        groups: Dict[int, dict] = {}
        if self._group_members:
            for gid, cards in self._group_members.items():
                if gid < 0:
                    continue
                sample = card_mask.get(cards[0], (gid, 1.0, len(cards)))
                groups[gid] = {
                    "cards": list(cards),
                    "is_core": sample[1],
                    "size": len(cards),
                    "type": self._group_type_map.get(gid, "Unknown"),
                }
            return groups

        for card, (gid, is_core, gsize) in card_mask.items():
            if gid < 0:
                continue
            if gid not in groups:
                groups[gid] = {
                    "cards": [],
                    "is_core": is_core,
                    "size": gsize,
                    "type": self._group_type_map.get(gid, "Unknown"),
                }
            groups[gid]["cards"].append(card)
        return groups

    def _scatter_singles(self, card_mask: Dict[str, tuple]) -> List[str]:
        if self._group_members and -1 in self._group_members:
            return list(self._group_members[-1])
        return [c for c, (gid, _, _) in card_mask.items() if gid < 0]

    def _collect_single_follow_candidates(
        self,
        card_mask: Dict[str, tuple],
        groups: Dict[int, dict],
        hand_cards: List[str],
        cur_rank: str,
        *,
        allow_assist_pair_borrow: bool = False,
    ) -> List[str]:
        """Build single-follow candidates with an assist-only 99/TT/JJ borrow window."""
        from src.v.nn.guards.v7_guards import get_card_rank

        singles = list(self._scatter_singles(card_mask))
        pair_gtypes = ("pair", "pair_in_three_with_two", "pair_in_three_pair")
        # GUA-233: 级牌 trips（如 curRank=2 时的三个 2）跟压可拆单，牌力强过普通单。
        # 普通 trips 仍不拆（保持 GUA-081 整组牌理）。
        trips_gtypes = ("trips", "trip_in_three_with_two")
        respect_r12 = self._has_any_natural_single(hand_cards, cur_rank)
        assist_borrow_ranks = {"9", "T", "J"}

        for _gid, ginfo in groups.items():
            is_trips = ginfo["type"] in trips_gtypes
            if ginfo["type"] not in pair_gtypes and not is_trips:
                continue
            if respect_r12:
                for card in ginfo["cards"]:
                    rank = get_card_rank(str(card))
                    if rank in ("HR", "SB") or rank == cur_rank:
                        singles.append(card)
                    elif (
                        allow_assist_pair_borrow
                        and ginfo["is_core"] <= 0
                        and rank in assist_borrow_ranks
                    ):
                        singles.append(card)
                continue
            if ginfo["is_core"] <= 0:
                if is_trips:
                    raise ValueError("trips 组不应 is_core<=0")
                singles.extend(ginfo["cards"])
                continue
            for card in ginfo["cards"]:
                rank = get_card_rank(str(card))
                if rank in ("HR", "SB") or rank == cur_rank:
                    singles.append(card)
        return singles

    def _single_breaks_pair_under_r12(
        self, action: List, hand_cards: List[str], cur_rank: str
    ) -> bool:
        """GUA-075 主路径：拆普通对出单且手中有自然单张 → 应回退（与 R12 一致）。"""
        from src.v.nn.guards.v7_guards import get_card_rank

        if not self._card_mask or not action or len(action) < 3:
            return False
        action_cards = action[2] if isinstance(action[2], list) else []
        if len(action_cards) != 1:
            return False
        card_info = self._card_mask.get(action_cards[0])
        if not card_info or card_info[2] != 2:
            return False
        card_rank = get_card_rank(str(action_cards[0]))
        if card_rank in ("HR", "SB") or card_rank == cur_rank:
            return False
        return self._has_any_natural_single(hand_cards, cur_rank)

    # ── 决议 6: 投喂场景判断辅助方法 ──────────────────────

    RANK_ORDER = {"2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
                  "8": 6, "9": 7, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12}

    def _has_any_natural_single(self, hand_cards: List[str], cur_rank: str) -> bool:
        """GUA-070 R12：手牌中是否存在任何自然单张（card_mask group_id=-1 的牌）。

        自然单张 = 组牌引擎判定为散牌、未归入任何结构化牌组（对子/三张/顺子/炸弹等）的单张。
        如果存在自然单张，禁止拆对子出单（应优先出现成单张）。
        如果手牌全部是结构化牌型（无自然单张），允许拆对子。

        注：wild_cards（逢人配）也标记为 group_id=-1，但它们不算"废单"，
        因为 wild 随时可配入其他牌型。wild 不被计入自然单张。
        """
        if not self._card_mask:
            return False
        for card in hand_cards:
            info = self._card_mask.get(card)
            if info is None:
                continue
            gid, _is_core, gsize = info
            if gid == -1 and gsize == 1:
                # 检查是不是逢人配（wild card）
                # 逢人配不算是可出的废单，因为通常已配入牌型
                # 简单判定：如果在 singles 列表中 + 不是 wild → 自然单张
                rank = self._parse_rank(card)
                is_hr_or_sb = rank in ("HR", "SB")
                is_wild = f"H{cur_rank}" == card
                if not is_hr_or_sb and not is_wild:
                    return True
        return False

    def _has_natural_singles_below_cur_rank(self, hand_cards: List[str],
                                             cur_rank: str) -> bool:
        """手牌中是否存在 rank < curRank 且 count==1 的自然单张。"""
        from collections import Counter
        counts = Counter(self._parse_rank(c) for c in hand_cards)
        for r, cnt in counts.items():
            if r in ("HR", "SB"):
                continue  # 王不算"级牌以下废单"
            if r == cur_rank:
                continue  # 级牌本身不算
            if cnt == 1 and self._rank_below(r, cur_rank):
                return True
        return False

    def _has_natural_pairs_below_cur_rank(self, hand_cards: List[str],
                                           cur_rank: str) -> bool:
        """手牌中是否存在 rank < curRank 且 count>=2 的自然对子。"""
        from collections import Counter
        counts = Counter(self._parse_rank(c) for c in hand_cards)
        for r, cnt in counts.items():
            if r in ("HR", "SB"):
                continue
            if r == cur_rank:
                continue
            if cnt >= 2 and self._rank_below(r, cur_rank):
                return True
        return False

    @staticmethod
    def _parse_rank(card: str) -> str:
        """从牌串提取 rank。"""
        if card in ("SB", "HR", "BJ", "RJ"):
            # 归一化
            return {"BJ": "SB", "RJ": "HR"}.get(card, card)
        if len(card) >= 2 and card[0] in ("S", "H", "D", "C"):
            raw = card[1:]
            return "T" if raw == "10" else raw
        return card

    @staticmethod
    def _rank_below(rank: str, cur_rank: str) -> bool:
        """判断 rank 是否在 cur_rank 之下（级牌以下）。"""
        order = {"HR": 99, "SB": 98}  # 王在顶部
        order["2"] = 2
        order["3"] = 3
        order["4"] = 4
        order["5"] = 5
        order["6"] = 6
        order["7"] = 7
        order["8"] = 8
        order["9"] = 9
        order["T"] = 10
        order["J"] = 11
        order["Q"] = 12
        order["K"] = 13
        order["A"] = 14
        # cur_rank 本身等于级牌值
        cur_val = order.get(cur_rank, 6)
        r_val = order.get(rank, 0)
        return r_val < cur_val

    def _scenario_1_feed_single(self, game_state: Dict[str, Any]) -> bool:
        """场景一：队友出单 + 自己无级牌以下自然单张 → 允许拆对子送单。

        前置条件：
          1. 队友获得出牌权: greaterPos == teammate
          2. 队友出的牌型是单张: get_action_type(greaterAction) == "Single"
          3. 自己手中不存在级牌以下的自然单张
        """
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        if greater_pos != teammate:
            return False

        greater_action = game_state.get("greaterAction", [])
        if not greater_action or greater_action[0] == "PASS":
            return False

        # 检查队友是否刚获得出牌权（决议 3）
        if not self._teammate_just_gained_lead(game_state):
            return False

        # 检查牌型是否为 Single
        from src.v.nn.guards.v7_guards import get_action_type, ACTION_TYPE_SINGLE
        if get_action_type(greater_action) != ACTION_TYPE_SINGLE:
            return False

        # 检查自己有无级牌以下自然单张
        hand_cards = game_state.get("handCards", []) or []
        cur_rank = str(game_state.get("curRank", "2"))
        if self._has_natural_singles_below_cur_rank(hand_cards, cur_rank):
            return False  # 有现成废单 → 不拆牌

        return True

    def _scenario_2_feed_pair(self, game_state: Dict[str, Any]) -> bool:
        """场景二：队友出对 + 自己无级牌以下自然对子 → 允许拆三张/三带二送对。

        前置条件：
          1. 队友获得出牌权: greaterPos == teammate
          2. 队友出的牌型是对子: get_action_type(greaterAction) == "Pair"
          3. 自己手中不存在级牌以下的自然对子
        """
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        if greater_pos != teammate:
            return False

        greater_action = game_state.get("greaterAction", [])
        if not greater_action or greater_action[0] == "PASS":
            return False

        # 检查队友是否刚获得出牌权（决议 3）
        if not self._teammate_just_gained_lead(game_state):
            return False

        # 检查牌型是否为 Pair
        from src.v.nn.guards.v7_guards import get_action_type, ACTION_TYPE_PAIR
        if get_action_type(greater_action) != ACTION_TYPE_PAIR:
            return False

        # 检查自己有无级牌以下自然对子
        hand_cards = game_state.get("handCards", []) or []
        cur_rank = str(game_state.get("curRank", "2"))
        if self._has_natural_pairs_below_cur_rank(hand_cards, cur_rank):
            return False  # 有现成废对 → 不拆牌

        return True

    def _scenario_3_teammate_sprinting(self, game_state: Dict[str, Any]) -> bool:
        """场景三：队友只剩 7-8 张牌+自己无赢面 → 允许拆顺子/结构性牌型送。

        前置条件：
          1. 队友剩余手牌数: 7 或 8 张
          2. 自己角色为超弱（无赢面）
        """
        role = self._current_role or "主攻"
        if role != "超弱":
            return False

        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        public_info = game_state.get("publicInfo", [])
        if (isinstance(public_info, list) and teammate < len(public_info) and
                isinstance(public_info[teammate], dict)):
            rest = public_info[teammate].get("rest", 27)
            return rest in (7, 8)

        # fallback: 用 numofplayers
        numofplayers = game_state.get("numofplayers", [])
        if numofplayers and len(numofplayers) >= 4:
            return numofplayers[teammate] in (7, 8)

        return False

    def _scenario_4_counter_press(self, game_state: Dict[str, Any],
                                   action_type: str, action_rank: str) -> bool:
        """场景四：对手领出 + 同型可压 → 放行拆非炸弹/同花顺 core 的压牌动作。

        前置条件：
          1. greaterPos 是对手（非 -1，非自己，非队友）
          2. action type == greaterAction type（同型可压）
          3. action rank > greaterAction rank（能压过）
          4. 不是 solo 模式（solo 已强制主攻，不走超弱分支）
        """
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction", [])

        if greater_pos < 0:
            return False
        if greater_pos in (my_pos, teammate):
            return False
        if not greater_action or len(greater_action) < 2:
            return False

        ga_type, ga_rank = str(greater_action[0]), str(greater_action[1])
        if ga_type.upper() == "PASS":
            return False

        if action_type != ga_type:
            return False

        from src.v.nn.guards.v7_guards import CARD_RANK_ORDER
        my_val = CARD_RANK_ORDER.get(action_rank, -1)
        opp_val = CARD_RANK_ORDER.get(ga_rank, -1)
        if my_val < 0 or opp_val < 0 or my_val <= opp_val:
            return False

        numofplayers = game_state.get("numofplayers", [])
        if numofplayers and len(numofplayers) >= 4 and numofplayers[teammate] == 0:
            return False

        return True

    def _teammate_just_gained_lead(self, game_state: Dict[str, Any]) -> bool:
        """决议 3：队友是否刚获得出牌权（本轮第一次）。

        检查 prev_greaterPos（上一轮）是否不是队友，现在变成队友。
        如果队友连续持轮次，不重复触发 → 返回 False。
        """
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        if greater_pos != teammate:
            return False

        # 查看 history 中上一轮的 greaterPos
        history = game_state.get("history", [])
        if not history:
            # 无 history → 视为第一轮，触发
            return True

        # 找上一个非 PASS 的 greaterPos
        prev_greater_pos = -2  # 特殊值表示未找到
        for h in reversed(history[:-1]):  # 排除最后一个（就是当前 greater_action）
            gp = h.get("greaterPos", -1)
            if gp >= 0:
                prev_greater_pos = gp
                break

        # 如果上一轮不是队友控牌 → 队友刚获得出牌权
        return prev_greater_pos != teammate

    # ── GUA-063 Phase 3: 中局重分组触发 ──────────────────────

    def _check_midgame_triggers(self, game_state: Dict[str, Any],
                                 chosen_action) -> None:
        """检查是否触发中局重分组条件。

        触发条件（设计文档 §三 第三层）：
          - 核心牌型被破坏
          - 手牌降到 15 张 → 结构显著变化
          - 手牌降到 10 张 → 进入残局
          - 手牌降到 5 张 → 微调
          - 炸弹已全部消耗

        触发后记录日志并标记 _core_broken_since_regroup。
        下次 _run_grouping_engine 会因手牌 hash 变化自然重跑。
        """
        hand_cards = game_state.get("handCards", []) or []
        hand_size = len(hand_cards)

        # 手牌降量阈值
        thresholds = [15, 10, 5]
        for t in thresholds:
            if self._prev_hand_size > t >= hand_size:
                self._regroup_triggered_count += 1
                self.logger.debug(
                    "中局重分组触发: 手牌 %d→%d (阈值 %d)",
                    self._prev_hand_size, hand_size, t,
                )
                break

        # 检查当前动作是否拆了核心牌型
        if (self._card_mask and chosen_action and
                self._action_breaks_core(
                    chosen_action, self._card_mask, self._group_members)):
            self._core_broken_since_regroup = True
            self.logger.debug("核心牌型被破坏: 动作=%s", chosen_action[:2] if isinstance(chosen_action, list) else chosen_action)

        self._prev_hand_size = hand_size

    # ── 决议 8: 接风跟线 — 记忆队友末手牌型 ──────────────────

    def _ensure_mid_feed_tracker(self):
        if self._mid_feed_tracker is None:
            from src.v.nn.midgame_teammate_demand import MidgameTeammateDemandTracker
            self._mid_feed_tracker = MidgameTeammateDemandTracker()
        return self._mid_feed_tracker

    def _update_midgame_teammate_demand(self, game_state: Dict[str, Any]) -> None:
        """GUA-234 B：更新中期 demand / feed_P（观测层）。

        不驱动重组；仅写入 game_state 与日志，供后续阶段 D/E 消费。
        """
        tracker = self._ensure_mid_feed_tracker()
        my_pos = int(game_state.get("myPos", self.player_id) or 0)
        teammate = (my_pos + 2) % 4

        # 增量同步 MemoryTracker 出牌史（若有）
        mt = getattr(self, "_tracker", None) or game_state.get("_memory_tracker")
        if mt is not None and getattr(mt, "play_history", None):
            try:
                tracker.sync_from_play_history(mt.play_history, my_pos)
            except Exception as e:
                self.logger.debug("GUA-234 sync play_history 失败: %s", e)

        # 本回合 greater 快照（防重复记同一控牌动作）
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction") or []
        try:
            gkey = (greater_pos, tuple(greater_action) if isinstance(greater_action, list) else greater_action)
        except TypeError:
            gkey = (greater_pos, str(greater_action))
        if gkey != self._last_greater_key and greater_action:
            self._last_greater_key = gkey
            if greater_pos is not None and int(greater_pos) >= 0:
                is_pass = (
                    isinstance(greater_action, list)
                    and greater_action
                    and greater_action[0] == "PASS"
                )
                tracker.observe(int(greater_pos), greater_action, my_pos, is_pass=is_pass)

        nop = game_state.get("numofplayers") or []
        mate_rest = None
        if isinstance(nop, (list, tuple)) and len(nop) > teammate:
            try:
                mate_rest = int(nop[teammate])
            except (TypeError, ValueError):
                mate_rest = None

        feed_p = tracker.compute_feed_P(mate_rest)
        self._mid_feed_P = feed_p
        snap = tracker.snapshot()
        game_state["_mid_feed_P"] = feed_p
        game_state["_mid_feed_snapshot"] = snap
        game_state["_dynamic_regroup_enabled"] = bool(self._dynamic_regroup_enabled)
        if self._power_gate_tier:
            game_state["_power_gate_tier"] = self._power_gate_tier

        if feed_p or snap.get("twt_topped_out") or snap.get("straight_pressed_unreclaimed"):
            self.logger.info(
                "GUA-234 mid_feed: enabled=%s tier=%s P=%s snap=%s",
                self._dynamic_regroup_enabled,
                self._power_gate_tier,
                feed_p,
                {
                    k: snap.get(k)
                    for k in (
                        "raw_main",
                        "play_count",
                        "twt_topped_out",
                        "twt_pressed_unreclaimed",
                        "straight_pressed_unreclaimed",
                    )
                },
            )

    def _update_teammate_last_trick(self, game_state: Dict[str, Any]) -> None:
        """每轮 decide() 入口处调用，检测队友末手牌型并记忆。

        条件：上一轮 greaterPos == teammate 且 greaterAction 非 PASS。
        队友走完后清空（None）。
        """
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction", [])
        if greater_action is None:
            greater_action = []

        # 检查队友是否已走完 → 清空记忆
        numofplayers = game_state.get("numofplayers", [])
        if (numofplayers and len(numofplayers) >= 4 and
                numofplayers[teammate] == 0):
            self._teammate_last_trick_type = None
            return

        # 队友当前控牌且出了非 PASS 动作 → 记忆
        if greater_pos == teammate and greater_action and greater_action[0] != "PASS":
            from src.v.nn.guards.v7_guards import get_action_type
            trick_type = get_action_type(greater_action)
            if trick_type and trick_type != "PASS":
                self._teammate_last_trick_type = trick_type
                return

        # 回合切换（greaterPos 变化）→ 接风窗口关闭，清空
        # 但保留到 decide() 流程中用于接风重排

    def _apply_wind_catch_anchor(self, action_list: List,
                                  game_state: Dict[str, Any]) -> List:
        """决议 8：接风时优先跟队友末手牌型。

        条件：
          - greaterPos == teammate（队友刚获得出牌权，接风窗口）
          - _teammate_last_trick_type 非 None
          - 自己手里有对应牌型的现有牌（不拆 core）

        重排：将匹配牌型的动作提到前面。
        """
        if self._teammate_last_trick_type is None:
            return action_list

        greater_pos = game_state.get("greaterPos", -1)
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        if greater_pos != teammate:
            return action_list

        from src.v.nn.guards.v7_guards import get_action_type
        target_type = self._teammate_last_trick_type

        # 收集匹配牌型且不拆 core 的动作
        matched = []
        others = []
        for idx, act in enumerate(action_list):
            act_type = get_action_type(act)
            if act_type == target_type:
                # 检查是否拆 core
                if (self._card_mask and
                        not self._action_breaks_core(act, self._card_mask, self._group_members)):
                    matched.append(idx)
                    continue
            others.append(idx)

        if not matched:
            return action_list  # 无匹配牌型 → 让 NN 自由选

        # 重排：匹配牌型在前
        ordered_indices = matched + others
        reordered = [action_list[i] for i in ordered_indices]
        self.logger.debug("接风跟线: 队友末手=%s, 匹配 %d 个动作提前",
                          target_type, len(matched))
        return reordered

    # ── 决议 10: 方案 C — 基于队友余牌数的投喂策略 ──────────

    def _try_teammate_feeding(self, action_list: List,
                               game_state: Dict[str, Any]) -> List:
        """方案 C 投喂策略（在 _group_consistency_filter 之后、NN 之前调用）。

        两阶段：
          阶段 1（硬约束）：_should_rescue_teammate() → 删 PASS，强制压制
          阶段 2（软引导）：_pick_feeding_action() → 按余牌数选最小现成牌型

        Returns:
            处理后的 action_list（可能删 PASS / 重排投喂动作在前）
        """
        role = self._current_role or "主攻"
        # 仅弱牌角色触发
        if role not in ("超弱", "助攻"):
            return action_list

        # D5: 退出条件检查
        if self._feeding_should_abort(game_state):
            return action_list

        # 阶段 1: 被动侧解围 — 对手压队友时，删 PASS 强制压制
        rescued = self._should_rescue_teammate(action_list, game_state)
        if rescued is not None:
            return rescued

        # 阶段 2: 主动侧投喂 — 按队友余牌数选最小现成牌型
        return self._pick_feeding_action(action_list, game_state)

    def _feeding_should_abort(self, game_state: Dict[str, Any]) -> bool:
        """D5：投喂退出条件检查。优先级：防对手跑 > 自己冲线 > 投喂队友。"""
        my_pos = game_state.get("myPos", self.player_id)

        # 优先级 1: 对手剩余 ≤ 2 张 → 先防对手跑
        opp1 = (my_pos + 1) % 4
        opp2 = (my_pos + 3) % 4
        public_info = game_state.get("publicInfo", [])
        for opp_pos in (opp1, opp2):
            if (isinstance(public_info, list) and opp_pos < len(public_info) and
                    isinstance(public_info[opp_pos], dict)):
                if public_info[opp_pos].get("rest", 27) <= 2:
                    return True

        # 优先级 2: 自己剩余 ≤ 5 张 → 先自己冲线
        hand_cards = game_state.get("handCards", []) or []
        if len(hand_cards) <= 5:
            return True

        return False

    def _should_rescue_teammate(self, action_list: List,
                                 game_state: Dict[str, Any]) -> Optional[List]:
        """阶段 1（硬约束）：对手压队友 → 删 PASS，强制用更大牌或炸弹压制。

        Returns:
            处理后的 action_list，或 None（不触发解围）。
        """
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction", [])
        if isinstance(greater_action, str):
            import ast
            try:
                greater_action = ast.literal_eval(greater_action)
            except (ValueError, SyntaxError):
                greater_action = []
        if greater_action is None:
            greater_action = []

        # 前置条件：对手控牌（greaterPos 是对手）
        opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
        if greater_pos not in opponent_positions:
            return None

        if not greater_action or greater_action[0] == "PASS":
            return None

        # 检查队友是否被压（队友余牌数暗示牌型，但队友 PASS 了）
        # 简化：只要对手控牌 + 队友余牌 ≤ 10 → 尝试解围
        numofplayers = game_state.get("numofplayers", [])
        if not numofplayers or len(numofplayers) < 4:
            return None
        if numofplayers[teammate] > 10 or numofplayers[teammate] == 0:
            return None

        # 特别强制：队友余牌 ≤5 + 对手出 A 级以上 5 张类牌型
        from src.v.nn.guards.v7_guards import (get_action_type, get_card_value,
                                                ACTION_TYPE_STRAIGHT,
                                                ACTION_TYPE_THREE_WITH_TWO,
                                                ACTION_TYPE_PASS)
        cur_rank = str(game_state.get("curRank", "2"))
        greater_type = get_action_type(greater_action)
        force_rescue = False
        if (numofplayers[teammate] <= 5 and
                greater_type in (ACTION_TYPE_STRAIGHT, ACTION_TYPE_THREE_WITH_TWO)):
            # 检查对手出的是否 A 级以上
            if greater_action[1] if len(greater_action) >= 2 else "" in ("A", "B", "R", "SB", "HR"):
                force_rescue = True

        # 找 PASS 索引
        pass_idx = None
        has_counter = False
        for i, act in enumerate(action_list):
            if get_action_type(act) == ACTION_TYPE_PASS:
                pass_idx = i
            elif not is_bomb_straight_flush_for_check(act):
                # 有非炸弹非 PASS 的动作 → 可以压制
                has_counter = True

        if not has_counter and not force_rescue:
            # 无压制牌 + 非强制 → 不删 PASS
            return None

        if pass_idx is not None:
            # D2: 重排 PASS 到末尾（等价于硬删，但保持 action_map 有效）
            if len(action_list) > 1:
                non_pass = [i for i in range(len(action_list)) if i != pass_idx]
                reordered = non_pass + [pass_idx]
                self.logger.debug("投喂阶段1: PASS 移至末尾强制压制对手, 队友余牌=%d",
                                  numofplayers[teammate])
                return [action_list[i] for i in reordered]

        return None

    def _pick_feeding_action(self, action_list: List,
                              game_state: Dict[str, Any]) -> List:
        """阶段 2（软引导）：按队友余牌数选最小现成牌型，提到前面。

        D3：多候选选最小牌。D4：5 张有反馈路径。
        """
        my_pos = game_state.get("myPos", self.player_id)
        teammate = (my_pos + 2) % 4
        numofplayers = game_state.get("numofplayers", [])
        if not numofplayers or len(numofplayers) < 4:
            return action_list
        teammate_rest = numofplayers[teammate]
        if teammate_rest == 0:
            return action_list  # 队友已走完，不投喂

        from src.v.nn.guards.v7_guards import (get_action_type,
                                                ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR,
                                                ACTION_TYPE_TRIPS,
                                                ACTION_TYPE_THREE_WITH_TWO,
                                                ACTION_TYPE_STRAIGHT,
                                                ACTION_TYPE_STRAIGHT_FLUSH)

        # 按队友余牌数映射目标牌型
        target_types = self._feeding_target_types(teammate_rest, game_state)
        if not target_types:
            return action_list

        # D4: 5 张反馈路径 — 已试探过 5 张类，对手没接 → 降档送单
        if teammate_rest == 5 and self._feed_five_card_tried:
            target_types = [ACTION_TYPE_SINGLE]
            self._feed_five_card_tried = False  # 重置

        # 收集匹配牌型且不拆 core 的动作
        from src.v.nn.guards.v7_guards import get_card_value, get_action_rank
        cur_rank = str(game_state.get("curRank", "2"))
        matched = []  # (index, value, is_five_card)
        others = []

        for idx, act in enumerate(action_list):
            act_type = get_action_type(act)
            if act_type in target_types:
                # 检查是否拆 core
                if (self._card_mask and
                        not self._action_breaks_core(act, self._card_mask, self._group_members)):
                    # D3: 记录值用于选最小
                    val = 0
                    if act_type == ACTION_TYPE_SINGLE:
                        val = get_card_value(act[0], cur_rank) if len(act) >= 1 else 99
                    elif act_type == ACTION_TYPE_PAIR:
                        rank = get_action_rank(act)
                        from src.v.nn.guards.v7_guards import CARD_RANK_ORDER
                        val = CARD_RANK_ORDER.get(rank, 99)
                    else:
                        val = len(act[2]) if len(act) >= 3 else 99
                    is_five = act_type in (ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT)
                    matched.append((idx, val, is_five))
                    continue
            others.append(idx)

        if not matched:
            # 无匹配牌型 → D4: 5 张时记录试探失败
            if teammate_rest == 5 and not self._feed_five_card_tried:
                self._feed_five_card_tried = True
            return action_list

        # D3: 选最小
        matched.sort(key=lambda x: x[1])
        if teammate_rest == 5 and not self._feed_five_card_tried:
            # 优先选 5 张类（三带二/顺子）
            five_card_matches = [m for m in matched if m[2]]
            if five_card_matches:
                best = five_card_matches[0]
                self._feed_five_card_tried = True  # 标记已试探
            else:
                best = matched[0]
        else:
            best = matched[0]

        # 重排：最优投喂在前
        best_idx = best[0]
        ordered = [i for i, _, _ in matched] + others
        # 但确保 best 在最前面
        if ordered and ordered[0] != best_idx:
            ordered.remove(best_idx)
            ordered.insert(0, best_idx)

        reordered = [action_list[i] for i in ordered]
        self.logger.debug("投喂阶段2: 队友余牌=%d 目标牌型=%s 候选=%d 选最小idx=%d",
                          teammate_rest, target_types, len(matched), best_idx)
        return reordered

    def _feeding_target_types(self, teammate_rest: int,
                               game_state: Dict[str, Any]) -> List[str]:
        """按队友余牌映射投喂牌型；中期优先 _mid_feed_P（GUA-234 D）。"""
        from src.v.nn.dynamic_regroup import resolve_feed_prefer_types

        prefer = resolve_feed_prefer_types(
            teammate_rest,
            game_state.get("_mid_feed_P"),
        )
        if prefer:
            return prefer

        from src.v.nn.guards.v7_guards import (ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR,
                                                ACTION_TYPE_TRIPS,
                                                ACTION_TYPE_THREE_WITH_TWO,
                                                ACTION_TYPE_STRAIGHT)

        if teammate_rest in (10, 9):
            return [ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT]
        elif teammate_rest in (8, 7, 6):
            return [ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR]
        elif teammate_rest == 5:
            return [ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT]
        elif teammate_rest == 4:
            return [ACTION_TYPE_PAIR]
        elif teammate_rest == 3:
            return [ACTION_TYPE_TRIPS]
        elif teammate_rest == 2:
            return [ACTION_TYPE_PAIR]
        elif teammate_rest == 1:
            return [ACTION_TYPE_SINGLE]
        else:
            return []

    def _model_decision(self, game_state: Dict[str, Any], action_list: List) -> Optional[int]:
        """
        使用模型进行决策

        Args:
            game_state: 游戏状态
            action_list: 可选动作列表

        Returns:
            动作索引，如果失败返回None
        """
        try:
            # 提取特征（与 bc_dataset.py 训练对齐）
            features = self._extract_features(game_state, action_list)
            if features is None:
                return None

            # 转换为张量
            features_tensor = torch.FloatTensor(features).unsqueeze(0).to(self.device)

            # 模型预测
            with torch.no_grad():
                predictions = self.model(features_tensor)
                action_logits = predictions['action_logits']
                probabilities = torch.softmax(action_logits, dim=-1)

            # 选择最佳动作
            action_probs = probabilities[0][:len(action_list)]
            self._last_model_scores = [
                (i, float(action_probs[i].item()))
                for i in range(len(action_list))
            ]
            self._replay_record(
                "model_scores",
                {"scores": list(self._last_model_scores)},
            )
            best_action_idx = torch.argmax(action_probs).item()

            # 验证动作索引
            if 0 <= best_action_idx < len(action_list):
                confidence = action_probs[best_action_idx].item()
                self._last_nn_confidence = confidence
                self.logger.debug(f"模型决策: 动作{best_action_idx}, 置信度: {confidence:.3f}")
                return best_action_idx
            else:
                self.logger.warning(f"模型返回无效动作索引: {best_action_idx}")
                return None

        except Exception as e:
            self.logger.error(f"模型决策失败: {e}")
            return None

    def _extract_features(self, game_state: Dict[str, Any], action_list: List) -> Optional[np.ndarray]:
        """
        从游戏状态中提取 512 维特征向量（与 bc_dataset.py 训练管线对齐）。

        维度分段（512 维）：
          0-123:   extract_static_features (124)
          124-187: extract_dynamic_features (64)
          188-195: extract_state_belief (8)  — GUA-050
          196-228/243: MemoryTracker.state_vector — GUA-052 + GUA-054/061
          229-240/244-255: rule_memory (12) — GUA-072 M5
        """
        try:
            if not FEATURE_IMPORT_OK:
                return self._fallback_extract(game_state)

            self._replay_history_to_tracker(game_state)

            static_features = extract_static_features(game_state)
            features = np.zeros(TARGET_FEATURE_DIM, dtype=np.float32)
            features[:STATIC_STATE_DIM] = static_features

            try:
                dynamic = extract_dynamic_features(game_state, static_features)
                features[STATIC_STATE_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM] = dynamic
            except Exception:
                pass

            try:
                belief = extract_state_belief(game_state)
                features[STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM:STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM] = belief
            except Exception:
                pass

            # ── GUA-063: MemoryTracker + 组牌特征拼接 ──
            mt_start = STATIC_STATE_DIM + DYNAMIC_HIDDEN_DIM + BELIEF_DIM
            if self.use_grouping_engine:
                # 24 维追踪 + 24 维组牌特征（由 _run_grouping_engine 缓存）→ 48 维
                try:
                    tracking = self._get_tracker_state()  # 24 维，不含组牌
                    grouping = self._grouping_features
                    if grouping is None or len(grouping) == 0:
                        grouping = np.zeros(24, dtype=np.float32)
                    features[mt_start:mt_start + 24] = tracking[:24]
                    features[mt_start + 24:mt_start + 48] = grouping[:24]
                except Exception:
                    pass
            else:
                # 向后兼容：使用 get_state_vector 含 grouping_scanner（33 维）
                try:
                    mt_state = self._get_tracker_state(game_state)
                    mt_dim = MEMORY_TRACKER_DIM
                    features[mt_start:mt_start + mt_dim] = mt_state[:mt_dim]
                except Exception:
                    pass

            try:
                from src.v.nn.training.bc_dataset import rule_memory_feature_start
                from src.v.nn.features.rule_card_counter import (
                    RULE_MEMORY_DIM,
                    extract_rule_memory_features,
                    create_counter_from_tracker,
                )
                if self._tracker is not None:
                    rm_vec = extract_rule_memory_features(
                        create_counter_from_tracker(self._tracker).get_belief(game_state)
                    )
                else:
                    rm_vec = game_state.get("_rule_memory_vec") or [0.0] * RULE_MEMORY_DIM
                rm_start = rule_memory_feature_start(self.use_grouping_engine)
                features[rm_start:rm_start + RULE_MEMORY_DIM] = rm_vec[:RULE_MEMORY_DIM]
            except Exception:
                pass

            return features

        except Exception as e:
            self.logger.error(f"特征提取失败: {e}")
            return None

    def _fallback_extract(self, game_state: Dict[str, Any]) -> Optional[np.ndarray]:
        """Fallback 简化特征提取（特征工程导入失败时使用）。"""
        try:
            features = []
            my_pos = game_state.get("myPos", self.player_id)
            cur_pos = game_state.get("curPos", -1)
            greater_pos = game_state.get("greaterPos", -1)
            for pos, feat_list in [(my_pos, 4), (cur_pos, 4), (greater_pos, 4)]:
                feat = [0] * 4
                if 0 <= pos < 4:
                    feat[pos] = 1
                features.extend(feat)
            features.append(len(game_state.get("handCards", [])))
            public_info = game_state.get("publicInfo", [])
            for i in range(4):
                rest = DEFAULT_REST_CARDS
                if i < len(public_info) and isinstance(public_info[i], dict):
                    rest = public_info[i].get("rest", DEFAULT_REST_CARDS)
                features.append(rest)
            rank_map = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
                       "9": 9, "T": 10, "J": 11, "Q": 12, "K": 13, "A": 14}
            for rk in ["curRank", "selfRank", "oppoRank"]:
                features.append(rank_map.get(game_state.get(rk, "2"), 2))
            features.append(len(game_state.get("actionList", [])))
            for fk in ["curAction", "greaterAction"]:
                features.append(len(game_state.get(fk, [])))
            if len(features) < TARGET_FEATURE_DIM:
                features.extend([0] * (TARGET_FEATURE_DIM - len(features)))
            else:
                features = features[:TARGET_FEATURE_DIM]
            return np.array(features, dtype=np.float32)
        except Exception as e:
            self.logger.error(f"Fallback 特征提取失败: {e}")
            return None

    def _heuristic_select(self, game_state: Dict[str, Any], action_list: List) -> int:
        """
        GUA-071: 启发式动作选择 — Layer 2（软排序）。

        ── 三层决策管道（GUA-073 整理）────
          Layer 1: Guard (v7_guards.py)     → 硬排除错误动作
          Layer 2: Heuristic (本方法)        → 软排序合理动作 ← 你在这里
          Layer 3: validate_decision         → 安全网兜底

        职责：在 Guard 保留的动作中，按"哪个更好"排序。
        不要重复 Layer 1 的判断——Guard 已经删了不该有的动作，
        heuristic 只需在剩下的里选最优。

        核心原则：组局引擎已经算好了最优牌型结构，出牌必须按组局节奏走。
        如果选了一个拆局的动作，组局就白组了。

        优先级（分高者胜）：
        ① 组局一致性：动作所有牌来自同一个 core 组（+10000，碾压一切）
        ② 队友控牌时 PASS 优先（+200），非炸（+100）
        ③ 对手急眼（剩牌≤4）时炸弹优先（+800），PASS 降权（-100）
        ④ 非 PASS > PASS（+50）
        ⑤ 同分时取起始 rank 最小的（节约牌力）
        ⑧ 存在合法同型非炸可压时，Bomb/StraightFlush 不进入评分
        ⑨ GUA-082 R12：有自然单张时拆普通对出单重罚并跳过（回退路径兜底）

        Args:
            game_state: 游戏状态
            action_list: 候选动作列表（post Guard + post _group_consistency_filter）

        Returns:
            最优动作索引
        """
        if not action_list:
            return 0

        from src.v.nn.guards.v7_guards import (
            get_action_type, get_action_rank, get_card_value, get_card_rank,
            ACTION_TYPE_PASS, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
            ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS,
            ACTION_TYPE_THREE_PAIR, ACTION_TYPE_TWO_TRIPS,
            ACTION_TYPE_THREE_WITH_TWO, ACTION_TYPE_STRAIGHT,
        )

        my_pos = game_state.get("myPos", self.player_id)
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction", []) or []
        cur_rank = str(game_state.get("curRank", "2"))
        teammate_pos = (my_pos + 2) % 4
        numofplayers = game_state.get("numofplayers", []) or [27, 27, 27, 27]
        hand_cards = game_state.get("handCards", []) or []
        my_hand_size = len(hand_cards)
        is_early_game = (my_hand_size > 12)
        teammate_controls = (
            greater_pos == teammate_pos
            and greater_action
            and greater_action[0] != "PASS"
        )

        # ── GUA-149 soft guard: 仅剩 1 个非 PASS 合法候选时禁止 PASS ──
        # R-D05: 组牌去单化后散牌极少，heuristic 打分中 PASS 靠
        # 队友控牌 +200 / 对手双HR推断 +350 叠分，远超非组局一致的非PASS动作
        # （如 Single/CJ 仅得 50-9=41），导致手牌僵死 3 轮不动。
        # 硬守卫：唯一非 PASS 候选 → 跳过所有打分，直接选中。
        #
        # v2 修订 (GUA-149-v2): 加入场景感知，避免早期/队友控牌时浪费炸弹。
        #   R-D29: 主攻角色在跟牌场景下，前置过滤杀光所有 TWT 选项，
        #   只剩 Bomb 和 PASS，GUA-149 强制选炸 → 第一轮浪费4张J。
        #   修复：早期+非炸更大动作+队友有牌力 → 允许 PASS。
        _BOMB_TYPES = {ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH}
        non_pass_count = 0
        non_pass_idx = -1
        for i, act in enumerate(action_list):
            if get_action_type(act) != ACTION_TYPE_PASS:
                non_pass_count += 1
                non_pass_idx = i
        if non_pass_count == 1 and non_pass_idx >= 0:
            non_pass_act = action_list[non_pass_idx]
            non_pass_type = get_action_type(non_pass_act)

            # ── 场景感知：是否允许 PASS ──
            # 条件 A: 对手出的是非炸弹牌型（TWT/顺子/对子/单张等）
            #         用炸弹去压非炸弹是大材小用 → 允许 PASS
            # 条件 B: 早期游戏（手牌 > 12），炸弹应保留到关键时刻
            # 条件 C: 队友控牌（teammate_controls），让队友继续
            # 条件 D: 队友还有足够牌力（剩余 > 6 张），不需要帮炸
            greater_type_for_149 = get_action_type(greater_action) if greater_action else ACTION_TYPE_PASS
            is_wasteful_bomb = (
                non_pass_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)
                and greater_type_for_149 not in (*_BOMB_TYPES, ACTION_TYPE_PASS)
            )
            teammate_rest = numofplayers[teammate_pos] if len(numofplayers) > teammate_pos else 0
            should_allow_pass_149 = (
                (is_wasteful_bomb and is_early_game)
                or (teammate_controls and is_early_game)
                or (is_wasteful_bomb and teammate_rest > 6)
            )
            if not should_allow_pass_149:
                self.logger.debug(
                    "GUA-149 soft guard: only 1 non-PASS candidate (idx=%d, type=%s), "
                    "force-selecting it over PASS to prevent hand freeze "
                    "(wasteful=%s early=%s teammate_rest=%d)",
                    non_pass_idx, non_pass_type,
                    is_wasteful_bomb, is_early_game, teammate_rest,
                )
                return non_pass_idx
            else:
                self.logger.debug(
                    "GUA-149 soft guard: only 1 non-PASS candidate (idx=%d, type=%s), "
                    "but context ALLOWS PASS (wasteful=%s early=%s teammate_rest=%d) "
                    "\u2192 fall through to scoring",
                    non_pass_idx, non_pass_type,
                    is_wasteful_bomb, is_early_game, teammate_rest,
                )
                # 继续进入打分流程，不强制选非 PASS

        # ── 场景判断（teammate_controls / is_early_game 已在 GUA-149 前定义）──
        opp_left = (my_pos + 1) % 4
        opp_right = (my_pos + 3) % 4
        opp_in_danger = (
            (len(numofplayers) > opp_left and 0 < numofplayers[opp_left] <= 4)
            or (len(numofplayers) > opp_right and 0 < numofplayers[opp_right] <= 4)
        )

        belief = game_state.get("_belief") or {}
        belief_hand_counts = belief.get("hand_counts") or numofplayers
        joker_belief = self._joker_belief_from_state(game_state)
        hr_with_opponents = joker_belief["hr_with_opponents"]

        # ── 预扫描：用于规则 ⑥⑦ ──
        # 对手出牌的 rank value
        greater_val = 0
        if greater_action and greater_action[0] != "PASS":
            ga_type = get_action_type(greater_action)
            if ga_type == ACTION_TYPE_SINGLE:
                ga_cards = greater_action[2] if len(greater_action) >= 3 and isinstance(greater_action[2], list) else greater_action
                ga_card = ga_cards[0] if ga_cards else (greater_action[0] if len(greater_action) >= 1 else "")
                greater_val = get_card_value(str(ga_card), cur_rank)
        # 是否有 SB 单张可用（能压对手）
        has_sb_single = False
        for act in action_list:
            if get_action_type(act) == ACTION_TYPE_SINGLE:
                cards = act[2] if len(act) >= 3 and isinstance(act[2], list) else act
                card = cards[0] if cards else (act[0] if len(act) >= 1 else "")
                if get_card_rank(str(card)) == "SB" and get_card_value(str(card), cur_rank) > greater_val:
                    has_sb_single = True
                    break
        # ── GUA-071 预扫描：同型非炸弹计数器 ──
        # 检测 action_list 中是否有与对手同牌型的非炸弹动作
        # 用于规则⑧（有同型可压不该炸）和后置炸弹滥用覆盖
        # _BOMB_TYPES defined above inside GUA-149-v2 guard
        greater_type = ""
        if greater_action and greater_action[0] != "PASS":
            greater_type = get_action_type(greater_action)
        has_same_type_nonbomb = False
        if greater_type and greater_type not in _BOMB_TYPES and greater_type != ACTION_TYPE_PASS:
            for act in action_list:
                at = get_action_type(act)
                if at == greater_type and at not in _BOMB_TYPES:
                    has_same_type_nonbomb = True
                    break

        # ── 组局一致性检查 ──
        mask = self._card_mask or {}

        def _is_group_consistent(action) -> bool:
            """动作所有牌是否来自同一个 core 组（group_id ≥ 0）。"""
            if not action or action[0] == "PASS":
                return True  # PASS 不干扰组局
            # 兼容平台格式 [type, rank, [cards]] 和简式 ["S2"]
            cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
            if not cards:
                return False
            if len(cards) == 1:
                return False
            if self._group_members:
                allocation, broken_group_ids = self._best_group_allocation(
                    [str(card) for card in cards],
                    mask,
                    self._group_type_map or {},
                    self._group_members,
                )
                if broken_group_ids:
                    return False
                allocated_group_ids = {
                    group_id
                    for group_id, used_count in allocation.items()
                    if group_id >= 0 and used_count > 0
                }
                allocated_core_cards = sum(
                    used_count
                    for group_id, used_count in allocation.items()
                    if group_id >= 0
                )
                return (
                    len(allocated_group_ids) == 1
                    and allocated_core_cards == len(cards)
                )
            group_ids = set()
            for c in cards:
                c = str(c)
                entry = mask.get(c)
                if entry:
                    gid, _, _ = entry
                    if gid >= 0:
                        group_ids.add(gid)
            # 所有牌属于同一个 core 组 → 组局一致
            return len(group_ids) == 1

        # ── 拆局扣分计算 ──
        def _group_break_penalty(action) -> int:
            """返回负分：拆局越严重（撕散越多 core 组），扣分越多。"""
            if not action or action[0] == "PASS":
                return 0
            cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
            if not cards:
                return -500
            if self._group_members:
                _, broken_group_ids = self._best_group_allocation(
                    [str(card) for card in cards],
                    mask,
                    self._group_type_map or {},
                    self._group_members,
                )
                return -300 * len(broken_group_ids)
            group_ids = set()
            for c in cards:
                c = str(c)
                entry = mask.get(c)
                if entry:
                    gid, is_core, _ = entry
                    if gid >= 0 and is_core > 0:
                        group_ids.add(gid)  # 只统计 core 组
            n_broken = len(group_ids)
            if n_broken <= 1:
                return 0
            # 每多撕一个 core 组，扣 300 × 数量
            return -(n_broken - 1) * 300

        # ── 计分 ──
        RANK_KEY: Dict[str, int] = {
            "2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
            "8": 6, "9": 7, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12,
            "SB": 16, "HR": 17,  # GUA-071: joker 也入 rank key
        }
        # 级牌(curRank)的 rank 应高于 A(12)；对齐 get_card_value curRank=15
        if cur_rank and cur_rank not in ("SB", "HR", "R", "B"):
            RANK_KEY[cur_rank] = 15
        # 早期出王压牌的最大允许级差
        JOKER_MAX_GAP = 6

        # ── GUA-150: 中局冲刺潜力预检测（只算一次，供 _score 消费）──
        # 只在领出 + 非早期 + 手牌≥6 张场景检测（跟压/被压不涉及整结构保炸选择）
        cur_pos_val = game_state.get("curPos", -1)
        _is_lead_heuristic = (cur_pos_val == -1) or (
            greater_pos in (-1, my_pos) and 0 <= my_pos <= 3
        )
        _sprint_potential: Dict[str, Any] = {}
        if _is_lead_heuristic and not is_early_game and my_hand_size >= 6:
            _sprint_potential = self._midgame_sprint_potential_check(
                hand_cards, is_lead=True,
            )

        def _score(i: int, action) -> float:
            atype = get_action_type(action)
            is_pass = (atype == ACTION_TYPE_PASS)
            is_bomb = (atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH))
            is_single = (atype == ACTION_TYPE_SINGLE)
            grp_consistent = _is_group_consistent(action)

            score = 0.0

            # ① 组局一致性：最高优先级（PASS 不参与组局，不加此项）
            # GUA-149-v2: 跟牌浪费炸弹例外 — 早期用炸弹/同花顺压非炸牌型
            # （如 yf2 第3步用4张J炸 TWT/4），不应享受组局一致性加分。
            _wasteful_follow_bomb = (
                is_bomb
                and not _is_lead_heuristic
                and is_early_game
                and greater_action
                and get_action_type(greater_action) not in (*_BOMB_TYPES, ACTION_TYPE_PASS)
            )
            # MemoryV2 soft risk/send signal; hard rules remain authoritative
            try:
                from src.v.nn.features.memory_v2 import MemoryV2Adapter
                if not hasattr(self, "_memory_v2_adapter") or self._memory_v2_adapter is None:
                    self._memory_v2_adapter = MemoryV2Adapter(my_seat=int(game_state.get("myPos", self.player_id)), cur_rank=cur_rank)
                score += self._memory_v2_adapter.score_action(action, game_state, self._tracker)
            except Exception as memory_v2_err:
                self.logger.debug("MemoryV2 soft scoring skipped: %s", memory_v2_err)
            if not is_pass:
                if grp_consistent and not _wasteful_follow_bomb:
                    score += 10000
                else:
                    score += _group_break_penalty(action)  # 拆局扣分

            # ② 队友控牌：PASS 优先，非炸优先
            if teammate_controls:
                if is_pass:
                    score += 200
                elif not is_bomb:
                    score += 100

            # ③ 对手急眼（剩牌 ≤ 4）：炸弹优先
            if opp_in_danger:
                if is_bomb:
                    score += 800
                elif is_pass:
                    score -= 100

            # ③b GUA-072/GUA-079：对手剩 1 张且有人控牌 → 禁止 PASS
            if is_pass and greater_action and greater_action[0] != "PASS":
                for opp in (opp_left, opp_right):
                    if (
                        len(belief_hand_counts) > opp
                        and belief_hand_counts[opp] == 1
                    ):
                        score -= 2500
                        break

            # ③c GUA-072：对手无法确信压制当前控牌 → 鼓励用最小非 PASS 压牌
            if (
                not is_pass
                and not is_bomb
                and greater_action
                and greater_action[0] != "PASS"
                and belief.get("can_opp_suppress_current") is False
            ):
                score += 120

            # ④ 非 PASS 基础加分
            if not is_pass:
                score += 50

            # ⑤ 同优先级：起始 rank 越小越好（节约牌力）
            rank_key = 99
            if not is_pass:
                rank_str = get_action_rank(action)
                if rank_str:
                    rank_key = RANK_KEY.get(rank_str, 99)
            score -= rank_key  # rank 越小 → 负扣越少 → 分越高

            # ⑤b GUA-167: 领出时优先继续出同类型组合（对子/顺子/三带二），避免切换单张
            # 原理：领出后切换单张 = 送对手小牌上手；继续出组合 = 维持压制 + 清手牌效率高
            if _is_lead_heuristic and not is_pass and atype in (ACTION_TYPE_PAIR, ACTION_TYPE_STRAIGHT, ACTION_TYPE_THREE_WITH_TWO):
                # 统计 action_list 中同类型非炸弹候选数量
                same_type_count = sum(1 for a in action_list if get_action_type(a) == atype)
                if same_type_count >= 2:
                    # 保留最高同类型不当领出（避免 AAA 等高牌力组合被浪费）
                    same_ranks = {
                        RANK_KEY.get(get_action_rank(a), 99) for a in action_list
                        if get_action_type(a) == atype and get_action_rank(a)
                    }
                    if len(same_ranks) == 1:
                        score += 40  # 全等 rank → 全加（原始行为）
                    elif rank_key < max(same_ranks):
                        score += 40  # 非最高同类型 → 领出继续清组合

            # ⑥ GUA-071: 早期不出王压小牌（级差 > 6 且手牌 > 12）
            if is_single and greater_val > 0 and not is_pass:
                cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
                card = cards[0] if cards else (action[0] if len(action) >= 1 else "")
                card_rank = get_card_rank(str(card))
                card_val = get_card_value(str(card), cur_rank)
                gap = card_val - greater_val
                joker_gap_penalty = 500
                if hr_with_opponents >= 1:
                    joker_gap_penalty = 800
                if card_rank in ("HR", "SB") and is_early_game and gap > JOKER_MAX_GAP:
                    score -= joker_gap_penalty

            # ⑦ GUA-071: 小王优先 — 有 SB 可用时不用 HR
            if is_single and has_sb_single and not is_pass:
                cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
                card = cards[0] if cards else (action[0] if len(action) >= 1 else "")
                if get_card_rank(str(card)) == "HR":
                    score -= 300  # SB 可用却用 HR，浪费

            # ⑩ GUA-072: 推断对手侧双 HR → 避免领出/跟压王、避免早期小单试探
            if is_single and not is_pass and hr_with_opponents >= 2:
                cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
                card = cards[0] if cards else (action[0] if len(action) >= 1 else "")
                card_rank = get_card_rank(str(card))
                if card_rank in ("HR", "SB"):
                    score -= 900
                elif greater_val <= 0 and is_early_game:
                    score -= 200

            # ⑪ GUA-072: 推断对手侧 ≥1 HR → 跟压时优先 PASS，勿浪费王
            if (
                is_pass
                and hr_with_opponents >= 2
                and greater_action
                and greater_action[0] != "PASS"
                and get_action_type(greater_action) == ACTION_TYPE_SINGLE
            ):
                score += 350

            # ⑨ GUA-082/GUA-070 R12: 有自然单张时禁止拆普通对出单（heuristic 兜底）
            if is_single and not is_pass:
                if self._single_breaks_pair_under_r12(action, hand_cards, cur_rank):
                    score -= 20000

            # ⑩ GUA-157 + GUA-166: 助攻 5-T + 主攻 5-9 严一档 拆对拦单
            # 主攻阈值严一档：对手 ≥T（rank value 8）不借调
            borrow_window_ok = False
            if self._current_role in ("助攻", "超强主攻") and 3 <= greater_val <= 8:
                borrow_window_ok = True  # 5-T
            elif self._current_role == "主攻" and 3 <= greater_val <= 7:
                borrow_window_ok = True  # 5-9
            if (
                is_single
                and not is_pass
                and not teammate_controls
                and borrow_window_ok
            ):
                # 检查是否有自然单张（无散单才拆对）
                if not self._has_any_natural_single(hand_cards, cur_rank):
                    # 检查动作是否来自拆对（单张来自 pair group，非 core）
                    cards = action[2] if len(action) >= 3 and isinstance(action[2], list) else action
                    card = cards[0] if cards else None
                    if card:
                        card_info = mask.get(str(card))
                        if card_info:
                            gid, is_core, gsize = card_info
                            # 来自 pair group（gsize=2）且非 core → 拆对
                            if gsize == 2 and is_core <= 0:
                                # 拆对加分（比拆炸弹/三张优先）
                                score += 500
                                # 拆最小可拆对（99/TT/JJ）额外加分
                                from src.v.nn.guards.v7_guards import CARD_RANK_ORDER
                                card_pip = CARD_RANK_ORDER.get(get_card_rank(str(card)), 99)
                                if 7 <= card_pip <= 9:  # 9/T/J
                                    score += 200  # 优先拆9-J对

            # GUA-150: 中局冲刺潜力评分（领出场景）
            # 手牌含「炸弹 + 可出整结构」时：
            #   · 出整结构后剩余具备冲刺能力 → +800（保留冲刺路径）
            #   · 拆散炸弹组（部分使用 Bomb 组牌但非炸弹动作） → -600
            if not is_pass and not is_bomb and _sprint_potential.get("has_potential"):
                if self._action_creates_sprint(
                    action, hand_cards, is_lead=_is_lead_heuristic,
                ):
                    score += 800
                elif self._action_breaks_bomb_core(
                    action, mask, self._group_type_map or {},
                ):
                    score -= 600

            # GUA-179: 空扔炸弹罚分 — 领出有可用非炸整结构却选炸
            if is_bomb and _is_lead_heuristic:
                has_nonbomb_structure = any(
                    get_action_type(a) not in (*_BOMB_TYPES, "PASS")
                    and _is_group_consistent(a)
                    for a in action_list
                )
                if has_nonbomb_structure:
                    score -= 500

            # GUA-149-v2: 跟牌浪费炸弹罚分 — 跟非炸牌型时用炸弹/同花顺
            # R-D29: 前置过滤杀光 TWT 后只剩 Bomb 和 PASS，
            # 不加罚分时 Bomb/J 靠组局一致性 +10000 碾压 PASS。
            # 但早期用炸弹压 TWT/顺子/对子是严重浪费。
            if (
                is_bomb
                and not _is_lead_heuristic
                and not is_pass
                and is_early_game
                and greater_action
                and get_action_type(greater_action) not in (*_BOMB_TYPES, ACTION_TYPE_PASS)
            ):
                score -= 3000

            return score

        hard_blocked_bomb_indices = [
            i
            for i, act in enumerate(action_list)
            if has_same_type_nonbomb and get_action_type(act) in _BOMB_TYPES
        ]
        scored = [
            (i, _score(i, act))
            for i, act in enumerate(action_list)
            if i not in hard_blocked_bomb_indices
        ]
        scored.sort(key=lambda x: -x[1])  # 降序
        self._last_heuristic_scores = list(scored)
        self._replay_record(
            "heuristic_scores",
            {
                "scores": list(scored),
                "hard_blocked_bombs": hard_blocked_bomb_indices,
            },
        )

        if self.logger.isEnabledFor(logging.DEBUG):
            top3 = scored[:min(3, len(scored))]
            self.logger.debug(
                "heuristic top3: %s",
                [(i, f"{s:.0f}", get_action_type(action_list[i])) for i, s in top3]
            )

        # GUA-082: 最高分仍违 R12 时顺延下一候选（回退路径硬兜底）
        for idx, _ in scored:
            act = action_list[idx]
            if (
                get_action_type(act) == ACTION_TYPE_SINGLE
                and self._single_breaks_pair_under_r12(act, hand_cards, cur_rank)
            ):
                continue
            return idx
        return scored[0][0] if scored else 0

    # ═══════════════════════════════════════════════════════════════
    # GUA-075: 出牌推荐系统（排除法 → 推荐法）
    # ═══════════════════════════════════════════════════════════════

    # 牌力排序 key（用于推小牌优先）
    # 包含平台 rank 名（R/HR=14 大王，B/SB=13 小王）
    RANK_ORDER: Dict[str, int] = {
        "2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5,
        "8": 6, "9": 7, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12,
        "SB": 13, "B": 13,    # 小王：内部 SB，平台 B
        "HR": 14, "R": 14,    # 大王/红心级牌：内部 HR，平台 R
    }

    # 内部 rank → 平台 actionList 中使用的 rank 名
    INTERNAL_TO_PLATFORM_RANK: Dict[str, str] = {"HR": "R", "SB": "B"}
    PLATFORM_TO_INTERNAL_RANK: Dict[str, str] = {"R": "HR", "B": "SB"}

    # 牌型 → 行动类型映射（group_type → action_type）
    GROUP_TO_ACTION: Dict[str, str] = {
        "straight": "Straight",
        "trips": "Trips",
        "pair": "Pair",
        "pair_in_three_pair": "Pair",
        "pair_in_three_with_two": "Pair",
        "trip_in_three_with_two": "Trips",   # 三张主体仍可做纯三张（Trips 跟牌用）
        "trip_in_steel_plate": "Trips",       # 同上
    }

    @staticmethod
    def _group_type_to_platform_action(gtype: str) -> str:
        """组牌 group_type → 平台 action 类型名（Bomb/StraightFlush 已与平台一致）。"""
        if gtype in ("Bomb", "StraightFlush"):
            return gtype
        return UltimateWinRateEngineV7.GROUP_TO_ACTION.get(gtype, "Unknown")

    def _recommend_play(
        self, game_state: Dict[str, Any], action_list: Optional[List] = None
    ) -> Optional[Dict[str, Any]]:
        """
        GUA-075: 出牌推荐器 — 基于组牌方案 + 局面上下文，**主动推荐最优出牌**。

        与现有管线的本质区别：
          ① 不依赖 position-based NN（不看 actionList slot 位置）
          ② 基于组牌引擎 card_mask 决定「该从哪个组出牌」
          ③ 场景感知（领出/打上家/卡下家/让对家）
          ④ 接收 actionList，推荐后立即自检：确保产出在合法候选列表中

        返回 None 表示推荐失败，走回退路径。

        Args:
            game_state: 完整游戏状态
            action_list: 平台下发的 actionList（用于验证推荐的合法性）

        Returns:
            {"type": str, "rank": str, "cards": [str, ...]} 或 None
        """
        from src.v.nn.guards.v7_guards import (
            get_action_type, get_action_rank, ACTION_TYPE_PASS,
        )

        my_pos = game_state.get("myPos", self.player_id)
        cur_pos = game_state.get("curPos", -1)
        greater_pos = game_state.get("greaterPos", -1)
        greater_action = game_state.get("greaterAction", []) or []
        hand_cards = game_state.get("handCards", []) or []
        cur_rank = str(game_state.get("curRank", "2"))
        current_stage = str(game_state.get("_current_stage", ""))

        card_mask = self._card_mask or {}
        if not card_mask or not hand_cards:
            return None

        # ── 场景判断（跟牌看 greaterPos=本圈最大者，不是 curPos=轮谁出牌）──
        # curPos 在 act 消息里是「当前行动席」；greaterPos 才是上家/下家/对家谁出的牌。
        # 仍保留 R11/让道等逻辑，并非 greaterPos 命中就必压。
        teammate_pos = (my_pos + 2) % 4
        opp_right = (my_pos + 3) % 4   # 上家
        xia_jia = (my_pos + 1) % 4     # 下家

        is_lead = (cur_pos in (-1, my_pos)) and (greater_pos in (-1, my_pos))
        is_teammate = (greater_pos == teammate_pos)
        is_upper = (greater_pos == opp_right)
        is_lower = (greater_pos == xia_jia)

        # ── DIAG-001: 场景诊断（GUA-091 队友炸弹根因排查）──
        self.logger.info(
            "DIAG-001 场景: myPos=%d greaterPos=%d teammatePos=%d "
            "curPos=%d is_teammate=%s is_upper=%s is_lower=%s is_lead=%s "
            "stage=%s role=%s",
            my_pos, greater_pos, teammate_pos, cur_pos,
            is_teammate, is_upper, is_lower, is_lead,
            current_stage, self._current_role,
        )

        greater_type = ""
        greater_rank = ""
        if greater_action and greater_action[0] != "PASS":
            greater_type = get_action_type(greater_action)
            greater_rank = get_action_rank(greater_action) or ""

        role = self._current_role or "主攻"

        # ── 内联辅助：验证推荐是否在 actionList 中，不在则尝试宽松匹配 ──
        def _ensure_valid(rec: Dict[str, Any], scenario_label: str) -> Optional[Dict[str, Any]]:
            """确保推荐在 actionList 中；精确匹配失败则做 type+rank 宽松匹配。"""
            if not rec or not action_list:
                return rec
            r_type = rec.get("type", "")
            r_rank = rec.get("rank", "")
            r_cards = sorted(rec.get("cards", []) or [])

            # PASS 直接通过
            if r_type == "PASS":
                return rec

            # 精确匹配
            for a in action_list:
                if not a or len(a) < 2:
                    continue
                a_type = a[0]
                a_rank = a[1] if len(a) >= 2 else ""
                a_cards = sorted(str(c) for c in (a[2] if len(a) >= 3 and isinstance(a[2], list) else a))
                if a_type == r_type and a_rank == r_rank and a_cards == r_cards:
                    return rec

            # 精确匹配失败 → 宽松匹配：找 actionList 中同 type+rank 的第一个条目
            for a in action_list:
                if not a or len(a) < 2:
                    continue
                a_type = a[0]
                a_rank = a[1] if len(a) >= 2 else ""
                if a_type == r_type and a_rank == r_rank:
                    a_cards = sorted(str(c) for c in (a[2] if len(a) >= 3 and isinstance(a[2], list) else a))
                    self.logger.info(
                        "GUA-075 %s: 推荐精确匹配失败(rec_cards=%s) → 宽松匹配 actionList_cards=%s",
                        scenario_label, r_cards, a_cards)
                    return {"type": a_type, "rank": a_rank, "cards": a_cards}

            # 完全匹配失败
            al_sample = ""
            if action_list and len(action_list) <= 8:
                try:
                    from src.communication.v7_game_recorder import summarize_action_list_for_context
                    al_sample = summarize_action_list_for_context(action_list)
                except Exception:
                    al_sample = f"size={len(action_list)}"
            self.logger.warning(
                "GUA-075 %s: 推荐无法匹配 actionList rec={type=%s rank=%s cards=%s} sample=%s",
                scenario_label, r_type, r_rank, r_cards, al_sample)
            return None

        # ── GUA-117：助攻/超弱 领出（先于 090/091，避免 fake feed / 主攻逻辑）──
        if role in ("助攻", "超弱"):
            if is_teammate:
                self.logger.info(
                    "GUA-117 推荐: 让队友 → PASS (teammatePos=%d)", teammate_pos)
                return {
                    "type": "PASS",
                    "rank": "",
                    "cards": [],
                    "intent": "assist_yield_teammate",
                }
            if is_lead:
                from src.v.nn.stage_assist_feed import recommend_assist_lead
                assist_rec = recommend_assist_lead(
                    self,
                    game_state,
                    card_mask,
                    hand_cards,
                    cur_rank,
                    current_stage,
                    teammate_pos,
                    action_list,
                )
                assist_rec = _ensure_valid(assist_rec, "GUA-117 助攻领出") if assist_rec else None
                if assist_rec:
                    self.logger.info(
                        "GUA-117 助攻领出: intent=%s → type=%s rank=%s cards=%s",
                        assist_rec.get("intent"),
                        assist_rec.get("type"),
                        assist_rec.get("rank"),
                        assist_rec.get("cards"),
                    )
                    self._last_stage_intent = assist_rec.get("intent")
                    return assist_rec

        # ── GUA-090：stage_0 / stage_1 开局与初期入口 ──
        # stage_0（27 张）= 组牌+角色；stage_1（21-26）= 初期动态；暂共用 _stage_open_plan。
        # 若命不中，再回落到 GUA-075 通用四场景逻辑。
        if current_stage in ("stage_0", "stage_1"):
            stage_rec = self._stage_open_plan(
                game_state=game_state,
                card_mask=card_mask,
                hand_cards=hand_cards,
                cur_rank=cur_rank,
                is_lead=is_lead,
                is_teammate=is_teammate,
                teammate_pos=teammate_pos,
            )
            stage_rec = _ensure_valid(stage_rec, "GUA-090 开局阶段") if stage_rec else None
            if stage_rec:
                self.logger.info(
                    "GUA-090 开局阶段: intent=%s → type=%s rank=%s cards=%s",
                    stage_rec.get("intent"),
                    stage_rec.get("type"),
                    stage_rec.get("rank"),
                    stage_rec.get("cards"),
                )
                self._last_stage_intent = stage_rec.get("intent")
                return stage_rec

        # ── GUA-091：stage_2 中局入口 ──
        # 中局不再直接落入通用四场景逻辑，而是先统一消费
        # `_belief + _phase_relation + role + greaterAction` 形成攻守意图。
        if current_stage == "stage_2" and self._is_stage2_dispatch_enabled():
            game_state["actionList"] = action_list
            stage_rec = self._stage_mid_dispatch(
                game_state=game_state,
                card_mask=card_mask,
                hand_cards=hand_cards,
                cur_rank=cur_rank,
                greater_action=greater_action,
                greater_type=greater_type,
                greater_rank=greater_rank,
                is_lead=is_lead,
                is_teammate=is_teammate,
                is_upper=is_upper,
                is_lower=is_lower,
                teammate_pos=teammate_pos,
            )
            stage_rec = _ensure_valid(stage_rec, "GUA-091 中局阶段") if stage_rec else None
            if stage_rec:
                self.logger.info(
                    "GUA-091 中局阶段: intent=%s → type=%s rank=%s cards=%s",
                    stage_rec.get("intent"),
                    stage_rec.get("type"),
                    stage_rec.get("rank"),
                    stage_rec.get("cards"),
                )
                self._last_stage_intent = stage_rec.get("intent")
                return stage_rec

        # ── ① 对家在出牌：PASS 让道 ──
        if is_teammate:
            self.logger.info(
                "GUA-075 推荐: 让对家 → PASS (teammatePos=%d)", teammate_pos)
            return {"type": "PASS", "rank": "", "cards": []}

        # ── ② 领出场景 ──
        if is_lead:
            if role in ("助攻", "超弱"):
                return None
            from src.v.nn.stage_main_attack_lead import recommend_main_attack_lead
            rec = recommend_main_attack_lead(
                self,
                game_state,
                card_mask,
                hand_cards,
                cur_rank,
                game_state.get("_current_stage", "stage_1"),
            )
            if not rec:
                rec = self._recommend_lead_impl(game_state, card_mask, hand_cards, cur_rank)
            rec = _ensure_valid(rec, f"领出(curPos=start)")
            if rec:
                self.logger.info(
                    "GUA-075 推荐: 领出 → type=%s rank=%s cards=%s",
                    rec.get("type"), rec.get("rank"), rec.get("cards"))
            return rec

        # ── ③ 跟上家牌：找同型最小压；无同型时 R11 预检改炸 ──
        if is_upper and greater_action and greater_action[0] != "PASS":
            rec_impl = self._recommend_min_press_impl(
                game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank)
            if not rec_impl:
                rec_impl = self._recommend_targeted_regroup_press(
                    game_state,
                    card_mask,
                    greater_action,
                    greater_type,
                    hand_cards,
                    cur_rank,
                )
            if rec_impl:
                rec = _ensure_valid(rec_impl, f"跟上家(greater={greater_type}/{greater_rank})")
                if rec:
                    self.logger.info(
                        "GUA-075 推荐: 跟上家(greater=%s/%s) → type=%s rank=%s cards=%s",
                        greater_type, greater_rank, rec.get("type"), rec.get("rank"),
                        rec.get("cards"))
                    return rec
                # GUA-083: 有推荐但 actionList 无匹配 → 回退，勿误当「无同型 PASS」
                self.logger.warning(
                    "GUA-075 跟上家: 推荐存在但 actionList 无匹配 → return None 回退")
                return None
            # 无同型可压 → R11 预检：是否允许改炸
            can_bomb, reason = self._r11_bomb_throttle_check(
                game_state, greater_action, greater_rank, cur_rank)
            if can_bomb:
                # GUA-172 PASS-priority: 单张王无自然压时不炸
                if greater_type == "Single" and greater_rank in ("B", "R"):
                    if not self._is_in_endgame_state(hand_cards, game_state):
                        self.logger.info(
                            "GUA-172 PASS-priority: 跟上家单张王(%s)无自然压 → PASS",
                            greater_rank)
                        return {"type": "PASS", "rank": "", "cards": []}
                # GUA-172: 优先从 actionList 选最廉价炸
                bomb_impl = self._recommend_cheapest_bomb_from_action_list(
                    action_list, cur_rank)
                if not bomb_impl:
                    bomb_impl = self._recommend_bomb_from_mask(card_mask, cur_rank)
                if bomb_impl:
                    bomb_rec = _ensure_valid(bomb_impl, f"跟上家改炸({reason})")
                    if bomb_rec:
                        self.logger.info(
                            "GUA-075 推荐: 跟上家改炸(%s) → type=%s rank=%s cards=%s",
                            reason, bomb_rec.get("type"), bomb_rec.get("rank"),
                            bomb_rec.get("cards"))
                        return bomb_rec
                    self.logger.warning(
                        "GUA-075 跟上家改炸: 推荐存在但 actionList 无匹配 → return None 回退")
                    return None
            # 不让改炸 → 尝试 GUA-123 敌炸 counter
            counter = self._recommend_counter_bomb_in_action_list(game_state)
            if counter:
                rec = _ensure_valid(counter, "跟上家敌炸counter")
                if rec:
                    self.logger.info(
                        "GUA-075 推荐: 跟上家敌炸counter → type=%s rank=%s cards=%s",
                        rec.get("type"), rec.get("rank"), rec.get("cards"))
                    return rec
            # 不让改炸 → PASS 让道
            self.logger.info(
                "GUA-075 推荐: 跟上家无同型 → R11决定PASS(%s)", reason)
            return {"type": "PASS", "rank": "", "cards": []}

        # ── ④ 卡下家：按牌力/危急分档（顺势 min / 卡点≈J / 危急 max）──
        # 人类定音见 docs/guandan-brain/issues/GUA-075-卡下家.md
        if is_lower and greater_action and greater_action[0] != "PASS":
            rec_impl = self._recommend_max_press_impl(
                game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank)
            if rec_impl:
                mode_tag = rec_impl.pop("_xiajia_mode", "press")
                rec = _ensure_valid(rec_impl, f"卡下家(greater={greater_type}/{greater_rank})")
                if rec:
                    self.logger.info(
                        "GUA-075 推荐: 卡下家-%s(greater=%s/%s) → type=%s rank=%s cards=%s",
                        mode_tag, greater_type, greater_rank,
                        rec.get("type"), rec.get("rank"), rec.get("cards"))
                    return rec
                # GUA-083: 有推荐但 actionList 无匹配 → 回退，勿误当「无同型 PASS」
                self.logger.warning(
                    "GUA-075 卡下家: 推荐存在但 actionList 无匹配 → return None 回退")
                return None
            # 无同型可压 → R11 预检
            can_bomb, reason = self._r11_bomb_throttle_check(
                game_state, greater_action, greater_rank, cur_rank)
            if can_bomb:
                # GUA-172 PASS-priority: 单张王无自然压时不炸
                if greater_type == "Single" and greater_rank in ("B", "R"):
                    if not self._is_in_endgame_state(hand_cards, game_state):
                        self.logger.info(
                            "GUA-172 PASS-priority: 卡下家单张王(%s)无自然压 → PASS",
                            greater_rank)
                        return {"type": "PASS", "rank": "", "cards": []}
                # GUA-172: 优先从 actionList 选最廉价炸
                bomb_impl = self._recommend_cheapest_bomb_from_action_list(
                    action_list, cur_rank)
                if not bomb_impl:
                    bomb_impl = self._recommend_bomb_from_mask(card_mask, cur_rank)
                if bomb_impl:
                    bomb_rec = _ensure_valid(bomb_impl, f"卡下家改炸({reason})")
                    if bomb_rec:
                        self.logger.info(
                            "GUA-075 推荐: 卡下家改炸(%s) → type=%s rank=%s cards=%s",
                            reason, bomb_rec.get("type"), bomb_rec.get("rank"),
                            bomb_rec.get("cards"))
                        return bomb_rec
                    self.logger.warning(
                        "GUA-075 卡下家改炸: 推荐存在但 actionList 无匹配 → return None 回退")
                    return None
            # 不让改炸 → 尝试 GUA-123 敌炸 counter
            counter = self._recommend_counter_bomb_in_action_list(game_state)
            if counter:
                rec = _ensure_valid(counter, "卡下家敌炸counter")
                if rec:
                    self.logger.info(
                        "GUA-075 推荐: 卡下家敌炸counter → type=%s rank=%s cards=%s",
                        rec.get("type"), rec.get("rank"), rec.get("cards"))
                    return rec
            # 不让改炸 → PASS
            self.logger.info(
                "GUA-075 推荐: 卡下家无同型 → R11决定PASS(%s)", reason)
            return {"type": "PASS", "rank": "", "cards": []}

        return None

    def _stage_open_plan(
        self,
        game_state: Dict[str, Any],
        card_mask: Dict[str, tuple],
        hand_cards: List[str],
        cur_rank: str,
        *,
        is_lead: bool,
        is_teammate: bool,
        teammate_pos: int,
    ) -> Optional[Dict[str, Any]]:
        """
        GUA-090：开局/初期阶段（stage_0 / stage_1）专用入口。

        目标不是“随手挑一个最小合法动作”，而是先产出开局意图：
          1. 队友控牌时优先让道
          2. 领出时优先低耗损试探单张
          3. 若只剩高耗损单张（K/A/级牌/王），优先安全小对开路

        本阶段暂不接管非领出且非队友控牌场景，交由 GUA-075 通用逻辑。
        """
        from src.v.nn.guards.v7_guards import get_card_rank, get_card_value

        def _prank(internal_rank: str) -> str:
            return self.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

        role = self._current_role or "主攻"
        if role in ("助攻", "超弱") and is_lead:
            return None

        if role in ("主攻", "超强主攻") and is_lead:
            from src.v.nn.stage_main_attack_lead import recommend_main_attack_lead
            main_rec = recommend_main_attack_lead(
                self,
                game_state,
                card_mask,
                hand_cards,
                cur_rank,
                game_state.get("_current_stage", "stage_1"),
            )
            if main_rec:
                return main_rec

        groups = self._build_group_index(card_mask)
        group_type_map = self._group_type_map or {}
        group_members = self._group_members or None
        protected_core = frozenset(("Bomb", "StraightFlush", "straight"))

        if is_teammate:
            return {
                "type": "PASS",
                "rank": "",
                "cards": [],
                "intent": "yield_to_teammate",
            }

        sprint_fire_bomb = self._maybe_recommend_sprint_fire_bomb(
            game_state,
            card_mask,
            cur_rank,
            teammate_pos=teammate_pos,
            intent="open_sprint_fire_bomb",
        )
        if sprint_fire_bomb:
            return sprint_fire_bomb

        if not is_lead:
            return None

        def _single_breaks_protected_core(card: str) -> bool:
            rank = _prank(get_card_rank(str(card)))
            broken = self._get_broken_core_type(
                ["Single", rank, [str(card)]],
                card_mask,
                group_type_map,
                group_members,
            )
            return broken in protected_core

        def _opening_value(card: str) -> int:
            return get_card_value(str(card), cur_rank)

        def _is_high_cost_single(card: str) -> bool:
            # 不写死 K/A/王 名字，直接按当前单张强度阈值判。
            return _opening_value(card) >= self.RANK_ORDER["K"]

        scatter_singles = [
            str(card) for card in self._scatter_singles(card_mask)
            if not _single_breaks_protected_core(str(card))
        ]
        scatter_singles.sort(key=lambda c: (_opening_value(c), str(c)))

        low_cost_singles = [c for c in scatter_singles if not _is_high_cost_single(c)]

        pair_groups = []
        pair_like_types = ("pair", "pair_in_three_pair", "pair_in_three_with_two")
        for gid, ginfo in groups.items():
            if ginfo["type"] not in pair_like_types:
                continue
            if ginfo["is_core"] > 0:
                continue
            if len(ginfo["cards"]) < 2:
                continue
            cards = sorted(str(c) for c in ginfo["cards"])[:2]
            if _opening_value(cards[0]) >= self.RANK_ORDER["K"]:
                continue
            pair_groups.append((cards, get_card_rank(cards[0])))
        pair_groups.sort(key=lambda item: (_opening_value(item[0][0]), item[0]))

        if low_cost_singles:
            card = low_cost_singles[0]
            return {
                "type": "Single",
                "rank": _prank(get_card_rank(card)),
                "cards": [card],
                "intent": "assist_probe_single" if role in ("助攻", "超弱") else "main_probe_single",
            }

        if pair_groups:
            cards, rank = pair_groups[0]
            return {
                "type": "Pair",
                "rank": _prank(rank),
                "cards": cards,
                "intent": "assist_safe_pair" if role in ("助攻", "超弱") else "main_safe_pair",
            }

        if scatter_singles:
            card = scatter_singles[0]
            return {
                "type": "Single",
                "rank": _prank(get_card_rank(card)),
                "cards": [card],
                "intent": "fallback_high_cost_single",
            }

        return None

    # ═══════════════════════════════════════════════════════════════
    # GUA-150：中局冲刺潜力检测
    # ═══════════════════════════════════════════════════════════════

    def _midgame_sprint_potential_check(
        self,
        hand_cards: List[str],
        *,
        is_lead: bool = True,
    ) -> Dict[str, Any]:
        """
        GUA-150：中局冲刺潜力检测。

        冲刺能力（_hand_has_sprint_capability, GUA-135）要求「炸 + 一手整牌」。
        中局手牌常不满足此严格条件（如 炸+顺+散单），但「出完一手整结构后
        剩余手牌即具备冲刺能力」——这条路径应被感知并优先选择。

        检测逻辑：
          1. 手牌中是否含炸弹族（≥4 同点）
          2. 是否至少存在一个非炸弹整组，出完后剩余手牌满足 GUA-135 冲刺能力

        典型场景：
          handCards=10: Bomb(4Q) + Straight(5) + 散牌(CJ)
          → 出 Straight 后剩 Bomb+CJ (5张=1手) → 进入冲刺态 ✅
          → 出 Trips Q（拆 Bomb）后丧失冲刺路径 ❌

        Returns:
            {"has_potential": bool, "preferred_gids": [int], "bomb_gids": [int]}
        """
        result: Dict[str, Any] = {"has_potential": False, "preferred_gids": [], "bomb_gids": []}
        if not is_lead or not hand_cards or len(hand_cards) < 6:
            return result

        from collections import Counter
        from src.v.nn.guards.v7_guards import get_card_rank

        hand_ranks = Counter(get_card_rank(c) for c in hand_cards)
        has_bomb = any(cnt >= 4 for cnt in hand_ranks.values())
        if not has_bomb:
            return result

        group_members = self._group_members or {}
        group_type_map = self._group_type_map or {}

        # 收集炸弹组 gid（用于后续拆弹检测）
        bomb_gids = [
            gid for gid, gtype in group_type_map.items()
            if gtype in ("Bomb", "StraightFlush")
        ]
        result["bomb_gids"] = bomb_gids

        try:
            from src.v.nn.endgame.endgame_decide import EndgameDecider
        except Exception:
            return result

        preferred_gids = []
        for gid, members in group_members.items():
            gtype = group_type_map.get(gid, "")
            # 跳过炸弹 / 同花顺 — 我们希望保留它们作为冲刺武器
            if gtype in ("Bomb", "StraightFlush"):
                continue
            # 跳过非整结构（散牌 scatter、拆出子组如 pair_in_xxx）
            if gtype in ("scatter", "straight_flush") or gid < 0:
                continue

            # 模拟出完这个组后剩余手牌是否具备冲刺能力
            member_set = set(str(m) for m in members)
            remaining = [c for c in hand_cards if str(c) not in member_set]
            if not remaining or len(remaining) < 5:
                continue  # 剩余太少，无冲刺讨论意义

            if EndgameDecider._hand_has_sprint_capability(remaining):
                preferred_gids.append(gid)

        result["has_potential"] = len(preferred_gids) > 0
        result["preferred_gids"] = preferred_gids
        return result

    @staticmethod
    def _action_breaks_bomb_core(
        action,
        card_mask: Dict[str, tuple],
        group_type_map: Dict[int, str],
    ) -> bool:
        """
        GUA-150 helper：动作是否拆散炸弹组。

        判断标准：动作使用了炸弹组（Bomb/StraightFlush）中的牌，
        但自身不是炸弹动作（即部分使用 = 拆散）。
        """
        from src.v.nn.guards.v7_guards import (
            get_action_type, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )
        atype = get_action_type(action)
        if atype in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH, "PASS"):
            return False

        action_cards = (
            action[2] if isinstance(action, list) and len(action) >= 3 and isinstance(action[2], list)
            else (action if isinstance(action, list) and len(action) > 0 else [])
        )
        if not action_cards:
            return False

        if not card_mask or not group_type_map:
            return False

        for c in action_cards:
            info = card_mask.get(str(c))
            if info:
                gid, is_core, _ = info
                if gid >= 0 and is_core >= 1.0:
                    if group_type_map.get(gid) in ("Bomb", "StraightFlush"):
                        return True
        return False

    @staticmethod
    def _action_creates_sprint(
        action,
        hand_cards: List[str],
        is_lead: bool = True,
    ) -> bool:
        """
        GUA-150 helper：出完此动作后剩余手牌是否具备冲刺能力。
        """
        if not is_lead:
            return False
        from src.v.nn.guards.v7_guards import (
            get_action_type, ACTION_TYPE_PASS,
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )
        atype = get_action_type(action)
        if atype in (ACTION_TYPE_PASS, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return False

        action_cards = (
            action[2] if isinstance(action, list) and len(action) >= 3 and isinstance(action[2], list)
            else (action if isinstance(action, list) and len(action) > 0 else [])
        )
        if not action_cards:
            return False

        action_set = set(str(c) for c in action_cards)
        remaining = [c for c in hand_cards if str(c) not in action_set]
        if len(remaining) < 5:
            return False

        try:
            from src.v.nn.endgame.endgame_decide import EndgameDecider
            return EndgameDecider._hand_has_sprint_capability(remaining)
        except Exception:
            return False

    def _stage_mid_dispatch(
        self,
        game_state: Dict[str, Any],
        card_mask: Dict[str, tuple],
        hand_cards: List[str],
        cur_rank: str,
        *,
        greater_action: List[Any],
        greater_type: str,
        greater_rank: str,
        is_lead: bool,
        is_teammate: bool,
        is_upper: bool,
        is_lower: bool,
        teammate_pos: int,
    ) -> Optional[Dict[str, Any]]:
        """
        GUA-091：stage_2 中局统一入口。

        只消费统一信号：
          - `_belief`：剩张 / 炸弹风险 / 当前控牌可否被压
          - `_phase_relation`：关键敌方、牌型粗分类、队友承接、同型压制外部性
          - `role`：主攻 / 助攻 / 超弱

        输出中局意图，再复用既有 `lead / min_press / max_press / bomb`
        基元去落具体动作，避免继续在 `_recommend_play()` 里堆牌例特判。
        """
        belief = game_state.get("_belief") or {}
        phase_relation = game_state.get("_phase_relation") or {}
        role = self._current_role or "主攻"
        hand_counts = belief.get("hand_counts") or game_state.get("numofplayers") or {}

        def _remaining(seat: int, default: int = 27) -> int:
            if seat < 0:
                return default
            if isinstance(hand_counts, dict):
                try:
                    return int(hand_counts.get(seat, default))
                except (TypeError, ValueError):
                    return default
            if isinstance(hand_counts, list) and seat < len(hand_counts):
                try:
                    return int(hand_counts[seat])
                except (TypeError, ValueError):
                    return default
            return default

        def _with_intent(rec: Optional[Dict[str, Any]], intent: str) -> Optional[Dict[str, Any]]:
            if not rec:
                return None
            tagged = dict(rec)
            tagged["intent"] = intent
            return tagged

        critical_enemy_seat = int(phase_relation.get("critical_enemy_seat", -1))
        critical_enemy_remaining = _remaining(critical_enemy_seat)
        teammate_cover_confidence = float(
            phase_relation.get("teammate_cover_confidence", 0.0) or 0.0
        )
        teammate_rear_single_cover_confidence = float(
            phase_relation.get("teammate_rear_single_cover_confidence", 0.0) or 0.0
        )
        same_type_suppressor_outside = bool(
            phase_relation.get("same_type_suppressor_outside", False)
        )
        enemy_bomb_risk_max = float(
            phase_relation.get("enemy_bomb_risk_max", 0.0) or 0.0
        )
        enemy_shape_hint = str(phase_relation.get("enemy_shape_hint", "unknown") or "unknown")
        greater_remaining = _remaining(game_state.get("greaterPos", -1))
        sprint_fire_ready = bool(phase_relation.get("sprint_fire_ready", False))
        hold_rear_teammate_single_cover = (
            is_upper
            and greater_type == "Single"
            and game_state.get("greaterPos", -1) == critical_enemy_seat
            and critical_enemy_remaining <= 0
            and teammate_rear_single_cover_confidence >= 0.65
        )
        joker_belief = self._joker_belief_from_state(game_state)
        hr_with_opponents = joker_belief["hr_with_opponents"]

        if is_teammate:
            # GUA-205 支线1：队友已持 great（greaterPos==teammate），
            # 一律让道——用炸弹抢队友控制权损己利敌，禁止抢攻开炸。
            intent = (
                "mid_yield_teammate_control"
                if teammate_cover_confidence >= 0.65
                else "mid_preserve_teammate_lane"
            )
            return {
                "type": "PASS",
                "rank": "",
                "cards": [],
                "intent": intent,
            }

        if is_lead:
            if role in ("助攻", "超弱"):
                return None
            from src.v.nn.stage_main_attack_lead import recommend_main_attack_lead
            rec = recommend_main_attack_lead(
                self,
                game_state,
                card_mask,
                hand_cards,
                cur_rank,
                game_state.get("_current_stage", "stage_2"),
            )
            if not rec:
                return None
            # GUA-150：中局冲刺潜力感知 — 手牌含「炸 + 可出整结构」时标记意图
            sprint_check = self._midgame_sprint_potential_check(
                hand_cards, is_lead=True,
            )
            has_sprint_potential = sprint_check.get("has_potential", False)
            if critical_enemy_remaining <= 4:
                return _with_intent(rec, "mid_probe_critical_enemy")
            if hr_with_opponents >= 2:
                return _with_intent(rec, "mid_safe_structure_probe")
            if enemy_shape_hint == "structured" and enemy_bomb_risk_max >= 0.5:
                return _with_intent(rec, "mid_safe_structure_probe")
            if has_sprint_potential:
                return _with_intent(rec, rec.get("intent") or "mid_sprint_structure_lead")
            return _with_intent(rec, rec.get("intent") or "mid_balance_lead")

        if not greater_action or greater_action[0] == "PASS":
            return None

        if sprint_fire_ready and not hold_rear_teammate_single_cover:
            sprint_fire_bomb = self._maybe_recommend_sprint_fire_bomb(
                game_state,
                card_mask,
                cur_rank,
                teammate_pos=teammate_pos,
                intent="mid_sprint_fire_bomb",
            )
            if sprint_fire_bomb:
                return sprint_fire_bomb

        if is_upper:
            if game_state.get("greaterPos", -1) == critical_enemy_seat and critical_enemy_remaining <= 4:
                rec = self._recommend_max_press_impl(
                    game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank
                )
                if rec:
                    return _with_intent(rec, "mid_cut_critical_upper")

            rec = self._recommend_min_press_impl(
                game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank
            )
            if not rec:
                rec = self._recommend_targeted_regroup_press(
                    game_state,
                    card_mask,
                    greater_action,
                    greater_type,
                    hand_cards,
                    cur_rank,
                )
            if rec:
                if (
                    hr_with_opponents >= 2
                    and greater_type == "Single"
                    and self._recommendation_uses_joker(rec)
                    and critical_enemy_remaining > 4
                ):
                    return {
                        "type": "PASS",
                        "rank": "",
                        "cards": [],
                        "intent": "mid_hold_joker_vs_double_hr",
                    }
                intent = (
                    "mid_trade_min_press"
                    if same_type_suppressor_outside
                    else "mid_take_control_min_press"
                )
                return _with_intent(rec, intent)

            if hold_rear_teammate_single_cover:
                return {
                    "type": "PASS",
                    "rank": "",
                    "cards": [],
                    "intent": "mid_hold_rear_teammate_single_cover",
                }

            can_bomb, reason = self._r11_bomb_throttle_check(
                game_state, greater_action, greater_rank, cur_rank
            )
            if (
                can_bomb
                and game_state.get("greaterPos", -1) == critical_enemy_seat
                and critical_enemy_remaining <= 3
                and teammate_cover_confidence < 0.5
                and teammate_rear_single_cover_confidence < 0.65
            ):
                bomb = self._recommend_bomb_from_mask(card_mask, cur_rank, action_list=game_state.get("actionList") or [])
                if bomb:
                    return _with_intent(bomb, f"mid_bomb_cutoff:{reason}")

            # GUA-205 支线2：超强手牌中局主动开炸抢攻（敌方非报单临界）
            aggressive = self._mid_aggressive_bomb_special(
                game_state, card_mask, hand_cards, cur_rank,
                greater_action=greater_action,
                greater_type=greater_type,
                greater_rank=greater_rank,
                teammate_pos=teammate_pos,
                is_teammate=False,
            )
            if aggressive:
                return aggressive

            if teammate_cover_confidence >= 0.75 and 0 < _remaining(teammate_pos) <= 4:
                return {
                    "type": "PASS",
                    "rank": "",
                    "cards": [],
                    "intent": "mid_hold_for_teammate",
                }
            counter = self._recommend_counter_bomb_in_action_list(game_state)
            if counter:
                return _with_intent(counter, "mid_counter_enemy_bomb")
            return {
                "type": "PASS",
                "rank": "",
                "cards": [],
                "intent": "mid_no_same_type_pass",
            }

        if is_lower:
            if game_state.get("greaterPos", -1) == critical_enemy_seat or greater_remaining <= 4:
                rec = self._recommend_max_press_impl(
                    game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank
                )
                if rec:
                    return _with_intent(rec, "mid_block_critical_enemy")
            elif same_type_suppressor_outside:
                rec = self._recommend_min_press_impl(
                    game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank
                )
                if rec:
                    if (
                        hr_with_opponents >= 2
                        and greater_type == "Single"
                        and self._recommendation_uses_joker(rec)
                    ):
                        return {
                            "type": "PASS",
                            "rank": "",
                            "cards": [],
                            "intent": "mid_hold_joker_vs_double_hr",
                        }
                    return _with_intent(rec, "mid_keep_overcall_in_reserve")
            else:
                rec = self._recommend_max_press_impl(
                    game_state, card_mask, greater_action, greater_type, hand_cards, cur_rank
                )
                if rec:
                    return _with_intent(rec, "mid_block_lower_enemy")

            can_bomb, reason = self._r11_bomb_throttle_check(
                game_state, greater_action, greater_rank, cur_rank
            )
            if (
                can_bomb
                and game_state.get("greaterPos", -1) == critical_enemy_seat
                and critical_enemy_remaining <= 3
                and teammate_cover_confidence < 0.5
            ):
                bomb = self._recommend_bomb_from_mask(card_mask, cur_rank, action_list=game_state.get("actionList") or [])
                if bomb:
                    return _with_intent(bomb, f"mid_bomb_cutoff:{reason}")

            # GUA-205 支线2：超强手牌中局主动开炸抢攻（敌方非报单临界）
            aggressive = self._mid_aggressive_bomb_special(
                game_state, card_mask, hand_cards, cur_rank,
                greater_action=greater_action,
                greater_type=greater_type,
                greater_rank=greater_rank,
                teammate_pos=teammate_pos,
                is_teammate=False,
            )
            if aggressive:
                return aggressive

            counter = self._recommend_counter_bomb_in_action_list(game_state)
            if counter:
                return _with_intent(counter, "mid_counter_enemy_bomb")

            return {
                "type": "PASS",
                "rank": "",
                "cards": [],
                "intent": "mid_no_same_type_pass",
            }

        return None

    def _mid_aggressive_bomb_special(
        self,
        game_state: Dict[str, Any],
        card_mask: Dict[str, tuple],
        hand_cards: List[str],
        cur_rank: str,
        *,
        greater_action: List[Any],
        greater_type: str,
        greater_rank: str,
        teammate_pos: int,
        is_teammate: bool,
    ) -> Optional[Dict[str, Any]]:
        """GUA-205：超强主攻中局主动开炸抢攻。

        触发前提（全局）：
          1. 手牌炸弹族数量 bombs>=3，或 role=超强主攻
          2. 存在可选炸弹（_recommend_bomb_from_mask 非空）

        支线1（is_teammate=True，队友出牌）：
          队友已持 great（greaterPos==teammate_pos）——无论队友出什么牌，
          用炸弹抢队友控制权都是损己利敌（炸队友小王/炸队友炸弹），一律让道。
          不炸队友是本线的硬规则，不再依赖队友剩牌或所出牌型。

        支线2（is_teammate=False，敌方出牌）：
          额外要求：
            a. greater 是普通牌型（非 Bomb/SF，R11 已拦对手出炸场景）
            b. 敌方非报单临界（critical_enemy_remaining > 3）——
               报单临界仍交给原 mid_bomb_cutoff 精确处理
            c. teammate_cover_confidence < 0.5（队友也接不住，一圈无人接）
            d. 开炸价值达标（_mid_aggressive_value_check）
        """
        from collections import Counter

        if not greater_action or greater_action[0] == "PASS":
            return None

        group_type_map = self._group_type_map or {}
        type_counter = Counter(group_type_map.values())
        bomb_count = int(
            type_counter.get("Bomb", 0) + type_counter.get("StraightFlush", 0)
        )
        role = self._current_role or "主攻"
        if not (bomb_count >= 3 or role == "超强主攻"):
            return None

        belief = game_state.get("_belief") or {}
        phase_relation = game_state.get("_phase_relation") or {}
        hand_counts = belief.get("hand_counts") or game_state.get("numofplayers") or {}

        if is_teammate:
            # GUA-205 支线1：队友已持 great（greaterPos==teammate_pos）。
            # 无论队友出什么牌，用炸弹抢队友控制权都是损己利敌
            # （炸队友小王/炸队友炸弹都帮敌方），一律让道。
            self.logger.info(
                "GUA-205 支线1 队友持 great(greaterPos=%d) → 让道不炸",
                teammate_pos)
            return None
        else:
            from src.v.nn.guards.v7_guards import (
                get_action_type, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
            )
            gt = get_action_type(greater_action)
            if gt in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                return None
            critical_enemy_seat = int(phase_relation.get("critical_enemy_seat", -1))
            critical_enemy_remaining = 27
            if isinstance(hand_counts, dict):
                critical_enemy_remaining = int(hand_counts.get(critical_enemy_seat, 27) or 27)
            elif isinstance(hand_counts, list) and critical_enemy_seat < len(hand_counts):
                critical_enemy_remaining = int(hand_counts[critical_enemy_seat] or 27)
            if critical_enemy_remaining <= 3:
                return None
            teammate_cover_confidence = float(
                phase_relation.get("teammate_cover_confidence", 0.0) or 0.0
            )
            if teammate_cover_confidence >= 0.5:
                return None
            if not self._mid_aggressive_value_check(
                game_state, card_mask, hand_cards, cur_rank,
                teammate_pos=teammate_pos,
            ):
                return None

        # GUA-218: 抢攻选炸最廉优先（保留高价值同花顺给后续领出）。
        # greater 已保证非炸类（上方 gt 拦截），任意炸都能赢回合；
        # _mid_aggressive_value_check 已保证 enemy_bomb_risk_max<0.5，
        # 故最廉炸足够。不带入 GUA-172 主路径的「单张王 PASS 优先」。
        bomb = self._recommend_cheapest_bomb_from_action_list(
            game_state.get("actionList") or [], cur_rank)
        if not bomb:
            bomb = self._recommend_bomb_from_mask(
                card_mask, cur_rank,
                action_list=game_state.get("actionList") or [],
            )
        if not bomb:
            return None

        tagged = dict(bomb)
        tagged["intent"] = "mid_aggressive_bomb"
        return tagged

    def _mid_aggressive_value_check(
        self,
        game_state: Dict[str, Any],
        card_mask: Dict[str, tuple],
        hand_cards: List[str],
        cur_rank: str,
        *,
        teammate_pos: int,
    ) -> bool:
        """GUA-205：开炸价值判断（支线2 专用）。

        同时满足才算有开炸价值：
          1. 本手含 ≥3 炸弹族（bomb_count>=3）或 role=超强主攻（外层已保证）
          2. enemy_bomb_risk_max < 0.5（敌方反炸风险不失控）
          3. 手牌总张数 > 3（非只剩炸弹等收尾阶段）
        """
        phase_relation = game_state.get("_phase_relation") or {}
        enemy_bomb_risk_max = float(
            phase_relation.get("enemy_bomb_risk_max", 0.0) or 0.0
        )
        if enemy_bomb_risk_max >= 0.5:
            return False
        if not hand_cards or len(hand_cards) <= 3:
            return False
        return True

    def _recommend_lead_impl(
        self, game_state, card_mask, hand_cards, cur_rank
    ) -> Optional[Dict[str, Any]]:
        """
        领出推荐：优先推小单张或小对子（非 core 组），遵守首出高压线。
        """
        from src.v.nn.guards.v7_guards import (
            get_card_rank, ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR,
        )

        def _prank(internal_rank: str) -> str:
            """内部 rank → 平台 actionList rank 名。"""
            return self.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

        # ── 检查：进贡后慎出单张（P-H01）──
        # 如果有进贡背景，避免出单张给对手进贡机会
        is_tribute_round = game_state.get("isTributeRound", False)
        hand_size = len(hand_cards)

        groups = self._build_group_index(card_mask)

        # 非 core 组的牌 → 可以直接单出/对出
        # 散牌 (gid=-1) → 不在 groups 中，单独收集
        singles = self._scatter_singles(card_mask)

        group_type_map = self._group_type_map or {}
        group_members = self._group_members or None
        _PROTECTED_LEAD_CORE = frozenset(("Bomb", "StraightFlush", "straight"))

        def _single_breaks_protected_core(card: str) -> bool:
            pr = _prank(get_card_rank(str(card)))
            broken = self._get_broken_core_type(
                ["Single", pr, [str(card)]],
                card_mask,
                group_type_map,
                group_members,
            )
            return broken in _PROTECTED_LEAD_CORE

        # ── 策略：优先出最小的非 core 单张或对子 ──
        if singles and not is_tribute_round:
            singles = self._filter_joker_lead_singles(singles, game_state)
            singles.sort(key=lambda c: self.RANK_ORDER.get(get_card_rank(c), 99))
            for card in singles:
                if _single_breaks_protected_core(card):
                    self.logger.debug(
                        "GUA-075 领出跳过拆 core 单张: %s (broken=%s)",
                        card,
                        self._get_broken_core_type(
                            ["Single", _prank(get_card_rank(str(card))), [str(card)]],
                            card_mask, group_type_map, group_members,
                        ),
                    )
                    continue
                return {
                    "type": "Single",
                    "rank": _prank(get_card_rank(str(card))),
                    "cards": [str(card)],
                }

        # 如果没有安全单张，尝试非 core 对子
        pair_groups = [(gid, ginfo) for gid, ginfo in groups.items()
                       if ginfo["type"] in ("pair",) and ginfo["is_core"] <= 0
                       and len(ginfo["cards"]) >= 2]
        if pair_groups:
            # 找 rank 最小的对子
            def _pair_sort_key(item):
                gid, ginfo = item
                card = ginfo["cards"][0]
                return self.RANK_ORDER.get(get_card_rank(str(card)), 99)
            gid, ginfo = min(pair_groups, key=_pair_sort_key)
            cards = sorted(ginfo["cards"])[:2]
            rank = get_card_rank(str(cards[0]))
            return {"type": "Pair", "rank": _prank(rank), "cards": cards}

        # 没能从非 core 组找到 → 出最小散牌（即使进贡）
        if singles:
            singles.sort(key=lambda c: self.RANK_ORDER.get(get_card_rank(c), 99))
            return {"type": "Single", "rank": _prank(get_card_rank(singles[0])), "cards": [str(singles[0])]}

        return None

    def _recommend_counter_bomb_in_action_list(
        self, game_state: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """GUA-123：从平台 actionList 选最小足够反炸（敌 sprint ≤5 张）。"""
        from src.v.nn.endgame.endgame_decide import (
            _is_following_enemy_bomb_control,
            _enemy_bomb_sprint_remaining,
            select_counter_bomb_like,
            action_list_item_to_feed_recommendation,
        )

        if not _is_following_enemy_bomb_control(game_state):
            return None
        enemy_rem = _enemy_bomb_sprint_remaining(game_state)
        if enemy_rem is None or enemy_rem > 5:
            return None
        greater_action = game_state.get("greaterAction")
        action_list = game_state.get("actionList") or []
        picked = select_counter_bomb_like(action_list, greater_action, game_state)
        if not picked:
            return None
        _, act = picked
        return action_list_item_to_feed_recommendation(
            act, "mid_counter_enemy_bomb",
        )


    def _is_in_endgame_state(self, hand_cards, game_state):
        """GUA-165: 手牌 ≤ 10 张或命中 endgame Q1 → 放行百搭作单张。"""
        if len(hand_cards) <= 10:
            return True
        if game_state.get("_endgame_q1_hit"):
            return True
        if game_state.get("_endgame_in_progress"):
            return True
        return False

    def _has_non_wild_single_press(
        self, hand_cards, greater_val, cur_rank, wild_card
    ):
        """GUA-165: 是否存在非百搭 natural 单张能压对手单张。"""
        from src.v.nn.guards.v7_guards import get_card_value
        for c in hand_cards:
            if c == wild_card:
                continue
            try:
                if get_card_value(str(c), cur_rank) > greater_val:
                    return True
            except Exception:
                continue
        return False

    def _recommend_min_press_impl(
        self, game_state, card_mask, greater_action, greater_type,
        hand_cards, cur_rank,
        *,
        apply_belief_gate: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        跟上家牌：找同型可压中最小的（节牌力）。
        如果无同型可压 → 返回 None（不走炸弹推荐，让回退路径决定是否炸）。
        """
        from src.v.nn.guards.v7_guards import (
            get_action_type, get_action_rank, get_card_rank,
            get_card_value, _extract_action_cards,
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
            ACTION_TYPE_SINGLE, ACTION_TYPE_PAIR, ACTION_TYPE_TRIPS,
            ACTION_TYPE_STRAIGHT, ACTION_TYPE_THREE_WITH_TWO,
            ACTION_TYPE_THREE_PAIR, ACTION_TYPE_TWO_TRIPS,
        )
        from collections import Counter

        if not greater_action or greater_action[0] == "PASS":
            return None
        if greater_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            # 对手出了炸弹，不推荐跟（走回退判断是否该炸）
            return None

        greater_rank = get_action_rank(greater_action)
        if not greater_rank:
            return None

        # GUA-075：用 get_card_value 比较（考虑级牌 cur_rank 提升）
        # GUA-255：greater_val 必须用「主牌 rank」而非 greater_cards[0]——
        # 平台 TWT 动作 [type,rank,[cards]] 的 cards 首位常为带牌（如
        # TWT/7 ['C5','H7','D5','S7','C7'] 首位 C5 是带牌，value=3），
        # 若按首位算会误以为 666 能压 777 → 推荐 666+KK 被 actionList 拒
        # → PASS，真正可压的 JJJ+KK 从未考虑（match=6a86911a L370-377）。
        # 普通同型（Pair/Trips/Straight/ThreePair/TwoTrips）也一律用主牌 rank。
        greater_rank = get_action_rank(greater_action)
        if not greater_rank:
            return None
        if greater_rank in ("B", "R"):
            # 大小王主牌（Single 场景），用实际牌面取值，避免 'HB'/'HR' 误判
            greater_cards = _extract_action_cards(greater_action)
            if greater_cards:
                greater_val = get_card_value(str(greater_cards[0]), cur_rank)
            else:
                greater_val = self.RANK_ORDER.get(greater_rank, 0)
        else:
            greater_val = get_card_value(f"H{greater_rank}", cur_rank)

        groups = self._build_group_index(card_mask)

        def _gate(rec: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not apply_belief_gate:
                return rec
            return self._apply_belief_gate_min_press(game_state, rec)

        def _to_platform_rank(internal_rank: str) -> str:
            """将内部 rank 转成平台 actionList 中使用的 rank 名。"""
            return self.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

        # ── 单张处理 ──
        if greater_type == "Single":
            natural_singles = list(self._scatter_singles(card_mask))
            # GUA-165: natural_can_press 排除百搭 HA（wild 不算 natural）
            natural_can_press = any(
                get_card_value(str(card), cur_rank) > greater_val
                for card in natural_singles if card != f"H{cur_rank}"
            )
            # GUA-165 wild-guard: 散张里无非百搭 natural 可压、但百搭能压对手 5-T 单时
            wild_card_gua165 = f"H{cur_rank}"
            wild_can_press = (
                wild_card_gua165 in hand_cards
                and wild_card_gua165 in natural_singles
                and get_card_value(str(wild_card_gua165), cur_rank) > greater_val
            )
            if (
                wild_can_press
                and not natural_can_press
                and greater_rank in {"5", "6", "7", "8", "9", "T"}
                and self._current_role in ("主攻", "助攻", "超强主攻")
                and len(hand_cards) > 10
                and not self._is_in_endgame_state(hand_cards, game_state)
            ):
                from src.v.nn.guards.v7_guards import get_card_rank as _gua165_gr
                has_borrowable_pair = any(
                    ginfo["type"] in ("pair", "pair_in_three_with_two", "pair_in_three_pair")
                    and ginfo["is_core"] <= 0
                    and any(_gua165_gr(str(c)) in ("9", "T", "J") for c in ginfo["cards"])
                    for ginfo in groups.values()
                )
                if not has_borrowable_pair:
                    return None  # GUA-165 让出
            # GUA-157 + GUA-166: role 扩到主攻（5-9 严一档），助攻/超强主攻 5-T
            if self._current_role == "主攻":
                borrow_window = {"5", "6", "7", "8", "9"}
            else:
                borrow_window = {"5", "6", "7", "8", "9", "T"}
            # GUA-166: small_natural_can_press 排除大小王 + 百搭
            from src.v.nn.guards.v7_guards import get_card_rank as _gua166_gr
            small_natural_can_press = any(
                get_card_value(str(c), cur_rank) > greater_val
                for c in natural_singles
                if _gua166_gr(str(c)) not in ("HR", "SB") and c != f"H{cur_rank}"
            )
            allow_assist_pair_borrow = (
                self._current_role in ("主攻", "助攻", "超强主攻")
                and greater_rank in borrow_window
                and not small_natural_can_press
            )
            singles = self._collect_single_follow_candidates(
                card_mask,
                groups,
                hand_cards,
                cur_rank,
                allow_assist_pair_borrow=allow_assist_pair_borrow,
            )
            if singles:
                candidates = []
                for c in singles:
                    c_val = get_card_value(str(c), cur_rank)
                    if c_val > greater_val:
                        candidates.append((c_val, c, get_card_rank(str(c))))
                if candidates:
                    candidates = self._filter_joker_press_single_candidates(
                        candidates, game_state
                    )
                    # GUA-165: 百搭（curRank H 花色）排最后
                    wild_card_sort = f"H{cur_rank}"
                    candidates.sort(key=lambda x: (1 if x[1] == wild_card_sort else 0, x[0]))
                    _, best, best_rank = candidates[0]
                    return _gate({
                        "type": "Single",
                        "rank": _to_platform_rank(best_rank),
                        "cards": [str(best)],
                    })
                return None

        # ── 三带二（ThreeWithTwo）：从手牌直接建，不用组引擎子结构 ──
        if greater_type == "ThreeWithTwo":
            rec = self._build_three_with_two_press(
                hand_cards,
                greater_val,
                cur_rank,
                "min",
                card_mask=card_mask,
                group_type_map=self._group_type_map,
                group_members=self._group_members,
            )
            if rec:
                return _gate(rec)
            if self._should_force_three_with_two_counter_press(game_state, greater_action):
                return _gate(
                    self._build_three_with_two_press(
                        hand_cards,
                        greater_val,
                        cur_rank,
                        "min",
                        card_mask=card_mask,
                        group_type_map=self._group_type_map,
                        group_members=self._group_members,
                        allow_break_protected_core=True,
                    )
                )
            return None

        # ── 三连对 / 钢板：从 pair_in_three_pair / trip_in_steel_plate 重建连续结构 ──
        if greater_type == "ThreePair":
            rec = self._build_consecutive_structure_press(
                groups, "pair_in_three_pair", 3, greater_val, cur_rank, "min",
            )
            if rec:
                rec["rank"] = _to_platform_rank(rec["rank"])
                return _gate(rec)
            return None
        if greater_type == "TwoTrips":
            rec = self._build_consecutive_structure_press(
                groups, "trip_in_steel_plate", 2, greater_val, cur_rank, "min",
            )
            if rec:
                rec["rank"] = _to_platform_rank(rec["rank"])
                return _gate(rec)
            return None

        # ── 普通同型匹配（Pair / Trips / Straight）──
        GTYPE_MAP = {
            "Pair": ("pair", "pair_in_three_pair", "pair_in_three_with_two"),
            "Trips": ("trips", "trip_in_three_with_two", "trip_in_steel_plate"),
            "Straight": ("straight",),
        }
        target_gtypes = GTYPE_MAP.get(greater_type, ())
        if not target_gtypes:
            return None

        candidates = []
        for gid, ginfo in groups.items():
            gtype = ginfo["type"]
            if gtype not in target_gtypes:
                continue
            cards = ginfo["cards"]
            if not cards:
                continue
            c_rank = get_card_rank(str(cards[0]))
            c_val = get_card_value(str(cards[0]), cur_rank)
            c_type = self._group_type_to_platform_action(gtype)

            if c_type == greater_type and c_val > greater_val:
                candidates.append((c_val, gid, ginfo, c_rank, c_type))

        # GUA-233: 压对时允许拆「级牌 trips」（curRank 的三张）取对子，牌力强过普通对。
        if greater_type == "Pair":
            for gid, ginfo in groups.items():
                gtype = ginfo["type"]
                if gtype != "trips":
                    continue
                trip_cards = ginfo["cards"]
                if not trip_cards:
                    continue
                t_rank = get_card_rank(str(trip_cards[0]))
                if t_rank != cur_rank:
                    continue
                if len(trip_cards) < 2:
                    continue
                t_val = get_card_value(str(trip_cards[0]), cur_rank)
                if t_val <= greater_val:
                    continue
                pair_two = sorted(str(c) for c in trip_cards)[:2]
                candidates.append((t_val, gid, ginfo, t_rank, "Pair"))

        if not candidates:
            return None

        # 节牌力：选最小能压的
        candidates.sort(key=lambda x: x[0])
        _, gid, ginfo, c_rank, c_type = candidates[0]

        # GUA-233: trips 拆对 → 只取两张（普通对子/Pair 组取全量）
        if ginfo["type"] == "trips" and c_type == "Pair":
            out_cards = sorted(str(c) for c in ginfo["cards"])[:2]
        else:
            out_cards = sorted(ginfo["cards"])

        return _gate({
            "type": c_type,
            "rank": _to_platform_rank(c_rank),
            "cards": out_cards,
        })

    def _build_three_with_two_press(
        self,
        hand_cards: List[str],
        greater_val: int,
        cur_rank: str,
        strategy: str = "min",
        *,
        card_mask: Optional[Dict] = None,
        group_type_map: Optional[Dict[int, str]] = None,
        group_members: Optional[Dict[int, List[str]]] = None,
        allow_break_protected_core: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        从手牌直接构建三带二（ThreeWithTwo）可压推荐。
        不依赖组引擎子结构，避免 trip_in_three_with_two 只有3张的歧义。

        strategy: "min"=节牌力（跟上家）, "max"=卡下家（选最大）。
        GUA-081: 跳过会部分拆 bomb/同花顺 core 的三张，尝试下一档 rank。
        GUA-114: min 策略带牌优先独立对子（gsize=2 / 剩余恰 2 张），避免从 ≥3 张同点抠对留孤张。
        """
        from collections import Counter
        from src.v.nn.guards.v7_guards import get_card_rank

        rank_counts: Dict[str, List[str]] = {}
        wildcard_str = f"H{cur_rank}"
        for c in hand_cards:
            r = get_card_rank(str(c))
            rank_counts.setdefault(r, []).append(c)
        if cur_rank in rank_counts:
            rank_counts[cur_rank].sort(key=lambda c: 1 if c == wildcard_str else 0)

        # 构建 SF/Bomb 牌集（pair 选择时优先避开，避免后续 broken 拦截）
        cards_in_sf_bomb: set = set()
        if group_type_map and group_members:
            for _gid, _gtype in group_type_map.items():
                if _gtype in ("Bomb", "StraightFlush"):
                    cards_in_sf_bomb.update(group_members.get(_gid, []))

        # 找能压的三张（rank > greater_val 且 ≥3 张）
        from src.v.nn.guards.v7_guards import get_card_value as _gcv
        trip_candidates = []
        for rank_str, cards in rank_counts.items():
            if len(cards) < 3:
                continue
            rank_val = _gcv(str(cards[0]), cur_rank)
            if rank_val > greater_val:
                trip_candidates.append((rank_val, rank_str, cards[:3]))

        if not trip_candidates:
            return None

        def _pair_is_natural(rank_str: str, pair_cards: List[str], remaining: Dict[str, List[str]]) -> bool:
            """独立对子：该 rank 剩余恰 2 张，或 card_mask 中两张均为 gsize=2。"""
            cards_left = remaining.get(rank_str) or []
            if len(cards_left) == 2:
                return True
            if card_mask and len(cards_left) < 3:
                gsizes = []
                for c in pair_cards:
                    info = card_mask.get(c)
                    if info and len(info) >= 3:
                        gsizes.append(info[2])
                if len(gsizes) == len(pair_cards) and all(g == 2 for g in gsizes):
                    return True
            return False

        def _pair_has_sf_bomb(pair_cards: List[str]) -> bool:
            return any(c in cards_in_sf_bomb for c in pair_cards)

        def _find_available_pair(
            exclude_cards: List[str], prefer_large: bool = False
        ) -> Optional[Tuple[str, List[str]]]:
            remaining: Dict[str, List[str]] = {}
            for c in hand_cards:
                if c in exclude_cards:
                    continue
                r = get_card_rank(str(c))
                if r not in remaining:
                    remaining[r] = []
                remaining[r].append(c)
            pair_opts = []
            for r, cards in remaining.items():
                if len(cards) >= 2:
                    pair_opts.append((_gcv(str(cards[0]), cur_rank), r, cards[:2]))
            if not pair_opts:
                return None
            if strategy == "min":
                natural_opts = [
                    o
                    for o in pair_opts
                    if _pair_is_natural(o[1], o[2], remaining)
                ]
                pool = natural_opts if natural_opts else pair_opts
            else:
                pool = pair_opts
            pool.sort(key=lambda x: (
                1 if _pair_has_sf_bomb(x[2]) else 0,
                -x[0] if prefer_large else x[0],
            ))
            return (pool[0][1], pool[0][2])

        want_large = (strategy == "max")
        trip_candidates.sort(key=lambda x: -x[0] if want_large else x[0])

        for _, trip_rank, trip_cards in trip_candidates:
            pair = _find_available_pair(trip_cards, prefer_large=want_large)
            if not pair:
                continue
            pair_rank, pair_cards = pair
            platform_rank = self.INTERNAL_TO_PLATFORM_RANK.get(trip_rank, trip_rank)
            rec_cards = sorted(trip_cards + pair_cards)
            if card_mask and group_type_map is not None:
                broken = self._get_broken_core_type(
                    ["ThreeWithTwo", platform_rank, rec_cards],
                    card_mask,
                    group_type_map,
                    group_members,
                )
                if broken in ("Bomb", "StraightFlush") and not allow_break_protected_core:
                    continue
            return {
                "type": "ThreeWithTwo",
                "rank": platform_rank,
                "cards": rec_cards,
            }

        return None

    def _should_force_three_with_two_counter_press(
        self,
        game_state: Dict[str, Any],
        greater_action: Optional[List[Any]],
    ) -> bool:
        """高压三带二对抗下，允许受控拆炸续压，避免直接双 PASS。"""
        from src.v.nn.guards.v7_guards import get_action_type

        if not greater_action or get_action_type(greater_action) != "ThreeWithTwo":
            return False

        role = self._current_role or "主攻"
        if role != "主攻":
            return False

        phase_relation = game_state.get("_phase_relation") or {}
        belief = game_state.get("_belief") or {}
        hand_counts = belief.get("hand_counts") or game_state.get("numofplayers") or {}

        def _remaining(seat: int, default: int = 27) -> int:
            if seat < 0:
                return default
            if isinstance(hand_counts, dict):
                try:
                    return int(hand_counts.get(seat, default))
                except (TypeError, ValueError):
                    return default
            if isinstance(hand_counts, list) and seat < len(hand_counts):
                try:
                    return int(hand_counts[seat])
                except (TypeError, ValueError):
                    return default
            return default

        greater_pos = int(game_state.get("greaterPos", -1))
        critical_enemy_seat = int(phase_relation.get("critical_enemy_seat", -1))
        enemy_shape_hint = str(phase_relation.get("enemy_shape_hint", "unknown") or "unknown")
        teammate_cover_confidence = float(
            phase_relation.get("teammate_cover_confidence", 0.0) or 0.0
        )

        target_remaining = _remaining(greater_pos)
        if greater_pos == critical_enemy_seat:
            target_remaining = min(target_remaining, _remaining(critical_enemy_seat))

        return (
            enemy_shape_hint == "structured"
            and 1 <= target_remaining <= 9
            and teammate_cover_confidence < 0.5
        )

    def _build_consecutive_structure_press(
        self, groups, member_type, chain_len, greater_val, cur_rank, strategy,
    ):
        """
        从组牌引擎子结构重建连续结构候选（ThreePair / TwoTrips）。
        member_type: "pair_in_three_pair"(三连对) 或 "trip_in_steel_plate"(钢板)
        chain_len: 三连对=3(三对), 钢板=2(两组三张)
        strategy: "min"=跟上家节牌力, "max"=卡下家选最大
        """
        from src.v.nn.guards.v7_guards import get_card_rank, get_card_value

        rank_groups = {}
        for gid, ginfo in groups.items():
            if ginfo["type"] != member_type:
                continue
            cards = ginfo["cards"]
            if not cards:
                continue
            r = get_card_rank(str(cards[0]))
            val = get_card_value(str(cards[0]), cur_rank)
            rank_groups.setdefault(val, []).append((val, r, gid, ginfo))

        if len(rank_groups) < chain_len:
            return None

        sorted_vals = sorted(rank_groups.keys())
        candidates = []
        for i in range(len(sorted_vals) - chain_len + 1):
            window = sorted_vals[i:i + chain_len]
            if window[-1] - window[0] != chain_len - 1:
                continue
            start_val = window[0]
            if start_val <= greater_val:
                continue
            all_cards = []
            for v in window:
                all_cards.extend(rank_groups[v][0][3]["cards"])
            platform_type = "ThreePair" if member_type == "pair_in_three_pair" else "TwoTrips"
            start_rank = get_card_rank(str(all_cards[0]))
            candidates.append({
                "type": platform_type,
                "rank": start_rank,
                "cards": sorted(all_cards),
            })

        if not candidates:
            return None
        if strategy == "min":
            candidates.sort(key=lambda c: get_card_value(c["cards"][0], cur_rank))
        else:
            candidates.sort(key=lambda c: -get_card_value(c["cards"][0], cur_rank))
        return candidates[0]

    # 卡下家「脖子位」点数档（全牌型主牌/顶牌）
    _XIAJIA_NECK_RANKS = frozenset({"9", "T", "J"})

    def _xia_jia_remaining(self, game_state: Dict[str, Any]) -> int:
        """下家剩余张数；缺省按 27（未危急）。"""
        my_pos = int(game_state.get("myPos", self.player_id) or 0)
        xia = (my_pos + 1) % 4
        nop = game_state.get("numofplayers") or []
        if isinstance(nop, (list, tuple)) and len(nop) > xia:
            try:
                return int(nop[xia])
            except (TypeError, ValueError):
                pass
        public = game_state.get("publicInfo") or []
        if isinstance(public, list) and len(public) > xia:
            try:
                return int((public[xia] or {}).get("rest", 27))
            except (TypeError, ValueError):
                pass
        return 27

    def _resolve_xiajia_press_mode(
        self,
        game_state: Dict[str, Any],
        hand_cards: List[str],
        n_pressable: int,
    ) -> str:
        """GUA-075 卡下家分档：critical_max / follow_min / neck。

        - 下家 rest≤5 或残局 → 危急 max
        - 强牌(主攻/超强主攻)且可压同型≥2 → 顺势 min
        - 否则弱牌卡点（优先 9/T/J，再全体 min）
        """
        if n_pressable <= 0:
            return "follow_min"
        rest = self._xia_jia_remaining(game_state)
        # 危急只看下家短牌（≤5）；不因「本方手数少」误判——否则开局试探后
        # hand=6 会被 _is_in_endgame_state 打成 critical_max 仍出大王。
        if rest <= 5:
            return "critical_max"
        role = self._current_role or ""
        if role in ("主攻", "超强主攻") and n_pressable >= 2:
            return "follow_min"
        return "neck"

    @staticmethod
    def _pick_xiajia_press_candidate(
        candidates: List[Tuple],
        mode: str,
        *,
        wild_card: Optional[str] = None,
        rank_index: int = 2,
        value_index: int = 0,
        payload_index: int = 1,
    ) -> Optional[Tuple]:
        """从 (value, payload, rank, ...) 候选中按卡下家 mode 取一条。"""
        if not candidates:
            return None

        def _wild_key(item: Tuple) -> int:
            if wild_card is None:
                return 0
            payload = item[payload_index]
            card = payload if isinstance(payload, str) else (
                payload[0] if isinstance(payload, (list, tuple)) and payload else ""
            )
            return 1 if card == wild_card else 0

        if mode == "critical_max":
            ordered = sorted(
                candidates,
                key=lambda x: (_wild_key(x), -x[value_index]),
            )
            return ordered[0]

        pool = list(candidates)
        if mode == "neck":
            neck = [
                c for c in candidates
                if str(c[rank_index]) in UltimateWinRateEngineV7._XIAJIA_NECK_RANKS
            ]
            if neck:
                pool = neck
        # follow_min 与 neck（无卡点档时）均为最小够压；百搭靠后
        ordered = sorted(
            pool,
            key=lambda x: (_wild_key(x), x[value_index]),
        )
        return ordered[0]

    def _recommend_max_press_impl(
        self, game_state, card_mask, greater_action, greater_type,
        hand_cards, cur_rank
    ) -> Optional[Dict[str, Any]]:
        """
        卡下家同型压制（GUA-075 定音修订）：
          critical_max — 下家短牌/残局，同型最大
          follow_min   — 强牌+多可压，顺势最小够压
          neck         — 弱牌卡点≈J（9/T/J），否则最小够压
        无同型可压 → 返回 None。成功时附带 ``_xiajia_mode`` 供日志（调用方应 pop）。
        """
        from src.v.nn.guards.v7_guards import (
            get_action_type, get_action_rank, get_card_rank, get_card_value,
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )

        if not greater_action or greater_action[0] == "PASS":
            return None
        if greater_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return None

        greater_rank = get_action_rank(greater_action)
        if not greater_rank:
            return None
        # GUA-255：主牌 rank 算牌力（Single/Pair/Trips/Straight 等）；TWT 另支
        try:
            greater_val = get_card_value(
                f"S{greater_rank}" if greater_rank not in ("B", "R") else (
                    "SB" if greater_rank == "B" else "HR"
                ),
                cur_rank,
            )
        except Exception:
            greater_cards = greater_action[2] if len(greater_action) >= 3 else []
            greater_val = get_card_value(
                str(greater_cards[0]) if greater_cards else greater_rank, cur_rank)

        groups = self._build_group_index(card_mask)

        def _to_platform_rank(internal_rank: str) -> str:
            return self.INTERNAL_TO_PLATFORM_RANK.get(internal_rank, internal_rank)

        def _tag(rec: Dict[str, Any], mode: str) -> Dict[str, Any]:
            rec["_xiajia_mode"] = {
                "critical_max": "危急",
                "follow_min": "顺势",
                "neck": "卡点",
            }.get(mode, mode)
            return rec

        # 单张
        if greater_type == "Single":
            natural_singles = list(self._scatter_singles(card_mask))
            wild_card_gua165 = f"H{cur_rank}"
            natural_can_press = any(
                get_card_value(str(c), cur_rank) > greater_val
                for c in natural_singles if c != wild_card_gua165
            )
            wild_can_press = (
                wild_card_gua165 in hand_cards
                and wild_card_gua165 in natural_singles
                and get_card_value(str(wild_card_gua165), cur_rank) > greater_val
            )
            if (
                wild_can_press
                and not natural_can_press
                and greater_rank in {"5", "6", "7", "8", "9", "T"}
                and self._current_role in ("主攻", "助攻", "超强主攻")
                and len(hand_cards) > 10
                and not self._is_in_endgame_state(hand_cards, game_state)
            ):
                from src.v.nn.guards.v7_guards import get_card_rank as _gua165_gr_max
                has_borrowable_pair = any(
                    ginfo["type"] in ("pair", "pair_in_three_with_two", "pair_in_three_pair")
                    and ginfo["is_core"] <= 0
                    and any(_gua165_gr_max(str(c)) in ("9", "T", "J") for c in ginfo["cards"])
                    for ginfo in groups.values()
                )
                if not has_borrowable_pair:
                    return None
            singles = self._collect_single_follow_candidates(
                card_mask, groups, hand_cards, cur_rank)
            if not singles:
                return None
            candidates = []
            for c in singles:
                c_rank = get_card_rank(str(c))
                c_val = get_card_value(str(c), cur_rank)
                if c_val > greater_val:
                    candidates.append((c_val, c, c_rank))
            if not candidates:
                return None
            mode = self._resolve_xiajia_press_mode(
                game_state, hand_cards, len(candidates))
            picked = self._pick_xiajia_press_candidate(
                candidates, mode, wild_card=wild_card_gua165)
            if not picked:
                return None
            _, best, best_rank = picked
            return _tag({
                "type": "Single",
                "rank": _to_platform_rank(best_rank),
                "cards": [str(best)],
            }, mode)

        # 三带二：按 mode 选 min/max（卡点/顺势用 min；危急用 max）
        if greater_type == "ThreeWithTwo":
            # 先估可压 trips 数以定 mode
            from src.v.nn.guards.v7_guards import get_card_rank as _gr
            rc: Dict[str, int] = {}
            for c in hand_cards:
                r = _gr(str(c))
                rc[r] = rc.get(r, 0) + 1
            n_trip_press = 0
            for r, n in rc.items():
                if n < 3:
                    continue
                try:
                    sample = "SB" if r == "B" else ("HR" if r == "R" else f"S{r}")
                    if get_card_value(sample, cur_rank) > greater_val:
                        n_trip_press += 1
                except Exception:
                    n_trip_press += 1
            mode = self._resolve_xiajia_press_mode(
                game_state, hand_cards, max(n_trip_press, 1))
            twt_strategy = "max" if mode == "critical_max" else "min"
            rec = self._build_three_with_two_press(
                hand_cards,
                greater_val,
                cur_rank,
                twt_strategy,
                card_mask=card_mask,
                group_type_map=self._group_type_map,
                group_members=self._group_members,
            )
            if rec:
                return _tag(rec, mode)
            if self._should_force_three_with_two_counter_press(game_state, greater_action):
                forced = self._build_three_with_two_press(
                    hand_cards,
                    greater_val,
                    cur_rank,
                    twt_strategy,
                    card_mask=card_mask,
                    group_type_map=self._group_type_map,
                    group_members=self._group_members,
                    allow_break_protected_core=True,
                )
                if forced:
                    return _tag(forced, mode)
            return None

        # 三连对 / 钢板
        if greater_type == "ThreePair":
            mode = self._resolve_xiajia_press_mode(game_state, hand_cards, 2)
            strat = "max" if mode == "critical_max" else "min"
            rec = self._build_consecutive_structure_press(
                groups, "pair_in_three_pair", 3, greater_val, cur_rank, strat,
            )
            if rec:
                rec["rank"] = _to_platform_rank(rec["rank"])
                return _tag(rec, mode)
            return None
        if greater_type == "TwoTrips":
            mode = self._resolve_xiajia_press_mode(game_state, hand_cards, 2)
            strat = "max" if mode == "critical_max" else "min"
            rec = self._build_consecutive_structure_press(
                groups, "trip_in_steel_plate", 2, greater_val, cur_rank, strat,
            )
            if rec:
                rec["rank"] = _to_platform_rank(rec["rank"])
                return _tag(rec, mode)
            return None

        # Pair / Trips / Straight
        GTYPE_MAP = {
            "Pair": ("pair", "pair_in_three_pair", "pair_in_three_with_two"),
            "Trips": ("trips", "trip_in_three_with_two", "trip_in_steel_plate"),
            "Straight": ("straight",),
        }
        target_gtypes = GTYPE_MAP.get(greater_type, ())
        if not target_gtypes:
            return None

        candidates = []
        for gid, ginfo in groups.items():
            if ginfo["type"] not in target_gtypes:
                continue
            cards = ginfo["cards"]
            if not cards:
                continue
            # Straight：用声明/顶牌；其余用主牌第一张
            if greater_type == "Straight":
                c_rank = get_card_rank(str(cards[-1])) if cards else get_card_rank(str(cards[0]))
            else:
                c_rank = get_card_rank(str(cards[0]))
            c_val = get_card_value(str(cards[0] if greater_type != "Straight" else cards[-1]), cur_rank)
            c_type = self._group_type_to_platform_action(ginfo["type"])
            if c_type == greater_type and c_val > greater_val:
                candidates.append((c_val, sorted(ginfo["cards"]), c_rank, c_type))

        if not candidates:
            return None

        mode = self._resolve_xiajia_press_mode(
            game_state, hand_cards, len(candidates))
        picked = self._pick_xiajia_press_candidate(
            candidates, mode, rank_index=2, value_index=0, payload_index=1)
        if not picked:
            return None
        _, cards_out, c_rank, c_type = picked
        return _tag({
            "type": c_type,
            "rank": _to_platform_rank(c_rank),
            "cards": list(cards_out),
        }, mode)

    # ── R11 改炸预检 + 炸弹推荐（GUA-075 扩展）────────────

    def _r11_bomb_throttle_check(
        self, game_state: Dict[str, Any], greater_action: List[str],
        greater_rank: str, cur_rank: str,
    ) -> Tuple[bool, str]:
        """
        R11 预检：当推荐器无同型可压时，决定是否允许改炸。

        复用 v7_guards 的全局牌记忆 + 上家让道模块级状态，
        但作为轻量预检（不操作 actionList，只返回 can_bomb + reason）。

        Returns:
            (can_bomb: bool, reason: str)
        """
        from src.v.nn.guards.v7_guards import (
            get_action_type, ACTION_TYPE_SINGLE, ACTION_TYPE_BOMB,
            ACTION_TYPE_STRAIGHT_FLUSH,
            _UPPER_SKIP_MEMORY, _POST_BOMB_BLOCK_TYPE,
            _compute_pass_num, _count_remaining_suppressors,
        )

        my_pos = game_state.get("myPos", self.player_id)
        greater_pos = game_state.get("greaterPos", -1)

        # ── 前置：对手出炸/同花顺 → 不跟（改压更高炸弹是另一回事）──
        gt = get_action_type(greater_action)
        if gt in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return (False, f"对手出{gt} → 不跟炸弹")

        opponent_positions = [(my_pos + 1) % 4, (my_pos + 3) % 4]
        if greater_pos not in opponent_positions:
            return (False, "非对手出牌")

        upper_opp = (my_pos + 3) % 4
        is_upper = (greater_pos == upper_opp)

        # ══════════════ 上家让道（第一圈 PASS，第二圈改炸）══════════════
        if is_upper:
            skip_key = (my_pos, upper_opp)
            prev_skipped = _UPPER_SKIP_MEMORY.get(skip_key)

            if prev_skipped == gt:
                # 第二圈：同样牌型队友未接 → 允许改炸
                del _UPPER_SKIP_MEMORY[skip_key]
                _POST_BOMB_BLOCK_TYPE[skip_key] = gt
                self.logger.debug(
                    "R11 预检: 上家第二轮出%s → 允许改炸（炸后禁出%s）", gt, gt)
                return (True, f"上家第二轮出{gt}改炸")
            else:
                # 第一圈：让道 PASS
                _UPPER_SKIP_MEMORY[skip_key] = gt
                _POST_BOMB_BLOCK_TYPE.pop(skip_key, None)
                self.logger.debug("R11 预检: 上家出%s无同型 → 第一圈让道PASS", gt)
                return (False, f"上家出{gt}第一圈让道")

        # ══════════════ 下家：全局抑制牌检查 ─────────────────────
        # 仅 Single 做全局检查（非 Single 暂走默认 PASS）
        if gt != ACTION_TYPE_SINGLE:
            return (False, f"下家{gt}（非Single）→ 暂不让道改炸")

        tracker = game_state.get("_memory_tracker", None)
        suppressors = _count_remaining_suppressors(tracker, greater_rank, cur_rank)

        # Phase A-1: 抑制牌充足（≥2）→ 不炸
        if suppressors >= 2:
            self.logger.debug(
                "R11 预检: 抑制牌充足(剩余%d张可压%s) → 不炸", suppressors, greater_rank)
            return (False, f"抑制牌充足({suppressors}张)")

        # Phase A-2: 仅剩 1 张 → pass_num==0 时等等
        if suppressors == 1:
            pass_num, _ = _compute_pass_num(game_state, my_pos)
            if pass_num == 0:
                self.logger.debug(
                    "R11 预检: 抑制牌仅1张 pass_num=0 → 等等看")
                return (False, "抑制牌仅1张等等看")

        # Phase A-3: suppressors==0 或 suppressors==1且pass_num>=1 → 允许改炸
        self.logger.debug(
            "R11 预检: 抑制牌=%s pass已进 → 允许改炸", suppressors)
        return (True, f"改炸(suppressors={suppressors})")

    def _recommend_bomb_from_mask(
        self,
        card_mask: Dict,
        cur_rank: str,
        action_list: Optional[List] = None,
    ) -> Optional[Dict[str, Any]]:
        """选择拿权价值最高且与平台动作一致的 Bomb-like 牌型。

        来源优先级：平台 actionList 真源 → _group_members multiset →
        card_mask._group_type_map 退化路径。三者都没有则返回 None。
        排序：同花顺(9) > 五星炸(5) > 四星炸(4)；再按 wild 配牌 + 牌点 + cards 元组。
        """
        from src.v.nn.guards.v7_guards import (
            get_card_rank, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )

        candidates = []
        for action in action_list or []:
            if not isinstance(action, list) or len(action) < 3:
                continue
            if action[0] not in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                continue
            if not isinstance(action[2], list):
                continue
            candidates.append({
                "type": action[0],
                "rank": str(action[1]),
                "cards": sorted(str(card) for card in action[2]),
            })

        if not candidates:
            members_src = self._group_members if self._group_members else {}
            group_type_map = self._group_type_map or {}
            if members_src:
                for gid, g_cards in members_src.items():
                    if gid < 0 or len(g_cards) < 4:
                        continue
                    gtype = group_type_map.get(gid, "")
                    if gtype not in ("Bomb", "StraightFlush"):
                        continue
                    cards = sorted(g_cards)
                    candidates.append({
                        "type": (
                            ACTION_TYPE_STRAIGHT_FLUSH
                            if gtype == "StraightFlush" else ACTION_TYPE_BOMB
                        ),
                        "rank": get_card_rank(str(g_cards[0])),
                        "cards": cards,
                    })
            elif group_type_map:
                # 退化路径：_group_members 为空但 _group_type_map 仍记录 group_id
                gid_to_cards: Dict[int, List[str]] = {}
                for card, info in card_mask.items():
                    if not isinstance(info, tuple) or len(info) < 1:
                        continue
                    gid = info[0]
                    if gid < 0:
                        continue
                    gid_to_cards.setdefault(gid, []).append(card)
                for gid, g_cards in gid_to_cards.items():
                    gtype = group_type_map.get(gid, "")
                    if gtype not in ("Bomb", "StraightFlush") or len(g_cards) < 4:
                        continue
                    cards = sorted(g_cards)
                    candidates.append({
                        "type": (
                            ACTION_TYPE_STRAIGHT_FLUSH
                            if gtype == "StraightFlush" else ACTION_TYPE_BOMB
                        ),
                        "rank": get_card_rank(str(g_cards[0])),
                        "cards": cards,
                    })

        if not candidates:
            return None

        wild_card = "H" + cur_rank

        def priority(candidate: Dict[str, Any]) -> tuple:
            size = len(candidate["cards"])
            strength = 9 if candidate["type"] == ACTION_TYPE_STRAIGHT_FLUSH else size
            return (
                -strength,
                1 if wild_card in candidate["cards"] else 0,
                -self.RANK_ORDER.get(candidate["rank"], -1),
                tuple(candidate["cards"]),
            )

        best = min(candidates, key=priority)
        return {
            "type": best["type"],
            "rank": best["rank"],
            "cards": best["cards"],
        }

    def _recommend_cheapest_bomb_from_action_list(
        self, action_list, cur_rank
    ) -> Optional[Dict[str, Any]]:
        """GUA-172: 从 actionList 选最廉价炸/同花顺。"""
        from src.v.nn.guards.v7_guards import (
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
        )
        candidates = []
        for action in action_list or []:
            if not isinstance(action, list) or len(action) < 3:
                continue
            if action[0] not in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
                continue
            if not isinstance(action[2], list) or len(action[2]) < 4:
                continue
            candidates.append(action)
        if not candidates:
            return None
        def sort_key(action) -> tuple:
            atype = action[0]
            size = len(action[2])
            rank_val = self.RANK_ORDER.get(str(action[1]), 0)
            strength = 9 if atype == ACTION_TYPE_STRAIGHT_FLUSH else size
            return (strength, rank_val, tuple(sorted(str(c) for c in action[2])))
        best = min(candidates, key=sort_key)
        return {
            "type": best[0],
            "rank": str(best[1]),
            "cards": sorted(str(c) for c in best[2]),
        }

    def _recommend_vs_teammate(
        self, game_state, card_mask, greater_action, greater_type
    ) -> Optional[Dict[str, Any]]:
        """对家出牌时：默认 PASS 让道，除非对手在压队友需要解围。"""
        greater_pos = game_state.get("greaterPos", -1)
        my_pos = game_state.get("myPos", self.player_id)
        teammate_pos = (my_pos + 2) % 4

        if greater_pos == teammate_pos:
            # 对家在控牌 → 直接 PASS
            return {"type": "PASS", "rank": "", "cards": []}

        # 队友被压（greaterPos 是对手）且队友剩牌多 → 可能需解围
        # 暂不做复杂解围判断，返回 PASS 让回退路径处理
        return {"type": "PASS", "rank": "", "cards": []}


    @staticmethod
    def _match_chosen_to_original_action_list(
        chosen: Optional[List],
        action_list: List,
    ) -> int:
        """GUA-085: group_actions 选中项 → 原始 actionList 下标（内容精确匹配）。"""
        if not chosen or not action_list:
            return 0
        for orig_i, candidate in enumerate(action_list):
            if candidate == chosen:
                return orig_i
        return 0

    @staticmethod
    def _fallback_group_action_index(
        group_idx: int,
        group_filter_map: List[int],
        action_map: List[int],
        action_list_len: int,
    ) -> int:
        """group_filter_map 旧式映射（仅内容回查失败时兜底）。"""
        if group_idx < len(group_filter_map):
            filtered_idx = group_filter_map[group_idx]
        else:
            filtered_idx = group_idx
        if filtered_idx < len(action_map):
            original_idx = action_map[filtered_idx]
        else:
            original_idx = 0
        if original_idx < 0 or original_idx >= action_list_len:
            return 0
        return original_idx

    def _match_actionList(
        self, recommendation: Dict[str, Any], action_list: List
    ) -> int:
        """
        GUA-075: actionList 匹配器 — 三要素精确匹配（牌型/点数/牌张）。

        在原始 actionList 中查找与推荐方案匹配的候选动作。
        支持平台格式 [type, rank, [cards]] 和简式 ["S2"]。

        Args:
            recommendation: {type, rank, cards}
            action_list: 原始 actionList（服务端下发的完整列表）

        Returns:
            actIndex (0-based) 或 -1（未找到）
        """
        if not recommendation or not action_list:
            return -1

        r_type = recommendation.get("type", "")
        r_rank = recommendation.get("rank", "")
        r_cards = sorted(recommendation.get("cards", []) or [])

        # PASS 特殊处理：找第一个 PASS 候选
        if r_type == "PASS":
            for i, candidate in enumerate(action_list):
                if candidate and candidate[0] == "PASS":
                    return i
            return -1

        for i, candidate in enumerate(action_list):
            if not candidate:
                continue
            # 平台格式: [type, rank, [cards]]
            c_type = candidate[0] if len(candidate) >= 1 else ""
            c_rank = candidate[1] if len(candidate) >= 2 else ""
            c_cards_raw = candidate[2] if len(candidate) >= 3 and isinstance(candidate[2], list) else candidate
            c_cards = sorted([str(c) for c in c_cards_raw])

            if c_type == r_type and c_rank == r_rank and c_cards == r_cards:
                return i

        return -1

    def _quick_guard_validate(
        self, act_index: int, action_list: List, game_state: Dict[str, Any]
    ) -> bool:
        """
        GUA-075: 主路径快速校验 — 不可逾越的硬规则底线。

        比 Guard filter 轻量，只检查 3 条硬规则：
          R10: 领出不炸
          R01: 压单不用炸（有同型单张可压时）
          R05: 队友不炸

        不检查软规则（让回退路径的 validate_decision 处理）。

        Returns:
            True = 通过校验；False = 不通过需回退
        """
        if act_index < 0 or act_index >= len(action_list):
            return False

        from src.v.nn.guards.v7_guards import (
            get_action_type, ACTION_TYPE_PASS,
            ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH,
            ACTION_TYPE_SINGLE,
        )

        chosen = action_list[act_index]
        if not chosen:
            return False

        chosen_type = get_action_type(chosen)
        my_pos = game_state.get("myPos", self.player_id)
        cur_pos = game_state.get("curPos", -1)
        greater_action = game_state.get("greaterAction", []) or []
        teammate_pos = (my_pos + 2) % 4

        # R10: 领出不炸
        if cur_pos == -1 and chosen_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return False

        # R05: 队友不炸（对家在出牌时不用炸弹压队友）
        if cur_pos == teammate_pos and chosen_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            return False

        # R01: 压单不用炸 — 对手出单张，我们有同型单张可压却用炸
        if greater_action and greater_action[0] != "PASS" and chosen_type in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH):
            greater_type = get_action_type(greater_action)
            if greater_type == ACTION_TYPE_SINGLE:
                # 检查 actionList 中是否有同型单张可压
                for act in action_list:
                    if get_action_type(act) == ACTION_TYPE_SINGLE and act != chosen:
                        return False  # 有单张可用却选炸弹 → 不通过

        # R12: 有自然单张时禁止拆普通对子出单（GUA-075 主路径补检）
        if chosen_type == ACTION_TYPE_SINGLE:
            hand_cards = game_state.get("handCards", []) or []
            cur_rank = str(game_state.get("curRank", "2"))
            if self._single_breaks_pair_under_r12(chosen, hand_cards, cur_rank):
                return False

        return True

    def _rule_based_decision(self, game_state: Dict[str, Any], action_list: List) -> int:
        """
        基于规则的回退决策（终极保底，不应频繁触发）。

        Args:
            game_state: 游戏状态
            action_list: 可选动作列表

        Returns:
            动作索引
        """
        try:
            # 简单的规则：优先选择非PASS动作
            for i, action in enumerate(action_list):
                if action and len(action) > 0:
                    if isinstance(action, list) and action[0] != "PASS":
                        return i
                    elif isinstance(action, str) and action.upper() != "PASS":
                        return i

            # 如果都是PASS，返回第一个
            return 0

        except Exception as e:
            self.logger.error(f"规则决策失败: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """获取决策统计信息"""
        return {
            "total_decisions": self.decision_count,
            "model_decisions": self.model_decisions,
            "fallback_decisions": self.fallback_decisions,
            "model_usage_rate": self.model_decisions / max(1, self.decision_count),
            "model_available": self.model is not None,
            # GUA-045 Guard 统计（2026-06-17 接入）
            "guard_filtered_count": self.guard_filtered_count,
            "guard_validated_count": self.guard_validated_count,
            "guard_override_count": self.guard_override_count,
            "guard_filter_rate": self.guard_filtered_count / max(1, self.decision_count),
            "guard_override_rate": self.guard_override_count / max(1, self.guard_validated_count),
            "guard_import_ok": GUARD_IMPORT_OK,
            # GUA-063 前置过滤统计（2026-06-18）
            "group_filtered_count": self.group_filtered_count,
            "group_filter_bypass_count": self.group_filter_bypass_count,
            "group_filter_rate": self.group_filtered_count / max(1, self.decision_count),
            "current_role": self._current_role,
            "has_card_mask": self._card_mask is not None and len(self._card_mask) > 0,
            "regroup_triggered_count": self._regroup_triggered_count,
            # GUA-075 推荐路径统计（2026-06-20）
            "recommend_count": self.recommend_count,
            "recommend_hit_count": self.recommend_hit_count,
            "recommend_valid_count": self.recommend_valid_count,
            "recommend_rate": self.recommend_count / max(1, self.decision_count),
            "recommend_hit_rate": self.recommend_hit_count / max(1, self.recommend_count) if self.recommend_count else 0,
            "recommend_valid_rate": self.recommend_valid_count / max(1, self.decision_count),
            # GUA-075 匹配失败分类（2026-06-20）
            "match_fail_type_mismatch": self._match_fail_type_mismatch,
            "match_fail_rank_mismatch": self._match_fail_rank_mismatch,
            "match_fail_cards_mismatch": self._match_fail_cards_mismatch,
            # GUA-078 残局管线（2026-06-21 接入 decide）
            "endgame_activated_count": self._endgame_activated_count,
            "endgame_hit_count": self._endgame_hit_count,
            "endgame_hit_rate": (
                self._endgame_hit_count / max(1, self._endgame_activated_count)
            ),
        }


# ── 辅助函数 ──────────────────────────────────────────

def is_bomb_straight_flush_for_check(action: List) -> bool:
    """快速检查动作是不是炸弹/同花顺（避免循环导入）。"""
    from src.v.nn.guards.v7_guards import get_action_type, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH
    return get_action_type(action) in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)
