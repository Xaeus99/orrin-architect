"""Apply a validated plan to a server, and undo it.

Talks to Discord only through an *adapter* (see discord_adapter.py for the real one and
tests/fake_guild.py for the in-memory one the tests use), so every rule here is testable
without Discord."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import limits as L
from .batching import Op, run_batched
from .overwrites import compute, everyone_base
from .render import rendered, plain
from .schema import VERIFICATION, EXPLICIT, NOTIFY

LOG_CHANNEL = "architect-log"


class CapacityError(RuntimeError):
    pass


@dataclass
class Report:
    journal: dict
    ok: int = 0
    failed: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def summary(self) -> str:
        c = self.journal.get("created", {})
        s = (f"Created {len(c.get('roles', []))} roles, {len(c.get('channels', []))} channels/categories, "
             f"{len(c.get('automod', []))} AutoMod rules.")
        d = self.journal.get("deleted", {})
        if d.get("channels") or d.get("roles"):
            s += f" Removed {len(d.get('channels', []))} old channels and {len(d.get('roles', []))} old roles."
        if self.failed:
            s += f" {len(self.failed)} step(s) failed."
        return s


PICKER_MAX = 20   # buttons per message (Discord allows 25: 5 rows x 5)
PICKER_TEXT = ("🎨 **Pick your roles** — tap a button to add it, tap again to remove it. "
               "Colours, pings and more.")


def picker_channel(plan: dict, ch_ids: dict):
    """The channel the self-role picker goes in: self-roles > *roles* > welcome."""
    names = [ch["name"] for c in plan["categories"] for ch in c["channels"] if ch["type"] == "text"]
    for want in ("self-roles", "pick-roles", "get-roles", "roles"):
        for n in names:
            if n == want and ch_ids.get(n):
                return ch_ids[n]
    for n in names:
        if "role" in n and "info" not in n and ch_ids.get(n):
            return ch_ids[n]
    return None


def to_create(plan: dict, snapshot: dict, mode: str) -> dict:
    """What the plan will add, after 'add' mode skips things that already exist."""
    roles_existing = {r["name"].lower() for r in snapshot["roles"]}
    chans = snapshot["channels"]
    cat_existing = {plain(c["name"]) for c in chans if c["type"] == "category"}
    ch_existing = {plain(c["name"]) for c in chans if c["type"] != "category"}
    roles = [r for r in plan["roles"] if r["name"].lower() not in roles_existing]  # same name = reused
    n_cats = n_ch = 0
    for c in plan["categories"]:
        if mode == "replace" or plain(c["name"]) not in cat_existing:
            n_cats += 1
        for ch in c["channels"]:
            if mode == "replace" or plain(ch["name"]) not in ch_existing:
                n_ch += 1
    log_missing = not any(plain(c["name"]) == LOG_CHANNEL for c in chans)
    return {"roles": len(roles), "categories": n_cats, "channels": n_ch, "log": int(log_missing)}


def check_capacity(plan: dict, snapshot: dict, mode: str) -> dict:
    """Raise CapacityError if the server would go over Discord's limits at any point.
    New things are created before old ones are removed, so the peak is existing + new."""
    t = to_create(plan, snapshot, mode)
    peak_ch = len(snapshot["channels"]) + t["categories"] + t["channels"] + t["log"]
    peak_roles = len(snapshot["roles"]) + t["roles"]
    if peak_ch > L.MAX_CHANNELS:
        raise CapacityError(f"this would need {peak_ch} channels; Discord allows {L.MAX_CHANNELS}. "
                            "Remove some channels first or ask for a smaller layout.")
    if peak_roles > L.MAX_ROLES:
        raise CapacityError(f"this would need {peak_roles} roles; Discord allows {L.MAX_ROLES}.")
    if len([c for c in snapshot["channels"] if c["type"] == "category"]) + t["categories"] > L.MAX_CHANNELS:
        raise CapacityError("too many categories")
    t.update(peak_channels=peak_ch, peak_roles=peak_roles)
    return t


class Applier:
    def __init__(self, adapter, *, batch_size=5, pause=1.0, sleep=None, log=None):
        self.a = adapter
        self.batch_size, self.pause = batch_size, pause
        self.kw = {"sleep": sleep} if sleep else {}
        self.log = log  # async callable(str) -> None, posts to #architect-log

    async def _log(self, msg):
        if self.log:
            try:
                await self.log(msg)
            except Exception:  # logging must never break a build
                pass

    async def _run(self, ops, progress, phase):
        async def prog(p):
            if progress:
                await progress(phase, p)
        return await run_batched(ops, batch_size=self.batch_size, pause=self.pause, on_progress=prog, **self.kw)

    # ------------------------------------------------------------------ apply
    async def apply(self, plan: dict, snapshot: dict, mode: str = "add", backup_file: str = "",
                    progress=None) -> Report:
        assert mode in {"add", "replace"}
        check_capacity(plan, snapshot, mode)
        J = {"id": time.strftime("%Y%m%d-%H%M%S"), "guild_id": snapshot.get("guild_id"), "mode": mode,
             "backup_file": backup_file, "plan_summary": plan.get("summary", ""),
             "created": {"roles": [], "channels": [], "automod": [], "messages": []},
             "edited_roles": [], "deleted": {"channels": [], "roles": []},
             "settings_before": snapshot.get("settings", {}), "everyone_before": snapshot.get("everyone_permissions"),
             "everyone_id": snapshot.get("everyone_id") or snapshot.get("guild_id"),
             "undone": False}
        rep = Report(J)
        everyone_id = snapshot.get("everyone_id") or snapshot.get("guild_id")
        existing_roles = {r["name"].lower(): r for r in snapshot["roles"] if not r.get("default")}
        role_ids: dict[str, object] = {"@everyone": everyone_id}
        await self._log(f"🏗️ Setup started ({mode} mode): {plan.get('summary') or 'custom plan'}")

        # 1. roles ------------------------------------------------------
        ops = []
        for r in plan["roles"]:
            ex = existing_roles.get(r["name"].lower())
            if ex and mode == "add":
                role_ids[r["name"]] = ex["id"]
                continue
            if ex and mode == "replace":
                role_ids[r["name"]] = ex["id"]
                if ex.get("managed") or ex.get("above_bot"):
                    continue

                async def edit(r=r, ex=ex):
                    J["edited_roles"].append({"id": ex["id"], "before": {k: ex.get(k) for k in
                                              ("name", "permissions", "color", "hoist", "mentionable")}})
                    await self.a.edit_role(ex["id"], permissions=r["permissions"], color=r["color"],
                                           hoist=r["hoist"], mentionable=r["mentionable"])
                ops.append(Op(f"update role {r['name']}", edit))
                continue

            async def make(r=r):
                rid = await self.a.create_role(r["name"], r["permissions"], r["color"], r["hoist"], r["mentionable"])
                role_ids[r["name"]] = rid
                J["created"]["roles"].append(rid)
                return rid
            ops.append(Op(f"role {r['name']}", make))

        async def everyone():
            await self.a.edit_role(everyone_id, permissions=everyone_base(plan))
        ops.append(Op("@everyone permissions", everyone))
        res = await self._run(ops, progress, "roles")

        order = [role_ids[r["name"]] for r in plan["roles"] if r["name"] in role_ids
                 and not (existing_roles.get(r["name"].lower()) or {}).get("above_bot")
                 and not (existing_roles.get(r["name"].lower()) or {}).get("managed")]
        if order:
            res += await self._run([Op("order roles", lambda: self.a.move_roles(order))], progress, "roles")

        def ow_ids(ow: dict) -> dict:
            out = {}
            for name, (al, de) in ow.items():
                rid = role_ids.get(name)
                if rid is None:
                    m = existing_roles.get(name.lower())
                    rid = m["id"] if m else None
                if rid is None:
                    rep.notes.append(f"role '{name}' not found; its channel access was skipped")
                    continue
                out[rid] = (al, de)
            return out

        # 2. log channel -------------------------------------------------
        log_ex = next((c for c in snapshot["channels"] if plain(c["name"]) == LOG_CHANNEL), None)
        log_id = log_ex["id"] if log_ex else None
        if not log_id:
            staff = compute({"private": True}, None, plan)   # @everyone hidden, staff roles can see it

            async def mklog():
                nonlocal log_id
                log_id = await self.a.create_channel("text", LOG_CHANNEL, None, ow_ids(staff),
                                                     "ORRIN Architect's log of every change it makes.", 0, False, [])
                return log_id
            res += await self._run([Op("#architect-log", mklog)], progress, "channels")
        J["log_channel_id"] = log_id

        # 3. categories, then channels ------------------------------------
        ex_cats = {plain(c["name"]): c["id"] for c in snapshot["channels"] if c["type"] == "category"}
        ex_chs = {plain(c["name"]): c["id"] for c in snapshot["channels"] if c["type"] != "category"}
        cat_ids: dict[int, object] = {}
        ch_ids: dict[str, object] = {}
        deferred: list = []  # (kind, disp, cat_index, ch) needing Community
        ops = []
        layout = list(rendered(plan))
        for ci, (cdisp, chans, cat) in enumerate(layout):
            if mode == "add" and plain(cat["name"]) in ex_cats:
                cat_ids[ci] = ex_cats[plain(cat["name"])]
                continue

            async def mkcat(ci=ci, cdisp=cdisp, cat=cat):
                cid = await self.a.create_channel("category", cdisp, None, ow_ids(compute(cat, None, plan)), "", 0, False, [])
                cat_ids[ci] = cid
                J["created"]["channels"].append(cid)
                return cid
            ops.append(Op(f"category {cdisp}", mkcat))
        res += await self._run(ops, progress, "categories")

        community = bool(snapshot.get("community"))
        ops = []
        for ci, (cdisp, chans, cat) in enumerate(layout):
            for disp, ch in chans:
                if mode == "add" and plain(ch["name"]) in ex_chs:
                    ch_ids[ch["name"]] = ex_chs[plain(ch["name"])]
                    continue
                kind = ch["type"]
                if kind == "stage" and not community:
                    deferred.append(("stage", disp, ci, ch))
                    continue
                if kind == "announcement" and not community:
                    deferred.append(("announcement", disp, ci, ch))
                    kind = "text"

                async def mkch(ci=ci, disp=disp, ch=ch, cat=cat, kind=kind):
                    cid = await self.a.create_channel(kind, disp, cat_ids.get(ci),
                                                      ow_ids(compute(ch, cat, plan)), ch["topic"], ch["slowmode"],
                                                      ch["nsfw"], ch.get("tags", []))
                    ch_ids[ch["name"]] = cid
                    J["created"]["channels"].append(cid)
                    return cid
                ops.append(Op(f"channel {disp}", mkch))
        res += await self._run(ops, progress, "channels")

        # 4. server settings + Community -----------------------------------
        st = plan["settings"]
        want = {"verification_level": VERIFICATION[st["verification_level"]],
                "explicit_content_filter": EXPLICIT[st["explicit_content_filter"]],
                "default_notifications": NOTIFY[st["default_notifications"]]}
        rules_id = ch_ids.get(plan.get("rules_channel"))
        updates_id = log_id
        ops = [Op("server settings", lambda: self.a.edit_guild(want))]
        if st.get("community") and not community and rules_id and updates_id:
            if want["verification_level"] < 1:
                want["verification_level"] = 1
                rep.notes.append("Community needs verification ≥ low; raised it")
            if want["explicit_content_filter"] != 2:
                want["explicit_content_filter"] = 2
                rep.notes.append("Community needs the media filter on for everyone; turned it on")

            async def comm():
                nonlocal community
                community = bool(await self.a.enable_community(rules_id, updates_id))
                return community
            ops.append(Op("turn on Community", comm))
        elif st.get("community") and community and rules_id:
            ops.append(Op("point Community at the new rules channel",
                          lambda: self.a.edit_guild({"rules_channel_id": rules_id})))
        res += await self._run(ops, progress, "settings")

        # 5. things that need Community ------------------------------------
        ops = []
        for kind, disp, ci, ch in deferred:
            cat = layout[ci][2]
            if kind == "announcement":
                cid = ch_ids.get(ch["name"])
                if cid and community:
                    ops.append(Op(f"make {disp} an announcement channel",
                                  lambda cid=cid: self.a.edit_channel(cid, type="announcement")))
                elif not community:
                    rep.notes.append(f"{disp} stays a text channel (announcement channels need Community)")
            else:
                k = "stage" if community else "voice"
                if not community:
                    rep.notes.append(f"{disp} became a voice channel (stage channels need Community)")

                async def mkst(ci=ci, disp=disp, ch=ch, cat=cat, k=k):
                    cid = await self.a.create_channel(k, disp, cat_ids.get(ci), ow_ids(compute(ch, cat, plan)),
                                                      ch["topic"], 0, False, [])
                    ch_ids[ch["name"]] = cid
                    J["created"]["channels"].append(cid)
                    return cid
                ops.append(Op(f"channel {disp}", mkst))
        if ops:
            res += await self._run(ops, progress, "channels")

        # 6. AutoMod -----------------------------------------------------------
        exempt = [role_ids[r["name"]] for r in plan["roles"] if r.get("staff") and r["name"] in role_ids]
        ops = []
        have_am: dict[str, int] = {}
        have_names = set()
        for r0 in snapshot.get("automod") or []:
            have_am[r0.get("kind", "")] = have_am.get(r0.get("kind", ""), 0) + 1
            have_names.add(str(r0.get("name", "")).lower())
        for rule in plan["automod"]:
            cap = 6 if rule["kind"] == "keyword" else 1   # Discord's per-server limit for each kind
            if rule["name"].lower() in have_names or have_am.get(rule["kind"], 0) >= cap:
                rep.notes.append(f"AutoMod '{rule['name']}': this server already has that kind of rule, kept it")
                continue
            have_am[rule["kind"]] = have_am.get(rule["kind"], 0) + 1

            async def mkam(rule=rule):
                aid = await self.a.create_automod(rule, log_id, exempt)
                J["created"]["automod"].append(aid)
                return aid
            ops.append(Op(f"AutoMod: {rule['name']}", mkam))
        res += await self._run(ops, progress, "automod")

        # 7. rules + welcome posts -----------------------------------------------
        ops = []
        created_set = set(J["created"]["channels"])
        target_rules = rules_id or ch_ids.get(plan.get("welcome_channel"))
        if plan["rules"] and target_rules and (target_rules in created_set or mode == "replace"):
            accept = role_ids.get(plan.get("member_role")) if plan.get("rules_gate") else None

            async def post_rules():
                mid = await self.a.send(target_rules, rules=plan["rules"], server=plan.get("server_name") or "",
                                        accept_role_id=accept)
                J["created"]["messages"].append([target_rules, mid])
            ops.append(Op("post the rules", post_rules))
        wid = ch_ids.get(plan.get("welcome_channel"))
        if plan.get("welcome_message") and wid and (wid in created_set or mode == "replace"):
            async def post_welcome():
                mid = await self.a.send(wid, content=plan["welcome_message"])
                J["created"]["messages"].append([wid, mid])
            ops.append(Op("post the welcome", post_welcome))
        # self-role picker: buttons for every self-assignable role, in a self-roles / roles channel
        picks = [(role_ids[r["name"]], r["name"]) for r in plan["roles"]
                 if r.get("self_assignable") and role_ids.get(r["name"]) is not None]
        pick_ch = picker_channel(plan, ch_ids)
        if picks and pick_ch and (pick_ch in created_set or mode == "replace"):
            for i in range(0, len(picks), PICKER_MAX):
                group = picks[i:i + PICKER_MAX]

                async def post_picker(group=group, first=(i == 0)):
                    mid = await self.a.send(pick_ch, content=PICKER_TEXT if first else "More roles:",
                                            role_buttons=group)
                    J["created"]["messages"].append([pick_ch, mid])
                ops.append(Op("post the self-role picker", post_picker))
        res += await self._run(ops, progress, "messages")

        # 8. replace: remove the old layout (backed up already) --------------------
        if mode == "replace":
            new_ids = set(J["created"]["channels"]) | {log_id}
            old = [c for c in snapshot["channels"] if c["id"] not in new_ids and plain(c["name"]) != LOG_CHANNEL]
            old.sort(key=lambda c: c["type"] == "category")  # channels before their categories
            ops = []
            for c in old:
                async def rm(c=c):
                    await self.a.delete_channel(c["id"])
                    J["deleted"]["channels"].append(c)
                ops.append(Op(f"remove old {c['name']}", rm))
            keep = {r["name"].lower() for r in plan["roles"]}
            for r in snapshot["roles"]:
                if r.get("default") or r.get("managed") or r.get("above_bot") or r["name"].lower() in keep:
                    continue

                async def rmr(r=r):
                    await self.a.delete_role(r["id"])
                    J["deleted"]["roles"].append(r)
                ops.append(Op(f"remove old role {r['name']}", rmr))
            res += await self._run(ops, progress, "cleanup")

        rep.ok = sum(1 for x in res if x.ok)
        rep.failed = [(x.label, x.error) for x in res if not x.ok]
        await self._log("✅ " + rep.summary() + ("\nFailed: " + "; ".join(f"{a} ({b})" for a, b in rep.failed[:15])
                                                if rep.failed else ""))
        return rep

    # ------------------------------------------------------------------ undo
    async def undo(self, journal: dict, backup: dict | None = None, progress=None) -> Report:
        rep = Report(journal)
        if journal.get("undone"):
            raise RuntimeError("that setup was already undone")
        await self._log(f"↩️ Undo started for setup {journal.get('id')}")

        async def gone_ok(fn, *a, **kw):
            try:
                await fn(*a, **kw)
            except Exception as e:
                if getattr(e, "status", None) == 404:
                    return
                raise
        c = journal["created"]
        ops = [Op(f"remove AutoMod {i}", lambda i=i: gone_ok(self.a.delete_automod, i)) for i in c.get("automod", [])]
        ops += [Op(f"remove channel {i}", lambda i=i: gone_ok(self.a.delete_channel, i))
                for i in reversed(c.get("channels", []))]
        ops += [Op(f"remove role {i}", lambda i=i: gone_ok(self.a.delete_role, i)) for i in c.get("roles", [])]
        for e in journal.get("edited_roles", []):
            ops.append(Op(f"restore role {e['before'].get('name')}",
                          lambda e=e: gone_ok(self.a.edit_role, e["id"], **{k: v for k, v in e["before"].items()
                                                                           if k != "name"})))
        sb = journal.get("settings_before") or {}
        if sb:
            ops.append(Op("restore server settings", lambda: self.a.edit_guild(
                {k: sb[k] for k in ("verification_level", "explicit_content_filter", "default_notifications") if k in sb})))
        if journal.get("everyone_before") is not None:
            ops.append(Op("restore @everyone", lambda: self.a.edit_role(
                journal.get("everyone_id") or journal.get("guild_id"), permissions=journal["everyone_before"])))
        res = await self._run(ops, progress, "undo")

        if journal.get("mode") == "replace":
            res += await self._restore_deleted(journal, progress)
        journal["undone"] = True
        rep.ok = sum(1 for x in res if x.ok)
        rep.failed = [(x.label, x.error) for x in res if not x.ok]
        await self._log(f"↩️ Undo finished: {rep.ok} steps ok, {len(rep.failed)} failed")
        return rep

    async def _restore_deleted(self, journal, progress):
        d = journal.get("deleted", {})
        snap = await self.a.snapshot()
        names = {r["name"].lower(): r["id"] for r in snap["roles"]}
        names["@everyone"] = snap.get("everyone_id")
        old_to_new: dict = {}
        res = []
        ops = []
        for r in sorted(d.get("roles", []), key=lambda r: -r.get("position", 0)):
            async def mk(r=r):
                rid = await self.a.create_role(r["name"], r["permissions"], r["color"], r["hoist"], r["mentionable"])
                names[r["name"].lower()] = rid
                old_to_new[r["id"]] = rid
            ops.append(Op(f"recreate role {r['name']}", mk))
        res += await self._run(ops, progress, "undo")

        def ows(c):
            out = {}
            for o in c.get("overwrites", []):
                if o.get("kind") != "role":
                    continue
                rid = names["@everyone"] if o.get("default") else names.get((o.get("role_name") or "").lower())
                if rid is not None:
                    out[rid] = (o["allow"], o["deny"])
            return out
        chans = d.get("channels", [])
        cat_map = {}
        ops = []
        for c in sorted([c for c in chans if c["type"] == "category"], key=lambda c: c.get("position", 0)):
            async def mkc(c=c):
                cat_map[c["id"]] = await self.a.create_channel("category", c["name"], None, ows(c), "", 0, False, [])
            ops.append(Op(f"recreate {c['name']}", mkc))
        res += await self._run(ops, progress, "undo")
        ops = []
        for c in sorted([c for c in chans if c["type"] != "category"], key=lambda c: c.get("position", 0)):
            kind = c["type"] if c["type"] in {"text", "voice", "forum", "announcement", "stage"} else "text"

            async def mkch(c=c, kind=kind):
                await self.a.create_channel(kind, c["name"], cat_map.get(c.get("parent_id")), ows(c),
                                            c.get("topic") or "", c.get("slowmode", 0), c.get("nsfw", False), [])
            ops.append(Op(f"recreate {c['name']}", mkch))
        res += await self._run(ops, progress, "undo")
        return res
