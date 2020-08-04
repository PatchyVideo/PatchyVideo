
import socket
import re
import os
import sys
import json
from urllib import request, parse, error

cookies = None
insecure = False
default_encoding = 'utf-8'
force = True

fake_headers = {
	'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',  # noqa
	'Accept-Charset': 'UTF-8,*;q=0.5',
	'Accept-Encoding': 'gzip,deflate,sdch',
	'Accept-Language': 'en-US,en;q=0.8',
	'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:64.0) Gecko/20100101 Firefox/64.0',  # noqa
}

def ungzip(data):
	"""Decompresses data for Content-Encoding: gzip.
	"""
	from io import BytesIO
	import gzip
	buffer = BytesIO(data)
	f = gzip.GzipFile(fileobj=buffer)
	return f.read()

def undeflate(data):
	"""Decompresses data for Content-Encoding: deflate.
	(the zlib compression is used.)
	"""
	import zlib
	decompressobj = zlib.decompressobj(-zlib.MAX_WBITS)
	return decompressobj.decompress(data)+decompressobj.flush()

def match1(text, *patterns):
	"""Scans through a string for substrings matched some patterns (first-subgroups only).
	Args:
		text: A string to be scanned.
		patterns: Arbitrary number of regex patterns.
	Returns:
		When only one pattern is given, returns a string (None if no match found).
		When more than one pattern are given, returns a list of strings ([] if no match found).
	"""

	if len(patterns) == 1:
		pattern = patterns[0]
		match = re.search(pattern, text)
		if match:
			return match.group(1)
		else:
			return None
	else:
		ret = []
		for pattern in patterns:
			match = re.search(pattern, text)
			if match:
				ret.append(match.group(1))
		return ret

def urlopen_with_retry(*args, **kwargs):
	retry_time = 3
	for i in range(retry_time):
		try:
			return request.urlopen(*args, **kwargs)
		except socket.timeout as e:
			if i + 1 == retry_time:
				raise e
		# try to tackle youku CDN fails
		except error.HTTPError as http_error:
			if i + 1 == retry_time:
				raise http_error

def post_content(url, headers={}, post_data={}, decoded=True, **kwargs):
	"""Post the content of a URL via sending a HTTP POST request.
	Args:
		url: A URL.
		headers: Request headers used by the client.
		decoded: Whether decode the response body using UTF-8 or the charset specified in Content-Type.
	Returns:
		The content as a string.
	"""

	req = request.Request(url, headers=headers)
	if cookies:
		cookies.add_cookie_header(req)
		req.headers.update(req.unredirected_hdrs)
	if kwargs.get('post_data_raw'):
		post_data_enc = bytes(kwargs['post_data_raw'], 'utf-8')
	else:
		post_data_enc = bytes(parse.urlencode(post_data), 'utf-8')
	response = urlopen_with_retry(req, data=post_data_enc)
	data = response.read()

	# Handle HTTP compression for gzip and deflate (zlib)
	content_encoding = response.getheader('Content-Encoding')
	if content_encoding == 'gzip':
		data = ungzip(data)
	elif content_encoding == 'deflate':
		data = undeflate(data)

	# Decode the response body
	if decoded:
		charset = match1(
			response.getheader('Content-Type'), r'charset=([\w-]+)'
		)
		if charset is not None:
			data = data.decode(charset)
		else:
			data = data.decode('utf-8')

	return data

def get_content(url, headers={}, decoded=True):
	"""Gets the content of a URL via sending a HTTP GET request.
	Args:
		url: A URL.
		headers: Request headers used by the client.
		decoded: Whether decode the response body using UTF-8 or the charset specified in Content-Type.
	Returns:
		The content as a string.
	"""

	req = request.Request(url, headers=headers)
	if cookies:
		cookies.add_cookie_header(req)
		req.headers.update(req.unredirected_hdrs)

	response = urlopen_with_retry(req)
	data = response.read()

	# Handle HTTP compression for gzip and deflate (zlib)
	content_encoding = response.getheader('Content-Encoding')
	if content_encoding == 'gzip':
		data = ungzip(data)
	elif content_encoding == 'deflate':
		data = undeflate(data)

	# Decode the response body
	if decoded:
		charset = match1(
			response.getheader('Content-Type', ''), r'charset=([\w-]+)'
		)
		if charset is not None:
			data = data.decode(charset, 'ignore')
		else:
			data = data.decode('utf-8', 'ignore')

	return data

def r1(pattern, text):
	m = re.search(pattern, text)
	if m:
		return m.group(1)

def url_size(url, faker=False, headers={}):
	if faker:
		response = urlopen_with_retry(
			request.Request(url, headers=fake_headers)
		)
	elif headers:
		response = urlopen_with_retry(request.Request(url, headers=headers))
	else:
		response = urlopen_with_retry(url)

	size = response.headers['content-length']
	return int(size) if size is not None else float('inf')

def urls_size(urls, faker=False, headers={}):
	return sum([url_size(url, faker=faker, headers=headers) for url in urls])

def tr(s):
	if default_encoding == 'utf-8':
		return s
	else:
		return s
		# return str(s.encode('utf-8'))[2:-1]


def url_save(
	url, filepath, refer=None, is_part=False, faker=False,
	headers=None, timeout=None, **kwargs
):
	tmp_headers = headers.copy() if headers is not None else {}
	# When a referer specified with param refer,
	# the key must be 'Referer' for the hack here
	if refer is not None:
		tmp_headers['Referer'] = refer
	if type(url) is list:
		file_size = urls_size(url, faker=faker, headers=tmp_headers)
		is_chunked, urls = True, url
	else:
		file_size = url_size(url, faker=faker, headers=tmp_headers)
		is_chunked, urls = False, [url]

	continue_renameing = True
	while continue_renameing:
		continue_renameing = False
		if os.path.exists(filepath):
			if not force and (file_size == os.path.getsize(filepath) or True):
				return
		elif not os.path.exists(os.path.dirname(filepath)):
			os.mkdir(os.path.dirname(filepath))

	temp_filepath = filepath + '.download' if file_size != float('inf') \
		else filepath
	received = 0
	if not force:
		open_mode = 'ab'

		if os.path.exists(temp_filepath):
			received += os.path.getsize(temp_filepath)
	else:
		open_mode = 'wb'

	for url in urls:
		received_chunk = 0
		if received < file_size:
			if faker:
				tmp_headers = fake_headers
			'''
			if parameter headers passed in, we have it copied as tmp_header
			elif headers:
				headers = headers
			else:
				headers = {}
			'''
			if received and not is_chunked:  # only request a range when not chunked
				tmp_headers['Range'] = 'bytes=' + str(received) + '-'
			if refer:
				tmp_headers['Referer'] = refer

			if timeout:
				response = urlopen_with_retry(
					request.Request(url, headers=tmp_headers), timeout=timeout
				)
			else:
				response = urlopen_with_retry(
					request.Request(url, headers=tmp_headers)
				)
			try:
				range_start = int(
					response.headers[
						'content-range'
					][6:].split('/')[0].split('-')[0]
				)
				end_length = int(
					response.headers['content-range'][6:].split('/')[1]
				)
				range_length = end_length - range_start
			except:
				content_length = response.headers['content-length']
				range_length = int(content_length) if content_length is not None \
					else float('inf')

			if is_chunked:  # always append if chunked
				open_mode = 'ab'
			elif file_size != received + range_length:  # is it ever necessary?
				received = 0
				open_mode = 'wb'

			with open(temp_filepath, open_mode) as output:
				while True:
					buffer = None
					try:
						buffer = response.read(1024 * 256)
					except socket.timeout:
						pass
					if not buffer:
						if is_chunked and received_chunk == range_length:
							break
						elif not is_chunked and received == file_size:  # Download finished
							break
						# Unexpected termination. Retry request
						if not is_chunked:  # when
							tmp_headers['Range'] = 'bytes=' + str(received) + '-'
						response = urlopen_with_retry(
							request.Request(url, headers=tmp_headers)
						)
						continue
					output.write(buffer)
					received += len(buffer)
					received_chunk += len(buffer)

	assert received == os.path.getsize(temp_filepath), '%s == %s == %s' % (
		received, os.path.getsize(temp_filepath), temp_filepath
	)

	if os.access(filepath, os.W_OK):
		# on Windows rename could fail if destination filepath exists
		os.remove(filepath)
	os.rename(temp_filepath, filepath)

def random_bytes(length) :
	bytes = os.urandom(length)
	return bytes

import binascii
import tempfile

def random_bytes_str(length) :
	return binascii.hexlify(bytearray(random_bytes(length))).decode()

def get_temp_file_name() :
	return next(tempfile._get_candidate_names())

def download_urls(
	urls, title, ext, total_size, output_dir='.', refer=None, merge=True,
	faker=False, headers={}, **kwargs
):
	assert urls

	if not total_size:
		try:
			total_size = urls_size(urls, faker=faker, headers=headers)
		except:
			import traceback
			traceback.print_exc(file=sys.stdout)
			pass

	output_filename = get_temp_file_name()
	output_filepath = os.path.join(output_dir, output_filename)

	if len(urls) == 1:
		url = urls[0]
		#print('Downloading %s ...' % tr(output_filename))

		url_save(
			url, output_filepath, refer=refer, faker=faker,
			headers=headers, **kwargs
		)

	return output_filename

def download_twitter(url, output_dir='.', merge=True, info_only=False, **kwargs) :
	if re.match(r'https?://mobile', url): # normalize mobile URL
		url = 'https://' + match1(url, r'//mobile\.(.+)')

	html = get_content(url) # disable faker to prevent 302 infinite redirect
	screen_name = r1(r'twitter\.com/([^/]+)', url) or r1(r'data-screen-name="([^"]*)"', html) or \
		r1(r'<meta name="twitter:title" content="([^"]*)"', html)
	item_id = r1(r'twitter\.com/[^/]+/status/(\d+)', url) or r1(r'data-item-id="([^"]*)"', html) or \
		r1(r'<meta name="twitter:site:id" content="([^"]*)"', html)
	page_title = "{} [{}]".format(screen_name, item_id)


	authorization = 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'

	ga_url = 'https://api.twitter.com/1.1/guest/activate.json'
	ga_content = post_content(ga_url, headers={'authorization': authorization})
	guest_token = json.loads(ga_content)['guest_token']

	api_url = 'https://api.twitter.com/2/timeline/conversation/%s.json?tweet_mode=extended' % item_id
	api_content = get_content(api_url, headers={'authorization': authorization, 'x-guest-token': guest_token})

	info = json.loads(api_content)
	desc = info['globalObjects']['tweets'][item_id]['full_text']
	variants = info['globalObjects']['tweets'][item_id]['extended_entities']['media'][0]['video_info']['variants']
	variants = sorted(variants, key=lambda kv: kv.get('bitrate', 0))
	urls = [ variants[-1]['url'] ]
	#print(urls)
	size = urls_size(urls)
	mime, ext = variants[-1]['content_type'], 'mp4'

	#print_info(site_info, page_title, mime, size)
	if not info_only:
		return screen_name, item_id, desc#, download_urls(urls, page_title, ext, size, output_dir, merge=merge)


