import discord
from discord.ext import commands
from discord import app_commands


class Kick(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick",
                          description="Expulsa um usuário do servidor.")
    @app_commands.describe(member="O usuário a ser expulso",
                           reason="Motivo da expulsão (opcional)")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self,
                   interaction: discord.Interaction,
                   member: discord.Member,
                   reason: str = "Nenhum motivo fornecido."):
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(
                f'👢 O usuário {member.mention} foi expulso. Motivo: {reason}')
        except discord.Forbidden:
            await interaction.response.send_message(
                "Eu não tenho permissão para expulsar este usuário.")
        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro: {e}")


async def setup(bot):
    await bot.add_cog(Kick(bot))
