import sublime, sublime_plugin, json, threading, time
from Fuse.interop_win import *

items = []
autoCompleteEvent = threading.Event()

def recv(msg):
	command = json.loads(msg)	
	suggestions = json.loads(command["Arguments"])["CodeSuggestions"]
		
	global items
	items = []
	for suggestion in suggestions:
		suggestionText = suggestion["Suggestion"]
		text = suggestionText + "\t(" + suggestion["Type"] + ")" 
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
		interop.Send(json.dumps({"Command":"SetFeatures", "Arguments":{"Features":[{"Name":"TextManager"}, {"Name":"CodeCompletion"}]}}))

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