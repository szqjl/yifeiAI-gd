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

            # 产出 1: card mask（进前置过滤）
            self._card_mask = best_plan.to_card_mask()

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

        # GUA-065: 队友控牌场景 → 当作助攻处理，不拆对子（队友可能接）
        greater_pos = game_state.get("greaterPos", -1)
        my_pos_for_filter = game_state.get("myPos", self.player_id)
        if greater_pos == (my_pos_for_filter + 2) % 4:
            role = "助攻"

        # 助攻/超弱：全部放行
        if role in ("助攻", "超弱"):
            return action_list, list(range(len(action_list)))

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

        # ── 过滤逻辑 ──
        keep_indices: List[int] = []
        removed_count = 0

        for idx, action in enumerate(action_list):
            if self._action_breaks_core(action, self._card_mask):
                removed_count += 1
                continue
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