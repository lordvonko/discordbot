import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timezone

APPEALS_FILE = "ban_appeals.json"

class BanAppeal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.appeals = self.load_appeals()

    def load_appeals(self):
        """Load ban appeals from JSON file"""
        if os.path.exists(APPEALS_FILE):
            with open(APPEALS_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_appeals(self):
        """Save ban appeals to JSON file"""
        with open(APPEALS_FILE, 'w') as f:
            json.dump(self.appeals, f, indent=4)

    @app_commands.command(name="ban_appeal", description="Submit a ban appeal (use in DM)")
    @app_commands.describe(
        guild_id="The server ID where you were banned",
        reason="Explain why you think the ban should be lifted"
    )
    async def ban_appeal(self, interaction: discord.Interaction, guild_id: str, reason: str):
        """Allows users to submit ban appeals via DM"""
        # Check if command is used in DM
        if interaction.guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in Direct Messages with the bot.", 
                ephemeral=True
            )

        try:
            guild_id_int = int(guild_id)
            guild = self.bot.get_guild(guild_id_int)
            if not guild:
                return await interaction.response.send_message(
                    "❌ Invalid server ID or bot is not in that server."
                )
        except ValueError:
            return await interaction.response.send_message("❌ Invalid server ID format.")

        user_id = str(interaction.user.id)
        guild_id_str = str(guild_id_int)

        # Check if user is actually banned
        try:
            ban_entry = await guild.fetch_ban(interaction.user)
        except discord.NotFound:
            return await interaction.response.send_message(
                f"❌ You are not banned from **{guild.name}**."
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I don't have permission to check ban status in that server."
            )

        # Check for existing pending appeal
        if guild_id_str in self.appeals:
            if user_id in self.appeals[guild_id_str]:
                if self.appeals[guild_id_str][user_id]['status'] == 'pending':
                    return await interaction.response.send_message(
                        "⏳ You already have a pending appeal for this server. Please wait for a response."
                    )

        # Create appeal entry
        appeal_data = {
            'user_id': user_id,
            'username': str(interaction.user),
            'guild_name': guild.name,
            'reason': reason,
            'submitted_at': datetime.now(timezone.utc).isoformat(),
            'status': 'pending'
        }

        if guild_id_str not in self.appeals:
            self.appeals[guild_id_str] = {}
        
        self.appeals[guild_id_str][user_id] = appeal_data
        self.save_appeals()

        # Create embed for moderators
        embed = discord.Embed(
            title="🏛️ New Ban Appeal",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="User", value=f"{interaction.user} ({user_id})", inline=True)
        embed.add_field(name="Server", value=guild.name, inline=True)
        embed.add_field(name="Original Ban Reason", value=ban_entry.reason or "No reason provided", inline=False)
        embed.add_field(name="Appeal Reason", value=reason, inline=False)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        # Find appeals channel or send to owner
        appeals_channel = None
        for channel in guild.text_channels:
            if 'appeal' in channel.name.lower() or 'ban-appeal' in channel.name.lower():
                appeals_channel = channel
                break
        
        if not appeals_channel:
            # Try to find mod channel
            for channel in guild.text_channels:
                if any(word in channel.name.lower() for word in ['mod', 'staff', 'admin']):
                    appeals_channel = channel
                    break

        if appeals_channel:
            view = AppealView(self, guild_id_str, user_id)
            try:
                await appeals_channel.send(embed=embed, view=view)
            except discord.Forbidden:
                # Fallback to owner DM
                owner = guild.owner
                if owner:
                    try:
                        await owner.send(embed=embed, view=view)
                    except discord.Forbidden:
                        pass

        await interaction.response.send_message(
            f"✅ Your ban appeal has been submitted to **{guild.name}**.\n"
            f"📧 Moderators will review your appeal and respond accordingly.\n"
            f"⏰ Please be patient as this may take some time."
        )

    @app_commands.command(name="appeal_status", description="Check status of your ban appeals")
    async def appeal_status(self, interaction: discord.Interaction):
        """Check the status of user's ban appeals"""
        if interaction.guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in Direct Messages with the bot.", 
                ephemeral=True
            )

        user_id = str(interaction.user.id)
        user_appeals = []

        for guild_id, appeals in self.appeals.items():
            if user_id in appeals:
                appeal = appeals[user_id]
                guild = self.bot.get_guild(int(guild_id))
                guild_name = guild.name if guild else f"Unknown Server ({guild_id})"
                
                status_emoji = {
                    'pending': '⏳',
                    'approved': '✅',
                    'denied': '❌'
                }.get(appeal['status'], '❓')

                user_appeals.append(f"{status_emoji} **{guild_name}**: {appeal['status'].title()}")

        if not user_appeals:
            return await interaction.response.send_message("📭 You have no ban appeals submitted.")

        embed = discord.Embed(
            title="📋 Your Ban Appeals Status",
            description="\n".join(user_appeals),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

class AppealView(discord.ui.View):
    def __init__(self, cog, guild_id: str, user_id: str):
        super().__init__(timeout=None)  # Persistent view
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve the ban appeal"""
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ You need ban permissions to handle appeals.", ephemeral=True)

        # Update appeal status
        if self.guild_id in self.cog.appeals and self.user_id in self.cog.appeals[self.guild_id]:
            self.cog.appeals[self.guild_id][self.user_id]['status'] = 'approved'
            self.cog.appeals[self.guild_id][self.user_id]['handled_by'] = str(interaction.user)
            self.cog.appeals[self.guild_id][self.user_id]['handled_at'] = datetime.now(timezone.utc).isoformat()
            self.cog.save_appeals()

        # Try to unban user
        guild = interaction.guild
        user = await self.cog.bot.fetch_user(int(self.user_id))
        
        try:
            await guild.unban(user, reason=f"Ban appeal approved by {interaction.user}")
            
            # Notify user via DM
            try:
                embed = discord.Embed(
                    title="✅ Ban Appeal Approved",
                    description=f"Your ban appeal for **{guild.name}** has been approved!\n"
                               f"You can now rejoin the server.",
                    color=discord.Color.green()
                )
                await user.send(embed=embed)
            except discord.Forbidden:
                pass  # User has DMs disabled

            # Update message
            embed = discord.Embed(
                title="✅ Ban Appeal Approved",
                description=f"Appeal approved by {interaction.user.mention}",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)

        except discord.NotFound:
            await interaction.response.send_message("❌ User is not banned.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to unban users.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error unbanning user: {e}", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, emoji="❌")
    async def deny_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deny the ban appeal"""
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ You need ban permissions to handle appeals.", ephemeral=True)

        # Show modal for denial reason
        modal = DenialReasonModal(self.cog, self.guild_id, self.user_id, interaction.user)
        await interaction.response.send_modal(modal)

class DenialReasonModal(discord.ui.Modal, title="Denial Reason"):
    def __init__(self, cog, guild_id: str, user_id: str, moderator):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.user_id = user_id
        self.moderator = moderator

    reason = discord.ui.TextInput(
        label="Reason for denial",
        placeholder="Explain why this appeal is being denied...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Update appeal status
        if self.guild_id in self.cog.appeals and self.user_id in self.cog.appeals[self.guild_id]:
            self.cog.appeals[self.guild_id][self.user_id]['status'] = 'denied'
            self.cog.appeals[self.guild_id][self.user_id]['denial_reason'] = self.reason.value
            self.cog.appeals[self.guild_id][self.user_id]['handled_by'] = str(self.moderator)
            self.cog.appeals[self.guild_id][self.user_id]['handled_at'] = datetime.now(timezone.utc).isoformat()
            self.cog.save_appeals()

        # Notify user via DM
        user = await self.cog.bot.fetch_user(int(self.user_id))
        try:
            embed = discord.Embed(
                title="❌ Ban Appeal Denied",
                description=f"Your ban appeal for **{interaction.guild.name}** has been denied.\n\n"
                           f"**Reason:** {self.reason.value}",
                color=discord.Color.red()
            )
            await user.send(embed=embed)
        except discord.Forbidden:
            pass  # User has DMs disabled

        # Update message
        embed = discord.Embed(
            title="❌ Ban Appeal Denied",
            description=f"Appeal denied by {self.moderator.mention}\n**Reason:** {self.reason.value}",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(BanAppeal(bot))