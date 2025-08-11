import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime, timedelta, timezone
import re
from typing import Optional

REMINDERS_FILE = "reminders.json"

class RemindMe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = self.load_reminders()
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    def load_reminders(self):
        """Load reminders from JSON file"""
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, 'r') as f:
                data = json.load(f)
                # Convert ISO strings back to datetime objects
                for user_id, user_reminders in data.items():
                    for reminder in user_reminders:
                        reminder['remind_time'] = datetime.fromisoformat(reminder['remind_time'])
                        reminder['created_at'] = datetime.fromisoformat(reminder['created_at'])
                return data
        return {}

    def save_reminders(self):
        """Save reminders to JSON file"""
        # Convert datetime objects to ISO strings for JSON serialization
        serializable_data = {}
        for user_id, user_reminders in self.reminders.items():
            serializable_data[user_id] = []
            for reminder in user_reminders:
                reminder_copy = reminder.copy()
                reminder_copy['remind_time'] = reminder['remind_time'].isoformat()
                reminder_copy['created_at'] = reminder['created_at'].isoformat()
                serializable_data[user_id].append(reminder_copy)
        
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(serializable_data, f, indent=4)

    def parse_time(self, time_string: str) -> Optional[timedelta]:
        """Parse time string into timedelta"""
        time_string = time_string.lower().strip()
        
        # Patterns for different time formats
        patterns = [
            (r'(\d+)\s*s(?:ec(?:ond)?s?)?', 'seconds'),
            (r'(\d+)\s*m(?:in(?:ute)?s?)?', 'minutes'),
            (r'(\d+)\s*h(?:r|our)?s?', 'hours'),
            (r'(\d+)\s*d(?:ay)?s?', 'days'),
            (r'(\d+)\s*w(?:eek)?s?', 'weeks'),
        ]
        
        total_seconds = 0
        
        for pattern, unit in patterns:
            matches = re.findall(pattern, time_string)
            for match in matches:
                value = int(match)
                if unit == 'seconds':
                    total_seconds += value
                elif unit == 'minutes':
                    total_seconds += value * 60
                elif unit == 'hours':
                    total_seconds += value * 3600
                elif unit == 'days':
                    total_seconds += value * 86400
                elif unit == 'weeks':
                    total_seconds += value * 604800
        
        if total_seconds > 0:
            return timedelta(seconds=total_seconds)
        
        return None

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        """Check for due reminders and send them"""
        current_time = datetime.now(timezone.utc)
        due_reminders = []

        for user_id, user_reminders in self.reminders.items():
            for i, reminder in enumerate(user_reminders):
                if current_time >= reminder['remind_time']:
                    due_reminders.append((user_id, i, reminder))

        # Send reminders and remove them
        for user_id, reminder_index, reminder in reversed(due_reminders):
            await self.send_reminder(user_id, reminder)
            del self.reminders[user_id][reminder_index]
            
            # Remove user entry if no more reminders
            if not self.reminders[user_id]:
                del self.reminders[user_id]

        if due_reminders:
            self.save_reminders()

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    async def send_reminder(self, user_id: str, reminder: dict):
        """Send a reminder to the user"""
        try:
            user = await self.bot.fetch_user(int(user_id))
            
            embed = discord.Embed(
                title="⏰ Reminder",
                description=reminder['message'],
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Calculate how long ago the reminder was set
            time_diff = datetime.now(timezone.utc) - reminder['created_at']
            
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} day{'s' if time_diff.days != 1 else ''} ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            
            embed.add_field(name="Set", value=time_ago, inline=True)
            
            if reminder.get('guild_name'):
                embed.add_field(name="Server", value=reminder['guild_name'], inline=True)
            
            embed.set_footer(text="Reminder from Musashi Bot")
            
            await user.send(embed=embed)
            
        except discord.Forbidden:
            # User has DMs disabled, try to send in the original channel if available
            if reminder.get('channel_id'):
                try:
                    channel = self.bot.get_channel(reminder['channel_id'])
                    if channel:
                        embed = discord.Embed(
                            title="⏰ Reminder",
                            description=f"{user.mention} - {reminder['message']}",
                            color=discord.Color.orange()
                        )
                        embed.set_footer(text="(DMs disabled - reminder sent here instead)")
                        await channel.send(embed=embed)
                except:
                    pass  # Channel no longer accessible
        except Exception as e:
            print(f"Error sending reminder to {user_id}: {e}")

    @app_commands.command(name="remindme", description="Set a personal reminder")
    @app_commands.describe(
        time="When to remind you (e.g., '30m', '2h', '1d', '1w 2d 3h')",
        message="What to remind you about"
    )
    async def remindme(self, interaction: discord.Interaction, time: str, message: str):
        """Set a personal reminder"""
        
        # Parse the time
        time_delta = self.parse_time(time)
        
        if not time_delta:
            return await interaction.response.send_message(
                "❌ Invalid time format. Use formats like: `30m`, `2h`, `1d`, `1w 2d 3h`\n"
                "Supported units: s(econds), m(inutes), h(ours), d(ays), w(eeks)",
                ephemeral=True
            )
        
        # Check limits
        if time_delta.total_seconds() < 60:
            return await interaction.response.send_message(
                "❌ Minimum reminder time is 1 minute.",
                ephemeral=True
            )
        
        if time_delta.total_seconds() > 31536000:  # 1 year
            return await interaction.response.send_message(
                "❌ Maximum reminder time is 1 year.",
                ephemeral=True
            )

        # Check user reminder limit
        user_id = str(interaction.user.id)
        if user_id in self.reminders and len(self.reminders[user_id]) >= 10:
            return await interaction.response.send_message(
                "❌ You can only have 10 active reminders at a time. Use `/reminders list` to see them.",
                ephemeral=True
            )

        # Calculate remind time
        current_time = datetime.now(timezone.utc)
        remind_time = current_time + time_delta

        # Create reminder
        reminder_data = {
            'message': message[:1000],  # Limit message length
            'remind_time': remind_time,
            'created_at': current_time,
            'guild_name': interaction.guild.name if interaction.guild else None,
            'channel_id': interaction.channel.id if interaction.guild else None
        }

        # Add to reminders
        if user_id not in self.reminders:
            self.reminders[user_id] = []
        
        self.reminders[user_id].append(reminder_data)
        self.save_reminders()

        # Format time for display
        time_parts = []
        total_seconds = int(time_delta.total_seconds())
        
        weeks = total_seconds // 604800
        days = (total_seconds % 604800) // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if weeks > 0:
            time_parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
        if days > 0:
            time_parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 and not time_parts:  # Only show seconds if it's the only unit
            time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        time_display = ", ".join(time_parts)

        embed = discord.Embed(
            title="✅ Reminder Set",
            description=f"I'll remind you about: **{message}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Time", value=time_display, inline=True)
        embed.add_field(name="Remind at", value=f"<t:{int(remind_time.timestamp())}:F>", inline=True)
        embed.set_footer(text="You'll receive a DM when it's time!")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reminders", description="Manage your active reminders")
    @app_commands.describe(
        action="What to do with your reminders",
        reminder_number="The reminder number to delete (use 'list' first to see numbers)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="delete", value="delete"),
        app_commands.Choice(name="clear", value="clear")
    ])
    async def reminders(
        self, 
        interaction: discord.Interaction, 
        action: str,
        reminder_number: Optional[int] = None
    ):
        """Manage your active reminders"""
        
        user_id = str(interaction.user.id)
        user_reminders = self.reminders.get(user_id, [])

        if action == "list":
            if not user_reminders:
                return await interaction.response.send_message("📭 You have no active reminders.", ephemeral=True)

            embed = discord.Embed(
                title="📋 Your Active Reminders",
                color=discord.Color.blue()
            )

            for i, reminder in enumerate(user_reminders, 1):
                time_left = reminder['remind_time'] - datetime.now(timezone.utc)
                
                if time_left.total_seconds() > 0:
                    days = time_left.days
                    hours = time_left.seconds // 3600
                    minutes = (time_left.seconds % 3600) // 60
                    
                    time_left_parts = []
                    if days > 0:
                        time_left_parts.append(f"{days}d")
                    if hours > 0:
                        time_left_parts.append(f"{hours}h")
                    if minutes > 0:
                        time_left_parts.append(f"{minutes}m")
                    
                    time_left_text = " ".join(time_left_parts) if time_left_parts else "< 1m"
                else:
                    time_left_text = "Due now!"

                embed.add_field(
                    name=f"#{i}: {reminder['message'][:50]}{'...' if len(reminder['message']) > 50 else ''}",
                    value=f"⏰ **Time left:** {time_left_text}\n"
                          f"📅 **Set:** <t:{int(reminder['created_at'].timestamp())}:R>",
                    inline=False
                )

            embed.set_footer(text=f"Total: {len(user_reminders)} reminder{'s' if len(user_reminders) != 1 else ''}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "delete":
            if not user_reminders:
                return await interaction.response.send_message("📭 You have no active reminders.", ephemeral=True)

            if reminder_number is None:
                return await interaction.response.send_message(
                    "❌ Please specify which reminder to delete. Use `/reminders list` first to see the numbers.",
                    ephemeral=True
                )

            if reminder_number < 1 or reminder_number > len(user_reminders):
                return await interaction.response.send_message(
                    f"❌ Invalid reminder number. You have {len(user_reminders)} active reminder{'s' if len(user_reminders) != 1 else ''}.",
                    ephemeral=True
                )

            # Remove the reminder
            deleted_reminder = user_reminders.pop(reminder_number - 1)
            
            if not user_reminders:
                del self.reminders[user_id]
            
            self.save_reminders()

            await interaction.response.send_message(
                f"✅ Deleted reminder: **{deleted_reminder['message'][:100]}**",
                ephemeral=True
            )

        elif action == "clear":
            if not user_reminders:
                return await interaction.response.send_message("📭 You have no active reminders.", ephemeral=True)

            count = len(user_reminders)
            del self.reminders[user_id]
            self.save_reminders()

            await interaction.response.send_message(
                f"✅ Cleared all {count} reminder{'s' if count != 1 else ''}.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(RemindMe(bot))