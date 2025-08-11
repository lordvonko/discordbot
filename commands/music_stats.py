import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO

STATS_FILE = "music_usage.json"

class MusicStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_stats(self):
        """Load music usage statistics from JSON file"""
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        return {
            'songs_played': [],
            'user_activity': {},
            'guild_activity': {},
            'daily_stats': {}
        }

    def save_stats(self, stats):
        """Save music usage statistics to JSON file"""
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)

    def log_song_play(self, guild_id: int, user_id: int, song_title: str, artist: str = "Unknown"):
        """Log a song play (call this from music.py)"""
        stats = self.load_stats()
        
        timestamp = datetime.now(timezone.utc).isoformat()
        song_data = {
            'timestamp': timestamp,
            'guild_id': guild_id,
            'user_id': user_id,
            'title': song_title,
            'artist': artist
        }
        
        stats['songs_played'].append(song_data)
        
        # Update user activity
        user_key = str(user_id)
        if user_key not in stats['user_activity']:
            stats['user_activity'][user_key] = 0
        stats['user_activity'][user_key] += 1
        
        # Update guild activity
        guild_key = str(guild_id)
        if guild_key not in stats['guild_activity']:
            stats['guild_activity'][guild_key] = 0
        stats['guild_activity'][guild_key] += 1
        
        # Update daily stats
        date_key = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if date_key not in stats['daily_stats']:
            stats['daily_stats'][date_key] = 0
        stats['daily_stats'][date_key] += 1
        
        # Keep only last 30 days of detailed song data
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        stats['songs_played'] = [
            song for song in stats['songs_played']
            if datetime.fromisoformat(song['timestamp']) > cutoff_date
        ]
        
        self.save_stats(stats)

    @app_commands.command(name="music_stats", description="View music usage statistics for this server")
    @app_commands.describe(
        period="Time period to analyze",
        stat_type="Type of statistics to display"
    )
    @app_commands.choices(
        period=[
            app_commands.Choice(name="Last 7 days", value="7d"),
            app_commands.Choice(name="Last 30 days", value="30d"),
            app_commands.Choice(name="All time", value="all")
        ],
        stat_type=[
            app_commands.Choice(name="Overview", value="overview"),
            app_commands.Choice(name="Top Songs", value="songs"),
            app_commands.Choice(name="Top Users", value="users"),
            app_commands.Choice(name="Top Artists", value="artists"),
            app_commands.Choice(name="Activity Graph", value="graph")
        ]
    )
    async def music_stats(
        self,
        interaction: discord.Interaction,
        period: str = "7d",
        stat_type: str = "overview"
    ):
        """Display music usage statistics for the server"""
        
        await interaction.response.defer()
        
        stats = self.load_stats()
        guild_id = interaction.guild.id
        
        # Filter data by time period
        if period == "7d":
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            period_name = "Last 7 Days"
        elif period == "30d":
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            period_name = "Last 30 Days"
        else:
            cutoff_date = datetime.min.replace(tzinfo=timezone.utc)
            period_name = "All Time"
        
        # Filter songs for this guild and time period
        guild_songs = [
            song for song in stats['songs_played']
            if song['guild_id'] == guild_id and
            datetime.fromisoformat(song['timestamp']) > cutoff_date
        ]
        
        if not guild_songs:
            embed = discord.Embed(
                title="📊 Music Statistics",
                description="No music activity found for the specified period.",
                color=discord.Color.blue()
            )
            return await interaction.followup.send(embed=embed)
        
        if stat_type == "overview":
            await self.send_overview_stats(interaction, guild_songs, period_name)
        elif stat_type == "songs":
            await self.send_top_songs(interaction, guild_songs, period_name)
        elif stat_type == "users":
            await self.send_top_users(interaction, guild_songs, period_name)
        elif stat_type == "artists":
            await self.send_top_artists(interaction, guild_songs, period_name)
        elif stat_type == "graph":
            await self.send_activity_graph(interaction, guild_songs, period_name)

    async def send_overview_stats(self, interaction, songs, period_name):
        """Send overview statistics"""
        total_songs = len(songs)
        unique_songs = len(set((song['title'], song['artist']) for song in songs))
        unique_users = len(set(song['user_id'] for song in songs))
        unique_artists = len(set(song['artist'] for song in songs if song['artist'] != "Unknown"))
        
        # Most active day
        daily_counts = defaultdict(int)
        for song in songs:
            date = datetime.fromisoformat(song['timestamp']).strftime('%Y-%m-%d')
            daily_counts[date] += 1
        
        most_active_day = max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else ("N/A", 0)
        
        # Average songs per day
        if songs:
            first_song = min(songs, key=lambda x: x['timestamp'])
            last_song = max(songs, key=lambda x: x['timestamp'])
            days_span = (datetime.fromisoformat(last_song['timestamp']) - 
                        datetime.fromisoformat(first_song['timestamp'])).days + 1
            avg_per_day = total_songs / max(days_span, 1)
        else:
            avg_per_day = 0
        
        embed = discord.Embed(
            title=f"📊 Music Statistics - {period_name}",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="🎵 Total Songs Played", value=f"{total_songs:,}", inline=True)
        embed.add_field(name="🎶 Unique Songs", value=f"{unique_songs:,}", inline=True)
        embed.add_field(name="👥 Active Users", value=f"{unique_users:,}", inline=True)
        embed.add_field(name="🎤 Unique Artists", value=f"{unique_artists:,}", inline=True)
        embed.add_field(name="📅 Most Active Day", value=f"{most_active_day[1]} songs", inline=True)
        embed.add_field(name="📈 Avg Songs/Day", value=f"{avg_per_day:.1f}", inline=True)
        
        embed.set_footer(text=f"Stats for {interaction.guild.name}")
        
        await interaction.followup.send(embed=embed)

    async def send_top_songs(self, interaction, songs, period_name):
        """Send top songs statistics"""
        song_counter = Counter((song['title'], song['artist']) for song in songs)
        top_songs = song_counter.most_common(10)
        
        embed = discord.Embed(
            title=f"🎵 Top Songs - {period_name}",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if not top_songs:
            embed.description = "No songs found."
        else:
            song_list = []
            for i, ((title, artist), count) in enumerate(top_songs, 1):
                artist_text = f" - {artist}" if artist != "Unknown" else ""
                song_list.append(f"**{i}.** {title}{artist_text}\n`{count} play{'s' if count != 1 else ''}`")
            
            embed.description = "\n\n".join(song_list)
        
        embed.set_footer(text=f"Stats for {interaction.guild.name}")
        
        await interaction.followup.send(embed=embed)

    async def send_top_users(self, interaction, songs, period_name):
        """Send top users statistics"""
        user_counter = Counter(song['user_id'] for song in songs)
        top_users = user_counter.most_common(10)
        
        embed = discord.Embed(
            title=f"👥 Top Users - {period_name}",
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if not top_users:
            embed.description = "No users found."
        else:
            user_list = []
            for i, (user_id, count) in enumerate(top_users, 1):
                user = self.bot.get_user(user_id)
                username = user.display_name if user else f"Unknown User ({user_id})"
                user_list.append(f"**{i}.** {username}\n`{count} song{'s' if count != 1 else ''} played`")
            
            embed.description = "\n\n".join(user_list)
        
        embed.set_footer(text=f"Stats for {interaction.guild.name}")
        
        await interaction.followup.send(embed=embed)

    async def send_top_artists(self, interaction, songs, period_name):
        """Send top artists statistics"""
        artists = [song['artist'] for song in songs if song['artist'] != "Unknown"]
        if not artists:
            embed = discord.Embed(
                title=f"🎤 Top Artists - {period_name}",
                description="No artist information available.",
                color=discord.Color.orange()
            )
            return await interaction.followup.send(embed=embed)
        
        artist_counter = Counter(artists)
        top_artists = artist_counter.most_common(10)
        
        embed = discord.Embed(
            title=f"🎤 Top Artists - {period_name}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        
        artist_list = []
        for i, (artist, count) in enumerate(top_artists, 1):
            artist_list.append(f"**{i}.** {artist}\n`{count} song{'s' if count != 1 else ''} played`")
        
        embed.description = "\n\n".join(artist_list)
        embed.set_footer(text=f"Stats for {interaction.guild.name}")
        
        await interaction.followup.send(embed=embed)

    async def send_activity_graph(self, interaction, songs, period_name):
        """Send activity graph (requires matplotlib)"""
        try:
            # Group songs by date
            daily_counts = defaultdict(int)
            for song in songs:
                date = datetime.fromisoformat(song['timestamp']).date()
                daily_counts[date] += 1
            
            if not daily_counts:
                embed = discord.Embed(
                    title="📈 Activity Graph",
                    description="No activity data available.",
                    color=discord.Color.blue()
                )
                return await interaction.followup.send(embed=embed)
            
            # Sort dates and create data
            sorted_dates = sorted(daily_counts.keys())
            dates = []
            counts = []
            
            # Fill in missing days with 0
            start_date = min(sorted_dates)
            end_date = max(sorted_dates)
            current_date = start_date
            
            while current_date <= end_date:
                dates.append(current_date)
                counts.append(daily_counts.get(current_date, 0))
                current_date += timedelta(days=1)
            
            # Create graph
            plt.figure(figsize=(12, 6))
            plt.plot(dates, counts, marker='o', linewidth=2, markersize=4)
            plt.title(f'Music Activity - {period_name}', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Songs Played', fontsize=12)
            plt.grid(True, alpha=0.3)
            
            # Format x-axis
            if len(dates) > 14:
                plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator())
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            else:
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Save to bytes buffer
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            # Create embed with graph
            embed = discord.Embed(
                title=f"📈 Music Activity Graph - {period_name}",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=f"Stats for {interaction.guild.name}")
            
            file = discord.File(buffer, filename="music_activity.png")
            embed.set_image(url="attachment://music_activity.png")
            
            await interaction.followup.send(embed=embed, file=file)
            
        except ImportError:
            embed = discord.Embed(
                title="📈 Activity Graph",
                description="Graph functionality requires matplotlib. Feature temporarily unavailable.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="📈 Activity Graph",
                description=f"Error generating graph: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MusicStats(bot))