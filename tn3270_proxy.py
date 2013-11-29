#!/usr/bin/env python

from py3270 import EmulatorBase,CommandError,FieldTruncateError
import time
import sys 
import argparse
import re
import platform
from colorama import Fore,Back,Style,init
from datetime import datetime
from IPython import embed
import curses

#todo add fields DoM-style object to the Screen structure
#todo build a request & response obj to hold screens
#todo store lots of req/responses with other pertinent info in a list, serialise to file
#todo build replay

# Object to hold a screen from x3270
class tn3270_Screen:
	def __init__(self, rawbuff):
		self.rawbuffer = rawbuff
		self.rows = len(self.rawbuffer)
		self.cols = len(self.rawbuffer[0])
		#From x3270 defines
		self.FA_PRINTABLE = 0xc0 #these make the character "printable"
		self.FA_PROTECT = 0x20 #unprotected (0) / protected (1)
		self.FA_NUMERIC = 0x10 #alphanumeric (0) /numeric (1)Skip?
		self.FA_HIDDEN = 0x0c #display/selector pen detectable:
		self.FA_INT_NORM_NSEL = 0x00 # 00 normal, non-detect
		self.FA_INT_NORM_SEL = 0x04 # 01 normal, detectable
		self.FA_INT_HIGH_SEL = 0x08 # 10 intensified, detectable
		self.FA_INT_ZERO_NSEL = 0x0c # 11 nondisplay, non-detect
		self.FA_RESERVED = 0x02 #must be 0
		self.FA_MODIFY = 0x01 #modified (1)
		
	@property
	# Dump the hex without the field & formatting markers
	def plainbuffer(self):
		plnbuf = list()
		for line in self.rawbuffer:
			splitline = line.split(' ')
			plainline = [i for i in splitline if len(i) == 2]
			plnbuf.append(plainline)
		return plnbuf

	@property
	# Give us a string version of plainbuffer
	def stringbuffer(self):
		strbuf = list()
		for line in self.plainbuffer:
			newstr = ''.join(line).decode("hex")
			strbuf.append(newstr)
		return strbuf

	# A pretty printed version converting NULL to ' '
	def tostring(self):
		return '\n'.join(bar.stringbuffer).replace('\x00',' ')

	@property
	# Highlight different fields so we can see what is really going on on the screen
	# This looks at field markers only and ignores colours asked for by the host
	def colourbuffer(self):
		colbuf = list()
		colbuf.append(Fore.RED) #Highlight unfield'ed text
		for line in self.rawbuffer:
			newline = list()
			for i in line.split(' '):
				# SF(c0=c8) is example of StartField markup
				if len(i) > 3 and i.find('SF(') >= 0:
					attrib = int(i[3:5],16)
					val = int(i[6:8],16)
					if (val | self.FA_PROTECT | self.FA_HIDDEN | self.FA_NUMERIC) == val:
						#hidden protected field - Green on Red
						newline.append(Back.RED+Fore.GREEN+Style.NORMAL)
					elif (val | self.FA_PROTECT | self.FA_NUMERIC) == val:
						#protected & numeric/skip - Clear
						newline.append(Back.RESET+Fore.RESET+Style.NORMAL)
					elif (val | self.FA_PROTECT | self.FA_INT_HIGH_SEL) == val:
						#protected & intense  - White on Clear
						newline.append(Back.RESET+Fore.WHITE+Style.BRIGHT)
					elif (val | self.FA_PROTECT | self.FA_MODIFY) == val:
						#protected & modified? - Magenta on Red
						#Fore will be overwritten by global modified check below
						newline.append(Back.RED+Fore.MAGENTA+Style.NORMAL)
					elif (val | self.FA_PROTECT) == val:
						#labels - Blue on Clear
						newline.append(Back.RESET+Fore.BLUE+Style.NORMAL)
					elif (val | self.FA_INT_HIGH_SEL) == val or (val | self.FA_INT_NORM_SEL) == val:
						#normal input field - Red on Green
						newline.append(Back.GREEN+Fore.RED+Style.NORMAL)
					elif (val | self.FA_HIDDEN) == val or (val | self.FA_INT_NORM_NSEL) == val or (val | self.FA_INT_ZERO_NSEL) == val:
						#hidden unprotected input field - Blue on Green
						newline.append(Back.GREEN+Fore.BLUE+Style.NORMAL)

					if (val | self.FA_MODIFY) == val:
						#modified text - Purple on Existing
						newline.append(Fore.MAGENTA)

					newline.append(u'\u2219') #Field marker

				elif len(i) == 2:
					if i == '00':
						newline.append(u"\u2400")
					else:
						newline.append(i.decode("hex"))
			#newline.append(Fore.RESET+Back.RESET)
			colbuf.append(''.join(newline))
		strcolbuf = '\n'.join(colbuf) + Fore.RESET + Back.RESET
		return strcolbuf

# Object to hold an single tn3270 "transaction" i.e. request/response & timestamp
class tn3270_Transaction:
	def __init__(self, request, response):
		# these should be tn3270_Screen objects
		self.request = request
		self.response = response
		# For now I'm going to assume the last item in the list is the newest
		self.timestamp = datetime.now()
	
class tn3270_History:
	def __init__(self):
		self.timeline = list()

	def append(self, transaction):
		self.timeline.append(transaction)
	
# Send text without triggering field protection
def safe_send(em, text):
	for i in xrange(0,len(text)):
		em.send_string(text[i])
		if em.status.field_protection == 'P':
			return False #We triggered field protection, stop
	return True #Safe

def safe_fieldfill(em, ypos, xpos, tosend, length):
	if length - len(tosend) < 0:
		raise FieldTruncateError('length limit %d, but got "%s"' % (length, tosend))
	if xpos is not None and ypos is not None:
		em.move_to(ypos, xpos)
	try:
		em.delete_field()
		if safe_send(em, tosend):
			return True #Hah, we win, take that mainframe
		else:
			return False #we entered what we could, bailing
	except CommandError, e:
		# We hit an error, get mad
		return False
		#if str(e) == 'Keyboard locked':

# Search the screen for text when we don't know exactly where it is, checking for read errors
def find_response(em, response):
	for rows in xrange(1,int(em.status.row_number)+1):
		for cols in xrange(1,int(em.status.col_number)+1-len(response)):
			try:
				if em.string_found(rows, cols, response):
					return True
			except CommandError, e:
				# We hit a read error, usually because the screen hasn't returned
				# increasing the delay works
				time.sleep(results.sleep)
				results.sleep += 1
				whine('Read error encountered, assuming host is slow, increasing delay by 1s to: ' + str(results.sleep),kind='warn')
				return False
	return False

# Update a screen object with the latest x3270 screen	
def updateScreen(em,screen):
	screen = tn3270_Screen(em.exec_command('ReadBuffer(Ascii)').data)
	return screen

# Record the current screen, hit enter, and record the response
def executeTrans(em,history):
	request = UpdateScreen(em,response)
	em.send_enter()
	response = UpdateScreen(em,response)
	trans = tn3270_Transaction(request,response)
	history.append(trans)

# Print output that can be surpressed by a CLI opt
def logger(text, kind='clear', level=0):
	if results.quiet and (kind == 'warn' or kind == 'info'):
			return
	else:
		typdisp = ''
		lvldisp = ''
		if kind == 'warn': typdisp = '[!] '
		elif kind == 'info': typdisp = '[+] '
		elif kind == 'err': typdisp = '[#] '
		elif kind == 'good': typdisp = '[*] '
		if level == 1: lvldisp = "\t"
		elif level == 2: lvldisp = "\t\t"
		elif level == 3: lvldisp = "\t\t\t"
		print lvldisp+typdisp+text

# Override some behaviour of py3270 library
class EmulatorIntermediate(EmulatorBase):
	def send_enter(self): #Allow a delay to be configured
		self.exec_command('Enter')
		if results.sleep > 0:
			time.sleep(results.sleep)

	def screen_get(self):
		response = self.exec_command('Ascii()')
		return response.data
	
# Set the emulator intelligently based on your platform
if platform.system() == 'Darwin':
	class Emulator(EmulatorIntermediate):
		x3270_executable = '/Users/singe/manual-install/x3270-hack/x3270'
		s3270_executable = 'MAC_Binaries/s3270'
elif platform.system() == 'Linux':
	class Emulator(EmulatorIntermediate):
		x3270_executable = '/usr/bin/x3270' #comment this line if you do not wish to use x3270 on Linux
		s3270_executable = '/usr/bin/s3270'
elif platform.system() == 'Windows':
	class Emulator(EmulatorIntermediate):
		#x3270_executable = 'Windows_Binaries/wc3270.exe'
		s3270_executable = 'Windows_Binaries/ws3270.exe'
else:
	logger('Your Platform:', platform.system(), 'is not supported at this time.',kind='err')
	sys.exit(1)

def getPos(em):
	results = em.exec_command('Query(Cursor)')
	row = int(results.data[0].split(' ')[0])
	col = int(results.data[0].split(' ')[1])
	return (row,col)

def interactive(em,history):
	stdscr = curses.initscr()
	curses.cbreak()
	stdscr.keypad(1)
	curses.raw()
	pos = (0,0)
	row = 0
	col = 0
	
	#stdscr.addstr(0,10,"Hit ESC to quit")
	stdscr.refresh()

	key = ''
	while key != 27:
		key = stdscr.getch()
		#stdscr.refresh()
		if key == curses.KEY_UP: 
			pos = getpos(em)
			#row = pos[0]-1
			#col = pos[1]
			#em.exec_command('MoveCursor('+str(row)+','+str(col)+')')
			em.exec_command('Up()')
		elif key == curses.KEY_DOWN: 
			em.exec_command('Down()')
		elif key == curses.KEY_LEFT: 
			em.exec_command('Left()')
		elif key == curses.KEY_RIGHT: 
			em.exec_command('Right()')
		#elif key == curses.KEY_ENTER: # 343 != 10, may be OS specific
		elif key == ord('\n'): #Enter 10
			#em.send_enter()
			executeTrans(em,history)
		elif key == ord('	'): #Tab 9
			em.exec_command('Tab()')
		elif key == 8: #Backspace
			em.exec_command('BackSpace()')
		elif key == 127: #Delete
			em.exec_command('Delete()')
		elif key == 3: #Ctrl-c
			em.exec_command('Clear()')
		elif key == 17: #Ctrl-q
			em.exec_command('#PA(1)')
		elif key == 23: #Ctrl-w
			em.exec_command('#PA(2)')
		elif key == 5: #Ctrl-e
			em.exec_command('#PA(3)')
		elif key > 31 and key < 127: #Alphanumeric
			safe_send(em, chr(key))
		elif key > 264 and key < 289: #Send PFn key
			fkey = key - 264
			em.exec_command('#PF('+str(fkey)+')')
	
	curses.endwin()

def connect_zOS(em, target):
	logger('Connecting to ' + results.target,kind='info')
	em.connect(target)

	if not em.is_connected():
		logger('Could not connect to ' + results.target + '. Aborting.',kind='err')
		sys.exit(1)

init() # initialise coloured output from colorama

# Define and fetch commandline arguments
parser = argparse.ArgumentParser(description='z/OS Mainframe Screenshotter', epilog='Get to it!')
parser.add_argument('-t', '--target', help='Target IP address or Hostname and port: TARGET[:PORT] default port is 23', required=True, dest='target')
parser.add_argument('-s', '--sleep', help='Seconds to sleep between actions (increase on slower systems). The default is 0 seconds.', default=0, type=float, dest='sleep')
parser.add_argument('-m', '--moviemode', help='Enables ULTRA AWESOME Movie Mode. Watch the system get hacked in real time!', default=False, dest='movie_mode', action='store_true')
parser.add_argument('-q', '--quiet', help='Only display found users / found passwords', default=False, dest='quiet', action='store_true')
results = parser.parse_args()

# Parse commandline arguments
logger('z/OS Mainframe Screenshotter',kind='info')
logger('Target Acquired\t\t: ' + results.target,kind='info')
logger('Slowdown is\t\t\t: ' + str(results.sleep),kind='info')
logger('Attack platform\t\t: ' + platform.system(),kind='info')

if results.movie_mode and not platform.system() == 'Windows':
	logger('ULTRA Hacker Movie Mode\t: Enabled',kind='info')
	#Enables Movie Mode which uses x3270 so it looks all movie like 'n shit
	em = Emulator(visible=True)
elif results.movie_mode and platform.system() == 'Windows':
	logger('ULTRA Hacker Movie Mode not supported on Windows',kind='warn')
	em = Emulator()
else:
	logger('ULTRA Hacker Movie Mode\t: Disabled',kind='info')
	em = Emulator()
if results.quiet:
	logger('Quiet Mode Enabled\t: Shhhhhhhhh!',kind='warn')

connect_zOS(em,results.target) #connect to the host
history = tn3270_History

embed() # Start IPython shell

# And we're done. Close the connection
em.terminate()
