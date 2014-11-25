import sublime, sublime_plugin

outputViewPanel = None
outputViewIsOpen = False

def AppendStrToReadonlyPanel(panel, strData):
	panel.set_read_only(False)
	panel.run_command("append", {"characters": strData})
	panel.set_read_only(True)

class OutputView:
	def __init__(self):
		self.__output = ""
	
	def Show(self):
		window = sublime.active_window()
		window.run_command("output_view", {"data": self.__output})

	def Write(self, strData):
		self.__output += strData

		if outputViewIsOpen:
			self.Show()

	def ToggleShow(self):
		global outputViewIsOpen

		if outputViewIsOpen:
			sublime.active_window().run_command("hide_panel", {"cancel": True})
			outputViewIsOpen = False
		else:
			self.Show()

class OutputViewCommand(sublime_plugin.WindowCommand):
	def run(self, data):
		global outputViewPanel
		global outputViewIsOpen

		window = self.window
		view = window.create_output_panel("FuseOutput")		
		outputViewPanel = view

		view.set_name("Fuse - Output")
		AppendStrToReadonlyPanel(view, data)

		view.run_command("move_to", {"to": "eol", "extend": false});

		window.run_command("show_panel", {"panel": "output.FuseOutput"})
		outputViewIsOpen = True