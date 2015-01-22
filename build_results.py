import sublime, sublime_plugin
from Fuse.fuse_util import *

paths = []
buildResultPanel = None

def NameRegions(view):
	return view.find_by_selector("entity.name.filename.find-in-files") + view.find_by_selector("entity.name.tag.xml")

def FileRegions(view):
	regions = NameRegions(view)
	lastRegion = view.find("^\!\=", 0)
	if lastRegion.a < 0:
		lastRegion = sublime.Region(view.size(), 0)

	newRegions = []
	for i in range(0, len(regions)):
		lastPoint = lastRegion.a - 1
		if i + 1 < len(regions):
			lastPoint = regions[i+1].a - 1

		newRegions.append(sublime.Region(regions[i].b, lastPoint - 1))
	return newRegions

class BuildResults:
	def __init__(self, window):
		global paths	
		paths = []

		global buildResultPanel
		buildResultPanel = window.create_output_panel("FuseBuildResults")
		buildResultPanel.set_name("Fuse - Build Results")
		buildResultPanel.set_syntax_file("Packages/Fuse/Build Results.hidden-tmLanguage")

		self.__CreateViewModel()
		self.Show()

	def __CreateViewModel(self):
		self.Append("- Build Result -\n")

	def Add(self, cmd):
		filePath = cmd["Path"]
		startPos = cmd["StartPosition"]

		if startPos == None:
			startPos = {"Line": 0, "Character": 0} 

		startLine = startPos["Line"]
		startCol = startPos["Character"]
		message = cmd["Message"]
		eventType = cmd["Type"]				

		fileData = LoadFile(filePath)
		output = ""

		if fileData == "":
			if eventType == "Error" or eventType == "FatalError":
				output += "\n{Message} - {Path}({Line}:{Col}):E\n".format(Path = filePath, Message = message, 
					Line = startLine, Col = startCol)
			else:
				output += "\n{Message} - {Path}({Line}:{Col}):\n".format(Path = filePath, Message = message, 
					Line = startLine, Col = startCol)
		else:
			lines = fileData.split('\n')
			line = int(startLine)

			dataBefore = ""
			for i in range(line - 5, line-1):
				if i < 0:
					continue
				if i > len(lines):
					continue

				dataBefore += "   " + str(i+1) + " " + lines[i] + "\n"

			dataAfter = ""
			for i in range(line, line+5):
				if i < 0:
					continue
				if i >= len(lines):
					continue

				dataAfter += "   " + str(i+1) + " " + lines[i] + "\n"

			paths.append([buildResultPanel.size() + 1, filePath, line])		

			if eventType == "Error" or eventType == "FatalError":
				output += "\n{Message} - {Path}:E\n{DataBefore}   {Line}:{LineData}\n{DataAfter}".format(
					Path = filePath, Line = startLine, LineData = lines[line-1], Message = message, DataBefore = dataBefore, DataAfter = dataAfter)
			elif eventType == "Warning":
				output += "\n{Message} - {Path}:\n{DataBefore}   {Line}:{LineData}\n{DataAfter}".format(
					Path = filePath, Line = startLine, LineData = lines[line-1], Message = message, DataBefore = dataBefore, DataAfter = dataAfter)
			else:
				output += "\n{Message} - {Path}:\n{DataBefore}   {Line}{LineData}\n{DataAfter}".format(
					Path = filePath, Line = startLine, LineData = lines[line-1], Message = message, DataBefore = dataBefore, DataAfter = dataAfter)		

		self.Append(output)

	def Append(self, data):
		view = buildResultPanel
		view.run_command("append", {"characters": data})

		view.fold(FileRegions(view))

		codePoints = view.find_by_selector("constant.numeric.line-number.match.find-in-files")
		lines = []
		for codePoint in codePoints:
			lines.append(view.line(codePoint))

		view.add_regions("errors", lines, "keyword", "bookmark", 
			sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.PERSISTENT | sublime.DRAW_SQUIGGLY_UNDERLINE)

	def Show(self):
		window = sublime.active_window()
		window.run_command("build_results")

	def ToggleShow(self):
		self.Show()

class BuildResultsCommand(sublime_plugin.WindowCommand):
	def run(self):
		window = self.window
		window.run_command("show_panel", {"panel": "output.FuseBuildResults" })

class GotoLocationCommand(sublime_plugin.TextCommand):
	def GetPath(self, region):
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
			filePath = self.GetPath(scope)
			window.open_file(filePath[0]+":"+str(filePath[1]), sublime.ENCODED_POSITION)
		else:
			self.OpenBasedOnNumericLine(window, view, sel)

	def OpenBasedOnNumericLine(self, window, view, sel):
			foundSelLoc = self.FindSelectionLocation(view, sel)
			if foundSelLoc == None:
				return

			fileRegions = FileRegions(view)

			foundRegion = None
			for region in fileRegions:
				if region.contains(sel):
					foundRegion = sublime.Region(region.a-1, region.b)

			if foundRegion != None:
				nameRegions = NameRegions(view)
				for region in nameRegions:
					if region.intersects(foundRegion):
						scope = view.extract_scope(region.a+1)			
						filePath = self.GetPath(scope)[0]
						line = view.substr(foundSelLoc)						
						window.open_file(filePath+":" + line, sublime.ENCODED_POSITION)
						break

	def FindSelectionLocation(self, view, sel):
		allLocations = view.find_by_selector("constant.numeric.line-number.match.find-in-files")
		for location in allLocations:
			if view.line(location).contains(sel):
				return location

class BuildResultListener(sublime_plugin.EventListener):
	def on_text_command(self, view, command_name, args):
		if command_name == "drag_select" and "by" in args.keys() and args["by"] == "words" and view.name() == "Fuse - Build Results":
			view.run_command("goto_location")				