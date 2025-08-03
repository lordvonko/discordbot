# commands/music.py
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
from collections import deque
from urllib.parse import urlparse, parse_qs


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queues = {}  # guild_id_str: deque of (audio_url, title)
        self.current_songs = {}  # guild_id_str: (audio_url, title) for the current playing song

    async def run_blocking_async(self, func, *args, **kwargs):
        """Executa uma função bloqueante de forma assíncrona."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    def get_tracks_from_spotify(self, spotify_url):
        """Extrai títulos de tracks de uma playlist ou álbum do Spotify."""
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET não configurados.")

        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))

        if 'playlist' in spotify_url:
            playlist_id = spotify_url.split('/')[-1].split('?')[0]
            results = sp.playlist_tracks(playlist_id)
            return [(track['track']['artists'][0]['name'], track['track']['name']) for track in results['items']]
        elif 'album' in spotify_url:
            album_id = spotify_url.split('/')[-1].split('?')[0]
            results = sp.album_tracks(album_id)
            return [(track['artists'][0]['name'], track['name']) for track in results['items']]
        elif 'track' in spotify_url:
            track_id = spotify_url.split('/')[-1].split('?')[0]
            track = sp.track(track_id)
            return [(track['artists'][0]['name'], track['name'])]
        return []

    def get_track_from_apple(self, apple_url):
        """Extrai título da track do Apple Music."""
        parsed_url = urlparse(apple_url)
        path_parts = parsed_url.path.split('/')
        if 'song' in path_parts:
            song_id = path_parts[-1]
            api_url = f"https://api.music.apple.com/v1/catalog/us/songs/{song_id}"
        else:
            raise ValueError("Link do Apple Music inválido. Use link de música individual.")

        # Nota: Para Apple Music, você precisaria de uma API key, mas para simplificar, vamos simular ou usar scraping básico.
        # Aqui, assumimos uma requisição simples para obter metadata (em produção, use API oficial).
        response = requests.get(apple_url)
        # Parsing simples (não ideal, use BeautifulSoup ou API)
        # Para exemplo, extraímos de <meta> tags ou similar.
        # Implementação real precisaria de parsing HTML.
        # Placeholder:
        artist = "Artista Desconhecido"
        title = "Título Desconhecido"
        # Real parsing would go here
        return [(artist, title)]  # Retorna como lista para consistência

    async def search_ytdlp_async(self, query, ydl_opts):
        """Extrai info com yt_dlp de forma assíncrona."""

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(query, download=False)

        return await self.run_blocking_async(_extract)

    async def add_to_queue(self, guild_id, tracks):
        """Adiciona tracks à fila (cada track é (audio_url, title))."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.song_queues:
            self.song_queues[guild_id_str] = deque()
        self.song_queues[guild_id_str].extend(tracks)

    async def play_next_song(self, voice_client, guild_id, channel):
        """Função recursiva para tocar a próxima música da fila."""
        guild_id_str = str(guild_id)
        if guild_id_str in self.song_queues and self.song_queues[guild_id_str]:
            audio_url, title = self.song_queues[guild_id_str].popleft()
            self.current_songs[guild_id_str] = (audio_url, title)  # Armazena a música atual

            ffmpeg_options = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                "options": "-vn",
            }

            source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)

            def after_play(error):
                if error:
                    print(f"Erro ao tocar {title}: {error}")
                if guild_id_str in self.current_songs:
                    del self.current_songs[guild_id_str]  # Remove a música atual ao terminar
                asyncio.run_coroutine_threadsafe(
                    self.play_next_song(voice_client, guild_id, channel),
                    self.bot.loop)

            voice_client.play(source, after=after_play)
        else:
            self.current_songs.pop(guild_id_str, None)  # Limpa current se fila vazia
            if voice_client.is_connected():
                await voice_client.disconnect()
            self.song_queues.pop(guild_id_str, None)

    @app_commands.command(name="play", description="Toca uma música ou a adiciona na fila.")
    @app_commands.describe(nome_da_musica="Digite o nome ou link da música/playlist")
    async def play(self, interaction: discord.Interaction, nome_da_musica: str):
        await interaction.response.defer()

        voice_channel = interaction.user.voice.channel if interaction.user.voice else None
        if not voice_channel:
            await interaction.followup.send("Você precisa estar em um canal de voz para usar este comando.")
            return

        voice_client = interaction.guild.voice_client
        if not voice_client:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)

        ydl_options = {
            "format": "bestaudio",
            "noplaylist": False
        }  # Permitir playlists agora

        try:
            tracks_to_add = []  # Lista de (audio_url, title)

            if 'open.spotify.com' in nome_da_musica:
                spotify_tracks = await self.run_blocking_async(self.get_tracks_from_spotify, nome_da_musica)
                for artist, title in spotify_tracks:
                    search_query = f"ytsearch1:{artist} {title} official audio"
                    results = await self.search_ytdlp_async(search_query, ydl_options)
                    if results.get("entries"):
                        first_track = results["entries"][0]
                        tracks_to_add.append((first_track["url"], first_track.get("title", "Música sem título")))
            elif 'music.apple.com' in nome_da_musica:
                if '/playlist/' in nome_da_musica or '/album/' in nome_da_musica:
                    await interaction.followup.send("Playlists e álbuns do Apple Music não são suportados ainda. Use Spotify ou o nome da música.")
                    return
                apple_tracks = await self.run_blocking_async(self.get_track_from_apple, nome_da_musica)
                for artist, title in apple_tracks:
                    search_query = f"ytsearch1:{artist} {title} official audio"
                    results = await self.search_ytdlp_async(search_query, ydl_options)
                    if results.get("entries"):
                        first_track = results["entries"][0]
                        tracks_to_add.append((first_track["url"], first_track.get("title", "Música sem título")))
            else:
                # Para YouTube, YT Music ou busca por nome
                query = nome_da_musica if nome_da_musica.startswith('http') else f"ytsearch1:{nome_da_musica}"
                results = await self.search_ytdlp_async(query, ydl_options)
                if 'entries' in results:  # Playlist ou busca múltipla
                    for entry in results['entries'][:50]:  # Limite 50
                        tracks_to_add.append((entry["url"], entry.get("title", "Música sem título")))
                else:  # Single track
                    tracks_to_add.append((results["url"], results.get("title", "Música sem título")))

            if not tracks_to_add:
                await interaction.followup.send("Não encontrei resultados para essa busca.")
                return

            await self.add_to_queue(interaction.guild_id, tracks_to_add)

            if voice_client.is_playing() or voice_client.is_paused():
                await interaction.followup.send(f"Adicionado {len(tracks_to_add)} música(s) à fila!")
            else:
                await interaction.followup.send(f"Tocando agora: **{tracks_to_add[0][1]}** (e mais {len(tracks_to_add)-1} na fila se houver).")
                await self.play_next_song(voice_client, interaction.guild_id, interaction.channel)

        except Exception as e:
            await interaction.followup.send(f"Erro ao processar: {str(e)}")
            print(f"Erro no /play: {str(e)}")

    @app_commands.command(name="queue", description="Mostra a fila de músicas atual.")
    async def queue(self, interaction: discord.Interaction):
        guild_id_str = str(interaction.guild_id)
        embed = discord.Embed(title="Fila de Músicas", color=discord.Color.blue())

        # Música atual
        if guild_id_str in self.current_songs:
            current_title = self.current_songs[guild_id_str][1]
            embed.add_field(name="Tocando agora:", value=current_title, inline=False)

        # Fila
        if guild_id_str in self.song_queues and self.song_queues[guild_id_str]:
            queue_list = list(self.song_queues[guild_id_str])
            for i, (url, title) in enumerate(queue_list[:10], 1):  # Mostra até 10
                embed.add_field(name=f"{i}. {title[:100]}...", value="\u200b", inline=False)
            if len(queue_list) > 10:
                embed.set_footer(text=f"E mais {len(queue_list) - 10} músicas...")
        else:
            embed.description = "A fila está vazia!"

        await interaction.response.send_message(embed=embed)

    # Os outros comandos (skip, pause, resume, stop) permanecem iguais
    @app_commands.command(name="skip", description="Pula a música que está tocando.")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and (interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused()):
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Música pulada!")
        else:
            await interaction.response.send_message("Não há nada tocando para pular.")

    @app_commands.command(name="pause", description="Pausa a música atual.")
    async def pause(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Música pausada.")
        else:
            await interaction.response.send_message("Não há nada tocando para pausar.")

    @app_commands.command(name="resume", description="Retoma a música pausada.")
    async def resume(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Música retomada!")
        else:
            await interaction.response.send_message("A música não está pausada.")

    @app_commands.command(name="stop", description="Para a música e limpa a fila.")
    async def stop(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return await interaction.response.send_message("Não estou conectado a um canal de voz.")

        guild_id_str = str(interaction.guild_id)
        if guild_id_str in self.song_queues:
            self.song_queues[guild_id_str].clear()
        self.current_songs.pop(guild_id_str, None)  # Limpa a música atual

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        await voice_client.disconnect()
        await interaction.response.send_message("Playback parado e bot desconectado!")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
    print("Cog Music adicionado ao bot!")  # Debug: Confirma setup