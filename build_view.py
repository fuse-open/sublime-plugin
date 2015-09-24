import sublime, sublime_plugin
import queue, threading, time, os
from .msg_parser import *
from .build_results import BuildResults
from .fuse_util import *

class BuildStatus:
	success = 1,
	error = 2,
	internalError = 3

def appendStrToView(view, strData):
	view.run_command("append", {"characters": strData})

class BuildViewManager:
	buildViews = {}

	def tryHandleBuildEvent(self, event):
		validTypes = [
			"Fuse.LogEvent",
			"Fuse.BuildStarted", 
			"Fuse.BuildEnded", 
			"Fuse.BuildStageChanged", 
			"Fuse.BuildIssueDetected",
			"Fuse.BuildLogged"]

		if not event.type in validTypes:
			return False			

		if event.type == "Fuse.BuildStarted":
			fileName, fileExtension = os.path.splitext(os.path.basename(event.data["ProjectPath"]))
			projectPath = event.data["ProjectPath"]

			target = None
			if "Target" in event.data: 
				target = event.data["Target"]
			buildId = event.data["BuildId"]
			previewId = event.data["PreviewId"]

			buildView = None						
			if event.data["BuildType"] == "FullCompile":
				if "BuildTag" in event.data and event.data["BuildTag"] != "Sublime_Text_3":
					return False

				if target is not None:
					# Try to reuse build view			
					for previewId, view in self.buildViews.items():				
						if view.projectPath == projectPath and view.target == target:
							self.buildViews.pop(previewId)
							if view.view.window() != None:
								view.clear()
								view.show()
								view.buildId = buildId
								buildView = view
							break

				if buildView is None:
					buildView = self.createFullCompileView(fileName, projectPath, target, buildId)
			elif event.data["BuildType"] == "LoadMarkup":
				buildView = self.createLoadMarkupView(fileName, buildId)
			else:
				print("Invalid buildtype: " + event.data["BuildType"])			

			self.buildViews[event.data["PreviewId"]] = buildView
		elif event.type == "Fuse.LogEvent":
			for previewId, view in self.buildViews.items():
				if previewId == event.data.get("PreviewId", "") or previewId == event.data.get("ClientId", ""):
					view.tryHandleBuildEvent(event)
		else:
			for previewId, view in self.buildViews.items():
				if view.buildId == event.data["BuildId"]:
					view.tryHandleBuildEvent(event)

		return True
	
	def createLoadMarkupView(self, name, buildId):		
		return BuildResults(sublime.active_window(), buildId)

	def createFullCompileView(self, name, projectPath, target, buildId):
		return BuildView(name, projectPath, target, buildId)

class BuildView:
	def __init__(self, name, projectPath, target, buildId):
		self.buildId = buildId
		self.projectPath = projectPath
		self.status = BuildStatus()
		self.queue = queue.Queue()
		self.target = target
		self.gotDataEvent = threading.Event()
		self.pollThread = threading.Thread(target = self.__poll)
		self.pollThread.daemon = True
		self.pollThread.start()
		
		if not getSetting("fuse_show_build_results"):
			return
		
		window = sublime.active_window()
		self.view = window.new_file()			
		self.view.set_scratch(True)
		if target is None:
			self.view.set_name("Build Result - " + name + " - " + target)
		else:	
			self.view.set_name("Build Result - " + name + " - " + target)
		self.view.set_syntax_file("Packages/Fuse/BuildView.hidden-tmLanguage")

	def tryHandleBuildEvent(self, event):
		if not getSetting("fuse_show_build_results"):
			return False

		if event.type == "Fuse.BuildLogged":
			self.__write(event.data["Message"])
			return True
		elif event.type == "Fuse.LogEvent":
			self.__write("Output:\t" + event.data["Message"] + "\n")
			return True
		elif event.type == "Fuse.BuildEnded":
			status = event.data["Status"]
			if status == "Success":
				window = self.view.window()
				if window is not None:
					window.run_command("next_view_in_stack")
				self.status = BuildStatus.success
			elif status == "Error":
				self.status = BuildStatus.error
			elif status == "InternalError":
				self.status = BuildStatus.internalError

			self.__write("\n# Build complete.\n\n")

		return False

	def close(self):
		if not getSetting("fuse_show_build_results"):
			return

		if self.view.window() == None:
			return

		window = self.view.window()
		groupIndex, viewIndex = window.get_view_index(self.view)
		window.run_command("close_by_index", { "group": groupIndex, "index": viewIndex })

	def clear(self):
		self.view.run_command("select_all")
		self.view.run_command("right_delete")

	def show(self):
		window = self.view.window()
		if window is None:
			return
		window.focus_view(self.view)

	def __write(self, strData):
		if not getSetting("fuse_show_build_results"):
			return
		
		self.queue.put(strData, True)
		self.gotDataEvent.set()		

	def __poll(self):
		if not getSetting("fuse_show_build_results"):
			return

		while(True):
			self.gotDataEvent.wait()
			self.gotDataEvent.clear()
			res = ""
			while not self.queue.empty():
				res += self.queue.get_nowait()
			
			appendStrToView(self.view, res)
			
			time.sleep(0.05)