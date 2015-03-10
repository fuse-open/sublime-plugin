import sublime, sublime_plugin
import json, threading, time, sys, os, time
from Fuse.interop import *
from Fuse.cmd_parser import *
from Fuse.fuse_util import *
from Fuse.go_to_definition import *
from Fuse.build_results import *
from Fuse.output_view import *
from Fuse.build_output import *

items = None
isUpdatingCache = False
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
		print(sys.exc_info()[0])

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

# Rebuild a sequence as a list of n-tuples
def Group(lst, n):
    return zip(*[lst[i::n] for i in range(n)]) 

def TrimType(typeDesc):
	return typeDesc.rpartition(".")[2]

# Parse a method or constructor into tab completion text, type hint and verbose hint
def ParseMethod(access, methodName, arguments, returntype, asCtor):
	args = Group(arguments, 2)
	verboseHintText = " ".join(access)
	methodText = methodName+"("
		
	if asCtor:
		typeHint = "Class ("
	else:
		typeHint = "("

	count = 1
	for arg in args:
		if(count>1):
			methodText += ", "
			typeHint += ", "
		argName = arg[1]
		isOut = argName.find("&") > -1
		if isOut:
			argName = argName.replace("&", "")
			methodText += "out ${" + str(count) + ":" + argName + "}"
			typeHint += "out ";
		else:
			methodText += "${" + str(count) + ":" + argName + "}"

		typeHint += TrimType(arg[0]) + " " + argName
		count += 1

	if asCtor:
		typeHint += ")"
	else:
		typeHint += "):" + TrimType(returntype)
	methodText += ")"

	return (methodText, typeHint, verboseHintText)

def HandleCodeSuggestion(cmd):
	suggestions = cmd["CodeSuggestions"]

	global items
	global isUpdatingCache
	isUpdatingCache = cmd["IsUpdatingCache"]
	items = []

	print("Received "+str(len(suggestions)))
	for suggestion in suggestions:

		suggestionText = suggestion["Suggestion"]
		memberType = suggestion["Type"]
		# new stuff
		accessModifiers = suggestion["AccessModifiers"]
		fieldModifiers = suggestion["FieldModifiers"]
		descriptionText = suggestion["TypeDescription"]
		arguments = suggestion["MethodArguments"]

		verboseHintText = ""

		if descriptionText == "":
			descriptionText = memberType 

		outtext = suggestionText 

		if memberType == "Method" or memberType == "Constructor":
			# Build sublime tab completion, type hint and verbose type hint
			parsedMethod = ParseMethod(accessModifiers, suggestionText, arguments, descriptionText, memberType == "Constructor")
			suggestionText = parsedMethod[0]
			descriptionText = parsedMethod[1]
			verboseHintText = parsedMethod[2]

		if memberType == "Field" or memberType == "Property":
			descriptionText = TrimType(descriptionText)

		if suggestion["PreText"] != "":
			suggestionText = suggestion["PreText"] + suggestion["PostText"]

		outtext += "\t" + descriptionText

		items.append((outtext, suggestionText))

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
		global items

		if GetSetting("fuse_completion") == False or not interop.IsConnected():
			return

		syntaxName = GetExtension(view.settings().get("syntax"))
		if not IsSupportedSyntax(syntaxName):
			return

		self.RequestAutoComplete(view, prefix, syntaxName)

		autoCompleteEvent.wait(0.2)
		
		data = (items, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		if len(items) == 0:
			if isUpdatingCache == True:
				return ([("Updating suggestion cache...", "_"), ("", "")], sublime.INHIBIT_WORD_COMPLETIONS)

			if GetSetting("fuse_if_no_completion_use_sublime") == False:				
				return ([("", "")], sublime.INHIBIT_WORD_COMPLETIONS)
			else:
				return
						
		items = []
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