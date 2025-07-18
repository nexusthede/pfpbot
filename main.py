import os
import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from keep_alive import keep_alive
import random
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

# Keep the bot alive on Render
keep_alive()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="PFPs for Nexus ❤️"))
    autopost.start()
    print(f"✅ Logged in as {bot.user}")

# Channel ID to list of selected tags
channel_tags = {}

# All available tags (NSFW all grouped as "body")
all_tags = [
    "anime", "egirl", "eboy", "faceless", "cute", "goth", "emo", "pixel", "vaporwave", "fantasy",
    "cyber", "matching", "banners", "kpop", "drip", "city", "aesthetic", "plushies", "soft",
    "body", "gif", "sets", "random"
]

# Fetch images from Google Custom Search API
def fetch_google_images(query, amount=5):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "searchType": "image",
        "num": amount,
        "safe": "off"  # "off" to allow NSFW for 'body' tag, be careful!
    }
    res = requests.get(url, params=params)
    if res.status_code == 200:
        return [item["link"] for item in res.json().get("items", [])]
    return []

# Auto-post images every 60 seconds per channel
@tasks.loop(seconds=60)
async def autopost():
    for channel_id, tags in channel_tags.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        # Pick random tag if "random" selected; else use first tag
        tag = random.choice(tags) if "random" in tags else tags[0]
        images = fetch_google_images(tag)
        for img_url in images:
            await channel.send(img_url)

# /start command to select tags with buttons
@bot.command()
async def start(ctx):
    class TagSelector(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.selected = set()
            for tag in all_tags:
                button = Button(label=tag, style=discord.ButtonStyle.secondary, custom_id=tag)
                button.callback = self.toggle
                self.add_item(button)
            done_btn = Button(label="✅ Done", style=discord.ButtonStyle.success)
            done_btn.callback = self.finish
            self.add_item(done_btn)

        async def toggle(self, interaction: discord.Interaction):
            tag = interaction.data["custom_id"]
            if tag in self.selected:
                self.selected.remove(tag)
            else:
                self.selected.add(tag)
            await interaction.response.defer()

        async def finish(self, interaction: discord.Interaction):
            if not self.selected:
                await interaction.response.send_message("❌ Select at least one tag before finishing.", ephemeral=True)
                return
            channel_tags[interaction.channel.id] = list(self.selected)
            await interaction.response.send_message(f"✅ Auto-post started with tags: {', '.join(self.selected)}", ephemeral=True)
            self.stop()

    await ctx.send("🎯 Select your PFP tags for this channel:", view=TagSelector())

# /stop command to disable autoposting in channel
@bot.command()
async def stop(ctx):
    if ctx.channel.id in channel_tags:
        del channel_tags[ctx.channel.id]
        await ctx.send("🛑 Auto-posting stopped in this channel.")
    else:
        await ctx.send("⚠️ This channel wasn’t set up for auto-posting.")

bot.run(TOKEN)
