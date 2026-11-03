"""The real adapter: the applier's primitive operations on a live discord.py Guild."""
from __future__ import annotations

import datetime as dt

import discord

REASON = "ORRIN Architect /setup"
ACCEPT_PREFIX = "architect:accept:"
PICK_PREFIX = "architect:pick:"

TRIGGER = {"spam": discord.AutoModRuleTriggerType.spam,
           "mention_spam": discord.AutoModRuleTriggerType.mention_spam,
           "profanity": discord.AutoModRuleTriggerType.keyword_preset,
           "keyword": discord.AutoModRuleTriggerType.keyword}


def _type_name(ch) -> str:
    t = ch.type
    return {discord.ChannelType.text: "text", discord.ChannelType.voice: "voice",
            discord.ChannelType.category: "category", discord.ChannelType.news: "announcement",
            discord.ChannelType.stage_voice: "stage", discord.ChannelType.forum: "forum"}.get(t, str(t))


def accept_view(role_id) -> discord.ui.View:
    v = discord.ui.View(timeout=None)
    v.add_item(discord.ui.Button(label="I accept the rules", emoji="✅", style=discord.ButtonStyle.success,
                                 custom_id=f"{ACCEPT_PREFIX}{role_id}"))
    return v


def picker_view(role_buttons) -> discord.ui.View:
    """Persistent toggle buttons for self-assignable roles (handled in Architect.on_interaction)."""
    v = discord.ui.View(timeout=None)
    for rid, name in list(role_buttons)[:25]:
        v.add_item(discord.ui.Button(label=str(name)[:80], style=discord.ButtonStyle.secondary,
                                     custom_id=f"{PICK_PREFIX}{rid}"))
    return v


def rules_embed(rules: list[str], server: str = "") -> discord.Embed:
    e = discord.Embed(title=f"📜 {server + ' ' if server else ''}Rules".strip(), color=0x5865F2,
                      description="\n\n".join(f"**{i}.** {r}" for i, r in enumerate(rules, 1))[:4000])
    e.set_footer(text="Breaking the rules can get you warned, timed out or banned.")
    return e


class DiscordAdapter:
    def __init__(self, guild: discord.Guild):
        self.g = guild
        self.roles: dict[int, discord.Role] = {r.id: r for r in guild.roles}
        self.chans: dict[int, discord.abc.GuildChannel] = {c.id: c for c in guild.channels}

    # ---- reading
    def bot_top(self) -> discord.Role:
        return self.g.me.top_role

    async def snapshot(self) -> dict:
        g = self.g
        top = self.bot_top().position
        roles = [{"id": r.id, "name": r.name, "color": r.colour.value, "hoist": r.hoist, "mentionable": r.mentionable,
                  "permissions": r.permissions.value, "position": r.position, "managed": r.managed,
                  "default": r.is_default(), "above_bot": r.position >= top and not r.is_default()}
                 for r in g.roles]
        chans = []
        for c in g.channels:
            ows = []
            for target, ow in c.overwrites.items():
                a, d = ow.pair()
                is_role = isinstance(target, discord.Role)
                ows.append({"id": target.id, "kind": "role" if is_role else "member",
                            "role_name": target.name if is_role else None,
                            "default": is_role and target.is_default(), "allow": a.value, "deny": d.value})
            chans.append({"id": c.id, "name": c.name, "type": _type_name(c), "position": c.position,
                          "parent_id": c.category_id, "topic": getattr(c, "topic", None),
                          "nsfw": getattr(c, "nsfw", False) if not isinstance(c, discord.CategoryChannel) else False,
                          "slowmode": getattr(c, "slowmode_delay", 0) or 0, "overwrites": ows})
        automod = []
        try:   # existing AutoMod rules, so a second /setup doesn't hit Discord's one-per-kind limits
            kinds = {v: k for k, v in TRIGGER.items()}
            for r in await g.fetch_automod_rules():
                automod.append({"id": r.id, "name": r.name, "kind": kinds.get(r.trigger.type, str(r.trigger.type))})
        except (discord.HTTPException, AttributeError):
            pass
        return {"guild_id": g.id, "name": g.name, "everyone_id": g.default_role.id, "automod": automod,
                "everyone_permissions": g.default_role.permissions.value,
                "community": "COMMUNITY" in g.features, "taken_at": dt.datetime.utcnow().isoformat() + "Z",
                "settings": {"verification_level": g.verification_level.value,
                             "explicit_content_filter": g.explicit_content_filter.value,
                             "default_notifications": g.default_notifications.value},
                "roles": roles, "channels": chans}

    # ---- helpers
    def _role(self, rid):
        r = self.roles.get(rid) or self.g.get_role(rid)
        return r or discord.Object(id=rid, type=discord.Role)

    def _ows(self, ows: dict):
        return {self._role(rid): discord.PermissionOverwrite.from_pair(discord.Permissions(a), discord.Permissions(d))
                for rid, (a, d) in ows.items()}

    def _chan(self, cid):
        return self.chans.get(cid) or self.g.get_channel(cid)

    # ---- roles
    async def create_role(self, name, permissions, color, hoist, mentionable):
        r = await self.g.create_role(name=name, permissions=discord.Permissions(permissions), colour=color,
                                     hoist=hoist, mentionable=mentionable, reason=REASON)
        self.roles[r.id] = r
        return r.id

    async def edit_role(self, rid, **kw):
        r = self.roles.get(rid) or self.g.get_role(rid)
        if r is None:
            return  # already gone
        args = {}
        if "permissions" in kw and kw["permissions"] is not None:
            args["permissions"] = discord.Permissions(kw["permissions"])
        if kw.get("color") is not None:
            args["colour"] = kw["color"]
        for k in ("hoist", "mentionable"):
            if kw.get(k) is not None:
                args[k] = kw[k]
        await r.edit(reason=REASON, **args)

    async def move_roles(self, order):
        """Put these roles, in this order, right under the bot's own top role."""
        top = self.bot_top().position
        pos = {}
        for i, rid in enumerate(order):
            r = self.roles.get(rid) or self.g.get_role(rid)
            if r is not None and not r.managed:
                pos[r] = max(1, top - 1 - i)
        if pos:
            await self.g.edit_role_positions(positions=pos, reason=REASON)

    async def delete_role(self, rid):
        r = self.roles.get(rid) or self.g.get_role(rid)
        if r is not None:
            await r.delete(reason=REASON)

    # ---- channels
    async def create_channel(self, kind, name, parent_id, overwrites, topic, slowmode, nsfw, tags):
        g, ow = self.g, self._ows(overwrites)
        cat = self._chan(parent_id) if parent_id else None
        if kind == "category":
            c = await g.create_category(name, overwrites=ow, reason=REASON)
        elif kind in ("text", "announcement"):
            c = await g.create_text_channel(name, category=cat, overwrites=ow, topic=topic or "",
                                            slowmode_delay=slowmode or 0, nsfw=nsfw, news=kind == "announcement",
                                            reason=REASON)
        elif kind == "voice":
            c = await g.create_voice_channel(name, category=cat, overwrites=ow, reason=REASON)
        elif kind == "stage":
            c = await g.create_stage_channel(name, category=cat, overwrites=ow, reason=REASON)
        elif kind == "forum":
            try:
                c = await g.create_forum(name, category=cat, overwrites=ow, topic=topic or "",
                                         slowmode_delay=slowmode or 0, nsfw=nsfw,
                                         available_tags=[discord.ForumTag(name=t) for t in (tags or [])][:20],
                                         reason=REASON)
            except discord.HTTPException:
                c = await g.create_text_channel(name, category=cat, overwrites=ow, topic=topic or "", reason=REASON)
        else:
            raise ValueError(kind)
        self.chans[c.id] = c
        return c.id

    async def edit_channel(self, cid, **kw):
        c = self._chan(cid)
        if kw.get("type") == "announcement" and isinstance(c, discord.TextChannel):
            await c.edit(type=discord.ChannelType.news, reason=REASON)

    async def delete_channel(self, cid):
        c = self._chan(cid)
        if c is not None:
            await c.delete(reason=REASON)

    # ---- server
    async def edit_guild(self, s: dict):
        args = {}
        if "verification_level" in s:
            args["verification_level"] = discord.VerificationLevel(s["verification_level"])
        if "explicit_content_filter" in s:
            args["explicit_content_filter"] = discord.ContentFilter(s["explicit_content_filter"])
        if "default_notifications" in s:
            args["default_notifications"] = discord.NotificationLevel(s["default_notifications"])
        if "rules_channel_id" in s:
            args["rules_channel"] = self._chan(s["rules_channel_id"])
        if args:
            await self.g.edit(reason=REASON, **args)

    async def enable_community(self, rules_id, updates_id) -> bool:
        await self.g.edit(community=True, rules_channel=self._chan(rules_id),
                          public_updates_channel=self._chan(updates_id),
                          verification_level=discord.VerificationLevel(max(self.g.verification_level.value, 1)),
                          explicit_content_filter=discord.ContentFilter.all_members, reason=REASON)
        return True

    # ---- AutoMod
    async def create_automod(self, rule, log_channel_id, exempt_role_ids):
        k = rule["kind"]
        if k == "keyword":
            trig = discord.AutoModTrigger(type=TRIGGER[k], keyword_filter=rule["keywords"])
        elif k == "profanity":
            trig = discord.AutoModTrigger(type=TRIGGER[k], presets=discord.AutoModPresets.all())
        elif k == "mention_spam":
            trig = discord.AutoModTrigger(type=TRIGGER[k], mention_limit=rule.get("mention_limit", 5),
                                          mention_raid_protection=True)
        else:
            trig = discord.AutoModTrigger(type=TRIGGER[k])
        actions = [discord.AutoModRuleAction(custom_message=rule.get("message") or "Blocked by AutoMod.")]
        if log_channel_id:
            actions.append(discord.AutoModRuleAction(channel_id=log_channel_id))
        if k == "mention_spam":
            actions.append(discord.AutoModRuleAction(duration=dt.timedelta(minutes=10)))
        r = await self.g.create_automod_rule(name=rule["name"], event_type=discord.AutoModRuleEventType.message_send,
                                             trigger=trig, actions=actions, enabled=True,
                                             exempt_roles=[discord.Object(id=i) for i in exempt_role_ids][:20],
                                             reason=REASON)
        return r.id

    async def delete_automod(self, aid):
        r = await self.g.fetch_automod_rule(aid)
        await r.delete(reason=REASON)

    # ---- messages
    async def send(self, cid, content=None, rules=None, server="", accept_role_id=None, role_buttons=None):
        c = self._chan(cid)
        if role_buttons:
            m = await c.send((content or "Pick your roles:")[:2000], view=picker_view(role_buttons),
                             allowed_mentions=discord.AllowedMentions.none())
        elif rules:
            view = accept_view(accept_role_id) if accept_role_id else discord.utils.MISSING
            m = await c.send(embed=rules_embed(rules, server), view=view)
        else:
            m = await c.send(content[:2000], allowed_mentions=discord.AllowedMentions.none())
        return m.id
