#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feishu 飞书 Gateway 启动脚本
- 配置飞书OAuth授权
- 监听飞书机器人消息
- 处理用户点击同意按钮后的自动化请求
"""

import subprocess
import sys
import logging
import json
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class FeishuGateway:
    def __init__(self):
        self.cli_path = r"C:\Users\Jennifer\AppData\Roaming\npm\node_modules\@larksuite\cli\bin\lark-cli.exe"
        self.bot_process = None

    def check_cli(self):
        """检查飞书CLI是否可用"""
        try:
            result = subprocess.run(
                [self.cli_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✓ 飞书CLI可用: {result.stdout.strip()}")
                return True
        except Exception as e:
            logger.error(f"❌ 飞书CLI不可用: {e}")
        return False

    def check_auth(self):
        """检查是否已授权"""
        try:
            result = subprocess.run(
                [self.cli_path, "auth", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✓ 已授权: {result.stdout[:100]}")
                return True
            else:
                logger.info("⚠ 未授权，需要进行OAuth认证")
                return False
        except Exception as e:
            logger.warning(f"⚠ 无法检查授权状态: {e}")
            return False

    def request_auth(self):
        """请求授权"""
        logger.info("=" * 70)
        logger.info("【第1步】飞书 OAuth 授权")
        logger.info("=" * 70)

        try:
            logger.info("启动飞书认证流程...")
            result = subprocess.run(
                [self.cli_path, "auth", "create"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"✓ 授权成功！")
                logger.info(result.stdout)
                return True
            else:
                logger.error(f"❌ 授权失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("❌ 授权超时")
            return False
        except Exception as e:
            logger.error(f"❌ 授权异常: {e}")
            return False

    def start_gateway(self):
        """启动飞书事件网关"""
        logger.info("=" * 70)
        logger.info("【第2步】启动飞书事件监听网关")
        logger.info("=" * 70)

        try:
            logger.info("启动飞书事件订阅...")
            self.bot_process = subprocess.Popen(
                [
                    self.cli_path,
                    "event",
                    "+subscribe",
                    "--event-types",
                    "im.message.receive_v1",
                    "--compact"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            logger.info("✓ 飞书网关已启动")
            logger.info("  监听来自飞书机器人的消息...")
            logger.info("  当用户点击同意按钮时，自动执行请求")
            logger.info("\n  【等待飞书事件...】")

            return True

        except Exception as e:
            logger.error(f"❌ 启动网关失败: {e}")
            return False

    def handle_message(self, message):
        """处理来自飞书的消息"""
        try:
            msg = json.loads(message) if isinstance(message, str) else message
            msg_type = msg.get('msg_type', 'unknown')
            content = msg.get('content', {})

            logger.info(f"\n📨 收到飞书消息 (类型: {msg_type})")

            # 处理用户点击同意按钮的事件
            if 'action' in content:
                action = content['action']
                logger.info(f"✓ 用户点击了: {action}")

                if 'approve' in action.lower() or 'yes' in action.lower():
                    logger.info("✓ 用户同意! 可以继续执行自动化任务...")
                    return True

            return False

        except Exception as e:
            logger.debug(f"无法解析消息: {e}")
            return False

    def listen(self):
        """监听飞书事件"""
        if not self.bot_process:
            logger.error("❌ 网关未启动")
            return False

        try:
            logger.info("=" * 70)
            logger.info("【第3步】监听飞书事件")
            logger.info("=" * 70)

            while self.bot_process.poll() is None:
                try:
                    line = self.bot_process.stdout.readline()
                    if line:
                        self.handle_message(line.strip())
                except:
                    pass

            return True

        except KeyboardInterrupt:
            logger.info("\n⚠ 用户中断")
            return True
        except Exception as e:
            logger.error(f"❌ 监听异常: {e}")
            return False

    def stop(self):
        """停止网关"""
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=3)
                logger.info("✓ 网关已停止")
            except:
                self.bot_process.kill()
                logger.info("✓ 网关已强制停止")

    def run(self):
        """运行完整流程"""
        logger.info("\n╔" + "=" * 68 + "╗")
        logger.info("║  Feishu 飞书 授权网关                                  ║")
        logger.info("║  用于接收用户授权并执行自动化任务                      ║")
        logger.info("╚" + "=" * 68 + "╝\n")

        try:
            # 检查CLI
            if not self.check_cli():
                logger.error("❌ 飞书CLI不可用，退出")
                return False

            # 检查授权
            if not self.check_auth():
                # 如果未授权，请求授权
                if not self.request_auth():
                    logger.error("❌ 授权失败，退出")
                    return False

            # 启动网关
            if not self.start_gateway():
                logger.error("❌ 启动网关失败，退出")
                return False

            # 监听事件
            self.listen()

            return True

        finally:
            self.stop()

if __name__ == "__main__":
    gateway = FeishuGateway()
    success = gateway.run()
    sys.exit(0 if success else 1)
