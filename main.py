import os
import re
import random
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup

TOKEN = os.getenv("TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0 Safari/537.36"
}

async def google_search_images(query, num=5):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "searchType": "image",
        "q": query,
        "num": num,
        "safe": "high"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return [item["link"] for item in data.get("items", [])]

async def pinterest_scrape_images(query, num=5):
    search_url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
    images = []

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(search_url) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
            soup = BeautifulSoup(text, 'html.parser')
            img_tags = soup.find_all('img', src=True)
            for img in img_tags:
                src = img['src']
                if re.search(r'https://i.pinimg.com/', src):
                    images.append(src)
                if len(images) >= num:
                    break
    return images

class PfpBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}

    @app_commands.command(name="startposting", description="Start posting images here from Google or Pinterest.")
    @app_commands.describe(
        source="Image source: google or pinterest",
        query="Search term or tags (like 'egirl', 'anime', etc.)"
    )
    async def startposting(self, interaction: discord.Interaction, source: str, query: str):
        source = source.lower()
        if source not in ["google", "pinterest"]:
            await interaction.response.send_message("❌ Source must be 'google' or 'pinterest'.", ephemeral=True)
            return
        channel_id = interaction.channel.id
        self.active_channels[channel_id] = {"source": source, "query": query}
        await interaction.response.send_message(
            f"✅ Started posting `{query}` images from {source} here every minute.", ephemeral=True)

    @app_commands.command(name="stopposting", description="Stop posting images in this channel.")
    async def stopposting(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id
        if channel_id in self.active_channels:
            self.active_channels.pop(channel_id)
            await interaction.response.send_message("🛑 Stopped posting images here.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No active posting in this channel.", ephemeral=True)

    async def posting_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            for channel_id, settings in list(self.active_channels.items()):
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    self.active_channels.pop(channel_id)
                    continue
                images = []
                if settings["source"] == "google":
                    images = await google_search_images(settings["query"], num=5)
                elif settings["source"] == "pinterest":
                    images = await pinterest_scrape_images(settings["query"], num=5)

                for img_url in images:
                    embed = discord.Embed()
                    embed.set_image(url=img_url)
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass
            await asyncio.sleep(60)  # wait 1 minute

async def setup(bot):
    pfp_bot = PfpBot(bot)
    bot.loop.create_task(pfp_bot.posting_loop())
    await bot.add_cog(pfp_bot)

# Setup discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Command sync failed: {e}")

# Keep-alive web server for Render
async def handle(request):
    return web.Response(text="Bot is alive!")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def run_webserver():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv("PORT", 8080)))
    await site.start()

async def main():
    await setup(bot)
    await run_webserver()
    await bot.start(TOKEN)

import asyncio
asyncio.run(main())
