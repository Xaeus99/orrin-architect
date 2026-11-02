import pytest

from architect import limits as L
from architect.schema import validate_plan, slug, clean_emoji, parse_color, assert_valid, PlanError
from architect import presets
from architect.render import rendered, channel_name, category_name, plain


def base(**kw):
    d = {"roles": [{"name": "Owner", "permissions": "administrator"}, {"name": "Member"}],
         "categories": [{"name": "Main", "emoji": "💬", "channels": [{"name": "General Chat"}]}]}
    d.update(kw)
    return d


def test_minimal_plan_ok():
    plan, w, e = validate_plan(base())
    assert not e
    assert plan["categories"][0]["channels"][0]["name"] == "general-chat"
    assert plan["roles"][0]["staff"] and not plan["roles"][1]["staff"]


@pytest.mark.parametrize("raw,out", [("General Chat!!", "general-chat"), ("#rules", "rules"),
                                     ("  Café ☕ talk ", "café-talk"), ("", "channel"), ("a" * 300, "a" * 60)])
def test_slug(raw, out):
    assert slug(raw) == out


def test_emoji_and_color():
    assert clean_emoji("🎮") == "🎮" and clean_emoji("rocket") == "" and clean_emoji(":smile:") == ""
    assert parse_color("#ff0000") == 0xFF0000 and parse_color("0F0") == 0x00FF00
    assert parse_color("purple") == 0xA855F7 and parse_color("nope") == 0 and parse_color(0x123456) == 0x123456


def test_errors():
    assert validate_plan([])[2]
    assert validate_plan({"roles": [], "categories": []})[2]
    with pytest.raises(PlanError):
        assert_valid({"categories": [{"name": "x", "channels": []}]})


def test_repairs():
    raw = base(roles=[{"name": "@everyone"}, {"name": "A", "permissions": "administrator"},
                      {"name": "B", "permissions": "administrator"}, {"name": "C", "permissions": "administrator"},
                      {"name": "Pingme", "permissions": ["kick", "send"], "self_assignable": True},
                      {"name": "A"}],
               categories=[{"name": "X", "emoji": "x", "channels": [
                   {"name": "t", "type": "weird", "topic": "z" * 5000, "slowmode": 99999},
                   {"name": "t"}, {"name": "Voice Room", "type": "vc"},
                   {"name": "f", "type": "forum", "tags": ["a" * 50] * 30}]}])
    plan, w, e = validate_plan(raw)
    assert not e
    names = [r["name"] for r in plan["roles"]]
    assert "@everyone" not in names and names.count("A") == 1
    admins = [r for r in plan["roles"] if r["permissions"] & 8]
    assert len(admins) == 2
    ping = next(r for r in plan["roles"] if r["name"] == "Pingme")
    assert not ping["permissions"] & 2 and ping["permissions"] & (1 << 11)
    chans = plan["categories"][0]["channels"]
    assert [c["name"] for c in chans] == ["t", "Voice Room", "f"]
    assert chans[0]["type"] == "text" and len(chans[0]["topic"]) == L.MAX_TOPIC and chans[0]["slowmode"] == L.MAX_SLOWMODE
    assert chans[1]["type"] == "voice"
    assert len(chans[2]["tags"]) == 1 and len(chans[2]["tags"][0]) <= L.MAX_FORUM_TAG_NAME
    assert plan["categories"][0]["emoji"] == ""


def test_plan_size_caps():
    cats = [{"name": f"C{i}", "channels": [{"name": f"c{i}-{j}"} for j in range(60)]} for i in range(30)]
    roles = [{"name": f"R{i}"} for i in range(80)]
    plan, w, e = validate_plan({"roles": roles, "categories": cats})
    assert not e
    assert len(plan["roles"]) <= L.PLAN_MAX_ROLES + 1
    assert sum(len(c["channels"]) for c in plan["categories"]) <= L.PLAN_MAX_CHANNELS
    assert all(len(c["channels"]) <= L.MAX_CHANNELS_PER_CATEGORY for c in plan["categories"])
    assert len(plan["categories"]) <= L.PLAN_MAX_CATEGORIES


def test_automod_caps():
    am = [{"kind": "spam"}, {"kind": "spam"}, {"kind": "mentions", "mention_limit": 999},
          {"kind": "bad words"}] + [{"kind": "keyword", "keywords": ["x" * 100, "y"]}] * 8 + [
          {"kind": "keyword", "keywords": []}, {"kind": "laser"}]
    plan, w, e = validate_plan(base(automod=am))
    kinds = [a["kind"] for a in plan["automod"]]
    assert kinds.count("spam") == 1 and kinds.count("keyword") == L.MAX_AUTOMOD_KEYWORD_RULES
    assert kinds.count("profanity") == 1
    m = next(a for a in plan["automod"] if a["kind"] == "mention_spam")
    assert m["mention_limit"] == 50
    k = next(a for a in plan["automod"] if a["kind"] == "keyword")
    assert all(len(x) <= L.MAX_AUTOMOD_KEYWORD_LEN for x in k["keywords"])


def test_rules_gate_adds_member_role():
    plan, w, e = validate_plan({"roles": [{"name": "Boss", "permissions": "administrator"}],
                                "categories": [{"name": "Main", "channels": ["rules", "chat"]}],
                                "rules": ["1. Be nice", "2) No spam"]})
    assert plan["rules_gate"] and plan["member_role"] == "Member"
    assert plan["rules"] == ["Be nice", "No spam"] and plan["rules_channel"] == "rules"
    plan2, _, _ = validate_plan(base(rules_gate=True))
    assert not plan2["rules_gate"]  # no rules -> nothing to accept


def test_unknown_role_refs_warn():
    raw = base()
    raw["categories"][0]["private"] = True
    raw["categories"][0]["visible_to"] = ["Ghost", "member"]
    plan, w, e = validate_plan(raw)
    assert plan["categories"][0]["visible_to"] == ["Ghost", "Member"]
    assert any("Ghost" in x for x in w)


@pytest.mark.parametrize("name", list(presets.PRESETS))
def test_presets_valid_and_names_fit(name):
    plan, w, e = validate_plan(presets.get(name))
    assert not e, e
    assert not [x for x in w if "not in the plan" in x], w
    for cdisp, chans, cat in rendered(plan):
        assert 1 <= len(cdisp) <= L.MAX_NAME
        for disp, ch in chans:
            assert 1 <= len(disp) <= L.MAX_NAME
            if ch["type"] in ("text", "forum", "announcement"):
                assert " " not in disp
            assert plain(disp) == plain(ch["name"])


def test_render_style():
    st = {"category": "{emoji} | {NAME} | {emoji}", "separator": "︱", "tree": True, "emoji": True}
    assert category_name({"name": "Important", "emoji": "📢"}, st) == "📢 | IMPORTANT | 📢"
    ch = {"name": "rules", "emoji": "📜", "type": "text"}
    assert channel_name(ch, st, 0, 3) == "╭📜︱rules"
    assert channel_name(ch, st, 1, 3) == "┊📜︱rules"
    assert channel_name(ch, st, 2, 3) == "╰📜︱rules"
    assert channel_name({"name": "Lounge", "emoji": "🔊", "type": "voice"}, st) == "🔊 | Lounge"
    assert channel_name(ch, {**st, "emoji": False}) == "rules"
    assert plain("📢 | IMPORTANT | 📢") == "important" and plain("╭📜︱rules") == "rules"
