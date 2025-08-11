import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional
import asyncio
from datetime import datetime, timedelta, timezone

class Poll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # {message_id: poll_data}
        self.active_polls = {}
        self.poll_check.start()

    def cog_unload(self):
        self.poll_check.cancel()

    # NEW: Helper function to update the poll embed with live vote counts
    async def update_poll_embed(self, message_id):
        if message_id not in self.active_polls:
            return

        poll_data = self.active_polls[message_id]
        try:
            channel = self.bot.get_channel(poll_data['channel_id'])
            if not channel:
                # Maybe the channel was deleted, let's clean up
                if message_id in self.active_polls:
                    del self.active_polls[message_id]
                return
                
            message = await channel.fetch_message(message_id)
            
            total_votes = 0
            # Recalculate total votes from reactions
            for reaction in message.reactions:
                if str(reaction.emoji) in poll_data['options']:
                    # Subtract 1 for the bot's own reaction
                    total_votes += (reaction.count - 1)

            # Create a new embed, keeping the original structure
            embed = discord.Embed(
                title=f"📊 {poll_data['question']}",
                color=discord.Color.blue(),
                timestamp=poll_data['end_time']
            )
            options_text = [f"{emoji} {option}" for emoji, option in poll_data['options'].items()]
            embed.description = "\n".join(options_text)
            embed.add_field(name="Duration", value=poll_data['duration_text'], inline=True)
            # Update the total votes field
            embed.add_field(name="Total Votes", value=str(total_votes), inline=True)
            
            creator = await self.bot.fetch_user(poll_data['creator_id'])
            embed.set_footer(text=f"Poll ends • Created by {creator.display_name}", 
                            icon_url=creator.display_avatar.url)

            await message.edit(embed=embed)

        except discord.NotFound:
            # Message was deleted, remove from active polls
            if message_id in self.active_polls:
                del self.active_polls[message_id]
        except Exception as e:
            print(f"Error updating poll embed for {message_id}: {e}")

    # NEW: Listener for reaction additions
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore the bot's own reactions
        if payload.user_id == self.bot.user.id:
            return
        # Check if the reaction is on an active poll
        if payload.message_id in self.active_polls:
            await self.update_poll_embed(payload.message_id)

    # NEW: Listener for reaction removals
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        # Ignore the bot's own reactions
        if payload.user_id == self.bot.user.id:
            return
        # Check if the reaction is on an active poll
        if payload.message_id in self.active_polls:
            await self.update_poll_embed(payload.message_id)

    @tasks.loop(minutes=1)
    async def poll_check(self):
        current_time = datetime.now(timezone.utc)
        expired_polls = []

        for message_id, poll_data in list(self.active_polls.items()):
            if current_time >= poll_data['end_time']:
                expired_polls.append(message_id)

        for message_id in expired_polls:
            await self.finalize_poll(message_id)

    @poll_check.before_loop
    async def before_poll_check(self):
        await self.bot.wait_until_ready()

    async def finalize_poll(self, message_id):
        if message_id not in self.active_polls:
            return

        poll_data = self.active_polls.pop(message_id, None)
        if not poll_data:
            return
        
        try:
            channel = self.bot.get_channel(poll_data['channel_id'])
            message = await channel.fetch_message(message_id)
            
            results = {}
            total_votes = 0
            
            for reaction in message.reactions:
                if str(reaction.emoji) in poll_data['options']:
                    vote_count = reaction.count - 1
                    results[str(reaction.emoji)] = vote_count
                    total_votes += vote_count

            embed = discord.Embed(
                title=f"📊 Poll Results: {poll_data['question']}",
                color=discord.Color.gold(),
                timestamp=datetime.now(timezone.utc)
            )

            if total_votes > 0:
                results_text = []
                for emoji, option in poll_data['options'].items():
                    votes = results.get(emoji, 0)
                    percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
                    bar_length = int(percentage / 5)
                    progress_bar = "█" * bar_length + "░" * (20 - bar_length)
                    results_text.append(f"{emoji} **{option}**\n`{progress_bar}` {votes} votes ({percentage:.1f}%)")
                
                embed.description = "\n\n".join(results_text)
            else:
                embed.description = "No votes were cast in this poll."

            embed.add_field(name="Total Votes", value=str(total_votes), inline=True)
            embed.add_field(name="Duration", value=poll_data['duration_text'], inline=True)
            creator = await self.bot.fetch_user(poll_data['creator_id'])
            embed.set_footer(text=f"Poll ended • Originally created by {creator.display_name}", icon_url=creator.display_avatar.url)

            await message.edit(embed=embed, view=None)
            
        except Exception as e:
            print(f"Error finalizing poll {message_id}: {e}")

    @app_commands.command(name="poll", description="Create a poll with multiple options")
    @app_commands.describe(
        question="The poll question",
        option1="First option",
        option2="Second option", 
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        option5="Fifth option (optional)",
        duration_minutes="Poll duration in minutes (default: 60, max: 10080)"
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: Optional[str] = None,
        option4: Optional[str] = None,
        option5: Optional[str] = None,
        duration_minutes: Optional[int] = 60
    ):
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            
        if duration_minutes < 1:
            return await interaction.response.send_message("❌ Duration must be at least 1 minute.", ephemeral=True)
        if duration_minutes > 10080:
            return await interaction.response.send_message("❌ Duration cannot exceed 1 week (10080 minutes).", ephemeral=True)

        options = [opt for opt in [option1, option2, option3, option4, option5] if opt is not None]

        if len(options) < 2:
            return await interaction.response.send_message("❌ You must provide at least 2 options.", ephemeral=True)

        emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        option_emojis = {emoji_list[i]: option for i, option in enumerate(options)}

        end_time = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        
        if duration_minutes < 60:
            duration_text = f"{duration_minutes} minute{'s' if duration_minutes != 1 else ''}"
        elif duration_minutes < 1440:
            hours, remaining_minutes = divmod(duration_minutes, 60)
            duration_text = f"{hours} hour{'s' if hours != 1 else ''}"
            if remaining_minutes > 0:
                duration_text += f" {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
        else:
            days, remaining_minutes = divmod(duration_minutes, 1440)
            hours, _ = divmod(remaining_minutes, 60)
            duration_text = f"{days} day{'s' if days != 1 else ''}"
            if hours > 0:
                duration_text += f" {hours} hour{'s' if hours != 1 else ''}"

        embed = discord.Embed(
            title=f"📊 {question}",
            color=discord.Color.blue(),
            timestamp=end_time
        )

        options_text = [f"{emoji} {option}" for emoji, option in option_emojis.items()]
        
        embed.description = "\n".join(options_text)
        embed.add_field(name="Duration", value=duration_text, inline=True)
        embed.add_field(name="Total Votes", value="0", inline=True)
        embed.set_footer(text=f"Poll ends • Created by {interaction.user.display_name}", 
                        icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        for emoji in option_emojis.keys():
            await message.add_reaction(emoji)

        self.active_polls[message.id] = {
            'question': question,
            'options': option_emojis,
            'channel_id': interaction.channel.id,
            'creator_id': interaction.user.id,
            'end_time': end_time,
            'duration_text': duration_text
        }

    @app_commands.command(name="poll_end", description="Manually end a poll early")
    @app_commands.describe(message_id="The message ID of the poll to end")
    async def poll_end(self, interaction: discord.Interaction, message_id: str):
        try:
            msg_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)

        if msg_id not in self.active_polls:
            return await interaction.response.send_message("❌ Poll not found or already ended.", ephemeral=True)

        poll_data = self.active_polls[msg_id]
        
        if (interaction.user.id != poll_data['creator_id'] and 
            not interaction.user.guild_permissions.manage_messages):
            return await interaction.response.send_message(
                "❌ You can only end polls you created, or you need Manage Messages permission.", 
                ephemeral=True
            )

        await self.finalize_poll(msg_id)
        await interaction.response.send_message("✅ Poll ended successfully!", ephemeral=True)

    @app_commands.command(name="poll_list", description="List active polls in this server")
    async def poll_list(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)

        server_polls = []
        for message_id, poll_data in self.active_polls.items():
            try:
                channel = self.bot.get_channel(poll_data['channel_id'])
                if channel and channel.guild.id == interaction.guild.id:
                    creator = self.bot.get_user(poll_data['creator_id'])
                    creator_name = creator.display_name if creator else "Unknown"
                    
                    time_left = poll_data['end_time'] - datetime.now(timezone.utc)
                    if time_left.total_seconds() < 0: continue

                    hours_left, remainder = divmod(int(time_left.total_seconds()), 3600)
                    minutes_left, _ = divmod(remainder, 60)
                    
                    time_left_text = ""
                    if hours_left > 0:
                        time_left_text += f"{hours_left}h "
                    time_left_text += f"{minutes_left}m"
                    
                    server_polls.append({
                        'question': poll_data['question'][:50] + ("..." if len(poll_data['question']) > 50 else ""),
                        'channel': channel.mention,
                        'creator': creator_name,
                        'time_left': time_left_text,
                        'message_id': message_id
                    })
            except:
                continue

        if not server_polls:
            return await interaction.response.send_message("📭 No active polls in this server.", ephemeral=True)

        embed = discord.Embed(
            title="📊 Active Polls",
            color=discord.Color.blue()
        )

        for poll in server_polls[:10]:
            embed.add_field(
                name=poll['question'],
                value=f"**Channel:** {poll['channel']}\n"
                      f"**Creator:** {poll['creator']}\n"
                      f"**Time left:** {poll['time_left']}\n"
                      f"**ID:** `{poll['message_id']}`",
                inline=False
            )

        if len(server_polls) > 10:
            embed.set_footer(text=f"Showing 10 of {len(server_polls)} active polls")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Poll(bot))