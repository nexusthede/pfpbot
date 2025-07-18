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

# Keep alive for Render 24/7
keep_alive()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="PFPs with Nexus"))
    autopost.start()
    print(f"✅ Logged in as {bot.user}")

# Channel ID -> List of tags
channel_tags = {}

# All tag options
all_tags = [
    "anime", "egirl", "eboy", "faceless", "cute", "goth", "emo", "pixel", "vaporwave", "fantasy",
    "cyber", "matching", "banners", "kpop", "drip", "city", "aesthetic", "plushies", "soft",
    "body", "thighs", "mirror", "boobs", "ass", "arch", "panties", "gif", "sets", "random"
]

# Fetch PFPs from Google Images using Custom Search API
def fetch_google_images(query, amount=5):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "searchType": "image",
        "num": amount,
        "safe": "off"
    }
    res = requests.get(url, params=params)
    if res.status_code == 200:
        return [item["link"] for item in res.json().get("items", [])]
    return []

# Auto-post every 60 seconds per configured channel
@tasks.loop(seconds=60)
async def autopost():
    for channel_id, tags in channel_tags.items():
        channel = bot.get_channel(channel_id)
        if channel:
            selected_tag = random.choice(tags) if "random" in tags else tags[0]
            images = fetch_google_images(selected_tag)
            for url in images:
                await channel.send(url)

# Slash-style command using /start (via prefix for now)
@bot.command()
async def start(ctx):
    class TagSelector(View):
        def __init__(self):
            super().__init__(timeout=None)
            self.selected = set()
            rows = [[], [], [], []]
            for i, tag in enumerate(all_tags):
                button = Button(label=tag, style=discord.ButtonStyle.secondary, custom_id=tag, row=i // 8)
                button.callback = self.toggle
                self.add_item(button)

            done_btn = Button(label="✅ Done", style=discord.ButtonStyle.success, row=3)
            done_btn.callback = self.finish
            self.add_item(done_btn)

        async def toggle(self, interaction):
            tag = interaction.data["custom_id"]
            if tag in self.selected:
                self.selected.remove(tag)
            else:
                self.selected.add(tag)
            await interaction.response.defer()

        async def finish(self, interaction):
            if not self.selected:
                await interaction.response.send_message("❌ You need to select at least one tag.", ephemeral=True)
                return
            channel_tags[interaction.channel.id] = list(self.selected)
            await interaction.response.send_message(f"✅ Started auto-posting in this channel for: {', '.join(self.selected)}", ephemeral=True)
            self.stop()

    await ctx.send("🎯 Select PFP tags for this channel:", view=TagSelector())

# Command to stop autopost in current channel
@bot.command()
async def stop(ctx):
    if ctx.channel.id in channel_tags:
        del channel_tags[ctx.channel.id]
        await ctx.send("🛑 Auto-posting disabled in this channel.")
    else:
        await ctx.send("⚠️ This channel wasn't set up for auto-posting.")

bot.run(TOKEN)
