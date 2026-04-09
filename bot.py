"""Main entry point for the One Page Rules Matchmaking Bot."""

import asyncio
import logging
import os

import discord
from discord.ext import commands

logger = logging.getLogger("opr_matchmaking")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.members = True

BOT_PREFIX = "!"

# The guild where our matchmaking server lives
MATCHMAKING_GUILD_ID = 1196551644645695658


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set.")
        return

    bot = commands.Bot(command_prefix=BOT_PREFIX, intents=INTENTS)

    @bot.event
    async def on_ready():
        logger.info("=" * 60)
        logger.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
        logger.info("Connected to %d guild(s)", len(bot.guilds))
        for g in bot.guilds:
            logger.info("  - Guild: '%s' (ID: %s)", g.name, g.id)

        # Force sync to the specific guild we care about
        guild = bot.get_guild(MATCHMAKING_GUILD_ID)
        if guild:
            try:
                synced = await bot.tree.sync(guild=guild)
                logger.info("Synced %d command(s) to guild '%s': %s",
                            len(synced), guild.name, [c.name for c in synced])
            except Exception as e:
                logger.error("Failed to sync to guild '%s': %s", guild.name, e)
        else:
            logger.error("Bot is NOT in guild %d! Cannot sync commands.", MATCHMAKING_GUILD_ID)

        # Global fallback sync
        try:
            synced = await bot.tree.sync()
            logger.info("Global synced %d command(s)", len(synced))
        except Exception as e:
            logger.error("Failed global sync: %s", e)

        logger.info("=" * 60)

    # Load the matchmaking cog BEFORE starting
    await bot.load_extension("matchmaking_cog")

    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    asyncio.run(main())
