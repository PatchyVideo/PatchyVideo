

from aiohttp import web
from aiohttp import ClientSession

app = web.Application()
routes = web.RouteTableDef()

init_funcs = []
