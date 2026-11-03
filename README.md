# ORRIN Architect

A Discord bot that builds a whole server from a text prompt. Add it to a server, type
`/setup prompt: a chill gaming clan with tournaments and a music corner`, look at the preview, press
**Confirm**, and it creates the categories, channels, roles, permissions, rules, welcome post and
AutoMod for you. It's styled like the ORRIN server: `📢 | IMPORTANT | 📢` category headers and
`╭📜︱rules` channel names.

Free to run, MIT licensed. It plans with the free local AI on your PC (Ollama), and still works
with no AI at all thanks to its built-in planner.

## What it does

| Command | What happens |
|---|---|
| `/setup prompt:<description>` | Plans a layout and shows a preview with ✅ Confirm · ✖️ Cancel · 🔄 Regenerate |
| `/setup ... size:big\|normal\|small` | How big to build. **big** (default) ≈ 25 roles and 30+ text channels plus voice, forum and stage; **normal** ≈ 17 roles and 20+ text channels; **small** ≈ 8 roles and 10 text channels. Saying "small server for friends" in the prompt also picks small |
| `/setup ... mode:replace` | Replaces the current layout. Asks twice, and saves a full backup first |
| `/setup preset:<name>` | Builds a built-in preset: software product (like ORRIN), gaming community, study group, creator fanbase, roleplay, community/friends hangout, or the ORRIN layout (works with `size:` too) |
| `/setup-undo` | Reverts the last setup in this server |
| `/template save name:<n>` | Saves this server's current layout (copy the ORRIN server, then load it anywhere) |
| `/template load name:<n>` | Previews and builds a saved template (or `preset:gaming` etc.) |
| `/template list` | Lists the saved templates and presets |
| `/architect-help` | Quick help |

**New in 1.1: bigger, better servers.** The presets and the planner follow what Discord
server-setup guides actually recommend (notes from 105 setup videos and 3 written guides in
[`knowledge/server_design.md`](knowledge/server_design.md)):

- **Roles, top to bottom:** Owner (the only full admin) → Admin → Moderator → Trial Mod →
  Bots → special roles (Event Host, Pro Player, Streamer, VIP…) → colour roles → level roles
  (Active Lv 5 → Legend Lv 50) → the member role → ping roles (announcements, events,
  giveaways, LFG…) → pronoun / region roles.
- **Channels** in emoji-header categories, in the order a newcomer reads them: 📢 Important
  (rules, announcements, welcome, roles-info, self-roles, faq, server-guide) → 💬 Community
  (general, introductions, media, memes, bot-commands, off-topic, question-of-the-day,
  counting…) → the server's own topics → 🎉 Events → 💡 Feedback → 🔒 Staff → 🔊 Voice.
- **Self-role picker:** the bot posts buttons in `#self-roles` so members pick their own
  colour, ping and pronoun roles (tap again to remove). It only ever hands out roles with no
  permissions.
- **Thin AI plans get topped up:** if the local AI plans too few roles or channels for the
  size you chose, the missing basics (staff ladder, bots, levels, colours, pings, info,
  community, events, staff and voice channels) are added. Nothing it planned is removed.
- The AI prompt now carries a short digest of those guides, and asks Ollama not to "think"
  first, so `/setup` answers much faster with qwen3.

Level roles are created for you; hand them out with any levelling bot (or by hand).

**What a plan contains:** categories with an emoji header; text, voice, forum, announcement and
stage channels with topics and slowmode; roles with colours and real permission sets (full admin
for the top role only, plus admin, moderator, helper, member and colour/ping-only roles); private
categories (e.g. Staff or Testers) and read-only channels (rules, announcements) made with
permission overwrites; a rules post with an **"I accept the rules"** button that gives new people the
Member role (the rules gate); a welcome post; AutoMod (spam, mention spam, slurs/sexual content,
scam-bait keywords) alerting to a log channel; verification level, explicit-media filter,
mentions-only notifications and Community mode.

**Safety rules built in**
- Only server administrators can run it. Optionally lock it to your own user ID (`ARCHITECT_OWNER_IDS`).
- Default mode is **add**: it never deletes or edits anything that's already there. Existing
  channels and roles with the same name are kept as they are.
- **replace** deletes old channels and roles only after a second, red confirmation, and only after
  a JSON backup of the whole layout is saved under `data/backups/`. `/setup-undo` rebuilds the old
  layout. Messages in deleted channels can't come back, and the button says so.
- Every change is logged in a private `#architect-log` channel and in `data/journal/`.
- It checks Discord's limits before touching anything (500 channels, 250 roles, 50 channels per
  category, 100-character names, AutoMod caps), and caps one plan at 20 categories, 150 channels
  and 40 roles (a big preset is about 60 channels and 30 roles).
- The AI's plan is never trusted blindly. It's validated and repaired: bad names, unknown
  permissions, too many admins, dangerous permissions on self-assignable roles, oversized topics and
  so on. If the AI answers nonsense twice, the built-in planner takes over.
- It builds in small batches with pauses, retries rate limits and server errors with backoff, and
  carries on past a single failed step. The preview message shows live progress.

## Go live in 5 steps (Windows)

You need Python 3.10 or newer ([python.org](https://www.python.org/downloads/), tick "Add to PATH").

1. **Create the bot.** Open <https://discord.com/developers/applications> → **New Application** →
   name it `ORRIN Architect` → Create. Optionally, under **General Information**, add the ORRIN icon.
2. **Get the token.** Go to the **Bot** tab → **Reset Token** → copy it. Under **Privileged Gateway
   Intents**, leave all three **off** (it doesn't need them). Turn **Public Bot** off if only you
   should be able to add it.
3. **Invite it to a server.** Copy your **Application ID** from General Information and open this
   link with your ID filled in:
   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_APPLICATION_ID&permissions=8&integration_type=0&scope=bot+applications.commands
   ```
   `permissions=8` is Administrator, which it needs to create channels, roles, AutoMod and
   overwrites. Then go to **Server Settings → Roles** and drag the **ORRIN Architect** role to the
   **top**. Roles above it are out of its reach, and the rules button can only give out roles below it.
4. **Start it.** Unzip this folder, double-click **`start.bat`**. The first run installs everything
   and opens `.env` in Notepad: paste the token after `DISCORD_TOKEN=`. Optionally add your server ID
   to `DEV_GUILD_ID` so the commands show up instantly. Save, then run `start.bat` again.
   Leave the window open; it restarts itself if it crashes.
5. **Use it.** In the server, type `/setup` and a prompt. Check the preview, then press Confirm.
   Try it on a fresh test server first.

Optional: **`install_autostart.bat`** starts it hidden every time you sign in to Windows
(`remove_autostart.bat` undoes that).

## The AI planner (free, local)

By default it asks **Ollama** on the same PC. If Ollama isn't running, it uses the built-in
planner, so `/setup` always answers.

```
winget install Ollama.Ollama      (skip if you already have it)
ollama pull qwen2.5:7b            (8 GB graphics card;  weaker PC: qwen2.5:3b or llama3.2:3b)
```
Set `OLLAMA_MODEL` in `.env` to the model you pulled. Ollama's structured-output mode forces the
model to answer in the plan's JSON shape.

Other choices in `.env`:
- `ARCHITECT_LLM=none`: built-in planner only. Instant and offline. It reads keywords (game, clan,
  study, YouTube, roleplay, app, music, art, events, market…) and blends the matching presets.
  🔄 Regenerate cycles through styles and blends.
- `ARCHITECT_LLM=openai` with `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`: any OpenAI-compatible
  endpoint, including free tiers (e.g. Groq or Google AI Studio's OpenAI-compatible endpoint).
  Check their current free-tier limits.

## Try it without Discord (dry run)

```
dry_run.bat a cozy study group for AP exams with focus rooms
python -m architect.cli "creator fanbase for my twitch streams" --variant 2
python -m architect.cli --preset orrin --json
python -m architect.cli --preset gaming --size normal
```
This prints the full plan (roles with permissions, decorated channel names, rules, AutoMod) and
changes nothing.

## Running it 24/7 for free

The bot only needs to be online when someone runs a command (and for the rules button). Free options:
- **Your own PC**: simplest, with `install_autostart.bat`. It's offline while the PC is off.
- **An old laptop or Raspberry Pi** at home: `./start.sh`. Use `ARCHITECT_LLM=none` or a free API
  if it can't run Ollama.
- **Always-free cloud VMs**: Oracle Cloud "Always Free" and Google Cloud's free-tier e2-micro can run
  a small Python bot around the clock at $0, but both ask for a card to verify the account. Read
  their current terms, and stay inside the free shapes. Those VMs are too small for Ollama: use
  `ARCHITECT_LLM=none` or a free API endpoint there.

On Linux, `start.sh` plus a systemd service or `tmux` keeps it running. No paid host is needed.

## Files

```
architect/
  bot.py              slash commands, preview buttons, rules-accept button
  planner/llm.py      Ollama / OpenAI-compatible planner (schema, retries)
  planner/fallback.py keyword -> preset blend (no AI)
  planner/expand.py   tops thin plans up to the size's minimum roles / text channels
  presets.py          software (ORRIN), gaming, study, creator, roleplay, community; sizes
  knowledge.py        the short guide digest the AI planner reads
  schema.py           plan JSON schema + validation/repair
  permissions.py      permission names -> Discord bits, role permission sets
  overwrites.py       private / read-only channel permissions
  applier.py          builds the plan (add / replace), undo, limit checks
  batching.py         rate-limit-safe batches, retries, progress
  discord_adapter.py  the discord.py calls
  storage.py          backups, journals, templates, copy-a-server
  cli.py              dry run
tests/                164 tests, including an in-memory fake server
```

Run the tests: `pip install -r requirements-dev.txt` then `python -m pytest`.

## Notes and limits

- Discord's native **Rules Screening** and **Onboarding** are set in Server Settings by hand. The
  bot's rules button does the same job: new people can read but not chat until they accept.
- Undo restores channels, categories, roles, their permissions and server settings. It can't restore
  messages or which members had a deleted role.
- Global slash commands can take a while to appear the first time. Set `DEV_GUILD_ID` for instant
  updates in your own server.
- Bot data (backups, journals, templates) lives in `data/` next to the bot. Keep it if you move the bot.

MIT © 2026 Oliver Wilson (Xaeus99). Original project. Not affiliated with Discord.
