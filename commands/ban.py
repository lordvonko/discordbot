import discord
from discord.ext import commands
from discord import app_commands


class Ban(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban",
                          description="Bane um usuário do servidor.")
    @app_commands.describe(member="O usuário a ser banido",
                           reason="Motivo do ban (opcional)")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self,
                  interaction: discord.Interaction,
                  member: discord.Member,
                  reason: str = "Nenhum motivo fornecido."):
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(
                f'🔨 O usuário {member.mention} foi banido. Motivo: {reason}')
        except discord.Forbidden:
            await interaction.response.send_message(
                "Eu não tenho permissão para banir este usuário.")
        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro: {e}")


async def setup(bot):
    await bot.add_cog(Ban(bot))
