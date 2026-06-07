# -*- coding: utf-8 -*-
"""
WebSocket 连接管理器
支持配置化连接、自动重连、心跳机制和超时控制
"""

import asyncio
import websockets
import json
import logging
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import sys

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config_loader import get_config

try:
    from batch_executor.client_ready import (
        mark_client_ready,
        mark_game_ready,
        wait_for_connect_turn,
    )
except ImportError:
    def mark_client_ready(_client_id: str) -> None:
        pass

    def mark_game_ready(_client_id: str) -> None:
        pass

    def wait_for_connect_turn(_client_id: str, *, timeout: float = 120.0, poll_interval: float = 0.5) -> bool:
        return True


class WebSocketManager:
    """
    WebSocket 连接管理器
    
    功能：
    - 从配置文件读取 WebSocket 设置
    - 自动重连机制
    - 心跳保活机制
    - 连接超时控制
    - 消息处理回调
    """
    
    def __init__(self, user_info: str, use_local: bool = True):
        """
        初始化 WebSocket 管理器
        
        Args:
            user_info: 用户信息（用于构建连接URL）
            use_local: 是否使用本地连接（True=本地，False=网络）
        """
        self.user_info = user_info
        self.use_local = use_local
        self.logger = logging.getLogger(f"websocket_manager.{user_info}")
        
        # 加载配置
        self.config = get_config()
        self.ws_config = self.config.get_websocket_config()
        
        # 连接参数
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.reconnect_interval = self.ws_config.get("reconnect_interval", 5)
        self.heartbeat_interval = self.ws_config.get("heartbeat_interval", 30)
        self.timeout = self.ws_config.get("timeout", 10)
        
        # 状态标志
        self.is_connected = False
        self.should_reconnect = True
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # 消息处理回调
        self.message_handler: Optional[Callable] = None
        
        # game_ready 标记（首条游戏消息到达后置位）
        self._game_ready_marked = False
        
        # 获取连接URL
        self.uri = self._get_connection_uri()
        
        self.logger.info(f"WebSocket Manager initialized for {user_info}")
        self.logger.info(f"  - URI: {self.uri}")
        self.logger.info(f"  - Reconnect interval: {self.reconnect_interval}s")
        self.logger.info(f"  - Heartbeat interval: {self.heartbeat_interval}s")
        self.logger.info(f"  - Timeout: {self.timeout}s")
    
    def _get_connection_uri(self) -> str:
        """获取连接URI"""
        if self.use_local:
            url_template = self.ws_config.get("local_url", "ws://127.0.0.1:23456/game/{user_info}")
        else:
            url_template = self.ws_config.get("network_url", "ws://[局域网IP]:23456/game/{user_info}")
        
        return url_template.format(user_info=self.user_info)
    
    async def connect(self, max_retries: int = -1) -> bool:
        """
        连接到服务器
        
        Args:
            max_retries: 最大重试次数，-1表示无限重试
        
        Returns:
            是否成功连接
        """
        retry_count = 0
        
        while self.should_reconnect and (max_retries < 0 or retry_count < max_retries):
            try:
                gate_ok = await asyncio.to_thread(
                    wait_for_connect_turn,
                    self.user_info,
                    timeout=120.0,
                )
                if not gate_ok:
                    self.logger.error(
                        "前序席位未在时限内就绪，中止连接 user=%s",
                        self.user_info,
                    )
                    return False

                self.logger.info(f"Connecting to {self.uri}... (attempt {retry_count + 1})")
                
                # 连接服务器
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.uri,
                        ping_interval=None,
                        ping_timeout=None,
                        close_timeout=self.timeout,
                    ),
                    timeout=self.timeout
                )
                
                self.is_connected = True
                self.logger.info(f"✓ Connected to server: {self.uri}")
                await asyncio.to_thread(mark_client_ready, self.user_info)
                self.logger.info(f"✓ 已登记就绪: {self.user_info}")
                
                # 启动心跳任务
                self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                return True
                
            except asyncio.TimeoutError:
                self.logger.warning(f"✗ Connection timeout after {self.timeout}s")
                retry_count += 1
                if self.should_reconnect and (max_retries < 0 or retry_count < max_retries):
                    await asyncio.sleep(self.reconnect_interval)
                    
            except Exception as e:
                self.logger.error(f"✗ Connection error: {e}")
                retry_count += 1
                if self.should_reconnect and (max_retries < 0 or retry_count < max_retries):
                    await asyncio.sleep(self.reconnect_interval)
        
        self.logger.error("Failed to connect after all retries")
        return False
    
    async def _heartbeat_loop(self):
        """心跳保活循环"""
        try:
            while self.is_connected and self.websocket:
                await asyncio.sleep(self.heartbeat_interval)
                if self.is_connected and self.websocket:
                    try:
                        # 发送ping保持连接
                        await self.websocket.ping()
                        self.logger.debug("Heartbeat ping sent")
                    except Exception as e:
                        self.logger.warning(f"Heartbeat failed: {e}")
                        self.is_connected = False
                        break
        except asyncio.CancelledError:
            self.logger.debug("Heartbeat loop cancelled")
        except Exception as e:
            self.logger.error(f"Heartbeat loop error: {e}")
    
    async def send(self, message: str):
        """
        发送消息
        
        Args:
            message: 要发送的消息（字符串）
        """
        if not self.is_connected or not self.websocket:
            raise ConnectionError("WebSocket is not connected")
        
        try:
            await self.websocket.send(message)
            self.logger.debug(f"Sent message: {message[:100]}...")
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            self.is_connected = False
            raise
    
    async def send_json(self, data: dict):
        """
        发送JSON消息
        
        Args:
            data: 要发送的数据字典
        """
        message = json.dumps(data)
        await self.send(message)
    
    async def receive(self) -> Optional[str]:
        """
        接收消息
        
        Returns:
            接收到的消息字符串，如果连接关闭则返回None
        """
        if not self.is_connected or not self.websocket:
            return None
        
        try:
            message = await self.websocket.recv()
            return message
        except websockets.ConnectionClosed:
            self.logger.info("Connection closed by server")
            self.is_connected = False
            return None
        except Exception as e:
            self.logger.error(f"Failed to receive message: {e}")
            self.is_connected = False
            return None
    
    async def receive_json(self) -> Optional[dict]:
        """
        接收JSON消息
        
        Returns:
            解析后的JSON字典，如果连接关闭或解析失败则返回None
        """
        message = await self.receive()
        if message is None:
            return None
        
        try:
            return json.loads(message)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON received: {e}")
            return None
    
    async def handle_messages(self, message_handler: Optional[Callable] = None):
        """
        处理消息循环
        
        Args:
            message_handler: 消息处理回调函数，接收 (data: dict) 参数
        """
        if message_handler:
            self.message_handler = message_handler
        
        if not self.message_handler:
            self.logger.warning("No message handler set, using default")
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    # 首次收到游戏消息时登记 game_ready（确认客户端能处理消息）
                    if not self._game_ready_marked:
                        self._game_ready_marked = True
                        await asyncio.to_thread(mark_game_ready, self.user_info)
                        self.logger.info(f"✓ 首条消息到达，game_ready: {self.user_info}")
                    await self.message_handler(data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"✗ Invalid JSON: {e}")
                except Exception as e:
                    self.logger.error(f"✗ Message processing error: {e}", exc_info=True)
        
        except websockets.ConnectionClosed as e:
            self.logger.info(f"Connection closed: {e}")
            self.is_connected = False
        except Exception as e:
            self.logger.error(f"✗ Connection error: {e}", exc_info=True)
            self.is_connected = False
        finally:
            self.logger.info("Message handling loop ended")
    
    async def close(self):
        """关闭连接"""
        self.should_reconnect = False
        self.is_connected = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")
        
        self.logger.info("WebSocket connection closed")
    
    def set_message_handler(self, handler: Callable):
        """
        设置消息处理回调
        
        Args:
            handler: 消息处理函数，接收 (data: dict) 参数
        """
        self.message_handler = handler

