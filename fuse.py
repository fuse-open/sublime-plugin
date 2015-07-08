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
	interop = None	
	outputView = OutputView()
	useShortCompletion = False
	wordAtCaret = ""
	doCompleteAttribs = False
	foldUXNameSpaces = False
	completionSyntax = None
	buildViews = BuildViewManager()
	msgManager = MsgManager()

	def __init__(self):
		self.interop = Interop(self.recv, self.sendHello, self.tryConnect)

	def recv(self, msg):
		try:
			parsedRes = self.msgManager.parse(msg)

			if parsedRes == None:
				return

			if parsedRes.messageType == "Event":
				self.buildViews.tryHandleBuildEvent(parsedRes)
		except:
			traceback.print_exc()

	def handleErrors(self, errors):
		for error in errors:
			print("Fuse - Error({Code}): {Message}".format(Code = error["Code"], Message = error["Message"]))

	def handleCodeSuggestion(self, cmd):
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

	def onQueryCompletion(self, view):
		if GetSetting("fuse_completion") == False:
			return

		syntaxName = GetExtension(view.settings().get("syntax"))
		if not IsSupportedSyntax(syntaxName):
			return

		if not self.interop.isConnected():
			self.tryConnect()

		self.doCompleteAttribs = GetSetting("fuse_ux_attrib_completion")
		self.foldUXNameSpaces = GetSetting("fuse_ux_attrib_folding")
		self.completionSyntax = syntaxName

		response = self.requestAutoComplete(view, syntaxName)
		if response == None:
			return

		if response.status != "Success":
			self.handleErrors(response.errors)
			return

		self.handleCodeSuggestion(response.data)
		
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

	def requestAutoComplete(self, view, syntaxName):
		fileName = view.file_name()
		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a

		return self.msgManager.sendRequest(
			self.interop,
			"Fuse.GetCodeSuggestions",
			{
				"Path": fileName, 
				"Text": text, 
				"SyntaxType": syntaxName, 
				"CaretPosition": GetRowCol(view, caret)
			},
			0.2)

	def sendHello(self):
		self.msgManager.sendRequest(self.interop, 
		"Hello",
		{
			"Identifier": "Sublime Text 3",					
			"EventFilter": ""
		})

	def tryConnect(self):
		try:				
			if GetSetting("fuse_enabled") == True and not self.interop.isConnected():
				try:		
					if os.name == "nt":
						CREATE_NO_WINDOW = 0x08000000			
						subprocess.call(["fuse", "daemon", "-b"], creationflags=CREATE_NO_WINDOW)
					else:
						subprocess.call(["fuse", "daemon", "-b"])
				except:
					traceback.print_exc()

				self.interop.connect()
		except:
			traceback.print_exc()

def plugin_loaded():
	global gFuse
	gFuse = Fuse()

	s = sublime.load_settings("Preferences.sublime-settings")
	if GetSetting("fuse_open_files_in_same_window"):
		s.set("open_files_in_new_window", False)
	else:
		s.set("open_files_in_new_window", True)

def plugin_unloaded():
	global gFuse
	gFuse.interop.disconnect()
	gFuse = None

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
		return gFuse.onQueryCompletion(view)

class DisconnectCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.disconnect()

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

		response = gFuse.msgManager.sendRequest(
			gFuse.interop,
			"Fuse.GotoDefinition",
			{
				"Path": view.file_name(),
				"Text": text,
				"SyntaxType": syntaxName,
				"CaretPosition": GetRowCol(view, caret),					
			}
		)

		if response == None:
			return

		if response.status != "Success":
			gFuse.handleErrors(response.errors)
			return

		GotoDefinition(response.data)

class FuseBuildRunCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.Send("Event", json.dumps({"Command": "BuildAndRun"}))

class FuseRecompileCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.Send("Event", json.dumps({"Command": "Recompile"}))

class FusePreview(sublime_plugin.ApplicationCommand):
	def run(self, type, paths = []):	
		gFuse.tryConnect()

		for path in paths:			
			subprocess.Popen(["fuse", "preview", "--target=" + type, path])
			
	def is_visible(self, type, paths = []):
		if os.name == "nt" and type == "iOS":
			return False

		for path in paths:
			fileName, fileExtension = os.path.splitext(path)
			fileExtensionUpper = fileExtension.upper()
			if fileExtensionUpper != ".UX" and fileExtensionUpper != ".UNOSLN" and fileExtensionUpper != ".UNOPROJ":
				return False

		return True

class FusePreviewCurrent(sublime_plugin.TextCommand):
	def run(self, edit, type):
		sublime.run_command("fuse_preview", {"type": type, "paths": [self.view.file_name()]});

	def is_visible(self, type):
		return FusePreview.is_visible(None, type, [self.view.file_name()])