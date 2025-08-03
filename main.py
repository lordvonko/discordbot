import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import traceback
from keep_alive import keep_alive  # Para manter online 24/7

keep_alive()

# --- Configuração do Bot ---
TOKEN = os.getenv("DISCORD_TOKEN")  # Pega o token do Replit Secrets
GUILD_ID = os.getenv(
    "TEST_GUILD_ID"
)  # Adicione no Replit Secrets para testes (ex: seu server ID)
IS_PROD = os.getenv(
    "IS_PROD",
    "0") == "1"  # "1" para produção (sync global), "0" para dev (guild)

# Define as permissões (Intents) que o bot precisa
intents = discord.Intents.default()
intents.message_content = True  # Para eventos de mensagem, se necessário
intents.members = True  # Para comandos como ban/kick
intents.voice_states = True  # Para suporte a voice (música)

# Cria a instância do bot sem prefixo funcional (foco em slash commands)
bot = commands.Bot(command_prefix="thisbotwontuse!", intents=intents)


# --- Custom Check para Owner ---
async def is_owner(interaction: discord.Interaction) -> bool:
    return await bot.is_owner(interaction.user)


# --- Evento de Inicialização ---
@bot.event
async def on_ready():
    print(f'Logado como {bot.user}!')
    print('O bot está pronto para ser boiola e tocar um som!')
    print('------')
    # Sincronização automática dos slash commands
    await sync_commands(manual=False)


# --- Função auxiliar para sincronizar com retry ---
async def sync_commands(manual=True, scope="guild"):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if scope == "global":
                fmt = await bot.tree.sync()
                msg = f"Sincronizados {len(fmt)} comandos globalmente."
            else:
                if not GUILD_ID:
                    raise ValueError(
                        "TEST_GUILD_ID não definido para sync guild.")
                guild = discord.Object(id=int(GUILD_ID))
                fmt = await bot.tree.sync(guild=guild)
                msg = f"Sincronizados {len(fmt)} comandos no guild {GUILD_ID}."
            print(msg)
            return msg
        except Exception as e:
            print(
                f"Erro ao sincronizar (tentativa {attempt+1}/{max_retries}): {str(e)}"
            )
            print(traceback.format_exc())
            if attempt < max_retries - 1:
                await asyncio.sleep(5)  # Delay antes de retry
    return f"Falha na sincronização após {max_retries} tentativas."


# --- Comando de Sync como Slash (/) ---
@bot.tree.command(name="sync",
                  description="Sincroniza os comandos de barra (apenas owner)")
@app_commands.check(is_owner)  # Usa o check personalizado
@app_commands.describe(
    scope="Escolha 'guild' para testes ou 'global' para produção")
@app_commands.choices(scope=[
    app_commands.Choice(name="Guild (testes)", value="guild"),
    app_commands.Choice(name="Global (produção)", value="global")
])
async def sync_command(interaction: discord.Interaction, scope: str = "guild"):
    await interaction.response.defer(ephemeral=True
                                     )  # Defer para evitar timeout
    print(f"Sincronizando comandos de barra via /sync (scope: {scope})...")
    result = await sync_commands(manual=True, scope=scope)
    await interaction.followup.send(result, ephemeral=True)


# --- Função para Carregar os Comandos (Cogs) ---
async def load_cogs():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'commands.{filename[:-3]}')
                print(f'Carregado o cog: {filename}')
            except Exception as e:
                print(f'Falha ao carregar o cog {filename}: {str(e)}')
                print(traceback.format_exc())


# --- Função Principal para Iniciar Tudo ---
async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)


# Roda o bot
if __name__ == "__main__":
    asyncio.run(main())
