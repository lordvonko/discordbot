import discord
from discord.ext import commands
from discord import app_commands


class Clear(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Limpa mensagens de um canal.")
    @app_commands.describe(amount="Número de mensagens a limpar (opcional, limpa o máximo se vazio)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = None):
        """
        Limpa uma quantidade de mensagens do canal.
        Se nenhum número for fornecido, tenta limpar o máximo possível (mensagens com menos de 14 dias).
        """
        try:
            await interaction.response.defer(ephemeral=True)  # Defer para evitar timeout durante purge
            if amount is None:
                deleted = await interaction.channel.purge(limit=1000)
                await interaction.followup.send(
                    f'🧹 Limpeza geral concluída! {len(deleted)} mensagens foram varridas.',
                    ephemeral=True
                )
            else:
                deleted = await interaction.channel.purge(limit=amount)
                await interaction.followup.send(f'🧹 {amount} mensagens foram para a lixeira!',
                                                ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Eu não tenho permissão para apagar mensagens neste canal.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Clear(bot))