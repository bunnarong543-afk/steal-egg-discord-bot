import os
import asyncio
import aiohttp
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN. Add it in GitHub: Settings > Secrets and variables > Actions")

# Steal an Egg place ID (can be overridden with a PLACE_ID env var)
PLACE_ID = 107778070777162
API_URL = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"

intents = discord.Intents.default()
intents.message_content = True  # also enable in Discord Developer Portal > Bot


class EggBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"})
        await self.tree.sync()  # registers /servers (needs applications.commands scope to be visible)

    async def close(self):
        await self.session.close()
        await super().close()


bot = EggBot(command_prefix="!", intents=intents)


async def fetch_servers(session):
    # sortOrder=Asc returns the servers with the fewest players first
    params = {"sortOrder": "Asc", "limit": 100, "excludeFullGames": "true"}
    for attempt in range(3):
        async with session.get(API_URL, params=params) as r:
            status = r.status
            data = await r.json() if status == 200 else {}
        if status == 200: return data.get("data", [])
        if status != 429: raise RuntimeError(f"Roblox API error {status}")
