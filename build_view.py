import sublime, sublime_plugin
import queue, threading, time, os
from Fuse.msg_parser import *
from Fuse.build_results import BuildResults

class BuildStatus:
	success = 1,
	error = 2,
	internalError = 3

def AppendStrToView(view, strData):
	view.run_command("append", {"characters": strData})

class BuildViewManager:
	buildViews = {}
	buildIds = {}
	previewIds = {}

	def closeView(self, previewId):
		self.buildViews[previewId].close()
		self.buildViews.pop(previewId)
		self.previewIds.pop(self.buildIds[previewId])
		self.buildIds.pop(previewId)

	def tryHandleBuildEvent(self, event):
		validTypes = [
			"Fuse.LogEvent",
			"Fuse.BuildStarted", 
			"Fuse.BuildEnded", 
			"Fuse.BuildStageChanged", 
			"Fuse.BuildIssueDetected",
			"Fuse.BuildLogged",
			"Fuse.PreviewClosed"]

		if not event.type in validTypes:
			return False

		if event.type == "Fuse.BuildStarted":

			fileName, fileExtension = os.path.splitext(os.path.basename(event.data["ProjectPath"]))

			buildId = event.data["BuildId"]
			previewId = event.data["PreviewId"]
			self.buildIds[previewId] = buildId
			self.previewIds[buildId] = previewId

			buildView = None
			if event.data["BuildType"] == "FullCompile":
				buildView = self.createFullCompileView(fileName, buildId, previewId)
			elif event.data["BuildType"] == "LoadMarkup":
				buildView = self.createLoadMarkupView(fileName, buildId, previewId)
			else:
				print("Invalid buildtype: " + event.data["BuildType"])

			self.buildViews[event.data["PreviewId"]] = buildView
		elif event.type == "Fuse.PreviewClosed":
			previewId = event.data["PreviewId"]
			self.closeView(previewId)
		elif event.type == "Fuse.LogEvent":
			for previewId, view in self.buildViews.items():
				if view.previewId == event.data["PreviewId"]:
					view.tryHandleBuildEvent(event)
		else:
			for previewId, view in self.buildViews.items():
				if view.buildId == event.data["BuildId"]:
					view.tryHandleBuildEvent(event)

		return True
	
	def createLoadMarkupView(self, name, buildId, previewId):		
		return BuildResults(sublime.active_window(), buildId, previewId)

	def createFullCompileView(self, name, buildId, previewId):
		return BuildView(name, buildId, previewId)

class BuildView:
	def __init__(self, name, buildId, previewId):
		self.previewId = previewId
		self.buildId = buildId
		self.status = BuildStatus()
		self.queue = queue.Queue()
		self.gotDataEvent = threading.Event()
		self.pollThread = threading.Thread(target = self.__poll)
		self.pollThread.daemon = True
		self.pollThread.start()
		
		window = sublime.active_window()
		self.view = window.new_file()			
		self.view.set_scratch(True)		
		self.view.set_name("Build Result - " + name)
		self.view.set_syntax_file("Packages/Fuse/BuildView.hidden-tmLanguage")

	def tryHandleBuildEvent(self, event):
		if event.type == "Fuse.BuildLogged":
			self.__write(event.data["Message"])
			return True
		elif event.type == "Fuse.LogEvent":
			self.__write("Output:\t" + event.data["Message"] + "\n")
			return True
		elif event.type == "Fuse.BuildEnded":
			status = event.data["Status"]
			if status == "Success":
				self.status = BuildStatus.success
			elif status == "Error":
				self.status = BuildStatus.error
			elif status == "InternalError":
				self.status = BuildStatus.internalError

			self.__write("\n# Build complete.\n\n")

		return False

	def close(self):
		if self.status != BuildStatus.success:
			return

		window = self.view.window()
		groupIndex, viewIndex = window.get_view_index(self.view)
		window.run_command("close_by_index", { "group": groupIndex, "index": viewIndex })

	def __write(self, strData):
		self.queue.put(strData, True)
		self.gotDataEvent.set()		

	def __poll(self):
		while(True):
			self.gotDataEvent.wait()
			self.gotDataEvent.clear()
			res = ""
			while not self.queue.empty():
				res += self.queue.get_nowait()
			
			AppendStrToView(self.view, res)
			
			time.sleep(0.05)	

class BuildViewTest(sublime_plugin.ApplicationCommand):
	def run(self):
		buildView = BuildView()
		buildView.handleBuildEvent(Event("Fuse.BuildStarted", {"ProjectPath": "C:\\Users\\Emil\\Documents\\Fuse\\Untitled138\\Untitled138.unoproj"}))
		buildView.handleBuildEvent(Event("Fuse.BuildLogged", {"Message": "Lol"}))