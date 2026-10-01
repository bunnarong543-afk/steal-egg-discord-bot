import os
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN environment variable")

intents = discord.Intents.default()
intents.message_content = True  # also enable it in Discord Developer Portal -> Bot

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})")


@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")


@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.display_name}!")


bot.run(TOKEN)

