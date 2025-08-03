import discord
from discord.ext import commands
from discord import app_commands
import asyncio


class TempBan(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tempban", description="Bane um usuário temporariamente.")
    @app_commands.describe(member="O usuário a ser banido", duration="Duração (ex: 10m, 2h, 1d)", reason="Motivo do ban (opcional)")
    @app_commands.default_permissions(ban_members=True)
    async def tempban(self,
                      interaction: discord.Interaction,
                      member: discord.Member,
                      duration: str,
                      reason: str = "Nenhum motivo fornecido."):
        try:
            time_unit = duration[-1].lower()
            time_value = int(duration[:-1])

            if time_unit == 's':
                seconds = time_value
                unit_text = "segundo(s)"
            elif time_unit == 'm':
                seconds = time_value * 60
                unit_text = "minuto(s)"
            elif time_unit == 'h':
                seconds = time_value * 3600
                unit_text = "hora(s)"
            elif time_unit == 'd':
                seconds = time_value * 86400
                unit_text = "dia(s)"
            else:
                await interaction.response.send_message(
                    "Duração inválida! Use 's', 'm', 'h' ou 'd'. Ex: `10m` para 10 minutos."
                )
                return

            await member.ban(
                reason=f"{reason} (Ban temporário por {time_value}{unit_text})"
            )
            await interaction.response.send_message(
                f'🔨 O usuário {member.mention} foi banido por {time_value} {unit_text}. Motivo: {reason}'
            )

            await asyncio.sleep(seconds)

            await interaction.guild.unban(member,
                                  reason="O tempo de banimento expirou.")
            await interaction.channel.send(
                f'✅ O banimento de {member.mention} expirou e ele foi desbanido.'
            )

        except ValueError:
            await interaction.response.send_message(
                "Formato de duração inválido. Exemplo: `10m`, `2h`, `1d`.")
        except discord.Forbidden:
            await interaction.response.send_message(
                "Eu não tenho permissão para banir/desbanir este usuário.")
        except Exception as e:
            await interaction.response.send_message(f"Ocorreu um erro: {e}")


async def setup(bot):
    await bot.add_cog(TempBan(bot))