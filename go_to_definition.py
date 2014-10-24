import sublime, sublime_plugin 
import Fuse.fuse_util

class GoToDefinition:
	def __init__(self, cmd):
		self.caretHack = -1
		self.__GoToDefinition(cmd)

	def __GoToDefinition(self, cmd):
		if cmd["FoundDefinition"] == False:
			return

		window = sublime.active_window()
		path = cmd["Path"]
		
		self.caretHack = cmd["Offset"]

		view = window.find_open_file(path)
		if view == None:		
			view = window.open_file(cmd["Path"], sublime.TRANSIENT)
			sublime.set_timeout(self.SetCaretTimeout, 100)
		else:
			window.focus_view(view)
			self.SetCaretTimeout()

	def SetCaretTimeout(self):	
		if self.caretHack >= 0:
			view = sublime.active_window().active_view()
			view.run_command("setcaret", {"caretPos": self.caretHack})		
			self.caretHack = -1

class SetcaretCommand(sublime_plugin.TextCommand):
	def run(self, edit, caretPos):
		view = self.view		
		view.sel().clear()
		view.sel().add(sublime.Region(caretPos, caretPos))
		view.show_at_center(caretPos)