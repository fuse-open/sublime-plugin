import os
import sublime
import subprocess

from .log import log

class FocusEditorService:

	def __init__(self, msgManager, interop):
		self.msgManager = msgManager
		self.interop = interop

	def publish(self):
		self.msgManager.sendRequestAsync(
			self.interop,
			"PublishService",
			{
			"RequestNames" : ["FocusEditor"]
			},
			self.focusEditorServiceSuccess)

	def focusEditorServiceSuccess(self, _):
		log().info("Successfully registered FocusEditor service")

	def tryHandle(self, request):
		if request.name != "FocusEditor":
			return false
		if self._projectIsOpen(request.arguments["Project"]):
			fileName = request.arguments["File"]
			line = request.arguments["Line"]
			column = request.arguments["Column"]
			if not os.path.isfile(fileName):
				msg = "File '{}' does not exist".format(fileName)
				log().info("FocusEditorService: " + msg)
				self.msgManager.sendResponse(self.interop, request.id, "Error", {}, [{"Code":2, "Message": msg}])
				return True
			window = sublime.active_window()
			view = window.open_file( "{}:{}:{}".format(fileName, line, column), sublime.ENCODED_POSITION)
			if sublime.platform() == "osx":
				self._focusWindowOSX()
				self.msgManager.sendResponse(self.interop, request.id, "Success")
				return True
			elif sublime.platform() == "windows":
				self.msgManager.sendResponse(self.interop, request.id, "Success", {"FocusHwnd":window.hwnd()})
				return True
		return False

	def _projectIsOpen(self, project):
		if not os.path.isfile(project):
			return False
		for folder in sublime.active_window().folders():
			if project.startswith(folder):
				return True
		return False

	def _focusWindowOSX(self):
		cmd = """
			tell application "System Events"
				activate application "Sublime Text"
			end tell"""
		subprocess.Popen(['/usr/bin/osascript', "-e", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
