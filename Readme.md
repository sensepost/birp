Big Iron Recon & Pwnage (BIRP)
==============================
by @singe (Dominic White @ SensePost)

Overview
--------

BIRP is a tool that will assist in the security assessment of mainframe applications served over TN3270. Much like what BURP and other web application proxies do for web application assessments, BIRP aims to do the same for TN3270 application assessments. And, much like with web applications, being able to see and modify fields that the application developer assumed were neither visible nor modifiable allows security assumptions be bypassed.

In particular, BIRP provides two capabilities for the aspiring TN3270 hacker. The first is that it shows all the data returned by the application in the screen. This includes hidden fields. The second is that it allows fields marked as "protected" aka "non modifiable" to be modified. Depending on how the application has been developed, this can allow application functionality to be modified.

Running
-------

./birp.py -h will give you startup help if you want to get running.

All you need is to specify a target with -t . Target specification can include a port with a : after the IP e.g. 10.10.10.10:1023. If no port is specified it will default to :23 as per x3270 default behaviour.

You can use -l to load a previously saved history file into the history. You must always specify a target and cannot just view history yet unfortunately.

Check the pre-requisites below for installing. Unfortunately, this will only run in Unix environments at the moment, no Windows support.

Functionality
-------------

Currently, BIRP has a fairly limited set of functionality. These are:

* Interactive Mode

Interactive mode is the heart of BIRPs functionality. It will pass keypresses and other commands from BIRP to x3270 and allow the analyst to interact with the application as they would if they were using x3270 directly. However, it will also display the marked up "hacker view" of each screen returned, as well as record "transactions" and store it in the proxy history for later analysis and inspection.

In interactive mode hitting Ctrl-h will print a help screen, Ctrl-k will display a color key, and ESC will exit back to the menu.

BIRP tries to work out when a "transaction" has occurred, and record the before and after screen, as well as the modified fields. Certain keys are usually guaranteed to initiate a transaction such as Enter or any of the PF/PA keys. However, if for any reason the screen requires different keys to function, you can manually "push" a transaction with Ctrl-u right after performing the action. 

Finally, if you want to have the screen re-printed hit Ctrl-r.

* View History

This will display the history of all transactions BIRP recorded, and allow them to be inspected. Specifically it provides access to the screen submitted, the fields that were modified in that screen (i.e. the data submitted) and the response.

For each screen, only the first row is displayed as context, but the full screen can be printed if you view the transaction.

Also, you can drop into python and examine the screen object directly.

* Search History

Here you can perform a case sensitive search to find transactions with screens that contain certain text.

* Save History

You can save your history to a file, and load it again later with the -l switch on the command line. You need to save it to a unique filename.

* Python Console

The tool is not done yet, and right now there are lots of good reasons to be able to play with the objects directly. You can drop into an IPython embedded shell at various places. BIRP has a fairly useful set of python objects that you can interrogate, and I have made sure they have useful pythonic output (str/repr). The top object is the "history" which contains a list on "transactions". You can interrogate the last transaction added by referring to history.last(). Each transaction has a request and response screen object. So, for example, to get a list of all hidden fields in the last response from the server you could use: history.last().response.hidden_fields

For further detail, it would be best to view the tn3270.py module.

Pre-requisites:
---------------

* Python libraries: py3270 (v0.2.0), colorama, IPython
These can be installed with pip or easy_install. The code has been updated to work with the new version of py3270, so make sure you upgrade your older versions.

* Hacked x3270 client
The patches are included. You can download the source at http://x3270.bgp.nu/download.html then cd to the x3270 directory once extracted, and patch -p1 < x3270-hack-full.patch
You can use an unmodified client, but then you will not be able to edit protected fields.
The patch makes two changes, the first is to allow protected fields to be edited, the other is to make hidden fields visible (shown in reverse text highlightng). This functionality is split into two other patched if you would only like one or the other for some reason.

Design Choices
--------------

The key handling functionality I use is my own custom getch implementation. It is pretty horrible, but it works. I would love to use a more mature key handling implementation such as curses, pygame, urwid etc. but they all want to take over your screen too. Personally, I find the scroll back buffer to be invaluable in recording my activities or just being able to scroll up and remember what I did, so I did not want to loose that, hence this approach.

I found py3270 pretty rough and ended up wrapping some of it. I've provided this as a separate wrapper that you can use in your own programs.

Shouts
------

* Thanks to Soldier of Fortran (@mainframed) for the help figuring out this mainframe stuff.
* Andreas Lindh (@addelindh) for the clever name of the tool.
* Rogan Dawes for sitting opposite me for most of the writing the tool, always with helpful pointers.
* An unnamed client who gave me the opportunity to test their mainframes and develop the tool.

By dominic () sensepost.com (@singe)

License
-------

Big Iron Recon & Pwnage by SensePost is licensed under a Creative Commons Attribution-ShareAlike 4.0 International License (http://creativecommons.org/licenses/by-sa/4.0/)
Permissions beyond the scope of this license may be available at http://sensepost.com/contact us/.
