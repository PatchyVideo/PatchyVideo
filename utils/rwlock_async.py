from __future__ import print_function


"""
Copied from redisrwlock
"""

import redis

import asyncio
import logging
import logging.config
import os
import re
import time

logger = logging.getLogger(__name__)

# (1) Primary data structure for resource, owner, lock
#
# name  = resource name
# mode  = R|W
# owner = node/pid
# time  = sec.usec (from redis time command)
#
# SET:    rsrc -> set of lock grants
# STR:    lock -> ref-count:time      (time added for victim selection)
# SET:   owner -> set of rsrc access  (this set is for victim selection)
#
# rsrc_key   = rsrc:{name}
# lock_key   = lock:{name}:{mode}:{owner}
# owner_key  = owner:{owner}
#
# grant      = {mode}:{owner}
# access     = {mode}:{name}
#
# (2) Addtional data structure for deadlock detect wait-for graph
#
# SET:  waitor -> set of waitee
#
# waitor_key = wait:{owner}
# waitee     = {owner}

# atomic:
# - checking if any conflicting locks granted
# - adding lock if no confliction
_LOCK_SCRIPT = """\
local rsrc_key = KEYS[1]
local lock_key = KEYS[2]
local owner_key = KEYS[3]
local name = string.match(lock_key, 'lock:(.+):[RW]:.+')
local mode = string.match(lock_key, 'lock:.+:([RW]):.+')
local owner = string.match(lock_key, 'lock:.+:[RW]:(.+)')
local grants = redis.call('smembers', rsrc_key)
for i, grant in ipairs(grants) do
	local grant_mode = string.match(grant, '([RW]):.+')
	local grant_owner = string.match(grant, '[RW]:(.+)')
	if grant_owner ~= owner then
		if not (grant_mode == 'R' and mode == 'R') then
			return 'false'
		end
	end
end
-- add as grant and acccess, set lock k=v
redis.call('sadd', rsrc_key, mode..':'..owner)
redis.call('sadd', owner_key, mode..':'..name)
local rcnt = '1'
local time = ARGV[1]
local retval = redis.call('get', lock_key)
if retval ~= false then
	rcnt = tonumber(string.match(retval, '(.+):.+')) + 1
	time = string.match(retval, '.+:(.+)')
	redis.call('set', lock_key, '1:'..time)
end
redis.call('set', lock_key, rcnt..':'..time)
return 'true'
"""

# atomic:
# - decrease reference count
# - delete lock if no reference
_UNLOCK_SCRIPT = """\
local rsrc_key = KEYS[1]
local lock_key = KEYS[2]
local owner_key = KEYS[3]
local name = string.match(lock_key, 'lock:(.+):[RW]:.+')
local mode = string.match(lock_key, 'lock:.+:([RW]):.+')
local owner = string.match(lock_key, 'lock:.+:[RW]:(.+)')
local retval = redis.call('get', lock_key)
if retval == false then
	return 'false'
else
	local rcnt = tonumber(string.match(retval, '(.+):.+'))
	local time = string.match(retval, '.+:(.+)')
	if rcnt == 1 then
		redis.call('del', lock_key)
		redis.call('srem', rsrc_key, mode..':'..owner)
		redis.call('srem', owner_key, mode..':'..name)
	else
		rcnt = rcnt - 1
		redis.call('set', lock_key, rcnt..':'..time)
	end
end
return 'true'
"""


# Looks dirty, but OK
# Compare two time strings given in format of 'sec.usec'
def _cmp_time(left, right):
	# Compare seconds part numerically (30 > 4)
	left_sec = int(re.match(r'(.+)\..+', left).group(1))
	right_sec = int(re.match(r'(.+)\..+', right).group(1))
	if left_sec < right_sec:
		return -1
	elif left_sec == right_sec:
		# Comapre sub-seconds part also numerically
		# When input is '0.30' and '0.4' means
		# not 0.30s and 0.4s, but 30us 4us
		left_usec = int(re.match(r'.+\.(.+)', left).group(1))
		right_usec = int(re.match(r'.+\.(.+)', right).group(1))
		if left_usec < right_usec:
			return -1
		elif left_usec == right_usec:
			return 0
		else:
			return 1
	else:
		return 1


# lock result used as token
class Rwlock:
	"""
	Constants for Rwlock

	lock modes: READ, WRITE

	special timeout: FOREVER

	status: OK, FAIL, TIMEOUT, DEADLOCK,
	and None if not returned from lock method
	"""

	# lock modes
	READ = 'R'
	WRITE = 'W'

	# timeout
	FOREVER = -1

	# status
	OK = 0
	FAIL = 1
	TIMEOUT = 2
	DEADLOCK = 3

	def __init__(self, name, mode, node, pid):
		self.name = name
		self.mode = mode
		self.node = node
		self.pid = pid
		self.status = None

	def rsrc_key(self):
		return 'rsrc:' + self.name

	def lock_key(self):
		return self.__str__()

	def __str__(self):
		return 'lock:' + self.name + ':' + self.mode + ':' + \
			self.node + '/' + self.pid


class RwlockClient:

	def __init__(self,
				 redis=redis.StrictRedis(),
				 node='localhost', pid=str(os.getpid())):
		self.redis = redis
		self.node = node
		self.pid = pid
		self.redis.client_setname('redisrwlock:' + self.node + '/' + self.pid)

	def get_owner(self):
		return self.node + '/' + self.pid

	def owner_key(self):
		return 'owner:' + self.get_owner()

	def redis_time(self):
		sec, usec = self.redis.time()
		return str(sec) + '.' + str(usec)

	# Avoid use of 'KEYS'
	# return scan_iter with specified matching pattern and count=128
	# I just assume key length 32 bytes and 4K bytes unit i/o
	def _redis_scan_iter(self, pattern):
		return self.redis.scan_iter(match=pattern, count=128)

	def lock(self, name, mode, timeout=0, retry_interval=0.1):
		"""Locks on a named resource with mode in timeout.

		Specify timeout 0 (default) for no-wait, no-retry and
		timeout FOREVER waits until lock success or deadlock.

		When requested lock is not available, this method sleep
		given retry_interval seconds and retry until lock success,
		deadlock or timeout.

		returns rwlock, check status field to know lock obtained or failed
		"""
		t1 = t2 = time.monotonic()
		redis_time = self.redis_time()
		rwlock = Rwlock(name, mode, self.node, self.pid)
		while timeout == Rwlock.FOREVER or t2 - t1 <= timeout:
			retval = self.redis.eval(
				_LOCK_SCRIPT, 3,
				rwlock.rsrc_key(), rwlock.lock_key(), self.owner_key(),
				redis_time)
			lock_ok = True if retval == b'true' else False
			if lock_ok:
				rwlock.status = Rwlock.OK
				break
			elif timeout == 0:
				rwlock.status = Rwlock.FAIL
				break
			elif self._deadlock(name, mode):
				rwlock.status = Rwlock.DEADLOCK
				break
			time.sleep(retry_interval)
			t2 = time.monotonic()
		else:
			rwlock.status = Rwlock.TIMEOUT
		self.redis.delete('wait:' + self.get_owner())
		return rwlock

	async def lock_async(self, name, mode, timeout=0, retry_interval=0.1):
		"""Locks on a named resource with mode in timeout.

		Specify timeout 0 (default) for no-wait, no-retry and
		timeout FOREVER waits until lock success or deadlock.

		When requested lock is not available, this method sleep
		given retry_interval seconds and retry until lock success,
		deadlock or timeout.

		returns rwlock, check status field to know lock obtained or failed
		"""
		t1 = t2 = time.monotonic()
		redis_time = self.redis_time()
		rwlock = Rwlock(name, mode, self.node, self.pid)
		while timeout == Rwlock.FOREVER or t2 - t1 <= timeout:
			retval = self.redis.eval(
				_LOCK_SCRIPT, 3,
				rwlock.rsrc_key(), rwlock.lock_key(), self.owner_key(),
				redis_time)
			lock_ok = True if retval == b'true' else False
			if lock_ok:
				rwlock.status = Rwlock.OK
				break
			elif timeout == 0:
				rwlock.status = Rwlock.FAIL
				break
			elif self._deadlock(name, mode):
				rwlock.status = Rwlock.DEADLOCK
				break
			await asyncio.sleep(retry_interval)
			t2 = time.monotonic()
		else:
			rwlock.status = Rwlock.TIMEOUT
		self.redis.delete('wait:' + self.get_owner())
		return rwlock

	def unlock(self, rwlock):
		"""Unlocks rwlock previously acquired with lock method

		returns true for successfull unlock
		false if there is no such lock to unlock
		"""
		retval = self.redis.eval(
			_UNLOCK_SCRIPT, 3,
			rwlock.rsrc_key(), rwlock.lock_key(), self.owner_key())
		return retval == b'true'

	def gc(self):
		"""Removes stale locks, waits, and owner itself created by
		crashed/exit clients without unlocking or proper cleanup.

		Used by garbage collecting daemon or monitor
		"""
		# We get owners and waitors before active client list
		# Otherwise, we may mistakenly remove some lock, owner, or wait
		# made by last clients not included in the client list
		#
		# And we avoid scan of lock list
		# by exploiting owner -> { set of access }
		#
		# (1) find out stale owners and waitors
		# (2) delete locks and grants of stale owners
		# (3) delete stale waits
		# (4) delete stale owners
		owners = set()
		for owner_key in self._redis_scan_iter('owner:*'):
			owners.add(re.match(r'owner:(.+)', owner_key.decode()).group(1))
		waitors = set()
		for wait_key in self._redis_scan_iter('wait:*'):
			waitors.add(re.match(r'wait:(.+)', wait_key.decode()).group(1))
		active_clients = set()
		for client in self.redis.client_list():
			m = re.match(r'redisrwlock:(.+)', client['name'])
			if m:
				active_clients.add(m.group(1))
		# (1) Find out stale owners and waits
		stale_owners = set()
		for owner in owners:
			if owner not in active_clients:
				stale_owners.add(owner)
		stale_waitors = set()
		for waitor in waitors:
			if waitor not in active_clients:
				stale_waitors.add(waitor)
		# (2) Gc locks and grants of stale owners
		stale_lock_count = 0
		for owner in stale_owners:
			for access in self.redis.smembers('owner:' + owner):
				m = re.match(r'([RW]):(.+)', access.decode())
				mode, name = m.group(1, 2)
				lock = name + ':' + mode + ':' + owner
				self.redis.delete('lock:' + lock)
				self.redis.srem('rsrc:' + name, mode + ':' + owner)
				stale_lock_count += 1
				logger.info('gc: ' + 'lock:' + lock)
		# (3) Gc waitors and waitees? of stale owners
		stale_wait_count = 0
		for waitor in stale_waitors:
			self.redis.delete('wait:' + waitor)
			stale_wait_count += 1
			logger.info('gc: ' + 'wait:' + waitor)
			# Note: 'SREM' from other waitors having this waitor as member
			# This seems not required, because active waitors rebuild
			# their wait sets when they retry locking.
		# (4) Gc stale owners
		stale_owner_count = 0
		for owner in stale_owners:
			self.redis.delete('owner:' + owner)
			stale_owner_count += 1
			logger.info('gc: ' + 'owner:' + owner)
		# Gc report
		logger.info('gc: ' + str(stale_lock_count) + ' lock(s), ' +
					str(stale_wait_count) + ' wait(s), ' +
					str(stale_owner_count) + ' owner(s)')

	def _deadlock(self, name, mode):
		self._waitset(name, mode)
		myself, visited, path = self.get_owner(), set(), list()
		if self._cyclic(myself, visited, path):
			return self._victim(path)
		return False

	# Make sure wait set is up to date before deadlock detection
	# This could be done in _LOCK_SCRIPT, but here to satisfy redis
	# EVAL KEYS semantic
	def _waitset(self, name, mode):
		myself = self.get_owner()
		grants = self.redis.smembers('rsrc:' + name)
		self.redis.sadd('wait:' + myself, '__dummy_seed_waitee__')
		if logging.getLogger().isEnabledFor(logging.DEBUG):
			waitees = list()
		for grant in grants:
			m = re.match(r'([RW]):(.+)', grant.decode())
			grant_mode, grant_owner = m.group(1, 2)
			if grant_owner != myself:
				if not (grant_mode == Rwlock.READ and mode == Rwlock.READ):
					retval = self.redis.scard('wait:' + grant_owner)
					if retval:
						self.redis.sadd('wait:' + myself, grant_owner)
						if logging.getLogger().isEnabledFor(logging.DEBUG):
							waitees.append(grant_owner)
					else:
						self.redis.srem('wait:' + myself, grant_owner)
		if logging.getLogger().isEnabledFor(logging.DEBUG) and waitees:
			logger.debug('waitset: %s waits {%s}', myself, ', '.join(waitees))

	# Deadlock detect - cycle detect in wait-for graph (DAG)
	# DFS checking rediscovering of vertex in path
	def _cyclic(self, current, visited, path):
		if current in path:
			logger.debug("_cyclic: [%s]", '->'.join(path))
			return True
		adj_set = self.redis.smembers('wait:' + current)
		for adj in adj_set:
			adj = adj.decode()
			if adj not in visited:
				path.append(current)
				if self._cyclic(adj, visited, path):
					return True
				path.pop()
		visited.add(current)
		return False

	# Among the waitors in cycle, one who lives long with granted lock
	# will survive.
	# (1) oldest lock granted for each waitor
	# (2) victim is waitor with youngest lock granted obtained from (1)
	def _victim(self, path):
		victim, victim_time = None, None
		for waitor in path:
			waitor_time = self._oldest_lock_access_time(waitor)
			# waitor_time can be None when waitor is other waitor who is
			# selected as victim and returned after remove its wait set.
			if waitor_time is None:
				return False
			if victim is None or _cmp_time(waitor_time, victim_time) > 0:
				victim, victim_time = waitor, waitor_time
		assert victim is not None
		myself = self.get_owner()
		if victim != myself:
			logger.debug('_victim: %s, not victim. retry ...', myself)
			return False
		logger.debug('_victim: %s, the victim. DEADLOCK.', myself)
		return True

	# Oldest lock access time,
	# the representative (oldest) lock access time of this waitor
	def _oldest_lock_access_time(self, waitor):
		waitor_time = None
		for access in self.redis.smembers('owner:' + waitor):
			mode, name = re.match(r'([RW]):(.+)', access.decode()).group(1, 2)
			lock = self.redis.get('lock:' + name + ':' + mode + ':' + waitor)
			# lock can be deleted if DEADLOCK victim unlocked already
			if not lock:
				continue
			access_time = re.match(r'.+:(.+)', lock.decode()).group(1)
			if waitor_time is None or _cmp_time(access_time, waitor_time) < 0:
				waitor_time = access_time
		return waitor_time

	# For test aid, not public
	def _clear_all(self):
		count = 0
		for lock in self._redis_scan_iter('lock:*:[RW]:*'):
			logger.debug('_clear_all: ' + lock.decode())
			count += self.redis.delete(lock.decode())
		for rsrc in self._redis_scan_iter('rsrc:*'):
			logger.debug('_clear_all: ' + rsrc.decode())
			count += self.redis.delete(rsrc.decode())
		for owner in self._redis_scan_iter('owner:*'):
			logger.debug('_clear_all: ' + owner.decode())
			count += self.redis.delete(owner.decode())
		for wait in self._redis_scan_iter('wait:*'):
			logger.debug('_clear_all: ' + wait.decode())
			count += self.redis.delete(wait.decode())
		return True if count > 0 else False


# TODO: high availability! redis sentinel or replication?

"""
Async version
"""

from functools import wraps

_rw_rdb = redis.StrictRedis(host = os.getenv('REDISTOGO_URL', 'redis'))
_client = RwlockClient(redis = _rw_rdb)

"""
Define reader-writer lock RAII helpers
"""

class WriterLockAsync() :
    def __init__(self, name) :
        self.name = name
        
    async def __aenter__(self) :
        self.lock = await _client.lock_async(self.name, Rwlock.WRITE, timeout = Rwlock.FOREVER)
        if self.lock.status == Rwlock.OK:
            return self
        elif self.lock.status == Rwlock.DEADLOCK:
            raise Exception('Deadlock in redis WriterLock')

    async def __aexit__(self, type, value, traceback) :
        _client.unlock(self.lock)

class ReaderLockAsync() :
    def __init__(self, name) :
        self.name = name
        
    async def __aenter__(self) :
        self.lock = await _client.lock_async(self.name, Rwlock.READ, timeout = Rwlock.FOREVER)
        if self.lock.status == Rwlock.OK:
            return self
        elif self.lock.status == Rwlock.DEADLOCK:
            raise Exception('Deadlock in redis ReaderLock')

    async def __aexit__(self, type, value, traceback) :
        _client.unlock(self.lock)

"""
Define reader-writer lock decorator helpers
"""

def modifyingResourceAsync(name):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with WriterLockAsync(name) :
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def usingResourceAsync(name):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with ReaderLockAsync(name) :
                return await func(*args, **kwargs)
        return wrapper
    return decorator



