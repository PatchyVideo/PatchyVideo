
import os

from aiohttp import web
from .init import routes, init_funcs

from scraper.video import dispatch

from utils.jsontools import *
from utils.logger import log
from utils.interceptors import asyncJsonRequest
from utils.crypto import random_bytes_str
from bson.json_util import dumps

from config import UploadConfig

import PIL
from PIL import Image, ImageSequence
import io

from init import rdb

_COVER_PATH = os.getenv('IMAGE_PATH', "/images") + "/covers/"
_USERPHOTO_PATH = os.getenv('IMAGE_PATH', "/images") + "/userphotos/"

def _gif_thumbnails(frames, resolution = (320, 200)):
	for frame in frames:
		thumbnail = frame.copy()
		thumbnail.thumbnail(resolution, Image.ANTIALIAS)
		yield thumbnail

@routes.post("/upload_image.do")
async def upload_image(request):
	data = await request.post()
	try :
		file_field = data['file']
		type_field = data['type']
		if type_field == 'cover' :
			resolution = (320, 200)
			dst = _COVER_PATH
		elif type_field == 'userphoto' :
			resolution = (256, 256)
			dst = _USERPHOTO_PATH
		else :
			return web.json_response(makeResponseFailed('INCORRECT_UPLOAD_TYPE'), dumps = dumps)
		content = file_field.file.read()
	except :
		return web.json_response(makeResponseFailed('INCORRECT_REQUEST'), dumps = dumps)
	if len(content) > UploadConfig.MAX_UPLOAD_SIZE :
		return web.json_response(makeResponseFailed('FILE_TOO_LARGE'), dumps = dumps)
	try :
		img = Image.open(io.BytesIO(content))
		if img is None :
			raise Exception()
	except :
		return web.json_response(makeResponseFailed('UNRECOGNIZED_IMAGE_FILE'), dumps = dumps)
	if isinstance(img, PIL.GifImagePlugin.GifImageFile) :
		filename = random_bytes_str(24) + ".gif"
		frames = ImageSequence.Iterator(img)
		frames = _gif_thumbnails(frames, resolution)
		om = next(frames) # Handle first frame separately
		om.info = img.info # Copy sequence info
		om.save(dst + filename, save_all = True, append_images = list(frames), loop = 0)
	else :
		filename = random_bytes_str(24) + ".png"
		img.thumbnail(resolution, Image.ANTIALIAS)
		img.save(dst + filename)
	file_key = "upload-image-" + random_bytes_str(16)
	rdb.set(file_key, filename)
	log('fe_upload_image', obj = {'filename': filename, 'file_key': file_key, 'size': len(content)})
	return web.json_response(makeResponseSuccess({'file_key': file_key}), dumps = dumps)
