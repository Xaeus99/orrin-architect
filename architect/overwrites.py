"""Plan flags (private / read_only / visible_to / writable_by) -> permission overwrites.
Pure: works on role *names*; the applier maps names to ids."""
from __future__ import annotations

from .permissions import names_to_value, resolve_spec

VIEW = ["view_channel", "read_message_history", "connect"]
TALK = ["view_channel", "read_message_history", "send_messages", "add_reactions", "embed_links",
        "attach_files", "connect", "speak", "use_voice_activation", "stream",
        "create_public_threads", "send_messages_in_threads"]
NO_WRITE = ["send_messages", "create_public_threads", "create_private_threads",
            "send_messages_in_threads", "send_polls"]
READ_ONLY_ALLOW = ["view_channel", "read_message_history", "add_reactions"]


def _v(names):
    return names_to_value(names)[0]


def staff_names(plan: dict) -> list[str]:
    return [r["name"] for r in plan["roles"] if r.get("staff")]


def compute(scope: dict, parent: dict | None, plan: dict) -> dict[str, tuple[int, int]]:
    """Return {"@everyone" | role_name: (allow, deny)} for a category (parent=None) or a channel.
    A channel starts from its category's overwrites (so it stays in sync) and adds its own."""
    ow: dict[str, tuple[int, int]] = {}
    staff = staff_names(plan)

    def add(target, allow=(), deny=()):
        a, d = ow.get(target, (0, 0))
        av, dv = _v(allow), _v(deny)
        ow[target] = ((a | av) & ~dv, (d | dv) & ~av)   # the later word wins

    layers = ([parent] if parent else []) + [scope]
    for layer in layers:
        if layer.get("private"):
            add("@everyone", deny=["view_channel", "connect"])
            for r in list(dict.fromkeys(layer.get("visible_to", []) + staff)):
                if r != "@everyone":
                    add(r, allow=TALK)
        if layer.get("read_only"):
            add("@everyone", allow=[] if layer.get("private") or (parent and parent.get("private")) else READ_ONLY_ALLOW,
                deny=NO_WRITE)
            for r in list(dict.fromkeys(layer.get("writable_by", []) + staff)):
                if r != "@everyone":
                    add(r, allow=["send_messages", "embed_links", "attach_files", "create_public_threads",
                                  "send_messages_in_threads", "mention_everyone"])
    return ow


def everyone_base(plan: dict) -> int:
    """Server-wide @everyone permissions. With the rules gate on, new people can read and react
    but can't chat until they accept the rules (which grants the member role)."""
    return resolve_spec("restricted" if plan.get("rules_gate") else "member")[0]
