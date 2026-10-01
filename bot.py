import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")

    print(f"Bot online: {bot.user}")


async def get_servers(place_id, max_players=0):
    url = (
        f"https://games.roblox.com/v1/games/"
        f"{place_id}/servers/Public"
    )

    servers = []
    cursor = None

    async with aiohttp.ClientSession() as session:
        for _ in range(5):
            params = {
                "sortOrder": "Asc",
                "limit": 100
            }

            if cursor:
                params["cursor"] = cursor

            try:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

            except Exception:
                return None

            for server in data.get("data", []):
                playing = server.get("playing", 0)

                if playing <= max_players:
                    servers.append(server)

            cursor = data.get("nextPageCursor")
            if not cursor:
                break

            if servers:
                break

    return servers


@bot.tree.command(
    name="findserver",
    description="Find an empty or low-player Roblox server"
)
@app_commands.describe(
    game_id="Roblox Game Place ID",
    max_players="Maximum players allowed (0 = empty)"
)
async def findserver(
    interaction: discord.Interaction,
    game_id: str,
    max_players: app_commands.Range[int, 0, 100] = 0
):
    await interaction.response.defer(thinking=True)

    if not game_id.isdigit():
        await interaction.followup.send(
            "❌ Game ID must contain numbers only."
        )
        return

    servers = await get_servers(game_id, max_players)

    if servers is None:
        await interaction.followup.send(
            "⚠️ Roblox API error. Please try again."
        )
        return

    if not servers:
        await interaction.followup.send(
            "🔎 No matching public servers found."
        )
        return

    server = servers[0]
    playing = server.get("playing", 0)
    maximum = server.get("maxPlayers", 0)
    server_id = server.get("id")

    join_url = (
        "https://www.roblox.com/games/start"
        f"?placeId={game_id}&gameInstanceId={server_id}"
    )

    embed = discord.Embed(
        title="🎮 Roblox Server Found!",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👥 Players",
        value=f"{playing}/{maximum}",
        inline=True
    )

    embed.add_field(
        name="🆔 Server ID",
        value=f"`{server_id}`",
        inline=False
    )

    embed.add_field(
        name="🎯 Game ID",
        value=f"`{game_id}`",
        inline=True
    )

    view = discord.ui.View()
    view.add_item(
        discord.ui.Button(
            label="🚀 Join Server",
            url=join_url,
            style=discord.ButtonStyle.link
        )
    )

    await interaction.followup.send(
        embed=embed,
        view=view
    )


@bot.tree.command(
    name="help",
    description="Show bot commands"
)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Roblox Server Finder",
        description=(
            "**/findserver**\n"
            "Find Roblox public servers.\n\n"
            "**Example:**\n"
            "`/findserver game_id:123456 max_players:0`\n\n"
            "0 = empty servers only."
        ),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(embed=embed)


if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing!")

bot.run(TOKEN)
