
import discord
from discord.ext import commands
from discord import app_commands

class Lock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="lock", description="Locks the current channel, preventing messages.")
    @app_commands.default_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction):
        """Prevents the @everyone role from sending messages in the channel."""
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        
        if overwrite.send_messages is False:
            return await interaction.response.send_message("🔒 This channel is already locked.", ephemeral=True)

        overwrite.send_messages = False
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await interaction.response.send_message("🔒 Channel has been locked.")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have the required permissions to lock this channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="unlock", description="Unlocks the current channel, allowing messages.")
    @app_commands.default_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        """Allows the @everyone role to send messages in the channel."""
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)

        if overwrite.send_messages is not False:
            return await interaction.response.send_message("🔓 This channel is not locked.", ephemeral=True)

        overwrite.send_messages = None  # Use None to revert to default permissions
        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await interaction.response.send_message("🔓 Channel has been unlocked.")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have the required permissions to unlock this channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Lock(bot))
