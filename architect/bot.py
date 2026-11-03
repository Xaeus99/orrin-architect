"""ORRIN Architect - the Discord bot.

/setup prompt:<text> [mode:add|replace] [preset] [size:big|normal|small]  -> preview -> Confirm / Cancel / Regenerate
/setup-undo                                        -> undo the last setup in this server
/template save|load|list                           -> reuse layouts across servers
/architect-help
Run: python -m architect.bot   (reads .env)"""
from __future__ import annotations

import asyncio
import logging
import os
import time

import discord
from discord import app_commands

from . import __version__, presets, storage
from .applier import Applier, CapacityError, LOG_CHANNEL
from .discord_adapter import ACCEPT_PREFIX, PICK_PREFIX, DiscordAdapter
from .planner import make_plan, planner_from_env
from .preview import plan_embed
from .render import plain
from .schema import validate_plan

log = logging.getLogger("architect")
PRESET_CHOICES = [app_commands.Choice(name=v, value=k) for k, v in presets.DESCRIPTIONS.items()]
SIZE_CHOICES = [app_commands.Choice(name="big (default): ~25 roles, 30+ text channels", value="big"),
                app_commands.Choice(name="normal: ~15 roles, ~20 text channels", value="normal"),
                app_commands.Choice(name="small: ~8 roles, ~10 text channels", value="small")]
# a self-pick button never hands out a role with any of these
UNSAFE_PICK = ("administrator", "manage_guild", "manage_roles", "manage_channels", "manage_messages",
               "manage_webhooks", "manage_threads", "manage_nicknames", "manage_expressions", "manage_events",
               "kick_members", "ban_members", "moderate_members", "mention_everyone", "mute_members",
               "deafen_members", "move_members", "view_audit_log")


def pick_is_safe(role: discord.Role) -> bool:
    return not role.managed and not role.is_default() and not any(getattr(role.permissions, p, False)
                                                                  for p in UNSAFE_PICK)


MODE_CHOICES = [app_commands.Choice(name="add (keep everything, add what's missing)", value="add"),
                app_commands.Choice(name="replace (remove the old layout - asks twice)", value="replace")]


def is_allowed(member: discord.Member) -> bool:
    owners = {x.strip() for x in os.environ.get("ARCHITECT_OWNER_IDS", "").split(",") if x.strip()}
    if owners and str(member.id) not in owners:
        return False
    return member.guild_permissions.administrator


class Architect(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()   # no privileged intents needed
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.llm = planner_from_env()
        self.locks: dict[int, asyncio.Lock] = {}
        self.batch_size = int(os.environ.get("ARCHITECT_BATCH_SIZE", "5"))
        self.pause = float(os.environ.get("ARCHITECT_BATCH_PAUSE", "1.0"))
        register(self)

    async def setup_hook(self):
        gid = os.environ.get("DEV_GUILD_ID", "").strip()
        if gid:  # instant command updates while testing in one server
            g = discord.Object(id=int(gid))
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        else:
            await self.tree.sync()  # global commands can take a little while to appear

    async def on_ready(self):
        log.info("ORRIN Architect %s online as %s in %d server(s); planner: %s", __version__, self.user,
                 len(self.guilds), f"{self.llm.kind}:{self.llm.model}" if self.llm else "built-in")

    async def on_guild_join(self, guild: discord.Guild):
        ch = guild.system_channel
        if ch and ch.permissions_for(guild.me).send_messages:
            try:
                await ch.send("👋 **ORRIN Architect** is here. An admin can type `/setup` with a description "
                              "(e.g. *a chill gaming clan with tournaments*) and I'll preview a full server "
                              "layout before changing anything.")
            except discord.HTTPException:
                pass

    async def on_interaction(self, it: discord.Interaction):
        cid = (it.data or {}).get("custom_id", "") if it.type == discord.InteractionType.component else ""
        if it.guild is None:
            return
        if cid.startswith(PICK_PREFIX):
            return await self.toggle_pick(it, cid)
        if not cid.startswith(ACCEPT_PREFIX):
            return
        role = it.guild.get_role(int(cid[len(ACCEPT_PREFIX):]))
        if role is None:
            return await it.response.send_message("That role no longer exists; ask a staff member.", ephemeral=True)
        if role in it.user.roles:
            return await it.response.send_message("You're already in. 🎉", ephemeral=True)
        try:
            await it.user.add_roles(role, reason="Accepted the rules")
            await it.response.send_message(f"Welcome! You now have **{role.name}**. 🎉", ephemeral=True)
        except discord.Forbidden:
            await it.response.send_message("I couldn't give you the role (my role must be above it). "
                                           "Please tell a staff member.", ephemeral=True)

    async def toggle_pick(self, it: discord.Interaction, cid: str):
        try:
            role = it.guild.get_role(int(cid[len(PICK_PREFIX):]))
        except ValueError:
            role = None
        if role is None:
            return await it.response.send_message("That role no longer exists.", ephemeral=True)
        if not pick_is_safe(role):
            return await it.response.send_message("That role can't be self-assigned.", ephemeral=True)
        try:
            if role in it.user.roles:
                await it.user.remove_roles(role, reason="Self-role picker")
                await it.response.send_message(f"Removed **{role.name}**.", ephemeral=True)
            else:
                await it.user.add_roles(role, reason="Self-role picker")
                await it.response.send_message(f"Added **{role.name}**. Tap again to remove it.", ephemeral=True)
        except discord.Forbidden:
            await it.response.send_message("I couldn't change that role (my role must be above it). "
                                           "Please tell a staff member.", ephemeral=True)

    def lock(self, gid) -> asyncio.Lock:
        return self.locks.setdefault(gid, asyncio.Lock())


async def architect_log(guild: discord.Guild, text: str):
    ch = discord.utils.find(lambda c: plain(c.name) == LOG_CHANNEL, guild.text_channels)
    if ch:
        await ch.send(text[:1900], allowed_mentions=discord.AllowedMentions.none())


class PreviewView(discord.ui.View):
    def __init__(self, bot: Architect, author_id: int, prompt: str, mode: str, plan: dict, warns, used,
                 variant: int = 0, fixed_plan: bool = False, size: str | None = None):
        super().__init__(timeout=600)
        self.size = size
        self.bot, self.author_id, self.prompt, self.mode = bot, author_id, prompt, mode
        self.plan, self.warns, self.used, self.variant, self.fixed = plan, warns, used, variant, fixed_plan
        self.armed = False  # replace mode: second confirmation
        if fixed_plan:
            self.remove_item(self.regenerate)

    async def interaction_check(self, it: discord.Interaction) -> bool:
        if it.user.id != self.author_id:
            await it.response.send_message("Only the admin who ran /setup can use these buttons.", ephemeral=True)
            return False
        return True

    def embed(self) -> discord.Embed:
        return discord.Embed.from_dict(plan_embed(self.plan, mode=self.mode, used=self.used, warnings=self.warns,
                                                  prompt=self.prompt))

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, it: discord.Interaction, _b):
        if self.mode == "replace" and not self.armed:
            self.armed = True
            _b.label, _b.style, _b.emoji = "Yes, REMOVE the old layout and build", discord.ButtonStyle.danger, "⚠️"
            return await it.response.edit_message(
                content="⚠️ **Second confirmation.** Replace mode deletes every current channel and every role "
                        "not in this plan (messages in deleted channels are gone for good). A full layout backup "
                        "is saved first and `/setup-undo` rebuilds the old layout. Press the red button to go ahead.",
                view=self)
        for c in self.children:
            c.disabled = True
        await it.response.edit_message(content="🏗️ Building… (0%)", view=self)
        self.stop()
        await run_setup(self.bot, it, self.plan, self.mode)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, it: discord.Interaction, _b):
        self.stop()
        await it.response.edit_message(content="Cancelled. Nothing was changed.", embed=None, view=None)

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary, emoji="🔄")
    async def regenerate(self, it: discord.Interaction, _b):
        await it.response.defer()
        self.variant += 1
        self.armed = False
        self.confirm.label, self.confirm.style, self.confirm.emoji = "Confirm", discord.ButtonStyle.success, "✅"
        self.plan, self.warns, self.used = await make_plan(self.prompt, llm=self.bot.llm, variant=self.variant,
                                                           server_name=it.guild.name, size=self.size)
        await it.edit_original_response(content=None, embed=self.embed(), view=self)


async def run_setup(bot: Architect, it: discord.Interaction, plan: dict, mode: str):
    guild = it.guild
    lock = bot.lock(guild.id)
    if lock.locked():
        return await it.followup.send("A setup is already running in this server.", ephemeral=True)
    async with lock:
        started = time.monotonic()
        me = guild.me
        if not me.guild_permissions.administrator:
            return await it.edit_original_response(
                content="I need the **Administrator** permission to build a server. Re-invite me with the link "
                        "in the README (permissions=8), then run /setup again.", embed=None, view=None)
        adapter = DiscordAdapter(guild)
        snap = await adapter.snapshot()
        backup = storage.save_backup(guild.id, snap)
        last = {"t": 0.0}

        async def progress(phase, p):
            now = time.monotonic()
            if now - last["t"] < 2 and p.done < p.total:
                return
            last["t"] = now
            txt = f"🏗️ Building… **{phase}** {p.done}/{p.total}" + (f" · {p.failed} failed" if p.failed else "")
            try:
                if now - started < 14 * 60:   # interaction tokens last 15 minutes
                    await it.edit_original_response(content=txt)
            except discord.HTTPException:
                pass

        ap = Applier(adapter, batch_size=bot.batch_size, pause=bot.pause, log=lambda m: architect_log(guild, m))
        try:
            rep = await ap.apply(plan, snap, mode=mode, backup_file=backup, progress=progress)
        except CapacityError as e:
            return await it.edit_original_response(content=f"❌ Not applied: {e}", view=None)
        storage.save_journal(guild.id, rep.journal)
        # give the server owner the plan's top (Administrator) role, if they ran /setup themselves
        top = next((r for r in plan["roles"] if r["permissions"] & 8 and r.get("preset") == "administrator"), None)
        if top and it.user.id == guild.owner_id:
            role = discord.utils.get(guild.roles, name=top["name"])
            if role and role < guild.me.top_role and role not in it.user.roles:
                try:
                    await it.user.add_roles(role, reason="ORRIN Architect: server owner")
                except discord.HTTPException:
                    pass
        msg = f"✅ Done in {int(time.monotonic() - started)}s. {rep.summary()}"
        if rep.failed:
            msg += "\nFailed steps: " + "; ".join(a for a, _ in rep.failed[:8])
        if rep.notes:
            msg += "\nNotes: " + "; ".join(rep.notes[:5])
        msg += "\nNot happy with it? `/setup-undo` reverts this setup."
        try:
            await it.edit_original_response(content=msg[:2000], view=None)
        except discord.HTTPException:
            await architect_log(guild, msg)


def register(bot: Architect):
    tree = bot.tree

    async def guard(it: discord.Interaction) -> bool:
        if it.guild is None:
            await it.response.send_message("Use me inside a server.", ephemeral=True)
            return False
        if not is_allowed(it.user):
            await it.response.send_message("Only server administrators can use ORRIN Architect.", ephemeral=True)
            return False
        return True

    @tree.command(name="setup", description="Design and build this server from a description")
    @app_commands.describe(prompt="Describe the server, e.g. 'study group for AP exams with focus rooms'",
                           mode="add = keep everything (default); replace = remove the old layout first",
                           preset="Start from a built-in preset instead of the prompt",
                           size="How big: big (default), normal or small")
    @app_commands.choices(mode=MODE_CHOICES, preset=PRESET_CHOICES, size=SIZE_CHOICES)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup(it: discord.Interaction, prompt: str = "", mode: app_commands.Choice[str] = None,
                    preset: app_commands.Choice[str] = None, size: app_commands.Choice[str] = None):
        if not await guard(it):
            return
        m = mode.value if mode else "add"
        sz = size.value if size else None
        await it.response.defer(thinking=True)
        if preset:
            raw = presets.get(preset.value, sz or "big")
            raw.setdefault("server_name", it.guild.name)
            plan, warns, _e = validate_plan(raw)
            plan["welcome_message"] = plan["welcome_message"].replace("{server}", it.guild.name)
            used, fixed = f"preset:{preset.value}", True
        else:
            if not prompt.strip():
                return await it.followup.send("Give me a prompt (what the server is for) or pick a preset.")
            plan, warns, used = await make_plan(prompt, llm=bot.llm, server_name=it.guild.name, size=sz)
            fixed = False
        view = PreviewView(bot, it.user.id, prompt or preset.name, m, plan, warns, used, fixed_plan=fixed, size=sz)
        await it.followup.send(embed=view.embed(), view=view)

    @tree.command(name="setup-undo", description="Undo the last /setup in this server")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_undo(it: discord.Interaction):
        if not await guard(it):
            return
        found = storage.latest_journal(it.guild.id)
        if not found:
            return await it.response.send_message("There's no setup to undo here.", ephemeral=True)
        path, j = found
        await it.response.defer(thinking=True)
        async with bot.lock(it.guild.id):
            backup = storage.load_json(j["backup_file"]) if j.get("backup_file") and os.path.exists(j["backup_file"]) else None
            ap = Applier(DiscordAdapter(it.guild), batch_size=bot.batch_size, pause=bot.pause,
                         log=lambda m: architect_log(it.guild, m))
            rep = await ap.undo(j, backup)
            storage.save_journal(it.guild.id, j)
        await it.followup.send(f"↩️ Undone: {rep.ok} steps reverted" + (f", {len(rep.failed)} failed" if rep.failed else "")
                               + (". The old layout was rebuilt (old messages can't be restored)."
                                  if j.get("mode") == "replace" else "."))

    tg = app_commands.Group(name="template", description="Save and reuse server layouts",
                            default_permissions=discord.Permissions(administrator=True), guild_only=True)

    @tg.command(name="save", description="Save this server's current layout as a template")
    async def t_save(it: discord.Interaction, name: str):
        if not await guard(it):
            return
        snap = await DiscordAdapter(it.guild).snapshot()
        raw = storage.snapshot_to_plan(snap)
        plan, warns, errs = validate_plan(raw)
        if errs:
            return await it.response.send_message("Couldn't save: " + "; ".join(errs), ephemeral=True)
        storage.save_template(name, raw)
        await it.response.send_message(f"💾 Saved this layout as **{storage.template_name(name)}** "
                                       f"({len(plan['categories'])} categories, {len(plan['roles'])} roles).", ephemeral=True)

    @tg.command(name="load", description="Preview and build a saved template (or a preset) in this server")
    @app_commands.choices(mode=MODE_CHOICES)
    async def t_load(it: discord.Interaction, name: str, mode: app_commands.Choice[str] = None):
        if not await guard(it):
            return
        try:
            raw = presets.get(name.split(":", 1)[1]) if name.startswith("preset:") else storage.load_template(name)
        except (FileNotFoundError, KeyError, ValueError):
            return await it.response.send_message(f"No template called **{name}**. Try `/template list`.", ephemeral=True)
        plan, warns, errs = validate_plan(raw)
        if errs:
            return await it.response.send_message("That template is broken: " + "; ".join(errs), ephemeral=True)
        plan["welcome_message"] = plan["welcome_message"].replace("{server}", it.guild.name)
        view = PreviewView(bot, it.user.id, f"template {name}", mode.value if mode else "add", plan, warns,
                           f"template:{name}", fixed_plan=True)
        await it.response.send_message(embed=view.embed(), view=view)

    @t_load.autocomplete("name")
    async def t_load_ac(it: discord.Interaction, current: str):
        opts = storage.list_templates() + [f"preset:{k}" for k in presets.PRESETS]
        return [app_commands.Choice(name=o, value=o) for o in opts if current.lower() in o.lower()][:25]

    @tg.command(name="list", description="List saved templates and built-in presets")
    async def t_list(it: discord.Interaction):
        if not await guard(it):
            return
        saved = storage.list_templates()
        txt = "**Saved:** " + (", ".join(saved) if saved else "none yet") + "\n**Presets:** " + \
              ", ".join(f"preset:{k} ({v})" for k, v in presets.DESCRIPTIONS.items())
        await it.response.send_message(txt, ephemeral=True)

    tree.add_command(tg)

    @tree.command(name="architect-help", description="How ORRIN Architect works")
    async def help_(it: discord.Interaction):
        await it.response.send_message(
            "**ORRIN Architect** builds a whole server from a description.\n"
            "• `/setup prompt:<description>` → preview → ✅ Confirm / ✖️ Cancel / 🔄 Regenerate\n"
            "• `size:` big (default, ~25 roles, 30+ text channels), normal or small\n"
            "• `mode:replace` removes the old layout (asks twice, backs up first)\n"
            "• Members pick colour/ping/pronoun roles with the buttons in #self-roles\n"
            "• `/setup-undo` reverts the last setup · `/template save|load|list` reuse layouts\n"
            "Only server admins can use it. Every change is logged in #architect-log.", ephemeral=True)


def main():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and paste your bot token.")
    Architect().run(token, log_handler=None)


if __name__ == "__main__":
    main()
