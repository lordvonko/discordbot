import discord
from discord.ext import commands
from discord import app_commands


class Comandos(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="comandos", description="Mostra a lista de comandos do bot.")
    async def comandos(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏳️‍🌈 Comandos do Bot Boiolas de Tanga 🏳️‍🌈",
            description="Aqui está a lista de todos os comandos disponíveis:",
            color=0xff69b4)

        embed.add_field(
            name="👮 Moderação",
            value="`/kick member: @user reason: [motivo]` - Expulsa um usuário.\n"
            "`/ban member: @user reason: [motivo]` - Bane um usuário permanentemente.\n"
            "`/tempban member: @user duration: <duração> reason: [motivo]` - Bane um usuário temporariamente.\n"
            "`/disfarce member: @user novo_nome: {nome novo}` - Muda o apelido de um usuário.\n"
            "`/clear amount: [número]` - Limpa mensagens de um canal.",
            inline=False)
        embed.add_field(
            name="🎵 Musica",
            value=
            "`/play query: [nome_da_musica]` - Toca a música ou adiciona a fila.\n"
            "`/stop` - Para a música e limpa a fila.\n"
            "`/pause` - Para a música atual.\n"
            "`/skip` - Pula a música atual.",
            inline=False)

        embed.add_field(
            name="✨ Gerais",
            value=
            "`/fotodoparceiro member: [@user]` - Mostra a foto de perfil de alguém (ou a sua).\n"
            "`/comandos` - Mostra esta mensagem de ajuda.",
            inline=False)

        embed.set_footer(
            text=
            "Sempre que um comando novo for adicionado, esta lista será atualizada!"
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Comandos(bot))