"""Deterministic planner: keywords -> a preset blend. Works with no AI at all.

Same prompt + same variant -> same plan. `variant` (the Regenerate button) rotates
the emoji theme and the secondary preset so Regenerate shows something different."""
from __future__ import annotations

import copy
import re

from .. import presets as P

KEYWORDS: dict[str, list[str]] = {
    "gaming": ["game", "gaming", "gamer", "clan", "guild", "esport", "tournament", "minecraft", "valorant",
               "fortnite", "roblox", "lfg", "squad", "fps", "mmo", "apex", "league", "cod", "rocket league",
               "speedrun", "chess", "smp", "csgo", "cs2", "overwatch", "gta"],
    "software": ["app", "software", "bot", "product", "beta", "tester", "bug", "release", "saas", "api",
                 "open source", "opensource", "dev", "developer", "startup", "tool", "plugin", "mod ",
                 "assistant", "ai ", "support", "changelog", "orrin"],
    "study": ["study", "school", "class", "exam", "homework", "university", "college", "course", "learn",
              "students", "tutor", "revision", "gcse", "sat", "language exchange", "coding bootcamp", "notes"],
    "creator": ["youtube", "youtuber", "streamer", "stream", "twitch", "fans", "fanbase", "creator", "tiktok",
                "podcast", "musician", "artist", "band", "vtuber", "influencer", "subscribers", "fan "],
    "roleplay": ["roleplay", "role-play", "rp", "lore", "character", "fantasy", "dnd", "d&d", "campaign",
                 "story", "medieval", "kingdom", "dungeon", "rpg", "oc ", "worldbuilding"],
}

# extra feature modules that blend onto any base
MODULES = [
    (["music", "song", "playlist", "dj"], ("Music", "🎵", [P.ch("music-share", "🎵", topic="Share tracks."),
                                                         P.ch("Music Room", "🎧", "voice")])),
    (["art", "draw", "design", "artist"], ("Art", "🎨", [P.ch("art-showcase", "🎨", topic="Your art.", slowmode=30),
                                                       P.ch("feedback", "🖌️", "forum", "Ask for critique.")])),
    (["event", "tournament", "giveaway", "contest"], ("Events", "🎉", [
        P.ch("events", "📅", topic="Upcoming events.", read_only=True, writable_by=["Owner", "Admin", "Moderator"]),
        P.ch("giveaways", "🎁", topic="Giveaways and contests.", read_only=True,
             writable_by=["Owner", "Admin", "Moderator"])])),
    (["meme", "memes", "fun", "chill", "hangout"], ("Off Topic", "🎈", [P.ch("memes", "😂", topic="Memes (SFW)."),
                                                                       P.ch("pets", "🐾", topic="Pet pics.")])),
    (["code", "coding", "programming", "developer", "dev "], ("Code", "💻", [
        P.ch("code-help", "💻", "forum", "Ask coding questions."), P.ch("snippets", "🧩", topic="Share snippets.")])),
    (["shop", "store", "merch", "sell", "market", "trade", "trading"], ("Market", "🛒", [
        P.ch("marketplace", "🛒", "forum", "One post per listing. No scams."),
        P.ch("trade-rules", "⚖️", topic="How trading works here.", read_only=True,
             writable_by=["Owner", "Admin", "Moderator"])])),
    (["international", "language", "languages", "multilingual"], ("Languages", "🌐", [
        P.ch("english", "🇬🇧"), P.ch("español", "🇪🇸"), P.ch("français", "🇫🇷"), P.ch("deutsch", "🇩🇪")])),
]

THEMES = [
    {},  # variant 0: the preset's own emojis
    {"category": "{emoji}・{NAME}・{emoji}", "separator": "・", "tree": False},
    {"category": "── {emoji} {NAME} ──", "separator": "︱", "tree": True},
    {"category": "【{emoji}】{NAME}", "separator": "┃", "tree": False},
]


def score(prompt: str) -> dict[str, int]:
    p = " " + prompt.lower() + " "
    out = {}
    for name, kws in KEYWORDS.items():
        s = 0
        for k in kws:
            if len(k) <= 3 and k.strip() == k:      # short words: whole-word match only
                s += len(re.findall(rf"\b{re.escape(k)}s?\b", p))
            elif " " in k.strip():                   # phrases count double
                s += 2 * p.count(k)
            else:
                s += p.count(k)
        out[name] = s
    return out


def extract_name(prompt: str) -> str:
    m = re.search(r"(?:called|named|name it|for)\s+[\"“']([^\"”']{2,40})[\"”']", prompt, re.I)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:called|named)\s+([A-Z0-9][\w\-]*(?:\s+[A-Z0-9][\w\-]*){0,3})", prompt)
    if m:
        return m.group(1).strip()
    m = re.search(r"[\"“]([^\"”]{2,40})[\"”]", prompt)
    return m.group(1).strip() if m else ""


def fallback_plan(prompt: str, variant: int = 0) -> dict:
    prompt = prompt or ""
    sc = score(prompt)
    ranked = sorted(sc.items(), key=lambda kv: (-kv[1], list(KEYWORDS).index(kv[0])))
    base = ranked[0][0] if ranked[0][1] > 0 else "software"
    if "orrin" in prompt.lower() and base == "software":
        base = "orrin"
    plan = P.get(base)
    plan["source"] = f"fallback:{base}"
    picked = [base]

    seconds = [n for n, s in ranked[1:] if s > 0]
    if seconds:
        second = seconds[variant % len(seconds)] if variant else seconds[0]
        _blend(plan, P.get(second))
        picked.append(second)

    low = " " + prompt.lower() + " "
    existing = {c["name"].lower() for c in plan["categories"]}
    have_ch = {ch["name"].lower() for c in plan["categories"] for ch in c["channels"]}
    for kws, (cname, emoji, chans) in MODULES:
        new = [c for c in chans if c["name"].lower() not in have_ch]
        if any(k in low for k in kws) and cname.lower() not in existing and new:
            _insert_before_staff(plan, P.cat(cname, emoji, copy.deepcopy(new)))
            have_ch |= {c["name"].lower() for c in new}
            existing.add(cname.lower())
            picked.append(cname.lower())

    if any(w in low for w in ("no emoji", "minimal", "clean", "simple names", "plain")):
        plan["style"] = {"emoji": False, "tree": False}
    elif variant:
        plan["style"] = dict(THEMES[variant % len(THEMES)])
    if any(w in low for w in ("strict", "safe", "kids", "family", "school")):
        plan["settings"] = {**plan.get("settings", {}), "verification_level": "high"}
    if any(w in low for w in ("small", "friends", "private group", "just us")):
        plan["settings"] = {**plan.get("settings", {}), "verification_level": "low"}
        plan["rules_gate"] = False
    if any(w in low for w in ("no rules", "no verification")):
        plan["rules_gate"] = False

    name = extract_name(prompt)
    if name:
        plan["server_name"] = name
    plan["summary"] = (plan.get("summary", "") + f" Built from: {' + '.join(picked)}.").strip()
    return plan


def _insert_before_staff(plan: dict, category: dict) -> None:
    cats = plan["categories"]
    idx = next((i for i, c in enumerate(cats) if c.get("private") and c["name"].lower() in {"staff"}), None)
    if idx is None:
        idx = next((i for i, c in enumerate(cats) if c["name"].lower() == "voice"), len(cats))
    cats.insert(idx, category)


def _blend(plan: dict, other: dict) -> None:
    """Bring the other preset's distinctive public category and its non-staff roles."""
    have_cats = {c["name"].lower() for c in plan["categories"]}
    skip = {"important", "staff", "voice", "start here", "gateway", "community"}
    for c in other["categories"]:
        if c["name"].lower() not in have_cats and c["name"].lower() not in skip and not c.get("private"):
            _insert_before_staff(plan, copy.deepcopy(c))
            break
    have_roles = {r["name"].lower() for r in plan["roles"]}
    staffish = {"owner", "admin", "moderator", "organizer", "game master", "creator"}
    added = 0
    for r in other["roles"]:
        if r["name"].lower() not in have_roles and r["name"].lower() not in staffish and added < 2:
            pos = len(plan["roles"]) - 1  # keep the base member role last
            plan["roles"].insert(max(pos, 0), copy.deepcopy(r))
            added += 1
