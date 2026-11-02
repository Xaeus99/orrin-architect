from architect.overwrites import compute, everyone_base
from architect.permissions import bit
from architect.schema import validate_plan

PLAN, _, _ = validate_plan({
    "roles": [{"name": "Owner", "permissions": "administrator"}, {"name": "Mod", "permissions": "moderator"},
              {"name": "Tester"}, {"name": "Member"}],
    "categories": [{"name": "X", "channels": ["a"]}], "rules": ["be nice"]})
VIEW, SEND = bit("view_channel"), bit("send_messages")


def test_private_hides_from_everyone_shows_staff_and_listed():
    ow = compute({"private": True, "visible_to": ["Tester"]}, None, PLAN)
    assert ow["@everyone"][1] & VIEW and not ow["@everyone"][0] & VIEW
    for r in ("Tester", "Owner", "Mod"):
        assert ow[r][0] & VIEW and ow[r][0] & SEND
    assert "Member" not in ow


def test_read_only():
    ow = compute({"read_only": True, "writable_by": ["Tester"]}, None, PLAN)
    a, d = ow["@everyone"]
    assert a & VIEW and d & SEND and not a & SEND
    assert ow["Tester"][0] & SEND and ow["Mod"][0] & SEND


def test_channel_inherits_category_and_private_parent_stays_private():
    parent = {"private": True, "visible_to": ["Tester"]}
    ow = compute({"read_only": True}, parent, PLAN)
    assert ow["@everyone"][1] & VIEW and not ow["@everyone"][0] & VIEW
    assert ow["Tester"][0] & VIEW


def test_public_channel_in_read_only_category_can_be_private():
    ow = compute({"private": True, "visible_to": ["Tester"]}, {"read_only": True}, PLAN)
    assert ow["@everyone"][1] & VIEW and not ow["@everyone"][0] & VIEW


def test_plain_channel_no_overwrites():
    assert compute({}, None, PLAN) == {}


def test_everyone_base_gate():
    gated = everyone_base(PLAN)
    assert gated & VIEW and not gated & SEND
    open_ = everyone_base({**PLAN, "rules_gate": False})
    assert open_ & SEND and not open_ & bit("administrator")
