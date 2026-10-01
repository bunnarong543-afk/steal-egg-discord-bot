import os
import asyncio
from typing import Literal
import aiohttp
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN. Add it in GitHub: Settings > Secrets and variables > Actions")

# name -> (place id, title)
GAMES = {
    "egg": (107778070777162, "🥚 Steal an Egg"),
    "outfit": (124239460312806, "👕 Sell Your Outfit"),
}

intents = discord.Intents.default()
intents.message_content = True  # also enable in Discord Developer Portal > Bot


class GameBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"})
        await self.tree.sync()

    async def close(self):
        await self.session.close()
        await super().close()


bot = GameBot(command_prefix="!", intents=intents)


async def fetch_servers(session, place_id):
    # sortOrder=Asc returns the servers with the fewest players first
    url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public"
    params = {"sortOrder": "Asc", "limit": 100, "excludeFullGames": "true"}
    for attempt in range(3):
        async with session.get(url, params=params) as r:
