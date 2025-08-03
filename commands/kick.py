
import discord
from discord.ext import commands
from discord import app_commands

class Kick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kicks a user from the server.")
    @app_commands.describe(
        member="The user to kick.",
        reason="The reason for the kick (optional)."
    )
    @app_commands.default_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
        """Kicks a member from the server, with role hierarchy and permission checks."""
        if member == interaction.user:
            return await interaction.response.send_message("You cannot kick yourself.", ephemeral=True)
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("You cannot kick a member with an equal or higher role.", ephemeral=True)
        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("I cannot kick a member with an equal or higher role than me.", ephemeral=True)

        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(f"👢 {member.mention} has been kicked. Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to kick this user.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Kick(bot))
