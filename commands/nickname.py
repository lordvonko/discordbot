import discord
from discord.ext import commands
from discord import app_commands

class Nickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="nickname", description="Changes a user's nickname.")
    @app_commands.describe(
        member="The user whose nickname to change.",
        nickname="The new nickname."
    )
    @app_commands.default_permissions(manage_nicknames=True)
    @commands.has_permissions(manage_nicknames=True)
    async def nickname(self, interaction: discord.Interaction, member: discord.Member, nickname: str):
        """Changes a user's nickname, with role hierarchy and permission checks."""
        if len(nickname) > 32:
            return await interaction.response.send_message("Nicknames cannot be longer than 32 characters.", ephemeral=True)

        if member.top_role >= interaction.user.top_role and interaction.user.id != member.id:
            return await interaction.response.send_message("You cannot change the nickname of a member with an equal or higher role.", ephemeral=True)
        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("I cannot change the nickname of a member with an equal or higher role than me.", ephemeral=True)

        try:
            await member.edit(nick=nickname)
            await interaction.response.send_message(f"🎭 {member.mention}'s nickname has been changed to **{nickname}**.")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to change this user's nickname.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Nickname(bot))