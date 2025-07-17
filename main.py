import os, json, discord, asyncio, random, aiohttp
from discord.ext import commands, tasks
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.getenv("TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

SERVER_CONFIG = "server_config.json"
if not os.path.exists(SERVER_CONFIG):
    with open(SERVER_CONFIG, "w") as f:
        json.dump({}, f)

def load_config():
    with open(SERVER_CONFIG) as f:
        return json.load(f)

def save_config(data):
    with open(SERVER_CONFIG, "w") as f:
        json.dump(data, f, indent=2)

ALL_TAGS = [
    "anime", "egirl", "eboy", "faceless", "cute", "goth", "emo", "pixel",
    "vaporwave", "fantasy", "cyber", "matching", "banners", "kpop", "drip",
    "body"
]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    post_images.start()

@bot.slash_command(name="setup_pfp", description="Set up PFP posting channel and tags.")
async def setup_pfp(ctx: discord.ApplicationContext):
    view = TagSetupView(ctx)
    await ctx.respond("Choose the tags for this server:", view=view, ephemeral=True)

class TagSetupView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.selected_tags = []

        for tag in ALL_TAGS:
            self.add_item(TagButton(tag))

    async def on_timeout(self):
        await self.ctx.send("Setup timed out.", ephemeral=True)

class TagButton(discord.ui.Button):
    def __init__(self, tag):
        super().__init__(label=tag, style=discord.ButtonStyle.secondary)
        self.tag = tag

    async def callback(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)
        config[guild_id] = {
            "channel": interaction.channel.id,
            "tags": config.get(guild_id, {}).get("tags", [])
        }

        if self.tag not in config[guild_id]["tags"]:
            config[guild_id]["tags"].append(self.tag)
        else:
            config[guild_id]["tags"].remove(self.tag)

        save_config(config)
        await interaction.response.send_message(f"Updated tag: `{self.tag}`", ephemeral=True)

@tasks.loop(minutes=1)
async def post_images():
    config = load_config()
    for guild_id, data in config.items():
        channel = bot.get_channel(data["channel"])
        if not channel:
            continue
        for tag in data["tags"]:
            images = await fetch_images(tag)
            if images:
                embeds = [discord.Embed().set_image(url=url) for url in images[:5]]
                for embed in embeds:
                    await channel.send(embed=embed)
                await asyncio.sleep(2)

async def fetch_images(tag):
    urls = await fetch_google(tag)
    if urls:
        return urls
    urls = await fetch_reddit(tag)
    return urls or []

async def fetch_google(tag):
    search_url = (
        "https://www.googleapis.com/customsearch/v1"
        f"?q={tag}+pfp"
        f"&searchType=image"
        f"&cx={GOOGLE_CSE_ID}"
        f"&key={GOOGLE_API_KEY}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return [item["link"] for item in data.get("items", [])]

async def fetch_reddit(tag):
    headers = {"User-Agent": "PFPBot/1.0"}
    url = f"https://www.reddit.com/r/{tag}/hot.json?limit=10"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return [p["data"]["url"] for p in data["data"]["children"]
                    if any(p["data"]["url"].endswith(ext) for ext in [".jpg", ".png", ".jpeg"])]

keep_alive()
bot.run(TOKEN)
