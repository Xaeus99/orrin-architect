"""Turn plan names into the decorated names Discord shows, e.g.
category  ->  "📢 | IMPORTANT | 📢"
channel   ->  "╭📜︱rules"   (tree glyphs ╭ ┊ ╰ down each category)
Text channel names can't contain spaces on Discord, which is why the channel separator is the
thin "︱" bar by default; categories and voice channels may use " | "."""
from __future__ import annotations

from . import limits as L


def category_name(cat: dict, style: dict) -> str:
    emoji = cat.get("emoji") if style.get("emoji", True) else ""
    if not emoji:
        return cat["name"].upper()[:L.MAX_NAME]
    try:
        s = style.get("category", "{emoji} | {NAME} | {emoji}").format(
            emoji=emoji, NAME=cat["name"].upper(), name=cat["name"])
    except (KeyError, IndexError, ValueError):
        s = f"{emoji} | {cat['name'].upper()} | {emoji}"
    return s[:L.MAX_NAME]


def tree_glyph(i: int, n: int) -> str:
    if n <= 1:
        return ""
    return "╭" if i == 0 else ("╰" if i == n - 1 else "┊")


def channel_name(ch: dict, style: dict, i: int = 0, n: int = 1) -> str:
    emoji = ch.get("emoji") if style.get("emoji", True) else ""
    tree = tree_glyph(i, n) if style.get("tree", True) and emoji else ""
    sep = style.get("separator", "︱")
    if ch["type"] in {"voice", "stage"} and sep == "︱":
        sep = " | "  # voice channels allow spaces
    if emoji:
        s = f"{tree}{emoji}{sep}{ch['name']}"
    else:
        s = ch["name"]
    if ch["type"] in {"text", "announcement", "forum"}:
        s = s.replace(" ", "")
    return s[:L.MAX_NAME]


def rendered(plan: dict):
    """Yield (category_display, [(channel_display, channel_dict), ...], category_dict)."""
    st = plan["style"]
    for cat in plan["categories"]:
        n = len(cat["channels"])
        yield category_name(cat, st), [(channel_name(ch, st, i, n), ch) for i, ch in enumerate(cat["channels"])], cat


def find_display(plan: dict, base: str) -> str:
    for _c, chans, _ in rendered(plan):
        for disp, ch in chans:
            if ch["name"] == base:
                return disp
    return base


def plain(name: str) -> str:
    """Strip decoration from a display name so 'add' mode can match existing channels:
    '╭📜︱rules' -> 'rules', '📢 | IMPORTANT | 📢' -> 'important'."""
    s = name
    for g in "╭┊╰":
        s = s.replace(g, "")
    for sep in ("︱", " | ", "|", "・", "・", "┃", "│"):
        if sep in s:
            parts = [p.strip() for p in s.split(sep) if p.strip()]
            # keep the part with letters
            letters = [p for p in parts if any(c.isalnum() for c in p)]
            if letters:
                s = letters[0]
    s = "".join(c for c in s if c.isalnum() or c in "-_ ").strip()
    return s.lower().replace(" ", "-")
