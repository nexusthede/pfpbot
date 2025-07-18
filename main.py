import os
import re
import random
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import aiohttp
from bs4 import BeautifulSoup

TOKEN = os.getenv("TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
PORT = int(os.getenv("PORT", 8080))

app = Flask("")

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0 Safari/537.36"
}

# Tags for selection
TAGS = [
    "anime", "egirl", "eboy", "faceless", "cute", "goth", "emo",
    "pixel", "vaporwave", "fantasy", "cyber", "matching", "banners",
    "kpop", "drip", "body", "city", "aesthetic", "plushies", "soft", "random"
]

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

class TagSelect(Select):
    def __init__(self, pfp_cog, channel_id):
        options = [discord.SelectOption(label=tag, description=f"Add tag: {tag}") for tag in TAGS]
        super().__init__(placeholder="Select tags to add...", min_values=1, max_values=len(options), options=options)
        self.pfp_cog = pfp_cog
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        selected = self.values
        added = []
        for tag in selected:
            if tag not in self.pfp_cog.active_channels.get(self.channel_id, []):
                self.pfp_cog.active_channels.setdefault(self.channel_id, []).append(tag)
                added.append(tag)
        await interaction.response.send_message(
            f"✅ Added tags {', '.join(added)} for this channel. Bot will post images for all tags.", ephemeral=True
        )

class ClearButton(Button):
    def __init__(self, pfp_cog, channel_id):
        super().__init__(label="Clear Tags", style=discord.ButtonStyle.danger)
        self.pfp_cog = pfp_cog
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        if self.channel_id in self.pfp_cog.active_channels:
            self.pfp_cog.active_channels.pop(self.channel_id)
            await interaction.response.send_message("🛑 Cleared all tags for this channel.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No active tags to clear.", ephemeral=True)

class ShowTagsButton(Button):
    def __init__(self, pfp_cog, channel_id):
        super().__init__(label="Show Tags", style=discord.ButtonStyle.secondary)
        self.pfp_cog = pfp_cog
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        tags = self.pfp_cog.active_channels.get(self.channel_id, [])
        if tags:
            await interaction.response.send_message(f"🔖 Active tags for this channel: {', '.join(tags)}", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No active tags for this channel.", ephemeral=True)

class TagView(View):
    def __init__(self, pfp_cog, channel_id):
        super().__init__(timeout=None)
        self.add_item(TagSelect(pfp_cog, channel_id))
        self.add_item(ClearButton(pfp_cog, channel_id))
        self.add_item(ShowTagsButton(pfp_cog, channel_id))

class PfpBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Dict: channel_id -> list of tags
        self.active_channels = {}
        self.posting_loop.start()

    @commands.command(name="setuptags")
    async def setuptags(self, ctx):
        """Posts the tag selection UI in the channel"""
        view = TagView(self, ctx.channel.id)
        await ctx.send("Select tags to start posting PFP images:", view=view)

    @tasks.loop(minutes=1)
    async def posting_loop(self):
        for channel_id, tags in list(self.active_channels.items()):
            channel = self.bot.get_channel(channel_id)
            if not channel:
                self.active_channels.pop(channel_id)
                continue
            for tag in tags:
                images = []
                # Alternate sources for variety
                source = random.choice(["google", "pinterest"])
                if source == "google":
                    images = await google_search_images(tag, num=3)
                else:
                    images = await pinterest_scrape_images(tag, num=3)
                for img_url in images:
                    embed = discord.Embed()
                    embed.set_image(url=img_url)
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass

    @posting_loop.before_loop
    async def before_posting(self):
        await self.bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    # Sync commands if any slash commands added later
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Command sync failed: {e}")

    # Set custom status: Playing with Nexus
    await bot.change_presence(activity=discord.Game(name="Playing with Nexus"))

def run_bot():
    bot.add_cog(PfpBot(bot))
    bot.run(TOKEN)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()  # Run Flask keep-alive server in background
    run_bot()
