# -*- coding: utf-8 -*-
"""
OpenGuanDan 新平台协议适配器
封装 CREATE_ROOM / JOIN_ROOM / PLAY / TRIBUTE / PAYTRIBUTE 消息构造逻辑。

V8 对接方案真源：docs/guandan-brain/V8-新平台对接方案.md §3-A1
"""

from typing import Optional


class OpenGuanDanAdapter:
    """OpenGuanDan 新平台协议适配器"""

    def __init__(self, user_id: str, room_id: Optional[int] = None, seat_num: int = 0):
        self.user_id = user_id
        self.room_id = room_id
        self.seat_num = seat_num  # myPos，初次连接时确定
        
        # 还贡回传字段缓存（V8 方案 §2.3）
        self.last_tribute_pos: Optional[int] = None
        self.last_tribute_card: Optional[str] = None

    @classmethod
    def for_role(cls, user_id: str, role: str, seat_num: int = 0,
                 round_count: int = 1, room_id: Optional[int] = None):
        """工厂方法：根据角色创建适配器
        
        Args:
            user_id: 用户标识
            role: "creator"（建房间）或 "joiner"（加入房间）
            seat_num: 座位号
            round_count: 局数（creator 时有效）
            room_id: 房间 ID（joiner 时需提供，creator 时为 None）
        """
        return cls(user_id=user_id, room_id=room_id, seat_num=seat_num)

    # --- 房间管理 ---

    def create_room(self, round_count: int) -> dict:
        """构造 CREATE_ROOM 消息"""
        return {
            "type": "CREATE_ROOM",
            "data": {
                "userId": self.user_id,
                "round": round_count,
                "seatNum": self.seat_num,
            },
        }

    def join_room(self, room_id: int) -> dict:
        """构造 JOIN_ROOM 消息"""
        return {
            "type": "JOIN_ROOM",
            "data": {
                "userId": self.user_id,
                "roomId": room_id,
                "seatNum": self.seat_num,
            },
        }

    # --- 动作发送 ---

    def play_action(self, act_tuple: list) -> dict:
        """构造 PLAY 消息（从 actionList[selectedIndex] 生成）"""
        return {
            "type": "PLAY",
            "data": {
                "roomId": self.room_id,
                "player": self.seat_num,
                "act": act_tuple,
            },
        }

    def tribute_action(self, act_tuple: list) -> dict:
        """构造 TRIBUTE 消息"""
        return {
            "type": "TRIBUTE",
            "data": {
                "roomId": self.room_id,
                "player": self.seat_num,
                "act": act_tuple,
            },
        }

    def pay_tribute_action(
        self, act_tuple: list, tribute_pos: int, tribute_card: str
    ) -> dict:
        """构造 PAYTRIBUTE 消息（还贡需回传 tributePos/tribute）"""
        return {
            "type": "PAYTRIBUTE",
            "data": {
                "roomId": self.room_id,
                "player": self.seat_num,
                "tributePos": tribute_pos,
                "tribute": tribute_card,
                "act": act_tuple,
            },
        }

    # --- 房间管理 ---

    def create_room(self, round_count: int) -> dict:
        """构造 CREATE_ROOM 消息"""
        return {
            "type": "CREATE_ROOM",
            "data": {
                "userId": self.user_id,
                "round": round_count,
                "seatNum": self.seat_num,
            },
        }

    def join_room(self, room_id: int) -> dict:
        """构造 JOIN_ROOM 消息"""
        return {
            "type": "JOIN_ROOM",
            "data": {
                "userId": self.user_id,
                "roomId": room_id,
                "seatNum": self.seat_num,
            },
        }

    # --- 动作发送 ---

    def play_action(self, act_tuple: list) -> dict:
        """构造 PLAY 消息（从 actionList[selectedIndex] 生成）"""
        return {
            "type": "PLAY",
            "data": {
                "roomId": self.room_id,
                "player": self.seat_num,
                "act": act_tuple,
            },
        }

    def tribute_action(self, act_tuple: list) -> dict:
        """构造 TRIBUTE 消息"""
        return {
            "type": "TRIBUTE",
            "data": {
                "roomId": self.room_id,
                "player": self.seat_num,
                "act": act_tuple,
            },
        }

    def pay_tribute_action(
        self, act_tuple: list, tribute_pos: int, tribute_card: str
    ) -> dict:
        """构造 PAYTRIBUTE 消息（还贡需回传 tributePos/tribute）"""
        return {
            "type": "PAYTRIBUTE",
            "data": {
                "roomId": self.room_id,
                "player": self.seat_num,
                "tributePos": tribute_pos,
                "tribute": tribute_card,
                "act": act_tuple,
            },
        }
