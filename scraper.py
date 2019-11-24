
import asyncio
from aiohttp import web
from aiohttp import ClientSession

from init import rdb

from utils.jsontools import *
from utils.rwlock_async import modifyingResourceAsync, usingResourceAsync
from utils.lock_async import RedisLockAsync

routes = web.RouteTableDef()

@routes.post("/")
@usingResourceAsync('test')
async def post_video_async(request):
	print(await request.json())
	async with RedisLockAsync(rdb, 'test_lock') :
		xxx = {'id':'xxxx-xxxxxx-xxxxx-xxxxx'}
		return web.json_response(makeResponseSuccess(xxx))

app = web.Application()
app.add_routes(routes)

async def start_async_app():
	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, '0.0.0.0', 5003)
	await site.start()
	print("Serving up app on 0.0.0.0:5003")
	return runner, site

loop = asyncio.get_event_loop()
runner, site = loop.run_until_complete(start_async_app())
try:
	loop.run_forever()
except KeyboardInterrupt as err:
	loop.run_until_complete(runner.cleanup())

