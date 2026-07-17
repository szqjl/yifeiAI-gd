# -*- coding: utf-8 -*-
"""
游戏记录器 - 保存每局游戏并支持回放
格式参考：2021122022131000098 [szqjl]-[新城老王].fp
牌张与基本概念见：docs/archive/rules/牌张与基本概念.md，常量见 game_logic.guandan_constants。
"""

import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, Any, List, Any, Optional

try:
    from game_logic.guandan_constants import CARDS_PER_PLAYER
except ImportError:
    CARDS_PER_PLAYER = 27  # 掼蛋每人27张，规则见 docs/archive/rules/牌张与基本概念.md

# 文件名：YYYYMMDDHHMMSSffffff [player]-[opponent]-[round]-[level].json
RECORD_FILENAME_RE = re.compile(
    r"^(\d+) \[([^\]]+)\]-\[([^\]]+)\]-\[(\d+)\]-\[([^\]]*)\]\.json$"
)


def normalize_cards_to_string_list(cards: List) -> List[str]:
    """
    将服务器下发的卡牌列表统一为字符串列表（入口规范化）。
    支持 "S2" 与 ["S","2"] 两种格式。
    平台王编码 SB(小王)/HR(大王) 直接透传，不再转换。
    """
    if not cards:
        return []
    result = []
    for card in cards:
        if isinstance(card, str) and len(card) >= 2:
            result.append(card)
        elif isinstance(card, list) and len(card) >= 2:
            result.append(f"{str(card[0])}{str(card[1])}")
    return result


def normalize_action_list(action_list: List) -> List:
    """
    将 actionList 中每个动作的第三元（牌列表）规范成字符串列表。
    不修改原列表，返回新列表。
    """
    if not action_list:
        return action_list
    out = []
    for action in action_list:
        if not isinstance(action, list) or len(action) < 3 or not isinstance(action[2], list):
            out.append(action)
            continue
        out.append([action[0], action[1], normalize_cards_to_string_list(action[2])])
    return out


# WF-12 复盘：actionList 较小时写入 my_decisions.context（Layer 2 体积可控）
ACTION_LIST_CONTEXT_SAMPLE_MAX = 8
ACTION_LIST_CONTEXT_ITEM_MAX = 8


def summarize_action_list_for_context(
    action_list: List,
    *,
    max_items: int = ACTION_LIST_CONTEXT_ITEM_MAX,
) -> List[Dict[str, Any]]:
    """将 actionList 压缩为 [{type, rank, cards}, ...] 供牌谱 / 日志诊断。"""
    if not action_list or not isinstance(action_list, list):
        return []
    sample: List[Dict[str, Any]] = []
    for action in action_list[:max_items]:
        if not action or not isinstance(action, list) or len(action) < 2:
            continue
        a_type = action[0] if action[0] is not None else ""
        a_rank = action[1] if len(action) > 1 and action[1] is not None else ""
        cards_raw = action[2] if len(action) > 2 and isinstance(action[2], list) else []
        cards = normalize_cards_to_string_list(cards_raw) if cards_raw else []
        sample.append({"type": str(a_type), "rank": str(a_rank), "cards": cards})
    return sample


# ---------- 队友/对手识别（掼蛋规则：0与2一队，1与3一队） ----------

def get_teammate_pos(my_pos: int) -> int:
    """根据己方座位号返回队友座位号。掼蛋：0-2 一队，1-3 一队。"""
    if my_pos is None or not (0 <= my_pos <= 3):
        return -1
    return (int(my_pos) + 2) % 4


def get_opponent_positions(my_pos: int) -> tuple:
    """根据己方座位号返回两名对手的座位号 (上家方向、下家方向)。"""
    if my_pos is None or not (0 <= my_pos <= 3):
        return (-1, -1)
    return ((int(my_pos) + 1) % 4, (int(my_pos) + 3) % 4)


def is_teammate(my_pos: int, other_pos: int) -> bool:
    """判断 other_pos 是否是 my_pos 的队友。"""
    if my_pos is None or other_pos is None or other_pos == -1 or my_pos == -1:
        return False
    return get_teammate_pos(my_pos) == int(other_pos)


def ensure_my_pos_int(data: dict, fallback_player_id: int) -> int:
    """
    从消息中安全取出己方座位号并转为 int，供各客户端统一使用。
    优先 myPos，其次 playerPosition，否则用 fallback_player_id。
    """
    raw = data.get("myPos", data.get("playerPosition", fallback_player_id))
    if raw is None:
        return int(fallback_player_id)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(fallback_player_id)


_PLATFORM_PAYLOAD_KEYS = frozenset({
    "actionList",
    "stage",
    "handCards",
    "myPos",
    "curPos",
    "curAction",
    "greaterPos",
    "greaterAction",
    "publicInfo",
    "selfRank",
    "oppoRank",
    "curRank",
    "notifyType",
    "result",
    "victoryNum",
})


def unwrap_platform_payload(message: dict) -> dict:
    """
    v1006 平台 WebSocket 消息多为顶层字段（见 guandan_offline lalala/state.py）；
    少数封装为 {"type": "...", "data": {...}}。
    """
    if not isinstance(message, dict):
        return {}
    nested = message.get("data")
    if isinstance(nested, dict) and any(k in nested for k in _PLATFORM_PAYLOAD_KEYS):
        return nested
    return message


def is_ws_debug_enabled() -> bool:
    """是否打印 WebSocket 完整消息（YF_DEBUG_WS=1 开启）。"""
    return os.environ.get("YF_DEBUG_WS", "").strip().lower() in ("1", "true", "yes", "on")


def normalize_act_message_fields(data: dict) -> dict:
    """规范化 act 消息：字符串形式的 curAction/greaterAction 转列表。"""
    for field in ("curAction", "greaterAction"):
        value = data.get(field)
        if isinstance(value, str):
            try:
                data[field] = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                pass
    if "handCards" in data and data["handCards"]:
        data["handCards"] = normalize_cards_to_string_list(data["handCards"])
    if data.get("actionList"):
        data["actionList"] = normalize_action_list(data["actionList"])
    return data


def get_latest_victory_num_path() -> Path:
    """batch_executor 读取的 victoryNum 共享文件路径。"""
    return Path(__file__).parent.parent.parent / "batch_executor" / "latest_victory_num.json"


def notify_end_kind(data: dict) -> str:
    """区分副结束 (episode) 与局级结果 (session/gameResult)。
    V8: 新增 victory 字段检测（OpenGuanDan 新平台）。
    """
    key = data.get("notifyType") or data.get("stage", "")
    if key in ("gameResult", "gameEnd") or "victoryNum" in data or "victory" in data:
        return "session"
    if key in ("episodeOver", "gameOver"):
        return "episode"
    return "unknown"


def decision_context_from_act(
    data: dict,
    player_id: int,
    *,
    version: str = "v7",
    series: str = "V",
) -> Dict[str, Any]:
    """act 阶段 record_decision 的 context（对齐 M3 _decision_context_from_act）。

    GUA-072: 加入 handCards 字段，使 game record 可回放诊断 card_mask 退化问题。
    actionList_size≤8 时写入 actionList_sample（type/rank/cards），供 WF-12 复盘平台候选。
    GUA-078 取证：YF_DEBUG_WS=1 时始终存 greaterAction + 完整 actionList_sample。
    """
    action_list = data.get("actionList") or []
    size = len(action_list) if isinstance(action_list, list) else 0
    # 序列化了 handCards（已由 normalize_act_message_fields 标准化为字符串列表）
    hand_cards = data.get("handCards") or []
    ctx: Dict[str, Any] = {
        "myPos": data.get("myPos", player_id),
        "curPos": data.get("curPos", -1),
        "greaterPos": data.get("greaterPos", -1),
        "actionList_size": size,
        "handCards_size": len(hand_cards),
        "handCards": hand_cards,
        "selfRank": data.get("selfRank"),
        "oppoRank": data.get("oppoRank"),
        "curRank": data.get("curRank"),
        "version": version,
        "series": series,
        "source": "act",
        "stage": data.get("stage", ""),
    }
    # GUA-078: YF_DEBUG_WS=1 时始终保存 greaterAction 和完整 actionList_sample
    _debug_ws = is_ws_debug_enabled()
    if _debug_ws:
        ctx["greaterAction"] = data.get("greaterAction")  # 平台原始 greaterAction
        ctx["actionList_sample"] = summarize_action_list_for_context(action_list)
    elif 0 < size <= ACTION_LIST_CONTEXT_SAMPLE_MAX:
        ctx["actionList_sample"] = summarize_action_list_for_context(action_list)
    return ctx


def extract_notify_game_result(
    data: dict,
    decision_count: int = 0,
    game_count: int = 0,
) -> Dict[str, Any]:
    """从 notify 提取写入 game_records.result 的字段。

    平台约束（见 docs/guandan-brain/掼蛋AI算法对抗平台使用说明.md §消息类型）：
    - tribute/back 的 result 为 [[位,位,牌],...]，不是局结束
    - episodeOver 含 order/curRank/restCards
    """
    stage = data.get("stage", "")
    key = data.get("notifyType") or stage

    if key == "episodeOver" or stage == "episodeOver":
        return {
            k: v
            for k, v in {
                "order": data.get("order"),
                "curRank": data.get("curRank"),
                "restCards": data.get("restCards", []),
                "total_decisions": decision_count,
                "game_count": game_count,
            }.items()
            if v is not None
        }

    if key == "gameOver" or stage == "gameOver":
        return {
            k: v
            for k, v in {
                "curTimes": data.get("curTimes"),
                "settingTimes": data.get("settingTimes"),
                "total_decisions": decision_count,
                "game_count": game_count,
            }.items()
            if v is not None
        }

    result = data.get("result", {}) or {}
    if not isinstance(result, dict):
        result = {}

    if data.get("stage") == "gameResult" or "victoryNum" in data or "victory" in data:
        # V8: OpenGuanDan 用 victory 单值（0=0+2队胜，1=1+3队胜）
        victory_num = data.get("victoryNum") or result.get("victoryNum", [])
        if not victory_num and "victory" in data:
            v = data.get("victory", -1)
            if v == 0:
                victory_num = [1, 0, 1, 0]  # 座位0+2队胜
            elif v == 1:
                victory_num = [0, 1, 0, 1]  # 座位1+3队胜
        if victory_num:
            extra = {"victoryNum": victory_num}
            if "victoryRank" in data:
                extra["victoryRank"] = data["victoryRank"]
            return {
                **extra,
                "draws": data.get("draws", result.get("draws", [])),
                "total_decisions": decision_count,
                "game_count": game_count,
            }
        if not result:
            return {
                "draws": data.get("draws", []),
                "total_decisions": decision_count,
                "game_count": game_count,
            }
    return dict(result)


def save_victory_num_shared(
    victory_num: list,
    player: str,
    logger=None,
    *,
    vn_source: str = "gameResult",
    victory_rank: list = None,
) -> bool:
    """写入 latest_victory_num.json，供 batch_executor 批末对账。"""
    if not victory_num or len(victory_num) < 4:
        return False
    try:
        shared_file = get_latest_victory_num_path()
        shared_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "victoryNum": victory_num,
            "server_vn_raw": victory_num,
            "vn_source": vn_source,
            "timestamp": datetime.now().isoformat(),
            "player": player,
        }
        if victory_rank:
            payload["victoryRank"] = victory_rank
        with open(shared_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        if logger:
            logger.info("✓ victoryNum 已保存到共享文件: %s → %s", shared_file, victory_num)
        return True
    except Exception as e:
        if logger:
            logger.warning("保存 victoryNum 到共享文件失败: %s", e)
        return False


def process_platform_game_end_notify(
    data: dict,
    game_recorder: "GameRecorder",
    logger,
    player_tag: str,
    decision_count: int = 0,
    game_count: int = 0,
) -> None:
    """
    统一处理 episodeOver / gameResult 结束通知（M1/M3/V7 共用逻辑）。
    - episodeOver：落盘当前副记录（可无 victoryNum）
    - gameResult：写 latest_victory_num.json 并回填近期 game_records
    """
    key = data.get("notifyType") or data.get("stage", "")
    kind = notify_end_kind(data)
    result = extract_notify_game_result(data, decision_count, game_count)
    victory_num = result.get("victoryNum")

    if game_recorder.current_game:
        filepath = game_recorder.end_game(result)
        if filepath and logger:
            logger.info("✓ 游戏记录已保存: %s", filepath)
    elif kind == "episode":
        if logger:
            logger.info(
                "游戏结束通知(%s)收到但 current_game 为空，副记录可能已保存；跳过 end_game",
                key,
            )
    elif logger:
        logger.info("局级结束通知(%s)，current_game 为空", key)

    if kind == "session" and victory_num:
        v_rank = result.get("victoryRank") or data.get("victoryRank")
        save_victory_num_shared(victory_num, player_tag, logger, victory_rank=v_rank)
        filled = game_recorder.backfill_victory_num(victory_num)
        if logger and filled:
            logger.info("✓ victoryNum 已回填 %s 条 game_records", filled)
        # 战绩汇总打印
        if logger and len(victory_num) >= 4:
            vn = [int(v) for v in victory_num[:4]]
            v_rank = result.get("victoryRank") or data.get("victoryRank")
            vict = result.get("victory") if result.get("victory") is not None else data.get("victory")
            # 判定胜负：victoryRank 优先（含 "A" 的队胜），否则用 victory
            # GUA-148：双方都到 A（victoryRank=["A","A"]）→ fallback 到服务器 victory 字段
            if v_rank and isinstance(v_rank, list) and len(v_rank) >= 2:
                if v_rank[0] == "A" and v_rank[1] == "A":
                    # 双方都到 A → 以服务器 victory 字段为准
                    if vict is not None:
                        winner = "V8 队(座0+2)" if int(vict) == 0 else "LALALA(座1+3)"
                    else:
                        winner = None
                elif v_rank[0] == "A":
                    winner = "V8 队(座0+2)"
                elif v_rank[1] == "A":
                    winner = "LALALA(座1+3)"
                else:
                    winner = None
            elif vict is not None:
                winner = "V8 队(座0+2)" if int(vict) == 0 else "LALALA(座1+3)"
            else:
                winner = None
            logger.info("=" * 50)
            logger.info("🏆 最终等级: V8=%s LALALA=%s | 各席副胜: 座0=%d 座1=%d 座2=%d 座3=%d",
                        v_rank[0] if v_rank else "?", v_rank[1] if v_rank else "?", *vn)
            if winner:
                logger.info("🥇 局胜者: %s", winner)
            logger.info("=" * 50)


def sync_pass_counters(
    pass_num: int,
    my_pass_num: int,
    cur_action: list,
    cur_pos: int,
    player_id: int,
) -> tuple:
    """
    按 lalala 客户端逻辑更新连续 PASS 计数（GUA-022 context 补全）。
    返回 (pass_num, my_pass_num)。
    """
    if not cur_action:
        return pass_num, my_pass_num
    if cur_action[0] == "PASS":
        pass_num += 1
    else:
        pass_num = 0
    if cur_pos == player_id:
        if cur_action[0] == "PASS":
            my_pass_num += 1
        else:
            my_pass_num = 0
    return pass_num, my_pass_num


def _format_cards(action_cards: Any) -> str:
    """
    格式化牌面显示，支持多种数据格式
    
    Args:
        action_cards: 牌面数据，可能是各种格式
        
    Returns:
        格式化后的牌面字符串
    """
    if not action_cards:
        return ""
    
    try:
        # 如果是列表
        if isinstance(action_cards, list):
            if len(action_cards) == 0:
                return ""
            
            # 如果列表元素是列表（如 [["H", "4"], ["S", "5"]]）
            if isinstance(action_cards[0], list):
                cards = []
                for c in action_cards:
                    if isinstance(c, list) and len(c) >= 2:
                        # 处理 ["H", "4"] 格式
                        suit = str(c[0]) if len(c) > 0 else ""
                        rank = str(c[1]) if len(c) > 1 else ""
                        cards.append(f"{suit}{rank}")
                    elif isinstance(c, list) and len(c) == 1:
                        # 处理只有一个元素的列表
                        cards.append(str(c[0]))
                    elif isinstance(c, str):
                        cards.append(c)
                    else:
                        cards.append(str(c))
                return ' '.join(cards)
            
            # 如果列表元素是字符串（如 ["H4", "S5"]）
            elif isinstance(action_cards[0], str):
                return ' '.join(action_cards)
            
            # 如果列表元素是其他类型（如数字、元组等）
            else:
                return ' '.join([str(c) for c in action_cards])
        
        # 如果是字符串
        elif isinstance(action_cards, str):
            # 如果字符串看起来像是列表的字符串表示（如 "['H', '4']" 或 "['H', '4', 'S', '5']"）
            if action_cards.strip().startswith('['):
                # 尝试解析字符串形式的列表
                try:
                    import ast
                    parsed = ast.literal_eval(action_cards)
                    return _format_cards(parsed)  # 递归处理
                except:
                    # 如果解析失败，尝试手动解析简单的格式
                    # 处理类似 "['H', '4', 'S', '5']" 的格式
                    if "'" in action_cards or '"' in action_cards:
                        # 提取所有引号内的内容
                        import re
                        matches = re.findall(r"['\"]([^'\"]+)['\"]", action_cards)
                        if matches:
                            # 假设是成对的 [suit, rank, suit, rank, ...]
                            cards = []
                            for i in range(0, len(matches), 2):
                                if i + 1 < len(matches):
                                    cards.append(f"{matches[i]}{matches[i+1]}")
                            if cards:
                                return ' '.join(cards)
            return action_cards
        
        # 如果是元组
        elif isinstance(action_cards, tuple):
            return ' '.join([str(c) for c in action_cards])
        
        # 其他类型，直接转换
        else:
            result = str(action_cards)
            # 如果结果看起来像是列表的字符串表示，尝试解析
            if result.strip().startswith('[') and "'" in result:
                try:
                    import ast
                    parsed = ast.literal_eval(result)
                    return _format_cards(parsed)  # 递归处理
                except:
                    pass
            return result
    
    except Exception as e:
        # 如果格式化失败，返回原始数据的字符串表示（截断过长的内容）
        result = str(action_cards)
        if len(result) > 100:
            result = result[:100] + "..."
        return f"[格式化错误: {e}] {result}"


class GameRecorder:
    """游戏记录器 - 记录完整的游戏过程"""
    
    def __init__(self, player_id: int, player_name: str = ""):
        """
        初始化游戏记录器
        
        Args:
            player_id: 玩家位置 (0-3)
            player_name: 玩家名称
        """
        self.player_id = player_id
        self.player_name = player_name or f"player_{player_id}"
        
        # 创建记录目录（V8专用，与V7的game_records_v7分开）
        self.record_dir = Path(__file__).parent.parent.parent / "game_records_v8"
        self.record_dir.mkdir(exist_ok=True)
        
        # 当前游戏记录
        self.current_game: Optional[Dict[str, Any]] = None
        self.game_start_time: Optional[datetime] = None
        
        # 游戏计数，用于生成唯一文件名
        self.game_counter = 0
        
        # 确保记录目录存在
        if not self.record_dir.exists():
            self.record_dir.mkdir(parents=True, exist_ok=True)
        
    def backfill_victory_num(
        self,
        victory_num: list,
        pending_files: Optional[list] = None,
        *,
        expected_batch_games: Optional[int] = None,
        max_files: int = 50,
    ) -> int:
        """
        回填记录文件的 victoryNum（兼容 m-dev pending_files 与 v7 近期文件扫描两种模式）。
        - 传 pending_files：按 m-dev 逻辑校验 + 回填指定文件列表
        - 不传 pending_files：扫描近期本玩家 game_records 并回填（v7 模式）

        Args:
            victory_num: [pos0_wins, pos1_wins, pos2_wins, pos3_wins]
            pending_files: 待回填的文件路径列表（可选，为 None 则自动扫描）
            expected_batch_games: 本批 batch_games
            max_files: v7 模式下最多扫描的文件数
        Returns:
            成功回填的文件数
        """
        import logging
        import tempfile
        from communication.game_result_utils import validate_batch_victory_num

        logger = logging.getLogger(f"GameRecorder.{self.player_name}")

        # ── m-dev 模式：传了 pending_files ──
        if pending_files is not None:
            if not pending_files:
                return 0
            ok, reason = validate_batch_victory_num(victory_num, expected_batch_games)
            if not ok:
                logger.warning(
                    "跳过 victoryNum 回填: %s (vn=%s, batch_games=%s)",
                    reason,
                    victory_num,
                    expected_batch_games,
                )
                pending_files.clear()
                return 0
            flushed = 0
            for path in list(pending_files):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["result"] = data.get("result", {}) or {}
                    data["result"]["victoryNum"] = victory_num
                    fd, tmp = tempfile.mkstemp(dir=str(self.record_dir), suffix=".tmp")
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, path)
                    flushed += 1
                except Exception as e:
                    logger.warning("回填 pending 记录失败: {}, error={}".format(path, e))
            pending_files.clear()
            if flushed:
                logger.info("已批量回填 pending 记录 victoryNum: {} 个".format(flushed))
            return flushed

        # ── v7 模式：扫描近期本玩家 game_records ──
        if not victory_num or len(victory_num) < 4:
            return 0
        pattern = f"*{self.player_name}*.json"
        files = sorted(
            self.record_dir.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        filled = 0
        for filepath in files[:max_files]:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    record = json.load(f)
                existing = record.get("result")
                if not isinstance(existing, dict):
                    existing = {}
                if existing.get("victoryNum"):
                    continue
                existing["victoryNum"] = victory_num
                record["result"] = existing
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(record, f, ensure_ascii=False, indent=2)
                filled += 1
            except Exception:
                continue
        return filled

    def record_game_start(self, message: dict):
        """
        记录游戏开始（V7协议兼容方法）
        
        Args:
            message: 游戏开始消息，包含playerPosition、handCards等信息
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        try:
            # 从V7协议的gameStart消息中提取信息
            player_pos = message.get("playerPosition", self.player_id)
            hand_cards = message.get("handCards", [])
            
            # 提取游戏信息
            game_info = {
                "curRank": message.get("curRank", "2"),
                "selfRank": message.get("selfRank", "2"),
                "oppoRank": message.get("oppoRank", "2"),
            }
            
            # 提取所有玩家手牌（如果消息中包含）
            all_players_hands = {}
            if "allPlayersHands" in message:
                all_players_hands = message["allPlayersHands"]
            elif "all_players_hands" in message:
                all_players_hands = message["all_players_hands"]
            
            # 调用start_game方法
            self.start_game(
                hand_cards=hand_cards,
                my_pos=player_pos,
                game_info=game_info,
                all_players_hands=all_players_hands
            )
            
            logger.info(f"✓ 游戏记录已初始化: 位置={player_pos}, 手牌数={len(hand_cards)}")
            
        except Exception as e:
            logger.error(f"✗ 记录游戏开始失败: {e}", exc_info=True)
    
    def start_game(self, hand_cards: List, my_pos: int, game_info: Dict = None, all_players_hands: Dict[int, List] = None):
        """
        开始记录一局游戏
        
        Args:
            hand_cards: 初始手牌（自己的）
            my_pos: 玩家位置
            game_info: 游戏信息（等级、对手等）
            all_players_hands: 所有玩家的手牌 {pos: hand_cards}
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        # ⚠️ 重要：如果已经有游戏记录在进行，先保存它（防止多局游戏时丢失记录）
        # 修复：如果当前游戏还没有result，延迟保存，等待gameResult通知
        if self.current_game:
            # 检查是否已经有result（说明已经收到gameResult通知）
            if self.current_game.get("result") and isinstance(self.current_game.get("result"), dict):
                if "victoryNum" in self.current_game.get("result", {}):
                    # 已经有完整的result，可以保存
                    logger.info(f"✓ 新游戏开始，当前游戏已有完整result，先保存当前游戏记录")
                    self.end_game(self.current_game.get("result"))
                else:
                    # result存在但没有victoryNum，可能是临时result，等待gameResult
                    logger.warning(f"⚠ 新游戏开始，但当前游戏记录result不完整，延迟保存等待gameResult")
                    # 不保存，等待gameResult通知
            else:
                # 没有result，等待gameResult通知
                logger.warning(f"⚠ 新游戏开始，但当前游戏记录未结束（无result），延迟保存等待gameResult")
                # 不保存，等待gameResult通知
        
        self.game_start_time = datetime.now()
        
        # 递增游戏计数器
        self.game_counter += 1
        
        # 生成游戏ID（时间戳格式：YYYYMMDDHHMMSSffffff）
        game_id = self.game_start_time.strftime('%Y%m%d%H%M%S%f')
        
        # ⚠️ 入口规范化：统一将手牌转为字符串列表（兼容服务器发 ["C","8"] 格式）
        hand_cards = normalize_cards_to_string_list(hand_cards) if hand_cards else []
        # 构建所有玩家的手牌信息，统一使用字符串键
        all_hands = {}
        if all_players_hands:
            for pos, cards in all_players_hands.items():
                pos_str = str(pos)
                all_hands[pos_str] = normalize_cards_to_string_list(cards) if isinstance(cards, list) else []
        my_pos_str = str(my_pos)
        if my_pos_str not in all_hands:
            all_hands[my_pos_str] = hand_cards.copy()
        
        self.current_game = {
            "game_id": game_id,
            "start_time": self.game_start_time.isoformat(),
            "player_id": my_pos,
            "player_name": self.player_name,
            "initial_hand": hand_cards,  # 保留原有字段以兼容
            "all_players_hands": all_hands,  # 新增：所有玩家的手牌
            "game_info": game_info or {},
            "actions": [],  # 所有玩家的出牌动作
            "my_decisions": [],  # 我方的决策记录
            "result": None,
            "game_round": self.game_counter  # 新增：游戏轮次计数
        }
        
        logger.info(f"✓ 开始记录游戏 #{self.game_counter}: game_id={game_id}, my_pos={my_pos}, hand_cards={len(hand_cards)}, all_players_hands={len(all_hands)}个玩家")
        
    def record_action(self, cur_pos: int, cur_action: List, 
                     greater_pos: int = -1, greater_action: List = None,
                     context: Dict = None):
        """
        记录一个出牌动作
        
        Args:
            cur_pos: 出牌玩家位置
            cur_action: 当前动作
            greater_pos: 最大动作玩家位置
            greater_action: 最大动作
            context: 上下文信息（剩余牌数、等级等）
        """
        if not self.current_game:
            return
        
        # 注意：rest_cards包含的是剩余牌数，不是手牌列表，不要用它更新all_players_hands
        # 只保留原始的all_players_hands，确保它只包含手牌列表，不包含剩余牌数
        pass
        
        # ⚠️ 重要：规范化cur_action格式，确保卡牌信息正确
        normalized_action = self._normalize_action(cur_action)
        if normalized_action != cur_action:
            logger = logging.getLogger(f"GameRecorder.{self.player_name}")
            logger.debug(f"规范化动作: {cur_action} -> {normalized_action}")
            cur_action = normalized_action
        
        # 验证卡牌合法性（检测服务器发牌错误）
        self._validate_action_cards(cur_pos, cur_action)
        
        action_record = {
            "timestamp": datetime.now().isoformat(),
            "cur_pos": cur_pos,
            "cur_action": cur_action,
            "greater_pos": greater_pos,
            "greater_action": greater_action or [],
            "context": context or {}
        }
        
        self.current_game["actions"].append(action_record)

    def record_play_notify(self, data: dict, *, version: str = "v7") -> None:
        """记录平台 act/play notify（任意玩家出牌）。

        契约对齐 **M3**（`m-dev` 的 `yf1_m3._handle_act_notification`），写入 `actions` 供回放。
        """
        if not self.current_game:
            return

        cur_pos = data.get("curPos", -1)
        cur_action = data.get("curAction", [])
        greater_pos = data.get("greaterPos", -1)
        greater_action = data.get("greaterAction", [])

        if cur_pos == -1 or not cur_action:
            return

        if isinstance(cur_action, str):
            try:
                cur_action = ast.literal_eval(cur_action)
            except (ValueError, SyntaxError):
                pass
        if isinstance(greater_action, str):
            try:
                greater_action = ast.literal_eval(greater_action)
            except (ValueError, SyntaxError):
                pass

        context = {
            "publicInfo": data.get("publicInfo", []),
            "selfRank": data.get("selfRank"),
            "oppoRank": data.get("oppoRank"),
            "curRank": data.get("curRank"),
            "restCards": data.get("restCards", []),
            "source": "notify",
            "stage": data.get("stage", "play"),
            "version": version,
        }
        self.record_action(cur_pos, cur_action, greater_pos, greater_action, context)

    @staticmethod
    def _normalize_tribute_back_card(card: Any) -> Optional[str]:
        """贡/还单张 → 'S2' 大写（与 M3 yf1_m3 一致）。"""
        if card is None:
            return None
        normalized = normalize_cards_to_string_list([card])
        if not normalized:
            return None
        raw = normalized[0]
        if isinstance(raw, str) and len(raw) >= 2:
            return raw[0].upper() + raw[1:].upper()
        return raw

    def adjust_initial_hand_for_tribute_back(self, card_raw: Any, operation: str) -> None:
        """
        贡牌/还贡后调整 current_game["initial_hand"]，使记录的是还贡后的手牌。

        - "add": 收到进贡/还牌 → 将牌加入 initial_hand
        - "remove": 送出进贡/还牌 → 从 initial_hand 移除该牌

        GUA-067: gameStart handCards 是贡前手牌，训练侧 initial_hand 需反映贡后真实手牌。
        """
        if not self.current_game:
            return
        card_str = self._normalize_tribute_back_card(card_raw)
        if not card_str:
            return
        initial_hand = self.current_game.get("initial_hand")
        if not isinstance(initial_hand, list):
            return
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        pos_key = str(self.player_id)
        all_hands = self.current_game.get("all_players_hands")
        if not isinstance(all_hands, dict):
            all_hands = {}
            self.current_game["all_players_hands"] = all_hands
        player_hand = all_hands.get(pos_key)
        if not isinstance(player_hand, list):
            player_hand = list(initial_hand)
            all_hands[pos_key] = player_hand

        if operation == "add":
            initial_hand.append(card_str)
            player_hand.append(card_str)
            logger.info("✓ 贡牌调整: %s 加入 initial_hand (共%d张)", card_str, len(initial_hand))
        elif operation == "remove":
            # 找到并移除该牌（只移除第一张匹配的，避免误删同名牌）
            for i, c in enumerate(initial_hand):
                if c == card_str:
                    initial_hand.pop(i)
                    for j, pc in enumerate(player_hand):
                        if pc == card_str:
                            player_hand.pop(j)
                            break
                    logger.info("✓ 贡牌调整: %s 从 initial_hand 移除 (剩余%d张)", card_str, len(initial_hand))
                    return
            logger.warning("⚠ 贡牌调整: %s 不在 initial_hand 中，无法移除 (共%d张)", card_str, len(initial_hand))
        else:
            logger.warning("⚠ 未知贡牌调整操作: %s", operation)

    def _already_recorded_tribute_received(self, card_str: str, tribute_pos: int) -> bool:
        for md in self.current_game.get("my_decisions", []) if self.current_game else []:
            action = md.get("action") or []
            ctx = md.get("context") or {}
            if len(action) >= 3 and str(action[0]).lower() == "tribute":
                existing = action[2]
                if (
                    isinstance(existing, list)
                    and card_str in existing
                    and ctx.get("source") == "notify"
                    and ctx.get("receive_tribute_pos") == self.player_id
                    and ctx.get("tribute_pos") == tribute_pos
                ):
                    return True
        return False

    def _already_recorded_back(self, card_str: str) -> bool:
        for md in self.current_game.get("my_decisions", []) if self.current_game else []:
            action = md.get("action") or []
            if len(action) >= 3 and str(action[0]).lower() == "back":
                existing = action[2]
                if isinstance(existing, list) and card_str in existing:
                    return True
        return False

    def record_tribute_notify(self, data: dict, *, version: str = "v7") -> None:
        """进贡 notify：收贡方写入 my_decisions（对齐 M3 yf1_m3._handle_tribute_notification）。"""
        if not self.current_game:
            return
        for item in data.get("result") or []:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            tribute_pos, receive_pos, card = item[0], item[1], item[2]
            try:
                tribute_pos_i = int(tribute_pos)
                receive_pos_i = int(receive_pos)
            except (TypeError, ValueError):
                continue
            card_str = self._normalize_tribute_back_card(card)
            if receive_pos_i != self.player_id or tribute_pos_i == self.player_id or not card_str:
                continue
            if self._already_recorded_tribute_received(card_str, tribute_pos_i):
                continue
            # GUA-067: 收到进贡 → 加入 initial_hand
            self.adjust_initial_hand_for_tribute_back(card_str, "add")
            self.record_decision(
                0,
                ["tribute", "tribute", [card_str]],
                context={
                    "myPos": self.player_id,
                    "curPos": -1,
                    "greaterPos": -1,
                    "actionList_size": 0,
                    "selfRank": data.get("selfRank"),
                    "oppoRank": data.get("oppoRank"),
                    "curRank": data.get("curRank"),
                    "version": version,
                    "source": "notify",
                    "stage": "tribute",
                    "tribute_pos": tribute_pos_i,
                    "receive_tribute_pos": receive_pos_i,
                },
            )

    def record_back_notify(self, data: dict, *, version: str = "v7") -> None:
        """还贡 notify：对手还给我的牌写入 my_decisions（对齐 M3 yf1_m3._handle_back_notification）。"""
        if not self.current_game:
            return
        for item in data.get("result") or []:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                continue
            back_pos, receive_pos, card = item[0], item[1], item[2]
            try:
                receive_pos_i = int(receive_pos)
            except (TypeError, ValueError):
                continue
            card_str = self._normalize_tribute_back_card(card)
            if receive_pos_i != self.player_id or not card_str:
                continue
            if self._already_recorded_back(card_str):
                continue
            # GUA-067: 收到还牌 → 加入 initial_hand
            self.adjust_initial_hand_for_tribute_back(card_str, "add")
            self.record_decision(
                0,
                ["back", "back", [card_str]],
                context={
                    "myPos": self.player_id,
                    "curPos": -1,
                    "greaterPos": -1,
                    "actionList_size": 0,
                    "selfRank": data.get("selfRank"),
                    "oppoRank": data.get("oppoRank"),
                    "curRank": data.get("curRank"),
                    "version": version,
                    "source": "notify",
                    "stage": "back",
                    "back_pos": back_pos,
                    "receive_back_pos": receive_pos_i,
                },
            )
    
    def _normalize_action(self, cur_action: List) -> List:
        """
        规范化动作格式，确保卡牌信息正确
        
        Args:
            cur_action: 原始动作
            
        Returns:
            规范化后的动作
        """
        if not isinstance(cur_action, list):
            return cur_action
        
        # 如果是PASS，直接返回
        if len(cur_action) > 0 and cur_action[0] == "PASS":
            return cur_action
        
        # 标准格式：[action_type, rank, cards]
        if len(cur_action) >= 3 and isinstance(cur_action[2], list):
            # 规范化卡牌列表
            normalized_cards = []
            for card in cur_action[2]:
                if isinstance(card, str) and len(card) >= 2:
                    # 确保卡牌格式正确（如"C8"而不是其他格式）
                    normalized_cards.append(card)
                elif isinstance(card, list) and len(card) >= 2:
                    # 处理["C", "8"]格式，转换为"C8"
                    suit = str(card[0])
                    rank = str(card[1])
                    normalized_cards.append(f"{suit}{rank}")
                else:
                    # 无效卡牌，记录警告但保留
                    import logging
                    logger = logging.getLogger(f"GameRecorder.{self.player_name}")
                    logger.warning(f"⚠ 发现无效卡牌格式: {card}，已忽略")
            
            # 返回规范化后的动作
            return [cur_action[0], cur_action[1], normalized_cards]
        
        return cur_action
    
    def _validate_action_cards(self, cur_pos: int, cur_action: List):
        """
        验证动作中的卡牌是否合法（检测服务器发牌错误）
        
        Args:
            cur_pos: 出牌玩家位置
            cur_action: 当前动作
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        try:
            # ⚠️ 重要：PASS不是卡牌，只是动作，不需要验证
            if isinstance(cur_action, list) and len(cur_action) > 0:
                if cur_action[0] == "PASS":
                    return  # PASS动作不需要验证卡牌
            elif isinstance(cur_action, str) and cur_action.upper() == "PASS":
                return  # PASS字符串不需要验证卡牌
            
            # 提取动作中的卡牌
            action_cards = []
            if isinstance(cur_action, list):
                if len(cur_action) >= 3 and isinstance(cur_action[2], list):
                    action_cards = cur_action[2]
                elif all(isinstance(card, str) for card in cur_action):
                    # 检查是否是PASS格式（如["PASS", "PASS", "PASS"]）
                    if len(cur_action) >= 1 and cur_action[0] == "PASS":
                        return  # PASS格式不需要验证
                    action_cards = cur_action
            
            if not action_cards:
                return
            
            # 检查初始手牌（如果可用）
            all_hands = self.current_game.get("all_players_hands", {})
            # ⚠️ 重要：统一使用字符串键
            cur_pos_str = str(cur_pos)
            initial_hand = all_hands.get(cur_pos_str, [])
            
            if not initial_hand:
                # 如果没有初始手牌信息，无法验证
                return
            
            # ⚠️ 重要：过滤掉PASS字符串（PASS不是卡牌，只是动作）
            valid_action_cards = [card for card in action_cards 
                                 if card != "PASS" and card.upper() != "PASS" 
                                 and isinstance(card, str) and len(card) >= 2]
            
            if not valid_action_cards:
                # 如果过滤后没有有效卡牌，可能是PASS动作，不需要验证
                return
            
            # 统计卡牌出现次数
            from collections import Counter
            action_card_counts = Counter(valid_action_cards)
            initial_card_counts = Counter(initial_hand)
            
            # 检查是否有卡牌在动作中出现次数超过初始手牌
            for card, count in action_card_counts.items():
                initial_count = initial_card_counts.get(card, 0)
                if count > initial_count:
                    logger.warning(
                        f"⚠ 卡牌验证失败：位置{cur_pos}的动作中，卡牌{card}出现{count}次，"
                        f"但初始手牌中只有{initial_count}次！这可能是服务器发牌错误。"
                    )
                    print(
                        f"[GameRecorder] ⚠ 警告：位置{cur_pos}的动作中，卡牌{card}出现{count}次，"
                        f"但初始手牌中只有{initial_count}次！"
                    )
            
            # 检查特殊卡牌（大王、小王）的数量（平台原生 SB=小王, HR=大王）
            joker_cards = [card for card in action_cards if card in ("SB", "HR")]
            if len(joker_cards) > 2:
                logger.warning(
                    f"⚠ 检测到异常：位置{cur_pos}的动作中包含{len(joker_cards)}张王牌（SB/HR），"
                    f"这超过了正常数量（最多2张）！"
                )
                print(
                    f"[GameRecorder] ⚠ 警告：位置{cur_pos}的动作中包含{len(joker_cards)}张王牌，"
                    f"这可能是服务器发牌错误！"
                )
                
        except Exception as e:
            logger.debug(f"卡牌验证时出错（非关键）：{e}")
    
    def record_my_action(self, message: dict, selected_action: Any, decision_time: float = None):
        """
        记录我方的动作（V7协议兼容方法）
        
        Args:
            message: 游戏状态消息，包含当前状态信息
            selected_action: 选择的动作（可能是字符串如"PASS"或列表）
            decision_time: 决策耗时（秒）
        """
        if not self.current_game:
            import logging
            logger = logging.getLogger(f"GameRecorder.{self.player_name}")
            logger.warning("⚠ record_my_action() called but current_game is None")
            return
        
        try:
            # 提取当前状态信息
            cur_pos = message.get("curPlayer", self.player_id)
            hand_cards = message.get("handCards", [])
            valid_actions = message.get("actions", [])
            
            # 构建决策记录
            decision_record = {
                "timestamp": datetime.now().isoformat(),
                "cur_pos": cur_pos,
                "hand_cards_count": len(hand_cards),
                "selected_action": selected_action,
                "decision_time": decision_time,
                "valid_actions_count": len(valid_actions) if valid_actions else 0,
                "context": {
                    "curRank": message.get("curRank", "2"),
                    "selfRank": message.get("selfRank", "2"),
                    "oppoRank": message.get("oppoRank", "2"),
                }
            }
            
            self.current_game["my_decisions"].append(decision_record)
            
            # 同时记录为动作（如果动作不是PASS）
            if selected_action and selected_action != "PASS":
                # 尝试将动作转换为列表格式
                if isinstance(selected_action, str):
                    # 如果是字符串，可能需要解析（这里简化处理）
                    cur_action = [selected_action]
                elif isinstance(selected_action, list):
                    cur_action = selected_action
                else:
                    cur_action = [str(selected_action)]
                
                # 记录动作
                self.record_action(
                    cur_pos=cur_pos,
                    cur_action=cur_action,
                    greater_pos=-1,
                    greater_action=None,
                    context=decision_record["context"]
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(f"GameRecorder.{self.player_name}")
            logger.error(f"✗ 记录我方动作失败: {e}", exc_info=True)
    
    def record_decision(self, action_index: int, action: List, 
                       score: float = None, layer: str = None,
                       candidates: List = None, context: Dict = None,
                       *, candidates_count: int = None):
        """
        记录我方的决策
        
        Args:
            action_index: 选择的动作索引
            action: 选择的动作
            score: 动作评分
            layer: 使用的决策层
            candidates: 候选动作列表（可能很大，优先用 candidates_count）
            context: 决策上下文
            candidates_count: GUA-075 记录增强：候选动作数量（优先于 candidates 推导）
        """
        if not self.current_game:
            return

        _cnt = candidates_count
        if _cnt is None:
            _cnt = len(candidates) if candidates else 0
        
        decision_record = {
            "timestamp": datetime.now().isoformat(),
            "action_index": action_index,
            "action": action,
            "score": score,
            "layer": layer,
            "candidates_count": _cnt,
            "context": context or {}
        }
        
        self.current_game["my_decisions"].append(decision_record)
    
    def end_game(self, result: Dict):
        """
        结束游戏并保存记录
        
        Args:
            result: 游戏结果（victoryNum, draws等）
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        if not self.current_game:
            logger.warning(f"⚠ end_game() called but current_game is None! Player: {self.player_name}, Result: {result}")
            logger.warning("可能的原因：start_game()没有被调用，或者current_game被意外重置")
            return None
        
        try:
            end_time = datetime.now()
            self.current_game["end_time"] = end_time.isoformat()
            self.current_game["duration"] = (end_time - self.game_start_time).total_seconds()
            self.current_game["result"] = result
            
            # 生成文件名
            # 格式：YYYYMMDDHHMMSSffffff [player_name]-[opponent_name].json
            filename = self._generate_filename(result)
            filepath = self.record_dir / filename
            
            # 确保目录存在
            self.record_dir.mkdir(exist_ok=True)
            
            # 保存为JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.current_game, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ 游戏记录已保存: {filepath}")
            print(f"游戏记录已保存: {filepath}")
            
            # 重置（只有在result包含victoryNum时才重置，否则保留current_game等待gameResult）
            # 修复：如果result不包含victoryNum，不重置current_game，等待gameResult通知
            if result and isinstance(result, dict) and "victoryNum" in result:
                # 有完整的victoryNum，可以重置
                self.current_game = None
                self.game_start_time = None
            elif result and isinstance(result, dict) and result.get("reason") == "new_game_started_before_end":
                # 临时保存的情况，不重置，等待gameResult
                logger.info("保留current_game，等待gameResult通知以更新result")
            else:
                # 其他情况，正常重置
                self.current_game = None
                self.game_start_time = None
            
            return filepath
            
        except Exception as e:
            logger.error(f"✗ 保存游戏记录失败: {e}", exc_info=True)
            print(f"✗ 保存游戏记录失败: {e}")
            return None
            return None
    
    def _generate_filename(self, result: Dict) -> str:
        """
        生成文件名
        格式：YYYYMMDDHHMMSSffffff [player_name]-[opponent_name]-[game_round]-[start_level].json
        参考格式：2021122022131000098 [szqjl]-[新城老王]-[1]-[2].json
        """
        game_id = self.current_game["game_id"]
        game_round = self.current_game["game_round"]
        
        # 从结果中推断对手信息
        victory_num = result.get("victoryNum", [0, 0, 0, 0])
        # 某些 gameOver/中间通知里 victoryNum 可能为空或长度不足，避免索引越界
        if not isinstance(victory_num, list):
            victory_num = [0, 0, 0, 0]
        if len(victory_num) < 4:
            victory_num = (victory_num + [0, 0, 0, 0])[:4]
        
        # 判断对手位置（队友是(player_id+2)%4）
        teammate_pos = (int(self.player_id) + 2) % 4
        opponent_positions = [i for i in range(4) if i != int(self.player_id) and i != teammate_pos]
        
        # 根据胜利次数判断对手名称
        if len(opponent_positions) >= 2:
            oppo1_wins = victory_num[opponent_positions[0]]
            oppo2_wins = victory_num[opponent_positions[1]]
            if oppo1_wins > oppo2_wins:
                opponent_name = f"opponent_{opponent_positions[0]}"
            elif oppo2_wins > oppo1_wins:
                opponent_name = f"opponent_{opponent_positions[1]}"
            else:
                opponent_name = f"opponent_{opponent_positions[0]}_{opponent_positions[1]}"
        else:
            opponent_name = "opponent"
        
        # 获取当前游戏的等级信息（从game_info或result中获取）
        game_info = self.current_game.get("game_info", {})
        current_level = game_info.get("curRank", "unknown")
        
        # 从actions中获取游戏的起始等级（如果game_info中没有）
        if current_level == "unknown" and self.current_game.get("actions"):
            for action in self.current_game["actions"]:
                context = action.get("context", {})
                if "curRank" in context:
                    current_level = context["curRank"]
                    break
        
        # 生成唯一的文件名，包含游戏轮次和起始等级信息，避免覆盖
        # 格式：YYYYMMDDHHMMSSffffff [player_name]-[opponent_name]-[game_round]-[start_level].json
        filename = f"{game_id} [{self.player_name}]-[{opponent_name}]-[{game_round}]-[{current_level}].json"
        return filename
    
    @staticmethod
    def load_game(filepath: Union[str, Path]) -> Dict[str, Any]:
        """
        加载游戏记录文件，并自动合并同一局游戏的其他客户端记录
        支持 JSON 和 Pickle (.data) 格式
        
        Args:
            filepath: 游戏记录文件路径
            
        Returns:
            游戏数据字典（已合并所有玩家的手牌）
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"游戏记录文件不存在: {filepath}")
        
        # 根据文件扩展名选择加载方式
        if filepath.suffix.lower() == '.data':
            # Pickle 格式
            game_data = GameRecorder._load_pickle_game(filepath)
        else:
            # JSON 格式（默认）
            with open(filepath, 'r', encoding='utf-8') as f:
                game_data = json.load(f)
        
        # 尝试合并同一局游戏的其他客户端记录
        game_data = GameRecorder._merge_same_game_records(game_data, filepath)
        
        return game_data
    
    @staticmethod
    def _load_pickle_game(filepath: Path) -> Dict[str, Any]:
        """
        加载 Pickle 格式的游戏记录文件（.data 格式）
        将 Pickle 数据转换为与 JSON 格式兼容的字典结构
        
        Args:
            filepath: .data 文件路径
            
        Returns:
            转换后的游戏数据字典
        """
        import pickle
        from datetime import datetime
        
        game_data = {
            "game_id": filepath.stem,  # 使用文件名作为游戏ID
            "start_time": datetime.now().isoformat(),  # 如果没有时间信息，使用当前时间
            "player_id": 0,
            "player_name": "unknown",
            "initial_hand": [],
            "all_players_hands": {},
            "game_info": {},
            "actions": [],
            "my_decisions": [],
            "result": None,
            "game_round": 0
        }
        
        actions = []
        all_pickle_data = []
        
        try:
            # 读取 Pickle 文件中的所有数据（可能包含多个数据块）
            with open(filepath, 'rb') as f:
                while True:
                    try:
                        data = pickle.load(f)
                        all_pickle_data.append(data)
                    except EOFError:
                        break
                    except Exception as e:
                        # 如果某个数据块解析失败，记录但继续处理
                        continue
            
            # 如果只有一个数据块，可能是完整的游戏数据
            if len(all_pickle_data) == 1:
                data = all_pickle_data[0]
                # 尝试直接解析为游戏数据字典
                if isinstance(data, dict):
                    # 如果数据已经是字典格式，尝试直接使用
                    if "actions" in data or "cur_action" in data:
                        game_data.update(data)
                        if "actions" in data:
                            actions = data["actions"]
                    else:
                        # 可能是单个动作
                        action = GameRecorder._convert_pickle_data_to_action(data)
                        if action:
                            actions.append(action)
                else:
                    # 尝试转换为动作
                    action = GameRecorder._convert_pickle_data_to_action(data)
                    if action:
                        actions.append(action)
            else:
                # 多个数据块，每个可能是一个动作
                for data in all_pickle_data:
                    action = GameRecorder._convert_pickle_data_to_action(data)
                    if action:
                        actions.append(action)
            
            # 如果从字典中获取了actions，使用它；否则使用转换后的actions
            if not game_data.get("actions") and actions:
                game_data["actions"] = actions
            
            # 确保actions是列表
            if not isinstance(game_data.get("actions"), list):
                game_data["actions"] = actions if actions else []
            
            game_data["total_steps"] = len(game_data["actions"])
            
            # 尝试从动作中提取初始手牌信息
            # Pickle 格式可能不包含初始手牌，需要从动作中推断
            if game_data["actions"]:
                GameRecorder._infer_initial_hands_from_pickle(game_data, game_data["actions"])
            
        except Exception as e:
            raise ValueError(f"无法解析 Pickle 文件 {filepath}: {e}")
        
        return game_data
    
    @staticmethod
    def _convert_pickle_data_to_action(data: Any) -> Optional[Dict[str, Any]]:
        """
        将 Pickle 数据转换为标准动作格式
        
        Args:
            data: Pickle 加载的数据
            
        Returns:
            标准化的动作字典，如果无法转换则返回 None
        """
        from datetime import datetime
        
        # Pickle 数据可能是各种格式，需要灵活处理
        action = {
            "timestamp": datetime.now().isoformat(),
            "cur_pos": -1,
            "cur_action": [],
            "greater_pos": -1,
            "greater_action": [],
            "context": {}
        }
        
        # 尝试从数据中提取信息
        if isinstance(data, dict):
            # 如果数据已经是字典格式，直接使用
            # 检查是否包含标准字段
            if "cur_pos" in data or "cur_action" in data:
                action.update(data)
            elif "action" in data:
                # 可能是简化的格式
                action["cur_action"] = data.get("action", [])
                action["cur_pos"] = data.get("pos", data.get("player_id", -1))
        elif isinstance(data, (list, tuple)):
            # 如果数据是列表或元组，尝试解析为动作
            if len(data) >= 2:
                # 格式可能是 [pos, action] 或 [action_type, rank, cards]
                if isinstance(data[0], int):
                    # [pos, action] 格式
                    action["cur_pos"] = data[0]
                    action["cur_action"] = data[1] if isinstance(data[1], (list, str)) else []
                elif isinstance(data[0], str):
                    # [action_type, rank, cards] 格式
                    action["cur_action"] = list(data)
                    # 尝试从上下文推断位置（如果无法推断，使用-1）
                    action["cur_pos"] = -1
        elif isinstance(data, str):
            # 如果是字符串，尝试解析
            try:
                import ast
                parsed = ast.literal_eval(data)
                if isinstance(parsed, dict):
                    action.update(parsed)
                elif isinstance(parsed, (list, tuple)):
                    # 递归处理
                    return GameRecorder._convert_pickle_data_to_action(parsed)
            except:
                # 如果解析失败，将字符串作为动作内容
                action["cur_action"] = data
        
        # 确保 cur_action 是列表格式
        if isinstance(action["cur_action"], str):
            try:
                import ast
                action["cur_action"] = ast.literal_eval(action["cur_action"])
            except:
                # 如果解析失败，尝试简单的字符串分割
                if action["cur_action"].startswith('[') and action["cur_action"].endswith(']'):
                    # 可能是字符串形式的列表
                    try:
                        action["cur_action"] = eval(action["cur_action"])
                    except:
                        action["cur_action"] = [action["cur_action"]]
                else:
                    action["cur_action"] = [action["cur_action"]]
        
        # 如果无法提取有效信息，返回 None
        if action["cur_pos"] == -1 and not action["cur_action"]:
            return None
        
        return action
    
    @staticmethod
    def _infer_initial_hands_from_pickle(game_data: Dict[str, Any], actions: List[Dict[str, Any]]):
        """
        从 Pickle 格式的动作中推断初始手牌
        由于 Pickle 格式可能不包含初始手牌信息，需要从动作中反向推断
        
        Args:
            game_data: 游戏数据字典（会被修改）
            actions: 动作列表
        """
        # 统计每个玩家打出的牌
        played_cards_by_player = {str(i): [] for i in range(4)}
        
        for action in actions:
            cur_pos = action.get("cur_pos", -1)
            if cur_pos < 0 or cur_pos > 3:
                continue
            
            cur_action = action.get("cur_action", [])
            if not cur_action:
                continue
            
            # 解析动作，提取打出的牌
            if isinstance(cur_action, (list, tuple)) and len(cur_action) >= 3:
                cards = cur_action[2] if isinstance(cur_action[2], list) else []
                if cards:
                    played_cards_by_player[str(cur_pos)].extend(cards)
            elif isinstance(cur_action, str):
                # 尝试从字符串中提取卡牌信息
                try:
                    import ast
                    parsed = ast.literal_eval(cur_action)
                    if isinstance(parsed, (list, tuple)) and len(parsed) >= 3:
                        cards = parsed[2] if isinstance(parsed[2], list) else []
                        if played_cards_by_player[str(cur_pos)]:
                            played_cards_by_player[str(cur_pos)].extend(cards)
                except:
                    pass
        
        # 由于无法准确推断初始手牌（不知道哪些牌没被打出），
        # 这里只设置已打出的牌作为参考
        # 实际使用时，初始手牌可能不完整
        game_data["all_players_hands"] = played_cards_by_player
    
    @staticmethod
    def parse_record_filename(filepath: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """Parse standard game record filename into match keys for same-round merge."""
        name = Path(filepath).name
        m = RECORD_FILENAME_RE.match(name)
        if not m:
            return None
        return {
            "timestamp": int(m.group(1)),
            "player_name": m.group(2),
            "opponent": m.group(3),
            "round": m.group(4),
            "level": m.group(5),
        }

    @staticmethod
    def _normalize_all_hands_keys(all_hands: Dict) -> Dict[str, List]:
        """Normalize all_players_hands keys to str and card lists to string format."""
        normalized: Dict[str, List] = {}
        if not all_hands:
            return normalized
        for pos, cards in all_hands.items():
            pos_str = str(pos)
            if isinstance(cards, list) and cards:
                normalized[pos_str] = normalize_cards_to_string_list(cards)
            elif pos_str not in normalized:
                normalized[pos_str] = []
        return normalized

    @staticmethod
    def _merge_same_game_records(game_data: Dict[str, Any], current_filepath: Path) -> Dict[str, Any]:
        """
        合并同一局游戏的其他客户端记录，获取所有玩家的手牌。

        匹配规则（GUA-025）：文件名中的 opponent + round + level 必须一致；
        不再使用 start_time 5 秒窗口（batch 多局会在 5 秒内产生误合并）。
        同 round 多份记录时，取 game_id 时间戳最接近的队友/对手文件。
        """
        parsed = GameRecorder.parse_record_filename(current_filepath)
        if not parsed:
            return game_data

        all_hands = GameRecorder._normalize_all_hands_keys(game_data.get("all_players_hands", {}))
        my_pos = game_data.get("player_id")
        if my_pos is not None:
            my_pos_str = str(my_pos)
            if my_pos_str not in all_hands or not all_hands[my_pos_str]:
                initial = normalize_cards_to_string_list(game_data.get("initial_hand", []))
                if initial:
                    all_hands[my_pos_str] = initial

        record_dir = current_filepath.parent
        candidates = []
        for record_file in record_dir.glob("*.json"):
            if record_file == current_filepath:
                continue
            other_parsed = GameRecorder.parse_record_filename(record_file)
            if not other_parsed:
                continue
            if (
                other_parsed["opponent"] != parsed["opponent"]
                or other_parsed["round"] != parsed["round"]
                or other_parsed["level"] != parsed["level"]
            ):
                continue
            ts_diff = abs(other_parsed["timestamp"] - parsed["timestamp"])
            candidates.append((ts_diff, record_file))

        candidates.sort(key=lambda item: item[0])

        for _, record_file in candidates:
            try:
                with open(record_file, "r", encoding="utf-8") as f:
                    other_data = json.load(f)
            except Exception:
                continue

            other_hands = GameRecorder._normalize_all_hands_keys(other_data.get("all_players_hands", {}))
            if not other_hands:
                other_pos = other_data.get("player_id")
                if other_pos is not None:
                    initial = normalize_cards_to_string_list(other_data.get("initial_hand", []))
                    if initial:
                        other_hands[str(other_pos)] = initial

            for pos_str, hand_cards in other_hands.items():
                if hand_cards and (pos_str not in all_hands or not all_hands.get(pos_str)):
                    all_hands[pos_str] = hand_cards

        game_data["all_players_hands"] = all_hands
        return game_data
    
    @staticmethod
    def replay_game(game_data: Dict, verbose: bool = True, analyze_rules: bool = True):
        """
        回放游戏并分析规则使用情况
        
        Args:
            game_data: 游戏记录数据
            verbose: 是否详细输出
            analyze_rules: 是否分析规则使用情况
        """
        print("=" * 80)
        print(f"游戏回放: {game_data['game_id']}")
        print(f"玩家: {game_data['player_name']} (位置{game_data['player_id']})")
        print(f"开始时间: {game_data['start_time']}")
        if game_data.get('end_time'):
            print(f"结束时间: {game_data['end_time']}")
            print(f"游戏时长: {game_data.get('duration', 0):.1f}秒")
        print("=" * 80)
        
        # 显示所有玩家的初始手牌
        my_pos = game_data['player_id']
        all_hands = game_data.get('all_players_hands', {})
        
        # 如果没有all_players_hands，使用旧的initial_hand字段
        if not all_hands:
            all_hands = {my_pos: game_data.get('initial_hand', [])}
        
        # 规范化键为整数
        normalized_hands = {}
        for pos, hand_cards in all_hands.items():
            if isinstance(pos, str):
                try:
                    pos = int(pos)
                except:
                    continue
            normalized_hands[pos] = hand_cards
        all_hands = normalized_hands
        
        print(f"\n【所有玩家初始手牌】:")
        print("-" * 80)
        # 显示每个玩家的手牌
        from collections import Counter
        
        # 牌点大小顺序
        rank_order = {'3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 
                     'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12, '2': 13, 
                     'B': 14, 'R': 15}
        
        # 花色顺序（同牌点时按此顺序）
        suit_order = {'C': 1, 'D': 2, 'H': 3, 'S': 4, 'B': 5, 'R': 6}
        
        suits = {'H': '红桃', 'S': '黑桃', 'C': '梅花', 'D': '方块', 'B': '小王', 'R': '大王'}
        
        # 按牌点大小排序，同牌点按花色排序
        def card_sort_key(card):
            if len(card) < 2:
                return (999, 999)
            suit = card[0]
            rank = card[1]
            rank_val = rank_order.get(rank, 999)
            suit_val = suit_order.get(suit, 999)
            return (rank_val, suit_val)
        
        def format_hand(hand_cards):
            """格式化手牌显示"""
            if not hand_cards:
                return "未知"
            
            # 处理不同格式的手牌
            normalized_cards = []
            for c in hand_cards:
                if isinstance(c, str):
                    normalized_cards.append(c)
                elif isinstance(c, list) and len(c) >= 2:
                    normalized_cards.append(f"{c[0]}{c[1]}")
                else:
                    normalized_cards.append(str(c))
            
            card_counts = Counter(normalized_cards)
            hand_display = []
            for card in sorted(card_counts.keys(), key=card_sort_key):
                count = card_counts[card]
                suit = card[0] if len(card) > 0 else ''
                rank = card[1] if len(card) > 1 else ''
                suit_name = suits.get(suit, suit)
                if count > 1:
                    hand_display.append(f"{suit_name}{rank}({count})")
                else:
                    hand_display.append(f"{suit_name}{rank}")
            return ' '.join(hand_display)
        
        teammate_pos = (my_pos + 2) % 4
        for pos in range(4):
            if pos == my_pos:
                label = "我"
            elif pos == teammate_pos:
                label = "队友"
            else:
                label = "对手"
            
            hand_cards = all_hands.get(pos, [])
            total_count = len(hand_cards) if hand_cards else 0
            hand_display = format_hand(hand_cards)
            print(f"  {pos}号位({label}): {total_count}张 - {hand_display}")
        
        # 回放出牌过程（易读格式）
        print(f"\n【出牌过程】({len(game_data['actions'])}步):")
        print("-" * 80)
        
        # my_pos 和 teammate_pos 已在上面定义，这里不需要重复定义
        
        # 初始化玩家剩余牌数和牌型统计（每人 CARDS_PER_PLAYER，规则见 docs/archive/rules/牌张与基本概念.md）
        player_cards = {0: CARDS_PER_PLAYER, 1: CARDS_PER_PLAYER, 2: CARDS_PER_PLAYER, 3: CARDS_PER_PLAYER}
        # 使用所有玩家的手牌信息初始化剩余牌数
        for pos, hand_cards in all_hands.items():
            if hand_cards:
                player_cards[pos] = len(hand_cards)
        
        # 构建所有玩家的初始手牌集合（用于一致性检查）
        all_hands = game_data.get('all_players_hands', {})
        if not all_hands:
            # 兼容旧格式
            my_pos = game_data['player_id']
            all_hands = {my_pos: game_data.get('initial_hand', [])}
        
        # 规范化键为整数
        normalized_hands = {}
        for pos, hand_cards in all_hands.items():
            if isinstance(pos, str):
                try:
                    pos = int(pos)
                except:
                    continue
            normalized_hands[pos] = hand_cards
        
        all_players_hands_sets = {}
        for pos, hand_cards in normalized_hands.items():
            hand_set = set()
            for c in hand_cards:
                if isinstance(c, str):
                    hand_set.add(c)
                elif isinstance(c, list) and len(c) >= 2:
                    hand_set.add(f"{c[0]}{c[1]}")
            all_players_hands_sets[pos] = hand_set
        
        # 保留旧的initial_hand_set以兼容
        my_pos = game_data['player_id']
        initial_hand_set = all_players_hands_sets.get(my_pos, set())
        
        action_type_stats = {}
        consistency_warnings = []  # 记录数据不一致的警告
        
        for i, action in enumerate(game_data['actions'], 1):
            cur_pos = action['cur_pos']
            cur_action = action['cur_action']
            greater_pos = action['greater_pos']
            greater_action = action['greater_action']
            
            # 如果cur_action是字符串，尝试解析为列表
            if isinstance(cur_action, str):
                try:
                    import ast
                    cur_action = ast.literal_eval(cur_action)
                except:
                    pass
            
            if not cur_action or (isinstance(cur_action, list) and len(cur_action) == 0) or (isinstance(cur_action, list) and cur_action[0] == "PASS"):
                continue
            
            # 格式化动作显示
            if isinstance(cur_action, list):
                action_type = cur_action[0] if len(cur_action) > 0 else "PASS"
                action_rank = cur_action[1] if len(cur_action) > 1 else ""
                action_cards = cur_action[2] if len(cur_action) > 2 else []
            else:
                action_type = str(cur_action)
                action_rank = ""
                action_cards = []
            
            # 判断玩家关系
            if cur_pos == my_pos:
                player_label = "我"
            elif cur_pos == teammate_pos:
                player_label = "队友"
            else:
                player_label = "对手"
            
            # 格式化牌面显示
            cards_str = _format_cards(action_cards)
            
            # 如果action_rank有值，也显示出来
            rank_str = f" {action_rank}" if action_rank else ""
            
            # 如果格式化结果为空或不完整，尝试显示更多信息
            if not cards_str or (action_cards and len(str(action_cards)) > 20 and len(cards_str) < 5):
                # 显示原始数据的简化版本
                raw_str = str(action_cards)
                if len(raw_str) > 100:
                    raw_str = raw_str[:100] + "..."
                cards_str = f"[数据: {raw_str}]"
            
            # 计算出的牌数并更新剩余牌数
            if action_cards:
                if isinstance(action_cards, list):
                    card_count = len(action_cards)
                elif isinstance(action_cards, str):
                    try:
                        import ast
                        parsed = ast.literal_eval(action_cards)
                        card_count = len(parsed) if isinstance(parsed, list) else 1
                    except:
                        card_count = 1
                else:
                    card_count = 1
                player_cards[cur_pos] = max(0, player_cards[cur_pos] - card_count)
            
            # 统计牌型
            if action_type != "PASS":
                action_type_stats[action_type] = action_type_stats.get(action_type, 0) + 1
            
            # 检查数据一致性（检查所有有手牌记录的玩家）
            consistency_warning = None
            player_hand_set = all_players_hands_sets.get(cur_pos, set())
            if action_cards and player_hand_set:
                # 解析出牌
                played_cards = []
                if isinstance(action_cards, list) and len(action_cards) > 2:
                    # action_cards 是 cur_action[2]，即出牌列表
                    cards_data = action_cards
                    for c in cards_data:
                        if isinstance(c, str):
                            played_cards.append(c)
                        elif isinstance(c, list) and len(c) >= 2:
                            played_cards.append(f"{c[0]}{c[1]}")
                elif isinstance(cur_action, str):
                    # cur_action 是字符串格式，需要解析
                    try:
                        import ast
                        parsed = ast.literal_eval(cur_action)
                        if isinstance(parsed, list) and len(parsed) > 2:
                            cards_data = parsed[2]
                            if isinstance(cards_data, list):
                                for c in cards_data:
                                    if isinstance(c, str):
                                        played_cards.append(c)
                                    elif isinstance(c, list) and len(c) >= 2:
                                        played_cards.append(f"{c[0]}{c[1]}")
                    except:
                        pass
                
                # 检查是否有牌不在初始手牌中
                missing_cards = [card for card in played_cards if card not in player_hand_set]
                if missing_cards:
                    consistency_warning = f"⚠ 数据不一致：{', '.join(missing_cards)} 不在{cur_pos}号位初始手牌中（可能记录不完整）"
                    consistency_warnings.append((i, consistency_warning))
            
            # 显示剩余牌数
            remaining = player_cards[cur_pos]
            warning_str = f" {consistency_warning}" if consistency_warning else ""
            print(f"  {i:3d}. [{player_label:2s}] {cur_pos}号位: {action_type}{rank_str} {cards_str} (剩余:{remaining}张){warning_str}")
            
            # 如果是我的决策，显示决策信息
            if cur_pos == my_pos and analyze_rules:
                # 查找对应的决策记录
                decision = None
                for dec in game_data.get('my_decisions', []):
                    if dec.get('action') == cur_action:
                        decision = dec
                        break
                
                if decision:
                    layer = decision.get('layer', 'Unknown')
                    score = decision.get('score')
                    if score is not None:
                        print(f"       → 决策: {layer}层, 评分={score:.1f}")
        
        # 显示数据一致性警告
        if consistency_warnings:
            print("\n" + "=" * 80)
            print("【数据一致性警告】")
            print("-" * 80)
            print(f"发现 {len(consistency_warnings)} 处数据不一致：")
            for step, warning in consistency_warnings:
                print(f"  步骤{step}: {warning}")
            print("\n提示：这可能是因为初始手牌记录不完整，或出牌记录格式不一致。")
        
        # 显示牌型统计
        if action_type_stats:
            print("\n" + "=" * 80)
            print("【牌型使用统计】")
            print("-" * 80)
            for action_type, count in sorted(action_type_stats.items(), key=lambda x: x[1], reverse=True):
                print(f"  {action_type}: {count}次")
        
        # 显示最终剩余牌数
        print("\n" + "=" * 80)
        print("【最终剩余牌数】")
        print("-" * 80)
        for pos in range(4):
            if pos == my_pos:
                label = "我"
            elif pos == teammate_pos:
                label = "队友"
            else:
                label = "对手"
            print(f"  {pos}号位({label}): {player_cards[pos]}张")
        
        # 显示游戏结果
        if game_data['result']:
            print("\n" + "=" * 80)
            print("【游戏结果】")
            print("-" * 80)
            result = game_data['result']
            victory_num = result.get('victoryNum', [0, 0, 0, 0])
            print(f"胜利次数: 0号位={victory_num[0]}, 1号位={victory_num[1]}, "
                  f"2号位={victory_num[2]}, 3号位={victory_num[3]}")
            
            if result.get('layer_stats'):
                print(f"\n【决策层使用统计】")
                for layer, stats in result['layer_stats'].items():
                    success = stats.get('success', 0)
                    failure = stats.get('failure', 0)
                    total = success + failure
                    if total > 0:
                        rate = success / total * 100
                        print(f"  {layer}: {success}/{total} ({rate:.1f}%)")
        
        print("=" * 80)

    def record_game_end(self, message: dict):
        """
        记录游戏结束（V7协议兼容方法）
        
        Args:
            message: 游戏结束消息，包含result等信息
        """
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        
        # 提取结果信息
        result = {}
        if isinstance(message, dict):
            # V7协议格式
            game_result = message.get("result", {})
            if game_result:
                result = {
                    "winner": game_result.get("winner", -1),
                    "scores": game_result.get("scores", []),
                    "victoryNum": game_result.get("victoryNum", [])
                }
            else:
                # 可能是V5协议格式
                result = {
                    "victoryNum": message.get("victoryNum", []),
                    "draws": message.get("draws", 0)
                }
        
        # 调用end_game保存记录
        return self.end_game(result)
    
    def save_records(self):
        """保存游戏记录（兼容V7客户端）"""
        if self.current_game:
            # 修复：如果result为空，尝试保留current_game，等待gameResult通知
            # 只有在明确需要保存时才调用end_game
            if self.current_game.get("result") is not None:
                self.end_game(self.current_game.get("result", {}))  # 结束当前游戏并保存
            # 否则不保存，等待gameResult通知
        
        import logging
        logger = logging.getLogger(f"GameRecorder.{self.player_name}")
        logger.info(f"游戏记录已保存到 {self.record_dir}")