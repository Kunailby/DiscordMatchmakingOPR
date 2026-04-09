"""Discord matchmaking cog with slash commands for One Page Rules."""

import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from storage import MatchmakingStorage

logger = logging.getLogger(__name__)

FACTIONS = ["AOF", "GDF"]


class Matchmaking(commands.Cog):
    """Cog handling matchmaking slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = MatchmakingStorage()
        self._queue_lock = asyncio.Lock()
        self.auto_reset.start()

    # ------------------------------------------------------------------
    # /matchmaking command
    # ------------------------------------------------------------------

    @app_commands.command(name="matchmaking", description="Join, show, or leave matchmaking.")
    @app_commands.describe(
        action="Action to perform",
        system="Your system choice (required for Join)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Join", value="join"),
            app_commands.Choice(name="Show", value="show"),
            app_commands.Choice(name="Leave", value="leave"),
        ],
        system=[
            app_commands.Choice(name="AOF", value="AOF"),
            app_commands.Choice(name="GDF", value="GDF"),
        ],
    )
    async def matchmaking(
        self,
        interaction: discord.Interaction,
        action: str,
        system: app_commands.Choice[str] | None = None,
    ):
        if action == "join":
            await self._handle_join(interaction, system)
        elif action == "show":
            await self._handle_show(interaction)
        elif action == "leave":
            await self._handle_leave(interaction)

    # ------------------------------------------------------------------
    # /matchmaking reset  (admin only)
    # ------------------------------------------------------------------

    @app_commands.command(name="matchmaking_reset", description="Clear all queues and matches (Admin only).")
    @app_commands.checks.has_permissions(administrator=True)
    async def matchmaking_reset(self, interaction: discord.Interaction):
        self.storage.reset_all()
        await interaction.response.send_message(
            "🧹 **MATCHMAKING RESET** — All queues and matches have been cleared.",
            ephemeral=False,
        )
        logger.info("Matchmaking data reset by %s", interaction.user)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    async def _handle_join(
        self,
        interaction: discord.Interaction,
        system_choice: app_commands.Choice[str] | None,
    ):
        if system_choice is None:
            await interaction.response.send_message(
                "⚠️ You must specify a system (`AOF` or `GDF`) when joining.",
                ephemeral=True,
            )
            return

        system = system_choice.value
        user_id = interaction.user.id
        username = interaction.user.display_name

        async with self._queue_lock:
            if self.storage.is_in_queue(user_id):
                await interaction.response.send_message(
                    "⚠️ You are already in the matchmaking queue.", ephemeral=True
                )
                return

            if self.storage.is_in_match(user_id):
                await interaction.response.send_message(
                    "⚠️ You are already in a confirmed match. You cannot join the queue.",
                    ephemeral=True,
                )
                return

            # Check if there is someone waiting to pair with
            if self.storage.queue:
                opponent = self.storage.queue.pop(0)
                self.storage.add_match(
                    opponent,
                    {"user_id": user_id, "username": username, "system": system},
                )

                opponent_mention = f"<@{opponent['user_id']}>"
                await interaction.response.send_message(
                    f"⚔️ **MATCH FOUND!** {opponent_mention} vs {interaction.user.mention}!"
                )
            else:
                self.storage.add_to_queue(user_id, username, system)
                await interaction.response.send_message(
                    f"🕰️ {interaction.user.mention} has joined the queue with system **{system}**. Waiting for an opponent…"
                )

    async def _handle_show(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Matchmaking Status",
            colour=discord.Colour.blurple(),
            timestamp=datetime.now(timezone.utc),
        )

        # Active matches
        if self.storage.matches:
            match_lines = []
            for m in self.storage.matches:
                p1 = m["player1"]["username"]
                p2 = m["player2"]["username"]
                s1 = m["player1"]["system"]
                s2 = m["player2"]["system"]
                match_lines.append(f"⚔️ **{p1}** ({s1}) vs **{p2}** ({s2})")
            embed.add_field(name="Active Matches", value="\n".join(match_lines), inline=False)
        else:
            embed.add_field(name="Active Matches", value="No active matches.", inline=False)

        # Waiting players
        if self.storage.queue:
            wait_lines = []
            for p in self.storage.queue:
                wait_lines.append(f"🕰️ **{p['username']}** ({p['system']}): WAITING OPPONENT")
            embed.add_field(name="Waiting in Queue", value="\n".join(wait_lines), inline=False)
        else:
            embed.add_field(name="Waiting in Queue", value="No players waiting.", inline=False)

        await interaction.response.send_message(embed=embed)

    async def _handle_leave(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        async with self._queue_lock:
            if self.storage.is_in_match(user_id):
                await interaction.response.send_message(
                    "❌ You are already in a confirmed match. You cannot leave.", ephemeral=True
                )
                return

            if not self.storage.is_in_queue(user_id):
                await interaction.response.send_message(
                    "⚠️ You are not in the matchmaking queue.", ephemeral=True
                )
                return

            self.storage.remove_from_queue(user_id)

        await interaction.response.send_message(
            "👋 You have been removed from the matchmaking queue.", ephemeral=True
        )

    # ------------------------------------------------------------------
    # Scheduled auto-reset — second Thursday of every month
    # ------------------------------------------------------------------

    @tasks.loop(hours=1)
    async def auto_reset(self):
        """Check hourly if today is the second Thursday and reset if so."""
        now = datetime.now(timezone.utc)
        # Only act on Thursdays (weekday() == 3)
        if now.weekday() != 3:
            return

        # Calculate which Thursday of the month this is
        # Week 1 = days 1-7, Week 2 = days 8-14, etc.
        week_number = (now.day - 1) // 7 + 1

        if week_number == 2:
            last_reset_key = "last_auto_reset_date"
            last_reset = self.storage.data.get(last_reset_key)
            if last_reset == now.strftime("%Y-%m-%d"):
                return

            logger.info("Auto-reset triggered: second Thursday of the month.")
            self.storage.reset_all()
            self.storage.data[last_reset_key] = now.strftime("%Y-%m-%d")
            self.storage._save_data()

            # Announce in all guild channels if possible
            for guild in self.bot.guilds:
                channel = guild.system_channel
                if channel and channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(
                            "🧹 **SCHEDULED MAINTENANCE** — It's the second Thursday of the month! "
                            "All matchmaking queues and matches have been reset."
                        )
                    except discord.Forbidden:
                        pass

    @auto_reset.before_loop
    async def before_auto_reset(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Matchmaking(bot))
