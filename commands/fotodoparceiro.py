import discord
from discord.ext import commands
from discord import app_commands


class FotoDoParceiro(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="fotodoparceiro",
                          description="Mostra a foto de perfil de um usuário.")
    @app_commands.describe(member="O usuário (opcional, default é você mesmo)")
    async def fotodoparceiro(self,
                             interaction: discord.Interaction,
                             member: discord.Member = None):
        if member is None:
            member = interaction.user

        embed = discord.Embed(
            title=f"Foto de perfil do(a) parceiro(a) {member.display_name}",
            color=discord.Color.random())
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(
            text=f"Comando solicitado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(FotoDoParceiro(bot))
