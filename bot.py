import os
import asyncio
import aiohttp
import discord
from discord.ext import commands

TOKEN = os.environ.get("DISCORD_TOKEN")

if not TOKEN:
    raise SystemExit(
        "Missing DISCORD_TOKEN. Add it in GitHub: "
        "Settings > Secrets and variables > Actions"
    )

# name -> (Roblox Place ID, title)
GAMES = {
    "egg": (107778070777162, "🥚 Steal an Egg"),
    "outfit": (124239460312806, "👕 Sell Your Outfit"),
}

intents = discord.Intents.default()
intents.message_content = True


class GameBot(commands.Bot):
    async def setup_hook(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "Mozilla/5.0"}
        )

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"Slash command sync error: {e}")

    async def close(self):
        if hasattr(self, "session") and not self.session.closed:
            await self.session.close()

        await super().close()


bot = GameBot(
    command_prefix="!",
    intents=intents
)


async def fetch_servers(session, place_id):
    url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public"

    params = {
        "sortOrder": "Asc",
        "limit": 100,
        "excludeFullGames": "true",
    }

    for attempt in range(3):
        try:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as r:

                if r.status == 200:
                    return await r.json()

                print(
                    f"Roblox API HTTP {r.status} "
                    f"(attempt {attempt + 1}/3)"
                )

        except asyncio.TimeoutError:
            print(
                f"Roblox API timeout "
                f"(attempt {attempt + 1}/3)"
            )

        except aiohttp.ClientError as e:
            print(
                f"Roblox API error: {e} "
                f"(attempt {attempt + 1}/3)"
            )

        except Exception as e:
            print(
                f"Unexpected error: {e} "
                f"(attempt {attempt + 1}/3)"
            )

        await asyncio.sleep(2)

    return None


def make_server_embed(game_name, title, data):
    servers = data.get("data", [])

    embed = discord.Embed(
        title=f"{title} — Servers",
        description="Public Roblox servers with available slots.",
        color=discord.Color.blurple(),
    )

    if not servers:
        embed.add_field(
            name="No servers found",
            value="No available public servers were returned.",
            inline=False,
        )
        return embed

    shown = 0

    for server in servers:
        if shown >= 10:
            break

        server_id = server.get("id")
        playing = server.get("playing", 0)
        max_players = server.get("maxPlayers", 0)

        if not server_id:
            continue

        join_url = (
            "https://www.roblox.com/games/start?"
            f"placeId={GAMES[game_name][0]}"
            f"&gameInstanceId={server_id}"
        )

        embed.add_field(
            name=f"🟢 {playing}/{max_players} players",
            value=f"[Join Server]({join_url})",
            inline=False,
        )

        shown += 1

    embed.set_footer(
        text=f"Showing {shown} available server(s)"
    )

    return embed


class GameSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Steal an Egg",
                value="egg",
                emoji="🥚",
            ),
            discord.SelectOption(
                label="Sell Your Outfit",
                value="outfit",
                emoji="👕",
            ),
        ]

        super().__init__(
            placeholder="Choose a Roblox game...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        game_name = self.values[0]

        place_id, title = GAMES[game_name]

        await interaction.response.defer()

        data = await fetch_servers(
            interaction.client.session,
            place_id,
        )

        if data is None:
            await interaction.followup.send(
                "❌ Failed to get Roblox servers. Try again later.",
                ephemeral=True,
            )
            return

        embed = make_server_embed(
            game_name,
            title,
            data,
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True,
        )


class GameView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

        self.add_item(GameSelect())


@bot.command(name="servers")
async def servers(ctx):
    embed = discord.Embed(
        title="🎮 Roblox Server Finder",
        description=(
            "Select a game below to find available "
            "public Roblox servers."
        ),
        color=discord.Color.blurple(),
    )

    await ctx.send(
        embed=embed,
        view=GameView(),
    )


@bot.tree.command(
    name="servers",
    description="Find available Roblox servers"
)
async def slash_servers(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Roblox Server Finder",
        description=(
            "Select a game below to find available "
            "public Roblox servers."
        ),
        color=discord.Color.blurple(),
    )

    await interaction.response.send_message(
        embed=embed,
        view=GameView(),
        ephemeral=True,
    )


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")


bot.run(TOKEN)
