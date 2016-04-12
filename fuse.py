import sublime, sublime_plugin, traceback
import json, threading, time, sys, os, time, subprocess
from types import *
from .interop import *
from .msg_parser import *
from .fuse_parseutils import *
from .fuse_util import *
from .go_to_definition import *
from .build_view import *
from .version import VERSION
from .log import log

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
	previousBuildCommand = None

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
			log().error(traceback.format_exc())

	def showFuseNotFound(self):
		error_message("Fuse could not be found.\n\nAttempted to run from: '"+getFusePathFromSettings()+"'\n\nPlease verify your Fuse installation." + self.rebootMessage())

	def rebootMessage(self):
		if str(sublime.platform()) == "windows":
			return " If this is the first time you are running Fuse, please try to restart your computer."
		return ""

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
			log().error(traceback.format_exc())

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
		log().info("Sending hello request")
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
				self.startFuseEvent.wait()
				self.startFuseEvent.clear()
					
				if getSetting("fuse_enabled") == True and not self.interop.isConnected():

					path = getFusePathFromSettings()

					try:		
						start_daemon = [path, "daemon", "-b"]
						log().info("Calling subprocess '%s'", str(start_daemon))
						if os.name == "nt":
							CREATE_NO_WINDOW = 0x08000000			
							subprocess.check_output(start_daemon, creationflags=CREATE_NO_WINDOW, stderr=subprocess.STDOUT)
						else:
							subprocess.check_output(start_daemon, stderr=subprocess.STDOUT)
					except subprocess.CalledProcessError as e:
						log().error("Fuse returned exit status " + str(e.returncode) + ". Output was '" + e.output.decode("utf-8") + "'.")
						error_message("Error starting Fuse:\n\n" + e.output.decode("utf-8"))
						return
					except:
						log().error("Fuse not found: " + traceback.format_exc())
						gFuse.showFuseNotFound()
						return

					self.interop.connect()
					if self.fuseStartedCallback is not None:
						self.fuseStartedCallback()				
			except:
				log().error(traceback.format_exc())

	def cleanup(self):
		self.interop.disconnect()
		self.startFuseThreadExit = True
		self.startFuseEvent.set()

def plugin_loaded():
	log().info("Loading plugin")
	log().info("Sublime version '" + sublime.version() + "'")
	log().info("Fuse plugin version '" + VERSION + "'")
	global gFuse
	gFuse = Fuse()
	fix_osx_path()

	s = sublime.load_settings("Preferences.sublime-settings")
	if getSetting("fuse_open_files_in_same_window"):
		s.set("open_files_in_new_window", False)
	else:
		s.set("open_files_in_new_window", True)

	if getSetting("fuse_show_user_guide_on_start", True):
		sublime.active_window().run_command("open_file", {"file":"${packages}/Fuse/UserGuide.txt"})
		setSetting("fuse_show_user_guide_on_start", False)
	log().info("Plugin loaded successfully")

def fix_osx_path():
	if str(sublime.platform()) == "osx":
		capitan_path="/usr/local/bin"
		if not capitan_path in os.environ["PATH"]:
			os.environ["PATH"] += ":" + capitan_path

def plugin_unloaded():
	log().info("Unloading plugin")
	global gFuse
	gFuse.cleanup()
	gFuse = None
	log().info("Unloaded plugin")

class FuseEventListener(sublime_plugin.EventListener):
	lastCaret = -1

	def on_selection_modified_async(self, view):
		syntaxName = getExtension(view.settings().get("syntax"))
		if not syntaxName == "UX" or not getSetting("fuse_selection_enabled"):
		 	return

		# This is a race condition but it does not matter
		caret = view.sel()[0].a
		if caret == self.lastCaret:
			return
		self.lastCaret = caret

		fileName = view.file_name()
		text = view.substr(sublime.Region(0,view.size()))		

		gFuse.msgManager.sendEvent(gFuse.interop, "Fuse.Preview.SelectionChanged", 
		{
			"Path": fileName,
			"Text": text,
			"CaretPosition": getRowCol(view, caret)
		})

	def on_activated_async(self, view):
		syntaxName = getExtension(view.settings().get("syntax"))
		if not isSupportedSyntax(syntaxName):
			return
		gFuse.tryConnect();

	def on_query_completions(self, view, prefix, locations):
		return gFuse.onQueryCompletion(view)

#TODO delete, not in use
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
			text = text;

			if not os.path.exists(text):
				os.makedirs(text)

			proc = subprocess.Popen([getFusePathFromSettings(), "create", "app", self.projectName, text], shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
				error_message("Could not create project:\n"+out)

		except ValueError:
			pass

class GotoDefinitionCommand(sublime_plugin.TextCommand):
	def run(self, edit):		
		view = self.view
		syntaxName = getExtension(view.settings().get("syntax"))		
		log().info("Requested goto definition for syntax type '%s'", syntaxName)
		if not isSupportedSyntax(syntaxName) or len(view.sel()) == 0:
			return

		text = view.substr(sublime.Region(0,view.size()))
		caret = view.sel()[0].a

		log().info("Requested goto definition for '%s': '%s'", view.file_name(), getRowCol(view, caret))

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
			log().info("No response for goto definition")
			return

		if response.status != "Success":
			log().error("Error in goto definition: '%s'", response.status)
			return

		gotoDefinition(response.data)

class FuseBuild(sublime_plugin.WindowCommand):
	def run(self, working_dir, build_target, run, paths=[]):
		
		platform = str(sublime.platform())
		log().info("Requested build: platform:'%s', build_target:'%s, working_dir:'%s'", platform, build_target, working_dir)

		if platform == "windows":
			if build_target == "iOS":
				error_message("iOS builds are only available on OS X.")
				return
			elif build_target == "CMake":
				error_message("CMake builds are only available on OS X.")
				return
		elif platform == "osx":
			if build_target == "DotNetExe":
				error_message(".Net builds are only available on Windows.")
				return
			elif build_target == "MSVC12":
				error_message("MSVC12 builds are only available on Windows.")
				return

		if working_dir is "":
			working_dir = os.path.dirname(paths[0])


		gFuse.tryConnect()

		cmd = gFuse.previousBuildCommand

		log().info("Previous build command was '%s'", str(cmd))

		if build_target != "Default":
			cmd = [getFusePathFromSettings(), "build", "-t=" + build_target, "--name=Sublime_Text_3", "-c=Release"]
			if run:
				cmd.append("-r")
		elif cmd is None:
			error_message("No Fuse build target set.\n\nGo to Tools/Build With... to choose one.\n\nFuture attempts to build will use that.")
			return

		gFuse.previousBuildCommand = cmd
		
		try:
			log().info("Trying to build with " + str(gFuse.previousBuildCommand))
			subprocess.Popen(gFuse.previousBuildCommand, cwd=working_dir)
		except:
			gFuse.showFuseNotFound()

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
					self.targetFolder = os.path.dirname(path)
				else:
					self.targetFolder = path


		header = "";
		if type=="app":
			header = "Choose a project name:"
		elif type=="uno":
			header = "Choose a class name:"
		else:
			header = "Choose a file name:"

		self.window.show_input_panel(header, "", self.on_done, None, None)

	def on_done(self, file_name):
		try:
			log().info("Trying to create '" + self.full_path(file_name) +  "'")
			args = [getFusePathFromSettings(), "create", self.targetTemplate, file_name, self.targetFolder]
			try:
				proc = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
			except:
				gFuse.showFuseNotFound()
				return
			code = proc.wait()
			if code == 0:
				log().info("Succssfully created '" + self.full_path(file_name) +  "'")
				if self.targetTemplate != "app":
					self.window.open_file(self.full_path(file_name));
			else:
				out = "Could not create file:\n";
				out += self.full_path(file_name) + "\n";
				for line in proc.stdout.readlines():
					out += line.decode()
				error_message(out)
		except ValueError:
			pass

	def is_enabled(self, type, paths = []):
		return True

	def full_path(self, file_name):
	    return os.path.join(self.targetFolder, file_name) + "." + self.targetTemplate

#TODO not in use, delete?
class FuseOpenUrl(sublime_plugin.ApplicationCommand):
	def run(self, url):
		if sys.platform=='win32':
			os.startfile(url)
		elif sys.platform=='darwin':
			subprocess.Popen(['open', url])

class FusePreview(sublime_plugin.ApplicationCommand):
	def run(self, type, paths = []):	
		gFuse.tryConnect()

		log().info("Starting preview for %s", str(paths))
		for path in paths:
			thread = threading.Thread(target = self.do_preview, args = (type, path))
			thread.daemon = True
			thread.start()

	def do_preview(self, type, path):
		fusePath = getFusePathFromSettings()
		try:
			start_preview = [fusePath, "preview", "--target=" + type, "--name=Sublime_Text_3", path]
			log().info("Opening subprocess %s", str(start_preview))
			if os.name == "nt":
				CREATE_NO_WINDOW = 0x08000000
				p = subprocess.Popen(start_preview, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
			else:			
				p = subprocess.Popen(start_preview, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		except:
			gFuse.showFuseNotFound()
			return

		stdout, stderr = p.communicate()
		if p.returncode != 0 and p.returncode != 10:
			window = sublime.active_window()
			error = window.create_output_panel("FuseError")
			errorMsg = "Unexpected fatal error! Please report this to us.\n" + stdout.decode("utf-8") + stderr.decode("utf-8")				
			log().error(errorMsg.replace("\n", " \\n "))
			error.run_command("append", { "characters": errorMsg.replace("\r", "") })
			window.run_command("show_panel", {"panel": "output.FuseError" })

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

#TODO delete unused class?
class FusePreviewCurrent(sublime_plugin.TextCommand):
	def run(self, edit, type = "Local"):
		sublime.run_command("fuse_preview", {"type": type, "paths": [self.view.file_name()]});

	def is_enabled(self, type):
		return FusePreview.is_enabled(None, type, [self.view.file_name()])

	def is_visible(self, type):
		return FusePreview.is_visible(None, type, [self.view.file_name()])

class FuseToggleSelection(sublime_plugin.WindowCommand):
	def run(self):
		setSetting("fuse_selection_enabled", not getSetting("fuse_selection_enabled"))
		isSet = getSetting("fuse_selection_enabled")
		log().info("Selection enabled was set to %s", str(isSet))
		if isSet is False:
			gFuse.msgManager.sendEvent(gFuse.interop, "Fuse.Preview.SelectionChanged", 
			{
				"Path": "",
				"Text": "",
				"CaretPosition": {"Line": 1, "Character": 1}
			})


	def is_checked(self):
		return getSetting("fuse_selection_enabled")

def error_message(message):
	log().error(message.replace("\n", "\\n"))
	sublime.error_message(message)
