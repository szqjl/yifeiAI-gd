# -*- coding: utf-8 -*-
"""
Ultimate Win Rate Decision Engine V7
终极胜率导向决策引擎 V7版本
基于终极胜率导向训练模型的决策引擎
"""

import torch
import torch.nn as nn
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
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

        # 设备（必须在 _load_model 前设置）
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # 模型路径（GUA-061: 分组引擎模式用 bc_model_v3.pth，默认用 v2）
        # __file__ = src/v/nn/ultimate_win_rate_engine_v7.py → 4层 parent 到项目根
        if use_grouping_engine:
            self.model_path = Path(__file__).parent.parent.parent.parent / "models" / "v-nn" / "bc_model_v3.pth"
        else:
            self.model_path = Path(__file__).parent.parent.parent.parent / "models" / "v-nn" / "bc_model_v2.pth"

        # 加载模型
        self.model = None  # 确保 get_statistics 不爆 AttributeError
        self._load_model()

        # 决策统计
        self.decision_count = 0
        self.model_decisions = 0
        self.fallback_decisions = 0
        # GUA-045 Guard 统计（2026-06-17 接入）
        self.guard_filtered_count = 0
        self.guard_validated_count = 0
        self.guard_override_count = 0

        # GUA-052: MemoryTracker 实例（跨决策状态）
        self._tracker = None
        self._tracker_initialized = False

        # ── GUA-063: 组牌→出牌衔接（2026-06-18）────
        # 每次 decide() 前跑一次 enumerate_groupings()，缓存以下产物：
        self._card_mask: Optional[Dict[str, tuple]] = None   # card → (group_id, is_core, group_size)
        self._current_role: str = "主攻"                      # 角色（主攻/助攻/超强主攻/超弱）
        self._best_plan = None                                # 最优方案 GroupingPlan
        self._grouping_features: Optional[np.ndarray] = None  # 24 维组牌特征（进 NN）
        self._last_hand_hash: int = -1                        # 手牌 hash，用于判断是否需要重跑引擎
        # GUA-063 中局重分组触发标记
        self._core_broken_since_regroup: bool = False         # 核心牌型被破后标记
        # GUA-063 过滤统计
        self.group_filtered_count: int = 0
        self.group_filter_bypass_count: int = 0
        # GUA-063 Phase 3: 中局重分组触发追踪
        self._prev_hand_size: int = 27
        self._regroup_triggered_count: int = 0
        # 决议 8: 接风跟线 — 记忆队友末手牌型
        self._teammate_last_trick_type: Optional[str] = None  # "Pair"/"Bomb"/"StraightFlush" 等
        # 决议 10: 投喂策略 — 5 张反馈路径状态
        self._feed_five_card_tried: bool = False               # 是否已试探过 5 张类牌型
        # 决议 6: 组牌类型映射 — group_id → 牌型字符串
        self._group_type_map: Dict[int, str] = {}
        
    def _load_model(self):
        """加载终极胜率导向模型"""
        try:
            if not self.model_path.exists():
                self.logger.warning(f"[警告] 终极胜率导向模型未找到！模型路径: {self.model_path}")
                self.logger.warning("将使用规则引擎作为回退")
                return False
            
            # 加载模型
            checkpoint = torch.load(self.model_path, map_location=self.device)
            
            # 创建模型架构（与训练时一致的UltimateWinRateNet）
            from src.train.ultimate_win_rate_training import UltimateWinRateNet
            self.model = UltimateWinRateNet().to(self.device)
            
            # 加载权重
            if 'model_state_dict' in checkpoint:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model.load_state_dict(checkpoint)
            
            self.model.eval()
            
            self.logger.info(f"✓ 终极胜率导向模型加载成功: {self.model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ 模型加载失败: {e}")
            self.model = None
            return False
    
    def decide(self, game_state: Dict[str, Any]) -> int:
        """
        做出决策

        GUA-063 流程（2026-06-18）：
          actionList → Guard filter → 组牌引擎(一次枚举) → group_filter(角色前置过滤) → NN → validate → 返回

        Args:
            game_state: 游戏状态

        Returns:
            选择的动作索引（原始 actionList 下标）
        """
        self.decision_count += 1

        action_list = game_state.get("actionList", [])
        if not action_list:
            return 0

        # ── GUA-063 Phase 1: 跑一次组牌引擎，缓存 mask+role+features ──
        self._run_grouping_engine(game_state)

        # ── GUA-065: 注入 numofplayers 到 game_state（队友保护需要知道各家剩张）──
        self._inject_numofplayers(game_state)

        # ── 决议 8: 接风跟线 — 记忆队友末手牌型 ──
        self._update_teammate_last_trick(game_state)

        # ── GUA-068: 注入 MemoryTracker 到 game_state（R11 全局抑制牌检查需要）──
        if self._tracker is not None:
            game_state["_memory_tracker"] = self._tracker

        # ── GUA-045 Guard filter ──
        filtered_actions = action_list
        action_map = list(range(len(action_list)))
        if GUARD_IMPORT_OK:
            try:
                filtered_actions, action_map = filter_action_list(game_state)
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
                    # 两级映射：group_actions_idx → filtered_idx → original_idx
                    if action_index < len(group_filter_map):
                        filtered_idx = group_filter_map[action_index]
                    else:
                        filtered_idx = action_index
                    if filtered_idx < len(action_map):
                        original_idx = action_map[filtered_idx]
                    else:
                        original_idx = 0
                    # GUA-063 Phase 3: 中局重分组触发检查
                    chosen = (action_list[original_idx]
                              if original_idx < len(action_list) else None)
                    self._check_midgame_triggers(game_state, chosen)
                    return original_idx

            # 回退到规则引擎
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)

        except Exception as e:
            self.logger.error(f"✗ 决策失败: {e}")
            self.fallback_decisions += 1
            return self._rule_based_decision(game_state, action_list)
    
    def _replay_history_to_tracker(self, game_state: Dict[str, Any]) -> None:
        """从 game_state 回放历史到 MemoryTracker。"""
        if not FEATURE_IMPORT_OK:
            return
        my_pos = game_state.get("myPos", self.player_id)
        hand_cards = game_state.get("handCards", [])
        cur_rank = str(game_state.get("curRank", "2"))

        if not self._tracker_initialized:
            self._tracker = MemoryTracker(my_pos=my_pos, enable_inference=False, max_infer_depth=0,
                                          use_grouping_engine=self.use_grouping_engine)  # GUA-061
            if hand_cards:
                self._tracker.init_from_hand(hand_cards)
            self._tracker.set_level_rank(cur_rank)
            self._tracker_initialized = True

        # 回放 history
        history = game_state.get("history", [])
        for h in history:
            seat = h.get("pos", h.get("seat", -1))
            if seat < 0:
                continue
            action = h.get("action") or h.get("curAction") or []
            if action:
                self._tracker.record_play(seat, action)

        # 回放 recentPlays
        recent = game_state.get("recentPlays", [])
        for rp in recent:
            seat = rp.get("pos", -1)
            if seat < 0:
                continue
            cards = rp.get("cards", [])
            if cards:
                action_type = rp.get("type", "Unknown")
                self._tracker.record_play(seat, [action_type, "", cards])

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

            # 产出 1: card mask（进前置过滤）+ group_type_map
            self._card_mask, self._group_type_map = best_plan.to_card_mask()

            # 产出 2: role（决定过滤行为）
            self._current_role = best_plan.role or "主攻"

            # 产出 3: 24 维组牌特征（进 NN）
            features_24 = _extract_features(all_plans, hand_cards, cur_rank)
            self._grouping_features = np.array(features_24, dtype=np.float32)

            self.logger.debug(
                "组牌引擎: role=%s mask_groups=%d features=%d",
                self._current_role,
                len(set(v[0] for v in self._card_mask.values() if v[0] >= 0)),
                len(features_24),
            )
        except Exception as e:
            self.logger.warning(f"_run_grouping_engine 失败: {e}, 退化")
            self._card_mask = {}
            self._current_role = "助攻"
            self._grouping_features = np.zeros(24, dtype=np.float32)
            self._core_broken_since_regroup = False

    # ── GUA-065: 注入 numofplayers ────────────────────

    def _inject_numofplayers(self, game_state: Dict[str, Any]) -> None:
        """GUA-065：从 MemoryTracker 或 handCards 推算各玩家剩张数，注入 game_state。

        供 guard R07/R08/R09 使用。
        """
        my_pos = game_state.get("myPos", self.player_id)
        hand_cards = game_state.get("handCards", []) or []

        # 从 MemoryTracker 获取（优先）
        if self._tracker_initialized and self._tracker is not None:
            try:
                hc = self._tracker.hand_counts
                numofplayers = [hc.get(i, 27) for i in range(4)]
                # 纠偏：myPos 以 handCards 为准
                numofplayers[my_pos] = len(hand_cards)
                game_state["numofplayers"] = numofplayers
                return
            except Exception:
                pass

        # 回退：仅知自己手牌数，其他估算为 27
        numofplayers = [27, 27, 27, 27]
        numofplayers[my_pos] = len(hand_cards)
        game_state["numofplayers"] = numofplayers

    # ── GUA-063 Phase 2: 角色驱动前置过滤 ────────────────────

    def _group_consistency_filter(
        self,
        action_list: List,
        game_state: Dict[str, Any],
    ) -> Tuple[List, List[int]]:
        """角色驱动前置过滤：主攻时移除拆核心牌型的动作。

        过滤规则（设计文档 §三 第二层）：
          - 主攻/超强主攻：移除部分使用 core 组牌的动作
          - 助攻/超弱：全部放行
          - 安全阀：过滤后候选为空 → 全部放行
          - 硬例外（放行全部）：
            · 对手剩 1-2 张
            · 自己剩 ≤5 张

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

        # ── 过滤逻辑（角色分流） ──
        keep_indices: List[int] = []
        removed_count = 0

        # ── R12: 拆对子出单检查（有现成单张时禁止）──
        cur_rank = str(game_state.get("curRank", "2"))
        hand_cards_for_r12 = game_state.get("handCards", []) or []

        for idx, action in enumerate(action_list):
            # ── R12: 拆对子出单禁制（GUA-070）──
            # 任何角色 + 任何来源（普通对子 / ThreeWithTwo对子），有自然单张就不许拆对子
            action_cards_r12 = action[2] if isinstance(action, list) and len(action) >= 3 else []
            if len(action_cards_r12) == 1:
                card_info = self._card_mask.get(action_cards_r12[0])
                if card_info and card_info[2] == 2:  # 该单张从 gsize=2 的组拆出
                    if self._has_any_natural_single(hand_cards_for_r12, cur_rank):
                        removed_count += 1
                        continue

            broken_type = self._get_broken_core_type(action, self._card_mask, self._group_type_map)

            if broken_type is None:
                # 不拆任何 core → 保留
                keep_indices.append(idx)
            elif broken_type in ("bomb", "straight_flush"):
                # 炸弹/同花顺 → 永不放行（全角色）
                removed_count += 1
                continue
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
                    # pairs/trips/three_with_two 等 → 检查场景一/二/三
                    if (self._scenario_1_feed_single(game_state) or
                            self._scenario_2_feed_pair(game_state) or
                            self._scenario_3_teammate_sprinting(game_state)):
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
            self.logger.debug("安全阀：过滤后候选为空，全部放行")
            return action_list, list(range(len(action_list)))

        if removed_count > 0:
            self.group_filtered_count += 1
            self.logger.debug(
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
    def _get_broken_core_type(action, card_mask: Dict[str, tuple],
                               group_type_map: Dict[int, str]) -> Optional[str]:
        """检查一个动作破坏了哪种类型的 core 组牌。

        规则（设计文档 §八）：
          - 如果动作使用了某个 core 组的全部牌 → 不视为拆，放行
          - 如果动作使用了某个 core 组的部分牌 → 返回该组的类型字符串
          - 如果动作未使用任何 core 组牌 → 返回 None

        Args:
            action: 动作 [type, rank, [cards...]]
            card_mask: card → (group_id, is_core, group_size)
            group_type_map: group_id → type_string

        Returns:
            类型字符串 ("bomb"/"straight_flush"/"straight"/"trips"/"pair"/...) 或 None
        """
        # PASS 不拆任何牌
        if not action or (isinstance(action, list) and len(action) > 0
                          and str(action[0]).upper() == "PASS"):
            return None

        action_cards = action[2] if isinstance(action, list) and len(action) >= 3 else []
        if not action_cards:
            return None

        # 统计每个 core 组被使用的牌数
        from collections import Counter as _Counter
        core_usage: _Counter[int] = _Counter()  # group_id → 使用张数

        for card in action_cards:
            info = card_mask.get(card)
            if info is None:
                continue
            gid, is_core, gsize = info
            if is_core >= 1.0 and gid >= 0:
                core_usage[gid] += 1

        # 检查是否有 core 组被部分使用
        for gid, used_count in core_usage.items():
            for card in action_cards:
                info = card_mask.get(card)
                if info and info[0] == gid:
                    gsize = info[2]
                    if 0 < used_count < gsize:
                        # 返回该组的类型
                        return group_type_map.get(gid, "unknown")
                    break

        return None

    @staticmethod
    def _action_breaks_core(action, card_mask: Dict[str, tuple]) -> bool:
        """检查一个动作是否拆核心牌型。

        规则（设计文档 §三 第二层）：
          - 如果动作使用了某个 core 组的全部牌 → 不视为拆，放行
          - 如果动作使用了某个 core 组的部分牌（0 < count < group_size）→ 拆核心
          - 如果动作未使用任何 core 组牌 → 不视为拆

        Args:
            action: 动作 [type, rank, [cards...]]
            card_mask: card → (group_id, is_core, group_size)

        Returns:
            True 表示该动作拆核心牌型，应被过滤
        """
        # PASS 不拆任何牌
        if not action or (isinstance(action, list) and len(action) > 0
                          and str(action[0]).upper() == "PASS"):
            return False

        action_cards = action[2] if isinstance(action, list) and len(action) >= 3 else []
        if not action_cards:
            return False

        # 统计每个 core 组被使用的牌数
        from collections import Counter as _Counter
        core_usage: _Counter[int] = _Counter()  # group_id → 使用张数

        for card in action_cards:
            info = card_mask.get(card)
            if info is None:
                continue
            gid, is_core, gsize = info
            if is_core >= 1.0 and gid >= 0:
                core_usage[gid] += 1

        # 检查是否有 core 组被部分使用
        for gid, used_count in core_usage.items():
            # 查找该组的 group_size
            # 因为同一组的所有牌共享相同的 group_size，取第一次遇到的
            for card in action_cards:
                info = card_mask.get(card)
                if info and info[0] == gid:
                    gsize = info[2]
                    if 0 < used_count < gsize:
                        return True  # 部分使用 → 拆核心
                    break

        return False

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
                self._action_breaks_core(chosen_action, self._card_mask)):
            self._core_broken_since_regroup = True
            self.logger.debug("核心牌型被破坏: 动作=%s", chosen_action[:2] if isinstance(chosen_action, list) else chosen_action)

        self._prev_hand_size = hand_size

    # ── 决议 8: 接风跟线 — 记忆队友末手牌型 ──────────────────

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
                        not self._action_breaks_core(act, self._card_mask)):
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
                        not self._action_breaks_core(act, self._card_mask)):
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
        """按队友余牌数映射目标投喂牌型。"""
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
            best_action_idx = torch.argmax(action_probs).item()

            # 验证动作索引
            if 0 <= best_action_idx < len(action_list):
                confidence = action_probs[best_action_idx].item()
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
          196+:     MemoryTracker.state_vector — GUA-052 + GUA-054/061
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

    def _rule_based_decision(self, game_state: Dict[str, Any], action_list: List) -> int:
        """
        基于规则的回退决策

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
        }


# ── 辅助函数 ──────────────────────────────────────────

def is_bomb_straight_flush_for_check(action: List) -> bool:
    """快速检查动作是不是炸弹/同花顺（避免循环导入）。"""
    from src.v.nn.guards.v7_guards import get_action_type, ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH
    return get_action_type(action) in (ACTION_TYPE_BOMB, ACTION_TYPE_STRAIGHT_FLUSH)