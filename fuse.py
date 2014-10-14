import sublime, sublime_plugin, json, threading, time
from Fuse.interop_win import *
from Fuse.cmd_parser import *
from Fuse.fuse_util import *

items = []
autoCompleteEvent = threading.Event()

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

	autoCompleteEvent.set()
	autoCompleteEvent.clear()

interop = Interop(recv)

class ConnectCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		interop.Connect()

class DevconnectCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.run_command("connect")
		self.view.run_command("handshake")

class HandshakeCommand(sublime_plugin.TextCommand):
	def run(self, edit):
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
		if GetSetting("fuse_completion") == False:
			return

		if not interop.IsConnected():
			view.run_command("devconnect")

		global items
		self.RequestAutoComplete(view, prefix)			

		autoCompleteEvent.wait(0.2)
		
		data = (items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		return data

class DisconnectCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		interop.Disconnect()