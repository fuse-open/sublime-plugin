import sublime, sublime_plugin

outputViewPanel = None

def AppendStrToPanel(panel, strData):
	panel.run_command("append", {"characters": strData})
	
class OutputView:	
	def Show(self):
		window = sublime.active_window()
		window.run_command("output_view")

	def Write(self, strData):
		AppendStrToPanel(outputViewPanel, strData)

	def ToggleShow(self):
		self.Show()

class OutputViewCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		global outputViewPanel
		outputViewPanel = window.create_output_panel("FuseOutput")
		outputViewPanel.set_name("Fuse - Output")
		self.window = window

	def run(self):
		window = self.window	
		window.run_command("show_panel", {"panel": "output.FuseOutput", "toggle": True })