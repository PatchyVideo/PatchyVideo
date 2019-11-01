
from anytree import Node, RenderTree
from .NFA import eNFA

# simple LR parser
class Parser :
	def __init__(self) :
		self.nt_symbols = []
		self.t_symbols = []
		self.productions = {}
		self.start_symbol = ''
		self.tokens = ''
		self.ident = 0

		self.first = {}
		self.follow = {}
		self.items = []

	def AddT( self, symbol ) :
		assert not symbol in [ '__EPSILON__', '__DOLLAR__', '__BEGIN__' ]
		if not symbol in self.t_symbols :
			self.t_symbols.append( symbol )

	def AddNT( self, symbol ) :
		assert not symbol in [ '__EPSILON__', '__DOLLAR__', '__BEGIN__' ]
		if not symbol in self.nt_symbols :
			self.nt_symbols.append( symbol )

	def SetStartSymbol( self, symbol ) :
		self.start_symbol = symbol

	def AddP( self, symbol, body ) :
		assert not symbol in [ '__EPSILON__', '__DOLLAR__', '__BEGIN__' ]

		if not isinstance( body, list ) :
			body = [ body ]
		assert symbol in self.nt_symbols

		if symbol in self.productions :
			self.productions[symbol].append( body )
		else :
			self.productions[symbol] = [ body ]

	def _getAllFirstSet( self ) :
		self.first = {}
		#for terminal in self.t_symbols :
		#	self.first[terminal] = set( [ terminal ] )
		for nt in self.nt_symbols :
			self.first[nt] = set( filter( lambda first_symbol : first_symbol in self.t_symbols or first_symbol == '__EPSILON__', [ x[0] for x in self.productions[nt] ] ) )

		for _ in range( len( self.nt_symbols ) * 2 ) :
			for nt in self.nt_symbols :
				for p in self.productions[nt] : # for all productions p
					if p[0] in self.nt_symbols :
						self.first[nt] |= self.first[p[0]]


			for nt in self.nt_symbols :
				for p in self.productions[nt] : # for all productions p
					# production nt->p
					t_s = ''
					for s in p :
						if s in self.nt_symbols :
							if '__EPSILON__' in self.first[s] :
								continue
						t_s = s
						break
					if t_s in self.t_symbols:
						self.first[nt] |= set( [ t_s ] )

	def _ntToEmpty( self, symbol ) :
		return '__EPSILON__' in self._first( symbol )

	def _getAllFollowSet( self ) :
		self.follow = {}
		for nt in self.nt_symbols :
			self.follow[nt] = set()

		self.follow[self.start_symbol] = set( [ '__DOLLAR__' ] )

		# handle the easy cases
		for _ in range( len( self.nt_symbols ) * 2 ) :
			for nt in self.nt_symbols :
				for p in self.productions[nt] : # for all productions p
					for i in range( len( p ) - 1 ) :
						if p[i] in self.nt_symbols :
							if p[i + 1] in self.nt_symbols :
								self.follow[p[i]] |= self.first[p[ i + 1 ]]
							if p[i + 1] in self.t_symbols :
								self.follow[p[i]] |= set( [ p[i + 1] ] )

			for nt in self.nt_symbols :
				for p in self.productions[nt] : # for all productions p
					if p[-1] in self.nt_symbols :
						self.follow[p[-1]] |= self.follow[nt]
					for i in reversed( range( len( p ) - 1 ) ) :
						if p[i+1] in self.nt_symbols and p[i] in self.nt_symbols :
							if self._ntToEmpty( p[i+1] ) :
								self.follow[p[i]] |= self.follow[nt]
						else :
							break

			for nt in self.follow.keys() :
				if '__EPSILON__' in self.follow[nt] :
					self.follow[nt].remove( '__EPSILON__' )

	def _first( self, s_or_p ) :
		if isinstance( s_or_p, list ) : # s_or_p is a production
			s_or_p = s_or_p[0]
		if s_or_p == '__EPSILON__' :
			return [ '__EPSILON__' ]
		if s_or_p in self.t_symbols :
			return [ s_or_p ]
		return self.first[s_or_p]

	def _packItem( self, item ) :
		nt, body, dot = item
		body_str = chr( 1 ).join( body )
		return chr( 0 ).join( [ nt, body_str, str( dot ) ] )

	def _unpackItem( self, s ) :
		nt, body_str, dot_str = s.split( chr( 0 ) )
		body = body_str.split( chr( 1 ) )
		dot = int( dot_str )
		return ( nt, body, dot )

	def _getAllItems( self ) :
		self.items = []
		self.start_items = {}
		for nt in self.nt_symbols :
			self.start_items[nt] = []
			for p in self.productions[nt] : # for all productions p
				self.start_items[nt].append( ( nt, p, 0 ) )
				for i in range( len( p ) + 1 ) :
					self.items.append( ( nt, p, i ) ) # an item with . position marked by i


	def _buildNFA( self ) :
		n = eNFA( accept_any = False )
		[ n.AddState( self._packItem( x ), final = True ) for x in self.items ]
		s = list( filter( lambda x : x[0] == '__BEGIN__' and x[2] == 0, self.items ) ) # initialize a stack containing items to process
		vis = [] # visited

		assert len( s ) == 1
		n.MarkStartState( self._packItem( s[0] ) )

		while s :
			item = s.pop()
			if item in vis :
				continue
			vis.append( item )

			symbol, body, dot = item
			if dot == len( body ) : # end of production
				continue
			n.AddArc( self._packItem( item ), self._packItem( ( symbol, body, dot + 1 ) ), body[dot] ) # move dot right
			s.append( ( symbol, body, dot + 1 ) )
			if body[dot] in self.nt_symbols :
				nt = body[dot]
				for item2 in self.start_items[nt] :
					s.append( item2 )
					n.AddEpsilonTransition( self._packItem( item ), self._packItem( item2 ) )

		self.viable_prefix_NFA = n

	def PrepareParser( self ) :
		assert self.start_symbol

		# add a dummy production
		self.nt_symbols.append( '__BEGIN__' )
		self.productions['__BEGIN__'] = [ [ self.start_symbol ] ]
		self.start_symbol = '__BEGIN__'

		self._getAllFirstSet()
		self._getAllFollowSet()
		self._getAllItems()
		self._buildNFA()

	def Parse( self, tokens, stream ) :
		tokens.append( '__DOLLAR__' )
		tokens.reverse()
		stream.append( '__DOLLAR__' )
		stream.reverse()
		s = []
		sT = []
		n = self.viable_prefix_NFA

		last_reduction = None

		succeed = False

		#pdb.set_trace()
		while True :
			topI = tokens[-1]
			topS = stream[-1]

			items, accept = n.Simulate( s, execute_action = False )
			items = [ self._unpackItem( item ) for item in items ]
			if not accept :
				break

			ok_to_reduce = False
			completed_items = list( filter( lambda item : len( item[1] ) == item[2], items ) )
			available_reductions = list( filter( lambda item : topI in self.follow[item[0]], completed_items ) )
			if len( available_reductions ) > 1 :
				break
			elif len( available_reductions ) == 1 :
				ok_to_reduce = True

			ok_to_shift = False
			next_symbols = [ item[1][item[2]] for item in filter( lambda item : len( item[1] ) > item[2], items ) ]
			if topI in next_symbols :
				ok_to_shift = True

			if ok_to_reduce and ok_to_shift :
				break

			if ok_to_shift :
				tokens.pop()
				stream.pop()
				s.append( topI )
				sT.append( Node( topI + ' ' + topS ) )

			if ok_to_reduce :
				nt, body, dot = available_reductions[0]
				nt_node = Node( nt )
				for node in sT[ -len( body ) : : ] :
					node.parent = nt_node
				s = s[ : -len( body ) : ]
				sT = sT[ : -len( body ) : ]
				s.append( nt )
				sT.append( nt_node )

			if not ( ok_to_shift or ok_to_reduce ) :
				break

			if s ==  [ '__BEGIN__' ] and tokens == [ '__DOLLAR__' ] :
				succeed = True
				break
		if succeed :
			return sT[0].children[0]
		else :
			return None

	def _separateTerminal( self, v ) :
		return v.split( '|' )[0]

	def _removeEpsilon( self, root ) :
		to_remove = []
		for c in root.children :
			if self._removeEpsilon( c ) :
				to_remove.append( c )
		v = self._separateTerminal( root.name )
		root.children = list( filter( lambda x : not x in to_remove, root.children ) )
		return v in self.nt_symbols and len( root.children ) == 0

	def GetAST( self, tree ) :
		self._removeEpsilon( tree )
		return tree

