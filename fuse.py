import sublime, sublime_plugin, traceback
import json, threading, time, sys, os, time, subprocess
from types import *
from .interop import *
from .msg_parser import *
from .fuse_parseutils import *
from .fuse_util import *
from .go_to_definition import *
from .build_view import *

gFuse = None

class Fuse():
	items = []
	isUpdatingCache = False
	interop = None
	useShortCompletion = False
	wordAtCaret = ""
	doCompleteAttribs = False
	foldUXNameSpaces = False
	completionSyntax = None
	buildViews = BuildViewManager()
	msgManager = MsgManager()
	startFuseThread = None
	startFuseThreadExit = False
	startFuseEvent = threading.Event()

	def __init__(self):
		self.interop = Interop(self.recv, self.sendHello, self.tryConnect)
		self.startFuseThread = threading.Thread(target = self.tryConnectThread)
		self.startFuseThread.daemon = True
		self.startFuseThread.start()

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
			suggestedUXNameSpaces = []

			for suggestion in suggestions:

				outText = suggestionText = suggestion["Suggestion"]
				suggestionType = suggestion["Type"]
				hintText = "" # The right-column hint text

				if self.completionSyntax == "UX" and self.doCompleteAttribs and suggestionType == "Property":
					s = parseUXSuggestion(self.wordAtCaret, suggestion, suggestedUXNameSpaces, self.useShortCompletion, self.foldUXNameSpaces)
					if(s == None):
						continue
					else:
						outText = s[0]
						suggestionText = s[0]+s[1]					
				else:
					hintText = suggestion["ReturnType"]

					if suggestionType == "Method" or suggestionType == "Constructor":
						# Build sublime tab completion, type hint and verbose type hint
						parsedMethod = parseMethod(suggestion["AccessModifiers"], suggestionText, suggestion["MethodArguments"], hintText, suggestionType == "Constructor")

						if not self.useShortCompletion:
							suggestionText = parsedMethod[0]
						hintText = parsedMethod[1]

					if suggestionType == "Field" or suggestionType == "Property":
						hintText = trimType(hintText)


				if suggestion["PreText"] != "":
					suggestionText = suggestion["PreText"] + suggestion["PostText"]


				outText += "\t" + hintText
				if self.completionSyntax == "Uno":
					if self.wordAtCaret == "." or outText.casefold().find(self.wordAtCaret.casefold()) > -1:
						self.items.append((outText, suggestionText))
				else:
					self.items.append((outText, suggestionText))

		except:
			traceback.print_exc()

	lastResponse = None

	def onQueryCompletion(self, view):
		if getSetting("fuse_completion") == False:
		 	return

		syntaxName = getExtension(view.settings().get("syntax"))
		if not isSupportedSyntax(syntaxName):
		 	return

		self.doCompleteAttribs = getSetting("fuse_ux_attrib_completion")
		self.foldUXNameSpaces = getSetting("fuse_ux_attrib_folding")
		self.completionSyntax = syntaxName

		if self.lastResponse is None:
			self.requestAutoComplete(view, syntaxName, lambda res: self.responseAutoComplete(view, res))
			return ([("", "")], sublime.INHIBIT_WORD_COMPLETIONS)

		response = self.lastResponse
		self.lastResponse = None

		if response.status != "Success":
		 	self.handleErrors(response.errors)
		 	return

		caret = view.sel()[0].a
		vstr = view.substr(caret)
		self.wordAtCaret = view.substr(view.word(caret)).strip()

		if vstr == "(" or vstr == "=" or vstr == "\"": 
			self.useShortCompletion = True
		else:
			self.useShortCompletion = False

		self.handleCodeSuggestion(response.data)
		
		data = (self.items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		if len(self.items) == 0:
		 	if self.isUpdatingCache == True:
		 		return ([("Updating suggestion cache...", "_"), ("", "")], sublime.INHIBIT_WORD_COMPLETIONS)

		 	if getSetting("fuse_if_no_completion_use_sublime") == False:				
		 		return ([("", "")], sublime.INHIBIT_WORD_COMPLETIONS)
		 	else:
		 		return

		self.items = []
		return data

	def responseAutoComplete(self, view, res):
		self.lastResponse = res
		view.run_command("auto_complete",
		{
            "disable_auto_insert": True,
            "api_completions_only": False,
            "next_completion_if_showing": False,
            "auto_complete_commit_on_tab": True,
        })

	def requestAutoComplete(self, view, syntaxName, callback):
		fileName = view.file_name()
		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a

		self.msgManager.sendRequestAsync(
			self.interop,
			"Fuse.GetCodeSuggestions",
			{
				"Path": fileName, 
				"Text": text, 
				"SyntaxType": syntaxName, 
				"CaretPosition": getRowCol(view, caret)
			},
			callback)

	def sendHello(self):
		self.msgManager.sendRequest(self.interop, 
		"Hello",
		{
			"Identifier": "Sublime Text 3",					
			"EventFilter": ""
		})

	fuseStartedCallback = None

	def tryConnect(self, callback = None):
		self.fuseStartedCallback = callback
		self.startFuseEvent.set()

	def tryConnectThread(self):
		while not self.startFuseThreadExit:
			try:				
				if getSetting("fuse_enabled") == True and not self.interop.isConnected():
					try:		
						if os.name == "nt":
							CREATE_NO_WINDOW = 0x08000000			
							subprocess.call(["fuse", "daemon", "-b"], creationflags=CREATE_NO_WINDOW)
						else:
							subprocess.call(["fuse", "daemon", "-b"])
					except:
						traceback.print_exc()

					self.interop.connect()
					if self.fuseStartedCallback is not None:
						self.fuseStartedCallback()

				self.startFuseEvent.wait()
				self.startFuseEvent.clear()
			except:
				traceback.print_exc()

	def cleanup(self):
		self.interop.disconnect()
		self.startFuseThreadExit = True
		self.startFuseEvent.set()

def plugin_loaded():
	global gFuse
	gFuse = Fuse()

	s = sublime.load_settings("Preferences.sublime-settings")
	if getSetting("fuse_open_files_in_same_window"):
		s.set("open_files_in_new_window", False)
	else:
		s.set("open_files_in_new_window", True)

def plugin_unloaded():
	global gFuse
	gFuse.cleanup()
	gFuse = None

class FuseEventListener(sublime_plugin.EventListener):
	def on_modified(self, view):
		pass

	def on_query_completions(self, view, prefix, locations):
		return gFuse.onQueryCompletion(view)

class CreateProjectCommand(sublime_plugin.WindowCommand):
	projectName = ""

	def run(self):
		header = "Choose a project name:"
		self.window.show_input_panel(header, "", self.on_name_done, None, None)

	def on_name_done(self, text):
		try:
			self.projectName = text;
			header = "Choose project destination:"
			self.window.show_input_panel(header, "", self.on_destination_done, None, None)

		except ValueError:
			pass

	def on_destination_done(self, text):
		try:
			proc = subprocess.Popen(["fuse", "create", "app", self.projectName, text], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			code = proc.wait()
			if code==0:
				data = {
					"folders" : [
						{ "path" : text + "/" + self.projectName }
					]
				}
				self.window.set_project_data(data)
			else:
				out = ""
				for line in proc.stdout.readlines():
					out += line.decode()
				sublime.message_dialog("Could not create project:\n"+out)

		except ValueError:
			pass

	def is_enabled(self):
		return True

class GotoDefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):		
		view = self.view

		syntaxName = getExtension(view.settings().get("syntax"))		
		if not isSupportedSyntax(syntaxName) or len(view.sel()) == 0:
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
				"CaretPosition": getRowCol(view, caret),					
			}
		)

		if response == None:
			return

		if response.status != "Success":
			gFuse.handleErrors(response.errors)
			return

		gotoDefinition(response.data)

class FuseBuildRunCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.send("Event", json.dumps({"Command": "BuildAndRun"}))

class FuseRecompileCommand(sublime_plugin.ApplicationCommand):
	def run(self):
		gFuse.interop.send("Event", json.dumps({"Command": "Recompile"}))

class FuseCreate(sublime_plugin.WindowCommand):
	targetFolder = ""
	targetTemplate = ""

	def run(self, type, paths = []):
		self.targetTemplate = type
		folders = self.window.folders()
		if len(paths) == 0:
			if len(folders) == 0:
				return
			else:
				self.targetFolder = folders[0]
		else:
			for path in paths:
				self.targetFolder = ""
				# File or folder?
				if os.path.isfile(path):
					print("Is file")
					fileName, fileExtension = os.path.splitext(path)
					self.targetFolder = fileName
				else:
					print("Is not file")
					self.targetFolder = path


		header = "";
		if type=="ux":
			header = "Choose a file name:"
		elif type=="uno":
			header = "Choose a class name:"
		else:
			header = "Choose a project name:"

		self.window.show_input_panel(header, "", self.on_done, None, None)

	def on_done(self, text):
		try:
			proc = subprocess.Popen(["fuse", "create", self.targetTemplate, text, self.targetFolder], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			code = proc.wait()
			if code == 0:
				if self.targetTemplate != "app":
					self.window.open_file(self.targetFolder + "/" + text + "." + self.targetTemplate);
			else:
				out = ""
				for line in cmd.stdout.readlines():
					out += line.decode()
				sublime.message_dialog("Could not create file:\n"+out)
		except ValueError:
			pass

	def is_enabled(self, type, paths = []):
		return True

class FuseOpenUrl(sublime_plugin.ApplicationCommand):
	def run(self, url):
		if sys.platform=='win32':
			os.startfile(url)
		elif sys.platform=='darwin':
			subprocess.Popen(['open', url])

class FusePreview(sublime_plugin.ApplicationCommand):
	def run(self, type, paths = []):	
		gFuse.tryConnect()

		for path in paths:			
			subprocess.Popen(["fuse", "preview", "--target=" + type, "--name=Sublime Text 3", path])
	
	def is_visible(self, type, paths = []):
		if os.name == "nt" and type == "iOS":
			return False

		return True

	def is_enabled(self, type, paths = []):
		for path in paths:
			if path == None:
				return False
			fileName, fileExtension = os.path.splitext(path)
			fileExtensionUpper = fileExtension.upper()
			if fileExtensionUpper != ".UX" and fileExtensionUpper != ".UNOSLN" and fileExtensionUpper != ".UNOPROJ":
				return False

		return True

class FusePreviewCurrent(sublime_plugin.TextCommand):
	def run(self, edit, type = "Local"):
		sublime.run_command("fuse_preview", {"type": type, "paths": [self.view.file_name()]});

	def is_enabled(self, type):
		return FusePreview.is_enabled(None, type, [self.view.file_name()])

	def is_visible(self, type):
		return FusePreview.is_visible(None, type, [self.view.file_name()])