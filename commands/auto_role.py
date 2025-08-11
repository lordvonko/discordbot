
import discord
from discord.ext import commands
from discord import app_commands, ui
import sqlite3
import json
import os
from typing import Optional

# --- Database Setup ---
DB_FILE = "data/autorole.db"
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # auto_role_messages: Stores the main message and its configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auto_role_messages (
                message_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_content TEXT
            )
        """)
        # role_mappings: Stores the emoji-to-role mapping for each message
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                FOREIGN KEY (message_id) REFERENCES auto_role_messages (message_id) ON DELETE CASCADE
            )
        """)
        conn.commit()

# --- Views ---
class RoleSelectView(ui.View):
    def __init__(self, mappings):
        super().__init__(timeout=None)
        for mapping in mappings:
            self.add_item(RoleButton(
                emoji=mapping['emoji'],
                role_id=mapping['role_id'],
                custom_id=f"autorole:{mapping['message_id']}:{mapping['role_id']}"
            ))

class RoleButton(ui.Button):
    def __init__(self, emoji: str, role_id: int, custom_id: str):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.secondary, custom_id=custom_id)
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if not role:
            return await interaction.response.send_message("❌ This role no longer exists.", ephemeral=True)

        has_role = role in interaction.user.roles
        
        try:
            if has_role:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"✅ Role **{role.name}** has been removed.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ You now have the **{role.name}** role.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to manage roles. Please check my permissions.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# --- Cog ---
class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()
        self.bot.add_view(RoleSelectView(mappings=[])) # Register the view persistently

    @commands.Cog.listener()
    async def on_ready(self):
        print("AutoRole Cog is ready. Loading persistent views.")
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT message_id FROM auto_role_messages")
            messages = cursor.fetchall()
            for (message_id,) in messages:
                cursor.execute("SELECT emoji, role_id FROM role_mappings WHERE message_id = ?", (message_id,))
                mappings = [{'emoji': e, 'role_id': r, 'message_id': message_id} for e, r in cursor.fetchall()]
                self.bot.add_view(RoleSelectView(mappings=mappings))
        print(f"Loaded {len(messages)} auto role views.")


    @app_commands.command(name="autorole_create", description="Create a new auto-role message.")
    @app_commands.describe(
        channel="The channel to send the auto-role message in.",
        message_content="The text to display above the role buttons (e.g., 'React to get roles').",
        role1="The first role to assign.",
        emoji1="The emoji for the first role.",
        role2="The second role (optional).",
        emoji2="The emoji for the second role (optional).",
        role3="The third role (optional).",
        emoji3="The emoji for the third role (optional).",
        role4="The fourth role (optional).",
        emoji4="The emoji for the fourth role (optional).",
        role5="The fifth role (optional).",
        emoji5="The emoji for the fifth role (optional)."
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_create(
        self, 
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message_content: str,
        role1: discord.Role, emoji1: str,
        role2: Optional[discord.Role] = None, emoji2: Optional[str] = None,
        role3: Optional[discord.Role] = None, emoji3: Optional[str] = None,
        role4: Optional[discord.Role] = None, emoji4: Optional[str] = None,
        role5: Optional[discord.Role] = None, emoji5: Optional[str] = None
    ):
        """Creates a message with buttons for role selection."""
        
        pairs = [
            (role1, emoji1), (role2, emoji2), (role3, emoji3),
            (role4, emoji4), (role5, emoji5)
        ]
        
        mappings = []
        for role, emoji in pairs:
            if role and emoji:
                # Basic validation
                if role.position >= interaction.guild.me.top_role.position:
                    await interaction.response.send_message(f"❌ I cannot assign the role **{role.name}** because it is higher than or equal to my own top role.", ephemeral=True)
                    return
                mappings.append({'role': role, 'emoji': emoji})

        if not mappings:
            await interaction.response.send_message("❌ You must provide at least one valid role and emoji pair.", ephemeral=True)
            return

        # Create Embed
        embed = discord.Embed(
            title="✨ Role Selection",
            description=message_content,
            color=discord.Color.purple()
        )
        embed.set_footer(text="Click the buttons below to get or remove roles.")

        # Send message and get its ID
        try:
            msg = await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to send messages in that channel.", ephemeral=True)
            return
        
        # Store in DB
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO auto_role_messages (message_id, guild_id, channel_id, message_content) VALUES (?, ?, ?, ?)",
                (msg.id, interaction.guild.id, channel.id, message_content)
            )
            db_mappings = []
            for item in mappings:
                db_mappings.append((msg.id, item['emoji'], item['role'].id))
            
            cursor.executemany(
                "INSERT INTO role_mappings (message_id, emoji, role_id) VALUES (?, ?, ?)",
                db_mappings
            )
            conn.commit()

        # Add view to the message
        view_mappings = [{'emoji': m['emoji'], 'role_id': m['role'].id, 'message_id': msg.id} for m in mappings]
        view = RoleSelectView(mappings=view_mappings)
        await msg.edit(view=view)

        await interaction.response.send_message(f"✅ Auto-role message created in {channel.mention}", ephemeral=True)

    @app_commands.command(name="autorole_delete", description="Delete an auto-role message.")
    @app_commands.describe(message_id="The message ID of the auto-role message to delete.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def autorole_delete(self, interaction: discord.Interaction, message_id: str):
        """Deletes an auto-role message and its database entries."""
        try:
            msg_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT channel_id FROM auto_role_messages WHERE message_id = ? AND guild_id = ?", (msg_id, interaction.guild.id))
            result = cursor.fetchone()

            if not result:
                return await interaction.response.send_message("❌ No auto-role message found with that ID in this server.", ephemeral=True)
            
            channel_id = result[0]
            
            # Delete from DB (cascading delete will handle role_mappings)
            cursor.execute("DELETE FROM auto_role_messages WHERE message_id = ?", (msg_id,))
            conn.commit()

        # Delete the original message
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            message = await channel.fetch_message(msg_id)
            await message.delete()
        except discord.NotFound:
            pass # Message already deleted, that's fine
        except discord.Forbidden:
            await interaction.response.send_message("⚠️ Could not delete the original message (missing permissions), but the entry is removed.", ephemeral=True)
            return

        await interaction.response.send_message("✅ Auto-role message and configuration deleted.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoRole(bot))
