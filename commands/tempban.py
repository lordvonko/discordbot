import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta

TEMP_BANS_FILE = "tempbans.json"

def parse_duration(duration: str) -> timedelta:
    """Parses a duration string (e.g., 10m, 2h, 1d) into a timedelta object."""
    unit = duration[-1].lower()
    value = int(duration[:-1])
    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    else:
        raise ValueError("Invalid time unit. Use 'm' for minutes, 'h' for hours, or 'd' for days.")

class TempBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_bans = self.load_temp_bans()
        self.check_expired_bans.start()

    def cog_unload(self):
        self.check_expired_bans.cancel()

    def load_temp_bans(self):
        if os.path.exists(TEMP_BANS_FILE):
            with open(TEMP_BANS_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_temp_bans(self):
        with open(TEMP_BANS_FILE, 'w') as f:
            json.dump(self.temp_bans, f, indent=4)

    @app_commands.command(name="tempban", description="Bans a user temporarily.")
    @app_commands.describe(
        member="The user to ban.",
        duration="Duration of the ban (e.g., 10m, 2h, 1d).",
        reason="The reason for the ban (optional)."
    )
    @app_commands.default_permissions(ban_members=True)
    @commands.has_permissions(ban_members=True)
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason provided."):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("You cannot ban a member with an equal or higher role.", ephemeral=True)
        if member.top_role >= interaction.guild.me.top_role:
            return await interaction.response.send_message("I cannot ban a member with an equal or higher role than me.", ephemeral=True)

        try:
            delta = parse_duration(duration)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

        unban_time = datetime.utcnow() + delta
        unban_timestamp = int(unban_time.timestamp())

        guild_id = str(interaction.guild.id)
        user_id = str(member.id)

        if guild_id not in self.temp_bans:
            self.temp_bans[guild_id] = {}
        
        self.temp_bans[guild_id][user_id] = unban_timestamp
        self.save_temp_bans()

        try:
            await member.ban(reason=f"{reason} (Temporary ban until {unban_time.strftime('%Y-%m-%d %H:%M:%S')} UTC)")
            await interaction.response.send_message(f"🔨 {member.mention} has been temporarily banned for {duration}. Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to ban this user.", ephemeral=True)
            # If ban fails, remove from tracking
            del self.temp_bans[guild_id][user_id]
            self.save_temp_bans()
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
            # If ban fails, remove from tracking
            del self.temp_bans[guild_id][user_id]
            self.save_temp_bans()

    @tasks.loop(minutes=1)
    async def check_expired_bans(self):
        now = int(datetime.utcnow().timestamp())
        bans_to_remove = []

        for guild_id, users in self.temp_bans.items():
            for user_id, unban_timestamp in users.items():
                if now >= unban_timestamp:
                    try:
                        guild = self.bot.get_guild(int(guild_id))
                        if guild:
                            user = await self.bot.fetch_user(int(user_id))
                            await guild.unban(user, reason="Temporary ban expired.")
                            print(f"Unbanned {user} from {guild.name}.")
                    except discord.NotFound:
                        # User or guild not found, probably left or deleted
                        pass
                    except discord.Forbidden:
                        print(f"Failed to unban user {user_id} from guild {guild_id} due to permissions.")
                    except Exception as e:
                        print(f"An error occurred while unbanning: {e}")
                    
                    bans_to_remove.append((guild_id, user_id))

        if bans_to_remove:
            for guild_id, user_id in bans_to_remove:
                if guild_id in self.temp_bans and user_id in self.temp_bans[guild_id]:
                    del self.temp_bans[guild_id][user_id]
            self.save_temp_bans()

    @check_expired_bans.before_loop
    async def before_check_expired_bans(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(TempBan(bot))