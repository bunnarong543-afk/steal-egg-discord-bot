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
intents.message_content = True

# Dictionary ដើម្បីទុករក្សាទុកសារចាស់របស់អ្នកប្រើប្រាស់សម្រាប់លុបពេលបញ្ជាថ្មី
user_last_messages = {}


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
    params = {"sortOrder": "Asc", "limit": 100, "excludeFullGames": "true"}
    for attempt in range(3):
        try:
            async with session.get(API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("data", [])
                elif response.status == 429:
                    await asyncio.sleep(2 * (attempt + 1))
                else:
                    print(f"Roblox API returned status {response.status}", flush=True)
        except Exception as e:
            print(f"Error fetching servers (attempt {attempt+1}): {e}", flush=True)
        await asyncio.sleep(1)
    return []


def is_hacker(server_data):
    # ពិនិត្យរកមើលសញ្ញាណ Hacker (បើមាន FPS ខុសប្រក្រតី ឬសង្ស័យ)
    fps = server_data.get("fps", 0)
    if fps and fps > 999:
        return True
    return False


@bot.tree.command(name="servers", description="ស្វែងរក Server ដែលមានមនុស្ស ១ នាក់គត់ មិនមាន Hacker និង Ping ល្អ")
async def servers(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    user_id = interaction.user.id
    # លុបសារចាស់របស់អ្នកប្រើនេះចោលប្រសិនបើមាន
    if user_id in user_last_messages:
        try:
            old_msg = user_last_messages[user_id]
            await old_msg.delete()
        except Exception:
            pass

    servers_list = await fetch_servers(bot.session)
    if not servers_list:
        msg = await interaction.followup.send("❌ រកមិនឃើញ Server ទេ។", ephemeral=True)
        user_last_messages[user_id] = msg
        return

    # ត្រងរក Server ណាដែលមានមនុស្ស ១ នាក់ (playing == 1) និងគ្មាន Hacker
    valid_servers = []
    for s in servers_list:
        if s.get("playing") == 1 and not is_hacker(s):
            valid_servers.append(s)

    if not valid_servers:
        msg = await interaction.followup.send("❌ រកមិនដែលមាន Server ទំនេរ ១ នាក់គត់ និងគ្មាន Hacker ទេ។ សូមព្យាយាមផ្ដេញម្ដងទៀត។", ephemeral=True)
        user_last_messages[user_id] = msg
        return

    # រៀបចំតម្រៀបយក Server ដែលមាន Ping ល្អបំផុត (ទាបជាងគេ)
    valid_servers.sort(key=lambda x: x.get("ping", 999))
    
    # យក Server ល្អបំផុតដំបូងគេ
    s = valid_servers[0]
    playing = s.get("playing", 1)
    max_players = s.get("maxPlayers", 7)
    ping = s.get("ping", "N/A")
    fps = s.get("fps", "N/A")
    server_id = s.get("id", "Unknown")

    embed = discord.Embed(
        title=f"🌐 {TITLE} - Clean Server",
        description="បានរកឃើញ Server ដែលមានមនុស្ស **១ នាក់** គត់ និងមាន Ping ល្អស្អាត៖",
        color=discord.Color.green()
    )
    embed.add_field(name="👥 អ្នកលេង", value=f"{playing}/{max_players}", inline=True)
    embed.add_field(name="📶 Ping", value=f"{ping}ms", inline=True)
    embed.add_field(name="⚡ FPS", value=str(fps), inline=True)
    embed.add_field(name="🆔 Job ID", value=f"```{server_id}```", inline=False)
    embed.set_footer(text="ចុចប៊ូតុងខាងក្រោមដើម្បីចូលលេងចំ Server នេះផ្ទាល់។")

    # បង្កើតប៊ូតុង Join ចូលចំ Server ហ្នឹងផ្ទាល់
    join_url = f"https://www.roblox.com/games/start?placeId={PLACE_ID}&gameInstanceId={server_id}"
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="🎮 Join Server", style=discord.ButtonStyle.url, url=join_url))

    msg = await interaction.followup.send(embed=embed, view=view)
    user_last_messages[user_id] = msg


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})", flush=True)


if __name__ == "__main__":
    bot.run(TOKEN)

