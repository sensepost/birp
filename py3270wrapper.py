#!/usr/bin/env python

from py3270 import Emulator, Command, CommandError, FieldTruncateError, X3270App, S3270App, ExecutableApp
import platform
from time import sleep
from sys import exit
from os import path


# Override some behaviour of py3270 library
class EmulatorIntermediate(Emulator):
    def __init__(self, visible=True, delay=0, args=None):
        try:
            Emulator.__init__(self, visible, args=args)
            self.delay = delay
        except OSError as e:
            print("Can't run x3270, are you sure it's in the right place? Actual error: " + str(e))
            exit(1)

    def send_enter(self):  # Allow a delay to be configured
        self.exec_command(b'Enter')
        if self.delay > 0:
            sleep(self.delay)

    def screen_get(self):
        response = self.exec_command(b'Ascii()')
        return response.data

    # Send text without triggering field protection
    def safe_send(self, text):
        for i in range(0, len(text)):
            self.send_string(text[i])
            if self.status.field_protection == 'P':
                return False  # We triggered field protection, stop
        return True  # Safe

    # Fill fields in carefully, checking for triggering field protections
    def safe_fieldfill(self, ypos, xpos, tosend, length):
        if length - len(tosend) < 0:
            raise FieldTruncateError('length limit %d, but got "%s"' % (length, tosend))
        if xpos is not None and ypos is not None:
            self.move_to(ypos, xpos)
        try:
            self.delete_field()
            if safe_send(self, tosend):
                return True  # Hah, we win, take that mainframe
            else:
                return False  # we entered what we could, bailing
        except CommandError as e:
            # We hit an error, get mad
            return False
        # if str(e) == 'Keyboard locked':

    # Search the screen for text when we don't know exactly where it is, checking for read errors
    def find_response(self, response):
        for rows in range(1, int(self.status.row_number) + 1):
            for cols in range(1, int(self.status.col_number) + 1 - len(response)):
                try:
                    if self.string_found(rows, cols, response):
                        return True
                except CommandError as e:
                    # We hit a read error, usually because the screen hasn't returned
                    # increasing the delay works
                    sleep(self.delay)
                    self.delay += 1
                    logger(
                        'Read error encountered, assuming host is slow, increasing delay by 1s to: ' + str(self.delay),
                        kind='warn')
                    return False
        return False

    # Get the current x3270 cursor position
    def get_pos(self):
        results = self.exec_command(b'Query(Cursor)')
        row = int(results.data[0].split(b' ')[0])
        col = int(results.data[0].split(b' ')[1])
        return row, col

    def get_hostinfo(self):
        return self.exec_command(b'Query(Host)').data[0].split(b' ')

    def is_connected(self):
        try:
            return Emulator.is_connected(self)
        except BrokenPipeError:
            return False

    def exec_command(self, cmdstr):
        try:
            return Emulator.exec_command(self, cmdstr)
        except BrokenPipeError:
            return Command(self.app, cmdstr)


# Patching __init__ method to support args
# this fix is required for the current version of py3270(0.3.5)
def executable_app_init(instance, args):
    if args:
        instance.args = instance.args + args
    instance.sp = None
    instance.spawn_app()


ExecutableApp.__init__ = executable_app_init

# Set the emulator intelligently based on your platform
if platform.system() == 'Linux' or platform.system() == 'Darwin':
    X3270App.executable = './x3270'
    S3270App.executable = 's3270'
elif platform.system() == 'Windows':
    # x3270_executable = 'Windows_Binaries/wc3270.exe'
    X3270App.executable = 'wc3270.exe'
else:
    logger('Your Platform:', platform.system(), 'is not supported at this time.', kind='err')
    exit(1)
if not path.isfile(X3270App.executable):
    print("Can't find the x3270 executable at %s."
          "You can configure the location at the bottom of py3270wrapper.py" % X3270App.executable)
    exit(1)
