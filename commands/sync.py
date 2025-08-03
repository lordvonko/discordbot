import discord
from discord.ext import commands
from discord import app_commands

class Sync(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Synchronizes commands globally.")
    @commands.is_owner()
    async def sync(self, interaction: discord.Interaction):
        """Synchronizes all slash commands globally.

        This command is owner-only and ensures that the bot's commands are
        available across all servers it is a member of.
        """
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"Synced {len(synced)} commands globally.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to sync commands globally: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Sync(bot))