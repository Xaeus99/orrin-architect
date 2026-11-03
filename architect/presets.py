"""Built-in presets. Each is a raw plan (validated like any other).

Presets are written at full ("big") size. Items tagged ``tier="normal"`` are dropped for
size small; items tagged ``tier="big"`` are dropped for sizes small and normal. ``get(name, size)``
returns a sized copy with the tier tags removed.

The layouts follow the patterns in ``knowledge/server_design.md`` (distilled from Discord
server-setup guides): a read-only start-here category, a community category, the server's own
topic categories, events, support/feedback, a private staff area and voice; a staff ladder,
a bots role, level roles, self-assign colour/ping/pronoun roles and one base member role."""
from __future__ import annotations

import copy

SIZES = ("small", "normal", "big")
_RANK = {"small": 0, "normal": 1, "big": 2}


def ch(name, emoji="", type="text", topic="", **kw):
    d = {"name": name, "emoji": emoji, "type": type, "topic": topic}
    d.update(kw)
    return d


def cat(name, emoji, channels, **kw):
    d = {"name": name, "emoji": emoji, "channels": channels}
    d.update(kw)
    return d


def N(item):
    """Mark a channel/role/category as normal+big only."""
    item["tier"] = "normal"
    return item


def B(item):
    """Mark a channel/role/category as big only."""
    item["tier"] = "big"
    return item


STAFF = ["Owner", "Admin", "Moderator"]
STAFF_ALL = STAFF + ["Trial Mod"]
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


# ---------------------------------------------------------------- role kits
def role(name, color, permissions="member", **kw):
    d = {"name": name, "color": color, "permissions": permissions}
    d.update(kw)
    return d


def staff_roles(trial="Trial Mod"):
    return [
        role("Owner", "#F5B841", "administrator", hoist=True),
        role("Admin", "#E5484D", "admin", hoist=True),
        role("Moderator", "#3B82F6", "moderator", hoist=True, mentionable=True),
        N(role(trial, "#60A5FA", "helper", hoist=True, mentionable=True)),
    ]


def bots_role():
    return N(role("Bots", "#5865F2", "member", hoist=True))


def level_roles(names=("Legend", "Veteran", "Regular", "Active"), levels=(50, 25, 10, 5)):
    """Activity ladder (give them out with any levelling bot, or by hand)."""
    colors = ["#F59E0B", "#8B5CF6", "#10B981", "#64748B"]
    out = []
    for i, (n, lv) in enumerate(zip(names, levels)):
        r = role(f"{n} (Lv {lv})", colors[i % len(colors)], "cosmetic", hoist=i == 0)
        out.append(B(r) if i in (0, 1) else N(r))
    return out


COLOURS = [("Crimson", "#DC2626"), ("Sunset", "#F97316"), ("Sunflower", "#FACC15"), ("Mint", "#34D399"),
           ("Ocean", "#0EA5E9"), ("Lavender", "#A78BFA"), ("Bubblegum", "#F472B6")]


def colour_roles(n=6, normal=4):
    out = []
    for i, (name, c) in enumerate(COLOURS[:n]):
        r = role(name, c, "cosmetic", self_assignable=True)
        out.append(N(r) if i < normal else B(r))
    return out


def ping_roles(extra=()):
    base = [role("Announcement Ping", "#94A3B8", "cosmetic", mentionable=True, self_assignable=True),
            N(role("Event Ping", "#F97316", "cosmetic", mentionable=True, self_assignable=True)),
            B(role("Giveaway Ping", "#EC4899", "cosmetic", mentionable=True, self_assignable=True))]
    return base + [r if "tier" in r else r for r in extra]


def pronoun_roles():
    return [B(role(n, "#94A3B8", "cosmetic", self_assignable=True)) for n in ("He/Him", "She/Her", "They/Them")]


def region_roles():
    return [B(role(n, "#94A3B8", "cosmetic", self_assignable=True)) for n in ("NA", "EU", "Asia")]


def ladder(staff, special, member, pings, *, levels=None, colours=True, pronouns=True, regions=False):
    """Role order (top -> bottom): staff, bots, special, colour roles (above levels so a picked
    colour shows), level roles, base member role, ping roles, identity roles."""
    out = list(staff) + [bots_role()] + list(special)
    if colours:
        out += colour_roles()
    out += level_roles() if levels is None else levels
    out.append(member)
    out += pings
    if pronouns:
        out += pronoun_roles()
    if regions:
        out += region_roles()
    return out


# ---------------------------------------------------------------- category kits
def important(extra=None, welcome="welcome", writers=None):
    chans = [ch("rules", "📜", topic="Read these first. By chatting here you agree to them."),
             ch("announcements", "🔔", "announcement", "Official news."),
             ch(welcome, "👋", topic="Say hi to new members."),
             N(ch("roles-info", "🪪", topic="What every role means and how to earn it.")),
             ch("self-roles", "🎨", topic="Tap the buttons to pick your colour, pings and more."),
             B(ch("faq", "❓", topic="Answers to the questions everyone asks.")),
             B(ch("server-guide", "🧭", topic="Where everything is and how the server works."))]
    return cat("Important", "📢", chans + (extra or []), read_only=True, writable_by=writers or STAFF)


def community(extra=None, general="general", topic="Talk about anything. Keep it friendly."):
    chans = [ch(general, "💬", topic=topic, slowmode=2),
             N(ch("introductions", "🙋", topic="Tell us who you are and what brought you here.")),
             ch("media", "📸", topic="Pictures, clips and screenshots (SFW).", slowmode=10),
             N(ch("memes", "😂", topic="Memes (SFW).")),
             N(ch("bot-commands", "🤖", topic="Use bot commands here so other channels stay clean.")),
             B(ch("off-topic", "🌀", topic="Anything that doesn't fit elsewhere.")),
             B(ch("question-of-the-day", "🗳️", topic="One question a day. Answer in a thread.")),
             B(ch("counting", "🔢", topic="Count up one number at a time. Don't count twice in a row."))]
    return cat("Community", "💬", chans + (extra or []))


def events_cat(extra=None, writers=None):
    w = writers or STAFF
    chans = [ch("events", "📅", topic="Upcoming events.", read_only=True, writable_by=w),
             N(ch("event-chat", "🎟️", topic="Talk about the current event.")),
             B(ch("giveaways", "🎁", topic="Giveaways and contests.", read_only=True, writable_by=w)),
             B(ch("polls", "📊", topic="Vote on what happens next.", read_only=True, writable_by=w))]
    return N(cat("Events", "🎉", chans + (extra or [])))


def feedback_cat(extra=None):
    chans = [ch("suggestions", "💡", "forum", "One post per idea. Upvote with a reaction.",
                tags=["Idea", "Planned", "Done", "Declined"]),
             N(ch("server-feedback", "📣", topic="Tell staff what to improve.")),
             B(ch("report-a-user", "🚩", topic="Report problems. Staff will reply privately.", slowmode=30))]
    return cat("Feedback", "💡", chans + (extra or []))


def staff_cat(extra=None, visible=None):
    v = visible or STAFF_ALL
    chans = [ch("staff-chat", "💬", topic="Private: staff only."),
             ch("mod-log", "📋", topic="Private: AutoMod alerts and staff actions."),
             N(ch("staff-announcements", "📌", topic="Private: staff news and decisions.")),
             N(ch("reports", "🚨", topic="Private: user reports and how they were handled.")),
             B(ch("mod-commands", "🔨", topic="Private: run moderation bot commands here.")),
             B(ch("Staff Meeting", "🔐", "voice"))]
    return cat("Staff", "🔒", chans + (extra or []), private=True, visible_to=v)


def voice_cat(extra=None, lounge="Lounge"):
    return cat("Voice", "🔊", [ch(lounge, "🔊", "voice"), N(ch("Chill", "🛋️", "voice")), *(extra or []),
                               N(ch("Music", "🎵", "voice")), ch("AFK", "💤", "voice")])


PRESETS: dict[str, dict] = {}

# ---------------------------------------------------------------- software
PRESETS["software"] = {
    "summary": "Software product community: news, support forums, testers, feedback, staff.",
    "settings": SETTINGS,
    "roles": ladder(staff_roles(), [
        role("Developer", "#14B8A6", {"preset": "member", "add": ["manage_threads", "manage_messages"]},
             hoist=True, mentionable=True),
        role("Helper", "#22C55E", "helper", hoist=True, mentionable=True),
        N(role("Content Creator", "#A855F7", "member", hoist=True)),
        role("Tester", "#06B6D4", "member"),
        N(role("Supporter", "#EC4899", "member", hoist=True)),
    ], role("Member", "#94A3B8", "member"),
        ping_roles([N(role("Update Ping", "#06B6D4", "cosmetic", mentionable=True, self_assignable=True)),
                    B(role("Beta Ping", "#14B8A6", "cosmetic", mentionable=True, self_assignable=True))])),
    "categories": [
        important([ch("changelog", "🛠️", topic="What changed in each version."),
                   N(ch("sneak-peek", "👀", topic="Early looks at what's coming.")),
                   B(ch("roadmap", "🗺️", topic="What we're building next.")),
                   N(ch("downloads", "📥", topic="Official download links only."))]),
        community([ch("showcase", "🖼️", topic="Show your setups and creations.", slowmode=30),
                   N(ch("content-creator", "📽️", topic="Videos and streams by our Content Creators.",
                        read_only=True, writable_by=["Content Creator"] + STAFF))], general="lobby"),
        cat("Support", "🆘", [ch("help", "🆘", "forum", "Ask anything. One post per question.",
                                 tags=["Question", "Solved"]),
                              ch("bug-reports", "🐞", "forum", "One post per bug: version, OS, steps, what happened.",
                                 tags=["Windows", "Crash", "Install", "Fixed"]),
                              ch("install-help", "💿", topic="Download and first-launch problems.", slowmode=5),
                              N(ch("tips-and-tricks", "✨", topic="Share how you use it.")),
                              B(ch("known-issues", "🧯", topic="Problems we know about and workarounds.",
                                   read_only=True, writable_by=["Developer"] + STAFF))]),
        feedback_cat([B(ch("feature-requests", "🧩", "forum", "One feature per post.",
                           tags=["Requested", "Planned", "Shipped"]))]),
        N(cat("Dev Talk", "💻", [ch("dev-chat", "💻", topic="Programming and building things."),
                                 N(ch("plugins", "🔌", topic="Plugins, mods and integrations.")),
                                 B(ch("api-help", "🧑‍🔧", "forum", "Questions about the API and scripting."))])),
        events_cat(),
        cat("Testing", "🧪", [ch("testers", "🧪", topic="Private: testers and staff."),
                              ch("test-builds", "📦", topic="Private: early builds."),
                              N(ch("tester-feedback", "📝", topic="Private: what worked and what broke."))],
            private=True, visible_to=["Tester", "Developer"] + STAFF),
        staff_cat([ch("dev-lobby", "🧑‍💻", topic="Private: development talk.")]),
        voice_cat([ch("Stage", "🎙️", "stage"), N(ch("Pair Programming", "👥", "voice")),
                   B(ch("Support Call", "🎧", "voice"))]),
    ],
    "rules": BASE_RULES + ["Bug reports go in the bug-reports forum, one post per bug.",
                           "Self-promotion only in showcase, and only if it's related."],
    "rules_channel": "rules", "welcome_channel": "announcements", "rules_gate": True, "member_role": "Member",
    "welcome_message": "Welcome to {server}! Read the rules, pick your roles in self-roles, and say hi in the lobby. "
                       "Questions go in help, bugs in bug-reports.",
    "automod": COMMON_AUTOMOD,
}

# ---------------------------------------------------------------- gaming
PRESETS["gaming"] = {
    "summary": "Gaming community: LFG, clips, tournaments, game nights, ranks.",
    "settings": SETTINGS,
    "roles": ladder(staff_roles(), [
        N(role("Event Host", "#F97316",
               {"preset": "member", "add": ["manage_events", "create_events", "mute_members", "move_members"]},
               hoist=True, mentionable=True)),
        role("Pro Player", "#FACC15", "member", hoist=True),
        N(role("Streamer", "#A855F7", "member")),
        B(role("Team Captain", "#F472B6", "member", hoist=True)),
    ], role("Gamer", "#22C55E", "member"),
        ping_roles([role("LFG Ping", "#06B6D4", "cosmetic", mentionable=True, self_assignable=True),
                    N(role("Game Night Ping", "#8B5CF6", "cosmetic", mentionable=True, self_assignable=True))]),
        regions=True, pronouns=False),
    "categories": [
        important([N(ch("patch-notes", "🛠️", topic="Game updates and server changes."))]),
        community([ch("clips", "🎬", topic="Your best plays.", slowmode=15),
                   B(ch("setups", "🖥️", topic="Show your gaming setup."))]),
        cat("Gaming", "🎮", [ch("looking-for-group", "🤝", topic="Find teammates. Say game, region, rank."),
                             ch("game-chat", "🕹️", topic="Talk about the games you play."),
                             ch("strategies", "🧠", "forum", "Guides, builds and tips.", tags=["Guide", "Question"]),
                             N(ch("ranked", "📈", topic="Ranked grind, rank-ups and duo queue.")),
                             N(ch("game-news", "📰", topic="News and updates about our games.")),
                             B(ch("free-games", "🆓", topic="Free game deals (official stores only).")),
                             B(ch("achievements", "🏅", topic="Brag about your wins."))]),
        cat("Competitive", "🏆", [ch("tournaments", "🏆", topic="Brackets, sign-ups and results.", read_only=True,
                                     writable_by=["Event Host"] + STAFF),
                                  N(ch("scrims", "⚔️", topic="Find practice matches.")),
                                  N(ch("leaderboard", "📊", topic="Top players this season.", read_only=True,
                                       writable_by=["Event Host"] + STAFF)),
                                  B(ch("team-recruitment", "📝", "forum", "Teams looking for players and players "
                                       "looking for teams.", tags=["LFT", "LFP"]))]),
        events_cat(writers=["Event Host"] + STAFF),
        feedback_cat(),
        staff_cat(),
        voice_cat([ch("Squad 1", "🎮", "voice"), ch("Squad 2", "🎮", "voice"), N(ch("Squad 3", "🎮", "voice")),
                   ch("Tournament", "🏆", "voice"), N(ch("Streaming", "📡", "voice")),
                   B(ch("Duo Queue", "👥", "voice")), B(ch("Game Night Stage", "🎙️", "stage"))]),
    ],
    "rules": BASE_RULES + ["No cheating, hacks or selling accounts.", "Keep trash talk friendly."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Gamer",
    "welcome_message": "Welcome to {server}! Read the rules, grab your game and ping roles in self-roles, "
                       "and find a squad in looking-for-group.",
    "automod": COMMON_AUTOMOD,
}

# ---------------------------------------------------------------- study
_STUDY_STAFF = ["Owner", "Organizer", "Moderator"]
PRESETS["study"] = {
    "summary": "Study group: subjects, homework help, resources, focus rooms.",
    "settings": {**SETTINGS, "verification_level": "low"},
    "roles": ladder([
        role("Owner", "#F5B841", "administrator", hoist=True),
        role("Organizer", "#E5484D", "admin", hoist=True),
        role("Moderator", "#3B82F6", "moderator", hoist=True),
        role("Tutor", "#22C55E", "helper", hoist=True, mentionable=True),
    ], [N(role("Top Helper", "#14B8A6", "member", hoist=True)),
        B(role("Note Taker", "#06B6D4", "member"))],
        role("Student", "#94A3B8", "member"),
        [role("Study Session Ping", "#F97316", "cosmetic", mentionable=True, self_assignable=True),
         N(role("Exam Reminder Ping", "#EF4444", "cosmetic", mentionable=True, self_assignable=True)),
         N(role("Math", "#3B82F6", "cosmetic", self_assignable=True)),
         N(role("Science", "#22C55E", "cosmetic", self_assignable=True)),
         B(role("Languages", "#A855F7", "cosmetic", self_assignable=True)),
         B(role("Coding", "#14B8A6", "cosmetic", self_assignable=True))],
        levels=[N(role("Scholar (Lv 20)", "#8B5CF6", "cosmetic", hoist=True)),
                N(role("Dedicated (Lv 10)", "#10B981", "cosmetic"))]),
    "categories": [
        cat("Start Here", "📌", [ch("rules", "📜", topic="Read first."),
                                 ch("announcements", "🔔", "announcement", "Exams, deadlines and sessions."),
                                 ch("welcome", "👋", topic="Introduce yourself."),
                                 ch("self-roles", "🎨", topic="Pick your subjects and reminders."),
                                 B(ch("how-to-ask", "❔", topic="How to ask a good question."))],
            read_only=True, writable_by=_STUDY_STAFF),
        cat("Study", "📚", [ch("general", "💬", topic="Chat and check-ins."),
                            ch("homework-help", "❓", "forum", "One post per question. Show what you tried.",
                               tags=["Math", "Science", "Languages", "Solved"]),
                            ch("resources", "🔗", topic="Notes, links and past papers."),
                            ch("goals", "🎯", topic="Daily goals and wins."),
                            ch("schedule", "🗓️", topic="Study sessions and exam dates."),
                            N(ch("accountability", "🤝", topic="Post what you'll do; report back later.")),
                            N(ch("wins", "🏅", topic="Grades, finished essays and small victories.")),
                            B(ch("study-memes", "😂", topic="Procrastination memes, in moderation."))]),
        N(cat("Subjects", "🧪", [ch("math", "➗", topic="Algebra to calculus."),
                                 ch("science", "🔬", topic="Biology, chemistry, physics."),
                                 ch("languages", "🗣️", topic="Language learning and practice."),
                                 ch("coding", "💻", topic="Programming help and projects."),
                                 B(ch("history", "🏛️", topic="History and social studies.")),
                                 B(ch("english", "📖", topic="Essays, reading and writing.")),
                                 B(ch("art-and-music", "🎨", topic="Creative subjects."))])),
        N(cat("Lounge", "☕", [ch("off-topic", "🌀", topic="Breaks and chat."),
                               N(ch("bot-commands", "🤖", topic="Pomodoro and other bot commands.")),
                               B(ch("music-recs", "🎵", topic="Study playlists.")),
                               B(ch("introductions", "🙋", topic="Who you are, what you study."))])),
        cat("Focus", "⏱️", [ch("Focus Room 1", "🔇", "voice"), ch("Focus Room 2", "🔇", "voice"),
                            ch("Group Study", "🗣️", "voice"), ch("Pomodoro", "🍅", "voice"),
                            N(ch("Tutoring", "🧑‍🏫", "voice")), B(ch("Library (silent)", "📚", "voice")),
                            B(ch("Lecture Hall", "🎙️", "stage"))]),
        feedback_cat(),
        cat("Staff", "🔒", [ch("organizers", "💬", topic="Private."), ch("mod-log", "📋", topic="Private."),
                            N(ch("tutor-chat", "🧑‍🏫", topic="Private: tutors and staff.")),
                            B(ch("reports", "🚨", topic="Private: user reports."))],
            private=True, visible_to=_STUDY_STAFF + ["Tutor"]),
    ],
    "rules": ["Be kind and patient. Everyone learns at their own pace.",
              "No cheating: don't share live exam answers or do someone's graded work for them.",
              "Show what you've tried when you ask for help.",
              "Keep focus rooms quiet; cameras and mics are optional.",
              "No spam or unrelated self-promotion.",
              "Follow Discord's Terms of Service and Community Guidelines."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Student",
    "welcome_message": "Welcome to {server}! Pick your subjects in self-roles, post your goal for the week in "
                       "goals and join a focus room any time.",
    "automod": COMMON_AUTOMOD[:3],
}

# ---------------------------------------------------------------- creator
PRESETS["creator"] = {
    "summary": "Creator fanbase: uploads, streams, fan art, supporter perks.",
    "settings": SETTINGS,
    "roles": ladder(staff_roles(), [
        role("Creator", "#A855F7", "admin", hoist=True),
        N(role("Editor", "#14B8A6", "member")),
        B(role("Artist", "#F472B6", "member")),
        role("Supporter", "#EC4899", "member", hoist=True),
        N(role("VIP", "#FACC15", "member", hoist=True)),
    ], role("Fan", "#94A3B8", "member"),
        ping_roles([role("Stream Pings", "#F97316", "cosmetic", mentionable=True, self_assignable=True),
                    N(role("Upload Pings", "#EF4444", "cosmetic", mentionable=True, self_assignable=True))])),
    "categories": [
        important([ch("new-uploads", "🎬", topic="Every new video and stream."),
                   ch("schedule", "🗓️", topic="Stream and upload schedule."),
                   N(ch("socials", "🔗", topic="All official links."))]),
        community([ch("fan-art", "🎨", topic="Your art. Credit the artist.", slowmode=30),
                   N(ch("stream-chat", "📡", topic="Chat during live streams.", slowmode=3)),
                   N(ch("clips", "✂️", topic="Best moments from streams.")),
                   B(ch("fan-theories", "🔮", "forum", "Theories and discussions."))]),
        cat("Content", "📺", [ch("video-ideas", "💡", "forum", "Suggest a video. One idea per post.",
                                 tags=["Idea", "Planned", "Done"]),
                              N(ch("feedback-on-videos", "📝", topic="What you liked and what to change.")),
                              B(ch("collabs", "🤝", topic="Creators who want to collab.")),
                              B(ch("behind-the-scenes", "🎥", topic="How the videos get made.", read_only=True,
                                   writable_by=["Creator", "Editor"] + STAFF))]),
        cat("Supporters", "⭐", [ch("supporter-chat", "⭐", topic="Thanks for the support!"),
                                 ch("early-access", "👀", topic="Early cuts and behind the scenes."),
                                 N(ch("supporter-polls", "📊", topic="Vote on what comes next."))],
            private=True, visible_to=["Supporter", "VIP", "Creator"] + STAFF),
        events_cat(writers=["Creator"] + STAFF),
        feedback_cat(),
        staff_cat([ch("editing", "✂️", topic="Private: editors and creator.", private=True,
                      visible_to=["Editor", "Creator"] + STAFF)]),
        voice_cat([ch("Watch Party", "🍿", "voice"), ch("Stage", "🎙️", "stage"),
                   N(ch("Gaming With Fans", "🎮", "voice")), B(ch("Supporter Lounge", "⭐", "voice", private=True,
                                                                 visible_to=["Supporter", "VIP", "Creator"] + STAFF))]),
    ],
    "rules": BASE_RULES + ["No leaks of early-access content.", "No hate towards other creators."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Fan",
    "welcome_message": "Welcome to {server}! Turn on Stream Pings in self-roles so you never miss a stream.",
    "automod": COMMON_AUTOMOD,
}

# ---------------------------------------------------------------- roleplay
_RP_STAFF = ["Owner", "Game Master", "Moderator"]
PRESETS["roleplay"] = {
    "summary": "Roleplay server: lore, character sheets, in-character scenes, OOC chat.",
    "settings": SETTINGS,
    "roles": ladder([
        role("Owner", "#F5B841", "administrator", hoist=True),
        role("Game Master", "#E5484D", "admin", hoist=True, mentionable=True),
        role("Moderator", "#3B82F6", "moderator", hoist=True),
        N(role("Lore Keeper", "#14B8A6", {"preset": "member", "add": ["manage_threads"]}, hoist=True)),
    ], [role("Approved Character", "#22C55E", "member"),
        N(role("Character Pending", "#F59E0B", "member")),
        B(role("Artist", "#F472B6", "member"))],
        role("Adventurer", "#94A3B8", "member"),
        [role("Quest Ping", "#F97316", "cosmetic", mentionable=True, self_assignable=True),
         N(role("Plot Event Ping", "#8B5CF6", "cosmetic", mentionable=True, self_assignable=True)),
         N(role("Knight", "#64748B", "cosmetic", self_assignable=True)),
         N(role("Mage", "#6366F1", "cosmetic", self_assignable=True)),
         B(role("Rogue", "#1F2937", "cosmetic", self_assignable=True)),
         B(role("Healer", "#10B981", "cosmetic", self_assignable=True))],
        levels=[B(role("Legendary Hero (Lv 30)", "#F59E0B", "cosmetic", hoist=True)),
                N(role("Seasoned (Lv 10)", "#10B981", "cosmetic"))],
        pronouns=True),
    "categories": [
        cat("Gateway", "📜", [ch("rules", "📜", topic="Read first."),
                              ch("announcements", "🔔", "announcement", "Plot events and news."),
                              ch("welcome", "🚪", topic="Arrivals."),
                              ch("self-roles", "🎨", topic="Pick your class and pings."),
                              N(ch("how-to-start", "🧭", topic="How to make a character and join a scene."))],
            read_only=True, writable_by=_RP_STAFF),
        cat("World", "🌍", [ch("lore", "📖", topic="The world's history and factions.", read_only=True,
                               writable_by=["Lore Keeper", "Game Master", "Owner"]),
                            ch("map", "🗺️", topic="Locations.", read_only=True,
                               writable_by=["Lore Keeper", "Game Master", "Owner"]),
                            ch("character-sheets", "🧾", "forum", "One post per character. Staff approve.",
                               tags=["Pending", "Approved", "Retired"]),
                            N(ch("factions", "🛡️", topic="The factions and how to join.", read_only=True,
                                 writable_by=["Lore Keeper", "Game Master", "Owner"])),
                            N(ch("bestiary", "🐉", topic="Creatures of the world.", read_only=True,
                                 writable_by=["Lore Keeper", "Game Master", "Owner"])),
                            B(ch("timeline", "⏳", topic="What happened when.", read_only=True,
                                 writable_by=["Lore Keeper", "Game Master", "Owner"]))]),
        cat("In Character", "⚔️", [ch("tavern", "🍺", topic="In character only.", slowmode=5),
                                   ch("wilds", "🌲", topic="In character only.", slowmode=5),
                                   ch("city", "🏰", topic="In character only.", slowmode=5),
                                   ch("quests", "🗡️", "forum", "One thread per quest."),
                                   N(ch("market-square", "🛒", topic="In character: trade and haggle.", slowmode=5)),
                                   N(ch("castle", "👑", topic="In character only.", slowmode=5)),
                                   B(ch("dungeon", "🕯️", topic="In character only.", slowmode=5)),
                                   B(ch("harbor", "⚓", topic="In character only.", slowmode=5))],
            private=True, visible_to=["Approved Character"] + _RP_STAFF),
        cat("Out of Character", "💬", [ch("ooc-chat", "💬", topic="Out-of-character talk."),
                                       ch("art", "🎨", topic="Character art."),
                                       N(ch("introductions", "🙋", topic="Introduce yourself (not your character).")),
                                       N(ch("rp-help", "❓", topic="Questions about the rules or the world.")),
                                       N(ch("bot-commands", "🎲", topic="Dice rolls and bot commands.")),
                                       B(ch("memes", "😂", topic="RP memes.")),
                                       B(ch("writing-tips", "✍️", topic="Get better at writing scenes."))]),
        feedback_cat(),
        events_cat(writers=_RP_STAFF),
        cat("Staff", "🔒", [ch("gm-planning", "🗺️", topic="Private."), ch("mod-log", "📋", topic="Private."),
                            N(ch("sheet-review", "✅", topic="Private: approve character sheets.")),
                            B(ch("plot-ideas", "💭", topic="Private: future arcs."))],
            private=True, visible_to=_RP_STAFF + ["Lore Keeper"]),
        voice_cat([ch("Campaign Table", "🎲", "voice"), N(ch("Campaign Table 2", "🎲", "voice")),
                   B(ch("Story Stage", "🎙️", "stage"))], lounge="OOC Lounge"),
    ],
    "rules": BASE_RULES + ["No godmodding or controlling other people's characters.",
                           "Keep in-character channels in character; use ooc-chat otherwise.",
                           "Character sheets must be approved before you post in-character."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Adventurer",
    "welcome_message": "Welcome to {server}, traveller! Read the lore, post your character sheet, and a Game "
                       "Master will approve it.",
    "automod": COMMON_AUTOMOD[:3],
}

# ---------------------------------------------------------------- community / friends (new)
PRESETS["community"] = {
    "summary": "General community / friends hangout: chat, media, hobbies, events, voice.",
    "settings": SETTINGS,
    "roles": ladder(staff_roles(), [
        N(role("Event Host", "#F97316", {"preset": "member", "add": ["manage_events", "create_events"]},
               hoist=True, mentionable=True)),
        role("VIP", "#FACC15", "member", hoist=True),
        B(role("Artist", "#F472B6", "member")),
    ], role("Member", "#94A3B8", "member"),
        ping_roles([N(role("Movie Night Ping", "#8B5CF6", "cosmetic", mentionable=True, self_assignable=True)),
                    B(role("Chat Revive Ping", "#22C55E", "cosmetic", mentionable=True, self_assignable=True))]),
        regions=True),
    "categories": [
        important(),
        community([N(ch("selfies", "🤳", topic="Selfies (only your own, SFW).", slowmode=30)),
                   B(ch("vent", "🫂", topic="Need to talk? Be kind. For emergencies contact local services.",
                        slowmode=30))]),
        cat("Hobbies", "🎨", [ch("gaming", "🎮", topic="Games you're playing."),
                              ch("music-share", "🎵", topic="Share tracks."),
                              N(ch("pets", "🐾", topic="Pet pics.")),
                              ch("art", "🖌️", topic="Your art. Credit the artist.", slowmode=30),
                              N(ch("movies-and-tv", "🍿", topic="What you're watching.")),
                              N(ch("food", "🍔", topic="What's cooking.")),
                              B(ch("sports", "⚽", topic="Games, scores and hot takes.")),
                              B(ch("tech", "💻", topic="Gadgets, PCs and setups.")),
                              B(ch("books", "📚", topic="What you're reading."))]),
        events_cat(writers=["Event Host"] + STAFF),
        feedback_cat(),
        staff_cat(),
        voice_cat([ch("Hangout", "🎉", "voice"), N(ch("Game Room", "🎮", "voice")),
                   N(ch("Movie Night", "🍿", "voice")), B(ch("Late Night", "🌙", "voice")),
                   B(ch("Town Hall", "🎙️", "stage"))]),
    ],
    "rules": BASE_RULES + ["Respect people's boundaries and privacy; don't share others' personal info."],
    "rules_channel": "rules", "welcome_channel": "welcome", "rules_gate": True, "member_role": "Member",
    "welcome_message": "Welcome to {server}! Read the rules, pick a colour and pings in self-roles, "
                       "and introduce yourself.",
    "automod": COMMON_AUTOMOD,
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
    "community": "Community / friends hangout",
    "orrin": "Exact ORRIN layout",
}


def _keep(item, rank: int) -> bool:
    return _RANK.get(item.get("tier", "small"), 0) <= rank


def resize(plan: dict, size: str = "big") -> dict:
    """Drop items above `size`, drop emptied categories and dangling role references, strip tier tags."""
    size = size if size in _RANK else "big"
    rank = _RANK[size]
    p = copy.deepcopy(plan)
    p["roles"] = [r for r in p.get("roles", []) if not isinstance(r, dict) or _keep(r, rank)]
    names = {r["name"] if isinstance(r, dict) else r for r in p["roles"]}

    def refs(v):
        return [n for n in v if n in names or n.lstrip("@").lower() == "everyone"]

    cats = []
    for c in p.get("categories", []):
        if not _keep(c, rank):
            continue
        c["channels"] = [x for x in c.get("channels", []) if _keep(x, rank)]
        for x in [c] + c["channels"]:
            x.pop("tier", None)
            for k in ("visible_to", "writable_by"):
                if k in x:
                    x[k] = refs(x[k])
        if c["channels"]:
            cats.append(c)
    p["categories"] = cats
    for r in p["roles"]:
        if isinstance(r, dict):
            r.pop("tier", None)
    if p.get("member_role") and p["member_role"] not in names:
        p["member_role"] = ""
    return p


def get(name: str, size: str = "big") -> dict:
    p = resize(PRESETS[name], size)
    p.setdefault("source", f"preset:{name}")
    return p
