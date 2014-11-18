import sublime, sublime_plugin 
import Fuse.fuse_util

class GoToDefinition:
	def __init__(self, cmd):
		self.__GoToDefinition(cmd)

	def __GoToDefinition(self, cmd):
		if cmd["FoundDefinition"] == False:
			return

		window = sublime.active_window()
		path = cmd["Path"]
		
		caretPos = cmd["CaretPosition"]
		line = int(caretPos["Line"])
		column = int(caretPos["Character"])
		openCommand = cmd["Path"] + ":" + str(line) + ":" + str(column)

		view = window.open_file(openCommand, sublime.ENCODED_POSITION | sublime.TRANSIENT)