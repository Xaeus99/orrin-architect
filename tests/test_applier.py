import pytest

from architect import presets
from architect.applier import Applier, CapacityError, check_capacity, LOG_CHANNEL
from architect.permissions import bit
from architect.schema import validate_plan
from tests.fake_guild import FakeGuild


async def nosleep(_):
    pass


def plan_of(name="software"):
    p, w, e = validate_plan(presets.get(name))
    assert not e
    return p


async def apply(g, plan, mode="add"):
    snap = await g.snapshot()
    return await Applier(g, sleep=nosleep).apply(plan, snap, mode=mode, backup_file="b.json")


async def test_full_build_on_empty_server():
    g = FakeGuild(channels=[{"name": "general"}, {"name": "Text Channels", "type": "category"}])
    plan = plan_of()
    rep = await apply(g, plan)
    assert not rep.failed, rep.failed
    n_ch = sum(len(c["channels"]) for c in plan["categories"])
    assert len(rep.journal["created"]["channels"]) == len(plan["categories"]) + n_ch
    assert len(rep.journal["created"]["roles"]) == len(plan["roles"])
    assert g.community and g.settings["verification_level"] == 2 and g.settings["default_notifications"] == 1
    assert g.by_name(LOG_CHANNEL) and g.by_name("general")  # add mode keeps old channels
    ann = g.by_name("announcements")[0]
    assert ann["type"] == "announcement"
    assert g.by_name("stage")[0]["type"] == "stage"
    # roles ordered under the bot, in plan order
    pos = [g.role(r["name"])["position"] for r in plan["roles"]]
    assert pos == sorted(pos, reverse=True) and max(pos) < g.bot_role["position"]
    # rules posted with an accept button for Member; welcome posted
    rules = [m for m in g.messages if m["rules"]]
    assert rules and rules[0]["accept_role_id"] == g.role("Member")["id"]
    assert any(m["content"] for m in g.messages)
    # AutoMod logs to architect-log and exempts staff
    log_id = g.by_name(LOG_CHANNEL)[0]["id"]
    assert len(g.automod) == 4 and all(a["log"] == log_id for a in g.automod.values())
    assert g.role("Moderator")["id"] in next(iter(g.automod.values()))["exempt"]
    # gate: @everyone can read, not chat
    assert g.everyone["permissions"] & bit("view_channel") and not g.everyone["permissions"] & bit("send_messages")


async def test_private_category_overwrites_resolved_to_ids():
    g = FakeGuild()
    await apply(g, plan_of())
    staff = [c for c in g.channels.values() if c["type"] == "category" and "STAFF" in c["name"]][0]
    ev = next(o for o in staff["overwrites"] if o["id"] == 1)
    assert ev["deny"] & bit("view_channel")
    allowed = {o["role_name"] for o in staff["overwrites"] if o["allow"] & bit("view_channel")}
    assert {"Owner", "Admin", "Moderator"} <= allowed and "Member" not in allowed
    testers = g.by_name("testers")[0]
    assert "Tester" in {o["role_name"] for o in testers["overwrites"] if o["allow"] & bit("view_channel")}


async def test_add_mode_skips_existing_and_reuses_roles():
    g = FakeGuild(channels=[{"name": "rules"}, {"name": "💬 | COMMUNITY | 💬", "type": "category"}],
                  roles=[{"name": "Moderator", "permissions": 123}])
    rep = await apply(g, plan_of())
    assert len(g.by_name("rules")) == 1 and len(g.by_name("community")) == 1
    assert g.role("Moderator")["permissions"] == 123  # add mode never edits existing roles
    assert not [m for m in g.messages if m["rules"]]  # rules channel wasn't ours: no post
    assert not rep.failed


async def test_without_community_downgrades():
    g = FakeGuild(fail_on=lambda op, name: op == "enable_community")
    rep = await apply(g, plan_of())
    assert g.by_name("announcements")[0]["type"] == "text"
    assert g.by_name("stage")[0]["type"] == "voice"
    assert any("enable" in a or "Community" in a for a, _ in rep.failed)
    assert any("stage" in n for n in rep.notes)


async def test_one_failure_does_not_stop_the_build():
    g = FakeGuild(fail_on=lambda op, name: "media" in name)
    rep = await apply(g, plan_of())
    assert len(rep.failed) == 1 and "media" in rep.failed[0][0]
    assert g.by_name("lobby") and g.by_name("help")


async def test_rate_limits_are_retried():
    g = FakeGuild(flaky=3)
    rep = await apply(g, plan_of("study"))
    assert not rep.failed


def test_capacity_limits():
    plan = plan_of()
    snap = {"roles": [{"name": f"r{i}"} for i in range(245)], "channels": []}
    with pytest.raises(CapacityError):
        check_capacity(plan, snap, "add")
    snap = {"roles": [], "channels": [{"name": f"c{i}", "type": "text", "id": i} for i in range(480)]}
    with pytest.raises(CapacityError):
        check_capacity(plan, snap, "add")
    # replace counts the peak too (new built before old removed)
    with pytest.raises(CapacityError):
        check_capacity(plan, snap, "replace")
    snap = {"roles": [], "channels": [{"name": f"c{i}", "type": "text", "id": i} for i in range(10)]}
    t = check_capacity(plan, snap, "add")
    assert t["peak_channels"] < 500


async def test_capacity_checked_before_any_change():
    g = FakeGuild(channels=[{"name": f"c{i}"} for i in range(495)])
    with pytest.raises(CapacityError):
        await apply(g, plan_of())
    assert not [c for c in g.calls if c[0].startswith("create")]


async def test_replace_then_undo_restores_layout():
    g = FakeGuild(community=False, channels=[{"name": "old-chat"}, {"name": "Old Cat", "type": "category"}],
                  roles=[{"name": "OldRole", "permissions": 5, "color": 0x123456},
                         {"name": "Moderator", "permissions": 7}])
    before = await g.snapshot()
    rep = await apply(g, plan_of(), mode="replace")
    assert not g.by_name("old-chat") and not g.role("OldRole")
    assert g.role("Moderator")["permissions"] != 7  # replace updates same-name roles
    assert g.by_name(LOG_CHANNEL)
    assert g.role("ORRIN Architect")  # bot's managed role untouched
    rep2 = await Applier(g, sleep=nosleep).undo(rep.journal, before)
    assert not rep2.failed, rep2.failed
    assert g.by_name("old-chat") and g.by_name("old-cat")
    assert g.role("OldRole")["color"] == 0x123456
    assert g.role("Moderator")["permissions"] == 7
    assert not g.by_name("lobby") and not g.role("Tester")
    assert g.settings["verification_level"] == 0
    assert rep.journal["undone"]
    with pytest.raises(RuntimeError):
        await Applier(g, sleep=nosleep).undo(rep.journal, before)


async def test_undo_add_mode_removes_only_what_it_made():
    g = FakeGuild(channels=[{"name": "keep-me"}])
    rep = await apply(g, plan_of("gaming"))
    await Applier(g, sleep=nosleep).undo(rep.journal)
    assert g.by_name("keep-me") and g.by_name(LOG_CHANNEL)
    assert set(c["name"] for c in g.channels.values()) == {"keep-me", LOG_CHANNEL}
    assert set(r["name"] for r in g.roles.values()) == {"@everyone", "ORRIN Architect"}
    assert not g.automod


async def test_undo_tolerates_things_already_deleted():
    g = FakeGuild()
    rep = await apply(g, plan_of("study"))
    first = rep.journal["created"]["channels"][-1]
    await g.delete_channel(first)
    rep2 = await Applier(g, sleep=nosleep).undo(rep.journal)
    assert not rep2.failed


async def test_progress_and_log_called():
    g = FakeGuild()
    seen, logs = [], []

    async def prog(phase, p):
        seen.append(phase)

    async def log(m):
        logs.append(m)
    snap = await g.snapshot()
    await Applier(g, sleep=nosleep, log=log).apply(plan_of("creator"), snap, progress=prog)
    assert {"roles", "categories", "channels", "settings", "automod", "messages"} <= set(seen)
    assert logs[0].startswith("🏗️") and logs[-1].startswith("✅")
