import discord
from discord.ext import commands
from discord import app_commands

class Comandos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Shows the list of available commands.")
    async def help(self, interaction: discord.Interaction):
        """Displays a dynamic list of all available slash commands."""
        embed = discord.Embed(
            title="Help - Command List",
            description="Here are all the available commands:",
            color=discord.Color.blue()
        )

        for cog_name, cog in self.bot.cogs.items():
            command_list = []
            for command in cog.get_app_commands():
                command_list.append(f"`/{command.name}` - {command.description}")
            
            if command_list:
                embed.add_field(
                    name=cog_name,
                    value="\n".join(command_list),
                    inline=False
                )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Comandos(bot))

