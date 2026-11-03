"""In-memory stand-in for a Discord server, implementing the adapter interface."""
import itertools


class FakeHTTP(Exception):
    def __init__(self, status, msg=""):
        super().__init__(msg or f"HTTP {status}")
        self.status = status


class FakeGuild:
    def __init__(self, name="Test", community=False, channels=(), roles=(), fail_on=None, flaky=0):
        self.ids = itertools.count(1000)
        self.guild_id = 1
        self.name, self.community = name, community
        self.everyone = {"id": 1, "name": "@everyone", "color": 0, "hoist": False, "mentionable": False,
                         "permissions": 0, "position": 0, "managed": False, "default": True, "above_bot": False}
        self.bot_role = {"id": 2, "name": "ORRIN Architect", "color": 0, "hoist": False, "mentionable": False,
                         "permissions": 8, "position": 50, "managed": True, "default": False, "above_bot": True}
        self.roles = {1: self.everyone, 2: self.bot_role}
        for r in roles:
            rid = next(self.ids)
            self.roles[rid] = {"id": rid, "color": 0, "hoist": False, "mentionable": False, "permissions": 0,
                               "position": 1, "managed": False, "default": False, "above_bot": False, **r}
        self.channels = {}
        for c in channels:
            cid = next(self.ids)
            self.channels[cid] = {"id": cid, "type": "text", "position": len(self.channels), "parent_id": None,
                                  "topic": None, "nsfw": False, "slowmode": 0, "overwrites": [], **c}
        self.settings = {"verification_level": 0, "explicit_content_filter": 0, "default_notifications": 0}
        self.automod, self.messages, self.calls = {}, [], []
        self.fail_on = fail_on or (lambda op, name: False)
        self.flaky = flaky  # first N calls raise a 429-like error

    def _maybe_fail(self, op, name=""):
        self.calls.append((op, name))
        if self.flaky > 0:
            self.flaky -= 1
            raise FakeHTTP(429, "rate limited")
        if self.fail_on(op, name):
            raise FakeHTTP(400, f"{op} {name} refused")

    async def snapshot(self):
        return {"guild_id": self.guild_id, "name": self.name, "everyone_id": 1,
                "everyone_permissions": self.everyone["permissions"], "community": self.community,
                "settings": dict(self.settings),
                "roles": [dict(r) for r in self.roles.values()],
                "channels": [dict(c, overwrites=[dict(o) for o in c["overwrites"]]) for c in self.channels.values()]}

    async def create_role(self, name, permissions, color, hoist, mentionable):
        self._maybe_fail("create_role", name)
        rid = next(self.ids)
        self.roles[rid] = {"id": rid, "name": name, "permissions": permissions, "color": color, "hoist": hoist,
                           "mentionable": mentionable, "position": 1, "managed": False, "default": False,
                           "above_bot": False}
        return rid

    async def edit_role(self, rid, **kw):
        self._maybe_fail("edit_role", str(rid))
        if rid not in self.roles:
            raise FakeHTTP(404)
        self.roles[rid].update({k: v for k, v in kw.items() if v is not None})

    async def move_roles(self, order):
        self._maybe_fail("move_roles")
        for i, rid in enumerate(order):
            self.roles[rid]["position"] = 49 - i

    async def delete_role(self, rid):
        self._maybe_fail("delete_role", str(rid))
        if rid not in self.roles:
            raise FakeHTTP(404)
        del self.roles[rid]

    async def create_channel(self, kind, name, parent_id, overwrites, topic, slowmode, nsfw, tags):
        self._maybe_fail("create_channel", name)
        if kind in ("stage", "announcement") and not self.community:
            raise FakeHTTP(400, "needs community")
        if len(self.channels) >= 500:
            raise FakeHTTP(400, "max channels")
        cid = next(self.ids)
        ows = [{"id": rid, "kind": "role", "role_name": self.roles.get(rid, {}).get("name"),
                "default": rid == 1, "allow": a, "deny": d} for rid, (a, d) in overwrites.items()]
        self.channels[cid] = {"id": cid, "name": name, "type": kind, "position": len(self.channels),
                              "parent_id": parent_id, "topic": topic, "nsfw": nsfw, "slowmode": slowmode,
                              "overwrites": ows, "tags": list(tags or [])}
        return cid

    async def edit_channel(self, cid, **kw):
        self._maybe_fail("edit_channel", str(cid))
        if kw.get("type"):
            self.channels[cid]["type"] = kw["type"]

    async def delete_channel(self, cid):
        self._maybe_fail("delete_channel", str(cid))
        if cid not in self.channels:
            raise FakeHTTP(404)
        del self.channels[cid]

    async def edit_guild(self, s):
        self._maybe_fail("edit_guild")
        self.settings.update({k: v for k, v in s.items() if k in self.settings})

    async def enable_community(self, rules_id, updates_id):
        self._maybe_fail("enable_community")
        assert rules_id in self.channels and updates_id in self.channels
        self.community = True
        self.settings["explicit_content_filter"] = 2
        self.settings["verification_level"] = max(1, self.settings["verification_level"])
        return True

    async def create_automod(self, rule, log_channel_id, exempt):
        self._maybe_fail("create_automod", rule["name"])
        aid = next(self.ids)
        self.automod[aid] = dict(rule, log=log_channel_id, exempt=list(exempt))
        return aid

    async def delete_automod(self, aid):
        self._maybe_fail("delete_automod", str(aid))
        self.automod.pop(aid, None)

    async def send(self, cid, content=None, rules=None, server="", accept_role_id=None, role_buttons=None):
        self._maybe_fail("send", str(cid))
        mid = next(self.ids)
        self.messages.append({"id": mid, "channel": cid, "content": content, "rules": rules,
                              "accept_role_id": accept_role_id, "role_buttons": list(role_buttons or [])})
        return mid

    # helpers for assertions
    def by_name(self, plain_name):
        from architect.render import plain
        return [c for c in self.channels.values() if plain(c["name"]) == plain_name]

    def role(self, name):
        return next((r for r in self.roles.values() if r["name"] == name), None)
