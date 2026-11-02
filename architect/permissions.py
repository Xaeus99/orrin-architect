"""Permission names -> Discord permission bits, plus the role permission sets.

Pure Python (no discord.py import) so it can be unit-tested and used by the dry-run CLI.
Bit numbers are Discord's (https://discord.com/developers/docs/topics/permissions).
"""
from __future__ import annotations

BITS: dict[str, int] = {
    "create_instant_invite": 0, "kick_members": 1, "ban_members": 2, "administrator": 3,
    "manage_channels": 4, "manage_guild": 5, "add_reactions": 6, "view_audit_log": 7,
    "priority_speaker": 8, "stream": 9, "view_channel": 10, "send_messages": 11,
    "send_tts_messages": 12, "manage_messages": 13, "embed_links": 14, "attach_files": 15,
    "read_message_history": 16, "mention_everyone": 17, "use_external_emojis": 18,
    "view_guild_insights": 19, "connect": 20, "speak": 21, "mute_members": 22,
    "deafen_members": 23, "move_members": 24, "use_voice_activation": 25,
    "change_nickname": 26, "manage_nicknames": 27, "manage_roles": 28, "manage_webhooks": 29,
    "manage_expressions": 30, "use_application_commands": 31, "request_to_speak": 32,
    "manage_events": 33, "manage_threads": 34, "create_public_threads": 35,
    "create_private_threads": 36, "use_external_stickers": 37, "send_messages_in_threads": 38,
    "use_embedded_activities": 39, "moderate_members": 40, "use_soundboard": 42,
    "create_expressions": 43, "create_events": 44, "use_external_sounds": 45,
    "send_voice_messages": 46, "send_polls": 49, "use_external_apps": 50,
}

# friendly words an LLM (or a person) might write -> canonical names
ALIASES: dict[str, str] = {
    "admin": "administrator", "view": "view_channel", "read": "view_channel",
    "read_messages": "view_channel", "see": "view_channel", "send": "send_messages",
    "write": "send_messages", "talk": "send_messages", "chat": "send_messages",
    "react": "add_reactions", "reactions": "add_reactions", "history": "read_message_history",
    "embed": "embed_links", "links": "embed_links", "attach": "attach_files", "files": "attach_files",
    "upload": "attach_files", "external_emojis": "use_external_emojis", "emojis": "use_external_emojis",
    "kick": "kick_members", "ban": "ban_members", "timeout": "moderate_members",
    "mute": "mute_members", "deafen": "deafen_members", "move": "move_members",
    "voice_activity": "use_voice_activation", "use_vad": "use_voice_activation",
    "manage_emojis": "manage_expressions", "manage_emojis_and_stickers": "manage_expressions",
    "manage_guild_expressions": "manage_expressions", "manage_server": "manage_guild",
    "audit_log": "view_audit_log", "slash_commands": "use_application_commands",
    "app_commands": "use_application_commands", "threads": "create_public_threads",
    "public_threads": "create_public_threads", "private_threads": "create_private_threads",
    "send_in_threads": "send_messages_in_threads", "activities": "use_embedded_activities",
    "soundboard": "use_soundboard", "polls": "send_polls", "voice_messages": "send_voice_messages",
    "invite": "create_instant_invite", "create_invite": "create_instant_invite",
    "nickname": "change_nickname", "manage_nickname": "manage_nicknames", "events": "create_events",
    "pin": "manage_messages", "delete_messages": "manage_messages", "insights": "view_guild_insights",
    "stickers": "use_external_stickers", "external_stickers": "use_external_stickers",
    "priority": "priority_speaker", "tts": "send_tts_messages", "webhooks": "manage_webhooks",
    "mention_all": "mention_everyone",
}

# never on @everyone, whatever a plan says
DANGEROUS = frozenset({
    "administrator", "manage_guild", "manage_roles", "manage_channels", "kick_members",
    "ban_members", "manage_messages", "mention_everyone", "manage_webhooks", "moderate_members",
    "manage_nicknames", "manage_expressions", "manage_events", "manage_threads",
    "view_audit_log", "mute_members", "deafen_members", "move_members", "view_guild_insights",
})

MEMBER = [
    "view_channel", "send_messages", "add_reactions", "embed_links", "attach_files",
    "read_message_history", "use_external_emojis", "use_external_stickers", "connect", "speak",
    "use_voice_activation", "stream", "change_nickname", "use_application_commands",
    "request_to_speak", "create_public_threads", "send_messages_in_threads",
    "use_embedded_activities", "send_voice_messages", "send_polls", "use_soundboard",
    "use_external_sounds", "create_instant_invite",
]
HELPER = MEMBER + ["manage_threads", "create_private_threads"]
MODERATOR = HELPER + [
    "kick_members", "manage_messages", "moderate_members", "view_audit_log", "manage_nicknames",
    "mute_members", "deafen_members", "move_members", "mention_everyone", "priority_speaker",
]
ADMIN = MODERATOR + [
    "ban_members", "manage_channels", "manage_roles", "manage_guild", "manage_webhooks",
    "manage_expressions", "create_expressions", "manage_events", "create_events",
    "view_guild_insights",
]

PRESETS: dict[str, list[str]] = {
    "administrator": ["administrator"],   # full power: use for the top role only
    "admin": ADMIN,                       # everything except the Administrator bit
    "moderator": MODERATOR,
    "helper": HELPER,
    "member": MEMBER,
    "restricted": ["view_channel", "read_message_history", "add_reactions", "connect",
                   "use_application_commands"],
    "readonly": ["view_channel", "read_message_history"],
    "bot": ["administrator"],
    "cosmetic": [],                       # colour/badge role, permissions come from Member
    "none": [],
}
# which presets count as "staff" (they see private staff channels)
STAFF_PRESETS = {"administrator", "admin", "moderator"}


class PermissionError_(ValueError):
    pass


def canonical(name: str) -> str | None:
    """'Send Messages' / 'send' / 'SEND_MESSAGES' -> 'send_messages'; None if unknown."""
    if not isinstance(name, str):
        return None
    k = name.strip().lower().replace(" ", "_").replace("-", "_")
    if k in BITS:
        return k
    return ALIASES.get(k)


def names_to_value(names) -> tuple[int, list[str]]:
    """Return (bitfield, unknown_names)."""
    value, unknown = 0, []
    for n in names or []:
        c = canonical(n)
        if c is None:
            unknown.append(str(n))
        else:
            value |= 1 << BITS[c]
    return value, unknown


def value_to_names(value: int) -> list[str]:
    return [n for n, b in sorted(BITS.items(), key=lambda kv: kv[1]) if value >> b & 1]


def resolve_spec(spec) -> tuple[int, str | None, list[str]]:
    """A role's permission spec -> (value, preset_name_or_None, warnings).

    Accepted shapes: "moderator" | ["send_messages", ...] |
    {"preset": "member", "add": [...], "remove": [...]}
    """
    warns: list[str] = []
    preset = None
    if spec is None:
        spec = "member"
    if isinstance(spec, str):
        key = spec.strip().lower()
        if key in PRESETS:
            preset = key
            v, _ = names_to_value(PRESETS[key])
            return v, preset, warns
        v, unk = names_to_value([spec])
        if unk:
            warns.append(f"unknown permission set '{spec}', used 'member'")
            v, _ = names_to_value(MEMBER)
            preset = "member"
        return v, preset, warns
    if isinstance(spec, dict):
        base = str(spec.get("preset", "none")).lower()
        if base not in PRESETS:
            warns.append(f"unknown preset '{base}', used 'none'")
            base = "none"
        preset = base
        v, _ = names_to_value(PRESETS[base])
        add, unk1 = names_to_value(spec.get("add", []))
        rem, unk2 = names_to_value(spec.get("remove", []))
        for u in unk1 + unk2:
            warns.append(f"unknown permission '{u}' ignored")
        return (v | add) & ~rem, preset, warns
    if isinstance(spec, (list, tuple)):
        v, unk = names_to_value(spec)
        for u in unk:
            warns.append(f"unknown permission '{u}' ignored")
        return v, None, warns
    warns.append("unreadable permissions, used 'member'")
    v, _ = names_to_value(MEMBER)
    return v, "member", warns


def strip_dangerous(value: int) -> tuple[int, list[str]]:
    removed = [n for n in DANGEROUS if value >> BITS[n] & 1]
    for n in removed:
        value &= ~(1 << BITS[n])
    return value, sorted(removed)


def is_staff_value(value: int) -> bool:
    return bool(value >> BITS["administrator"] & 1 or value >> BITS["manage_guild"] & 1
                or (value >> BITS["kick_members"] & 1 and value >> BITS["manage_messages"] & 1))


def bit(name: str) -> int:
    return 1 << BITS[canonical(name)]
