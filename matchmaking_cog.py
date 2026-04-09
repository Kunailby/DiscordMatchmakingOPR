"""Discord matchmaking cog with slash commands for One Page Rules."""

import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View

from storage import MatchmakingStorage

logger = logging.getLogger(__name__)


class RivalChallenge:
    """Stores an active rival challenge for button callbacks."""

    def __init__(self, challenger: discord.User, target: discord.User, system: str, points: str):
        self.challenger_id = challenger.id
        self.target_id = target.id
        self.challenger_name = challenger.display_name
        self.target_name = target.display_name
        self.system = system
        self.points = points


class Matchmaking(commands.Cog):
    """Cog handling matchmaking slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage = MatchmakingStorage()
        self._queue_lock = asyncio.Lock()
        self._active_challenges: dict[int, RivalChallenge] = {}  # message_id -> challenge
        self.auto_reset.start()

    # ------------------------------------------------------------------
    # /matchmaking command
    # ------------------------------------------------------------------

    @app_commands.command(name="matchmaking", description="Join, rival, show, or leave matchmaking.")
    @app_commands.describe(
        action="Action to perform",
        system="Your system choice (required for Join/Rival)",
        points="Your points value (required for Join/Rival)",
        opponent="The member you want to challenge (required for Rival)",
        leave_target="What to leave (required when action is Leave)"
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="Join", value="join"),
            app_commands.Choice(name="Rival", value="rival"),
            app_commands.Choice(name="Show", value="show"),
            app_commands.Choice(name="Leave", value="leave"),
        ],
        system=[
            app_commands.Choice(name="AOF", value="AOF"),
            app_commands.Choice(name="GDF", value="GDF"),
        ],
        points=[
            app_commands.Choice(name="1000", value="1000"),
            app_commands.Choice(name="1500", value="1500"),
            app_commands.Choice(name="2000", value="2000"),
            app_commands.Choice(name="3000+", value="3000+"),
        ],
        leave_target=[
            app_commands.Choice(name="Queue", value="queue"),
            app_commands.Choice(name="Match", value="match"),
        ],
    )
    async def matchmaking(
        self,
        interaction: discord.Interaction,
        action: str,
        system: app_commands.Choice[str] | None = None,
        points: app_commands.Choice[str] | None = None,
        opponent: discord.Member | None = None,
        leave_target: app_commands.Choice[str] | None = None,
    ):
        if action == "join":
            await self._handle_join(interaction, system, points)
        elif action == "rival":
            await self._handle_rival(interaction, opponent, system, points)
        elif action == "show":
            await self._handle_show(interaction)
        elif action == "leave":
            await self._handle_leave(interaction, leave_target)

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
        points_choice: app_commands.Choice[str] | None,
    ):
        if system_choice is None or points_choice is None:
            missing = []
            if system_choice is None:
                missing.append("system")
            if points_choice is None:
                missing.append("points")
            await interaction.response.send_message(
                f"⚠️ You must specify **{', '.join(missing)}** when joining.",
                ephemeral=True,
            )
            return

        system = system_choice.value
        points = points_choice.value
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

            # Look for a compatible opponent (same system + points)
            opponent = self.storage.find_compatible_opponent(user_id, system, points)
            if opponent:
                self.storage.remove_from_queue_by_entry(opponent)
                self.storage.add_match(
                    opponent,
                    {"user_id": user_id, "username": username, "system": system, "points": points},
                )

                opponent_mention = f"<@{opponent['user_id']}>"
                await interaction.response.send_message(
                    f"⚔️ **MATCH FOUND!** {opponent_mention} vs {interaction.user.mention}!\n"
                    f"System: **{system}** • Points: **{points}**"
                )
            else:
                self.storage.add_to_queue(user_id, username, system, points)
                await interaction.response.send_message(
                    f"🕰️ {interaction.user.mention} has joined the queue with system **{system}** ({points} pts). Waiting for an opponent…"
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
                pt1 = m["player1"].get("points", "?")
                pt2 = m["player2"].get("points", "?")
                match_lines.append(f"⚔️ **{p1}** ({s1}, {pt1} pts) vs **{p2}** ({s2}, {pt2} pts)")
            embed.add_field(name="Active Matches", value="\n".join(match_lines), inline=False)
        else:
            embed.add_field(name="Active Matches", value="No active matches.", inline=False)

        # Waiting players
        if self.storage.queue:
            wait_lines = []
            for p in self.storage.queue:
                wait_lines.append(
                    f"🕰️ **{p['username']}** ({p['system']}, {p.get('points', '?')} pts): WAITING OPPONENT"
                )
            embed.add_field(name="Waiting in Queue", value="\n".join(wait_lines), inline=False)
        else:
            embed.add_field(name="Waiting in Queue", value="No players waiting.", inline=False)

        await interaction.response.send_message(embed=embed)

    async def _handle_leave(
        self,
        interaction: discord.Interaction,
        leave_target: app_commands.Choice[str] | None,
    ):
        user_id = interaction.user.id

        if leave_target is None:
            await interaction.response.send_message(
                "⚠️ You must specify **Queue** or **Match** when leaving.", ephemeral=True
            )
            return

        target = leave_target.value

        async with self._queue_lock:
            if target == "queue":
                if not self.storage.is_in_queue(user_id):
                    await interaction.response.send_message(
                        "⚠️ You are not in the matchmaking queue.", ephemeral=True
                    )
                    return
                self.storage.remove_from_queue(user_id)
                await interaction.response.send_message(
                    "👋 You have been removed from the matchmaking queue.", ephemeral=True
                )

            elif target == "match":
                match_entry = self.storage.find_match_for_user(user_id)
                if match_entry is None:
                    await interaction.response.send_message(
                        "⚠️ You are not in any confirmed match.", ephemeral=True
                    )
                    return
                self.storage.remove_match(match_entry)
                await interaction.response.send_message(
                    "👋 You have been removed from your confirmed match.", ephemeral=True
                )

    # ------------------------------------------------------------------
    # Rival challenge handler
    # ------------------------------------------------------------------

    async def _handle_rival(
        self,
        interaction: discord.Interaction,
        opponent: discord.Member | None,
        system_choice: app_commands.Choice[str] | None,
        points_choice: app_commands.Choice[str] | None,
    ):
        if opponent is None:
            await interaction.response.send_message(
                "⚠️ You must specify an **opponent** to challenge.", ephemeral=True
            )
            return
        if system_choice is None or points_choice is None:
            missing = []
            if system_choice is None:
                missing.append("system")
            if points_choice is None:
                missing.append("points")
            await interaction.response.send_message(
                f"⚠️ You must specify **{', '.join(missing)}** when challenging a rival.",
                ephemeral=True,
            )
            return

        system = system_choice.value
        points = points_choice.value
        challenger = interaction.user

        if opponent.id == challenger.id:
            await interaction.response.send_message(
                "⚠️ You cannot challenge yourself.", ephemeral=True
            )
            return

        if opponent.bot:
            await interaction.response.send_message(
                "⚠️ You cannot challenge a bot.", ephemeral=True
            )
            return

        # Send challenge message with Accept/Decline buttons
        challenge = RivalChallenge(challenger, opponent, system, points)
        view = RivalChallengeView(challenge, self)

        embed = discord.Embed(
            title="⚔️ Rival Challenge",
            description=(
                f"**{challenge.challenger_name}** challenges **{challenge.target_name}**!\n\n"
                f"System: **{challenge.system}** • Points: **{challenge.points}**\n\n"
                f"Do you accept?"
            ),
            colour=discord.Colour.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Challenged by {challenge.challenger_name}")

        await interaction.response.send_message(
            f"{opponent.mention}, you have been challenged!",
            embed=embed,
            view=view,
        )

        # DM the challenged player
        try:
            dm_embed = discord.Embed(
                title="⚔️ New Rival Challenge",
                description=(
                    f"**{challenge.challenger_name}** has challenged you to a match!\n\n"
                    f"System: **{challenge.system}** • Points: **{challenge.points}**\n\n"
                    f"Head to the channel and click **Accept** or **Decline**."
                ),
                colour=discord.Colour.orange(),
            )
            await opponent.send(embed=dm_embed)
        except (discord.Forbidden, discord.NotFound):
            pass

        # Store challenge by message id so button callbacks can find it
        msg = await interaction.original_response()
        self._active_challenges[msg.id] = challenge

    # ------------------------------------------------------------------
    # Rival button callback handlers (called by the view)
    # ------------------------------------------------------------------

    async def _handle_rival_accept(self, challenge: RivalChallenge, interaction: discord.Interaction):
        """Accept a rival challenge — create a match."""
        async with self._queue_lock:
            target_id = interaction.user.id
            challenger_id = challenge.challenger_id

            # If the target was in the queue, remove them
            if self.storage.is_in_queue(target_id):
                self.storage.remove_from_queue(target_id)

            # If the challenger was in the queue, remove them
            if self.storage.is_in_queue(challenger_id):
                self.storage.remove_from_queue(challenger_id)

            # Check if either is already in a match
            if self.storage.is_in_match(target_id):
                await interaction.response.send_message(
                    "❌ You are already in a confirmed match and cannot accept this challenge.",
                    ephemeral=True,
                )
                return
            if self.storage.is_in_match(challenger_id):
                await interaction.response.send_message(
                    "❌ Your challenger is already in a confirmed match.",
                    ephemeral=True,
                )
                return

            # Create the match
            self.storage.add_match(
                {"user_id": challenger_id, "username": challenge.challenger_name, "system": challenge.system, "points": challenge.points},
                {"user_id": target_id, "username": challenge.target_name, "system": challenge.system, "points": challenge.points},
            )

        # Announce the match
        await interaction.response.send_message(
            f"✅ **{challenge.target_name}** accepted the challenge!\n"
            f"⚔️ **MATCH CONFIRMED!** <@{challenger_id}> vs {interaction.user.mention}!\n"
            f"System: **{challenge.system}** • Points: **{challenge.points}**"
        )

        # Notify challenger
        try:
            challenger_user = interaction.guild.get_member(challenger_id) or await interaction.guild.fetch_member(challenger_id)
            await challenger_user.send(
                f"✅ Your rival challenge has been **accepted** by **{challenge.target_name}**!\n"
                f"System: **{challenge.system}** • Points: **{challenge.points}**"
            )
        except (discord.Forbidden, discord.NotFound):
            pass

    async def _handle_rival_decline(self, challenge: RivalChallenge, interaction: discord.Interaction):
        """Decline a rival challenge."""
        await interaction.response.send_message(
            f"❌ **{challenge.target_name}** declined the challenge.", ephemeral=False
        )

        # Notify challenger
        try:
            challenger_user = interaction.guild.get_member(challenge.challenger_id) or await interaction.guild.fetch_member(challenge.challenger_id)
            await challenger_user.send(
                f"❌ Your rival challenge to **{challenge.target_name}** was **declined**."
            )
        except (discord.Forbidden, discord.NotFound):
            pass

    # ------------------------------------------------------------------
    # Scheduled auto-reset — second Friday of every month
    # ------------------------------------------------------------------

    @tasks.loop(hours=1)
    async def auto_reset(self):
        """Check hourly if today is the second Friday and reset if so."""
        now = datetime.now(timezone.utc)
        # Only act on Fridays (weekday() == 4)
        if now.weekday() != 4:
            return

        # Calculate which Friday of the month this is
        # Week 1 = days 1-7, Week 2 = days 8-14, etc.
        week_number = (now.day - 1) // 7 + 1

        if week_number == 2:
            last_reset_key = "last_auto_reset_date"
            last_reset = self.storage.data.get(last_reset_key)
            if last_reset == now.strftime("%Y-%m-%d"):
                return

            logger.info("Auto-reset triggered: second Friday of the month.")
            self.storage.reset_all()
            self.storage.data[last_reset_key] = now.strftime("%Y-%m-%d")
            self.storage._save_data()

            # Announce in all guild channels if possible
            for guild in self.bot.guilds:
                channel = guild.system_channel
                if channel and channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(
                            "🧹 **SCHEDULED MAINTENANCE** — It's the second Friday of the month! "
                            "All matchmaking queues and matches have been reset."
                        )
                    except discord.Forbidden:
                        pass

    @auto_reset.before_loop
    async def before_auto_reset(self):
        await self.bot.wait_until_ready()


class RivalChallengeView(View):
    """Interactive Accept/Decline buttons for a rival challenge. Stays up indefinitely."""

    def __init__(self, challenge: RivalChallenge, cog: "Matchmaking"):
        super().__init__(timeout=None)  # no timeout — buttons persist until clicked
        self.challenge = challenge
        self.cog = cog
        self._responded = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.challenge.target_id:
            await interaction.response.send_message(
                "⚠️ Only the challenged player can respond.", ephemeral=True
            )
            return False
        if self._responded:
            await interaction.response.send_message(
                "⚠️ This challenge has already been resolved.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Accept", style=discord.ButtonStyle.success, custom_id="rival_accept")
    async def accept_button(self, interaction: discord.Interaction, _button: Button):
        self._responded = True
        self.stop()
        # Clear challenge from lookup
        self.cog._active_challenges.pop(interaction.message.id, None)
        # Disable both buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await self.cog._handle_rival_accept(self.challenge, interaction)

    @discord.ui.button(label="❌ Decline", style=discord.ButtonStyle.danger, custom_id="rival_decline")
    async def decline_button(self, interaction: discord.Interaction, _button: Button):
        self._responded = True
        self.stop()
        # Clear challenge from lookup
        self.cog._active_challenges.pop(interaction.message.id, None)
        # Disable both buttons
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        await self.cog._handle_rival_decline(self.challenge, interaction)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Matchmaking(bot))
