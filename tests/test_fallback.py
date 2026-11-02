import pytest

from architect.planner import make_plan
from architect.planner.fallback import fallback_plan, score, extract_name
from architect.schema import validate_plan


@pytest.mark.parametrize("prompt,base", [
    ("competitive valorant clan with tournaments", "gaming"),
    ("support server for my python app beta testers", "software"),
    ("study group for AP exams and homework help", "study"),
    ("fan server for my youtube channel and twitch streams", "creator"),
    ("medieval fantasy roleplay with lore and characters", "roleplay"),
    ("a server for ORRIN", "orrin"),
    ("something", "software"),
    ("", "software"),
])
def test_routes_to_base(prompt, base):
    assert fallback_plan(prompt)["source"] == f"fallback:{base}"


def test_deterministic_and_variants_differ():
    a, b = fallback_plan("gaming clan with music"), fallback_plan("gaming clan with music")
    assert a == b
    c = fallback_plan("gaming clan with music", variant=1)
    assert c != a and c["style"] != a.get("style")


def test_blend_and_modules():
    p = fallback_plan("minecraft server for my youtube fans with art and music")
    names = [c["name"] for c in p["categories"]]
    assert "Music" in names and "Art" in names
    plan, w, e = validate_plan(p)
    assert not e and not [x for x in w if "duplicate" in x]


def test_name_and_style_words():
    assert extract_name('a clan called "Night Owls"') == "Night Owls"
    assert extract_name("server named Pixel Forge for artists") == "Pixel Forge"
    p = fallback_plan("minimal study server for friends")
    assert p["style"] == {"emoji": False, "tree": False}
    assert p["settings"]["verification_level"] == "low" and p["rules_gate"] is False


def test_score_whole_words():
    assert score("rp")["roleplay"] >= 1 and score("grape")["roleplay"] == 0


@pytest.mark.parametrize("v", range(5))
async def test_make_plan_always_valid(v):
    plan, warns, used = await make_plan("trading card game community with market and events", variant=v,
                                        server_name="Cards")
    assert used == "fallback" and plan["categories"] and "Cards" in plan["welcome_message"]
