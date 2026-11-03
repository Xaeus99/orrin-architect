"""Short digest of knowledge/server_design.md for the AI planner's prompt.

Kept to ~1,000 characters on purpose: an 8B local model (qwen3:8b) needs most of its context
for the answer. The full notes, with how many guides recommended each pattern, are in
knowledge/server_design.md."""
DIGEST = (
    "What good Discord-server guides recommend: order categories the way a newcomer reads, top to bottom: "
    "INFO (rules, announcements, welcome, self-roles, roles-info, faq/server-guide; read-only for members) > "
    "COMMUNITY (general, introductions, media, memes, bot-commands, off-topic, question-of-the-day) > "
    "the server's own topic categories > EVENTS (events, giveaways, polls) > FEEDBACK/SUPPORT (suggestions "
    "and help as forums) > private STAFF (staff-chat, mod-log, reports) > VOICE (lounge, topic rooms, music, AFK). "
    "Every channel has one clear purpose; no near-duplicates. Roles top to bottom: Owner (the only "
    "administrator), Admin, Moderator, Trial Mod/Helper, Bots, special roles (VIP, event host, creator), "
    "colour roles, level roles (e.g. Lv 5/10/25/50), the base member role, ping roles (announcements, "
    "events, giveaways), pronoun/region/game roles. Hoist only staff and special roles; only staff and ping "
    "roles are mentionable; colour/ping/pronoun roles have no permissions and are self_assignable. Slowmode on "
    "busy and media channels; announcement type for news; forums for help, suggestions and showcases."
)
