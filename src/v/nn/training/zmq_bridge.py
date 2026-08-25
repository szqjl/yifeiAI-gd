# -*- coding: utf-8 -*-
"""GUA-039a ZMQ Actor-Learner 桥（占位；fd_native 本地训练不依赖）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ZmqBridgeConfig:
    learner_endpoint: str = "tcp://127.0.0.1:5555"
    actor_endpoint: str = "tcp://127.0.0.1:5556"
    enabled: bool = False


class ZmqBridge:
    """分布式 Actor-Learner 通信占位；GUA-039b 前默认关闭。"""

    def __init__(self, config: Optional[ZmqBridgeConfig] = None):
        self.config = config or ZmqBridgeConfig()

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def publish_weights(self, payload: Any) -> None:
        if not self.enabled:
            return
        raise NotImplementedError("ZMQ bridge not wired; use local DMCLearner")

    def pull_samples(self, max_items: int = 1024) -> list:
        if not self.enabled:
            return []
        raise NotImplementedError("ZMQ bridge not wired; use local DMCLearner")
