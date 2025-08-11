import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio

class BanNotifications(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Triggered when a member is banned from a server"""
        
        # Small delay to ensure ban entry is created
        await asyncio.sleep(2)
        
        try:
            # Fetch the ban entry to get the reason
            ban_entry = await guild.fetch_ban(user)
            ban_reason = ban_entry.reason or "No reason provided"
        except:
            ban_reason = "No reason provided"
        
        # Create informative DM embed
        embed = discord.Embed(
            title="🚫 You have been banned",
            description=f"You have been banned from **{guild.name}**",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Server information
        embed.add_field(
            name="🏠 Server Details",
            value=f"**Name:** {guild.name}\n"
                  f"**ID:** `{guild.id}`\n"
                  f"**Members:** {guild.member_count:,}",
            inline=True
        )
        
        # Ban details
        embed.add_field(
            name="📝 Ban Information",
            value=f"**Reason:** {ban_reason}\n"
                  f"**Date:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>",
            inline=True
        )
        
        # Server icon if available
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Appeal information
        embed.add_field(
            name="⚖️ Think this ban was unfair?",
            value=f"You can submit a ban appeal using the bot:\n"
                  f"• Send me a DM with `/ban_appeal {guild.id} <your reason>`\n"
                  f"• Explain why you believe the ban should be lifted\n"
                  f"• Server moderators will review your appeal",
            inline=False
        )
        
        # Additional helpful information
        embed.add_field(
            name="💡 What happens next?",
            value="• You can no longer access this server\n"
                  "• Your messages and roles have been preserved\n"
                  "• If appealed successfully, you can rejoin\n"
                  "• Check `/ban_list` to see all your bans",
            inline=False
        )
        
        # Tips section with random helpful advice
        tips = [
            "📋 **Tip:** Keep track of server rules to avoid future issues",
            "🤝 **Tip:** Consider reaching out to server staff if you have questions",
            "⏰ **Tip:** Some servers have cooldown periods before appeals are accepted",
            "📚 **Tip:** Review community guidelines before appealing",
            "🎯 **Tip:** Be honest and respectful when writing your appeal",
            "💭 **Tip:** Think about what led to this situation to prevent future bans",
            "🔍 **Tip:** Use `/ban_check` to verify your ban status anytime"
        ]
        
        import random
        selected_tip = random.choice(tips)
        
        embed.add_field(
            name="💭 Helpful Tip",
            value=selected_tip,
            inline=False
        )
        
        # Footer with bot branding
        embed.set_footer(
            text="Musashi Bot • Ban Notification System",
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None
        )
        
        # Try to send DM to the banned user
        try:
            await user.send(embed=embed)
            print(f"✅ Sent ban notification to {user} ({user.id}) for ban from {guild.name}")
        except discord.Forbidden:
            print(f"❌ Could not send ban notification to {user} ({user.id}) - DMs disabled")
            
            # Try to log in a staff channel if DM fails
            await self.try_log_failed_notification(guild, user, ban_reason)
        except Exception as e:
            print(f"❌ Error sending ban notification to {user} ({user.id}): {e}")

    async def try_log_failed_notification(self, guild, user, reason):
        """Try to log failed DM notification in a staff channel"""
        
        # Look for common staff channel names
        staff_channels = []
        for channel in guild.text_channels:
            channel_name = channel.name.lower()
            if any(word in channel_name for word in [
                'mod', 'staff', 'admin', 'log', 'ban', 'audit'
            ]):
                staff_channels.append(channel)
        
        if not staff_channels:
            return
        
        # Use the first staff channel found
        staff_channel = staff_channels[0]
        
        try:
            embed = discord.Embed(
                title="⚠️ Failed Ban Notification",
                description=f"Could not send ban notification to {user.mention} ({user}) - DMs are disabled.",
                color=discord.Color.orange()
            )
            embed.add_field(name="User", value=f"{user} ({user.id})", inline=True)
            embed.add_field(name="Reason", value=reason, inline=True)
            embed.add_field(
                name="Note", 
                value="The user was not notified of their ban via DM. "
                      "They can still use `/ban_list` to discover their ban status.",
                inline=False
            )
            
            await staff_channel.send(embed=embed)
            print(f"📝 Logged failed ban notification in #{staff_channel.name}")
            
        except discord.Forbidden:
            print(f"❌ No permission to log in #{staff_channel.name}")
        except Exception as e:
            print(f"❌ Error logging failed notification: {e}")

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Triggered when a member is unbanned from a server"""
        
        # Create unban notification embed
        embed = discord.Embed(
            title="✅ You have been unbanned",
            description=f"Great news! You have been unbanned from **{guild.name}**",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Server information
        embed.add_field(
            name="🏠 Server Details",
            value=f"**Name:** {guild.name}\n"
                  f"**ID:** `{guild.id}`\n"
                  f"**Members:** {guild.member_count:,}",
            inline=True
        )
        
        # Unban details
        embed.add_field(
            name="🎉 Unban Information",
            value=f"**Date:** <t:{int(datetime.now(timezone.utc).timestamp())}:F>\n"
                  f"**Status:** You can now rejoin the server",
            inline=True
        )
        
        # Server icon if available
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Rejoin information
        if guild.vanity_url_code:
            invite_text = f"discord.gg/{guild.vanity_url_code}"
        else:
            # Try to create an invite
            try:
                # Find a suitable channel for invite
                invite_channel = None
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).create_instant_invite:
                        invite_channel = channel
                        break
                
                if invite_channel:
                    invite = await invite_channel.create_invite(
                        max_age=86400,  # 24 hours
                        max_uses=1,
                        reason="Unban notification invite"
                    )
                    invite_text = invite.url
                else:
                    invite_text = "Contact server staff for an invite link"
            except:
                invite_text = "Contact server staff for an invite link"
        
        embed.add_field(
            name="🔗 Ready to return?",
            value=f"You can rejoin the server using:\n{invite_text}",
            inline=False
        )
        
        # Guidelines reminder
        embed.add_field(
            name="📋 Before rejoining",
            value="• Review the server rules carefully\n"
                  "• Ensure you understand what led to the original ban\n"
                  "• Be respectful to all members and staff\n"
                  "• Follow all community guidelines",
            inline=False
        )
        
        # Footer
        embed.set_footer(
            text="Musashi Bot • Unban Notification System",
            icon_url=self.bot.user.display_avatar.url if self.bot.user else None
        )
        
        # Try to send DM to the unbanned user
        try:
            await user.send(embed=embed)
            print(f"✅ Sent unban notification to {user} ({user.id}) for unban from {guild.name}")
        except discord.Forbidden:
            print(f"❌ Could not send unban notification to {user} ({user.id}) - DMs disabled")
        except Exception as e:
            print(f"❌ Error sending unban notification to {user} ({user.id}): {e}")

async def setup(bot):
    await bot.add_cog(BanNotifications(bot))