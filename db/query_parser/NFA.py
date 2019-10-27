
import collections

class NFA :	
	def __init__( self, accept_any = True ) :
		self.states = []
		self.final_states = []
		self.delta = {}
		self.final_states_map = {}
		self.alphabet = []
		self.start_state = None
		if accept_any :
			self.extendAlphabet( None )

	def Finalize( self ) :
		# TODO: make a DFA is possible
		pass

	def AddState( self, q, final = False, action = None ) :
		if not q in self.states :
			self.states.append( q )
		if final and not q in self.final_states :
			self.final_states.append( q )
		if action and not q in self.final_states_map :
			self.final_states_map[q] = action

	def MarkStartState( self, q ) :
		if q in self.states :
			self.start_state = q

	def MarkFinalState( self, q, action = None ) :
		if q in self.states :
			if not q in self.final_states :
				self.final_states.append( q )
			self.final_states_map[q] = action

	def extendAlphabet( self, symbol ) :
		if not symbol in self.alphabet :
			self.alphabet.append( symbol )

	def AddArc( self, fromState, toState, symbol = None ) :
		if not isinstance( toState, set ) :
			if isinstance( toState, list ) :
				toState = set( toState )
			else :
				toState = set( [ toState ] )
		if fromState in self.delta :
			if isinstance( symbol, list ) or isinstance( symbol, set ) :
				for sym in symbol :
					self.delta[fromState][sym] = toState
					self.extendAlphabet( sym )
			else :
				self.delta[fromState][symbol] = toState
				self.extendAlphabet( symbol )
		else :	
			if isinstance( symbol, list ) or isinstance( symbol, set ) :
				self.delta[fromState] = {}
				for sym in symbol :
					self.delta[fromState][sym] = toState
					self.extendAlphabet( sym )
			else :
				self.delta[fromState] = { symbol : toState }
				self.extendAlphabet( symbol )

	def exeAction( self, states, doit ) :
		if doit :
			for q in states :
				if q in self.final_states_map :
					self.final_states_map[q]()

	def Simulate( self, w, execute_action = True ) :
		assert self.start_state
		cur_states = [ self.start_state ]
		self.exeAction( cur_states, execute_action )
		for symbol in w :
			next_states = []
			for q in cur_states :
				if symbol in self.delta[q] :
					next_states.extend( self.delta[q][symbol] )
				if None in self.delta[q] :
					next_states.extend( self.delta[q][None] )
			cur_states = next_states
			if not cur_states :
				break # no valid moves from here
			self.exeAction( cur_states, execute_action )
		return cur_states, len( set( cur_states ) & set( self.final_states ) ) > 0

class eNFA( NFA ) :						   
	def __init__( self, accept_any = True ) :
		super( eNFA, self ).__init__( accept_any )
		self.delta_e = {}
		self.cltmp = []
		self.runningState = 'HALT'
										   
	def AddEpsilonTransition( self, curState, toState ) : 
		if not isinstance( toState, set ) :																																									
			if isinstance( toState, list ) : 
				toState = set( toState )   
			else :						   
				toState = set( [ toState ] ) 
		assert curState in self.states		  
		if curState in self.delta_e :
			self.delta_e[curState] |= toState   
		else :
			self.delta_e[curState] = toState
										   
	def closure( self, state ) :
		if state in self.cltmp :
			return set()
		self.cltmp.append( state ) # keep track of visited state	
		if state in self.delta_e :		   
			ans = self.delta_e[state]		  
			for s in ans :				   
				ans = ans | self.closure( s ) 
			#ans = ans | set( [ state ] )  
			ans = set( sorted( ans ) )		  
			return ans					   
		return set()					   
										   
	def MakeNFA( self ) :				   
		setify_final = set( self.final_states )
		for state in self.states :
			self.cltmp = []
			cl = self.closure( state )		  
			if not cl :					   
				continue				   
			for symbol in self.alphabet :	
				for q in cl :
					if symbol in self.delta[q] :				
						if self.delta[q][symbol] :
							if symbol in self.delta[state] :
								self.delta[state][symbol] |= self.delta[q][symbol]
							else :
								self.delta[state][symbol] = { symbol : q } # ???
							self.delta[state][symbol] = set( sorted( self.delta[state][symbol] ) ) 
			if ( setify_final & cl ) : # cl contains at least a final state
				self.MarkFinalState( state, self.final_states_map[state] if state in self.final_states_map else None )		
		self.delta_e = {}				   
	
	def extendEpsilonStates( self, cur_states ) :
		states = set( cur_states )
		for state in cur_states :
			self.cltmp = []
			states |= self.closure( state )
		return list( states )

	def Simulate( self, w, execute_action = True ) :
		assert self.start_state
		cur_states = [ self.start_state ]
		cur_states = self.extendEpsilonStates( cur_states )
		self.exeAction( cur_states, execute_action )
		for symbol in w :
			next_states = []
			for q in cur_states :
				if q in self.delta :
					if symbol in self.delta[q] :
						next_states.extend( self.delta[q][symbol] )
					if None in self.delta[q] :
						next_states.extend( self.delta[q][None] )
			cur_states = next_states
			cur_states = self.extendEpsilonStates( cur_states )
			if not cur_states :
				break # no valid moves from here
			self.exeAction( cur_states, execute_action )
		return cur_states, len( set( cur_states ) & set( self.final_states ) ) > 0


	def BeginSimulate( self ) :
		assert self.start_state
		self.runningState = 'RUNNING'
		self.cur_states = [ self.start_state ]
		self.cur_states = self.extendEpsilonStates( self.cur_states )
		return self.cur_states, len( set( self.cur_states ) & set( self.final_states ) ) > 0

	def SimulateStep( self, symbol ) :
		next_states = []
		for q in self.cur_states :
			if q in self.delta :
				if symbol in self.delta[q] :
					next_states.extend( self.delta[q][symbol] )
				if None in self.delta[q] :
					next_states.extend( self.delta[q][None] )
		self.cur_states = next_states
		self.cur_states = self.extendEpsilonStates( self.cur_states )
		if self.cur_states :
			self.runningState = 'ERROR'
		return self.cur_states, len( set( self.cur_states ) & set( self.final_states ) ) > 0


