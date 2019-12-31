import os
import sys
import time
import asyncio
import traceback
import PIL
import copy

from aiohttp import web
from aiohttp import ClientSession

from frontend_helpers import main
from frontend_helpers.init import app, routes, init_funcs

app.add_routes(routes)

async def start_async_app():
	# run init functions
	for f in init_funcs :
		await f()

	# schedule web server to run
	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, '0.0.0.0', 5004)
	await site.start()
	print("Serving up app on 0.0.0.0:5004")
	return runner, site

loop = asyncio.get_event_loop()
runner, site = loop.run_until_complete(start_async_app())

try:
	loop.run_forever()
except KeyboardInterrupt as err:
	loop.run_until_complete(runner.cleanup())

