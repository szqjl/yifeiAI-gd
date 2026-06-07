# -*- coding: utf-8 -*-
"""
GUA-038 V7-internal 录牌 — 每步存 full_state，**不依赖 M3 录牌链路**。

录牌格式（每步一条）：
  - full_state: handCards + actionList + publicInfo + curAction + greaterAction + tribute_result
  - action_index: 选中的 actionList 下标
  - meta: 步号、时间戳、player_id

与 GameRecorder 的关系：
  - 可单独使用或作为 GameRecorder 的补充
  - 使用方保证：game_records/*.json 由 GameRecorder 落盘，本 recorder 只追加 full_state
"""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("v7_recorder")


class V7Recorder:
    """V7-internal 录牌器，记录每步 full_state 用于 BC 训练。"""

    def __init__(self, player_id: int, player_name: str = "yf_v7"):
        self.player_id = player_id
        self.player_name = player_name
        self._current_game: Optional[Dict[str, Any]] = None
        self._step: int = 0

    def start_game(self, game_id: str, initial_hand: List[str],
                   game_info: Optional[Dict[str, Any]] = None) -> None:
        """开始一局录牌。应在收到 gameStart notify 时调用。"""
        self._current_game = {
            "game_id": game_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "start_time": datetime.now().isoformat(),
            "initial_hand": list(initial_hand),
            "game_info": copy.deepcopy(game_info or {}),
            "steps": [],
        }
        self._step = 0
        logger.debug("V7Recorder: 开始录牌 game_id=%s", game_id)

    def record_step(
        self,
        hand_cards: List[str],
        action_list: List[Any],
        chosen_index: int,
        chosen_action: Any,
        *,
        cur_action: Optional[Any] = None,
        greater_action: Optional[Any] = None,
        my_pos: int = 0,
        cur_pos: int = -1,
        greater_pos: int = -1,
        cur_rank: str = "2",
        stage: str = "play",
        public_info: Optional[List[str]] = None,
        tribute_result: Optional[Any] = None,
    ) -> None:
        """记录一步决策的 full_state。

        Args:
            hand_cards: 当前手牌（字符串列表）
            action_list: 平台下发的合法动作列表
            chosen_index: 选中的 action_list 下标
            chosen_action: 选中的动作（列表格式 [type, rank, cards]）
            cur_action: 当前动作（若被动则相当于 greaterAction）
            greater_action: 上家/对手的最后动作
            my_pos: 本座位号
            cur_pos: 当前出牌位
            greater_pos: 最后出牌位
            cur_rank: 当前级牌
            stage: 游戏阶段（play/tribute/back）
            public_info: 公开信息（桌面牌等）
            tribute_result: 贡牌结果（若有）
        """
        if self._current_game is None:
            logger.warning("record_step: 尚未 start_game，跳过")
            return

        step = {
            "step": self._step,
            "timestamp": datetime.now().isoformat(),
            "full_state": {
                "handCards": [str(c) for c in hand_cards],
                "actionList": copy.deepcopy(action_list),
                "actionList_size": len(action_list) if isinstance(action_list, list) else 0,
                "publicInfo": [str(p) for p in (public_info or [])],
                "curAction": copy.deepcopy(cur_action) if cur_action is not None else None,
                "greaterAction": copy.deepcopy(greater_action) if greater_action is not None else None,
                "myPos": my_pos,
                "curPos": cur_pos,
                "greaterPos": greater_pos,
                "curRank": cur_rank,
                "stage": stage,
                "tributeResult": copy.deepcopy(tribute_result) if tribute_result is not None else None,
            },
            "action_index": chosen_index,
            "action": copy.deepcopy(chosen_action),
            "meta": {
                "step": self._step,
                "player_id": self.player_id,
                "player_name": self.player_name,
            },
        }
        self._current_game["steps"].append(step)
        self._step += 1

    def end_game(self, result: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """结束当前局录牌，返回完整录牌数据。清空内部状态。

        Args:
            result: 游戏结果字典（含 order, curRank, restCards, victoryNum 等）

        Returns:
            本局完整录牌数据（含 steps 列表），若未 start_game 则返回 None
        """
        if self._current_game is None:
            return None
        game = self._current_game
        game["end_time"] = datetime.now().isoformat()
        game["result"] = copy.deepcopy(result or {})
        game["total_steps"] = self._step
        self._current_game = None
        self._step = 0
        return game

    def save_to_file(self, game_data: Dict[str, Any], record_dir: str = "game_records") -> Optional[Path]:
        """将录牌数据保存到 JSON 文件。

        文件名格式：{game_id} [{player_name}]-[opponent]-[{game_round}]-[{start_level}].json
        与 GameRecorder 兼容。

        Args:
            game_data: end_game 返回的完整录牌数据
            record_dir: 保存目录

        Returns:
            保存的文件路径，失败返回 None
        """
        record_path = Path(record_dir)
        record_path.mkdir(parents=True, exist_ok=True)

        game_id = game_data.get("game_id", "unknown")
        player_name = game_data.get("player_name", self.player_name)
        game_info = game_data.get("game_info", {})
        start_level = game_info.get("curRank", "2")
        game_round = game_info.get("game_round", 1)

        filename = f"{game_id} [{player_name}]-[opponent]-[{game_round}]-[{start_level}].json"
        filepath = record_path / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(game_data, f, ensure_ascii=False, indent=2)
            logger.info("✓ 录牌保存: %s (%d 步)", filepath, game_data.get("total_steps", 0))
            return filepath
        except Exception as e:
            logger.error("✗ 录牌保存失败: %s", e)
            return None

    @property
    def is_recording(self) -> bool:
        return self._current_game is not None

    @property
    def step_count(self) -> int:
        return self._step