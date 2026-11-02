"""The server plan: JSON schema, validation and repair.

`validate_plan(raw)` takes whatever a planner produced (an LLM's JSON, a preset, a saved
template) and returns a normalized plan that is safe to apply, plus warnings (things it
repaired) and errors (things that make the plan unusable). Pure Python, no Discord.
"""
from __future__ import annotations

import copy
import re
import unicodedata

from . import limits as L
from .permissions import (PRESETS, STAFF_PRESETS, BITS, resolve_spec, strip_dangerous,
                          is_staff_value)

CHANNEL_TYPES = {"text", "voice", "forum", "announcement", "stage"}
TYPE_ALIASES = {"news": "announcement", "announcements": "announcement", "vc": "voice",
                "audio": "voice", "stage_voice": "stage", "thread_forum": "forum", "chat": "text"}
VERIFICATION = {"none": 0, "low": 1, "medium": 2, "high": 3, "highest": 4, "very_high": 4}
EXPLICIT = {"disabled": 0, "off": 0, "members_without_roles": 1, "no_roles": 1,
            "all_members": 2, "all": 2, "on": 2}
NOTIFY = {"all": 0, "all_messages": 0, "mentions": 1, "only_mentions": 1}
AUTOMOD_KINDS = {"spam", "mention_spam", "keyword", "profanity"}
DEFAULT_STYLE = {"category": "{emoji} | {NAME} | {emoji}", "separator": "︱", "tree": True,
                 "emoji": True}

PLAN_JSON_SCHEMA = {
    "type": "object",
    "required": ["categories", "roles"],
    "properties": {
        "server_name": {"type": "string"},
        "summary": {"type": "string"},
        "style": {"type": "object", "properties": {
            "category": {"type": "string"}, "separator": {"type": "string"},
            "tree": {"type": "boolean"}, "emoji": {"type": "boolean"}}},
        "settings": {"type": "object", "properties": {
            "verification_level": {"enum": list(VERIFICATION)},
            "explicit_content_filter": {"enum": ["disabled", "members_without_roles", "all_members"]},
            "default_notifications": {"enum": ["all", "mentions"]},
            "community": {"type": "boolean"}}},
        "roles": {"type": "array", "items": {"type": "object", "required": ["name"], "properties": {
            "name": {"type": "string"}, "color": {"type": "string"},
            "hoist": {"type": "boolean"}, "mentionable": {"type": "boolean"},
            "permissions": {"description": "a preset (" + ", ".join(PRESETS) + ") or a list of permission names"},
            "self_assignable": {"type": "boolean"}}}},
        "categories": {"type": "array", "items": {"type": "object", "required": ["name", "channels"], "properties": {
            "name": {"type": "string"}, "emoji": {"type": "string"},
            "private": {"type": "boolean"}, "visible_to": {"type": "array", "items": {"type": "string"}},
            "read_only": {"type": "boolean"}, "writable_by": {"type": "array", "items": {"type": "string"}},
            "channels": {"type": "array", "items": {"type": "object", "required": ["name"], "properties": {
                "name": {"type": "string"}, "emoji": {"type": "string"},
                "type": {"enum": sorted(CHANNEL_TYPES)}, "topic": {"type": "string"},
                "slowmode": {"type": "integer"}, "nsfw": {"type": "boolean"},
                "private": {"type": "boolean"}, "visible_to": {"type": "array", "items": {"type": "string"}},
                "read_only": {"type": "boolean"}, "writable_by": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}}}}}}}},
        "rules": {"type": "array", "items": {"type": "string"}},
        "rules_channel": {"type": "string"},
        "welcome_channel": {"type": "string"},
        "welcome_message": {"type": "string"},
        "rules_gate": {"type": "boolean"},
        "member_role": {"type": "string"},
        "automod": {"type": "array", "items": {"type": "object", "properties": {
            "kind": {"enum": sorted(AUTOMOD_KINDS)}, "name": {"type": "string"},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "mention_limit": {"type": "integer"}}}},
    },
}


class PlanError(ValueError):
    pass


# ---------------------------------------------------------------- small helpers
def _s(v, default=""):
    return v.strip() if isinstance(v, str) else default


def _b(v, default=False):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "yes", "1", "on"}
    if isinstance(v, (int, float)):
        return bool(v)
    return default


def clean_emoji(v) -> str:
    """Keep a short emoji / symbol; drop words ('rocket'), letters and digits."""
    s = _s(v)
    if not s or len(s) > 8:
        return ""
    if any(ch.isascii() and ch.isalnum() for ch in s):
        return ""
    if s.startswith(":") or "<" in s:
        return ""
    return s


def slug(name: str, max_len: int = 60) -> str:
    """Discord text-channel style: lowercase, no spaces, hyphens."""
    s = unicodedata.normalize("NFKC", _s(name)).lower()
    s = re.sub(r"^[#\s]+", "", s)
    s = re.sub(r"[^\w\-]+", "-", s, flags=re.UNICODE)
    s = re.sub(r"-{2,}", "-", s).strip("-_")
    return s[:max_len].strip("-") or "channel"


def clean_title(name: str, max_len: int = 60) -> str:
    s = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", _s(name))).strip(" |#")
    return s[:max_len].strip() or "Untitled"


def parse_color(v) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, int):
        return v if 0 <= v <= 0xFFFFFF else 0
    s = _s(v).lower().lstrip("#")
    if s.startswith("0x"):
        s = s[2:]
    if len(s) == 3 and re.fullmatch(r"[0-9a-f]{3}", s):
        s = "".join(c * 2 for c in s)
    if re.fullmatch(r"[0-9a-f]{6}", s):
        return int(s, 16)
    named = {"red": 0xE5484D, "blue": 0x3B82F6, "green": 0x22C55E, "purple": 0xA855F7,
             "pink": 0xEC4899, "gold": 0xF5B841, "yellow": 0xFACC15, "orange": 0xF97316,
             "cyan": 0x06B6D4, "teal": 0x14B8A6, "grey": 0x94A3B8, "gray": 0x94A3B8,
             "white": 0xF8FAFC, "black": 0x111827}
    return named.get(s, 0)


def _strs(v, max_items=50, max_len=100):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, (list, tuple)):
        return []
    out = []
    for x in v:
        if isinstance(x, str) and x.strip():
            out.append(x.strip()[:max_len])
    return out[:max_items]


# ---------------------------------------------------------------- the validator
def validate_plan(raw) -> tuple[dict, list[str], list[str]]:
    """Return (plan, warnings, errors). A plan with errors must not be applied."""
    warns: list[str] = []
    errors: list[str] = []
    if not isinstance(raw, dict):
        return {}, warns, ["plan is not a JSON object"]
    raw = copy.deepcopy(raw)
    plan: dict = {}

    plan["server_name"] = clean_title(raw.get("server_name") or "", 100) if raw.get("server_name") else ""
    plan["summary"] = _s(raw.get("summary"))[:300]
    plan["source"] = _s(raw.get("source")) or "custom"

    st = raw.get("style") if isinstance(raw.get("style"), dict) else {}
    style = dict(DEFAULT_STYLE)
    if isinstance(st.get("category"), str) and "{" in st["category"]:
        try:
            st["category"].format(emoji="x", NAME="X", name="x")
            style["category"] = st["category"][:40]
        except (KeyError, IndexError, ValueError):
            warns.append("style.category format was unreadable, used the default")
    if isinstance(st.get("separator"), str) and len(st["separator"]) <= 3:
        style["separator"] = st["separator"]
    style["tree"] = _b(st.get("tree"), True)
    style["emoji"] = _b(st.get("emoji"), True)
    plan["style"] = style

    se = raw.get("settings") if isinstance(raw.get("settings"), dict) else {}
    vl = _s(se.get("verification_level"), "medium").lower()
    ef = _s(se.get("explicit_content_filter"), "all_members").lower()
    dn = _s(se.get("default_notifications"), "mentions").lower()
    plan["settings"] = {
        "verification_level": vl if vl in VERIFICATION else "medium",
        "explicit_content_filter": {0: "disabled", 1: "members_without_roles", 2: "all_members"}[EXPLICIT.get(ef, 2)],
        "default_notifications": "all" if NOTIFY.get(dn, 1) == 0 else "mentions",
        "community": _b(se.get("community"), True),
    }

    # ---- roles
    roles, seen = [], set()
    admin_roles = 0
    for r in raw.get("roles") or []:
        if isinstance(r, str):
            r = {"name": r}
        if not isinstance(r, dict):
            continue
        name = clean_title(r.get("name", ""), L.MAX_NAME)
        key = name.lower()
        if key in {"@everyone", "everyone", "@here", "here"} or key in seen or name == "Untitled":
            if key not in seen and name != "Untitled":
                warns.append(f"role '{name}' is reserved by Discord, skipped")
            continue
        value, preset, pw = resolve_spec(r.get("permissions", r.get("preset")))
        warns += [f"role '{name}': {m}" for m in pw]
        selfa = _b(r.get("self_assignable"))
        if value >> BITS["administrator"] & 1:
            admin_roles += 1
            if admin_roles > 2 or selfa:
                v2 = resolve_spec("admin")[0]
                value, preset = (v2, "admin") if not selfa else (strip_dangerous(v2)[0], "member")
                warns.append(f"role '{name}': Administrator removed (only the top roles get it)")
        if selfa:
            value, removed = strip_dangerous(value)
            if removed:
                warns.append(f"role '{name}' is self-assignable, so {', '.join(removed)} were removed")
        seen.add(key)
        roles.append({"name": name, "color": parse_color(r.get("color")), "hoist": _b(r.get("hoist")),
                      "mentionable": _b(r.get("mentionable")), "permissions": value,
                      "preset": preset, "self_assignable": selfa,
                      "staff": preset in STAFF_PRESETS or is_staff_value(value)})
    if len(roles) > L.PLAN_MAX_ROLES:
        warns.append(f"{len(roles)} roles planned, kept the first {L.PLAN_MAX_ROLES}")
        roles = roles[:L.PLAN_MAX_ROLES]
    plan["roles"] = roles
    role_names = {r["name"].lower(): r["name"] for r in roles}

    def refs(v, where):
        out = []
        for n in _strs(v):
            n2 = n.lstrip("@").strip()
            if n2.lower() in {"everyone", "@everyone"}:
                out.append("@everyone")
            elif n2.lower() in role_names:
                out.append(role_names[n2.lower()])
            else:
                out.append(n2)
                warns.append(f"{where}: role '{n2}' is not in the plan; it will only work if the server already has it")
        return list(dict.fromkeys(out))

    # ---- categories / channels
    cats, total, seen_ch = [], 0, set()
    for c in raw.get("categories") or []:
        if not isinstance(c, dict):
            continue
        if len(cats) >= L.PLAN_MAX_CATEGORIES:
            warns.append(f"more than {L.PLAN_MAX_CATEGORIES} categories planned, extra ones dropped")
            break
        cname = clean_title(c.get("name", ""), 40)
        cat = {"name": cname, "emoji": clean_emoji(c.get("emoji")), "private": _b(c.get("private")),
               "visible_to": refs(c.get("visible_to"), f"category '{cname}'"),
               "read_only": _b(c.get("read_only")),
               "writable_by": refs(c.get("writable_by"), f"category '{cname}'"), "channels": []}
        for ch in c.get("channels") or []:
            if isinstance(ch, str):
                ch = {"name": ch}
            if not isinstance(ch, dict):
                continue
            if len(cat["channels"]) >= L.MAX_CHANNELS_PER_CATEGORY:
                warns.append(f"category '{cname}' has more than {L.MAX_CHANNELS_PER_CATEGORY} channels, extras dropped")
                break
            if total >= L.PLAN_MAX_CHANNELS:
                warns.append(f"more than {L.PLAN_MAX_CHANNELS} channels planned, extras dropped")
                break
            t = _s(ch.get("type"), "text").lower()
            t = TYPE_ALIASES.get(t, t)
            if t not in CHANNEL_TYPES:
                warns.append(f"channel '{ch.get('name')}': unknown type '{t}', used text")
                t = "text"
            nm = slug(ch.get("name", "")) if t in {"text", "announcement", "forum"} else clean_title(ch.get("name", ""), 60)
            if nm.lower() in seen_ch:
                warns.append(f"duplicate channel '{nm}' skipped")
                continue
            seen_ch.add(nm.lower())
            sm = ch.get("slowmode", 0)
            sm = int(sm) if isinstance(sm, (int, float)) and not isinstance(sm, bool) else 0
            item = {"name": nm, "emoji": clean_emoji(ch.get("emoji")), "type": t,
                    "topic": _s(ch.get("topic"))[:L.MAX_TOPIC],
                    "slowmode": max(0, min(L.MAX_SLOWMODE, sm)), "nsfw": _b(ch.get("nsfw")),
                    "private": _b(ch.get("private")),
                    "visible_to": refs(ch.get("visible_to"), f"channel '{nm}'"),
                    "read_only": _b(ch.get("read_only")),
                    "writable_by": refs(ch.get("writable_by"), f"channel '{nm}'")}
            if t == "forum":
                tags = [clean_title(x, L.MAX_FORUM_TAG_NAME) for x in _strs(ch.get("tags"))]
                item["tags"] = list(dict.fromkeys(tags))[:L.MAX_FORUM_TAGS]
            cat["channels"].append(item)
            total += 1
        if cat["channels"]:
            cats.append(cat)
        else:
            warns.append(f"category '{cname}' had no channels, skipped")
    plan["categories"] = cats
    if not cats:
        errors.append("the plan has no channels")

    names = [ch["name"] for c in cats for ch in c["channels"]]

    def find_channel(v, want_types=("text", "announcement")):
        s = _s(v)
        if not s:
            return ""
        k = slug(s)
        for c in cats:
            for ch in c["channels"]:
                if ch["type"] in want_types and (ch["name"] == k or k in ch["name"]):
                    return ch["name"]
        return ""

    # ---- rules / welcome
    rules = [re.sub(r"^\s*\d+[.)]\s*", "", x)[:300] for x in _strs(raw.get("rules"), 25, 400)]
    plan["rules"] = rules
    plan["rules_channel"] = find_channel(raw.get("rules_channel")) or find_channel("rules")
    plan["welcome_channel"] = (find_channel(raw.get("welcome_channel")) or find_channel("welcome")
                               or find_channel("announcements") or find_channel("general")
                               or find_channel("lobby"))
    plan["welcome_message"] = _s(raw.get("welcome_message"))[:1800]
    if rules and not plan["rules_channel"]:
        warns.append("rules given but no rules channel; they will be posted in the welcome channel")
    gate = _b(raw.get("rules_gate"), bool(rules))
    member_role = _s(raw.get("member_role"))
    if gate:
        mr = role_names.get(member_role.lower()) if member_role else None
        mr = mr or role_names.get("member") or role_names.get("members") or role_names.get("verified")
        if not mr:
            warns.append("rules gate needs a Member role; added one")
            v = resolve_spec("member")[0]
            plan["roles"].append({"name": "Member", "color": 0x94A3B8, "hoist": False, "mentionable": False,
                                  "permissions": v, "preset": "member", "self_assignable": False, "staff": False})
            mr = "Member"
        if not rules:
            gate = False
            warns.append("rules gate turned off: no rules to accept")
        member_role = mr if gate else ""
    plan["rules_gate"] = gate
    plan["member_role"] = member_role if gate else ""

    # ---- automod
    am, counts = [], {"spam": 0, "mention_spam": 0, "profanity": 0, "keyword": 0}
    for a in raw.get("automod") or []:
        if isinstance(a, str):
            a = {"kind": a}
        if not isinstance(a, dict):
            continue
        k = _s(a.get("kind") or a.get("type")).lower().replace(" ", "_").replace("-", "_")
        k = {"mentions": "mention_spam", "mention": "mention_spam", "bad_words": "profanity",
             "slurs": "profanity", "keywords": "keyword", "words": "keyword", "links": "keyword",
             "keyword_preset": "profanity", "spam_links": "spam"}.get(k, k)
        if k not in AUTOMOD_KINDS:
            warns.append(f"AutoMod rule kind '{k}' unknown, skipped")
            continue
        cap = L.MAX_AUTOMOD_KEYWORD_RULES if k == "keyword" else 1
        if counts[k] >= cap:
            warns.append(f"Discord allows {cap} '{k}' AutoMod rule(s); extra skipped")
            continue
        rule = {"kind": k, "name": clean_title(a.get("name") or {
            "spam": "Block suspected spam", "mention_spam": "Block mention spam",
            "profanity": "Block slurs and sexual content", "keyword": "Blocked words"}[k], 100)}
        if k == "keyword":
            kws = [x[:L.MAX_AUTOMOD_KEYWORD_LEN] for x in _strs(a.get("keywords"), L.MAX_AUTOMOD_KEYWORDS, 200)]
            if not kws:
                warns.append(f"AutoMod keyword rule '{rule['name']}' had no words, skipped")
                continue
            rule["keywords"] = list(dict.fromkeys(kws))
        if k == "mention_spam":
            ml = a.get("mention_limit", 5)
            rule["mention_limit"] = max(1, min(50, int(ml) if isinstance(ml, (int, float)) and not isinstance(ml, bool) else 5))
        counts[k] += 1
        am.append(rule)
    plan["automod"] = am
    plan["log_channel"] = "architect-log"
    return plan, warns, errors


def counts(plan: dict) -> dict:
    chans = [ch for c in plan.get("categories", []) for ch in c["channels"]]
    by = {}
    for ch in chans:
        by[ch["type"]] = by.get(ch["type"], 0) + 1
    return {"categories": len(plan.get("categories", [])), "channels": len(chans),
            "roles": len(plan.get("roles", [])), "automod": len(plan.get("automod", [])),
            "by_type": by}


def assert_valid(raw) -> dict:
    plan, _w, errs = validate_plan(raw)
    if errs:
        raise PlanError("; ".join(errs))
    return plan
