import sublime, sublime_plugin
import queue, threading, time, os
from Fuse.msg_parser import *

def AppendStrToView(view, strData):
	view.run_command("append", {"characters": strData})

class BuildViewManager:
	buildViews = {}

	def tryHandleBuildEvent(self, event):
		validTypes = [
			"Fuse.BuildStarted", 
			"Fuse.BuildEnded", 
			"Fuse.BuildStageChanged", 
			"Fuse.BuildIssueDetected",
			"Fuse.BuildLogged"]

		if not event.type in validTypes:
			return False

		if event.type == "Fuse.BuildStarted":
			fileName, fileExtension = os.path.splitext(os.path.basename(event.data["ProjectPath"]))
			self.buildViews[event.data["BuildId"]] = BuildView(fileName)
		elif event.type == "Fuse.BuildEnded":
			self.buildViews.pop(event.data["BuildId"])
		else:
			return self.buildViews[event.data["BuildId"]].tryHandleBuildEvent(event)

		return True

class BuildView:
	def __init__(self, name):
		self.queue = queue.Queue()
		self.gotDataEvent = threading.Event()
		self.pollThread = threading.Thread(target = self.__poll)
		self.pollThread.daemon = True
		self.pollThread.start()
		
		window = sublime.active_window()
		self.view = window.new_file()			
		self.view.set_scratch(True)		
		self.view.set_name("Build Result - " + name)
		self.view.set_syntax_file("Packages/Fuse/Build Results.hidden-tmLanguage")

	def tryHandleBuildEvent(self, event):		
		if event.type == "Fuse.BuildLogged":
			self.__write(event.data["Message"])
			return True

		return False

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