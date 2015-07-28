import sublime, sublime_plugin
from .fuse_util import *

paths = []
buildResultPanel = None

def NameRegions(view):
	return view.find_by_selector("entity.name.filename.find-in-files.warning") + view.find_by_selector("entity.name.tag.error")

class BuildResults:
	def __init__(self, window, buildId):
		global paths	
		paths = []

		global buildResultPanel
		buildResultPanel = window.create_output_panel("FuseBuildResults")
		buildResultPanel.set_name("Fuse - Auto Reload Result")
		buildResultPanel.set_syntax_file("Packages/Fuse/BuildResults.hidden-tmLanguage")

		self.buildId = buildId
		self.projectPath = ""

		self.__createViewModel()
		self.show()

	def __createViewModel(self):
		self.append("- Auto Reload Result -\n")

	def tryHandleBuildEvent(self, event):
		if event.type == "Fuse.BuildIssueDetected":
			self.add(event.data)
			return True
		return False

	def add(self, cmd):
		filePath = cmd["Path"]
		startPos = cmd["StartPosition"]

		if startPos == None:
			startPos = {"Line": 0, "Character": 0} 

		startLine = startPos["Line"]
		startCol = startPos["Character"]
		message = cmd["Message"]
		eventType = cmd["IssueType"]		

		output = ""

		paths.append([buildResultPanel.size() + 1, filePath, int(startLine)])

		if eventType == "Error" or eventType == "FatalError":
			output += "\n{Message} - {Path}({Line}:{Col}):E\n".format(Path = filePath, Message = message, 
				Line = startLine, Col = startCol)
		else:
			output += "\n{Message} - {Path}({Line}:{Col}):\n".format(Path = filePath, Message = message, 
				Line = startLine, Col = startCol)

		self.append(output)

	def append(self, data):
		view = buildResultPanel
		view.run_command("append", {"characters": data})

		codePoints = view.find_by_selector("constant.numeric.line-number.match.find-in-files")
		lines = []
		for codePoint in codePoints:
			lines.append(view.line(codePoint))

		view.add_regions("errors", lines, "keyword", "bookmark", 
			sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.PERSISTENT | sublime.DRAW_SQUIGGLY_UNDERLINE)

	def show(self):
		window = sublime.active_window()
		window.run_command("fuse_build_results")

	def close(self):
		pass

class FuseBuildResultsCommand(sublime_plugin.WindowCommand):
	def run(self):
		window = self.window
		window.run_command("show_panel", {"panel": "output.FuseBuildResults" })

class FuseGotoLocationCommand(sublime_plugin.TextCommand):
	def getPath(self, region):
		for path in paths:
			if region.contains(path[0]):
				return (path[1], path[2])

	def run(self, edit):
		view = self.view
		window = view.window()
		sel = view.sel()[0]
		scope = view.scope_name(sel.a)

		if scope.find(".name.") > -1:
			scope = view.extract_scope(sel.a)
			filePath = self.getPath(scope)
			if filePath[0] == '':
				return
				
			window.open_file(filePath[0]+":"+str(filePath[1]), sublime.ENCODED_POSITION)
		else:
			self.openBasedOnNumericLine(window, view, sel)

	def openBasedOnNumericLine(self, window, view, sel):
			foundSelLoc = self.findSelectionLocation(view, sel)
			if foundSelLoc == None:
				return

			if foundRegion != None:
				nameRegions = NameRegions(view)
				for region in nameRegions:
					if region.intersects(foundRegion):
						scope = view.extract_scope(region.a+1)			
						filePath = self.getPath(scope)[0]
						line = view.substr(foundSelLoc)						
						window.open_file(filePath+":" + line, sublime.ENCODED_POSITION)
						break

	def findSelectionLocation(self, view, sel):
		allLocations = view.find_by_selector("constant.numeric.line-number")
		for location in allLocations:
			if view.line(location).contains(sel):
				return location

class BuildResultListener(sublime_plugin.EventListener):
	def on_text_command(self, view, command_name, args):
		isDragSelect = command_name == "drag_select"
		if args == None:
			return

		isSelectingWord = "by" in args.keys() and args["by"] == "words"
		if isDragSelect and isSelectingWord and view.name() == "Fuse - Auto Reload Result":
			view.run_command("fuse_goto_location")