import sublime, sublime_plugin

outputViewPanel = None
outputViewIsOpen = False

def AppendStrToPanel(panel, strData):
	panel.run_command("append", {"characters": strData})
	
class OutputView:
	def __init__(self):
		self.__output = ""
	
	def Show(self):
		window = sublime.active_window()
		window.run_command("output_view", {"data": self.__output})

	def Write(self, strData):
		self.__output += strData				
		if outputViewPanel != None:
			AppendStrToPanel(outputViewPanel, self.__output)
			self.__output = ""

		if outputViewIsOpen:
			self.Show()

	def ToggleShow(self):
		global outputViewIsOpen

		if outputViewIsOpen:
			sublime.active_window().run_command("hide_panel", {"cancel": False})
			outputViewIsOpen = False
		else:
			self.Show()

class OutputViewCommand(sublime_plugin.WindowCommand):
	def run(self, data):
		global outputViewPanel
		global outputViewIsOpen

		window = self.window
		view = outputViewPanel
		if outputViewPanel == None:			
			view = window.create_output_panel("FuseOutput")		
			outputViewPanel = view

		AppendStrToPanel(outputViewPanel, data)

		view.set_name("Fuse - Output")
		window.run_command("show_panel", {"panel": "output.FuseOutput"})
		outputViewIsOpen = True