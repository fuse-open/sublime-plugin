import subprocess
import threading
import os
import sublime

from .fuse_util import getFusePathFromSettings, getSetting
from .log import log

class BuildManager:
	def __init__(self, fuseNotFoundHandler):
		self.builds = {}
		self.fuseNotFoundHandler = fuseNotFoundHandler
		self.previousBuildCommand = None

	def preview(self, target, path):
		fusePath = getFusePathFromSettings()
		start_preview = [fusePath, "preview", "--target=" + target, "--name=Sublime_Text_3", path]
		name = target.capitalize() + " Preview"
		self._start(target, start_preview, name, None)

	def build(self, target, run, working_dir, error_handler):
		platform = str(sublime.platform())
		if self._isUnsupported(platform, target):
			error_handler(target + " builds are not available on " + platform + ".")
			return

		name =  target.capitalize() + " Build"
		cmd = self._tryCreateBuildCommand(target, run)
		if not cmd:
			error_handler("No Fuse build target set.\n\nGo to Tools/Build With... to choose one.\n\nFuture attempts to build will use that.")
			return
		self.previousBuildCommand = cmd
		self._start(target, cmd, name, working_dir)

	def _tryCreateBuildCommand(self, target, run):
		if target != "Default":
			return [getFusePathFromSettings(), "build", "-t=" + target, "-c=Release"] + (["-r"] if run else [])
		if self.previousBuildCommand:
			return self.previousBuildCommand
		return None

	def _start(self, target, cmd, name, working_dir):
		if name in self.builds:
			self.builds[name].stop()
		build = BuildInstance(cmd, name, working_dir, self.fuseNotFoundHandler)
		self.builds[name] = build
		build.start()

	def _isUnsupported(self, platform, target):
		unsupported = {
			"windows" : [ "ios", "cmake"],
			"osx" : ["dotnet", "msvc"]
		}
		return platform.lower() in unsupported and target.lower() in unsupported[platform]


class BuildInstance(threading.Thread):
	def __init__(self, cmd, title, working_dir, fuseNotFoundHandler):
		threading.Thread.__init__(self)
		self.cmd = cmd
		self.daemon = True
		self.output = OutputView(title) if getSetting("fuse_show_build_results") else NullOutputView()
		self.fuseNotFoundHandler = fuseNotFoundHandler
		self.process = None
		self.working_dir = working_dir

	def run(self):
		log().info("Opening subprocess %s", str(self.cmd))
		try:
			creationflags = 0x08000000 if os.name == "nt" else 0
			self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=creationflags, cwd=self.working_dir)
		except:
			self.fuseNotFoundHandler()
			self.output.close()
			return
		for line in iter(self.process.stdout.readline,b''):
			self.output.append(line.decode("utf-8").replace('\r',''))
		self.process.wait()

	def stop(self):
		if self.process:
			try:
				self.process.kill()
			except ProcessLookupError:
				pass #It died by itself, which is fine
		self.output.close()

class OutputView:
	def __init__(self, title):
		self.title = title
		window = sublime.active_window()
		self.view = window.new_file()
		self.view.set_scratch(True)
		self.view.set_name(title)

	def append(self, line):
		self.view.run_command("append", {"characters": line})

	def close(self):
		try:
			window = self.view.window()
			groupIndex, viewIndex = window.get_view_index(self.view)
			window.run_command("close_by_index", { "group": groupIndex, "index": viewIndex })
		except:
			pass #Failing to close a tab is not critical

class NullOutputView:
	def append(self, line):
		pass

	def close(self):
		pass
