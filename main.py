import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import sys
import traceback
import logging
from dotenv import load_dotenv

load_dotenv()

# Load Opus for voice support
try:
    discord.opus.load_opus('opus')
except:
    try:
        discord.opus.load_opus('libopus.so.0')
    except:
        try:
            discord.opus.load_opus('libopus-0.dll')
        except:
            print("Warning: Could not load Opus library. Voice features may not work.")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('discord_bot')

# --- Bot Configuration ---

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("Error: DISCORD_TOKEN environment variable not set. The bot cannot start.", file=sys.stderr)
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Owner Check ---

async def is_owner(interaction: discord.Interaction) -> bool:
    return await bot.is_owner(interaction.user)

# --- Core Events ---

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info("Bot is ready and operational.")
    logger.info("------")

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"An error occurred in event {event}:")
    logger.error(traceback.format_exc())

@bot.event  
async def on_command_error(ctx, error):
    logger.error(f"Command error in {ctx.command}: {error}")
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the required permissions to execute this command.")
    else:
        await ctx.send("An unexpected error occurred while processing the command.")

# --- Cog Loading ---

async def load_cogs():
    logger.info("Loading command cogs...")
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            cog_name = f'commands.{filename[:-3]}'
            try:
                await bot.load_extension(cog_name)
                logger.info(f"- Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog_name}: {e}")
                logger.error(traceback.format_exc())

# --- Main Execution ---

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except discord.LoginFailure:
        logger.error("Failed to log in - Invalid token")
    except KeyboardInterrupt:
        logger.info("Bot shutting down by user request")
    except Exception as e:
        logger.error("An unexpected error occurred while running the bot:")
        logger.error(traceback.format_exc())
