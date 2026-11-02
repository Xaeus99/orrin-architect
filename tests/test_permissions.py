import discord
import pytest

from architect import permissions as P


def test_bits_match_discord_py():
    alias = {"use_voice_activation": "use_voice_activation", "manage_expressions": "manage_expressions"}
    for name, bit in P.BITS.items():
        flag = getattr(discord.Permissions, alias.get(name, name))
        assert flag.flag == 1 << bit, name


@pytest.mark.parametrize("word,canon", [("Send Messages", "send_messages"), ("send", "send_messages"),
                                        ("ADMIN", "administrator"), ("view-channel", "view_channel"),
                                        ("timeout", "moderate_members"), ("nonsense", None)])
def test_canonical(word, canon):
    assert P.canonical(word) == canon


def test_preset_ladder():
    v = {k: P.resolve_spec(k)[0] for k in ("member", "helper", "moderator", "admin")}
    assert v["member"] & v["helper"] == v["member"]
    assert v["helper"] & v["moderator"] == v["helper"]
    assert v["moderator"] & v["admin"] == v["moderator"]
    assert not v["admin"] >> P.BITS["administrator"] & 1
    assert P.resolve_spec("administrator")[0] == 8


def test_spec_shapes_and_unknowns():
    v, preset, w = P.resolve_spec({"preset": "member", "add": ["manage_events"], "remove": ["attach_files", "bogus"]})
    assert preset == "member" and v & P.bit("manage_events") and not v & P.bit("attach_files")
    assert any("bogus" in x for x in w)
    v, preset, w = P.resolve_spec(["send", "react", "zzz"])
    assert v == P.bit("send_messages") | P.bit("add_reactions") and w
    v, preset, w = P.resolve_spec("superuser")
    assert preset == "member" and w
    assert P.resolve_spec(None)[1] == "member"


def test_strip_dangerous_and_staff():
    v = P.resolve_spec("admin")[0] | 8
    v2, removed = P.strip_dangerous(v)
    assert "administrator" in removed and "ban_members" in removed
    assert not P.is_staff_value(v2) and P.is_staff_value(v)
    assert P.value_to_names(P.bit("speak") | P.bit("connect")) == ["connect", "speak"]
