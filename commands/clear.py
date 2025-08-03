import discord
from discord.ext import commands
from discord import app_commands

class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Clears messages from a channel.")
    @app_commands.describe(amount="The number of messages to clear (optional, defaults to all)." )
    @app_commands.default_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = None):
        """Clears a specified number of messages, or all messages if amount is not provided."""
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            if amount is None:
                # Purge with a very large limit to clear as much as possible
                deleted = await interaction.channel.purge(limit=10000)
                await interaction.followup.send(f"🧹 Channel sweep complete! Deleted {len(deleted)} messages.", ephemeral=True)
            else:
                deleted = await interaction.channel.purge(limit=amount)
                await interaction.followup.send(f"🧹 Successfully deleted {len(deleted)} messages.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete messages in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Clear(bot))