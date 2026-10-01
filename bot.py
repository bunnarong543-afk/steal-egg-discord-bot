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


def check_for_hackers(server_data):
    # ពិនិត្យមើលសញ្ញាណ Hackers (ឧទាហរណ៍៖ FPS ខ្ពស់ហួសហេតុ)
    fps = server_data.get("fps", 0)
    if fps and fps > 999:
        return "⚠️ មានសង្ស័យ Hacker / Bot (FPS ผิดปกติ)"
    return "✅ មិនមានសញ្ញាណ Hacker"


class ServerPaginator(discord.ui.View):
    def __init__(self, servers):
        super().__init__(timeout=180)
        self.servers = servers
        self.current_index = 0
        self.update_view()

    def update_view(self):
        self.clear_items()
        
        # 1. ប៊ូតុង Previous
        prev_button = discord.ui.Button(
            label="⬅️ មុន", 
            style=discord.ButtonStyle.secondary, 
            disabled=(self.current_index == 0)
        )
        prev_button.callback = self.prev_callback
        self.add_item(prev_button)

        # 2. ប៊ូតុង Join Server (Link Button)
        join_button = discord.ui.Button(
            label="🎮 Join Server", 
            style=discord.ButtonStyle.url, 
            url=f"https://www.roblox.com/games/{PLACE_ID}"
        )
        self.add_item(join_button)

        # 3. ប៊ូតុង Next
        next_button = discord.ui.Button(
            label="➡️ បន្ទាប់", 
            style=discord.ButtonStyle.secondary, 
            disabled=(self.current_index >= len(self.servers) - 1)
        )
        next_button.callback = self.next_callback
        self.add_item(next_button)

    async def prev_callback(self, interaction: discord.Interaction):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_view()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def next_callback(self, interaction: discord.Interaction):
        if self.current_index < len(self.servers) - 1:
            self.current_index += 1
            self.update_view()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    def create_embed(self):
        s = self.servers[self.current_index]
        playing = s.get("playing", 0)
        max_players = s.get("maxPlayers", 0)
        ping = s.get("ping", "N/A")
        fps = s.get("fps", "N/A")
        server_id = s.get("id", "Unknown")
        
        hacker_status = check_for_hackers(s)

        embed = discord.Embed(
            title=f"🌐 {TITLE} - Server #{self.current_index + 1}",
            description=f"**ស្ថានភាព:** {hacker_status}",
            color=discord.Color.green() if "មិនមាន" in hacker_status else discord.Color.red()
        )
        embed.add_field(name="👥 អ្នកលេង", value=f"{playing}/{max_players}", inline=True)
        embed.add_field(name="📶 Ping", value=f"{ping}ms", inline=True)
        embed.add_field(name="⚡ FPS", value=str(fps), inline=True)
        embed.add_field(name="🆔 Job ID", value=f"```{server_id}```", inline=False)
        embed.set_footer(text=f"Server ទី {self.current_index + 1} នៃ {len(self.servers)}")
        return embed


@bot.tree.command(name="servers", description="រកមើល Server ហ្គេម Steal an Egg ម្ដងមួយ និងពិនិត្យ Hacker")
async def servers(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    servers_list = await fetch_servers(bot.session)
    if not servers_list:
        await interaction.followup.send("❌ រកមិនឃើញ Server ឬមានបញ្ហាទាក់ទងនឹង Roblox API ទេ។", ephemeral=True)
        return

    top_servers = servers_list[:10]
    view = ServerPaginator(top_servers)
    embed = view.create_embed()
    
    await interaction.followup.send(embed=embed, view=view)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})", flush=True)


if __name__ == "__main__":
    bot.run(TOKEN)

