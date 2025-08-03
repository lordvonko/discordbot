
import discord
from discord.ext import commands
from discord import app_commands

class Announce(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Sends an announcement to the channel.")
    @app_commands.describe(
        message="The message to announce.",
        mention_everyone="Whether to mention @everyone (default: False)."
    )
    @app_commands.default_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def announce(self, interaction: discord.Interaction, message: str, mention_everyone: bool = False):
        """Sends a formatted announcement to the current channel."""
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Announcement by {interaction.user.display_name}")

        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        mention = "@everyone" if mention_everyone else ""

        try:
            await interaction.response.send_message("Announcement sent!", ephemeral=True)
            await interaction.channel.send(content=mention, embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to send messages in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Announce(bot))
