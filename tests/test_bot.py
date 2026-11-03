"""The bot module loads, registers its commands and gates them to admins (no Discord login)."""
import types

from architect import bot


def test_commands_registered():
    b = bot.Architect()
    names = {c.name for c in b.tree.get_commands()}
    assert {"setup", "setup-undo", "template", "architect-help"} <= names
    tmpl = next(c for c in b.tree.get_commands() if c.name == "template")
    assert {c.name for c in tmpl.commands} == {"save", "load", "list"}
    setup = next(c for c in b.tree.get_commands() if c.name == "setup")
    assert setup.default_permissions.administrator
    assert {p.name for p in setup.parameters} == {"prompt", "mode", "preset", "size"}


def member(admin, uid=5):
    return types.SimpleNamespace(id=uid, guild_permissions=types.SimpleNamespace(administrator=admin))


def test_admin_gate(monkeypatch):
    monkeypatch.delenv("ARCHITECT_OWNER_IDS", raising=False)
    assert bot.is_allowed(member(True)) and not bot.is_allowed(member(False))
    monkeypatch.setenv("ARCHITECT_OWNER_IDS", "42")
    assert not bot.is_allowed(member(True, 5)) and bot.is_allowed(member(True, 42))
