#!/usr/bin/env python

from py3270 import EmulatorBase,CommandError,FieldTruncateError
import os
import time
import sys 
import argparse
import re
import platform
from colorama import Fore,Back,Style,init
from datetime import datetime
from IPython import embed
from getch import getch
import pickle

#todo DOM search
#todo build replay

# Object to hold field details
class tn3270_Field:
	def __init__(self, contents, row, col, rawstatus, printable=0, protected=0, numeric=0, hidden=0, normnsel=0, normsel=0, highsel=0, zeronsel=0, reserved=0, modify=0):
		self.contents = contents
		self.row = row
		self.col = col
		self.rawstatus = rawstatus
		self.printable = printable
		self.protected = protected
		self.numeric = numeric
		self.hidden = hidden
		self.normnsel = normnsel
		self.normsel = normsel
		self.highsel = highsel
		self.zeronsel = zeronsel
		self.reserved = reserved
		self.modify = modify

	def __repr__(self):
		a = "<tn3270_Field row:",`self.row`," col:",`self.col`," contents:",self.contents.strip(),">"
		return ''.join(a)

	def __str__(self):
		return self.contents

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
	def __str__(self):
		return '\n'.join(self.stringbuffer).replace('\x00',' ')

	def __repr__(self):
		a = "<tn3270_Screen rows:",`self.rows`," cols:",`self.cols`," firstline:",self.stringbuffer[0],">"
		return ''.join(a)

	@property
	# Highlight different fields so we can see what is really going on on the screen
	# This looks at field markers only and ignores colours asked for by the host
	def colorbuffer(self):
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

	@property
	# Return a DOM of sorts with each field and it's characteristics
	def fields(self):
		field_list = list()
		row = 0
		for line in self.rawbuffer:
			col = 0
			for i in line.split(' '):
				# SF(c0=c8) is example of StartField markup
				if len(i) > 3 and i.find('SF(') >= 0:
					attrib = int(i[3:5],16)
					val = int(i[6:8],16)

					printable = 0
					protected = 0
					numeric = 0
					hidden = 0
					normnsel = 0
					normsel = 0
					highsel = 0
					zeronsel = 0
					reserved = 0
					modify = 0
					rawstatus = i #store the raw status for later implementation of SA()
					if (val | self.FA_PRINTABLE) == val:
						printable = 1
					if (val | self.FA_PROTECT ) == val:
						protected = 1
					if (val | self.FA_NUMERIC ) == val:
						numeric = 1
					if (val | self.FA_HIDDEN) == val:
						hidden = 1
					if (val | self.FA_INT_NORM_NSEL) == val:
						normnsel = 1
					if (val | self.FA_INT_NORM_SEL) == val:
						normsel = 1
					if (val | self.FA_INT_HIGH_SEL) == val:
						highsel = 1
					if (val | self.FA_INT_ZERO_NSEL) == val:
						zeronsel = 1
					if (val | self.FA_RESERVED) == val:
						reserved = 1
					if (val | self.FA_MODIFY) == val:
						modify = 1

					field = tn3270_Field('', row, col, rawstatus, printable, protected, numeric, hidden, normnsel, normsel, highsel, zeronsel, reserved, modify)
					field_list.append(field)

				# Add the character to the last field entity added
				elif len(i) == 2:
					contents = i.decode("hex")
					field_list[len(field_list)-1].contents += contents

				col += 1
			row += 1
		return field_list

	def protected_fields(self):
		return filter(lambda x: x.protected == 1, self.fields)

	def input_fields(self):
		return filter(lambda x: x.protected == 0, self.fields)

	def hidden_fields(self):
		return filter(lambda x: x.hidden == 1, self.fields)

	def modified_fields(self):
		return filter(lambda x: x.modify == 1, self.fields)

# Object to hold an single tn3270 "transaction" i.e. request/response & timestamp
class tn3270_Transaction:
	def __init__(self, request, response, data, key='enter', host='', comment=''):
		# these should be tn3270_Screen objects
		self.request = request
		self.response = response 
		self.data = data #Data that was submitted
		# For now I'm going to assume the last item in the list is the newest
		self.timestamp = datetime.now()
		# What key initiated the transaction
		self.key = key
		self.comment = comment
		self.host = host

	def __repr__(self):
		a = "<tn3270_Transaction time:",str(self.timestamp)," host:",self.host,\
				" trigger:",self.key,"\n",\
				" Req : ",repr(self.request),"\n",\
				" Data: ",repr(self.data),"\n",\
				" Resp: ",repr(self.response),">"
		return ''.join(a)

class tn3270_History:
	def __init__(self):
		self.timeline = list()

	def __getitem__(self, index):
		return self.timeline[index]

	def __repr__(self):
		return "<tn3270_History timeline:\n"+repr(self.timeline)

	def __len__(self):
		return len(self.timeline)

	def append(self, transaction):
		self.timeline.append(transaction)

	def last(self):
		return self.timeline[len(self.timeline)-1]

	def count(self):
		return len(self.timeline)

def compare_screen(screen1,screen2,exact=False):
	diffcount = 0
	linecount = 0
	for line in screen1.rawbuffer:
		if screen1.rawbuffer[linecount] != screen2.rawbuffer[linecount]:
			diffcount += 1
			if exact:
				return 0
			elif diffcount > 2:
				return 0 #More than two lines different they're different
	return True #screens are the same
	
# Send text without triggering field protection
def safe_send(em, text):
	for i in xrange(0,len(text)):
		em.send_string(text[i])
		if em.status.field_protection == 'P':
			return False #We triggered field protection, stop
	return True #Safe

# Fill fields in carefully, checking for triggering field protections
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
def update_screen(em,screen):
	screen = tn3270_Screen(em.exec_command('ReadBuffer(Ascii)').data)
	return screen

# Record the current screen, hit enter, and record the response
def exec_trans(em,history,key='enter'):
	request = tn3270_Screen
	response = tn3270_Screen
	request = update_screen(em,request)
	keypress = ''
	hostinfo = em.exec_command('Query(Host)').data[0].split(' ')
	host = hostinfo[1]+':'+hostinfo[2]
	data = request.modified_fields()
	if key == 'enter':
		em.send_enter()
		keypress = key
	#PF1=1, PF24=24, PA1=25, PA3=27
	elif key > 0 and key < 25: 
		keypress = 'PF(' + str(key) + ')'
		em.exec_command(keypress)
	elif key > 25 and key < 28:
		keypress = 'PA(' + str(key - 24) + ')'
		em.exec_command(keypress)
	response = update_screen(em,response)
	trans = tn3270_Transaction(request,response,data,keypress,host)
	history.append(trans)
	return trans

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
	
def get_pos(em):
	results = em.exec_command('Query(Cursor)')
	row = int(results.data[0].split(' ')[0])
	col = int(results.data[0].split(' ')[1])
	return (row,col)

# Interactive mode, will record transactions, and display hacker view companion
def interactive(em,history):
	key = ''
	trans = ''
	screen = ''
	data = ''
	while key != getch.KEY_ESC:
		key = getch()

		if key == getch.KEY_UP: #Up
			em.exec_command('Up()')
		elif key == getch.KEY_DOWN: #Down
			em.exec_command('Down()')
		elif key == getch.KEY_LEFT: #Left
			em.exec_command('Left()')
		elif key == getch.KEY_RIGHT: #Right
			em.exec_command('Right()')
		elif key == getch.KEY_ENTER: #Enter
			trans = exec_trans(em,history,'enter')
			print trans.response.colorbuffer
			logger('Enter entered',kind='info')
		elif key == getch.KEY_CTRLr: #Ctrl-r print screen
			screen = update_screen(em,screen)
			print screen.colorbuffer
			logger('Screen refreshed',kind='info')
		elif key == getch.KEY_CTRLu: #Ctrl-u manually push transaction
			screen = update_screen(em,screen)
			data = screen.modified_fields()
			hostinfo = em.exec_command('Query(Host)').data[0].split(' ')
			host = hostinfo[1]+':'+hostinfo[2]
			trans = tn3270_Transaction(history.last().response,screen,data,'manual',host)
			history.append(trans)
			print screen.colorbuffer
			logger('Transaction added',kind='info')
		elif key == getch.KEY_TAB: #Tab 9
			em.exec_command('Tab()')
		elif key == getch.KEY_BACKSPACE: #Backspace
			em.exec_command('BackSpace()')
		elif key == getch.KEY_DELETE: #Delete
			em.exec_command('Delete()')
		elif key == getch.KEY_CTRLc: #Ctrl-c Clear
			em.exec_command('Clear()')
		elif key == getch.KEY_CTRLq: #Ctrl-q PA1
			trans = exec_trans(em,history,25)
			print trans.response.colorbuffer
		elif key == getch.KEY_CTRLw: #Ctrl-w PA2
			trans = exec_trans(em,history,26)
			print trans.response.colorbuffer
		elif key == getch.KEY_CTRLe: #Ctrl-e PA3
			trans = exec_trans(em,history,27)
			print trans.response.colorbuffer
		elif key > 31 and key < 127: #Alphanumeric
			safe_send(em, chr(key))
		elif key == getch.KEY_F1:
			trans = exec_trans(em,history,1)
			print trans.response.colorbuffer
		elif key == getch.KEY_F2:
			trans = exec_trans(em,history,2)
			print trans.response.colorbuffer
		elif key == getch.KEY_F3:
			trans = exec_trans(em,history,3)
			print trans.response.colorbuffer
		elif key == getch.KEY_F4:
			trans = exec_trans(em,history,4)
			print trans.response.colorbuffer
		elif key == getch.KEY_F5:
			trans = exec_trans(em,history,5)
			print trans.response.colorbuffer
		elif key == getch.KEY_F6:
			trans = exec_trans(em,history,6)
			print trans.response.colorbuffer
		elif key == getch.KEY_F7:
			trans = exec_trans(em,history,7)
			print trans.response.colorbuffer
		elif key == getch.KEY_F8:
			trans = exec_trans(em,history,8)
			print trans.response.colorbuffer
		elif key == getch.KEY_F9:
			trans = exec_trans(em,history,9)
			print trans.response.colorbuffer
		elif key == getch.KEY_F10:
			trans = exec_trans(em,history,10)
			print trans.response.colorbuffer
		elif key == getch.KEY_F11:
			trans = exec_trans(em,history,11)
			print trans.response.colorbuffer
		elif key == getch.KEY_F12:
			trans = exec_trans(em,history,12)
			print trans.response.colorbuffer
		elif key == getch.KEY_AltF8:
			trans = exec_trans(em,history,13)
			print trans.response.colorbuffer
		elif key == getch.KEY_AltF9:
			trans = exec_trans(em,history,14)
			print trans.response.colorbuffer
		elif key == getch.KEY_AltF10:
			trans = exec_trans(em,history,15)
			print trans.response.colorbuffer
		elif key == getch.KEY_AltF11:
			trans = exec_trans(em,history,16)
			print trans.response.colorbuffer
		elif key == getch.KEY_AltF12:
			trans = exec_trans(em,history,24)
			print trans.response.colorbuffer

def connect_zOS(em, target):
	logger('Connecting to ' + results.target,kind='info')
	try:
		em.connect(target)
	except:
		logger('Connection failure',kind='err')
		sys.exit(1)
	if not em.is_connected():
		logger('Could not connect to ' + results.target + '. Aborting.',kind='err')
		sys.exit(1)

def list_trans(history):
	print Fore.BLUE,"Transaction List\n",Fore.RESET
	print Fore.BLUE,"================\n",Fore.RESET
	count = 0
	for trans in history:
		print Fore.BLUE,count,trans.timestamp,Fore.CYAN,trans.key,\
					"\t",Fore.BLUE,trans.host,trans.comment,Fore.RESET
		print "  Req : ",trans.request.stringbuffer[0]
		for field in trans.data:
			print "  Data: row:",field.row,"col:",field.col,"str:",Fore.RED,field.contents,Fore.RESET
		print "  Resp: ",trans.response.stringbuffer[0]
		print ""
		count += 1

def save_history(history,savefile):
	if os.path.exists(savefile):
		logger('Savefile exists, I won\'t overwrite yet',kind='err')
		return 1 #Don't overwrite existing saves just yet
	sav = open(savefile,'w')
	pickle.dump(history, sav)
	sav.close()
	return 0

def load_history(loadfile):
	lod = open(loadfile,'r')
	hist = pickle.load(lod)
	lod.close()
	return hist

# Set the emulator intelligently based on your platform
if platform.system() == 'Darwin':
	class Emulator(EmulatorIntermediate):
		x3270_executable = '/Users/singe/manual-install/x3270-hack/x3270'
elif platform.system() == 'Linux':
	class Emulator(EmulatorIntermediate):
		x3270_executable = '/usr/bin/x3270' #comment this line if you do not wish to use x3270 on Linux
elif platform.system() == 'Windows':
	class Emulator(EmulatorIntermediate):
		x3270_executable = 'Windows_Binaries/wc3270.exe'
else:
	logger('Your Platform:', platform.system(), 'is not supported at this time.',kind='err')
	sys.exit(1)

init() # initialise coloured output from colorama

# Define and fetch commandline arguments
parser = argparse.ArgumentParser(description='z/OS Mainframe Screenshotter', epilog='Get to it!')
parser.add_argument('-t', '--target', help='Target IP address or Hostname and port: TARGET[:PORT] default port is 23', required=True, dest='target')
parser.add_argument('-s', '--sleep', help='Seconds to sleep between actions (increase on slower systems). The default is 0 seconds.', default=0, type=float, dest='sleep')
parser.add_argument('-q', '--quiet', help='Ssssh', default=False, dest='quiet', action='store_true')
results = parser.parse_args()

# Parse commandline arguments
logger('Big Iron Recon & Pwnage (BIRP)',kind='info')
logger('Target Acquired\t\t: ' + results.target,kind='info')
logger('Slowdown is\t\t\t: ' + str(results.sleep),kind='info')
logger('Attack platform\t\t: ' + platform.system(),kind='info')

if not platform.system() == 'Windows':
	em = Emulator(visible=True)
elif platform.system() == 'Windows':
	logger('x3270 not supported on Windows',kind='err')
	sys.exit(1)
if results.quiet:
	logger('Quiet Mode Enabled\t: Shhhhhhhhh!',kind='warn')

connect_zOS(em,results.target) #connect to the host
hostinfo = em.exec_command('Query(Host)').data[0].split(' ')
host = hostinfo[1]+':'+hostinfo[2]
history = tn3270_History()

embed() # Start IPython shell

# And we're done. Close the connection
em.terminate()
