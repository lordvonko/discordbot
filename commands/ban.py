
import discord
from discord.ext import commands
from discord import app_commands

class Ban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Bans a user from the server.")
    @app_commands.describe(
        member="The user to ban.",
        reason="The reason for the ban (optional)."
    )
    @app_commands.default_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        """Bans a member from the server, with role hierarchy and permission checks."""
        if member == interaction.user:
            return await interaction.response.send_message("You cannot ban yourself.", ephemeral=True)
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("You cannot ban a member with an equal or higher role.", ephemeral=True)
        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("I cannot ban a member with an equal or higher role than me.", ephemeral=True)

        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"🔨 {member.mention} has been banned. Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to ban this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ban(bot))
