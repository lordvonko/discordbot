import discord
from discord.ext import commands
from discord import app_commands
import re
from typing import Optional
from datetime import datetime, timedelta

class ClearAdvanced(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clear_advanced", description="Advanced message clearing with filtering options.")
    @app_commands.describe(
        amount="Number of messages to check (max 1000)",
        user="Clear messages only from this user",
        contains="Clear messages containing this text",
        starts_with="Clear messages starting with this text",
        ends_with="Clear messages ending with this text",
        regex="Clear messages matching this regex pattern",
        has_attachments="Clear messages with attachments (true/false)",
        has_embeds="Clear messages with embeds (true/false)",
        has_links="Clear messages with links (true/false)",
        from_bots="Clear messages from bots only (true/false)",
        older_than_hours="Clear messages older than X hours",
        newer_than_hours="Clear messages newer than X hours"
    )
    @app_commands.default_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def clear_advanced(
        self, 
        interaction: discord.Interaction,
        amount: int = 100,
        user: Optional[discord.Member] = None,
        contains: Optional[str] = None,
        starts_with: Optional[str] = None,
        ends_with: Optional[str] = None,
        regex: Optional[str] = None,
        has_attachments: Optional[bool] = None,
        has_embeds: Optional[bool] = None,
        has_links: Optional[bool] = None,
        from_bots: Optional[bool] = None,
        older_than_hours: Optional[int] = None,
        newer_than_hours: Optional[int] = None
    ):
        """Advanced message clearing with multiple filtering options"""
        
        # Validate inputs
        if amount > 1000:
            return await interaction.response.send_message("❌ Amount cannot exceed 1000 messages.", ephemeral=True)
        
        if amount < 1:
            return await interaction.response.send_message("❌ Amount must be at least 1.", ephemeral=True)

        # Validate regex if provided
        compiled_regex = None
        if regex:
            try:
                compiled_regex = re.compile(regex, re.IGNORECASE)
            except re.error:
                return await interaction.response.send_message("❌ Invalid regex pattern.", ephemeral=True)

        # Validate time ranges
        after_time = None
        before_time = None
        now = datetime.utcnow()
        
        if older_than_hours:
            before_time = now - timedelta(hours=older_than_hours)
        
        if newer_than_hours:
            after_time = now - timedelta(hours=newer_than_hours)

        await interaction.response.defer(ephemeral=True)

        try:
            # Get messages to check
            messages = []
            async for message in interaction.channel.history(limit=amount):
                messages.append(message)

            # Apply filters
            filtered_messages = []
            
            for message in messages:
                # Skip if message is too recent (Discord API limitation)
                if (datetime.utcnow() - message.created_at).total_seconds() < 14 * 24 * 60 * 60:
                    
                    # Apply all filters
                    if user and message.author != user:
                        continue
                    
                    if from_bots is not None:
                        if from_bots and not message.author.bot:
                            continue
                        if not from_bots and message.author.bot:
                            continue
                    
                    if contains and contains.lower() not in message.content.lower():
                        continue
                    
                    if starts_with and not message.content.lower().startswith(starts_with.lower()):
                        continue
                    
                    if ends_with and not message.content.lower().endswith(ends_with.lower()):
                        continue
                    
                    if compiled_regex and not compiled_regex.search(message.content):
                        continue
                    
                    if has_attachments is not None:
                        if has_attachments and not message.attachments:
                            continue
                        if not has_attachments and message.attachments:
                            continue
                    
                    if has_embeds is not None:
                        if has_embeds and not message.embeds:
                            continue
                        if not has_embeds and message.embeds:
                            continue
                    
                    if has_links is not None:
                        has_link = any(word.startswith(('http://', 'https://')) for word in message.content.split())
                        if has_links and not has_link:
                            continue
                        if not has_links and has_link:
                            continue
                    
                    if before_time and message.created_at > before_time:
                        continue
                    
                    if after_time and message.created_at < after_time:
                        continue
                    
                    filtered_messages.append(message)

            if not filtered_messages:
                return await interaction.followup.send(
                    "🔍 No messages found matching the specified criteria.", 
                    ephemeral=True
                )

            # Confirm deletion for large amounts
            if len(filtered_messages) > 50:
                view = ConfirmClearView(filtered_messages, interaction.channel)
                embed = discord.Embed(
                    title="⚠️ Confirm Bulk Deletion",
                    description=f"Found **{len(filtered_messages)}** messages matching your criteria.\n"
                               f"Are you sure you want to delete them?",
                    color=discord.Color.orange()
                )
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                # Delete messages directly
                deleted = await interaction.channel.delete_messages(filtered_messages)
                
                # Create summary embed
                embed = discord.Embed(
                    title="🧹 Advanced Clear Complete",
                    description=f"Successfully deleted **{len(deleted)}** messages.",
                    color=discord.Color.green()
                )
                
                # Add filter summary
                filters_used = []
                if user:
                    filters_used.append(f"👤 User: {user.mention}")
                if contains:
                    filters_used.append(f"📝 Contains: `{contains}`")
                if starts_with:
                    filters_used.append(f"▶️ Starts with: `{starts_with}`")
                if ends_with:
                    filters_used.append(f"⏹️ Ends with: `{ends_with}`")
                if regex:
                    filters_used.append(f"🔧 Regex: `{regex}`")
                if has_attachments is not None:
                    filters_used.append(f"📎 Attachments: {has_attachments}")
                if has_embeds is not None:
                    filters_used.append(f"📋 Embeds: {has_embeds}")
                if has_links is not None:
                    filters_used.append(f"🔗 Links: {has_links}")
                if from_bots is not None:
                    filters_used.append(f"🤖 Bots only: {from_bots}")
                if older_than_hours:
                    filters_used.append(f"⏰ Older than: {older_than_hours}h")
                if newer_than_hours:
                    filters_used.append(f"🕐 Newer than: {newer_than_hours}h")
                
                if filters_used:
                    embed.add_field(
                        name="🔍 Filters Applied",
                        value="\n".join(filters_used),
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I don't have permission to delete messages in this channel.", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}", 
                ephemeral=True
            )

class ConfirmClearView(discord.ui.View):
    def __init__(self, messages, channel):
        super().__init__(timeout=60)
        self.messages = messages
        self.channel = channel

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm and execute the bulk deletion"""
        try:
            deleted = await self.channel.delete_messages(self.messages)
            
            embed = discord.Embed(
                title="✅ Bulk Deletion Complete",
                description=f"Successfully deleted **{len(deleted)}** messages.",
                color=discord.Color.green()
            )
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to delete messages in this channel.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the bulk deletion"""
        embed = discord.Embed(
            title="❌ Deletion Cancelled",
            description="No messages were deleted.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        """Called when the view times out"""
        for item in self.children:
            item.disabled = True

async def setup(bot):
    await bot.add_cog(ClearAdvanced(bot))