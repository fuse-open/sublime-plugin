import sublime, sublime_plugin, traceback
import json, threading, time, sys, os, time, subprocess
from types import *
from Fuse.interop import *
from Fuse.msg_parser import *
from Fuse.fuse_parseutils import *
from Fuse.fuse_util import *
from Fuse.go_to_definition import *
from Fuse.output_view import *
from Fuse.build_view import *

gFuse = None

class Fuse():
	apiVersion = (1,2)
	remoteApiVersion = None
	items = []
	isUpdatingCache = False
	autoCompleteEvent = None
	closeEvent = None
	interop = None	
	outputView = OutputView()
	connectThread = None
	useShortCompletion = False
	wordAtCaret = ""
	doCompleteAttribs = False
	foldUXNameSpaces = False
	completionSyntax = None
	buildViews = BuildViewManager()

	def __init__(self):
		self.interop = Interop(self.Recv, self.SendHello)
		self.autoCompleteEvent = threading.Event()

	def Recv(self, msg):
		try:
			parsedRes = MsgParser.Parse(msg)

			if parsedRes.messageType == "Response":
				if parsedRes.status == "Error":
					self.HandleErrors(parsedRes.errors)				
				elif parsedRes.type == "Fuse.GetCodeSuggestions":
					self.HandleCodeSuggestion(parsedRes.data)
				elif parsedRes.type == "Fuse.GotoDefinition":
					GotoDefinition(parsedRes.data)

			if parsedRes.messageType == "Event":
				if parsedRes.type == "Fuse.DebugLog":
					self.LogEvent(parsedRes.data)
				
				self.buildViews.tryHandleBuildEvent(parsedRes)
		except:
			traceback.print_exc()

	def HandleErrors(self, errors):
		for error in errors:
			print("Fuse - Error({Code}): {Message}".format(Code = error["Code"], Message = error["Message"]))

		self.autoCompleteEvent.set()
		self.autoCompleteEvent.clear()

	def LogEvent(self, data):
		self.outputView.Write(data["Text"])

	def HandleCodeSuggestion(self, cmd):
		suggestions = cmd["CodeSuggestions"]

		self.isUpdatingCache = cmd["IsUpdatingCache"]
		self.items = []

		try:
			# Determine which fields are enabled for completions
			# If remoteApiVersion hasn't been defined, base fields on that
			# Version no used to pick fields is determined from lowest minor version of local and remote

			minor = self.apiVersion[1]
			if self.remoteApiVersion != None:
				minor = min(self.apiVersion[1], self.remoteApiVersion[1])

			suggestedUXNameSpaces = []

			for suggestion in suggestions:

				outText = suggestionText = suggestion["Suggestion"]
				suggestionType = suggestion["Type"]
				hintText = "" # The right-column hint text

				if minor >= 1:
					if self.completionSyntax == "UX" and self.doCompleteAttribs and suggestionType == "Property":
						s = ParseUXSuggestion(wordAtCaret, suggestion, suggestedUXNameSpaces, useShortCompletion, self.foldUXNameSpaces)
						if(s == None):
							continue
						else:
							outText = s[0]
							suggestionText = s[0]+s[1]
						
					else:
						hintText = suggestion["ReturnType"]

						if suggestionType == "Method" or suggestionType == "Constructor":
							# Build sublime tab completion, type hint and verbose type hint
							parsedMethod = ParseMethod(suggestion["AccessModifiers"], suggestionText, suggestion["MethodArguments"], hintText, suggestionType == "Constructor")

							if not useShortCompletion:
								suggestionText = parsedMethod[0]
							hintText = parsedMethod[1]

						if suggestionType == "Field" or suggestionType == "Property":
							hintText = TrimType(hintText)


				if suggestion["PreText"] != "":
					suggestionText = suggestion["PreText"] + suggestion["PostText"]


				outText += "\t" + hintText
				if self.completionSyntax == "Uno":
					if wordAtCaret == "." or outText.casefold().find(wordAtCaret.casefold()) > -1:
						self.items.append((outText, suggestionText))
				else:
					self.items.append((outText, suggestionText))

		except:
			traceback.print_exc()

		self.autoCompleteEvent.set()
		self.autoCompleteEvent.clear()

	def OnQueryCompletion(self, view):
		if GetSetting("fuse_completion") == False or not self.interop.IsConnected():
			return

		syntaxName = GetExtension(view.settings().get("syntax"))
		if not IsSupportedSyntax(syntaxName):
			return

		self.doCompleteAttribs = GetSetting("fuse_ux_attrib_completion")
		self.foldUXNameSpaces = GetSetting("fuse_ux_attrib_folding")
		self.completionSyntax = syntaxName

		self.RequestAutoComplete(view, syntaxName)

		self.autoCompleteEvent.wait(0.2)
		
		data = (self.items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		if len(self.items) == 0:
			if self.isUpdatingCache == True:
				return ([("Updating suggestion cache...", "_"), ("", "")], sublime.INHIBIT_WORD_COMPLETIONS)

			if GetSetting("fuse_if_no_completion_use_sublime") == False:				
				return ([("", "")], sublime.INHIBIT_WORD_COMPLETIONS)
			else:
				return

		self.items = []
		return data

	def RequestAutoComplete(self, view, syntaxName):
		fileName = view.file_name()
		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a

		gFuse.interop.Send(
			json.dumps(
			{
				"MessageType":"Request",
				"Id": 0,
				"Type": "Fuse.GetCodeSuggestions",
				"Data":
				{				
					"Path": fileName, 
					"Text": text, 
					"SyntaxType": syntaxName, 
					"CaretPosition": GetRowCol(view, caret)
				}
			}))

	def SendHello(self):
		msg = json.dumps(
			{
				"MessageType": "Request",
				"Type": "Hello",
				"Id": 0,				
				"Data":
				{
					"Identifier": "Sublime Text 3",					
					"EventFilter": ""
				}
			})
		self.interop.Send(msg)

def plugin_loaded():
	global gFuse
	gFuse = Fuse()
	gFuse.closeEvent = threading.Event()

	gFuse.connectThread = threading.Thread(target = TryConnect)
	gFuse.connectThread.daemon = True
	gFuse.connectThread.start()

	s = sublime.load_settings("Preferences.sublime-settings")
	if GetSetting("fuse_open_files_in_same_window"):
		s.set("open_files_in_new_window", False)
	else:
		s.set("open_files_in_new_window", True)

def plugin_unloaded():
	global gFuse
	if gFuse.closeEvent != None:
		gFuse.closeEvent.set()
		gFuse.connectThread.join(1)
		
	gFuse = None

def TryConnect():	
	try:		
		while not gFuse.closeEvent.is_set():			
			if GetSetting("fuse_enabled") == True and not gFuse.interop.IsConnected():
				try:					
					subprocess.call(["fuse", "daemon", "-b"])					
				except:
					pass

				gFuse.interop.Connect()

			time.sleep(1)
	finally:
		gFuse.interop.Disconnect()

class FuseEventListener(sublime_plugin.EventListener):
	def on_modified(self, view):
		global useShortCompletion
		global wordAtCaret
		caret = view.sel()[0].a
		vstr = view.substr(caret)
		wordAtCaret = view.substr(view.word(caret)).strip()

		if vstr == "(" or vstr == "=": 
			useShortCompletion = True
		else:
			useShortCompletion = False

	def on_query_completions(self, view, prefix, locations):
		return gFuse.OnQueryCompletion(view)

class DisconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.Disconnect()

class ToggleOutputviewCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.outputView.ToggleShow()

class GotoDefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):		
		view = self.view

		syntaxName = GetExtension(view.settings().get("syntax"))		
		if not IsSupportedSyntax(syntaxName) or len(view.sel()) == 0:
			return

		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a

		gFuse.interop.Send(json.dumps(
		{
			"MessageType": "Request",
			"Id": 0,
			"Type": "Fuse.GotoDefinition", 
			"Data":
			{
				"Path": view.file_name(),
				"Text": text,
				"SyntaxType": syntaxName,
				"CaretPosition": GetRowCol(view, caret),					
			}
		}))

class FuseBuildRunCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.Send(json.dumps({"Command": "BuildAndRun"}))

class FuseRecompileCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.Send(json.dumps({"Command": "Recompile"}))

class FusePreview(sublime_plugin.ApplicationCommand):
	def run(self, paths = []):		
		for path in paths:			
			subprocess.Popen(["Fuse.exe", "preview", path])
			
	def is_visible(self, paths = []):
		for path in paths:
			fileName, fileExtension = os.path.splitext(path)
			fileExtensionUpper = fileExtension.upper()
			if fileExtensionUpper != ".UX" and fileExtensionUpper != ".UNOSLN" and fileExtensionUpper != ".UNOPROJ":
				return False

		return True

class FusePreviewCurrent(sublime_plugin.TextCommand):
	def run(self, edit):
		sublime.run_command("fuse_preview", {"paths": [self.view.file_name()]});

	def is_visible(self):
		path = self.view.file_name()
		if path is None:
			return False

		fileName, fileExtension = os.path.splitext(path)
		fileExtensionUpper = fileExtension.upper()
		if fileExtensionUpper != ".UX" and fileExtensionUpper != ".UNOSLN" and fileExtensionUpper != ".UNOPROJ":
			return False
		return True