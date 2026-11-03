# Designing a good Discord server: what the guides agree on

These notes are what ORRIN Architect's presets, its built-in planner and its AI prompt are built
on. They were distilled on 2026-11-02 from the English transcripts of **105 YouTube
server-setup videos** (searches such as "how to make a good discord server", "discord server
setup guide", "best discord server channels and roles", "discord onboarding setup", "discord
level roles", "how to make a gaming discord server"; 116 had captions, 105 were
on-topic and long enough to use) plus **3 written guides** (jagrosh's "Tips for creating and
growing a new Discord server", PeakBot's "How to organize Discord channels and categories" and
wikiHow's "Discord channel ideas"). Everything below is summarised in our own words; nothing is
copied. The table at the end says how many of the 105 videos talked about each pattern.

## 1. Layout: categories in reading order

A newcomer reads the channel list top to bottom, so it should read like a path:

1. **📢 Info / Start Here** (read-only for members): `rules`, `announcements` (an Announcement
   channel, so other servers can follow it), `welcome`, `roles-info` (what each role means and
   how to get it), `self-roles` (the role picker), `faq` / `server-guide`. Guides keep these
   names plain on purpose.
2. **💬 Community**: `general` (with a short slowmode when busy), `introductions`, `media`
   (clips/screenshots, slowmode), `memes`, `bot-commands` (keeps bot spam out of chat),
   `off-topic`, and "activity" channels that keep a server alive: `question-of-the-day`,
   `counting`, `pets`.
3. **The server's own topic** (the thing it is about): e.g. LFG / game chat / strategies /
   ranked for gaming; help + bug-report forums for a software product; subjects for a study
   server; content / video-ideas for a creator; lore / character sheets / in-character scenes
   for roleplay. Guides stress that a server with a clear topic grows and a "random hangout"
   doesn't.
4. **🎉 Events**: `events` (read-only), `event-chat`, `giveaways`, `polls`.
5. **💡 Feedback / Support**: `suggestions` as a **forum** (one idea per post, tags such as
   Planned / Done), `server-feedback`, a reporting route (`report-a-user` or a ticket bot).
6. **🔒 Staff** (private): `staff-chat`, `mod-log` (AutoMod alerts + bot logs), `reports`,
   `staff-announcements`, `mod-commands`, a staff voice room.
7. **🔊 Voice** at the bottom: a lounge, topic rooms (squads, study rooms, watch party,
   music), an **AFK** channel, a **Stage** for big talks.

Other layout advice that came up again and again:
- One clear purpose per channel; merge near-duplicates instead of adding a second "chat".
  Order matters more than count: a big server can feel calm if it is grouped well.
- Decorate consistently: an emoji per channel, and a recognisable category header style
  (e.g. `📢 | IMPORTANT | 📢`, `╭📜︱rules`, `・`, `┃`, `【】`). Fancy fonts hurt search and
  screen readers; emoji plus a separator are enough.
- Hide what members don't need yet behind permissions (staff areas, tester/supporter areas,
  in-character channels until a sheet is approved) rather than cluttering the list.
- Discord's **Onboarding** (Community servers) wants at least 7 default channels, 5 of which
  members can talk in; questions there can hand out the same ping / colour / region roles.

## 2. Roles: the ladder, top to bottom

Order in the role list is power and colour: the highest coloured role decides a member's
name colour, and a role can only manage roles below it.

1. **Owner** (the one role with Administrator; most guides say give Administrator to as few
   roles as possible, never to bots or helpers "just in case").
2. **Admin** (manage server/channels/roles, ban), optionally **Co-Owner** above it.
3. **Moderator** (kick, timeout, manage messages, view audit log, move/mute in voice).
4. **Trial Mod / Helper** (timeout, manage messages; a probation step before Moderator).
5. **Bots**: one role for bots, placed above the roles they hand out (reaction-role and
   levelling bots can only give roles below them) with only the permissions they need.
6. **Special roles**: VIP, Event Host, Content Creator, Streamer, Pro Player, Supporter,
   Developer, Tester, Tutor, Artist…
7. **Colour roles** (self-assign, no permissions): kept above level roles so a picked colour
   shows.
8. **Level roles** (given by a levelling/XP bot at e.g. Lv 5 / 10 / 25 / 50: Active,
   Regular, Veteran, Legend). Some servers attach small perks (images, embeds, reactions)
   to them.
9. **The base member role** (Member / Gamer / Student / Fan…) that carries the normal chat
   permissions, given when someone accepts the rules or finishes verification.
10. **Ping roles** (self-assign, mentionable): Announcement Ping, Event Ping, Giveaway Ping,
    plus topic pings (LFG, Stream, Upload, Game Night, Study Session). These replace
    @everyone pings so people choose what they're notified about.
11. **Identity roles** (self-assign, no permissions): pronouns (He/Him, She/Her,
    They/Them), region (NA / EU / Asia…), games played, subjects, RP class.

Role settings the guides agree on: "display separately" (hoist) only for staff and a few
special roles; "allow anyone to @mention" only for ping roles (and maybe moderators); colour,
ping and identity roles carry **no** permissions; self-assigned roles never get dangerous
permissions. A "Muted" role is outdated: Discord's built-in **Timeout** does the job.

## 3. Permissions

- Start from a locked-down **@everyone** (read, react, connect; no mention @everyone, no
  managing anything) and grant chat through the member role.
- Read-only info channels: deny Send Messages for @everyone/member, allow it for staff.
- Private categories: deny View Channel for @everyone, allow it for the roles that belong;
  let channels sync to the category so one change covers them all.
- Turn off "Mention @everyone, @here and All Roles" for everyone except senior staff.
- Use slowmode on busy and media channels; use forums for help, suggestions and showcases.
- Default notifications to **mentions only**; verification level **medium** or higher for
  public servers; explicit media filter on for all members.

## 4. Onboarding, rules and safety

- Short, numbered rules (respect, no spam/DM ads, SFW, no scams, right channel, follow
  Discord's ToS, staff decisions) in a read-only `rules` channel, with an "I accept" step
  (rules screening, a verify button or Onboarding) that gives the member role.
- A welcome message that says what the server is and the first three things to do.
- AutoMod: spam, mention spam, slurs/sexual content presets, plus a keyword list for scam bait
  ("free nitro", fake gift links), alerting to the mod-log.
- Keep bots few and audited; check what role commands a bot exposes.

## 5. Keeping it alive

Activity channels (question of the day, counting, polls), regular events with an Event Ping
role, giveaways, levels that reward chatting, staff who actually talk, and a feedback channel
that gets answers. Several guides say the same thing bluntly: pick a clear topic, and don't
open 40 dead channels for 5 members, which is why ORRIN Architect has a `size:` option.

## How ORRIN Architect uses this

- Every preset is written at **big** size and trimmed for `normal` and `small`.
- The built-in planner and the AI post-processor top thin plans up to a minimum
  (normal: 12 roles / 20 text channels; big: 16 roles / 26 text channels) from the patterns
  above, without removing anything planned.
- The AI prompt carries a ~1,000-character digest of sections 1–3 (`architect/knowledge.py`).
- The bot posts a self-role picker (buttons) in `#self-roles` for every colour, ping and
  identity role.

## How often each pattern came up (105 videos)

"Mentioned" means the topic came up in that video's transcript, not that the video agreed
with it. Auto-captions mishear words ("role" as "roll"), so these are rough counts.

| Pattern | Videos |
|---|---|
| lock down @everyone permissions | 61 |
| staff roles (mod/admin ladder) | 58 |
| categories to group channels | 58 |
| emoji/symbols in channel names | 56 |
| a rules channel | 55 |
| a welcome channel / welcome message | 51 |
| a general chat | 50 |
| levels / level roles / XP bot | 49 |
| voice channels | 49 |
| announcements (announcement channel type) | 36 |
| events | 34 |
| Community server features | 31 |
| self-assign / reaction / button roles | 29 |
| role hierarchy (bots/staff above members) | 29 |
| never give Administrator casually | 28 |
| media / memes channels | 27 |
| Onboarding (Discord's own) | 26 |
| server boosts | 26 |
| region / age / timezone roles | 24 |
| mod-log / audit log channel | 23 |
| verification level / verify step | 22 |
| display role members separately (hoist) | 22 |
| AutoMod | 20 |
| introductions channel | 19 |
| forum channels | 18 |
| read-only info channels | 18 |
| ticket / support system | 17 |
| timeout instead of a muted role | 15 |
| a server guide / FAQ | 15 |
| a Bots role | 15 |
| bot-commands channel | 12 |
| giveaways | 12 |
| ping / notification roles | 12 |
| art / showcase channel | 10 |
| staff-only chat | 10 |
| suggestions channel | 9 |
| polls | 9 |
| AFK voice channel | 7 |
| stage channel | 7 |
| slowmode | 6 |
| colour roles | 5 |
| off-topic channel | 4 |
| pronoun roles | 3 |
| counting / question-of-the-day / activity channels | 3 |
| game roles | 1 |
| LFG / looking-for-group | 0 |

## Sources

Written guides: gist.github.com/jagrosh/342324d7084c9ebdac2fa3d0cd759d10 ·
peakbot.pro/blog/how-to-organize-discord-channels-and-categories ·
wikihow.com/Discord-Channel-Ideas

Videos (105):

- (2026) Create Application System For your Discord Server | MOD/STAFF Application System | Appy (youtube.com/watch?v=KVNtGNyy9XE)
- (2026) Create LEVELING System For your Discord Server ( Easy ) | Level Roles setup Discord (youtube.com/watch?v=p77EpCR9UAc)
- 10 Best Discord Server Templates (Aesthetic, Gaming, Community) (youtube.com/watch?v=PgLp6FR59Tc)
- 30 PROVEN Discord Hacks For Building Communities (youtube.com/watch?v=SJi469BuU6g)
- 5 Features EVERY Discord Server Should Have! (youtube.com/watch?v=-vXSBiXTAxs)
- 7 DISCORD Tips to Grow a Server and Keep it Active - A Guide (youtube.com/watch?v=eGWFdScSrr4)
- [DISCORD TUTORIAL] SETUP LEVELS IN YOUR DISCORD SERVER Using Arcane ─ iimelodyxh 🕯🍒💌 (youtube.com/watch?v=K63e7rAR8DM)
- Beginner-Friendly Discord Server Tutorial! (youtube.com/watch?v=sCEQDXZ_vIw)
- Build a Pro Discord Gaming Server from Scratch - Complete Tutorial (youtube.com/watch?v=GJxWEhm1iEg)
- Create An EPIC DISCORD SERVER In 2024 (FREE TEMPLATE) (youtube.com/watch?v=ALFqYy-H8Dw)
- Creating Categories & Channels in Discord (youtube.com/watch?v=_TSiTC8qSfA)
- Discord Server Permissions and Roles Tutorial | Member, Moderator, Admin Role Setup Guide (youtube.com/watch?v=LSkPwZ0x6hc)
- Discord Server Setup for Beginners – Gaming, Friends & Music (Step-by-Step) (youtube.com/watch?v=vL20nr00r2s)
- Discord Tutorial - Roles and Permissions (youtube.com/watch?v=iH6zp24IES8)
- Discord’s New BETA Channels & Roles! (youtube.com/watch?v=2vwYy4qUaiM)
- Every Text Channel Permission on Discord EXPLAINED! (youtube.com/watch?v=Y4fpvu29qqU)
- Features EVERY Discord Server Should Have! (2021) (youtube.com/watch?v=nr7znBHe6Vk)
- Free Discord Level / Rank Roles (Arcane Bot Setup) (youtube.com/watch?v=8WKvCXNqzxM)
- How Discord Works in 148,000 Miliseconds or Less (youtube.com/watch?v=TJ13BA3-NR4)
- How to Add Reaction Roles in Discord Server - Complete Guide (youtube.com/watch?v=y1Em-hErW9I)
- How To Become A Discord Moderator & Make Money! (youtube.com/watch?v=o1iCVuAPytM)
- How to become the BEST, Discord Moderator! (youtube.com/watch?v=Ddg5mt0XIK0)
- How To Build The Best Discord Staff Team | Discord Tutorials #3 (youtube.com/watch?v=43ypjymC_58)
- How to Change Server Permissions for All Members on Discord Mobile (Full Guide 2026) (youtube.com/watch?v=KKrSwUcj-XI)
- How to Create a Discord Server | Invite Friends, Create Channels & Categories (youtube.com/watch?v=F6-7gAxE-h0)
- How to Create a Discord Server: Complete Setup Guide 2026 (youtube.com/watch?v=ALr_AUXg4GU)
- How to Create A Gaming Server in Discord (youtube.com/watch?v=L4GDXM-I_RM)
- How To Create A Gaming Server In Discord (2026 Easy Guide) (youtube.com/watch?v=94Uq95ABn9c)
- How to Create and Set Up Custom Roles in Discord Step by Step (youtube.com/watch?v=q-2Lm_WlEAQ)
- How To Create Auto Rank Roles With Arcane Bot On Discord (2026) (youtube.com/watch?v=m7Xh4s5dvcs)
- How to Create Categories in Discord [2026 Full Guide] (youtube.com/watch?v=2LeNpwPmKqw)
- How to Disable @everyone Permissions on Your Discord Server (2025 Tutorial) (youtube.com/watch?v=C4YpBc2O5Ps)
- How to form and use a staff structure in a discord server! (youtube.com/watch?v=TiyUf4oiqpE)
- How to Grow a Discord Server FAST in 2026 (Real Methods That Actually Work) (youtube.com/watch?v=vH0VZgndcUk)
- How To Grow Your Discord Server (Easy Guide) (youtube.com/watch?v=Em3s3wuty88)
- How To Grow Your Discord Server (Fastest Methods!) (youtube.com/watch?v=Me-HtJoDYVE)
- How to GROW your Discord Server! (youtube.com/watch?v=xM01NFoDac8)
- How to Instantly Get a Guild Tag Server – No Boosts, Full Ownership (Discord 2025 Tutorial) (youtube.com/watch?v=o5geuQ-Cdns)
- How to Lock Roles in Your Discord Server (Full Guide) (youtube.com/watch?v=KOHELcEr5H8)
- How to Make a Moderator Role on Discord (Mod Role Permissions & Set Up) (youtube.com/watch?v=KA_ZgMmv4Ag)
- How To Make A Read Only Channel In Discord Server - Full Guide (youtube.com/watch?v=t6USTiqc-Rw)
- How to Make a Read Only Channel on Discord (youtube.com/watch?v=d58ufIhzc7s)
- How to Make a Small Discord Server for Friends (youtube.com/watch?v=e7tNoODmyTY)
- How To Make An Aesthetic Discord Server [2026 Guide] (youtube.com/watch?v=GAzAplhz2J4)
- How to Make an Aesthetic Discord Welcome Message with Carl Bot (youtube.com/watch?v=fXgJVT3AJJQ)
- How to make an EPIC Discord server (TUTORIAL) (youtube.com/watch?v=sEWCqjFZBMk)
- HOW To Make an EPIC DISCORD SERVER 2025 (Tips) (youtube.com/watch?v=ZpYyv7u1MLE)
- How to Make Reaction Roles on Discord - 2025 (Easy Guide) (youtube.com/watch?v=LPz9UQWwibM)
- How To Make Reaction Roles On Discord - Full Guide (youtube.com/watch?v=q5LO5uSBrr8)
- How To Make Reaction Roles On Discord - Step By Step (youtube.com/watch?v=x5_E3PGtUcw)
- How to Make Someone a Moderator on Discord (2025) (youtube.com/watch?v=6aIqcNM8nsA)
- How to Set Up a Discord Server (youtube.com/watch?v=BM8Jt8nFzo4)
- How to Set Up Channel Permissions in Discord Server Step by Step (youtube.com/watch?v=jWzQkrMGXMc)
- How to Set up Discord Onboarding (2026 Step By Step Guide) (youtube.com/watch?v=RZ_J8pc558I)
- How To Set Up Discord Onboarding (2026) (youtube.com/watch?v=xEQqtMvQ1hY)
- How to Set Up Discord Onboarding - Create Reaction Roles (youtube.com/watch?v=YjBna-qlW_s)
- How to Set up Discord Onboarding [2026 Full Guide] (youtube.com/watch?v=pDmmbhLT_Dk)
- How to Set Up Discord Permissions and Roles (Updated 2026) (youtube.com/watch?v=31np_swFbBY)
- How to Set Up Your First Discord Server (FREE Template 2026) (youtube.com/watch?v=JsnoaSmpHzA)
- How to Setup & Create a Discord Forum/Gallery Channel - Discord Community Server Setup Guide 2024 (youtube.com/watch?v=41THfsgL-dc)
- How to Setup a Community Discord Server In 2024 (FREE TEMPLATE) (youtube.com/watch?v=Y6eAWB1j8FU)
- How to Setup a Discord Server 2024 - The ULTIMATE Discord Setup Tutorial WITH Bots! (youtube.com/watch?v=R-J3fiBu9A8)
- How to Setup a Discord Server 2025 - The ULTIMATE Discord Setup Tutorial WITH Bots! (youtube.com/watch?v=1xKPtNy1PjM)
- How to Setup a Discord Server 2026 - The ULTIMATE Discord Setup Tutorial WITH Bots! (youtube.com/watch?v=8dbZ1HSZvaA)
- How to Setup a Discord Server EASILY in 2026 + BOTS (youtube.com/watch?v=KzHK_LznxtI)
- How To Setup a Discord Server for a Community (2026) (youtube.com/watch?v=6O3gxQcjC5U)
- How to Setup a Discord Server in 2026 (Full Step-by-Step Guide) (youtube.com/watch?v=0LUnT5oQgP4)
- How to Setup a Discord Server in Under 3 Minutes 2026! (youtube.com/watch?v=m32Aiizmeps)
- How to Setup a Level System in Discord! (youtube.com/watch?v=sZlB69vIIU0)
- How To Setup Discord Level Rank Roles - Full Guide (youtube.com/watch?v=yHDn8qDc0H8)
- How To Setup Discord Level Role Ranks With Arcane Bot - Full Guide (youtube.com/watch?v=6q_MDW3jbsk)
- How To Setup Discord Onboarding (Complete Guide) (youtube.com/watch?v=sy1vcm9RSvo)
- How to Setup Discord Onboarding in 2026 (Full Step-by-Step Tutorial) (youtube.com/watch?v=TpKDpTk-0XI)
- How to Setup Discord Onboarding! (BEST Discord Reaction Roles) (youtube.com/watch?v=5LmtYDZ_8n8)
- How To Setup Discord Onboarding... (youtube.com/watch?v=9Abwc7_9F9k)
- How To Setup Discord Reaction Roles with Sapphire Bot (youtube.com/watch?v=b_S1U96f60w)
- How To Setup Discord Server Levels... (youtube.com/watch?v=zxXjSFLn5qY)
- How To Setup Level Roles / Rank Roles (Arcane Bot Setup) (youtube.com/watch?v=M7zMFREiO1E)
- How to Setup Level Roles on Discord | Free And Easy! (youtube.com/watch?v=Hg_ni4n8Z6c)
- How to Setup Reaction Roles with Mimu and Carl-Bot (youtube.com/watch?v=tQRnl_XQxkg)
- How to setup SERVER GUIDE on DISCORD (youtube.com/watch?v=4SvP00-xvCY)
- How to Use Discord in 2026 | Beginner's Guide (Not Just for Gamers) (youtube.com/watch?v=J4fiGkg1nbc)
- I Fully Renovated a Bad Discord Server — Server Overhaul: Episode 1 (youtube.com/watch?v=HWUloe4oC68)
- I Made a Discord Server in 1 Minute, 10 Minutes & 1 Hour (youtube.com/watch?v=1uZwN6_6YXQ)
- Level Up your Discord Server with Onboarding (youtube.com/watch?v=UdcD-ac8rKw)
- Make A Discord Server to FIX YOUR LIFE (Productivity Server Template) (youtube.com/watch?v=eqf2ErjvfRc)
- Make a NICE Discord Server FAST (Under 5 mins) (youtube.com/watch?v=XsYWNu3Pfz4)
- Must-Have 30+ Discord Server Templates for Quick Setup! (youtube.com/watch?v=so-jzieZE_c)
- Productivity Discord Server Setup Tutorial! (youtube.com/watch?v=K4WoasbHuJ8)
- REACTION ROLES With BUTTONS & Selection Menus | Step-by-step Tutorial (youtube.com/watch?v=n5RrCJYlEno)
- SET UP YOUR DISCORD SERVER QUICKLY! | start to finish tutorial (youtube.com/watch?v=6bZMNtHaDjg)
- Setup Discord Button Roles (2022!) (youtube.com/watch?v=oYg7nH0TRTk)
- Setup Discord Server Level / Rank Roles (Lurkr Bot Setup) (youtube.com/watch?v=zWRmOh_T36I)
- The BEST Discord Reaction Roles - Discord Onboarding Setup Guide! (youtube.com/watch?v=uSxJKPWFMCY)
- The COMPLETE Discord Server Guide 2026 - Aesthetic Layouts & Bot Setup (youtube.com/watch?v=IIaqpPTrZZM)
- The Secrets to Owning a Big Discord Server (youtube.com/watch?v=GufZzqzmdoY)
- The Ultimate Discord Server Setup for Your Business (2025 Guide) (youtube.com/watch?v=FY0gy26e8aM)
- The Ultimate Guide to Discord Onboarding (Setup & Customize) (youtube.com/watch?v=2q8HF6zgqow)
- The Ultimate Guide To Discord Server Setup 2025! (youtube.com/watch?v=T9N-W_EObYk)
- The Ultimate Guide To Discord Server Setup 2026! (youtube.com/watch?v=CiUGZOqWf0E)
- The Ultimate Guide: Discord Permissions (youtube.com/watch?v=HKRP65747OY)
- Top 7 BEST Discord Server Templates (youtube.com/watch?v=vb0NU9v_jgE)
- ULTIMATE Discord Server Setup In 2024! - FULL Guide (youtube.com/watch?v=ApazcdJbD1k)
- Watch This Before You Start A Discord Server! (youtube.com/watch?v=39kkYlxvjmI)
- ˗ˏˋ ★ ˎˊ˗How to make your Discord servers aesthetic/detailed˗ˏˋ ★ ˎˊ˗ | Discord | cherryblossom (youtube.com/watch?v=uV9cSFUKF70)
