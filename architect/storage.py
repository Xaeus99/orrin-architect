"""Backups, setup journals and templates as JSON files under DATA_DIR (default ./data).

data/backups/<guild>/<time>.json     full snapshot taken before every setup
data/journal/<guild>/<time>.json     what a setup created/changed/removed (used by /setup-undo)
data/templates/<name>.json           saved plans (/template save|load|list)"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from .render import plain


def data_dir() -> Path:
    d = Path(os.environ.get("ARCHITECT_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)
    return str(path)


def save_backup(guild_id, snapshot: dict) -> str:
    return _write(data_dir() / "backups" / str(guild_id) / f"{time.strftime('%Y%m%d-%H%M%S')}.json", snapshot)


def load_json(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_journal(guild_id, journal: dict) -> str:
    return _write(data_dir() / "journal" / str(guild_id) / f"{journal['id']}.json", journal)


def latest_journal(guild_id) -> tuple[str, dict] | None:
    d = data_dir() / "journal" / str(guild_id)
    if not d.exists():
        return None
    for p in sorted(d.glob("*.json"), reverse=True):
        j = load_json(p)
        if not j.get("undone"):
            return str(p), j
    return None


SAFE = re.compile(r"[^a-z0-9_-]+")


def template_name(name: str) -> str:
    n = SAFE.sub("-", (name or "").strip().lower()).strip("-")[:40]
    if not n:
        raise ValueError("template name must contain letters or digits")
    return n


def save_template(name: str, plan: dict) -> str:
    return _write(data_dir() / "templates" / f"{template_name(name)}.json", plan)


def load_template(name: str) -> dict:
    p = data_dir() / "templates" / f"{template_name(name)}.json"
    if not p.exists():
        raise FileNotFoundError(name)
    return load_json(p)


def list_templates() -> list[str]:
    d = data_dir() / "templates"
    return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []


# ---------------------------------------------------------------- snapshot -> plan
def snapshot_to_plan(snap: dict) -> dict:
    """Turn a live server snapshot into a raw plan, so '/template save' can copy a server's
    layout (like the ORRIN server) onto another one. Decorations are kept as display names."""
    from .permissions import is_staff_value, BITS
    everyone = snap.get("everyone_id")
    role_by_id = {r["id"]: r for r in snap["roles"]}
    roles = []
    for r in sorted(snap["roles"], key=lambda r: -r.get("position", 0)):
        if r.get("default") or r.get("managed"):
            continue
        roles.append({"name": r["name"], "color": f"#{r.get('color', 0):06X}", "hoist": r.get("hoist", False),
                      "mentionable": r.get("mentionable", False),
                      "permissions": [n for n, b in BITS.items() if r["permissions"] >> b & 1]})
    view = 1 << BITS["view_channel"]
    send = 1 << BITS["send_messages"]

    def flags(c):
        private = read_only = False
        vis, wr = [], []
        for o in c.get("overwrites", []):
            if o.get("kind") != "role":
                continue
            if o["id"] == everyone or o.get("default"):
                private = private or bool(o["deny"] & view)
                read_only = read_only or bool(o["deny"] & send)
            else:
                rn = role_by_id.get(o["id"], {}).get("name") or o.get("role_name")
                if rn and o["allow"] & view:
                    vis.append(rn)
                if rn and o["allow"] & send:
                    wr.append(rn)
        return {"private": private, "visible_to": vis if private else [],
                "read_only": read_only, "writable_by": wr if read_only else []}

    chans = snap["channels"]
    cats = []
    for c in sorted([c for c in chans if c["type"] == "category"], key=lambda c: c.get("position", 0)):
        kids = sorted([x for x in chans if x.get("parent_id") == c["id"] and x["type"] != "category"],
                      key=lambda x: (x["type"] in {"voice", "stage"}, x.get("position", 0)))
        if not kids or plain(c["name"]) == "architect-log":
            continue
        cats.append({"name": plain(c["name"]).replace("-", " ").title() or c["name"],
                     "emoji": _first_emoji(c["name"]), **flags(c),
                     "channels": [{"name": plain(x["name"]) or x["name"], "emoji": _first_emoji(x["name"]),
                                   "type": x["type"] if x["type"] in {"text", "voice", "forum", "announcement", "stage"} else "text",
                                   "topic": x.get("topic") or "", "slowmode": x.get("slowmode", 0),
                                   **flags(x)} for x in kids if plain(x["name"]) != "architect-log"]})
    s = snap.get("settings", {})
    inv_v = {0: "none", 1: "low", 2: "medium", 3: "high", 4: "highest"}
    return {"server_name": snap.get("name", ""), "summary": f"Copied from {snap.get('name', 'a server')}",
            "settings": {"verification_level": inv_v.get(s.get("verification_level", 2), "medium"),
                         "explicit_content_filter": {0: "disabled", 1: "members_without_roles"}.get(
                             s.get("explicit_content_filter", 2), "all_members"),
                         "default_notifications": "all" if s.get("default_notifications") == 0 else "mentions",
                         "community": bool(snap.get("community"))},
            "roles": roles, "categories": cats, "rules": [], "automod": [
                {"kind": "spam"}, {"kind": "mention_spam"}, {"kind": "profanity"}], "source": "template"}


def _first_emoji(name: str) -> str:
    for ch in name:
        if ord(ch) > 0x2500 and ch not in "╭┊╰︱│┃・|" and not ch.isalnum():
            # include a following variation selector / ZWJ sequence
            i = name.index(ch)
            j = i + 1
            while j < len(name) and (name[j] in "\ufe0f\u200d" or (0x1F3FB <= ord(name[j]) <= 0x1F3FF)
                                     or (name[j - 1] == "\u200d")):
                j += 1
            return name[i:j]
    return ""
