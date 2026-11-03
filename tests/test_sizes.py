"""Preset sizes, Discord limits, minimum-size expansion and the self-role picker (v1.1)."""
import pytest

from architect import limits as L
from architect import presets
from architect.applier import Applier, picker_channel
from architect.knowledge import DIGEST
from architect.planner import make_plan, expand_plan, resolve_size, MINIMUMS
from architect.planner.fallback import fallback_plan
from architect.planner.llm import LLMPlanner, SIZE_GUIDE
from architect.permissions import BITS
from architect.schema import validate_plan, counts
from architect.preview import plan_embed, embed_size
from tests.fake_guild import FakeGuild


def text_count(plan):
    return sum(1 for c in plan["categories"] for ch in c["channels"] if ch["type"] in {"text", "announcement"})


def vplan(raw):
    p, w, e = validate_plan(raw)
    assert not e, e
    return p, w


@pytest.mark.parametrize("name", list(presets.PRESETS))
def test_big_presets_are_rich(name):
    p, w = vplan(presets.get(name))
    assert 16 <= len(p["roles"]) <= 32, len(p["roles"])
    assert 26 <= text_count(p) <= 45, text_count(p)
    by = counts(p)["by_type"]
    assert by.get("voice", 0) >= 4 and by.get("forum", 0) >= 1
    assert not [x for x in w if "duplicate" in x or "not in the plan" in x], w
    # every category has an emoji header, like the ORRIN style
    assert all(c["emoji"] for c in p["categories"])
    # staff ladder, bots role, self-assign roles, one base member role
    names = {r["name"] for r in p["roles"]}
    assert "Bots" in names and p["member_role"] in names
    assert sum(1 for r in p["roles"] if r["self_assignable"]) >= 6
    assert sum(1 for r in p["roles"] if r["permissions"] >> BITS["administrator"] & 1) == 1


@pytest.mark.parametrize("name", list(presets.PRESETS))
def test_sizes_shrink_in_order(name):
    sizes = [vplan(presets.get(name, s))[0] for s in ("small", "normal", "big")]
    roles = [len(p["roles"]) for p in sizes]
    texts = [text_count(p) for p in sizes]
    assert roles[0] < roles[1] < roles[2] and texts[0] < texts[1] < texts[2]
    assert roles[0] <= 10 and texts[0] <= 14          # small really is small
    assert roles[1] >= 12 and texts[1] >= 18          # normal is still generous
    for p in sizes:
        _p, w = vplan(p)
        assert not [x for x in w if "not in the plan" in x], w


@pytest.mark.parametrize("name", list(presets.PRESETS))
@pytest.mark.parametrize("size", ["small", "normal", "big"])
def test_presets_inside_discord_limits(name, size):
    p, _ = vplan(presets.get(name, size))
    total = sum(len(c["channels"]) for c in p["categories"])
    assert total + len(p["categories"]) + 1 <= L.MAX_CHANNELS  # +1 for architect-log
    assert total <= L.PLAN_MAX_CHANNELS and len(p["roles"]) <= L.PLAN_MAX_ROLES <= L.MAX_ROLES
    assert len(p["categories"]) <= L.PLAN_MAX_CATEGORIES
    assert all(len(c["channels"]) <= L.MAX_CHANNELS_PER_CATEGORY for c in p["categories"])
    e = plan_embed(p)
    assert embed_size(e) <= L.MAX_EMBED_TOTAL and len(e["fields"]) <= L.MAX_EMBED_FIELDS
    assert not any(f["name"] == "…" for f in e["fields"]), "preview hides categories"


def test_tier_tags_never_leak():
    for name in presets.PRESETS:
        for size in ("small", "normal", "big"):
            raw = presets.get(name, size)
            assert all("tier" not in r for r in raw["roles"])
            for c in raw["categories"]:
                assert "tier" not in c and all("tier" not in ch for ch in c["channels"])


def test_resolve_size():
    assert resolve_size("normal", "huge clan") == "normal"
    assert resolve_size(None, "a small server for me and my friends") == "small"
    assert resolve_size(None, "gaming clan") == "big"
    assert resolve_size(None, "huge community, lots of channels") == "big"
    assert resolve_size("bogus", "") == "big"


THIN = {"server_name": "Thin", "roles": [{"name": "Boss", "permissions": "administrator"},
                                         {"name": "Member", "permissions": "member"}],
        "categories": [{"name": "Chat", "emoji": "💬", "channels": [{"name": "general"}, {"name": "pics"}]}],
        "rules": ["Be nice."], "member_role": "Member"}


@pytest.mark.parametrize("size", ["normal", "big"])
def test_expand_thin_plan_to_minimum(size):
    raw, notes = expand_plan(THIN, size)
    p, w = vplan(raw)
    mr, mt = MINIMUMS[size]
    assert len(p["roles"]) >= mr and text_count(p) >= mt
    assert notes and "expanded" in notes[0]
    # nothing the plan had is lost or renamed, and there is still exactly one full admin
    names = [r["name"] for r in p["roles"]]
    assert names[0] == "Boss" and "Member" in names
    assert sum(1 for r in p["roles"] if r["permissions"] >> BITS["administrator"] & 1) == 1
    chans = {ch["name"] for c in p["categories"] for ch in c["channels"]}
    assert {"general", "pics", "rules", "self-roles", "staff-chat"} <= chans
    staff = next(c for c in p["categories"] if c["name"] == "Staff")
    assert staff["private"] and staff["visible_to"]
    assert any(ch["type"] == "voice" for c in p["categories"] for ch in c["channels"])
    assert not [x for x in w if "duplicate" in x or "not in the plan" in x], w
    # colour/level roles go above the base member role, ping roles below it
    assert names.index("Crimson") < names.index("Member") < names.index("Announcement Ping")


def test_expand_small_leaves_plan_alone():
    raw, notes = expand_plan(THIN, "small")
    assert raw == THIN and not notes


def test_expand_keeps_rich_plans_unchanged():
    rich = presets.get("gaming")
    raw, notes = expand_plan(rich, "big")
    assert raw == rich and not notes


def test_expand_never_exceeds_limits():
    raw = {"roles": [{"name": f"R{i}"} for i in range(39)],
           "categories": [{"name": f"C{i}", "channels": [{"name": f"c{i}-{j}", "type": "voice"} for j in range(7)]}
                          for i in range(20)]}
    out, _ = expand_plan(raw, "big")
    p, w, _e = validate_plan(out)
    assert sum(len(c["channels"]) for c in p["categories"]) <= L.PLAN_MAX_CHANNELS
    assert len(p["roles"]) <= L.PLAN_MAX_ROLES


@pytest.mark.parametrize("prompt", ["gaming clan with tournaments", "support server for my app",
                                    "study group", "my youtube fans", "fantasy roleplay", "something"])
def test_fallback_big_by_default(prompt):
    p, _ = vplan(fallback_plan(prompt))
    assert len(p["roles"]) >= MINIMUMS["big"][0] and text_count(p) >= MINIMUMS["big"][1]


def test_fallback_small_when_asked():
    p, _ = vplan(fallback_plan("tiny server for me and my friends to game"))
    assert len(p["roles"]) <= 12 and text_count(p) <= 16
    p2, _ = vplan(fallback_plan("tiny server for me and my friends to game", size="big"))
    assert len(p2["roles"]) > len(p["roles"])


async def test_make_plan_expands_thin_ai_plan(monkeypatch):
    class FakeLLM:
        model = "fake"

        async def plan(self, prompt, variant=0, size="big"):
            assert size == "normal"
            return dict(THIN)
    plan, warns, used = await make_plan("a server", llm=FakeLLM(), size="normal")
    assert used == "llm:fake"
    assert len(plan["roles"]) >= 12 and text_count(plan) >= 20
    assert any("expanded" in w for w in warns)


def test_llm_prompt_has_knowledge_and_size_and_stays_short():
    llm = LLMPlanner("ollama", "qwen3:8b", "http://x")
    for size in ("small", "normal", "big"):
        sys = llm.messages("gaming clan", size=size)[0]["content"]
        assert DIGEST[:40] in sys and SIZE_GUIDE[size] in sys
        assert len(sys) < 9000, len(sys)   # ~2.5k tokens: leaves room in qwen3:8b's context for the answer
    assert "big" in llm.messages("x")[1]["content"]


async def test_self_role_picker_is_posted():
    g = FakeGuild()
    plan, _ = vplan(presets.get("gaming"))
    snap = await g.snapshot()

    async def nosleep(_):
        pass
    rep = await Applier(g, sleep=nosleep).apply(plan, snap, mode="add")
    assert not rep.failed, rep.failed
    picks = [m for m in g.messages if m["role_buttons"]]
    selfa = [r["name"] for r in plan["roles"] if r["self_assignable"]]
    got = [n for m in picks for _rid, n in m["role_buttons"]]
    assert sorted(got) == sorted(selfa)
    assert all(len(m["role_buttons"]) <= 25 for m in picks)
    assert {m["channel"] for m in picks} == {g.by_name("self-roles")[0]["id"]}
    # the picker never offers a role with real permissions
    for n in got:
        assert g.role(n)["permissions"] == 0


def test_picker_channel_choice():
    plan, _ = vplan(presets.get("software"))
    ids = {ch["name"]: i for i, ch in enumerate((ch for c in plan["categories"] for ch in c["channels"]), 1)}
    assert picker_channel(plan, ids) == ids["self-roles"]
    assert picker_channel(plan, {}) is None


def test_pick_is_safe_blocks_powerful_roles():
    import discord
    from types import SimpleNamespace
    from architect.bot import pick_is_safe

    def mk(**perms):
        return SimpleNamespace(managed=False, is_default=lambda: False, permissions=discord.Permissions(**perms))
    assert pick_is_safe(mk())
    assert pick_is_safe(mk(send_messages=True, attach_files=True))
    for p in ("administrator", "manage_roles", "ban_members", "kick_members", "mention_everyone", "moderate_members"):
        assert not pick_is_safe(mk(**{p: True})), p
    assert not pick_is_safe(SimpleNamespace(managed=True, is_default=lambda: False, permissions=discord.Permissions()))


async def test_ollama_body_turns_thinking_off_and_widens_context():
    import json as _j
    from aiohttp import web
    seen = []

    async def chat(req):
        seen.append(await req.json())
        return web.json_response({"message": {"content": _j.dumps(presets.get("study"))}})
    app = web.Application()
    app.router.add_post("/api/chat", chat)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        plan, warns, used = await make_plan("study group", llm=LLMPlanner("ollama", "qwen3:8b",
                                                                          f"http://127.0.0.1:{port}", timeout=10))
        assert used == "llm:qwen3:8b"
        assert seen[0]["think"] is False and seen[0]["options"]["num_ctx"] >= 12288
        assert "big" in seen[0]["messages"][1]["content"]
    finally:
        await runner.cleanup()


async def test_ollama_without_think_switch_retries_plain():
    import json as _j
    from aiohttp import web
    seen = []

    async def chat(req):
        b = await req.json()
        seen.append(b)
        if "think" in b:
            return web.json_response({"error": "\"m\" does not support thinking"}, status=400)
        return web.json_response({"message": {"content": _j.dumps(presets.get("study"))}})
    app = web.Application()
    app.router.add_post("/api/chat", chat)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        plan, warns, used = await make_plan("study", llm=LLMPlanner("ollama", "m", f"http://127.0.0.1:{port}",
                                                                    timeout=10))
        assert used == "llm:m" and len(seen) == 2 and "think" not in seen[1]
    finally:
        await runner.cleanup()


def test_big_plans_get_more_ai_time():
    from architect.planner.llm import SIZE_TIMEOUT
    llm = LLMPlanner("ollama", "m", "http://x", timeout=120)
    assert llm.budget("big") == SIZE_TIMEOUT["big"] >= 300
    assert llm.budget("small") == 120
    assert LLMPlanner("ollama", "m", "http://x", timeout=900).budget("big") == 900


async def test_second_setup_keeps_existing_automod():
    g = FakeGuild()
    plan, _ = vplan(presets.get("gaming", "small"))

    async def nosleep(_):
        pass
    snap = await g.snapshot()
    snap["automod"] = [{"id": 1, "name": "Old mention rule", "kind": "mention_spam"},
                       {"id": 2, "name": "Old spam rule", "kind": "spam"}]
    rep = await Applier(g, sleep=nosleep).apply(plan, snap, mode="add")
    assert not rep.failed, rep.failed
    kinds = sorted(a["kind"] for a in g.automod.values())
    assert "mention_spam" not in kinds and "spam" not in kinds
    assert sum("already has" in n for n in rep.notes) == 2
