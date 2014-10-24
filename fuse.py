import sublime, sublime_plugin 
import json, threading, time, sys, os
from Fuse.interop_unix import *
from Fuse.cmd_parser import *
from Fuse.fuse_util import *

items = None
autoCompleteEvent = None
closeEvent = None
interop = None

def Recv(msg):
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
	if name == "BuildEventRaised":
		BuildEventRaised(args)

def WriteToConsole(cmd):
	print("Fuse: " + cmd["Text"])

def Error(cmd):
	print("Fuse - Error: " + cmd["ErrorString"])

def BuildEventRaised(cmd):
	window = sublime.active_window()
	path = cmd["Path"]

	view = window.find_open_file(path)
	if view == None:		
		view = window.open_file(cmd["Path"], sublime.TRANSIENT)
	else:
		window.focus_view(view)

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

	interop = InteropUnix(Recv)

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
	interop.Disconnect()

def SendHandshake():
	interop.Send(json.dumps({"Command":"SetFeatures", "Arguments":
		{"Features":[{"Name":"CodeCompletion"}, {"Name": "Console"}]}}))

def SendInvalidation(view):
	interop.Send(json.dumps({"Command":"InvalidateFile", "Arguments":{"Path": view.file_name()}}))

class FuseEventListener(sublime_plugin.EventListener):
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

class ShowErrorLine(sublime_plugin.TextCommand):
	def run(self, edit, key, region):
		view = self.view
		view.add_regions(key, [region], "keyword", "bookmark", 
			sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.PERSISTENT | sublime.DRAW_SQUIGGLY_UNDERLINE)

class Goto_definitionCommand(sublime_plugin.TextCommand):
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