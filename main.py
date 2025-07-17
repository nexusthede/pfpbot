import os
import sys

# PATCH: Fix audioop crash
try:
    import audioop
except ModuleNotFoundError:
    sys.modules['audioop'] = None

import json, discord, asyncio, random, aiohttp
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()
TOKEN = os.getenv("TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def pfp(ctx, *, query=None):
    if not query:
        return await ctx.send("Please provide a search query.")
    
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "searchType": "image",
        "num": 5,
        "safe": "off"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, params=params) as resp:
            data = await resp.json()
            items = data.get("items")
            if not items:
                return await ctx.send("No results found.")
            for item in items:
                await ctx.send(item["link"])

keep_alive()
bot.run(TOKEN)
