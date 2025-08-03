import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import traceback


class Mensagem(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="mensagem",
        description=
        "Envia um comunicado para todos com uma mensagem personalizada.")
    @app_commands.describe(
        marcar_pessoas="Digite '@here' para marcar todos online (opcional)",
        media=
        "Formato da foto anexada: quadrado, pequena ou original (opcional)")
    @app_commands.choices(media=[
        app_commands.Choice(name="Quadrado", value="quadrado"),
        app_commands.Choice(name="Pequena", value="pequena"),
        app_commands.Choice(name="Original", value="original")
    ])
    @app_commands.default_permissions(manage_messages=True)
    async def mensagem(self,
                       interaction: discord.Interaction,
                       marcar_pessoas: str = None,
                       media: str = None):
        """Permite que um usuário com permissão envie um comunicado em formato de embed."""
        # Responde pedindo a mensagem
        await interaction.response.send_message(
            "Por favor, envie a mensagem que deseja compartilhar (pode incluir uma foto ou vídeo como anexo).",
            ephemeral=True)

        def check(msg: discord.Message):
            return msg.author == interaction.user and msg.channel == interaction.channel

        try:
            # Aguarda a mensagem do usuário por 60 segundos
            message = await self.bot.wait_for("message",
                                              check=check,
                                              timeout=60.0)

            # Formata a mensagem: se for pequena (< 50 caracteres), usa negrito e itálico
            message_content = message.content
            if len(message_content) < 50:
                message_content = f"**_{message_content}_**"

            # Cria a embed
            embed = discord.Embed(description=message_content,
                                  color=discord.Color.blue(),
                                  timestamp=discord.utils.utcnow())
            embed.set_footer(
                text=f"*Comunicado de {interaction.user.display_name}*")

            # Adiciona menção @here se especificado
            mention = "@here" if marcar_pessoas == "@here" else ""

            # Verifica anexos (foto ou vídeo) ou usa a foto do servidor como thumbnail
            file_to_send = None  # Para enviar arquivos (imagens e vídeos)
            if message.attachments:
                attachment = message.attachments[0]
                print(
                    f"Anexo detectado: {attachment.filename}, Tipo: {attachment.content_type}, Tamanho: {attachment.size} bytes"
                )  # Debug

                # Verifica se é uma imagem (por content_type ou extensão) - expandido
                is_image = (attachment.content_type
                            and attachment.content_type.startswith("image/")
                            or attachment.filename.lower().endswith(
                                ('.png', '.jpg', '.jpeg', '.gif', '.webp',
                                 '.bmp', '.tiff', '.heic', '.svg')))

                # Verifica se é um vídeo (por content_type ou extensão) - expandido
                is_video = (attachment.content_type
                            and attachment.content_type.startswith("video/")
                            or attachment.filename.lower().endswith(
                                ('.mp4', '.mov', '.avi', '.mkv', '.webm',
                                 '.wmv', '.flv', '.m4v')))

                print(
                    f"Detectado como imagem: {is_image}, Detectado como vídeo: {is_video}"
                )  # Debug extra

                if is_image or is_video:
                    # Baixa o arquivo ANTES de deletar a mensagem
                    try:
                        file_to_send = await attachment.to_file()
                        print(
                            f"Arquivo baixado com sucesso: {attachment.filename}"
                        )  # Debug
                    except Exception as download_err:
                        await interaction.followup.send(
                            f"Falha ao baixar o anexo: {str(download_err)}",
                            ephemeral=True)
                        print(f"Erro ao baixar anexo: {str(download_err)}")
                        return

                    if is_image:
                        # Define o formato da imagem com base na opção media (padrão: original)
                        media = media or "original"
                        print(f"Formato de mídia escolhido: {media}")  # Debug
                        attachment_url = f"attachment://{attachment.filename}"
                        if media in ["quadrado", "pequena"]:
                            embed.set_thumbnail(url=attachment_url)
                        elif media == "original":
                            embed.set_image(url=attachment_url)
                    elif is_video:
                        print(
                            "Vídeo será enviado como anexo (player abaixo do embed)."
                        )  # Debug
                        embed.add_field(name="📹 Vídeo",
                                        value="Veja o vídeo anexado abaixo!",
                                        inline=False)  # Confirmação visual

                else:
                    print(
                        f"Anexo não suportado - Motivo: content_type '{attachment.content_type}' não inicia com 'image/' ou 'video/', e extensão '{attachment.filename.lower()}' não reconhecida."
                    )  # Debug detalhado
                    if interaction.guild.icon:
                        embed.set_thumbnail(url=interaction.guild.icon.url)
            elif interaction.guild.icon:
                # Usa a foto do servidor como thumbnail (pequena) se não houver anexo
                embed.set_thumbnail(url=interaction.guild.icon.url)

            # Agora, deleta a mensagem do usuário (DEPOIS de baixar o anexo)
            try:
                await message.delete()
            except discord.Forbidden:
                await interaction.followup.send(
                    "Não tenho permissão para deletar sua mensagem. O comunicado será enviado mesmo assim.",
                    ephemeral=True)

            # Envia o comunicado no canal
            try:
                sent_message = await interaction.channel.send(
                    content=mention, embed=embed, file=file_to_send)
                print(
                    f"Mensagem enviada com sucesso. ID: {sent_message.id}, File enviado: {file_to_send is not None}"
                )  # Debug
            except discord.HTTPException as http_err:
                await interaction.followup.send(
                    f"Erro ao enviar o anexo (possível limite de tamanho ou rede): {str(http_err)}",
                    ephemeral=True)
                print(f"Erro HTTP no envio: {str(http_err)}")
                return

            # Confirmação para o usuário
            await interaction.followup.send("Comunicado enviado com sucesso!",
                                            ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "Você demorou demais para enviar a mensagem. Tente novamente!",
                ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                "Não tenho permissão para enviar mensagens neste canal.",
                ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro: {str(e)}",
                                            ephemeral=True)
            print(
                f"Erro no comando /mensagem: {str(e)}\n{traceback.format_exc()}"
            )


async def setup(bot):
    await bot.add_cog(Mensagem(bot))
