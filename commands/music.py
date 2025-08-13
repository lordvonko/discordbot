import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import yt_dlp
import random
from typing import Optional
import traceback

# --- YTDL Configuration ---
yt_dlp.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'cache/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url')
        self.duration = data.get('duration')
        self.uploader = data.get('uploader')
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        
        def extract_info():
            return ytdl.extract_info(url, download=not stream)
            
        data = await loop.run_in_executor(None, extract_info)

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

    @classmethod
    async def search(cls, query, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        try:
            def search_query():
                return ytdl.extract_info(f"ytsearch:{query}", download=False)
                
            data = await loop.run_in_executor(None, search_query)
            if 'entries' in data and len(data['entries']) > 0:
                return data['entries'][0]
        except Exception as e:
            print(f"Error during search: {e}")
        return None

# --- Music Queue & State ---
class GuildMusicState:
    def __init__(self, loop):
        self.queue = asyncio.Queue()
        self.loop = loop
        self.current_song = None
        self.play_next_song = asyncio.Event()

    def __iter__(self):
        return self.queue._queue.__iter__()

    def __len__(self):
        return self.queue.qsize()

    def clear(self):
        self.queue = asyncio.Queue()

    async def player_loop(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        while True:
            self.play_next_song.clear()
            
            try:
                self.current_song = await asyncio.wait_for(self.queue.get(), timeout=300) # 5 min timeout
            except asyncio.TimeoutError:
                await voice_client.disconnect()
                return

            embed = discord.Embed(title="Now Playing", color=discord.Color.green())
            embed.add_field(name="Title", value=f"[{self.current_song.title}]({self.current_song.url})", inline=False)
            embed.add_field(name="Uploader", value=self.current_song.uploader, inline=True)
            if self.current_song.duration:
                embed.add_field(name="Duration", value=f"{int(self.current_song.duration // 60)}:{int(self.current_song.duration % 60):02d}", inline=True)
            if self.current_song.thumbnail:
                embed.set_thumbnail(url=self.current_song.thumbnail)
            
            await interaction.channel.send(embed=embed)
            
            def after_playing(error):
                if error:
                    print(f'Player error: {error}')
                self.loop.call_soon_threadsafe(self.play_next_song.set)
            
            voice_client.play(self.current_song, after=lambda e: after_playing(e))
            await self.play_next_song.wait()

# --- Music Cog ---
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.music_states = {}

    def get_music_state(self, guild_id: int):
        if guild_id not in self.music_states:
            self.music_states[guild_id] = GuildMusicState(self.bot.loop)
        return self.music_states[guild_id]

    async def cog_before_invoke(self, ctx):
        # This ensures we have a state for the guild before any command is run
        self.get_music_state(ctx.guild.id)

    async def process_playlist(self, interaction: discord.Interaction, url: str):
        loop = self.bot.loop
        state = self.get_music_state(interaction.guild.id)

        try:
            def extract_playlist():
                return ytdl.extract_info(url, download=False, process=False)
                
            playlist_info = await loop.run_in_executor(None, extract_playlist)
            if 'entries' not in playlist_info or not playlist_info['entries']:
                await interaction.followup.send("❌ Could not find any videos in that playlist.")
                return

            first_video_info = playlist_info['entries'][0]
            first_video_url = first_video_info.get('webpage_url')
            source = await YTDLSource.from_url(first_video_url, loop=loop, stream=True)
            await state.queue.put(source)

            await interaction.followup.send(f"▶️ Queued first song from **{playlist_info.get('title', 'playlist')}**. Loading the rest in the background...")
            
            asyncio.create_task(self.load_playlist_background(interaction, playlist_info['entries'][1:]))

        except Exception as e:
            await interaction.followup.send(f"An error occurred while processing the playlist: {e}")
            traceback.print_exc()

    async def load_playlist_background(self, interaction: discord.Interaction, entries: list):
        loop = self.bot.loop
        state = self.get_music_state(interaction.guild.id)
        songs_loaded = 0

        for entry in entries:
            if not interaction.guild.voice_client:
                break
            try:
                video_url = entry.get('webpage_url')
                source = await YTDLSource.from_url(video_url, loop=loop, stream=True)
                await state.queue.put(source)
                songs_loaded += 1
            except Exception as e:
                print(f"Error loading song {entry.get('title', 'N/A')}: {e}")
                continue
        
        if songs_loaded > 0:
            await interaction.channel.send(f"✅ Successfully loaded and queued **{songs_loaded}** more songs.")

    @app_commands.command(name="play", description="Plays a song or playlist.")
    @app_commands.describe(query="Song name or URL.")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            await interaction.followup.send("You are not connected to a voice channel.")
            return

        state = self.get_music_state(interaction.guild.id)

        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect()
            self.bot.loop.create_task(state.player_loop(interaction))

        if "list=" in query or "playlist" in query:
            await self.process_playlist(interaction, query)
            return

        try:
            if not query.startswith(('http', 'https')):
                search_result = await YTDLSource.search(query, loop=self.bot.loop)
                if not search_result:
                    await interaction.followup.send("❌ Could not find any song with that name.")
                    return
                query = search_result['webpage_url']

            source = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            await state.queue.put(source)
            await interaction.followup.send(f"✅ Queued **{source.title}**.")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")
            traceback.print_exc()

    @app_commands.command(name="skip", description="Skips the current song.")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Song skipped.")
        else:
            await interaction.response.send_message("Not playing anything to skip.")

    @app_commands.command(name="stop", description="Stops the music and clears the queue.")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            state = self.get_music_state(interaction.guild.id)
            state.clear()
            await interaction.guild.voice_client.disconnect()
            self.music_states.pop(interaction.guild.id, None)
            await interaction.response.send_message("⏹️ Music stopped and queue cleared.")
        else:
            await interaction.response.send_message("Not connected to a voice channel.")

    @app_commands.command(name="queue", description="Shows the current music queue.")
    async def queue(self, interaction: discord.Interaction):
        state = self.get_music_state(interaction.guild.id)
        
        if len(state) == 0 and not state.current_song:
            await interaction.response.send_message("The queue is empty.")
            return

        embed = discord.Embed(title="Music Queue", color=discord.Color.purple())
        
        if state.current_song:
            embed.add_field(name="Now Playing", value=f"[{state.current_song.title}]({state.current_song.url})", inline=False)

        if len(state) > 0:
            queue_text = ""
            for i, song in enumerate(list(state)[:10]):
                queue_text += f"{i+1}. [{song.title}]({song.url})\n"
            embed.add_field(name="Up Next", value=queue_text, inline=False)
        
        if len(state) > 10:
            embed.set_footer(text=f"And {len(state) - 10} more...")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))