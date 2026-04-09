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


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set.")
        return

    bot = commands.Bot(command_prefix=BOT_PREFIX, intents=INTENTS)

    @bot.event
    async def on_ready():
        logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Connected to {len(bot.guilds)} guild(s)")
        try:
            # Sync to each guild for instant command availability
            for guild in bot.guilds:
                try:
                    synced = await bot.tree.sync(guild=guild)
                    logger.info(f"Synced {len(synced)} command(s) to guild '{guild.name}'")
                except Exception as e:
                    logger.error(f"Failed to sync commands to guild '{guild.name}': {e}")
            # Also keep a global sync as fallback
            synced = await bot.tree.sync()
            logger.info(f"Global synced {len(synced)} slash command(s)")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}")

    # Load the matchmaking cog
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
