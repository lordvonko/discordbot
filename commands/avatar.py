
import discord
from discord.ext import commands
from discord import app_commands

class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Shows a user's avatar.")
    @app_commands.describe(member="The user whose avatar to show (optional, defaults to you).")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        """Displays a user's avatar."""
        if member is None:
            member = interaction.user

        if not member.avatar:
            return await interaction.response.send_message(f"{member.display_name} does not have a custom avatar.", ephemeral=True)

        embed = discord.Embed(
            title=f"{member.display_name}'s Avatar",
            color=discord.Color.random()
        )
        embed.set_image(url=member.avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
