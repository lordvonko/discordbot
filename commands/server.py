import discord
from discord.ext import commands
from discord import app_commands
import datetime

class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="server", description="Displays detailed information about the server.")
    async def server_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("This command can only be used in a server.")
            return

        # --- Member Status Count (excluding bots) ---
        # IMPORTANT: This requires the SERVER MEMBERS privileged intent to be enabled
        # on the Discord Developer Portal for bots in 100+ servers.
        online_count = 0
        idle_count = 0
        dnd_count = 0
        offline_count = 0
        
        human_members = 0
        bot_members = 0

        # Use guild.chunk() to ensure member list is fully populated
        await guild.chunk()

        for member in guild.members:
            if member.bot:
                bot_members += 1
            else:
                human_members += 1
                if member.status == discord.Status.online:
                    online_count += 1
                elif member.status == discord.Status.idle:
                    idle_count += 1
                elif member.status == discord.Status.dnd:
                    dnd_count += 1
                elif member.status == discord.Status.offline:
                    offline_count += 1
        
        # --- Create Embed ---
        embed = discord.Embed(
            title=f"Server Information: {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # --- General Information ---
        owner = guild.owner.mention if guild.owner else "Unknown"
        embed.add_field(name="Owner", value=owner, inline=True)
        embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Created On", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)

        # --- Member Counts ---
        embed.add_field(
            name="Members",
            value=f"👥 **Total:** {guild.member_count}\n"
                  f"👤 **Humans:** {human_members}\n"
                  f"🤖 **Bots:** {bot_members}",
            inline=True
        )

        # --- Member Status (FIXED LAYOUT) ---
        # This field now contains all statuses in a clean, single block.
        embed.add_field(
            name="Member Status (Humans)",
            value=f"🟢 **Online:** {online_count}\n"
                  f"🌙 **Idle:** {idle_count}\n"
                  f"⛔ **Do Not Disturb:** {dnd_count}\n"
                  f"⚫ **Offline:** {offline_count}",
            inline=True
        )
        
        # --- Channel Counts ---
        embed.add_field(
            name="Channels",
            value=f"💬 **Text:** {len(guild.text_channels)}\n"
                  f"🔊 **Voice:** {len(guild.voice_channels)}\n"
                  f"🗂️ **Categories:** {len(guild.categories)} ",
            inline=True
        )

        # --- Roles and Emojis ---
        role_count = len(guild.roles)
        emoji_count = len(guild.emojis)
        embed.add_field(name="Roles", value=f"🎨 **Count:** {role_count}", inline=True)
        embed.add_field(name="Emojis", value=f"😀 **Count:** {emoji_count}", inline=True)
        
        # --- Verification and Boosts ---
        verification_level = str(guild.verification_level).capitalize()
        boost_tier = f"Tier {guild.premium_tier}" if guild.premium_tier > 0 else "No Boosts"
        embed.add_field(name="Verification Level", value=verification_level, inline=True)
        embed.add_field(name="Boost Status", value=f"✨ **{boost_tier}**\n"
                                                   f"🚀 **Boosts:** {guild.premium_subscription_count}", inline=True)

        embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Server(bot))