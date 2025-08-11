import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import asyncio

class BanList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban_list", description="Lists servers where you are banned (DM only)")
    async def ban_list(self, interaction: discord.Interaction):
        """Lists all servers where the user is currently banned"""
        
        # Check if command is used in DM
        if interaction.guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in Direct Messages with the bot.", 
                ephemeral=True
            )

        await interaction.response.defer()

        user = interaction.user
        banned_servers = []
        accessible_servers = 0
        total_servers = len(self.bot.guilds)

        # Create initial embed showing progress
        progress_embed = discord.Embed(
            title="🔍 Checking Ban Status...",
            description=f"Scanning {total_servers} servers...",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=progress_embed)

        # Check each server for bans
        for i, guild in enumerate(self.bot.guilds, 1):
            try:
                # Try to fetch the ban entry for this user
                ban_entry = await guild.fetch_ban(user)
                
                # If we get here, the user is banned
                ban_info = {
                    'guild': guild,
                    'reason': ban_entry.reason or "No reason provided",
                    'ban_entry': ban_entry
                }
                banned_servers.append(ban_info)
                accessible_servers += 1
                
            except discord.NotFound:
                # User is not banned in this server
                accessible_servers += 1
                continue
            except discord.Forbidden:
                # Bot doesn't have permission to check bans in this server
                continue
            except Exception as e:
                # Other errors (server unavailable, etc.)
                print(f"Error checking ban status in {guild.name}: {e}")
                continue

            # Update progress every 10 servers
            if i % 10 == 0:
                try:
                    progress_embed.description = f"Scanning... {i}/{total_servers} servers checked"
                    await interaction.edit_original_response(embed=progress_embed)
                    await asyncio.sleep(0.1)  # Small delay to avoid rate limits
                except:
                    pass

        # Create results embed
        if not banned_servers:
            embed = discord.Embed(
                title="✅ Ban Status Report",
                description="🎉 **Great news!** You are not banned from any servers where this bot has access.",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(
                name="📊 Scan Summary",
                value=f"**Servers Checked:** {accessible_servers}/{total_servers}\n"
                      f"**Bans Found:** 0",
                inline=False
            )
            if accessible_servers < total_servers:
                embed.add_field(
                    name="ℹ️ Note",
                    value=f"Could not check {total_servers - accessible_servers} servers due to permission restrictions.",
                    inline=False
                )
        else:
            embed = discord.Embed(
                title="🚫 Ban Status Report",
                description=f"Found **{len(banned_servers)}** server{'s' if len(banned_servers) != 1 else ''} where you are banned.",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            
            # Add banned servers to embed
            ban_list = []
            for i, ban_info in enumerate(banned_servers[:10], 1):  # Limit to 10 to avoid embed limits
                guild = ban_info['guild']
                reason = ban_info['reason']
                
                # Truncate long reasons
                if len(reason) > 100:
                    reason = reason[:97] + "..."
                
                ban_list.append(
                    f"**{i}. {guild.name}**\n"
                    f"📝 *Reason:* {reason}\n"
                    f"🆔 *Server ID:* `{guild.id}`"
                )
            
            embed.add_field(
                name="🏴 Banned From",
                value="\n\n".join(ban_list),
                inline=False
            )
            
            if len(banned_servers) > 10:
                embed.add_field(
                    name="➕ Additional Bans",
                    value=f"And {len(banned_servers) - 10} more servers...\n"
                          f"Use `/ban_appeal` to appeal specific bans.",
                    inline=False
                )

            embed.add_field(
                name="📊 Scan Summary",
                value=f"**Servers Checked:** {accessible_servers}/{total_servers}\n"
                      f"**Bans Found:** {len(banned_servers)}",
                inline=True
            )
            
            embed.add_field(
                name="💡 What's Next?",
                value="Use `/ban_appeal <server_id> <reason>` to submit appeals for specific servers.",
                inline=True
            )

        embed.set_footer(text=f"Requested by {user.display_name}", icon_url=user.display_avatar.url)
        
        await interaction.edit_original_response(embed=embed)

        # If user has many bans, send additional detailed info
        if len(banned_servers) > 5:
            detailed_embed = discord.Embed(
                title="📋 Detailed Ban Information",
                color=discord.Color.orange()
            )
            
            # Group bans by reason for analysis
            reason_counts = {}
            for ban_info in banned_servers:
                reason = ban_info['reason']
                if reason in reason_counts:
                    reason_counts[reason] += 1
                else:
                    reason_counts[reason] = 1
            
            # Show most common ban reasons
            if len(reason_counts) > 1:
                sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
                reason_list = []
                for reason, count in sorted_reasons[:5]:
                    if len(reason) > 50:
                        reason = reason[:47] + "..."
                    reason_list.append(f"• {reason} ({count} server{'s' if count != 1 else ''})")
                
                detailed_embed.add_field(
                    name="📈 Most Common Ban Reasons",
                    value="\n".join(reason_list),
                    inline=False
                )
            
            # Server size analysis
            small_servers = sum(1 for ban_info in banned_servers if ban_info['guild'].member_count < 100)
            medium_servers = sum(1 for ban_info in banned_servers if 100 <= ban_info['guild'].member_count < 1000)
            large_servers = sum(1 for ban_info in banned_servers if ban_info['guild'].member_count >= 1000)
            
            detailed_embed.add_field(
                name="📊 Server Size Analysis",
                value=f"🏘️ Small servers (<100 members): {small_servers}\n"
                      f"🏙️ Medium servers (100-999 members): {medium_servers}\n"
                      f"🌆 Large servers (1000+ members): {large_servers}",
                inline=False
            )
            
            detailed_embed.set_footer(text="This analysis can help you identify patterns in your bans")
            
            await interaction.followup.send(embed=detailed_embed)

    @app_commands.command(name="ban_check", description="Check ban status in a specific server (DM only)")
    @app_commands.describe(server_id="The ID of the server to check")
    async def ban_check(self, interaction: discord.Interaction, server_id: str):
        """Check ban status in a specific server"""
        
        # Check if command is used in DM
        if interaction.guild:
            return await interaction.response.send_message(
                "❌ This command can only be used in Direct Messages with the bot.", 
                ephemeral=True
            )

        try:
            guild_id_int = int(server_id)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid server ID format.")

        guild = self.bot.get_guild(guild_id_int)
        if not guild:
            return await interaction.response.send_message(
                "❌ Server not found or bot is not in that server."
            )

        await interaction.response.defer()

        try:
            ban_entry = await guild.fetch_ban(interaction.user)
            
            # User is banned
            embed = discord.Embed(
                title="🚫 Ban Status",
                description=f"You are **banned** from **{guild.name}**",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Server", value=guild.name, inline=True)
            embed.add_field(name="Server ID", value=str(guild.id), inline=True)
            embed.add_field(name="Members", value=f"{guild.member_count:,}", inline=True)
            embed.add_field(name="Ban Reason", value=ban_entry.reason or "No reason provided", inline=False)
            embed.add_field(
                name="💡 Want to Appeal?",
                value=f"Use `/ban_appeal {guild.id} <your reason>` to submit an appeal.",
                inline=False
            )
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
        except discord.NotFound:
            # User is not banned
            embed = discord.Embed(
                title="✅ Ban Status",
                description=f"You are **not banned** from **{guild.name}**",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Server", value=guild.name, inline=True)
            embed.add_field(name="Server ID", value=str(guild.id), inline=True)
            embed.add_field(name="Members", value=f"{guild.member_count:,}", inline=True)
            
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
                
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Error",
                description="I don't have permission to check ban status in that server.",
                color=discord.Color.red()
            )
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while checking ban status: {str(e)}",
                color=discord.Color.red()
            )

        embed.set_footer(
            text=f"Requested by {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BanList(bot))