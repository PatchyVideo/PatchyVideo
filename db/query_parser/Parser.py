
import sys

from .SLR import Parser
from anytree import Node, RenderTree
from bson.json_util import loads

"""
<query> ::= <and-query>
		  | <query> OR <and-query>

<and-query> ::= <unary-query>
	    	  | <and-query> ' ' <unary-query>
	     	  | <and-query> AND <unary-query>

<unary-query> ::= <primary-query>
				| NOT <primary-query>

<primary-query> ::= ( <query> )
				  | <tag-list>
				  | ANY ( <and-query> )

<tag-list> ::= <tag>
	    	 | ANY : <tag>
	    	 | ALL : <tag>
	    	 | <tag> : <tag> // special query term

"""

def _build_parser() :
	p = Parser()
	# add non-terminal symbols
	p.AddNT( '<query>' )
	p.AddNT( '<and-query>' )
	p.AddNT( '<unary-query>' )
	p.AddNT( '<primary-query>' )
	p.AddNT( '<tag-list>' )
	# add terminal symbols
	for t in ['TAG','(',')',':',',','AND','OR','NOT','ANY','ALL'] :
		p.AddT( t )

	p.SetStartSymbol( '<query>' )

	# add productions
	p.AddP( '<query>', '<and-query>' )
	p.AddP( '<query>', [ '<query>', 'OR', '<and-query>' ] )

	p.AddP( '<and-query>', '<unary-query>' )
	p.AddP( '<and-query>', [ '<and-query>', '<unary-query>' ] )
	p.AddP( '<and-query>', [ '<and-query>', 'AND', '<unary-query>' ] )

	p.AddP( '<unary-query>', '<primary-query>' )
	p.AddP( '<unary-query>', [ 'NOT', '<primary-query>' ] )

	p.AddP( '<primary-query>', [ '(', '<query>', ')' ] )
	p.AddP( '<primary-query>', '<tag-list>' )
	p.AddP( '<primary-query>', [ 'ANY', '(', '<and-query>', ')' ] )
	
	p.AddP( '<tag-list>', 'TAG' )
	p.AddP( '<tag-list>', [ 'ANY', ':', 'TAG' ] )
	p.AddP( '<tag-list>', [ 'ALL', ':', 'TAG' ] )
	p.AddP( '<tag-list>', [ 'TAG', ':', 'TAG' ] )

	# build parse table
	p.PrepareParser()
	return p

def _lex( query ) :
	query += ' '
	ts = []
	ss = []
	tag = ''
	state = 'normal'
	def add_symbol(tag):
		if tag == 'AND' :
			ts.append( 'AND' )
			ss.append( 'AND' )
		elif tag == 'OR' :
			ts.append( 'OR' )
			ss.append( 'OR' )
		elif tag == 'ANY' :
			ts.append( 'ANY' )
			ss.append( 'ANY' )
		elif tag == 'ALL' :
			ts.append( 'ALL' )
			ss.append( 'ALL' )
		elif tag == 'NOT' :
			ts.append( 'NOT' )
			ss.append( 'NOT' )
		elif tag :
			ts.append( 'TAG' )
			ss.append( tag )
		return ''
	for ch in query :
		if ch in [' ', '\n', '\r', '\v', '\f', '\t'] :
			if state == 'normal' or state == 'pre()' :
				tag = add_symbol(tag)
			elif state == 'in()' :
				raise Exception()
		elif ch == '_' :
			if state == 'normal' or state == 'pre()' :
				state = 'pre()'
				tag += ch
			elif state == 'in()' :
				tag += ch
		elif ch == '(' :
			if state == 'normal' :
				tag = add_symbol(tag)
				ts.append( '(' )
				ss.append( '(' )
			elif state == 'pre()' :
				tag += ch
				state = 'in()'
			elif state == 'in()' :
				raise Exception()
		elif ch == ')' :
			if state == 'normal' or state == 'pre()' :
				tag = add_symbol(tag)
				ts.append( ')' )
				ss.append( ')' )
			elif state == 'in()' :
				tag += ch
			state = 'normal'
		elif ch == ':' :
			if state == 'normal' or state == 'pre()' :
				tag = add_symbol(tag)
				ts.append( ':' )
				ss.append( ':' )
			elif state == 'in()' :
				raise Exception()
		elif ch == ',' :
			if state == 'normal' or state == 'pre()' :
				tag = add_symbol(tag)
				ts.append( ',' )
				ss.append( ',' )
			elif state == 'in()' :
				raise Exception()
		else :
			if state == 'pre()' :
				state = 'normal'
			tag += ch
	return ts, ss

_p = _build_parser()

#TODO need optimization

from dateutil.parser import parse as parse_date
from datetime import timedelta

def _prepare_attributes(name, value):
	value = value.lower()
	name = name.lower()
	if name == 'site':
		query = ''
		if value == 'acfun':
			query = 'acfun'
		elif value in ['bilibili', 'bili']:
			query = 'bilibili'
		elif value in ['youtube', 'ytb']:
			query = 'youtube'
		elif value in ['nicovideo', 'niconico', 'nico']:
			query = 'nicovideo'
		elif value in ['twitter']:
			query = 'twitter'
		elif value in ['ipfs']:
			query = 'ipfs'
		else :
			query = value
		return { 'item.site': query }
	elif name == 'date':
		if value[:2] == '<=' :
			date = parse_date(value[2:])
			return { 'item.upload_time' : { '$lte' : date + timedelta(days = 1) } }
		elif value[:2] == '>=' :
			date = parse_date(value[2:])
			return { 'item.upload_time' : { '$gte' : date } }
		elif value[:1] == '<' :
			date = parse_date(value[1:])
			return { 'item.upload_time' : { '$lt' : date } }
		elif value[:1] == '>' :
			date = parse_date(value[1:])
			return { 'item.upload_time' : { '$gt' : date } }
		elif value[:1] == '=' :
			date = parse_date(value[1:])
			return { 'item.upload_time' : { '$gte' : date, '$lte' : date + timedelta(days = 1) } }
		date = parse_date(value)
		return { 'item.upload_time' : { '$gte' : date, '$lte' : date + timedelta(days = 1) } }
	elif name == 'tags':
		if value[:2] == '<=' :
			return { 'tag_count' : { '$lte' : int(value[2:]) } }
		elif value[:2] == '>=' :
			return { 'tag_count' : { '$gte' : int(value[2:]) } }
		elif value[:1] == '<' :
			return { 'tag_count' : { '$lt' : int(value[1:]) } }
		elif value[:1] == '>' :
			return { 'tag_count' : { '$gt' : int(value[1:]) } }
		elif value[:1] == '=' :
			return { 'tag_count' : { '$eq' : int(value[1:]) } }
		else :
			return {}
	elif name == 'placeholder':
		if value == 'true' :
			return { 'item.placeholder' : True }
		elif value == 'false' :
			return { 'item.placeholder' : False }
		else :
			return {}
	elif name == 'repost':
		return { 'item.repost_type': value }
	return {}

def _getk(node, idx):
	return node.children[idx].name.split()[0]

def _getv(node, idx):
	return ''.join(node.children[idx].name.split()[1:])

def _cd(t) :
	return list(set(t))

def _int(a) :
	if isinstance(a, int) :
		return a
	elif isinstance(a, str) :
		try :
			return int(a)
		except :
			return a
	elif isinstance(a, list) :
		return [_int(b) for b in a]

def _prepare_tag_list(node, groups, tag_translator, wildcard_translator):
	if len(node.children) == 3:
		if _getk(node, 0) == 'ALL':
			return 'all-tags', { 'tags' : { '$all' : _int(groups[_getv(node, 2)]) } }
		elif _getk(node, 0) == 'ANY':
			return 'any-tags', { 'tags' : { '$in' : _int(groups[_getv(node, 2)]) } }
		else :
			try:
				return 'complex-query', _prepare_attributes(_getv(node, 0), _getv(node, 2))
			except:
				return 'any-tags', {'$tags': {'$in': []}}
	else:
		tag = _getv(node, 0)
		if tag[0] == ')' :
			query_obj = loads(tag[1: ])
			return query_obj['type'], query_obj['obj']
		else :
			if '*' in tag :
				in_tags = _cd(wildcard_translator(tag))
				if len(in_tags) == 1 :
					return 'single-tag', { 'tags' : _int(in_tags[0]) }
				else :
					return 'any-tags', { 'tags' : { '$in' : _int(in_tags) } }
			else :
				return 'single-tag', { 'tags' : _int(tag) }

# parse syntax tree into query structure with some simple optimizations
# TODO: handle none tag
def _parse_tree(node, groups, tag_translator, wildcard_translator, any_node = False):
	if node.name == '<tag-list>':
		return _prepare_tag_list(node, groups, tag_translator, wildcard_translator)
	if node.name == '<primary-query>':
		if len(node.children) == 1:
			return _prepare_tag_list(node.children[0], groups, tag_translator, wildcard_translator)
		elif len(node.children) == 3:
			return _parse_tree(node.children[1], groups, tag_translator, wildcard_translator)
		else:
			struct, tree = _parse_tree(node.children[2], groups, tag_translator, wildcard_translator, any_node = True)
			if struct == 'any-tags' or struct == 'single-tag':
			    return struct, tree
			if len(tree) == 1 :
				return 'complex-query', tree
			else :
				return 'complex-query', { '$or' : tree }
	if node.name == '<unary-query>' :
		if len(node.children) == 1:
			return _parse_tree(node.children[0], groups, tag_translator, wildcard_translator)
		else:
			# handle NOT operator
			struct, tree = _parse_tree(node.children[1], groups, tag_translator, wildcard_translator)
			if struct == 'complex-query':
				return 'not-complex-query', { '$not' : tree }
			elif struct == 'not-complex-query':
				return 'complex-query', tree['$not']
			elif struct == 'single-tag':
				return 'not-single-tag', { 'tags' : { '$nin' : [ tree['tags'] ] } }
			elif struct == 'not-single-tag':
				return 'single-tag', { 'tags' : tree['tags']['$nin'][0] }
			elif struct == 'all-tags' :
				return 'not-all-tags', { '$not' : tree }
			elif struct == 'not-all-tags' :
				return 'all-tags', tree['$not']
			elif struct == 'any-tags' :
				return 'not-any-tags', { 'tags' : { '$nin' : tree['tags']['$in'] } }
			elif struct == 'not-any-tags':
				return 'any-tags', { 'tags' : { '$nin' : tree['tags']['$nin'] } }
			else:
				return 'not-complex-query', { '$not' : tree }
	if node.name == '<and-query>':
		if len(node.children) == 1:
			return _parse_tree(node.children[0], groups, tag_translator, wildcard_translator)
		elif len(node.children) == 2 and any_node:
			structl, treel = _parse_tree(node.children[0], groups, any_node, tag_translator, wildcard_translator)
			structr, treer = _parse_tree(node.children[1], groups, any_node, tag_translator, wildcard_translator)
			if structl == 'single-tag' and structr == 'single-tag':
				in_tag = _cd([ treel['tags'], treer['tags'] ])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif structl == 'single-tag' and structr == 'any-tags':
				in_tag = _cd([ treel['tags'] ] + treer['tags']['$in'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif structl == 'any-tags' and structr == 'single-tag':
				in_tag = _cd([ treer['tags'] ] + treel['tags']['$in'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif structl == 'any-tags' and structr == 'any-tags':
				in_tag = _cd(treel['tags']['$in'] + treer['tags']['$in'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif '$or' in treel and '$or' in treer:
				return 'complex-query', { '$or' : treel['$or'] + treer['$or'] }
			else:
				return 'complex-query', (treel if isinstance(treel, list) else [treel]) + (treer if isinstance(treer, list) else [treer])
		else:
			if len(node.children) == 3:
				structl, treel = _parse_tree(node.children[0], groups, tag_translator, wildcard_translator)
				structr, treer = _parse_tree(node.children[2], groups, tag_translator, wildcard_translator)
			else:
				structl, treel = _parse_tree(node.children[0], groups, tag_translator, wildcard_translator)
				structr, treer = _parse_tree(node.children[1], groups, tag_translator, wildcard_translator)
			if structl == 'single-tag' and structr == 'single-tag':
				in_tag = _cd([ treel['tags'], treer['tags'] ])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'all-tags', { 'tags' : { '$all' : in_tag } }
				return 'all-tags', { 'tags' : { '$all' : _cd([ treel['tags'], treer['tags'] ]) } }
			elif structl == 'single-tag' and structr == 'all-tags':
				in_tag = _cd([ treel['tags'] ] + treer['tags']['$all'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'all-tags', { 'tags' : { '$all' : in_tag } }
			elif structl == 'all-tags' and structr == 'single-tag':
				in_tag = _cd([ treer['tags'] ] + treel['tags']['$all'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'all-tags', { 'tags' : { '$all' : in_tag } }
			elif structl == 'all-tags' and structr == 'all-tags':
				in_tag = _cd(treel['tags']['$all'] + treer['tags']['$all'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'all-tags', { 'tags' : { '$all' : in_tag } }
			elif '$and' in treel and '$and' in treer:
				return 'complex-query', { '$and' : treel['$and'] + treer['$and'] }
			else:
				return 'complex-query', { '$and' : [ treel, treer ] }
	if node.name == '<query>':
		if len(node.children) == 1:
			return _parse_tree(node.children[0], groups, tag_translator, wildcard_translator)
		elif len(node.children) == 3:
			structl, treel = _parse_tree(node.children[0], groups, tag_translator, wildcard_translator)
			structr, treer = _parse_tree(node.children[2], groups, tag_translator, wildcard_translator)
			if structl == 'single-tag' and structr == 'single-tag':
				in_tag = _cd([ treel['tags'], treer['tags'] ])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif structl == 'single-tag' and structr == 'any-tags':
				in_tag = _cd([ treel['tags'] ] + treer['tags']['$in'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif structl == 'any-tags' and structr == 'single-tag':
				in_tag = _cd([ treer['tags'] ] + treel['tags']['$in'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif structl == 'any-tags' and structr == 'any-tags':
				in_tag = _cd(treel['tags']['$in'] + treer['tags']['$in'])
				if len(in_tag) == 1 :
					return 'single-tag', { 'tags' : in_tag[0] }
				else :
					return 'any-tags', { 'tags' : { '$in' : in_tag } }
			elif '$or' in treel and '$or' in treer:
				return 'complex-query', { '$or' : treel['$or'] + treer['$or'] }
			else:
				return 'complex-query', { '$or' : [ treel, treer ] }

def _expand_not(tree) :
	return tree

def parse_tag(query, tag_translator, group_translator, wildcard_translator):
	try :
		ts, ss = _lex(query)
	except :
		return None, None
	tags = []
	groups = []
	for i, (k, v) in enumerate(zip(ts, ss)):
		if k == 'TAG':
			if i > 0 and ts[i-1] == ':':
				groups.append(v)
			else:
				tags.append(v)
	tags2 = [str(t) for t in tag_translator(tags)]
	group_map = group_translator(groups)
	ti = 0
	for i, (k, v) in enumerate(zip(ts, ss)):
		if k == 'TAG' and ((i > 0 and ts[i-1] != ':') or i == 0):
			ss[i] = tags2[ti]
			ti += 1
	tree = _p.Parse(ts, ss)
	if tree is None:
		return None, None
	try:
		_, ans = _parse_tree(tree, group_map, tag_translator, wildcard_translator)
		ans = _expand_not(ans)
		return ans, tags
	except:
		return None, None

def parse_url(query):
	from scraper.video import dispatch as dispatch_url_query
	obj, cleanURL = dispatch_url_query(query)
	if obj is None:
		return None
	return { 'item.unique_id': obj.get_unique_id(obj, cleanURL) }

def parse(query, tag_translator, group_translator, wildcard_translator):
	tag_query, tags = parse_tag(query, tag_translator, group_translator, wildcard_translator)
	print(f'"{query}" to {tag_query}', file = sys.stderr)
	url_query = parse_url(query)
	if tag_query and url_query:
		return { '$or': [tag_query, url_query] }, tags
	if tag_query and not url_query:
		return tag_query, tags
	if not tag_query and url_query:
		return url_query, tags
	return None, None

