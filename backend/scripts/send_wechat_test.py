#!/usr/bin/env python3
"""Send a real test notification to the WeChat Work webhook configured
in backend/tests/wechat_test_config.json.

Usage:
  python backend/scripts/send_wechat_test.py
"""
import asyncio
import json
import os
import sys
import logging


# Ensure backend package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.notification import WeChatWorkChannel, NotificationContext, NotificationType


async def main():
    cfg_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tests", "wechat_test_config.json"))
    if not os.path.exists(cfg_path):
        print(f"Config not found: {cfg_path}")
        return

    with open(cfg_path, "r") as f:
        config = json.load(f)

    webhook = config.get("wechat_work_webhook_url")
    if not webhook:
        print("No wechat_work_webhook_url configured in test config")
        return

    channel = WeChatWorkChannel()

    ctx = NotificationContext(
        notification_type=NotificationType.BET_CREATED,
        family_id=1,
        family_name="测试家庭",
        title="[测试] 实际 Webhook 发送",
        content="这是一条用于验证企业微信机器人能否收到消息的测试通知。",
        requester_name="CI-Tester",
        bet_id=9999,
        base_url=config.get("external_base_url"),
        amount=1.0,
    )

    print("Sending test notification to:", webhook)
    ok = await channel.send(ctx, config)
    print("Send result:", ok)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
