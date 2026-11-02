"""The adapter builds valid discord.py objects (triggers, actions, overwrites, views) - checked
against a stub guild, so no network."""
import types

import discord
import pytest

from architect.discord_adapter import DiscordAdapter, accept_view, rules_embed, ACCEPT_PREFIX


class StubGuild:
    def __init__(self):
        self.roles, self.channels, self.calls = [], [], []
        self.verification_level = discord.VerificationLevel.none
        self.id = 1

    def get_role(self, i):
        return None

    def get_channel(self, i):
        return None

    async def create_automod_rule(self, **kw):
        self.calls.append(("automod", kw))
        return types.SimpleNamespace(id=99)

    async def create_text_channel(self, name, **kw):
        self.calls.append(("text", name, kw))
        return types.SimpleNamespace(id=5)

    async def create_forum(self, name, **kw):
        self.calls.append(("forum", name, kw))
        return types.SimpleNamespace(id=6)

    async def edit(self, **kw):
        self.calls.append(("edit", kw))


@pytest.mark.parametrize("rule", [{"kind": "spam", "name": "s"}, {"kind": "profanity", "name": "p"},
                                  {"kind": "mention_spam", "name": "m", "mention_limit": 5},
                                  {"kind": "keyword", "name": "k", "keywords": ["free nitro"]}])
async def test_automod_objects(rule):
    g = StubGuild()
    a = DiscordAdapter(g)
    assert await a.create_automod(rule, 123, [7]) == 99
    kw = g.calls[0][1]
    assert kw["enabled"] and kw["trigger"].type.name == {"profanity": "keyword_preset"}.get(rule["kind"], rule["kind"])
    assert any(x.type == discord.AutoModRuleActionType.send_alert_message for x in kw["actions"])
    if rule["kind"] == "mention_spam":
        assert any(x.type == discord.AutoModRuleActionType.timeout for x in kw["actions"])


async def test_channel_overwrites_and_forum_tags():
    g = StubGuild()
    a = DiscordAdapter(g)
    await a.create_channel("text", "╭📜︱rules", None, {1: (1024, 2048)}, "t", 3, False, [])
    kind, name, kw = g.calls[0]
    (target, ow), = kw["overwrites"].items()
    assert target.id == 1 and target.type is discord.Role
    assert ow.view_channel is True and ow.send_messages is False
    assert kw["slowmode_delay"] == 3 and kw["news"] is False
    await a.create_channel("forum", "help", None, {}, "t", 0, False, ["Solved", "Bug"])
    assert [t.name for t in g.calls[1][2]["available_tags"]] == ["Solved", "Bug"]


async def test_guild_settings():
    g = StubGuild()
    await DiscordAdapter(g).edit_guild({"verification_level": 2, "explicit_content_filter": 2,
                                        "default_notifications": 1})
    kw = g.calls[0][1]
    assert kw["verification_level"] == discord.VerificationLevel.medium
    assert kw["explicit_content_filter"] == discord.ContentFilter.all_members
    assert kw["default_notifications"] == discord.NotificationLevel.only_mentions


def test_rules_view_and_embed():
    v = accept_view(42)
    (btn,) = v.children
    assert btn.custom_id == f"{ACCEPT_PREFIX}42" and v.timeout is None
    e = rules_embed(["Be nice", "No spam"], "ORRIN")
    assert "**1.** Be nice" in e.description and e.title == "📜 ORRIN Rules"
