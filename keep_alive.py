# keep_alive.py

from aiohttp import web
import os
import asyncio

async def handle(request):
    return web.Response(text="Bot is alive!")

async def run():
    app = web.Application()
    app.add_routes([web.get('/', handle)])

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    # Keep running forever
    while True:
        await asyncio.sleep(3600)

# To run this keep alive server, use:
# import keep_alive
# asyncio.create_task(keep_alive.run())
