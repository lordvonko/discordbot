
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections import deque
import os
import traceback
import time


# --- Helper Functions ---

def is_spotify_url(url):
    return 'open.spotify.com' in url

def run_blocking_io(func, *args, **kwargs):
    """Runs a blocking function in a separate thread to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, func, *args, **kwargs)

# --- Music Cog ---

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.song_queues = {}  # {guild_id: deque}
        self.current_songs = {}  # {guild_id: song_info}
        self.spotify = self.setup_spotify()
        # Cache for search results: {query: {'data': song_info, 'timestamp': float}}
        self.search_cache = {}
        self.CACHE_TTL = 3600  # 1 hour in seconds

    def setup_spotify(self):
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if client_id and client_secret:
            return spotipy.Spotify(
                auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            )
        print("Warning: Spotify API credentials not found. Spotify links will not work.")
        return None

    # --- Queue Management ---

    def get_queue(self, guild_id):
        return self.song_queues.setdefault(str(guild_id), deque())

    # --- Audio Handling ---

    async def play_next_song(self, interaction):
        guild_id = str(interaction.guild.id)
        queue = self.get_queue(guild_id)

        if not queue:
            self.current_songs.pop(guild_id, None)
            if interaction.guild.voice_client:
                await interaction.guild.voice_client.disconnect()
            return

        song_info = queue.popleft()
        self.current_songs[guild_id] = song_info

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        source = discord.FFmpegOpusAudio(song_info['url'], **ffmpeg_options)
        
        interaction.guild.voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next_song(interaction), self.bot.loop))

    # --- Music Search and Extraction ---

    async def search_music(self, query):
        """
        Searches for a song using yt-dlp, with caching to speed up repeated searches.
        """
        # Check cache first
        if query in self.search_cache:
            cached_item = self.search_cache[query]
            if (time.time() - cached_item['timestamp']) < self.CACHE_TTL:
                print(f"Cache hit for query: {query}")
                return cached_item['data']

        YDL_OPTS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        try:
            print(f"Cache miss. Searching online for: {query}")
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = await run_blocking_io(ydl.extract_info, query)
                if 'entries' in info and info['entries']:
                    video_info = info['entries'][0]
                else:
                    video_info = info
                
                song_data = {'url': video_info['url'], 'title': video_info['title']}
                
                # Store in cache
                self.search_cache[query] = {'data': song_data, 'timestamp': time.time()}
                
                return song_data
        except Exception as e:
            print(f"Error with yt-dlp: {e}")
            return None

    async def get_spotify_tracks(self, url):
        if not self.spotify:
            return []

        try:
            if 'playlist' in url:
                results = await run_blocking_io(self.spotify.playlist_tracks, url)
                return [f"{item['track']['artists'][0]['name']} - {item['track']['name']}" for item in results['items']]
            elif 'album' in url:
                results = await run_blocking_io(self.spotify.album_tracks, url)
                return [f"{track['artists'][0]['name']} - {track['name']}" for track in results['items']]
            elif 'track' in url:
                track = await run_blocking_io(self.spotify.track, url)
                return [f"{track['artists'][0]['name']} - {track['name']}"]
        except Exception as e:
            print(f"Error with Spotify API: {e}")
        return []

    # --- Commands ---

    @app_commands.command(name="play", description="Plays a song or adds it to the queue.")
    @app_commands.describe(query="The song name or URL (YouTube, Spotify).")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            return await interaction.followup.send("You must be in a voice channel to play music.")

        voice_client = interaction.guild.voice_client
        if not voice_client:
            voice_client = await interaction.user.voice.channel.connect()
        elif voice_client.channel != interaction.user.voice.channel:
            await voice_client.move_to(interaction.user.voice.channel)

        queue = self.get_queue(interaction.guild.id)
        
        if is_spotify_url(query):
            if not self.spotify:
                return await interaction.followup.send("Spotify integration is not configured.")
            
            tracks = await self.get_spotify_tracks(query)
            if not tracks:
                return await interaction.followup.send("Could not retrieve tracks from Spotify.")

            for track_query in tracks:
                song = await self.search_music(track_query)
                if song:
                    queue.append(song)
            
            await interaction.followup.send(f"Added {len(tracks)} songs from the Spotify link to the queue.")
        else:
            song = await self.search_music(query)
            if not song:
                return await interaction.followup.send("Could not find a song with that name.")
            
            queue.append(song)
            await interaction.followup.send(f"Added **{song['title']}** to the queue.")

        if not voice_client.is_playing():
            await self.play_next_song(interaction)

    @app_commands.command(name="stop", description="Stops the music and clears the queue.")
    async def stop(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        self.song_queues.pop(guild_id, None)
        self.current_songs.pop(guild_id, None)

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()

        # Always acknowledge the interaction first
        await interaction.response.send_message("Music stopped and queue cleared.")

    @app_commands.command(name="skip", description="Skips the current song.")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("Skipped the current song.")
        else:
            await interaction.response.send_message("There is no song to skip.", ephemeral=True)

    @app_commands.command(name="pause", description="Pauses the music.")
    async def pause(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("Music paused.")
        else:
            await interaction.response.send_message("There is no music to pause.", ephemeral=True)

    @app_commands.command(name="resume", description="Resumes the music.")
    async def resume(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
            interaction.guild.voice_client.resume()
            await interaction.response.send_message("Music resumed.")
        else:
            await interaction.response.send_message("The music is not paused.", ephemeral=True)

    @app_commands.command(name="queue", description="Shows the current song queue.")
    async def queue(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        queue = self.get_queue(guild_id)
        current_song = self.current_songs.get(guild_id)

        embed = discord.Embed(title="Music Queue", color=discord.Color.blue())

        if current_song:
            embed.add_field(name="Now Playing", value=current_song['title'], inline=False)

        if not queue:
            embed.description = "The queue is empty."
        else:
            queue_text = ""
            for i, song in enumerate(list(queue)[:10]):
                queue_text += f"{i+1}. {song['title']}\n"
            embed.add_field(name="Up Next", value=queue_text, inline=False)

            if len(queue) > 10:
                embed.set_footer(text=f"And {len(queue) - 10} more...")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))