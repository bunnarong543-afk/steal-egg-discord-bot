import os
import asyncio
import aiohttp
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("Missing DISCORD_TOKEN. Add it in GitHub: Settings > Secrets and variables > Actions")

# Steal an Egg
PLACE_ID = 107778070777162
TITLE = "🥚 Steal an Egg"
API_URL = f"https://games.roblox.com/v1/games/{PLACE_ID}/servers/Public"

intents = discord.Intents.default()
intents.message_content = True  # also enable in Discord Developer Portal > Bot


class EggBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"})
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash command(s)", flush=True)
        except Exception as e:
            print(f"Slash sync error: {e}", flush=True)

    async def close(self):
        await self.session.close()
        await super().close()


bot = EggBot(command_prefix="!", intents=intents)


async def fetch_servers(session):
    # sortOrder=Asc returns the servers with the fewest players first
    params = {"sortOrder": "Asc", "limit": 100, "excludeFullGames": "true"}
    for attempt in range(3):
        try:
            async with session.get(API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                elif response.status == 429:
                    # Rate limited, wait before retrying
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    print(f"Roblox API returned status {response.status}", flush=True)
        except Exception as e:
            print(f"Error fetching servers (attempt {attempt+1}): {e}", flush=True)
        await asyncio.sleep(1)
    return []


@bot.tree.command(name="servers", description="Find low player servers for Steal an Egg")
async def servers(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    servers_list = await fetch_servers(bot.session)
    if not servers_list:
        await interaction.followup.send("❌ Failed to fetch servers or no servers available right now.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🌐 {TITLE} - Low Player Servers",
        description="Showing available servers sorted by fewest players:",
        color=discord.Color.orange()
    )

    # Display top 5 lowest player servers
    top_servers = servers_list[:5]
    
    for i, s in enumerate(top_servers, 1):
        playing = s.get("playing", 0)
        max_players = s.get("maxPlayers", 0)
        ping = s.get("ping", "N/A")
        fps = s.get("fps", "N/A")
        server_id = s.get("id", "Unknown")
        
        embed.add_field(
            name=f"Server #{i} ({playing}/{max_players} players)",
            value=f"**Ping:** {ping}ms | **FPS:** {fps}\n`Job ID:` ```{server_id}```",
            inline=False
        )

    embed.set_footer(text="Copy the Job ID to join via browser extension or script.")
    await interaction.followup.send(embed=embed)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})", flush=True)


if __name__ == "__main__":
    bot.run(TOKEN)
