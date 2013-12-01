#!/usr/bin/env python

from py3270 import EmulatorBase,CommandError,FieldTruncateError
import tn3270
import sys 
import argparse
import re
import platform
from time import sleep
from os import path
from colorama import Fore,Back,Style,init
from IPython import embed
from getch import getch
import pickle

#todo DOM search
#todo build replay
#todo menu

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
				sleep(results.sleep)
				results.sleep += 1
				whine('Read error encountered, assuming host is slow, increasing delay by 1s to: ' + str(results.sleep),kind='warn')
				return False
	return False

# Update a screen object with the latest x3270 screen	
def update_screen(em,screen):
	screen = tn3270.Screen(em.exec_command('ReadBuffer(Ascii)').data)
	return screen

# Record the current screen, hit enter, and record the response
def exec_trans(em,history,key='enter'):
	request = tn3270.Screen
	response = tn3270.Screen
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
	trans = tn3270.Transaction(request,response,data,keypress,host)
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
			sleep(results.sleep)

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
			trans = tn3270.Transaction(history.last().response,screen,data,'manual',host)
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
	if path.exists(savefile):
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
history = tn3270.History()

embed() # Start IPython shell

# And we're done. Close the connection
em.terminate()
