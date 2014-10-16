import sublime, sublime_plugin 
import json, threading, time, sys, os
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
	if name == "Error":
		Error(args)

def WriteToConsole(cmd):
	print("Fuse: " + cmd["Text"])

def Error(cmd):
	print("Fuse - Error: " + cmd["ErrorString"])

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

	interop = InteropUnix(recv)

	thread = threading.Thread(target = TryConnect)
	thread.daemon = True
	thread.start()

def TryConnect():
	while True:
		if GetSetting("fuse_enabled") == True and not interop.IsConnected():
			interop.Connect()
			if interop.IsConnected():
				sublime.run_command("handshake")

		time.sleep(1)

def GetExtension(path):
	base = os.path.basename(path)
	return os.path.splitext(base)[0] 

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
	def RequestAutoComplete(self, view, prefix, syntaxName):		
		fileName = view.file_name()
		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a
		interop.Send(json.dumps({"Command":"RequestCodeCompletion", "Arguments":{
			"QueryID": 1,
			"Path": fileName, "Text":text, 
			"Type": syntaxName, "Caret":caret}}))

	def on_query_completions(self, view, prefix, locations):
		if GetSetting("fuse_completion") == False or not interop.IsConnected():
			return

		syntaxName = GetExtension(view.settings().get("syntax"))
		if syntaxName != "Uno" and syntaxName != "UX":
			return

		self.RequestAutoComplete(view, prefix, syntaxName)

		autoCompleteEvent.wait(0.2)
		
		data = (items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		return data

class DisconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		interop.Disconnect()