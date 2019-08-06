
from .SLR import Parser

from anytree import Node, RenderTree

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
             | ANY : <tag> //by <tag> I mean <group-name> but whatever
             | ALL : <tag> //by <tag> I mean <group-name> but whatever

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
                if ch == ' ' :
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
                        tag += ch
        return ts, ss

_p = _build_parser()

#TODO need optimization

def _getk(node, idx):
        return node.children[idx].name.split()[0]

def _getv(node, idx):
        return node.children[idx].name.split()[1]

def _prepare_tag_list(node, groups):
        if len(node.children) == 3:
                if _getk(node, 0) == 'ALL':
                        return 'all-tags', { 'tags' : { '$all' : groups[_getv(node, 2)] } }
                else:
                        return 'any-tags', { 'tags' : { '$in' : groups[_getv(node, 2)] } }
        else:
                return 'single-tag', { 'tags' : _getv(node, 0) }

# parse syntax tree into query structure with some simple optimization
# TODO: reordering optimization required
def _parse_tree(node, groups, any_node = False):
        if node.name == '<tag-list>':
                return _prepare_tag_list(node, groups)
        if node.name == '<primary-query>':
                if len(node.children) == 1:
                        return _prepare_tag_list(node.children[0], groups)
                elif len(node.children) == 3:
                        return _parse_tree(node.children[1], groups)
                else:
                        struct, tree = _parse_tree(node.children[2], groups, any_node = True)
                        if struct == 'any-tags' or struct == 'single-tag':
                            return struct, tree
                        return 'complex-query', { '$or' : tree }
        if node.name == '<unary-query>' :
                if len(node.children) == 1:
                        return _parse_tree(node.children[0], groups)
                else:
                        # handle NOT operator
                        struct, tree = _parse_tree(node.children[1], groups)
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
                                return 'any-tags', { 'tags' : { 'nin' : tree['tags']['$nin'] } }
                        else:
                                return 'not-complex-query', { '$not' : tree }
        if node.name == '<and-query>':
                if len(node.children) == 1:
                        return _parse_tree(node.children[0], groups)
                elif len(node.children) == 2 and any_node:
                        structl, treel = _parse_tree(node.children[0], groups, any_node)
                        structr, treer = _parse_tree(node.children[1], groups, any_node)
                        if structl == 'single-tag' and structr == 'single-tag':
                                return 'any-tags', { 'tags' : { '$in' : [ treel['tags'], treer['tags'] ] } }
                        elif structl == 'single-tag' and structr == 'any-tags':
                                return 'any-tags', { 'tags' : { '$in' : [ treel['tags'] ] + treer['tags']['$in'] } }
                        elif structl == 'any-tags' and structr == 'single-tag':
                                return 'any-tags', { 'tags' : { '$in' : [ treer['tags'] ] + treel['tags']['$in'] } }
                        elif structl == 'any-tags' and structr == 'any-tags':
                                return 'any-tags', { 'tags' : { '$in' : treel['tags']['$in'] + treer['tags']['$in'] } }
                        elif '$or' in treel and '$or' in treer:
                                return 'complex-query', { '$or' : treel['$or'] + treer['$or'] }
                        else:
                                return 'complex-query', (treel if isinstance(treel, list) else [treel]) + (treer if isinstance(treer, list) else [treer])
                else:
                        if len(node.children) == 3:
                                structl, treel = _parse_tree(node.children[0], groups)
                                structr, treer = _parse_tree(node.children[2], groups)
                        else:
                                structl, treel = _parse_tree(node.children[0], groups)
                                structr, treer = _parse_tree(node.children[1], groups)
                        if structl == 'single-tag' and structr == 'single-tag':
                                return 'all-tags', { 'tags' : { '$all' : [ treel['tags'], treer['tags'] ] } }
                        elif structl == 'single-tag' and structr == 'all-tags':
                                return 'all-tags', { 'tags' : { '$all' : [ treel['tags'] ] + treer['tags']['$all'] } }
                        elif structl == 'all-tags' and structr == 'single-tag':
                                return 'all-tags', { 'tags' : { '$all' : [ treer['tags'] ] + treel['tags']['$all'] } }
                        elif structl == 'all-tags' and structr == 'all-tags':
                                return 'all-tags', { 'tags' : { '$all' : treel['tags']['$all'] + treer['tags']['$all'] } }
                        elif '$and' in treel and '$and' in treer:
                                return 'complex-query', { '$and' : treel['$and'] + treer['$and'] }
                        else:
                                return 'complex-query', { '$and' : [ treel, treer ] }
        if node.name == '<query>':
                if len(node.children) == 1:
                        return _parse_tree(node.children[0], groups)
                elif len(node.children) == 3:
                        structl, treel = _parse_tree(node.children[0], groups)
                        structr, treer = _parse_tree(node.children[2], groups)
                        if structl == 'single-tag' and structr == 'single-tag':
                                return 'any-tags', { 'tags' : { '$in' : [ treel['tags'], treer['tags'] ] } }
                        elif structl == 'single-tag' and structr == 'any-tags':
                                return 'any-tags', { 'tags' : { '$in' : [ treel['tags'] ] + treer['tags']['$in'] } }
                        elif structl == 'any-tags' and structr == 'single-tag':
                                return 'any-tags', { 'tags' : { '$in' : [ treer['tags'] ] + treel['tags']['$in'] } }
                        elif structl == 'any-tags' and structr == 'any-tags':
                                return 'any-tags', { 'tags' : { '$in' : treel['tags']['$in'] + treer['tags']['$in'] } }
                        elif '$or' in treel and '$or' in treer:
                                return 'complex-query', { '$or' : treel['$or'] + treer['$or'] }
                        else:
                                return 'complex-query', { '$or' : [ treel, treer ] }

def parse(query, tag_translator, group_translator):
        ts, ss = _lex(query)
        tags = []
        groups = []
        for i, (k, v) in enumerate(zip(ts, ss)):
                if k == 'TAG':
                        if i > 0 and ts[i-1] == ':':
                                groups.append(v)
                        else:
                                tags.append(v)
        tags = tag_translator(tags)
        group_map = group_translator(groups)
        ti = 0
        for i, (k, v) in enumerate(zip(ts, ss)):
                if k == 'TAG' and ((i > 0 and ts[i-1] != ':') or i == 0):
                        ss[i] = tags[ti]
                        ti += 1
        tree = _p.Parse(ts, ss)
        if tree is None:
                return None
        _, ans = _parse_tree(tree, group_map)
        return ans

