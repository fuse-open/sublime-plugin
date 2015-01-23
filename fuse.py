import asyncore
import sublime, sublime_plugin
import json, threading, time, sys, os, asyncore
from Fuse.interop import *
from Fuse.cmd_parser import *
from Fuse.fuse_util import *
from Fuse.go_to_definition import *
from Fuse.build_results import *
from Fuse.output_view import *
from Fuse.build_output import *

items = None
autoCompleteEvent = None
closeEvent = None
interop = None
buildResults = None
outputView = OutputView()
buildOutput = BuildOutputView()
connectThread = None

def Recv(msg):
	try:
		parsedRes = CmdParser.ParseCommand(msg)
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
		if name == "NewBuild":
			global buildResults
			buildResults = BuildResults(sublime.active_window())
	except:
		pass

def Error(cmd):
	print("Fuse - Error: " + cmd["ErrorString"])
	autoCompleteEvent.set()
	autoCompleteEvent.clear()

def WriteToConsole(args):
	typeOfConsole = args["Type"]
	if typeOfConsole == "DebugLog":
		outputView.Write(args["Text"])
	elif typeOfConsole == "BuildLog":
		buildOutput.Write(args["Text"])

def BuildEventRaised(cmd):
	buildResults.Add(cmd)

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
	global closeEvent
	global interop
	global buildResults

	items = []
	autoCompleteEvent = threading.Event()
	closeEvent = threading.Event()
	interop = Interop(Recv, SendHandshake)
	buildResults = BuildResults(sublime.active_window())

	global connectThread
	connectThread = threading.Thread(target = TryConnect)
	connectThread.daemon = True
	connectThread.start()

	s = sublime.load_settings("Preferences.sublime-settings")
	if GetSetting("fuse_open_files_in_same_window"):
		s.set("open_files_in_new_window", False)
	else:
		s.set("open_files_in_new_window", True)

def plugin_unloaded():
	closeEvent.set()
	connectThread.join(1)

	global interop
	interop = None	

def TryConnect():	
	try:		
		while not closeEvent.is_set():
			if GetSetting("fuse_enabled") == True and not interop.IsConnected():
				interop.Connect()
				if interop.IsConnected():
					SendHandshake()				

			time.sleep(1)
	finally:
		interop.Disconnect()

def SendHandshake():
	interop.Send(json.dumps({"Command":"SetFeatures", "Arguments":
		{"Features":[{"Name":"CodeCompletion"}, 
		{"Name": "Console"}, 
		{"Name": "BuildEvent"},
		{"Name": "ShortcutFeature"}]}}))

class FuseEventListener(sublime_plugin.EventListener):
	def RequestAutoComplete(self, view, prefix, syntaxName):		
		fileName = view.file_name()
		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a
		interop.Send(json.dumps({"Command":"RequestCodeCompletion", "Arguments":{
			"QueryId": 0,
			"Path": fileName, "Text": text, 
			"Type": syntaxName, "CaretPosition": GetRowCol(view, caret)}}))

	def on_query_completions(self, view, prefix, locations):
		if GetSetting("fuse_completion") == False or not interop.IsConnected():
			return

		syntaxName = GetExtension(view.settings().get("syntax"))
		if not IsSupportedSyntax(syntaxName):
			return

		self.RequestAutoComplete(view, prefix, syntaxName)

		autoCompleteEvent.wait(0.2)
		
		data = (items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		if len(items) == 0:
			return

		return data

class DisconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		interop.Disconnect()	

class ToggleBuildresCommand(sublime_plugin.ApplicationCommand):
	def run(self):	
		buildResults.ToggleShow()

class ToggleOutputviewCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		outputView.ToggleShow()

class ToggleBuildoutputCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		buildOutput.ToggleShow()

class GotoDefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):		
		view = self.view

		syntaxName = GetExtension(view.settings().get("syntax"))		
		if not IsSupportedSyntax(syntaxName) or len(view.sel()) == 0:
			return

		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a

		interop.Send(json.dumps({"Command": "GotoDefinition", "Arguments":{
			"Path": view.file_name(),
			"Text": text,
			"Type": syntaxName,
			"CaretPosition": GetRowCol(view, caret),
			"QueryId": 0}}))

class FuseRefreshCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		interop.Send(json.dumps({"Command": "RefreshViewports"}))