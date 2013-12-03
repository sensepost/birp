import signal
import platform

'''
	A very lightweight keypress handling library that won't try and take over
	your console.

	For the most part it a disgusting kludge based on the horrendously
	inconsistent key events you get in different OS'es

	I'm embarrassed to put my name on this, but it works - dominic () sensepost.com (@singe)
	Originally based on the recipe at http://code.activestate.com/recipes/134892/

	todo: map keypresses on windows
	todo: optimise decision tree on linux
'''
class TimeoutException(Exception): 
	pass 

class _Getch:
	# Gets a single character from standard input.  Does not echo to the screen.
	def __init__(self):
		if platform.system() == 'Darwin':
			self.impl = _GetchMac()
		if platform.system() == 'Linux':
			self.impl = _GetchUnix()
		if platform.system() == 'Windows':
			self.impl = _GetchWindows()

		self.KEY_TAB = self.impl.KEY_TAB
		self.KEY_ESC = self.impl.KEY_ESC
		self.KEY_a = self.impl.KEY_a
		self.KEY_b = self.impl.KEY_b
		self.KEY_c = self.impl.KEY_c
		self.KEY_d = self.impl.KEY_d
		self.KEY_e = self.impl.KEY_e
		self.KEY_f = self.impl.KEY_f
		self.KEY_g = self.impl.KEY_g
		self.KEY_h = self.impl.KEY_h
		self.KEY_i = self.impl.KEY_i
		self.KEY_j = self.impl.KEY_j
		self.KEY_k = self.impl.KEY_k
		self.KEY_l = self.impl.KEY_l
		self.KEY_m = self.impl.KEY_m
		self.KEY_n = self.impl.KEY_n
		self.KEY_o = self.impl.KEY_o
		self.KEY_p = self.impl.KEY_p
		self.KEY_q = self.impl.KEY_q
		self.KEY_r = self.impl.KEY_r
		self.KEY_s = self.impl.KEY_s
		self.KEY_t = self.impl.KEY_t
		self.KEY_u = self.impl.KEY_u
		self.KEY_v = self.impl.KEY_v
		self.KEY_w = self.impl.KEY_w
		self.KEY_x = self.impl.KEY_x
		self.KEY_y = self.impl.KEY_y
		self.KEY_z = self.impl.KEY_z
		self.KEY_A = self.impl.KEY_A
		self.KEY_B = self.impl.KEY_B
		self.KEY_C = self.impl.KEY_C
		self.KEY_D = self.impl.KEY_D
		self.KEY_E = self.impl.KEY_E
		self.KEY_F = self.impl.KEY_F
		self.KEY_G = self.impl.KEY_G
		self.KEY_H = self.impl.KEY_H
		self.KEY_I = self.impl.KEY_I
		self.KEY_J = self.impl.KEY_J
		self.KEY_K = self.impl.KEY_K
		self.KEY_L = self.impl.KEY_L
		self.KEY_M = self.impl.KEY_M
		self.KEY_N = self.impl.KEY_N
		self.KEY_O = self.impl.KEY_O
		self.KEY_P = self.impl.KEY_P
		self.KEY_Q = self.impl.KEY_Q
		self.KEY_R = self.impl.KEY_R
		self.KEY_S = self.impl.KEY_S
		self.KEY_T = self.impl.KEY_T
		self.KEY_U = self.impl.KEY_U
		self.KEY_V = self.impl.KEY_V
		self.KEY_W = self.impl.KEY_W
		self.KEY_X = self.impl.KEY_X
		self.KEY_Y = self.impl.KEY_Y
		self.KEY_Z = self.impl.KEY_Z
		self.KEY_0 = self.impl.KEY_0
		self.KEY_1 = self.impl.KEY_1
		self.KEY_2 = self.impl.KEY_2
		self.KEY_3 = self.impl.KEY_3
		self.KEY_4 = self.impl.KEY_4
		self.KEY_5 = self.impl.KEY_5
		self.KEY_6 = self.impl.KEY_6
		self.KEY_7 = self.impl.KEY_7
		self.KEY_8 = self.impl.KEY_8
		self.KEY_9 = self.impl.KEY_9
		self.KEY_CTRLa = self.impl.KEY_CTRLa
		self.KEY_CTRLb = self.impl.KEY_CTRLb
		self.KEY_CTRLc = self.impl.KEY_CTRLc
		self.KEY_CTRLd = self.impl.KEY_CTRLd
		self.KEY_CTRLe = self.impl.KEY_CTRLe
		self.KEY_CTRLf = self.impl.KEY_CTRLf
		self.KEY_CTRLg = self.impl.KEY_CTRLg
		self.KEY_CTRLh = self.impl.KEY_CTRLh
		self.KEY_CTRLi = self.impl.KEY_CTRLi
		self.KEY_CTRLj = self.impl.KEY_CTRLj
		self.KEY_CTRLk = self.impl.KEY_CTRLk
		self.KEY_CTRLl = self.impl.KEY_CTRLl
		self.KEY_CTRLm = self.impl.KEY_CTRLm
		self.KEY_CTRLn = self.impl.KEY_CTRLn
		self.KEY_CTRLo = self.impl.KEY_CTRLo
		self.KEY_CTRLp = self.impl.KEY_CTRLp
		self.KEY_CTRLq = self.impl.KEY_CTRLq
		self.KEY_CTRLr = self.impl.KEY_CTRLr
		self.KEY_CTRLs = self.impl.KEY_CTRLs
		self.KEY_CTRLt = self.impl.KEY_CTRLt
		self.KEY_CTRLu = self.impl.KEY_CTRLu
		self.KEY_CTRLv = self.impl.KEY_CTRLv
		self.KEY_CTRLw = self.impl.KEY_CTRLw
		self.KEY_CTRLx = self.impl.KEY_CTRLx
		self.KEY_CTRLy = self.impl.KEY_CTRLy
		self.KEY_CTRLz = self.impl.KEY_CTRLz
		self.KEY_SPACE = self.impl.KEY_SPACE
		self.KEY_BACKSPACE = self.impl.KEY_BACKSPACE
		self.KEY_BANG = self.impl.KEY_BANG
		self.KEY_DOUBLEQUOTE = self.impl.KEY_DOUBLEQUOTE
		self.KEY_HASH = self.impl.KEY_HASH
		self.KEY_DOLLAR = self.impl.KEY_DOLLAR
		self.KEY_PERCENT = self.impl.KEY_PERCENT
		self.KEY_QUOTE = self.impl.KEY_QUOTE
		self.KEY_OPENBRACKET = self.impl.KEY_OPENBRACKET
		self.KEY_CLOSEBRACKET = self.impl.KEY_CLOSEBRACKET
		self.KEY_ASTERISK = self.impl.KEY_ASTERISK
		self.KEY_PLUS = self.impl.KEY_PLUS
		self.KEY_MINUS = self.impl.KEY_MINUS
		self.KEY_COMMA = self.impl.KEY_COMMA
		self.KEY_DASH = self.impl.KEY_DASH
		self.KEY_PERIOD = self.impl.KEY_PERIOD
		self.KEY_FSLASH = self.impl.KEY_FSLASH
		self.KEY_BSLASH = self.impl.KEY_BSLASH
		self.KEY_DASH = self.impl.KEY_DASH
		self.KEY_SQUAREOPEN = self.impl.KEY_SQUAREOPEN
		self.KEY_SQUARECLOSE = self.impl.KEY_SQUARECLOSE
		self.KEY_CARET = self.impl.KEY_CARET
		self.KEY_UNDERSCORE = self.impl.KEY_UNDERSCORE
		self.KEY_BACKTICK = self.impl.KEY_BACKTICK
		self.KEY_CURLEYOPEN = self.impl.KEY_CURLEYOPEN
		self.KEY_CURLEYCLOSE = self.impl.KEY_CURLEYCLOSE
		self.KEY_PIPE = self.impl.KEY_PIPE
		self.KEY_TILDE = self.impl.KEY_TILDE
		self.KEY_UP = self.impl.KEY_UP
		self.KEY_DOWN = self.impl.KEY_DOWN
		self.KEY_LEFT = self.impl.KEY_LEFT
		self.KEY_RIGHT = self.impl.KEY_RIGHT
		self.KEY_DELETE = self.impl.KEY_DELETE
		self.KEY_ENTER = self.impl.KEY_ENTER
		self.KEY_SECTION = self.impl.KEY_SECTION
		self.KEY_PLUSMINUS = self.impl.KEY_PLUSMINUS
		self.KEY_F1 = self.impl.KEY_F1
		self.KEY_F2 = self.impl.KEY_F2
		self.KEY_F3 = self.impl.KEY_F3
		self.KEY_F4 = self.impl.KEY_F4
		self.KEY_F5 = self.impl.KEY_F5
		self.KEY_F6 = self.impl.KEY_F6
		self.KEY_F7 = self.impl.KEY_F7
		self.KEY_F8 = self.impl.KEY_F8
		self.KEY_F9 = self.impl.KEY_F9
		self.KEY_F10 = self.impl.KEY_F10
		self.KEY_F11 = self.impl.KEY_F11
		self.KEY_F12 = self.impl.KEY_F12
		self.KEY_AltF8 = self.impl.KEY_AltF8
		self.KEY_AltF9 = self.impl.KEY_AltF9
		self.KEY_AltF10 = self.impl.KEY_AltF10
		self.KEY_AltF11 = self.impl.KEY_AltF11
		self.KEY_AltF11 = self.impl.KEY_AltF11
		self.KEY_AltF12 = self.impl.KEY_AltF12

	def __call__(self): return self.impl()

class _GetchMac:
	def __init__(self):
		# General
		self.KEY_ESC = 27
		self.KEY_TAB = 9
		self.KEY_a = ord('a')
		self.KEY_b = ord('b')
		self.KEY_c = ord('c')
		self.KEY_d = ord('d')
		self.KEY_e = ord('e')
		self.KEY_f = ord('f')
		self.KEY_g = ord('g')
		self.KEY_h = ord('h')
		self.KEY_i = ord('i')
		self.KEY_j = ord('j')
		self.KEY_k = ord('k')
		self.KEY_l = ord('l')
		self.KEY_m = ord('m')
		self.KEY_n = ord('n')
		self.KEY_o = ord('o')
		self.KEY_p = ord('p')
		self.KEY_q = ord('q')
		self.KEY_r = ord('r')
		self.KEY_s = ord('s')
		self.KEY_t = ord('t')
		self.KEY_u = ord('u')
		self.KEY_v = ord('v')
		self.KEY_w = ord('w')
		self.KEY_x = ord('x')
		self.KEY_y = ord('y')
		self.KEY_z = ord('z')
		self.KEY_A = ord('A')
		self.KEY_B = ord('B')
		self.KEY_C = ord('C')
		self.KEY_D = ord('D')
		self.KEY_E = ord('E')
		self.KEY_F = ord('F')
		self.KEY_G = ord('G')
		self.KEY_H = ord('H')
		self.KEY_I = ord('I')
		self.KEY_J = ord('J')
		self.KEY_K = ord('K')
		self.KEY_L = ord('L')
		self.KEY_M = ord('M')
		self.KEY_N = ord('N')
		self.KEY_O = ord('O')
		self.KEY_P = ord('P')
		self.KEY_Q = ord('Q')
		self.KEY_R = ord('R')
		self.KEY_S = ord('S')
		self.KEY_T = ord('T')
		self.KEY_U = ord('U')
		self.KEY_V = ord('V')
		self.KEY_W = ord('W')
		self.KEY_X = ord('X')
		self.KEY_Y = ord('Y')
		self.KEY_Z = ord('Z')
		self.KEY_0 = ord('0')
		self.KEY_1 = ord('1')
		self.KEY_2 = ord('2')
		self.KEY_3 = ord('3')
		self.KEY_4 = ord('4')
		self.KEY_5 = ord('5')
		self.KEY_6 = ord('6')
		self.KEY_7 = ord('7')
		self.KEY_8 = ord('8')
		self.KEY_9 = ord('9')
		self.KEY_CTRLa = 1
		self.KEY_CTRLb = 2
		self.KEY_CTRLc = 3
		self.KEY_CTRLd = 4
		self.KEY_CTRLe = 5
		self.KEY_CTRLf = 6
		self.KEY_CTRLg = 7
		self.KEY_CTRLh = 8
		self.KEY_CTRLi = 9 #Sigh, that's a tab
		self.KEY_CTRLj = 10
		self.KEY_CTRLk = 11
		self.KEY_CTRLl = 12
		self.KEY_CTRLm = 13
		self.KEY_CTRLn = 14
		self.KEY_CTRLo = 15
		self.KEY_CTRLp = 16
		self.KEY_CTRLq = 17
		self.KEY_CTRLr = 18
		self.KEY_CTRLs = 19
		self.KEY_CTRLt = 20
		self.KEY_CTRLu = 21
		self.KEY_CTRLv = 22
		self.KEY_CTRLw = 23
		self.KEY_CTRLx = 24
		self.KEY_CTRLy = 25
		self.KEY_CTRLz = 26
		self.KEY_SPACE = ord(' ')
		self.KEY_BACKSPACE = 127
		self.KEY_BANG = ord('!')
		self.KEY_DOUBLEQUOTE = ord('"')
		self.KEY_HASH = ord('#')
		self.KEY_DOLLAR = ord('$')
		self.KEY_PERCENT = ord('%')
		self.KEY_QUOTE = ord("'")
		self.KEY_OPENBRACKET = ord('(')
		self.KEY_CLOSEBRACKET = ord(')')
		self.KEY_ASTERISK = ord('*')
		self.KEY_PLUS = ord('+')
		self.KEY_MINUS = ord('-')
		self.KEY_COMMA = ord(',')
		self.KEY_DASH = ord('-')
		self.KEY_PERIOD = ord('.')
		self.KEY_FSLASH = ord('/')
		self.KEY_BSLASH = ord('\\')
		self.KEY_DASH = ord('-')
		self.KEY_SQUAREOPEN = ord('[')
		self.KEY_SQUARECLOSE = ord(']')
		self.KEY_CARET = ord('^')
		self.KEY_UNDERSCORE = ord('_')
		self.KEY_BACKTICK = ord('`')
		self.KEY_CURLEYOPEN = ord('{')
		self.KEY_CURLEYCLOSE = ord('}')
		self.KEY_PIPE = ord('|')
		self.KEY_TILDE = ord('~')
		# Unix Specific
		self.KEY_UP = 113179
		self.KEY_DOWN = 114203
		self.KEY_LEFT = 116251
		self.KEY_RIGHT = 115227
		self.KEY_DELETE = 356891
		self.KEY_ENTER = 13
		self.KEY_F6 = 725531
		self.KEY_F7 = 727579
		self.KEY_F8 = 729627
		self.KEY_F9 = 712219
		self.KEY_F10 = 714267
		self.KEY_F11 = 718363
		self.KEY_F12 = 720411
		#OSX Specific
		# I have not gotten around to osx's Alt-SpecialChars
		self.KEY_SECTION = 85698
		self.KEY_PLUSMINUS = 90818
		self.KEY_F1 = 122395
		self.KEY_F2 = 123419
		self.KEY_F3 = 124443
		self.KEY_F4 = 125467
		self.KEY_F5 = 721435
		# AltF1-Alt-F7 = F6-F12
		self.KEY_AltF8 = 722459
		self.KEY_AltF9 = 724507
		self.KEY_AltF10 = 728603
		self.KEY_AltF11 = 730651
		self.KEY_AltF12 = 715291

	def __call__(self):
		def timeout_handler(signum, frame):
			raise TimeoutException()

		import sys, tty, termios
		fd = sys.stdin.fileno()
		old_settings = termios.tcgetattr(fd)
		try:
			tty.setraw(sys.stdin.fileno())
			tty.setcbreak(sys.stdin.fileno())
			ch0 = ord(sys.stdin.read(1))
			od = ch0
			#print ch0
			if od == 194: #mac section/plusminus key kludge
				ch1 = ord(sys.stdin.read(1))
				#print ch1
				od += ch1 * 512
			if od == 27: #special key
				# This is some horrible, kludge, upfu*kery but curses/tkinter won't work for my needs
				old_handler = signal.signal(signal.SIGALRM, timeout_handler) 
				signal.alarm(1)
				try:
					ch1 = ord(sys.stdin.read(1))
					#print ch1
					od += ch1 * 512
					ch2 = ord(sys.stdin.read(1))
					#print ch2
					od += ch2 * 1024
					pos = 2048
					if ch2 > 64 and ch2 < 69:
						pass
					elif ch1 == 91:
						while True:
							chx = ord(sys.stdin.read(1))
							#print chx
							od += chx * pos
							pos += pos
							if chx == 126:
								break
					signal.alarm(0)
				except TimeoutException:
					pass
				finally:
					signal.signal(signal.SIGALRM, old_handler) 
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
		return od

class _GetchUnix:
	def __init__(self):
		# General
		self.KEY_ESC = 27
		self.KEY_TAB = 9
		self.KEY_a = ord('a')
		self.KEY_b = ord('b')
		self.KEY_c = ord('c')
		self.KEY_d = ord('d')
		self.KEY_e = ord('e')
		self.KEY_f = ord('f')
		self.KEY_g = ord('g')
		self.KEY_h = ord('h')
		self.KEY_i = ord('i')
		self.KEY_j = ord('j')
		self.KEY_k = ord('k')
		self.KEY_l = ord('l')
		self.KEY_m = ord('m')
		self.KEY_n = ord('n')
		self.KEY_o = ord('o')
		self.KEY_p = ord('p')
		self.KEY_q = ord('q')
		self.KEY_r = ord('r')
		self.KEY_s = ord('s')
		self.KEY_t = ord('t')
		self.KEY_u = ord('u')
		self.KEY_v = ord('v')
		self.KEY_w = ord('w')
		self.KEY_x = ord('x')
		self.KEY_y = ord('y')
		self.KEY_z = ord('z')
		self.KEY_A = ord('A')
		self.KEY_B = ord('B')
		self.KEY_C = ord('C')
		self.KEY_D = ord('D')
		self.KEY_E = ord('E')
		self.KEY_F = ord('F')
		self.KEY_G = ord('G')
		self.KEY_H = ord('H')
		self.KEY_I = ord('I')
		self.KEY_J = ord('J')
		self.KEY_K = ord('K')
		self.KEY_L = ord('L')
		self.KEY_M = ord('M')
		self.KEY_N = ord('N')
		self.KEY_O = ord('O')
		self.KEY_P = ord('P')
		self.KEY_Q = ord('Q')
		self.KEY_R = ord('R')
		self.KEY_S = ord('S')
		self.KEY_T = ord('T')
		self.KEY_U = ord('U')
		self.KEY_V = ord('V')
		self.KEY_W = ord('W')
		self.KEY_X = ord('X')
		self.KEY_Y = ord('Y')
		self.KEY_Z = ord('Z')
		self.KEY_0 = ord('0')
		self.KEY_1 = ord('1')
		self.KEY_2 = ord('2')
		self.KEY_3 = ord('3')
		self.KEY_4 = ord('4')
		self.KEY_5 = ord('5')
		self.KEY_6 = ord('6')
		self.KEY_7 = ord('7')
		self.KEY_8 = ord('8')
		self.KEY_9 = ord('9')
		self.KEY_CTRLa = 1
		self.KEY_CTRLb = 2
		self.KEY_CTRLc = 3
		self.KEY_CTRLd = 4
		self.KEY_CTRLe = 5
		self.KEY_CTRLf = 6
		self.KEY_CTRLg = 7
		self.KEY_CTRLh = 8
		self.KEY_CTRLi = 9
		self.KEY_CTRLj = 10
		self.KEY_CTRLk = 11
		self.KEY_CTRLl = 12
		self.KEY_CTRLm = 13
		self.KEY_CTRLn = 14
		self.KEY_CTRLo = 15
		self.KEY_CTRLp = 16
		self.KEY_CTRLq = 17
		self.KEY_CTRLr = 18
		self.KEY_CTRLs = 19
		self.KEY_CTRLt = 20
		self.KEY_CTRLu = 21
		self.KEY_CTRLv = 22
		self.KEY_CTRLw = 23
		self.KEY_CTRLx = 24
		self.KEY_CTRLy = 25
		self.KEY_CTRLz = 26
		self.KEY_SPACE = ord(' ')
		self.KEY_BACKSPACE = 127
		self.KEY_BANG = ord('!')
		self.KEY_DOUBLEQUOTE = ord('"')
		self.KEY_HASH = ord('#')
		self.KEY_DOLLAR = ord('$')
		self.KEY_PERCENT = ord('%')
		self.KEY_QUOTE = ord("'")
		self.KEY_OPENBRACKET = ord('(')
		self.KEY_CLOSEBRACKET = ord(')')
		self.KEY_ASTERISK = ord('*')
		self.KEY_PLUS = ord('+')
		self.KEY_MINUS = ord('-')
		self.KEY_COMMA = ord(',')
		self.KEY_DASH = ord('-')
		self.KEY_PERIOD = ord('.')
		self.KEY_FSLASH = ord('/')
		self.KEY_BSLASH = ord('\\')
		self.KEY_DASH = ord('-')
		self.KEY_SQUAREOPEN = ord('[')
		self.KEY_SQUARECLOSE = ord(']')
		self.KEY_CARET = ord('^')
		self.KEY_UNDERSCORE = ord('_')
		self.KEY_BACKTICK = ord('`')
		self.KEY_CURLEYOPEN = ord('{')
		self.KEY_CURLEYCLOSE = ord('}')
		self.KEY_PIPE = ord('|')
		self.KEY_TILDE = ord('~')
		# Unix Specific
		self.KEY_UP = 113179
		self.KEY_DOWN = 114203
		self.KEY_LEFT = 116251
		self.KEY_RIGHT = 115227
		self.KEY_DELETE = 356891
		self.KEY_ENTER = 13
		#Linux Specific
		self.KEY_F1 = 272923
		self.KEY_F2 = 274971
		self.KEY_F3 = 277019
		self.KEY_F4 = 279061
		self.KEY_F5 = 281115
		self.KEY_F6 = 722531
		#Common
		self.KEY_F7 = 727579
		self.KEY_F8 = 729627
		self.KEY_F9 = 712219
		self.KEY_F10 = 714267
		self.KEY_F11 = 718363
		self.KEY_F12 = 720411
		#OSX Specific
		self.KEY_AltF8 = 0
		self.KEY_AltF9 = 0
		self.KEY_AltF10 = 0
		self.KEY_AltF11 = 0
		self.KEY_AltF12 = 0
		self.KEY_SECTION = 0
		self.KEY_PLUSMINUS = 0

	def __call__(self):
		def timeout_handler(signum, frame):
			raise TimeoutException()

		import sys, tty, termios
		fd = sys.stdin.fileno()
		old_settings = termios.tcgetattr(fd)
		try:
			tty.setraw(sys.stdin.fileno())
			tty.setcbreak(sys.stdin.fileno())
			ch0 = ord(sys.stdin.read(1))
			od = ch0
			#print ch0
			if od == 194: #mac section/plusminus key kludge
				ch1 = ord(sys.stdin.read(1))
				#print ch1
				od += ch1 * 512
			if od == 27: #special key
				# This is some horrible, kludge, upfu*kery but curses/tkinter won't work for my needs
				old_handler = signal.signal(signal.SIGALRM, timeout_handler) 
				signal.alarm(1)
				try:
					ch1 = ord(sys.stdin.read(1))
					#print ch1
					od += ch1 * 512
					ch2 = ord(sys.stdin.read(1))
					#print ch2
					od += ch2 * 1024
					pos = 2048
					if ch2 > 64 and ch2 < 69:
						pass
					elif ch1 == 91:
						while True:
							chx = ord(sys.stdin.read(1))
							#print chx
							od += chx * pos
							pos += pos
							if chx == 126:
								break
					signal.alarm(0)
				except TimeoutException:
					od = od
				finally:
					signal.signal(signal.SIGALRM, old_handler) 
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
		return od

class _GetchWindows:
	def __init__(self):
		self.KEY_UP = 0 #todo

	def __call__(self):
		import msvcrt
		return msvcrt.getch()

getch = _Getch()
