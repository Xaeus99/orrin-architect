"""Plan -> preview embed (as a dict, so it is testable without Discord) and plain text."""
from __future__ import annotations

from . import limits as L
from .render import rendered
from .schema import counts
from .permissions import value_to_names

TYPE_ICON = {"text": "#", "voice": "🔈", "forum": "🗂", "announcement": "📣", "stage": "🎙"}


def _cut(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def role_line(r: dict) -> str:
    p = r.get("preset") or ("custom" if r["permissions"] else "none")
    if p == "administrator":
        p = "full admin"
    elif p == "cosmetic":
        p = "colour/ping only"
    extra = " · self-assign" if r.get("self_assignable") else ""
    return f"`#{r['color']:06X}` **{r['name']}** · {p}{extra}"


def plan_embed(plan: dict, *, mode: str = "add", used: str = "", warnings=None, prompt: str = "") -> dict:
    c = counts(plan)
    title = _cut(f"🏗️ Server plan{': ' + plan['server_name'] if plan.get('server_name') else ''}", L.MAX_EMBED_TITLE)
    desc = []
    if prompt:
        desc.append(f"> {_cut(prompt, 300)}")
    if plan.get("summary"):
        desc.append(_cut(plan["summary"], 400))
    desc.append(f"**{c['categories']}** categories · **{c['channels']}** channels · **{c['roles']}** roles · "
                f"**{c['automod']}** AutoMod rules")
    st = plan["settings"]
    desc.append(f"Verification **{st['verification_level']}** · media filter **{st['explicit_content_filter'].replace('_', ' ')}** · "
                f"notifications **{st['default_notifications']}** · Community **{'on' if st['community'] else 'off'}**"
                + (f" · rules gate → **{plan['member_role']}**" if plan.get("rules_gate") else ""))
    if mode == "replace":
        desc.append("⚠️ **Replace mode**: the current channels and roles not in this plan will be REMOVED "
                    "(a backup is saved first; /setup-undo restores the layout, not old messages).")
    fields = []
    budget = L.MAX_EMBED_TOTAL - len(title) - 200
    desc_s = _cut("\n".join(desc), min(L.MAX_EMBED_DESCRIPTION, 1500))
    budget -= len(desc_s)
    for cdisp, chans, cat in rendered(plan):
        lock = " 🔒" if cat.get("private") else (" 👁️" if cat.get("read_only") else "")
        lines = []
        for disp, ch in chans:
            t = TYPE_ICON.get(ch["type"], "#")
            f = " 🔒" if ch.get("private") else (" 👁️" if ch.get("read_only") else "")
            lines.append(f"{t} {disp}{f}")
        name = _cut(cdisp + lock, L.MAX_EMBED_FIELD_NAME)
        val = _cut("\n".join(lines), L.MAX_EMBED_FIELD_VALUE)
        if len(fields) >= L.MAX_EMBED_FIELDS - 3 or budget - len(name) - len(val) < 900:
            fields.append({"name": "…", "value": "more categories not shown", "inline": False})
            break
        budget -= len(name) + len(val)
        fields.append({"name": name, "value": val, "inline": True})
    roles = "\n".join(role_line(r) for r in plan["roles"]) or "none"
    fields.append({"name": "Roles (top → bottom)", "value": _cut(roles, min(L.MAX_EMBED_FIELD_VALUE, max(100, budget - 500))),
                   "inline": False})
    budget -= len(fields[-1]["value"])
    extra = []
    if plan.get("rules"):
        extra.append(f"📜 {len(plan['rules'])} rules → #{plan.get('rules_channel') or plan.get('welcome_channel')}")
    if plan.get("welcome_message"):
        extra.append(f"👋 welcome post → #{plan.get('welcome_channel')}")
    if plan.get("automod"):
        extra.append("🛡️ AutoMod: " + ", ".join(a["name"] for a in plan["automod"]))
    if warnings:
        extra.append("ℹ️ " + "; ".join(warnings[:4]))
    if extra:
        fields.append({"name": "Also", "value": _cut("\n".join(extra), min(L.MAX_EMBED_FIELD_VALUE, max(50, budget - 100))),
                       "inline": False})
    footer = "🔒 private · 👁️ read-only for members" + (f" · planner: {used}" if used else "")
    return {"title": title, "description": desc_s, "color": 0x5865F2, "fields": fields,
            "footer": {"text": _cut(footer, 2048)}}


def embed_size(e: dict) -> int:
    n = len(e.get("title", "")) + len(e.get("description", "")) + len(e.get("footer", {}).get("text", ""))
    for f in e.get("fields", []):
        n += len(f["name"]) + len(f["value"])
    return n


def plan_text(plan: dict, warnings=None, used: str = "") -> str:
    """Readable plan for the dry-run CLI."""
    out = []
    if plan.get("server_name"):
        out.append(f"Server: {plan['server_name']}")
    if plan.get("summary"):
        out.append(plan["summary"])
    if used:
        out.append(f"Planner: {used}")
    st = plan["settings"]
    out.append(f"Settings: verification={st['verification_level']} media_filter={st['explicit_content_filter']} "
               f"notifications={st['default_notifications']} community={st['community']} "
               f"rules_gate={plan['rules_gate']}{' -> ' + plan['member_role'] if plan['rules_gate'] else ''}")
    out.append("")
    out.append("ROLES (top -> bottom)")
    for r in plan["roles"]:
        perms = value_to_names(r["permissions"])
        ps = "ADMINISTRATOR" if "administrator" in perms else (", ".join(perms[:8]) + (f" +{len(perms) - 8} more" if len(perms) > 8 else ""))
        out.append(f"  #{r['color']:06X} {r['name']:<22} [{r.get('preset') or 'custom'}] {ps or '-'}")
    out.append("")
    for cdisp, chans, cat in rendered(plan):
        flag = " (private: " + ", ".join(cat["visible_to"]) + " + staff)" if cat.get("private") else (
            " (read-only)" if cat.get("read_only") else "")
        out.append(cdisp + flag)
        for disp, ch in chans:
            f = " [private]" if ch.get("private") else (" [read-only]" if ch.get("read_only") else "")
            sm = f" slowmode {ch['slowmode']}s" if ch.get("slowmode") else ""
            out.append(f"   {TYPE_ICON.get(ch['type'], '#')} {disp}{f}{sm}" + (f"  — {ch['topic']}" if ch.get("topic") else ""))
    out.append("")
    if plan["rules"]:
        out.append(f"RULES (posted in #{plan.get('rules_channel')})")
        out += [f"  {i}. {r}" for i, r in enumerate(plan["rules"], 1)]
    if plan.get("welcome_message"):
        out.append(f"WELCOME (#{plan.get('welcome_channel')}): {plan['welcome_message']}")
    out.append("AUTOMOD: " + (", ".join(a["name"] for a in plan["automod"]) or "none"))
    if warnings:
        out.append("")
        out.append("NOTES:")
        out += [f"  - {w}" for w in warnings]
    return "\n".join(out)
