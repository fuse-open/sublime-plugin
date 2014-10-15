import sublime, sublime_plugin 
import json, threading, time, sys
from Fuse.interop_win import *
from Fuse.interop_unix import *
from Fuse.cmd_parser import *
from Fuse.fuse_util import *

items = None
autoCompleteEvent = None
interop = None

def recv(msg):
	command = json.loads(msg)
	parsedRes = CmdParser.ParseCommand(command)
	name = parsedRes[0]
	args = parsedRes[1]

	if name == "SetCodeSuggestions":
		HandleCodeSuggestion(args)
	if name == "WriteToConsole":
		WriteToConsole(args)

def WriteToConsole(cmd):
	print(cmd["Text"])

def HandleCodeSuggestion(cmd):
	suggestions = cmd["CodeSuggestions"]
		
	global items
	items = []
	
	for suggestion in suggestions:
		suggestionText = suggestion["Suggestion"]
		text = suggestionText + "\t(" + suggestion["Type"] + ")"

		if suggestion["PreText"] != "":
			suggestionText = suggestion["PreText"] + suggestion["PostText"]

		items.append((text, suggestionText))

	global autoCompleteEvent
	autoCompleteEvent.set()
	autoCompleteEvent.clear()

def plugin_loaded():
	global items
	global autoCompleteEvent
	global interop

	items = []
	autoCompleteEvent = threading.Event()

	#if sys.platform == "win32":	
	#	interop = InteropWin(recv)
	#else:
	interop = InteropUnix(recv)

	thread = threading.Thread(target = TryConnect)
	thread.daemon = True
	thread.start()

def TryConnect():
	while True:
		if GetSetting("fuse_enabled") == True and not interop.IsConnected():
			sublime.run_command("devconnect");
		time.sleep(1)

class ConnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		interop.Connect()

class DevconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		sublime.run_command("connect")
		sublime.run_command("handshake")

class HandshakeCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		interop.Send(json.dumps({"Command":"SetFeatures", "Arguments":{"Features":[{"Name":"TextManager"}, {"Name":"CodeCompletion"}, {"Name": "Console"}]}}))

class FuseAutoComplete(sublime_plugin.EventListener):
	def RequestAutoComplete(self, view, prefix):
		fileName = view.file_name()
		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a
		interop.Send(json.dumps({"Command":"RequestCodeCompletion", "Arguments":{
			"QueryID": 1,
			"Path": fileName, "Text":text, 
			"Type": "uno", "Caret":caret}}))

	def on_query_completions(self, view, prefix, locations):
		if GetSetting("fuse_completion") == False or not interop.IsConnected():
			return

		self.RequestAutoComplete(view, prefix)			

		autoCompleteEvent.wait(0.2)
		
		data = (items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		return data

class DisconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		interop.Disconnect()