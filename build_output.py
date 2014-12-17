import sublime, sublime_plugin

buildOutPanel = None

def AppendStrToPanel(panel, strData):
	panel.run_command("append", {"characters": strData})
	
class BuildOutputView:
	def __init__(self):
		self.__output = ""
		self.__outputBuf = ""
	
	def Show(self):
		window = sublime.active_window()
		window.run_command("build_output", {"data": self.__output})

	def Write(self, strData):
		self.__output += strData
		self.__outputBuf += strData		
		if buildOutPanel != None:
			AppendStrToPanel(buildOutPanel, self.__outputBuf)
			self.__outputBuf = ""

	def ToggleShow(self):
		global buildOutPanel 

		if buildOutPanel != None:
			sublime.active_window().run_command("hide_panel", {"cancel": False})
			buildOutPanel = None
		else:
			self.Show()

class BuildOutputCommand(sublime_plugin.WindowCommand):
	def run(self, data):
		global buildOutPanel

		window = self.window
		view = buildOutPanel
		if buildOutPanel == None:			
			view = window.create_output_panel("FuseBuildOutput")		
			buildOutPanel = view

		AppendStrToPanel(buildOutPanel, data)

		view.set_name("Fuse - Build Output")
		window.run_command("show_panel", {"panel": "output.FuseBuildOutput"})