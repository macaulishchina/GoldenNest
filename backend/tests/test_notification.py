import asyncio
import json
import os
import sys
import pytest

import httpx

# Ensure backend/ is on sys.path so `app` package can be imported during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services import notification
from app.services.notification import NotificationContext, NotificationType
from app.models.models import ApprovalRequestType


class FakeResponse:
    def __init__(self):
        self._json = {"errcode": 0}

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None):
        return FakeResponse()


@pytest.fixture(autouse=True)
def patch_httpx_client(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)


def load_test_config():
    path = os.path.join(os.path.dirname(__file__), "wechat_test_config.json")
    with open(path, "r") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_wechat_notifications_for_all_types():
    config = load_test_config()
    channel = notification.WeChatWorkChannel()

    base = config.get("external_base_url")

    # Build representative contexts for each notification type
    contexts = []
    for nt in NotificationType:
        ctx = NotificationContext(
            notification_type=nt,
            family_id=1,
            family_name="测试家庭",
            title=f"测试 - {nt.value}",
            content="这是测试消息",
            base_url=base,
        )

        # Fill type-specific fields
        if nt.name.startswith("APPROVAL"):
            ctx.request_id = 123
            ctx.request_type = ApprovalRequestType.EXPENSE
            ctx.requester_name = "Alice"
            ctx.approver_name = "Bob"
            ctx.amount = 99.9
        if nt.name.startswith("GIFT"):
            ctx.gift_id = 200
            ctx.requester_name = "Carol"
            ctx.approver_name = "Dave"
            ctx.extra_data = {"amount_percent": 5.0}
        if nt.name.startswith("VOTE"):
            ctx.proposal_id = 300
            ctx.requester_name = "Eve"
            ctx.voter_name = "Frank"
            ctx.vote_option = "选项A"
            ctx.amount = 50.0
        if nt.name.startswith("BET"):
            ctx.bet_id = 400
            ctx.requester_name = "Grace"
            ctx.voter_name = "Heidi"
            ctx.vote_option = "红"
            ctx.amount = 20.0
        if nt == NotificationType.PET_EVOLVED:
            ctx.content = "宠物进化测试"

        contexts.append(ctx)

    # Ensure channel considers config configured
    assert channel.is_configured(config)

    # Send each and assert True (FakeAsyncClient returns success)
    for ctx in contexts:
        ok = await channel.send(ctx, config)
        assert ok is True
