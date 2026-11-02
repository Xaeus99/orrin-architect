import json

import pytest

from architect import presets, storage, cli
from architect import limits as L
from architect.applier import Applier
from architect.preview import plan_embed, embed_size, plan_text
from architect.schema import validate_plan
from tests.fake_guild import FakeGuild


async def nosleep(_):
    pass


@pytest.mark.parametrize("name", list(presets.PRESETS))
@pytest.mark.parametrize("mode", ["add", "replace"])
def test_embed_within_discord_limits(name, mode):
    plan, w, _ = validate_plan(presets.get(name))
    e = plan_embed(plan, mode=mode, used="fallback", warnings=w + ["x" * 500], prompt="p" * 3000)
    assert embed_size(e) <= L.MAX_EMBED_TOTAL and len(e["fields"]) <= L.MAX_EMBED_FIELDS
    assert all(len(f["value"]) <= 1024 and len(f["name"]) <= 256 for f in e["fields"])
    if mode == "replace":
        assert "REMOVED" in e["description"]


def test_huge_plan_embed_still_fits():
    cats = [{"name": f"Category {i}", "emoji": "🎮",
             "channels": [{"name": f"channel-with-a-long-name-{i}-{j}", "emoji": "💬"} for j in range(7)]}
            for i in range(20)]
    roles = [{"name": f"Role number {i}"} for i in range(40)]
    plan, w, e = validate_plan({"categories": cats, "roles": roles})
    em = plan_embed(plan)
    assert embed_size(em) <= L.MAX_EMBED_TOTAL and len(em["fields"]) <= L.MAX_EMBED_FIELDS


def test_plan_text():
    plan, w, _ = validate_plan(presets.get("orrin"))
    t = plan_text(plan, w, "preset:orrin")
    assert "📢 | IMPORTANT | 📢" in t and "╭📜︱rules" in t and "ADMINISTRATOR" in t


def test_templates_roundtrip():
    storage.save_template("My Layout!", presets.get("study"))
    assert "my-layout" in storage.list_templates()
    assert storage.load_template("my layout")["categories"]
    with pytest.raises(FileNotFoundError):
        storage.load_template("missing")
    with pytest.raises(ValueError):
        storage.template_name("!!!")


async def test_snapshot_to_template_copies_a_built_server():
    g = FakeGuild()
    plan, _, _ = validate_plan(presets.get("orrin"))
    await Applier(g, sleep=nosleep).apply(plan, await g.snapshot())
    raw = storage.snapshot_to_plan(await g.snapshot())
    copy, w, e = validate_plan(raw)
    assert not e
    assert [c["name"].lower() for c in copy["categories"]] == [c["name"].lower() for c in plan["categories"]]
    assert sum(len(c["channels"]) for c in copy["categories"]) == sum(len(c["channels"]) for c in plan["categories"])
    staff = next(c for c in copy["categories"] if c["name"].lower() == "staff")
    assert staff["private"] and "Moderator" in staff["visible_to"]
    assert next(c for c in copy["categories"] if c["name"].lower() == "important")["read_only"]
    assert copy["categories"][0]["emoji"] == "📢" and copy["categories"][0]["channels"][0]["emoji"] == "📜"
    # and it can be applied to a second server
    g2 = FakeGuild()
    rep = await Applier(g2, sleep=nosleep).apply(copy, await g2.snapshot())
    assert not rep.failed


def test_journal_latest_skips_undone():
    storage.save_journal(77, {"id": "20260101-000000", "undone": False})
    storage.save_journal(77, {"id": "20260102-000000", "undone": True})
    p, j = storage.latest_journal(77)
    assert j["id"] == "20260101-000000"
    assert storage.latest_journal(78) is None


def test_cli_dry_run(capsys):
    assert cli.main(["--no-llm", "chill", "minecraft", "server"]) == 0
    out = capsys.readouterr().out
    assert "ROLES" in out and "embed size" in out
    assert cli.main(["--preset", "roleplay", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["planner"] == "preset:roleplay" and data["plan"]["categories"]
