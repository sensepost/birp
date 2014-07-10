#!/usr/bin/env python

from py3270wrapper import WrappedEmulator
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
from pprint import pprint
from encodings import utf_8

# Big Iron Recon & Pwnage (BIRP) is a TN3270 z/OS application assessment tool.
# Written by Dominic White (@singe) at SensePost
# It's homepage is available at https://github.com/sensepost/birp

# Big Iron Recon & Pwnage by SensePost is licensed under a Creative Commons
# Attribution-ShareAlike 4.0 International License. Permissions beyond the
# scope of this license may be available at http://sensepost.com/contact us/.

# todo allow field marker edits
# todo build replay
# todo intruder functionality

# Menus are here because folds don't like them
menu_list = "\nBIRP Menu\n\
=========\n\n\
1 - Interactive Mode\n\
2 - View History\n\
3 - Find Transaction\n\
4 - Python Console\n\
5 - Save History\n\
X - Quit\n\n\
Selection: "

interactive_help = "\nInteractive mode help\n\
=====================\n\n\
Hit ESC to exit interactive mode.\n\n\
Most keys will be passed directly to x3270. Except:\n\
Ctrl-c		- Clear\n\
Ctrl-q/w/e	- PA1, PA2, PA3\n\
Ctrl-r		- Re-print the markedup view of the current screen\n\
Ctrl-u		- Manually push the last interaction as a transaction\n\
Ctrl-p		- Drop to Python interactive shell\n\
Ctrl-s		- Create timestampe'd HTML file of the current screen\n\
Ctrl-k		- Color key\n\
Ctrl-h		- This help\n\
Alt-F8-11	- PF13-16\n\
Alt-F12		- PF24\n\n\
Hitting Enter, any of the PF/PA keys, or Ctrl-u will record a transaction."

color_key = u"\nColor Key\n\
=========\n\n\
\u2219\t\t\t- Start of field marker" + Style.RESET_ALL + "\n\
Hidden Fields\t\t- " + Back.RED + "Red background" + Style.RESET_ALL + "\n\
Modified Fields\t\t- " + Fore.YELLOW + "Yellow text" + Style.RESET_ALL + "\n\
Input Fields\t\t- " + Back.GREEN + "Green background" + Style.RESET_ALL + "\n\
"
#Intensified Fields\t- " + Style.BRIGHT + "Bright text" + Style.RESET_ALL + "\n\

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

# Update a screen object with the latest x3270 screen	
def update_screen(em,screen):
	screen = tn3270.Screen(em.exec_command('ReadBuffer(Ascii)').data)
	return screen

# Record the current screen, hit enter, and record the response
def exec_trans(em,history,key='enter'):
	request = tn3270.Screen
	response = tn3270.Screen
	check = tn3270.Screen
	request = update_screen(em,request)
	keypress = ''
	hostinfo = em.exec_command('Query(Host)').data[0].split(' ')
	host = hostinfo[1]+':'+hostinfo[2]
	data = request.modified_fields
	if key == 'enter':
		em.send_enter()
		keypress = key
	# PF1=1, PF24=24, PA1=25, PA3=27
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

# Compare two screens, allow a "fuzzy" match to account for time/terminal fields
def compare_screen(screen1,screen2,exact=False):
	diffcount = 0
	linecount = 0
	for line in screen1.rawbuffer:
		if screen1.rawbuffer[linecount] != screen2.rawbuffer[linecount]:
			diffcount += 1
			if exact:
				return 0
			elif diffcount > 2:
				return 0 # More than two lines different they're different
	return True # screens are the same
	
# Currently unused
def find_first(history,text):
	transid = 0
	row = 0
	rr = 0
	col = 0
	for trans in history:
		row = 0
		# Check the request
		for line in trans.request.stringbuffer:
			rr = 0
			col = line.find(text)
			if col >= 0:
				return (transid,rr,row,col)
			row += 1
		row = 0
		# Check the response
		for line in trans.response.stringbuffer:
			rr = 1
			col = line.find(text)
			if col >= 0:
				return (transid,rr,row,col)
			row += 1
		transid += 1
	return (-1,-1,-1,-1) # Not found

# Find text within the transaction history
def find_all(history,text):
	result = list()
	transid = 0
	row = 0
	rr = 0
	col = 0
	for trans in history:
		row = 0
		# Check the request
		for line in trans.request.stringbuffer:
			rr = 0
			col = line.find(text)
			if col >= 0:
				result.append((transid,rr,row,col))
			row += 1
		row = 0
		# Check the response
		for line in trans.response.stringbuffer:
			rr = 1
			col = line.find(text)
			if col >= 0:
				result.append((transid,rr,row,col))
			row += 1
		transid += 1
	return result

# Interactive mode, will record transactions, and display hacker view companion
def interactive(em,history):
	if not em.is_connected():
		logger(Fore.RED+"Emulator not connected, interactive mode prevented."+Fore.RESET,kind="err")
		return
	key = ''
	trans = ''
	screen = ''
	data = ''
	logger("Interactive mode started! Hit ESC to exit",kind="info")
	logger("Hit Ctrl-h for help. Start typing ...",kind="info")
	while key != getch.KEY_ESC:
		key = getch()

		if key == getch.KEY_UP: # Up
			em.exec_command('Up()')
		elif key == getch.KEY_DOWN: # Down
			em.exec_command('Down()')
		elif key == getch.KEY_LEFT: # Left
			em.exec_command('Left()')
		elif key == getch.KEY_RIGHT: # Right
			em.exec_command('Right()')
		elif key == getch.KEY_ENTER: # Enter
			trans = exec_trans(em,history,'enter')
			print trans.response.colorbuffer
			logger('Enter entered',kind='info')
		elif key == getch.KEY_CTRLr: # Ctrl-r print screen
			screen = update_screen(em,screen)
			print screen.colorbuffer
			logger('Screen refreshed',kind='info')
		elif key == getch.KEY_CTRLu: # Ctrl-u manually push transaction
			screen = update_screen(em,screen)
			data = screen.modified_fields
			hostinfo = em.exec_command('Query(Host)').data[0].split(' ')
			host = hostinfo[1]+':'+hostinfo[2]
			trans = tn3270.Transaction(history.last().response,screen,data,'manual',host)
			history.append(trans)
			print screen.colorbuffer
			logger('Transaction added',kind='info')
		elif key == getch.KEY_CTRLh: # Ctrl-h help
			print interactive_help
		elif key == getch.KEY_CTRLk: # Ctrl-k color key
			print color_key
		elif key == getch.KEY_CTRLp: # Ctrl-p python shell
			embed()
		elif key == getch.KEY_CTRLs: # Ctrl-s screenshot
			em.save_screen(str(trans.timestamp.date())+'_'+str(trans.timestamp.time())+'.html')
			logger('Screenshot saved',kind='info')
		elif key == getch.KEY_TAB: # Tab 9
			em.exec_command('Tab()')
		elif key == getch.KEY_BACKSPACE: # Backspace
			em.exec_command('BackSpace()')
		elif key == getch.KEY_DELETE: # Delete
			em.exec_command('Delete()')
		elif key == getch.KEY_CTRLc: # Ctrl-c Clear
			em.exec_command('Clear()')
		elif key == getch.KEY_CTRLq: # Ctrl-q PA1
			trans = exec_trans(em,history,25)
			print trans.response.colorbuffer
		elif key == getch.KEY_CTRLw: # Ctrl-w PA2
			trans = exec_trans(em,history,26)
			print trans.response.colorbuffer
		elif key == getch.KEY_CTRLe: # Ctrl-e PA3
			trans = exec_trans(em,history,27)
			print trans.response.colorbuffer
		elif key > 31 and key < 127: # Alphanumeric
			em.safe_send(chr(key))
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

def save_history(history,savefile):
	if path.exists(savefile):
		logger('Savefile exists, I won\'t overwrite yet',kind='err')
		return False # Don't overwrite existing saves just yet
	try:
		sav = open(savefile,'w')
		pickle.dump(history, sav)
		sav.close()
	except IOError:
		logger('Saving didn\'t work.',kind='err')
		return False
	return True

def load_history(loadfile):
	if not path.exists(loadfile):
		logger("Couldn't find the history file" + loadfile + " bailing.",kind='err')
		sys.exit(1)
	try:
		lod = open(loadfile,'r')
		hist = pickle.load(lod)
		lod.close()
	except KeyError:
		logger("That doesn't look like a BIRP file",kind='err')
		sys.exit(1)
	return hist

def print_trans(history,num,header):
	trans = history[num]
	if header:
		print "\n",Fore.BLUE,"View Transaction",Fore.RESET
		print Fore.BLUE,"================",Fore.RESET
	print "\n",Fore.YELLOW,num,Fore.BLUE,trans.timestamp,Fore.CYAN,trans.key,\
				"\t",Fore.BLUE,trans.host,trans.comment,Fore.RESET
	print "  Req : ",trans.request.stringbuffer[0]
	for field in trans.data:
		print "  Data: row:",field.row,"col:",field.col,"str:",Fore.RED,field.contents,Fore.RESET
	print "  Resp: ",trans.response.stringbuffer[0],'\n'

# todo have print_history call print_trans rather
def print_history(history):
	print "\n",Fore.BLUE,"Transaction List",Fore.RESET
	print Fore.BLUE,"================",Fore.RESET,"\n"
	count = 0
	for trans in history:
		print Fore.YELLOW,count,Fore.BLUE,trans.timestamp,Fore.CYAN,trans.key,\
					"\t",Fore.BLUE,trans.host,trans.comment,Fore.RESET
		print "  Req : ",trans.request.stringbuffer[0]
		for field in trans.data:
			fieldtxt = field.contents.strip()
			if len(fieldtxt) > 0:
				print "  Data: row:",field.row,"col:",field.col,"str:",Fore.RED,fieldtxt,Fore.RESET
		print "  Resp: ",trans.response.stringbuffer[0],"\n"
		count += 1

def menu_save(history):
	savefile = ''
	logger(''.join([Fore.CYAN,'What file should I save to (must not exist): ',Fore.RESET]),kind='info')
	savefile = sys.stdin.readline().strip()
	if save_history(history,savefile):
		logger(''.join([Fore.CYAN,'History saved to ',savefile,Fore.RESET]),kind='info')

def print_seq(history,start,stop):
	print '\n' * 100 
	for trans in history[start:stop+1]:
		print '\n' * 101
		print trans.request
		sleep(1)
		print '\n' * 100
		print Fore.RED,trans.key,Fore.RESET
		print trans.response
		sleep(1)

# this will print two copies of the individual screen
def screentofile(screen,path):
	f = open(path+'.emu','w')
	g = open(path+'.brp','w')
	f.write(utf_8.encode(screen.emubuffer)[0])
	g.write(utf_8.encode(screen.colorbuffer)[0])
	f.close()
	g.close()

def menu_screen(transaction, reqres):
	#If reqres is True, we show the request, if False, we show the response
	if reqres: screen = transaction.request
	else: screen = transaction.response
	key = ''
	print screen.colorbuffer
	while key != getch.KEY_x:
		logger(''.join([Fore.CYAN,"Type 'f' to view the screen's fields or 'p' to view the un-markedup screen, 'e' to view the screen as an emulator would, 'r' to switch between the Request/Response, or 's' to export a copy to a text file (.brp/.emu). Type 'x' to go back.",Fore.RESET]),kind='info')
		key = getch()
		if key == getch.KEY_f or key == getch.KEY_F:
			print Fore.BLUE,"View Fields",Fore.RESET
			print Fore.BLUE,"===========",Fore.RESET,"\n"
			pprint(screen.fields)
			logger(''.join([Fore.RED,"Dropping into shell, check the",Fore.BLUE," screen ",Fore.RED,"object. Type quit() to return here.",Fore.RESET,"\n\n"]),kind='info')
			embed()
		elif key == getch.KEY_p or key == getch.KEY_p:
			print '\n',screen
		elif key == getch.KEY_e or key == getch.KEY_e:
			print '\n',screen.emubuffer
		elif key == getch.KEY_r or key == getch.KEY_r:
			reqres = not reqres
			if reqres:
				screen = transaction.request
				print Fore.BLUE,'REQUEST',Fore.RESET
			else:
				screen = transaction.response
				print Fore.BLUE,'RESPONSE',Fore.RESET
			print screen.colorbuffer
		elif key == getch.KEY_s or key == getch.KEY_s:
			filename = transaction.host+'_'+str(transaction.timestamp.date())+'_'+str(transaction.timestamp.time())
			screentofile(screen, filename)

def menu_trans(history,num):
	if num >= len(history) or num < 0:
		logger(''.join([Fore.CYAN,"Whoops, that transaction doesn't exist.",Fore.RESET]),kind='info')
		return 1
	trans = history[num]
	key = ''
	while key != getch.KEY_x:
		print_trans(history,num,True)
		logger(''.join([Fore.CYAN,"Choose '1' to view the Request, and '2' to view the Response. Type 'j' to move to the next transaction, and 'k' to the previous. Type 'x' to go back.",Fore.RESET]),kind='info')

		key = getch()
		if key == getch.KEY_1:
			menu_screen(trans, reqres=True) #reqres True shows request, False shows response
		elif key == getch.KEY_2:
			menu_screen(trans, reqres=False)
		elif key == getch.KEY_j:
			return menu_trans(history,num+1)
		elif key == getch.KEY_k:
			return menu_trans(history,num-1)
	return 0

def menu_history(history):
	choice = ''
	while choice.lower() != 'x':
		print_history(history)
		logger(''.join([Fore.CYAN,'Choose a transaction to view with the appropriate numeric key. Hit x, then enter to go back.',Fore.RESET]),kind='info')

		# We'll have more than just single digits here, so readline
		choice = sys.stdin.readline().strip()
		if choice.isdigit():
			key = int(choice)
			if key >= 0 and key < len(history):
				menu_trans(history,key)

def menu_find(history):
	choice = ''
	while choice.lower() != 'x':
		logger(''.join([Fore.CYAN,'Type the text you would like to search for and hit enter. Hit x, then enter to go back.',Fore.RESET]),kind='info')

		# We'll have more than just single digits here, so readline
		choice = sys.stdin.readline().strip()
		if choice.lower() == 'x': break
		results = find_all(history,choice) # execute the search
		for result in results: # print out the results, suppressing the header
			print_trans(history,result[0],False)
		logger(''.join([Fore.CYAN,'Choose a transaction to view with the appropriate numeric key. Hit x, then enter to go back.',Fore.RESET]),kind='info')
		choice = sys.stdin.readline().strip()
		if choice.isdigit():
			key = int(choice)
			if key >= 0 and key < len(history):
				return menu_trans(history,key)

def menu(em, history):
	key = ''	
	while key != getch.KEY_CTRLc:
		print menu_list
		key = getch()

		if key == getch.KEY_1:
			interactive(em,history)
		elif key == getch.KEY_2:
			menu_history(history)
		elif key == getch.KEY_3:
			menu_find(history)
		elif key == getch.KEY_4:
			embed()
		elif key == getch.KEY_5:
			menu_save(history)
		elif key == getch.KEY_X or key == getch.KEY_x:
			logger('Do big irons dream of electric paddocks? Goodnight.',kind='info')
			sys.exit(0)

# Just an excuse to wrap this away in a fold
def prestartup():
	init() # initialise coloured output from colorama
	
	# Define and fetch commandline arguments
	parser = argparse.ArgumentParser(\
		description = 'Big Iron Recon & Pwnage (BIRP) by @singe',\
		epilog = "It's easier than you think" )
	parser.add_argument('-t', '--target',\
		help='Target IP address or hostname & port: TARGET[:PORT]. The default port is 23. If you don\'t specify a target, you can manually specify it in the emulator',\
		required = False, dest = 'target', default = "")
	parser.add_argument('-s', '--sleep',\
		help='Seconds to sleep between actions (increase on slower systems). The default is 0 seconds.',\
		default = 0, type = float, dest = 'sleep')
	parser.add_argument('-l', '--load', help='Load a previously saved history file', default='',\
		dest = 'loadfile', type = str)
	parser.add_argument('-q', '--quiet', help="Ssssh! Don't print info text.",\
		default = False, dest = 'quiet', action = 'store_true')
	results = parser.parse_args()
	return results

# Just an excuse to wrap this away in a fold
def startup():
	# Parse commandline arguments
	logger('Big Iron Recon & Pwnage (BIRP) by @singe',kind='info')
	if not results.target:
		logger('Manual target selection chosen.',kind='info')
	else:
		logger('Target Acquired\t\t: ' + results.target,kind='info')
	logger('Slowdown is\t\t\t: ' + str(results.sleep),kind='info')
	logger('Attack platform\t\t: ' + platform.system(),kind='info')
	
	if not platform.system() == 'Windows':
		em = WrappedEmulator(visible=True,delay=results.sleep)
	elif platform.system() == 'Windows':
		logger('x3270 not supported on Windows',kind='err')
		sys.exit(1)
	if results.quiet:
		logger('Quiet Mode Enabled\t: Shhhhhhhhh!',kind='warn')
	history = tn3270.History()
	if results.loadfile:
		logger('Load history from\t\t: ' + results.loadfile,kind='info')
		history = load_history(results.loadfile)

	return (em,history)

results = prestartup()
(em,history) = startup()

if results.target:
	logger('Connecting to ' + results.target,kind='info')
	try:
		em.connect(results.target)
	except:
		logger('Connection failure',kind='err')
		sys.exit(1)
	if not em.is_connected():
		logger('Could not connect to ' + results.target + '. Aborting.',kind='err')
		sys.exit(1)

	hostinfo = em.get_hostinfo()
	host = hostinfo[1]+':'+hostinfo[2]
menu(em, history)

# And we're done. Close the connection
em.terminate()
