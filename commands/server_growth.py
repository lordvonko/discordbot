
import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Literal
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# --- Database Setup ---
DB_FILE = "data/server_stats.db"
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                record_date DATE NOT NULL,
                member_count INTEGER NOT NULL,
                UNIQUE(guild_id, record_date)
            )
        """)
        conn.commit()

# --- Cog ---
class ServerGrowth(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()
        self.record_member_count.start()

    def cog_unload(self):
        self.record_member_count.cancel()

    @tasks.loop(hours=24)
    async def record_member_count(self):
        """Runs daily to record the member count for each server."""
        print("Running daily member count task...")
        today = datetime.utcnow().date()
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            for guild in self.bot.guilds:
                try:
                    cursor.execute(
                        "INSERT INTO member_counts (guild_id, record_date, member_count) VALUES (?, ?, ?)",
                        (guild.id, today, guild.member_count)
                    )
                except sqlite3.IntegrityError:
                    # Data for today already exists, update it just in case
                    cursor.execute(
                        "UPDATE member_counts SET member_count = ? WHERE guild_id = ? AND record_date = ?",
                        (guild.member_count, guild.id, today)
                    )
            conn.commit()
        print("Daily member count task finished.")

    @record_member_count.before_loop
    async def before_record_member_count(self):
        await self.bot.wait_until_ready()

    def _generate_chart(self, guild_id: int, timeframe: str) -> str:
        """Generates a growth chart and returns the file path."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            end_date = datetime.utcnow().date()
            if timeframe == 'Weekly':
                start_date = end_date - timedelta(days=7)
                title = "Crescimento Semanal de Membros"
            elif timeframe == 'Monthly':
                start_date = end_date - timedelta(days=30)
                title = "Crescimento Mensal de Membros"
            else: # All-time
                start_date = end_date - timedelta(days=365*5) # Effectively all
                title = "Crescimento Histórico de Membros"

            cursor.execute(
                "SELECT record_date, member_count FROM member_counts WHERE guild_id = ? AND record_date >= ? ORDER BY record_date ASC",
                (guild_id, start_date)
            )
            data = cursor.fetchall()

        if len(data) < 2:
            return None # Not enough data to plot

        dates = [datetime.strptime(d, '%Y-%m-%d') for d, c in data]
        counts = [c for d, c in data]

        # --- Chart Styling ---
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(dates, counts, marker='o', linestyle='-', color='#7289DA')

        # Formatting
        ax.set_title(title, fontsize=16, color='white')
        ax.set_ylabel("Total de Membros", color='white')
        ax.grid(True, which='both', linestyle='--', linewidth=0.5, color='gray')
        fig.autofmt_xdate()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        plt.tight_layout()

        # Save chart
        chart_path = f"data/growth_chart_{guild_id}.png"
        plt.savefig(chart_path, transparent=True)
        plt.close()
        
        return chart_path

    @app_commands.command(name="server_growth", description="Shows a chart of the server's member growth.")
    @app_commands.describe(timeframe="The time period to show the growth for.")
    async def server_growth(
        self, 
        interaction: discord.Interaction, 
        timeframe: Literal['Weekly', 'Monthly', 'All-time'] = 'Monthly'
    ):
        """Displays a chart of member growth over a specified period."""
        await interaction.response.defer()

        chart_path = self._generate_chart(interaction.guild.id, timeframe)

        if not chart_path:
            await interaction.followup.send("❌ Não há dados suficientes para gerar um gráfico. O bot precisa de pelo menos 2 dias de registros.")
            return

        file = discord.File(chart_path, filename="growth_chart.png")
        embed = discord.Embed(
            title=f"📊 Análise de Crescimento do Servidor",
            description=f"Exibindo dados para o período: **{timeframe}**.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_image(url="attachment://growth_chart.png")
        embed.set_footer(text="Rastreamento iniciado em (ou após) a primeira execução deste comando.")

        await interaction.followup.send(embed=embed, file=file)

async def setup(bot):
    await bot.add_cog(ServerGrowth(bot))
