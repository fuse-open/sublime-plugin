import sublime, sublime_plugin

buildOutPanel = None

def AppendStrToPanel(panel, strData):
	panel.run_command("append", {"characters": strData})
	
class BuildOutputView:
	def Show(self):
		window = sublime.active_window()
		window.run_command("build_output")

	def Write(self, strData):
		AppendStrToPanel(buildOutPanel, strData)

	def ToggleShow(self):
		self.Show()

class BuildOutputCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		global buildOutPanel
		buildOutPanel = window.create_output_panel("FuseBuildOutput")
		buildOutPanel.set_name("Fuse - Build Output")
		self.window = window

	def run(self):
		window = self.window	
		window.run_command("show_panel", {"panel": "output.FuseBuildOutput", "toggle": True })