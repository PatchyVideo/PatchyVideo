
from init import app
from utils.interceptors import loginOptional

@app.route('/ipfs', methods = ['GET'])
@loginOptional
def pages_ipfs(rd, user):
	return "render", "IPFS/fantasy.html"

@app.route('/ipfs/IPFS_player.html', methods = ['GET'])
@loginOptional
def pages_ipfs_(rd, user):
	return "render", "IPFS/IPFS_player.html"
