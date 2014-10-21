import sublime, sublime_plugin 
import json, threading, time, sys, os
from Fuse.interop_win import *
from Fuse.interop_unix import *
from Fuse.cmd_parser import *
from Fuse.fuse_util import *

items = None
autoCompleteEvent = None
closeEvent = None
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
	if name == "GoToDefinitionResponse":
		GoToDefinition(args)

def WriteToConsole(cmd):
	print("Fuse: " + cmd["Text"])

def Error(cmd):
	print("Fuse - Error: " + cmd["ErrorString"])

caretHack = -1

def GoToDefinition(cmd):
	if cmd["FoundDefinition"] == False:
		return

	window = sublime.active_window()
	path = cmd["Path"]

	global caretHack
	caretHack = cmd["Offset"]

	view = window.find_open_file(path)
	if view == None:		
		view = window.open_file(cmd["Path"], sublime.TRANSIENT)
		sublime.set_timeout(SetCaretTimeout, 100)
	else:
		window.focus_view(view)	
		SetCaretTimeout()

def SetCaretTimeout():	
	global caretHack
	if caretHack >= 0:
		sublime.active_window().active_view().run_command("setcaret", {"caretPos": caretHack})		
		caretHack = -1

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

	autoCompleteEvent.set()
	autoCompleteEvent.clear()

def plugin_loaded():
	global items
	global autoCompleteEvent
	global interop
	global closeEvent

	items = []
	autoCompleteEvent = threading.Event()
	closeEvent = threading.Event()

	interop = InteropUnix(recv)

	thread = threading.Thread(target = TryConnect)
	thread.daemon = True
	thread.start()

def plugin_unloaded():
	closeEvent.set()

def TryConnect():	
	while not closeEvent.is_set():
		if GetSetting("fuse_enabled") == True and not interop.IsConnected():
			interop.Connect()
			if interop.IsConnected():
				SendHandshake()

		time.sleep(1)

def GetExtension(path):
	base = os.path.basename(path)
	return os.path.splitext(base)[0]

def SendHandshake():
	interop.Send(json.dumps({"Command":"SetFeatures", "Arguments":
		{"Features":[{"Name":"CodeCompletion"}, {"Name": "Console"}]}}))

def SendInvalidation(view):
	interop.Send(json.dumps({"Command":"InvalidateFile", "Arguments":{"Path": view.file_name()}}))

def IsSupportedSyntax(syntaxName):	
	return syntaxName == "Uno" or syntaxName == "UX"

class FuseAutoComplete(sublime_plugin.EventListener):
	def on_post_save_async(self, view):
		SendInvalidation(view)		

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
		if not IsSupportedSyntax(syntaxName):
			return

		self.RequestAutoComplete(view, prefix, syntaxName)

		autoCompleteEvent.wait(0.2)
		
		data = (items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		return data

class DisconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		interop.Disconnect()

class SetcaretCommand(sublime_plugin.TextCommand):
	def run(self, edit, caretPos):
		view = self.view		
		view.sel().clear()
		view.sel().add(sublime.Region(caretPos, caretPos))
		view.show_at_center(caretPos)

class GotodefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):		
		view = self.view

		syntaxName = GetExtension(view.settings().get("syntax"))
		text = view.substr(sublime.Region(0,view.size()))
		if not IsSupportedSyntax(syntaxName) or len(view.sel()) == 0:
			return

		caret = view.sel()[0].a
		interop.Send(json.dumps({"Command": "GoToDefinition", "Arguments":{
			"Path": view.file_name(),
			"Text": text,
			"Type": syntaxName,
			"Caret": caret,
			"QueryID": 0}}))
