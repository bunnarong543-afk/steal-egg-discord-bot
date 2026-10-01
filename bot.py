import os
import asyncio
import aiohttp
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN. Add it in GitHub: Settings > Secrets and variables > Actions")

# Steal an Egg place ID
PLACE_ID = 107778070777162
API_URL = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"

intents = discord.Intents.default()
intents.message_content = True  # also enable in Discord Developer Portal > Bot


class EggBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"})
        await self.tree.sync()

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
        await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError("Roblox rate limit, try again in a minute")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})", flush=True)


@bot.hybrid_command(name="servers", description="Find Steal an Egg public servers with the fewest players")
async def servers(ctx, count: int = 5):
    count = max(1, min(count, 10))
    await ctx.defer()
    try:
        data = await fetch_servers(bot.session)
    except Exception as e:
        return await ctx.send(f"❌ {e}")

    data = [s for s in data if s.get("id")]
    data.sort(key=lambda s: s.get("playing", 0))
    top = data[:count]
    if not top:
        return await ctx.send("No public servers found.")

    embed = discord.Embed(title="🥚 Steal an Egg - quietest servers", color=0x5865F2)
    view = discord.ui.View()
    for i, s in enumerate(top, 1):
        url = f"https://www.roblox.com/games/start?placeId={PLACE_ID}&gameInstanceId={s['id']}"
        ping = s.get("ping")
        embed.add_field(
            name=f"#{i} - {s.get('playing', '?')}/{s.get('maxPlayers', '?')} players",
            value=f"Ping: {ping} ms" if ping is not None else "Ping: n/a",
            inline=False,
        )
        view.add_item(discord.ui.Button(label=f"Join #{i}", url=url, row=(i - 1) // 5))
    await ctx.send(embed=embed, view=view)


@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")


bot.run(TOKEN)
