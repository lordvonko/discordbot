import discord
from discord.ext import commands
from discord import app_commands


class Disfarce(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="disfarce", description="Muda o apelido de um usuário.")
    @app_commands.describe(member="O usuário a ser disfarçado", novo_nome="O novo apelido")
    @app_commands.default_permissions(manage_nicknames=True)
    async def disfarce(self, interaction: discord.Interaction, member: discord.Member, novo_nome: str):
        """Muda o apelido de um usuário para o nome fornecido."""

        # O Discord tem um limite de 32 caracteres para apelidos
        if len(novo_nome) > 32:
            await interaction.response.send_message("O apelido não pode ter mais de 32 caracteres!")
            return

        try:
            apelido_antigo = member.display_name
            await member.edit(nick=novo_nome)
            await interaction.response.send_message(
                f"🎭 O disfarce de **{apelido_antigo}** foi aplicado! Agora ele(a) se chama **{novo_nome}**."
            )

        except discord.Forbidden:
            # Ocorre se o bot não tiver permissão ou o cargo do membro for maior
            await interaction.response.send_message(
                "❌ Eu não tenho permissão para mudar o apelido deste usuário. Verifique minhas permissões e a hierarquia de cargos no servidor."
            )

        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro inesperado: {e}")


async def setup(bot):
    await bot.add_cog(Disfarce(bot))