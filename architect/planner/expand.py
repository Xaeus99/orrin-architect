"""Minimum-size expansion for thin plans (the AI's or the built-in planner's).

Discord-server guides agree on a common skeleton (see knowledge/server_design.md): an info
category, a community category, events, feedback, a private staff area and voice; a staff
ladder, a bots role, level roles, self-assign colour/ping/pronoun roles. When a plan is thinner
than the chosen size asks for, ``expand_plan`` tops it up from that skeleton without touching
anything the plan already has. Works on raw plans (before validation)."""
from __future__ import annotations

import copy
import re

from .. import limits as L
from .. import presets as P

SIZES = P.SIZES
# (min roles, min text channels) per size; text = text + announcement channels
MINIMUMS = {"small": (0, 0), "normal": (12, 20), "big": (16, 26)}
SMALL_WORDS = ("small server", "tiny", "just friends", "just us", "few friends", "private group",
               "small group", "minimal", "simple server", "for friends", "me and my friends", "small")
BIG_WORDS = ("big server", "huge", "large", "massive", "big community", "lots of channels", "a lot of channels")

STAFF_PERMS = {"administrator", "admin", "moderator", "helper"}
TEXTLIKE = {"text", "announcement", "news", "announcements", "chat"}


def resolve_size(size: str | None, prompt: str = "") -> str:
    """An explicit size wins; otherwise words in the prompt; otherwise big."""
    if size in SIZES:
        return size
    low = " " + (prompt or "").lower() + " "
    if any(w in low for w in BIG_WORDS):
        return "big"
    if any(re.search(rf"\b{re.escape(w)}\b", low) for w in SMALL_WORDS):
        return "small"
    return "big"


def _key(name) -> str:
    return re.sub(r"[\s_]+", "-", str(name or "").strip().lower())


def _role_name(r) -> str:
    return r if isinstance(r, str) else str((r or {}).get("name", ""))


def _perm(r) -> str:
    if not isinstance(r, dict):
        return ""
    p = r.get("permissions", r.get("preset"))
    if isinstance(p, dict):
        p = p.get("preset", "")
    return p if isinstance(p, str) else ""


def _strip(item: dict) -> dict:
    d = copy.deepcopy(item)
    d.pop("tier", None)
    return d


# ------------------------------------------------------------------ role pool
def _role_pool():
    staff = [P.role("Moderator", "#3B82F6", "moderator", hoist=True, mentionable=True),
             P.role("Trial Mod", "#60A5FA", "helper", hoist=True, mentionable=True)]
    bots = [P.role("Bots", "#5865F2", "member", hoist=True)]
    colours = [P.role(n, c, "cosmetic", self_assignable=True) for n, c in P.COLOURS[:6]]
    levels = [_strip(r) for r in P.level_roles()]
    pings = [P.role("Announcement Ping", "#94A3B8", "cosmetic", mentionable=True, self_assignable=True),
             P.role("Event Ping", "#F97316", "cosmetic", mentionable=True, self_assignable=True),
             P.role("Giveaway Ping", "#EC4899", "cosmetic", mentionable=True, self_assignable=True)]
    ident = [_strip(r) for r in P.pronoun_roles()]
    # priority order of what gets added first, with where it goes
    order = ([("staff", r) for r in staff] + [("staff", r) for r in bots] +
             [("mid", r) for r in levels[2:]] + [("mid", r) for r in colours[:4]] +
             [("end", r) for r in pings[:2]] + [("mid", r) for r in levels[:2]] +
             [("end", pings[2])] + [("mid", r) for r in colours[4:]] + [("end", r) for r in ident])
    return order


# ------------------------------------------------------------------ channel pool
# kit name -> (category name, emoji, aliases, flags)
KITS = {
    "info": ("Important", "📢", {"important", "info", "information", "start here", "start-here", "gateway",
                                "welcome", "server info", "read me", "readme", "announcements", "news"},
             {"read_only": True}),
    "community": ("Community", "💬", {"community", "general", "chat", "social", "lounge", "hangout",
                                     "main", "fan zone", "out of character", "text channels", "study"}, {}),
    "events": ("Events", "🎉", {"events", "event", "giveaways", "activities"}, {}),
    "feedback": ("Feedback", "💡", {"feedback", "suggestions", "support", "help"}, {}),
    "staff": ("Staff", "🔒", {"staff", "moderation", "mods", "admin", "staff only", "team"}, {"private": True}),
    "voice": ("Voice", "🔊", {"voice", "voice channels", "vc", "voice chat"}, {}),
}


def _chan_pool():
    c = P.ch
    return [
        ("info", c("rules", "📜", topic="Read these first.")),
        ("info", c("announcements", "🔔", "announcement", "Official news.")),
        ("info", c("welcome", "👋", topic="Say hi to new members.")),
        ("community", c("general", "💬", topic="Talk about anything. Keep it friendly.", slowmode=2)),
        ("info", c("self-roles", "🎨", topic="Tap the buttons to pick your colour, pings and more.")),
        ("info", c("roles-info", "🪪", topic="What every role means and how to earn it.")),
        ("community", c("introductions", "🙋", topic="Tell us who you are.")),
        ("community", c("media", "📸", topic="Pictures, clips and screenshots (SFW).", slowmode=10)),
        ("community", c("bot-commands", "🤖", topic="Use bot commands here.")),
        ("staff", c("staff-chat", "💬", topic="Private: staff only.")),
        ("staff", c("mod-log", "📋", topic="Private: AutoMod alerts and staff actions.")),
        ("community", c("memes", "😂", topic="Memes (SFW).")),
        ("events", c("events", "📅", topic="Upcoming events.", read_only=True)),
        ("feedback", c("server-feedback", "📣", topic="Tell staff what to improve.")),
        ("info", c("faq", "❓", topic="Answers to the questions everyone asks.")),
        ("community", c("off-topic", "🌀", topic="Anything that doesn't fit elsewhere.")),
        ("events", c("giveaways", "🎁", topic="Giveaways and contests.", read_only=True)),
        ("staff", c("reports", "🚨", topic="Private: user reports and how they were handled.")),
        ("community", c("question-of-the-day", "🗳️", topic="One question a day. Answer in a thread.")),
        ("events", c("event-chat", "🎟️", topic="Talk about the current event.")),
        ("info", c("server-guide", "🧭", topic="Where everything is and how the server works.")),
        ("staff", c("staff-announcements", "📌", topic="Private: staff news and decisions.")),
        ("community", c("counting", "🔢", topic="Count up one number at a time.")),
        ("community", c("pets", "🐾", topic="Pet pics.")),
        ("events", c("polls", "📊", topic="Vote on what happens next.", read_only=True)),
        ("community", c("music-share", "🎵", topic="Share tracks.")),
        ("community", c("art-share", "🎨", topic="Your art. Credit the artist.", slowmode=30)),
        ("staff", c("mod-commands", "🔨", topic="Private: moderation bot commands.")),
        ("community", c("food", "🍔", topic="What's cooking.")),
        ("community", c("movies-and-tv", "🍿", topic="What you're watching.")),
        ("community", c("tech-talk", "💻", topic="Gadgets, PCs and setups.")),
        ("community", c("gaming-chat", "🎮", topic="Games you're playing.")),
        ("community", c("selfies", "🤳", topic="Only your own, SFW.", slowmode=30)),
        ("community", c("books", "📚", topic="What you're reading.")),
        ("community", c("sports", "⚽", topic="Games, scores and hot takes.")),
    ]


VOICE_POOL = [P.ch("Lounge", "🔊", "voice"), P.ch("Chill", "🛋️", "voice"), P.ch("Gaming VC", "🎮", "voice"),
              P.ch("Music VC", "🎵", "voice"), P.ch("AFK", "💤", "voice")]


def _counts(raw):
    text = total = 0
    names = set()
    for c in raw.get("categories") or []:
        if not isinstance(c, dict):
            continue
        for x in c.get("channels") or []:
            if isinstance(x, str):
                x = {"name": x}
            if not isinstance(x, dict):
                continue
            total += 1
            names.add(_key(x.get("name")))
            if str(x.get("type", "text")).lower() in TEXTLIKE:
                text += 1
    return text, total, names


def _find_cat(cats, kit):
    _n, _e, aliases, flags = KITS[kit]
    for c in cats:
        if isinstance(c, dict) and str(c.get("name", "")).strip().lower() in aliases:
            if kit == "staff" or not c.get("private"):
                return c
    if kit == "staff":  # any private category that staff can see
        for c in cats:
            if isinstance(c, dict) and c.get("private") and "staff" in str(c.get("name", "")).lower():
                return c
    return None


def expand_plan(raw: dict, size: str = "big") -> tuple[dict, list[str]]:
    """Top a raw plan up to the minimum role / text-channel counts for `size`.
    Returns (new raw plan, notes). Never removes or renames anything."""
    size = size if size in SIZES else "big"
    min_roles, min_text = MINIMUMS[size]
    p = copy.deepcopy(raw) if isinstance(raw, dict) else {}
    notes: list[str] = []
    if not min_roles and not min_text:
        return p, notes

    # ---- roles
    roles = [r for r in (p.get("roles") or []) if isinstance(r, (dict, str))]
    have = {_role_name(r).strip().lower() for r in roles}
    staff_names = [_role_name(r) for r in roles if _perm(r) in STAFF_PERMS]
    added_roles = 0
    if not any(_perm(r) == "administrator" for r in roles) and "owner" not in have:
        roles.insert(0, P.role("Owner", "#F5B841", "administrator", hoist=True))
        have.add("owner")
        staff_names.insert(0, "Owner")
        added_roles += 1
    if not any(_perm(r) in {"admin", "administrator"} and _role_name(r).lower() != "owner" for r in roles) \
            and "admin" not in have:
        idx = next((i + 1 for i, r in enumerate(roles) if _perm(r) == "administrator"), 0)
        roles.insert(idx, P.role("Admin", "#E5484D", "admin", hoist=True))
        have.add("admin")
        staff_names.append("Admin")
        added_roles += 1
    member_name = str(p.get("member_role") or "")
    for kind, r in _role_pool():
        if len(roles) >= min(min_roles, L.PLAN_MAX_ROLES):
            break
        if r["name"].lower() in have:
            continue
        r = copy.deepcopy(r)
        if kind == "staff":
            idx = max((i + 1 for i, x in enumerate(roles) if _perm(x) in STAFF_PERMS
                       or _role_name(x).lower() == "bots"), default=0)
            if r["permissions"] in STAFF_PERMS:
                staff_names.append(r["name"])
        elif kind == "mid":
            m = next((i for i, x in enumerate(roles) if member_name and _role_name(x).lower() == member_name.lower()),
                     None)
            if m is None:
                m = next((i for i, x in enumerate(roles) if _role_name(x).lower() in {"member", "members", "verified"}),
                         None)
            if m is None:
                m = next((i for i, x in enumerate(roles) if isinstance(x, dict) and x.get("self_assignable")),
                         len(roles))
            idx = m
        else:
            idx = len(roles)
        roles.insert(idx, r)
        have.add(r["name"].lower())
        added_roles += 1
    p["roles"] = roles
    if not staff_names:
        staff_names = ["Owner"]

    # ---- channels
    cats = [c for c in (p.get("categories") or []) if isinstance(c, dict)]
    for c in cats:
        c["channels"] = list(c.get("channels") or [])
    text, total, names = _counts({"categories": cats})
    added_ch = 0
    want_selfroles = any(isinstance(r, dict) and r.get("self_assignable") for r in roles) and \
        not any("role" in n for n in names)

    def target(kit):
        c = _find_cat(cats, kit)
        if c is None:
            cname, emoji, _a, flags = KITS[kit]
            if cname.lower() in {str(x.get("name", "")).lower() for x in cats}:
                cname = cname + " Hub"
            c = P.cat(cname, emoji, [], **copy.deepcopy(flags))
            if kit == "info":
                c["writable_by"] = staff_names[:4]
                cats.insert(0, c)
            elif kit == "staff":
                c["visible_to"] = staff_names[:6]
                vi = next((i for i, x in enumerate(cats) if str(x.get("name", "")).lower() in KITS["voice"][2]),
                          len(cats))
                cats.insert(vi, c)
            else:
                si = next((i for i, x in enumerate(cats) if x.get("private")
                           or str(x.get("name", "")).lower() in KITS["voice"][2]), len(cats))
                cats.insert(si, c)
        return c

    def add(kit, chan):
        nonlocal text, total, added_ch
        if total >= L.PLAN_MAX_CHANNELS or len(cats) > L.PLAN_MAX_CATEGORIES:
            return False
        k = _key(chan["name"])
        if k in names:
            return False
        c = target(kit)
        if len(c["channels"]) >= L.MAX_CHANNELS_PER_CATEGORY:
            return False
        chan = copy.deepcopy(chan)
        if chan.get("read_only") and kit != "info":
            chan["writable_by"] = staff_names[:4]
        c["channels"].append(chan)
        names.add(k)
        total += 1
        added_ch += 1
        if chan.get("type", "text") in TEXTLIKE:
            text += 1
        return True

    if want_selfroles:
        add("info", P.ch("self-roles", "🎨", topic="Tap the buttons to pick your colour, pings and more."))
    for kit, chan in _chan_pool():
        if text >= min_text:
            break
        add(kit, chan)
    has_voice = any(str(x.get("type", "")).lower() in {"voice", "stage", "vc", "audio"} for c in cats
                    for x in c["channels"] if isinstance(x, dict))
    if not has_voice and size != "small":
        for v in VOICE_POOL[: (5 if size == "big" else 3)]:
            add("voice", v)
    p["categories"] = [c for c in cats if c["channels"]]
    if added_roles or added_ch:
        notes.append(f"expanded to {size} size: +{added_roles} roles, +{added_ch} channels")
    return p, notes
