"""Built-in presets. Each is a raw plan (validated like any other)."""
from __future__ import annotations

import copy


def ch(name, emoji="", type="text", topic="", **kw):
    d = {"name": name, "emoji": emoji, "type": type, "topic": topic}
    d.update(kw)
    return d


def cat(name, emoji, channels, **kw):
    d = {"name": name, "emoji": emoji, "channels": channels}
    d.update(kw)
    return d


STAFF = ["Owner", "Admin", "Moderator"]
COMMON_AUTOMOD = [
    {"kind": "spam"},
    {"kind": "mention_spam", "mention_limit": 5},
    {"kind": "profanity"},
    {"kind": "keyword", "name": "Block scam bait",
     "keywords": ["free nitro", "*discord.gift*", "*nitro-gift*", "steam gift", "*steamcommunity.com/gift*",
                  "crypto giveaway", "airdrop"]},
]
BASE_RULES = [
    "Be respectful. No harassment, hate speech, slurs or personal attacks.",
    "No spam, flooding or unsolicited DMs to members.",
    "Keep content safe for work. No NSFW, gore or shock content.",
    "No scams, phishing links or fake giveaways.",
    "Use the right channel for each topic.",
    "Follow Discord's Terms of Service and Community Guidelines.",
    "Staff decisions are final; if you disagree, ask a staff member privately and politely.",
]
SETTINGS = {"verification_level": "medium", "explicit_content_filter": "all_members",
            "default_notifications": "mentions", "community": True}


def staff_roles():
    return [
        {"name": "Owner", "color": "#F5B841", "hoist": False, "permissions": "administrator"},
        {"name": "Admin", "color": "#E5484D", "hoist": True, "permissions": "admin"},
        {"name": "Moderator", "color": "#3B82F6", "hoist": True, "mentionable": True, "permissions": "moderator"},
    ]


def important(extra=None, welcome="welcome"):
    chans = [ch("rules", "📜", topic="Read these first. By chatting here you agree to them."),
             ch("announcements", "🔔", "announcement", "Official news."),
             ch(welcome, "👋", topic="Say hi to new members.")]
    return cat("Important", "📢", chans + (extra or []), read_only=True, writable_by=STAFF)


def staff_cat(extra=None):
    return cat("Staff", "🔒", [ch("staff-chat", "💬", topic="Private: staff only."),
                               ch("mod-log", "📋", topic="Private: AutoMod alerts and staff actions.")] + (extra or []),
               private=True, visible_to=STAFF)


def voice_cat(extra=None):
    return cat("Voice", "🔊", [ch("Lounge", "🔊", "voice"), *(extra or []), ch("AFK", "💤", "voice")])


PRESETS: dict[str, dict] = {}

PRESETS["software"] = {
    "summary": "Software product community: news, support forums, testers, staff.",
    "settings": SETTINGS,
    "roles": staff_roles() + [
        {"name": "Helper", "color": "#22C55E", "hoist": True, "mentionable": True, "permissions": "helper"},
        {"name": "Content Creator", "color": "#A855F7", "permissions": "member"},
        {"name": "Tester", "color": "#06B6D4", "permissions": "member"},
        {"name": "Supporter", "color": "#EC4899", "permissions": "member"},
        {"name": "Member", "color": "#94A3B8", "permissions": "member"},
    ],
    "categories": [
        important([ch("changelog", "🛠️", topic="What changed in each version."),
                   ch("sneak-peek", "👀", topic="Early looks at what's coming.")]),
        cat("Community", "💬", [ch("lobby", "💬", topic="General chat. Keep it friendly.", slowmode=3),
                                ch("showcase", "🖼️", topic="Show your setups and creations.", slowmode=30),
                                ch("media", "📺", topic="Clips, screenshots and memes (SFW)."),
                                ch("content-creator", "📽️", topic="Videos and streams by our Content Creators.",
                                   read_only=True, writable_by=["Content Creator"] + STAFF),
                                ch("suggestions", "💡", "forum", "One post per idea. Upvote with a reaction."),
                                ch("roles", "🪪", topic="What every role means and how to get it.", read_only=True,
                                   writable_by=STAFF)]),
        cat("Support", "🆘", [ch("help", "🆘", "forum", "Ask anything. One post per question.",
                                 tags=["Question", "Solved"]),
                              ch("bug-reports", "🐞", "forum", "One post per bug: version, OS, steps, what happened.",
                                 tags=["Windows", "Crash", "Install", "Fixed"]),
                              ch("install-help", "💿", topic="Download and first-launch problems.", slowmode=5)]),
        cat("Testing", "🧪", [ch("testers", "🧪", topic="Private: testers and staff."),
                              ch("test-builds", "📦", topic="Private: early builds.")],
            private=True, visible_to=["Tester"] + STAFF),
        staff_cat([ch("dev-lobby", "🧑‍💻", topic="Private: development talk.")]),
        voice_cat([ch("Stage", "🎙️", "stage")]),
    ],
    "rules": BASE_RULES + ["Bug reports go in the bug-reports forum, one post per bug.",
                           "Self-promotion only in showcase, and only if it's related."],
    "rules_channel": "rules", "welcome_channel": "announcements", "rules_gate": True, "member_role": "Member",
    "welcome_message": "Welcome to {server}! Read the rules, grab your roles, and say hi in the lobby. "
                       "Questions go in help, bugs in bug-reports.",
    "automod": COMMON_AUTOMOD,
}

PRESETS["gaming"] = {
    "summary": "Gaming community: LFG, clips, tournaments, game nights.",
    "settings": SETTINGS,
    "roles": staff_roles() + [
        {"name": "Event Host", "color": "#F97316", "hoist": True, "mentionable": True,
         "permissions": {"preset": "member", "add": ["manage_events", "create_events", "mute_members", "move_members"]}},
        {"name": "Streamer", "color": "#A855F7", "permissions": "member"},
        {"name": "Pro Player", "color": "#FACC15", "hoist": True, "permissions": "member"},
        {"name": "Gamer", "color": "#22C55E", "permissions": "member"},
        {"name": "LFG Ping", "color": "#06B6D4", "mentionable": True, "self_assignable": True, "permissions": "cosmetic"},
    ],
    "categories": [
        important([ch("events", "📅", topic="Game nights and tournaments.")]),
        cat("Community", "💬", [ch("general", "💬", topic="Talk about anything.", slowmode=2),
                                ch("clips", "🎬", topic="Your best plays.", slowmode=15),
                                ch("memes", "😂", topic="Memes (SFW)."),
                                ch("self-roles", "🪪", topic="Pick your games and pings.", read_only=True,
                                   writable_by=STAFF)]),
        cat("Gaming", "🎮", [ch("looking-for-group", "🤝", topic="Find teammates. Say game, region, rank."),
                             ch("strategies", "🧠", "forum", "Guides, builds and tips.", tags=["Guide", "Question"]),
                             ch("tournaments", "🏆", topic="Brackets, sign-ups and results.", read_only=True,
                                writable_by=["Event Host"] + STAFF)]),
        staff_cat(),
        voice_cat([ch("Squad 1", "🎮", "voice"), ch("Squad 2", "🎮", "voice"), ch("Tournament", "🏆", "voice"),
                   ch("Streaming", "📡", "voice")]),
    ],
    "rules": BASE_RULES + ["No cheating, hacks or selling accounts.", "Keep trash talk friendly."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Gamer",
    "welcome_message": "Welcome to {server}! Read the rules, grab your game roles, and find a squad in looking-for-group.",
    "automod": COMMON_AUTOMOD,
}

PRESETS["study"] = {
    "summary": "Study group: subjects, homework help, resources, focus rooms.",
    "settings": {**SETTINGS, "verification_level": "low"},
    "roles": staff_roles()[:1] + [
        {"name": "Organizer", "color": "#E5484D", "hoist": True, "permissions": "admin"},
        {"name": "Tutor", "color": "#22C55E", "hoist": True, "mentionable": True, "permissions": "helper"},
        {"name": "Moderator", "color": "#3B82F6", "hoist": True, "permissions": "moderator"},
        {"name": "Student", "color": "#94A3B8", "permissions": "member"},
    ],
    "categories": [
        cat("Start Here", "📌", [ch("rules", "📜", topic="Read first."),
                                 ch("announcements", "🔔", "announcement", "Exams, deadlines and sessions."),
                                 ch("welcome", "👋", topic="Introduce yourself.")],
            read_only=True, writable_by=["Owner", "Organizer", "Moderator"]),
        cat("Study", "📚", [ch("general", "💬", topic="Chat and check-ins."),
                            ch("homework-help", "❓", "forum", "One post per question. Show what you tried.",
                               tags=["Math", "Science", "Languages", "Solved"]),
                            ch("resources", "🔗", topic="Notes, links and past papers."),
                            ch("goals", "🎯", topic="Daily goals and wins."),
                            ch("schedule", "🗓️", topic="Study sessions and exam dates.")]),
        cat("Focus", "⏱️", [ch("Focus Room 1", "🔇", "voice"), ch("Focus Room 2", "🔇", "voice"),
                            ch("Group Study", "🗣️", "voice"), ch("Pomodoro", "🍅", "voice")]),
        cat("Staff", "🔒", [ch("organizers", "💬", topic="Private."), ch("mod-log", "📋", topic="Private.")],
            private=True, visible_to=["Owner", "Organizer", "Moderator"]),
    ],
    "rules": ["Be kind and patient. Everyone learns at their own pace.",
              "No cheating: don't share live exam answers or do someone's graded work for them.",
              "Show what you've tried when you ask for help.",
              "Keep focus rooms quiet; cameras and mics are optional.",
              "No spam or unrelated self-promotion.",
              "Follow Discord's Terms of Service and Community Guidelines."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Student",
    "welcome_message": "Welcome to {server}! Post your goal for the week in goals and join a focus room any time.",
    "automod": COMMON_AUTOMOD[:3],
}

PRESETS["creator"] = {
    "summary": "Creator fanbase: uploads, streams, fan art, supporter perks.",
    "settings": SETTINGS,
    "roles": staff_roles() + [
        {"name": "Creator", "color": "#A855F7", "hoist": True, "permissions": "admin"},
        {"name": "Editor", "color": "#14B8A6", "permissions": "member"},
        {"name": "Supporter", "color": "#EC4899", "hoist": True, "permissions": "member"},
        {"name": "Fan", "color": "#94A3B8", "permissions": "member"},
        {"name": "Stream Pings", "color": "#F97316", "mentionable": True, "self_assignable": True, "permissions": "cosmetic"},
    ],
    "categories": [
        important([ch("new-uploads", "🎬", topic="Every new video and stream."),
                   ch("schedule", "🗓️", topic="Stream and upload schedule.")]),
        cat("Fan Zone", "💖", [ch("general", "💬", topic="Hang out.", slowmode=3),
                               ch("fan-art", "🎨", topic="Your art. Credit the artist.", slowmode=30),
                               ch("memes", "😂", topic="Memes (SFW)."),
                               ch("video-ideas", "💡", "forum", "Suggest a video. One idea per post."),
                               ch("self-roles", "🪪", topic="Pick your pings.", read_only=True, writable_by=STAFF)]),
        cat("Supporters", "⭐", [ch("supporter-chat", "⭐", topic="Thanks for the support!"),
                                 ch("early-access", "👀", topic="Early cuts and behind the scenes.")],
            private=True, visible_to=["Supporter", "Creator"] + STAFF),
        staff_cat([ch("editing", "✂️", topic="Private: editors and creator.", private=True,
                      visible_to=["Editor", "Creator"] + STAFF)]),
        voice_cat([ch("Watch Party", "🍿", "voice"), ch("Stage", "🎙️", "stage")]),
    ],
    "rules": BASE_RULES + ["No leaks of early-access content.", "No hate towards other creators."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Fan",
    "welcome_message": "Welcome to {server}! Turn on Stream Pings in self-roles so you never miss a stream.",
    "automod": COMMON_AUTOMOD,
}

PRESETS["roleplay"] = {
    "summary": "Roleplay server: lore, character sheets, in-character scenes, OOC chat.",
    "settings": SETTINGS,
    "roles": staff_roles()[:1] + [
        {"name": "Game Master", "color": "#E5484D", "hoist": True, "mentionable": True, "permissions": "admin"},
        {"name": "Moderator", "color": "#3B82F6", "hoist": True, "permissions": "moderator"},
        {"name": "Lore Keeper", "color": "#14B8A6", "hoist": True,
         "permissions": {"preset": "member", "add": ["manage_threads"]}},
        {"name": "Approved Character", "color": "#22C55E", "permissions": "member"},
        {"name": "Adventurer", "color": "#94A3B8", "permissions": "member"},
    ],
    "categories": [
        cat("Gateway", "📜", [ch("rules", "📜", topic="Read first."),
                              ch("announcements", "🔔", "announcement", "Plot events and news."),
                              ch("welcome", "🚪", topic="Arrivals.")],
            read_only=True, writable_by=["Owner", "Game Master", "Moderator"]),
        cat("World", "🌍", [ch("lore", "📖", topic="The world's history and factions.", read_only=True,
                               writable_by=["Lore Keeper", "Game Master", "Owner"]),
                            ch("map", "🗺️", topic="Locations.", read_only=True,
                               writable_by=["Lore Keeper", "Game Master", "Owner"]),
                            ch("character-sheets", "🧾", "forum", "One post per character. Staff approve.",
                               tags=["Pending", "Approved", "Retired"])]),
        cat("In Character", "⚔️", [ch("tavern", "🍺", topic="In character only.", slowmode=5),
                                   ch("wilds", "🌲", topic="In character only.", slowmode=5),
                                   ch("city", "🏰", topic="In character only.", slowmode=5),
                                   ch("quests", "🗡️", "forum", "One thread per quest.")],
            private=True, visible_to=["Approved Character", "Game Master", "Moderator", "Owner"]),
        cat("Out of Character", "💬", [ch("ooc-chat", "💬", topic="Out-of-character talk."),
                                       ch("art", "🎨", topic="Character art.")]),
        cat("Staff", "🔒", [ch("gm-planning", "🗺️", topic="Private."), ch("mod-log", "📋", topic="Private.")],
            private=True, visible_to=["Owner", "Game Master", "Moderator"]),
        voice_cat([ch("Campaign Table", "🎲", "voice")]),
    ],
    "rules": BASE_RULES + ["No godmodding or controlling other people's characters.",
                           "Keep in-character channels in character; use ooc-chat otherwise.",
                           "Character sheets must be approved before you post in-character."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Adventurer",
    "welcome_message": "Welcome to {server}, traveller! Read the lore, post your character sheet, and a Game Master will approve it.",
    "automod": COMMON_AUTOMOD[:3],
}

PRESETS["orrin"] = copy.deepcopy(PRESETS["software"])
PRESETS["orrin"]["server_name"] = "ORRIN"
PRESETS["orrin"]["summary"] = "The ORRIN community server layout (software product)."

DESCRIPTIONS = {
    "software": "Software product (like ORRIN)",
    "gaming": "Gaming community",
    "study": "Study group",
    "creator": "Creator fanbase",
    "roleplay": "Roleplay server",
    "orrin": "Exact ORRIN layout",
}


def get(name: str) -> dict:
    p = copy.deepcopy(PRESETS[name])
    p.setdefault("source", f"preset:{name}")
    return p
