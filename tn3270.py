from datetime import datetime
from colorama import Fore,Back,Style,init

# Object to hold field details
class Field:
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
		a = "<Field row:",`self.row`," col:",`self.col`," contents:",self.contents.strip(),">"
		return ''.join(a)

	def __str__(self):
		return self.contents

	def __len__(self):
		return len(self.contents)

# Object to hold a screen from x3270
class Screen:
	def __init__(self, rawbuff):
		self.rawbuffer = rawbuff
		self.rows = len(self.rawbuffer)
		self.cols = len(self.rawbuffer[0])
		#From x3270 defines
		self.__FA_PRINTABLE = 0xc0 #these make the character "printable"
		self.__FA_PROTECT = 0x20 #unprotected (0) / protected (1)
		self.__FA_NUMERIC = 0x10 #alphanumeric (0) /numeric (1)Skip?
		self.__FA_HIDDEN = 0x0c #display/selector pen detectable:
		self.__FA_INT_NORM_NSEL = 0x00 # 00 normal, non-detect
		self.__FA_INT_NORM_SEL = 0x04 # 01 normal, detectable
		self.__FA_INT_HIGH_SEL = 0x08 # 10 intensified, detectable
		self.__FA_INT_ZERO_NSEL = 0x0c # 11 nondisplay, non-detect, same as hidden
		self.__FA_RESERVED = 0x02 #must be 0
		self.__FA_MODIFY = 0x01 #modified (1)
		
	@property
	# Dump the hex without the field & formatting markers
	def plainbuffer(self):
		plnbuf = list()
		for line in self.rawbuffer:
			splitline = line.split(' ')
			plainline = []
			for i in splitline:
				if len(i) == 2: #Not a field marker
					plainline.append(i)
				else:
					plainline.append('00') #Use a NULL instead of a field marker
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
		a = "<Screen rows:",`self.rows`," cols:",`self.cols`," firstline:",self.stringbuffer[0],">"
		return ''.join(a)

	@property
	# Highlight different fields so we can see what is really going on on the screen
	# This looks at field markers only and ignores colours asked for by the host
	def colorbuffer(self):
		colbuf = list()
		colbuf.append(Fore.RED) #Highlight unfield'ed text
		counter = 0 #for line numbers
		for line in self.rawbuffer:
			newline = list()
			newline.append('{:>2}'.format(counter)+' ') #line no
			counter += 1
			for i in line.split(' '):
				# SF(c0=c8) is example of StartField markup
				if len(i) > 3 and i.find('SF(') >= 0:
					attrib = int(i[3:5],16)
					val = int(i[6:8],16)

					foreflag = False
					backflag = False
					styleflag = False
					if (val | self.__FA_HIDDEN) == val:
						newline.append(Back.RED)
						backflag = True
					if (val | self.__FA_MODIFY) == val:
						newline.append(Fore.YELLOW)
						newline.append(Style.BRIGHT)
						foreflag = True
						styleflag = True
					if (val | self.__FA_PROTECT) != val:
						newline.append(Back.GREEN)
						backflag = True
					#if (val | self.__FA_INT_HIGH_SEL) == val:
						#newline.append(Style.BRIGHT)
						#styleflag = True
					if not foreflag:
						newline.append(Fore.RESET)
					if not backflag:
						newline.append(Back.RESET)
					if not styleflag:
						newline.append(Style.NORMAL)

					newline.append(u'\u2219') #Field marker

				elif len(i) == 2:
					if i == '00':
						newline.append(u"\u2400")
					else:
						newline.append(i.decode("hex"))
				#newline.append(Fore.RESET+Back.RESET+Style.RESET_ALL)
			colbuf.append(''.join(newline))
		strcolbuf = '\n'.join(colbuf) + Fore.RESET + Back.RESET
		return strcolbuf

	@property
	# Display the screen as it would look in an emulator
	# This looks at field markers only and ignores colours asked for by the host
	# TODO: implement CF parsing
	def emubuffer(self):
		colbuf = list()
		for line in self.rawbuffer:
			newline = list()
			for i in line.split(' '):
				# SF(c0=c8) is example of StartField markup
				if len(i) > 3 and i.find('SF(') >= 0:
					attrib = int(i[3:5],16)
					val = int(i[6:8],16)

					newline.append(u' ') #Field marker

					modflag = False
					hideflag = False
					if (val | self.__FA_PROTECT) != val:
						modflag = True
						newline.append(Back.WHITE)
						newline.append(Fore.BLACK)
					if (val | self.__FA_HIDDEN) == val:
						hideflag = True
					if not modflag:
						newline.append(Fore.RESET)
						newline.append(Back.RESET)

				elif len(i) == 2:
					if i == '00':
						newline.append(u' ')
					elif hideflag:
						newline.append(u' ')
					else:
						newline.append(i.decode("hex"))
			colbuf.append(''.join(newline))
		strcolbuf = '\n'.join(colbuf)
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
					if (val | self.__FA_PRINTABLE) == val:
						printable = 1
					if (val | self.__FA_PROTECT ) == val:
						protected = 1
					if (val | self.__FA_NUMERIC ) == val:
						numeric = 1
					if (val | self.__FA_HIDDEN) == val:
						hidden = 1
					if (val | self.__FA_INT_NORM_NSEL) == val:
						normnsel = 1
					if (val | self.__FA_INT_NORM_SEL) == val:
						normsel = 1
					if (val | self.__FA_INT_HIGH_SEL) == val:
						highsel = 1
					if (val | self.__FA_INT_ZERO_NSEL) == val:
						zeronsel = 1
					if (val | self.__FA_RESERVED) == val:
						reserved = 1
					if (val | self.__FA_MODIFY) == val:
						modify = 1

					field = Field('', row, col, rawstatus, printable, protected, numeric, hidden, normnsel, normsel, highsel, zeronsel, reserved, modify)
					field_list.append(field)

				# Add the character to the last field entity added
				elif len(i) == 2:
					contents = i.decode("hex")
					if len(field_list) > 0:
						field_list[len(field_list)-1].contents += contents

				col += 1
			row += 1
		return field_list

	@property
	def protected_fields(self):
		try:	
			res = filter(lambda x: x.protected == 1, self.fields)
		except IndexError:
			res = []
		return res

	@property
	def input_fields(self):
		try:	
			res = filter(lambda x: x.protected == 0, self.fields)
		except IndexError:
			res = []
		return res

	@property
	def hidden_fields(self):
		try:	
			res = filter(lambda x: x.hidden == 1, self.fields)
		except IndexError:
			res = []
		return res

	@property
	def modified_fields(self):
		try:	
			res = filter(lambda x: x.modify == 1, self.fields)
		except IndexError:
			res = []
		return res

# Object to hold an single tn3270 "transaction" i.e. request/response & timestamp
class Transaction:
	def __init__(self, request, response, data, key='enter', host='', comment=''):
		# these should be Screen objects
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
		a = "<Transaction time:",str(self.timestamp)," host:",self.host,\
				" trigger:",self.key,"\n",\
				" Req : ",repr(self.request),"\n",\
				" Data: ",repr(self.data),"\n",\
				" Resp: ",repr(self.response),">"
		return ''.join(a)

class History:
	def __init__(self):
		self.timeline = list()

	def __getitem__(self, index):
		return self.timeline[index]

	def __repr__(self):
		return "<History timeline:\n"+repr(self.timeline)

	def __len__(self):
		return len(self.timeline)

	def append(self, transaction):
		self.timeline.append(transaction)

	def last(self):
		return self.timeline[len(self.timeline)-1]

	def count(self):
		return len(self.timeline)

