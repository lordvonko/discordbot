
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
import concurrent.futures


# --- Helper Functions ---

def is_spotify_url(url):
    return 'open.spotify.com' in url

# Create a thread pool executor with limited threads for better resource management
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="yt-dlp-worker")

async def run_blocking_io(func, *args, **kwargs):
    """Runs a blocking function in a separate thread pool to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, func, *args, **kwargs)

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
        # Inactivity tracking
        self.last_activity = {}  # {guild_id: timestamp}
        self.INACTIVITY_TIMEOUT = 600  # 10 minutes of inactivity before auto-disconnect
    
    def cog_unload(self):
        """Clean up resources when the cog is unloaded."""
        if _executor and not _executor._shutdown:
            _executor.shutdown(wait=True)

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
            # Update last activity timestamp
            self.last_activity[guild_id] = time.time()
            print(f"Queue empty for guild {guild_id}, waiting for more songs...")
            return

        # Check if voice client is still valid
        if not interaction.guild.voice_client or not interaction.guild.voice_client.is_connected():
            print(f"Voice client disconnected for guild {guild_id}")
            self.current_songs.pop(guild_id, None)
            queue.clear()
            return

        song_info = queue.popleft()
        self.current_songs[guild_id] = song_info
        print(f"Attempting to play: {song_info['title']} - URL: {song_info['url'][:50]}...")

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        try:
            print(f"Creating FFmpeg audio source with options: {ffmpeg_options}")
            source = discord.FFmpegOpusAudio(song_info['url'], **ffmpeg_options)
            print(f"✅ Audio source created successfully for {song_info['title']}")
        except Exception as e:
            print(f"❌ Error creating audio source for {song_info['title']}: {e}")
            print(f"URL that failed: {song_info['url']}")
            # Try next song if current one fails
            await self.play_next_song(interaction)
            return
        
        def after_playing(error):
            if error:
                print(f'Player error: {error}')
                # Try to play next song even on error
                try:
                    coro = self.play_next_song(interaction)
                    future = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                    future.result(timeout=30)
                except Exception as e:
                    print(f"Error in after_playing callback with error: {e}")
                return
            
            # Normal completion - play next song
            try:
                coro = self.play_next_song(interaction)
                future = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
                future.result(timeout=30)
            except Exception as e:
                print(f"Error in after_playing callback: {e}")
        
        print(f"Starting playback for {song_info['title']}...")
        interaction.guild.voice_client.play(source, after=after_playing)
        print(f"Playback started for {song_info['title']}")

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
            'format': 'bestaudio[ext=webm]/bestaudio/best',
            'noplaylist': True,
            'default_search': 'ytsearch',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'ignoreerrors': True,
            'logtostderr': False,
            'geo_bypass': True,
            'age_limit': None,
            # SSL/TLS and connection fixes
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            # Retry and timeout configurations
            'retries': 3,
            'fragment_retries': 3,
            'socket_timeout': 30,
            'sleep_interval': 1,
            'max_sleep_interval': 5,
        }
        
        # Add cookie file only if it exists
        if os.path.exists('cookies.txt'):
            YDL_OPTS['cookiefile'] = 'cookies.txt'
        try:
            print(f"Cache miss. Searching online for: {query}")
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = await run_blocking_io(ydl.extract_info, query)
                
                if not info:
                    print(f"No information found for query: {query}")
                    return None
                    
                if 'entries' in info and info['entries']:
                    video_info = info['entries'][0]
                else:
                    video_info = info
                
                if not video_info or not video_info.get('url'):
                    print(f"No valid URL found for query: {query}")
                    return None
                
                song_data = {
                    'url': video_info['url'], 
                    'title': video_info.get('title', 'Unknown Title'),
                    'duration': video_info.get('duration', 0),
                    'uploader': video_info.get('uploader', 'Unknown')
                }
                print(f"Successfully extracted: {song_data['title']} - URL: {song_data['url'][:50]}...")
                
                # Store in cache
                self.search_cache[query] = {'data': song_data, 'timestamp': time.time()}
                
                return song_data
        except yt_dlp.DownloadError as e:
            print(f"YouTube-dlp download error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error with yt-dlp: {e}")
            traceback.print_exc()
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
        try:
            if not voice_client:
                voice_client = await interaction.user.voice.channel.connect(timeout=30.0, reconnect=True)
            elif voice_client.channel != interaction.user.voice.channel:
                await voice_client.move_to(interaction.user.voice.channel)
        except asyncio.TimeoutError:
            return await interaction.followup.send("Timed out while trying to connect to the voice channel.")
        except discord.ClientException as e:
            return await interaction.followup.send(f"Failed to connect to voice channel: {e}")
        except Exception as e:
            return await interaction.followup.send(f"Unexpected error connecting to voice: {e}")

        queue = self.get_queue(interaction.guild.id)
        
        if is_spotify_url(query):
            if not self.spotify:
                return await interaction.followup.send("Spotify integration is not configured.")
            
            tracks = await self.get_spotify_tracks(query)
            if not tracks:
                return await interaction.followup.send("Could not retrieve tracks from Spotify.")

            added_count = 0
            for track_query in tracks:
                song = await self.search_music(track_query)
                if song:
                    queue.append(song)
                    added_count += 1
            
            if added_count > 0:
                # Update activity timestamp
                self.last_activity[str(interaction.guild.id)] = time.time()
                await interaction.followup.send(f"✅ Added {added_count} songs from the Spotify link to the queue.")
            else:
                return await interaction.followup.send("❌ Could not find any songs from the Spotify link. Please try again.")
        else:
            song = await self.search_music(query)
            if not song:
                # Don't disconnect on search failure - stay connected and inform user
                return await interaction.followup.send("❌ Could not find a song with that name. Please try a different search term or check your spelling.")
            
            queue.append(song)
            # Update activity timestamp
            self.last_activity[str(interaction.guild.id)] = time.time()
            await interaction.followup.send(f"✅ Added **{song['title']}** to the queue.")

        # Only try to play if we have songs in queue and not already playing
        if queue and not voice_client.is_playing():
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

    @app_commands.command(name="leave", description="Disconnects the bot from the voice channel.")
    async def leave(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ I'm not connected to a voice channel.", ephemeral=True)
        
        # Clear queue and current song
        self.song_queues.pop(guild_id, None)
        self.current_songs.pop(guild_id, None)
        
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Left the voice channel and cleared the queue.")

async def setup(bot):
    await bot.add_cog(Music(bot))
