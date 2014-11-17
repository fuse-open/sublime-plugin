import sublime, sublime_plugin
from Fuse.fuse_util import *

paths = []
outputPanel = None

def NameRegions(view):
	return view.find_by_selector("entity.name.filename.find-in-files")

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
	def __init__(self):
		self.__output = ""
		self.__CreateViewModel()
		global paths	
		paths = []

	def __CreateViewModel(self):
		self.__output = "- Build Result -\n"

	def Add(self, cmd):
		filePath = cmd["Path"]
		startLine = cmd["StartPosition"]["Line"]
		message = cmd["Message"]
		eventType = cmd["Type"]				

		fileData = LoadFile(filePath)
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

		paths.append([len(self.__output) + 1, filePath, line])		

		if eventType == "Error" or eventType == "FatalError" or eventType == "Warning":
			self.__output += "\n{Message} - {Path}:\n{DataBefore}   {Line}:{LineData}\n{DataAfter}".format(
				Path = filePath, Line = startLine, LineData = lines[line-1], Message = message, DataBefore = dataBefore, DataAfter = dataAfter)
		else:
			self.__output += "\n{Message} - {Path}:\n{DataBefore}   {Line}{LineData}\n{DataAfter}".format(
				Path = filePath, Line = startLine, LineData = lines[line-1], Message = message, DataBefore = dataBefore, DataAfter = dataAfter)

		self.Show()

	def Show(self):
		window = sublime.active_window()
		window.run_command("build_results", { "data": self.__output })

	def Close(self):
		global outputPanel

		if outputPanel:
			sublime.active_window().run_command("hide_panel", {"cancel": True})
			outputPanel = None
		else:
			self.Show()

class BuildResultsCommand(sublime_plugin.WindowCommand):
	def run(self, data):
		global outputPanel

		window = self.window
		view = window.create_output_panel("FuseBuildResults")
		outputPanel = view
		view.set_read_only(False)
		view.set_name("Fuse - Build Results")		
		view.set_syntax_file("Packages/Fuse/Build Results.hidden-tmLanguage")		
		view.run_command("append", {"characters": data})

		view.fold(FileRegions(view))
		view.set_read_only(True)

		codePoints = view.find_by_selector("constant.numeric.line-number.match.find-in-files")
		lines = []
		for codePoint in codePoints:
			lines.append(view.line(codePoint))

		view.add_regions("errors", lines, "keyword", "bookmark", 
			sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.PERSISTENT | sublime.DRAW_SQUIGGLY_UNDERLINE)

		window.run_command("show_panel", {"panel": "output.FuseBuildResults"})

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
				

text = r"""- Errors -

C:\Users\Emil\AppData\Roaming\Sublime Text 3\Packages\Fuse\fuse.py:
   11  interop = None
   12  
   13: def Recv(msg):
   14  	command = json.loads(msg)
   15  	parsedRes = CmdParser.ParseCommand(command)
   ..
   72  	closeEvent = threading.Event()
   73  
   74: 	interop = InteropUnix(Recv)
   75  
   76  	thread = threading.Thread(target = TryConnect)

C:\Users\Emil\AppData\Roaming\Sublime Text 3\Packages\Fuse\interop_unix.py:
    3  
    4  class InteropUnix:
    5: 	def __init__(self, on_recv):
    6  		self.readWorker = None
    7  		self.readWorkerStopEvent = None
    8  		self.socket = None
    9  		self.readFile = None
   10: 		self.on_recv = on_recv
   11  		self.socketMutex = threading.Lock()
   12  
   ..
   71  					break
   72  
   73: 				self.on_recv(msg)
   74  		except:
   75  			pass

C:\Users\Emil\AppData\Roaming\Sublime Text 3\Packages\Fuse\Uno.tmLanguage:
  142  				<dict>
  143  					<key>match</key>
  144: 					<string>\b(bool|byte|byte2|byte4|sbyte|sbyte2|sbyte4|char|decimal|double|float|float2|float3|float4|float3x3|float4x4|int|int2|int3|int4|uint|long|ulong|object|short|short2|short4|ushort|ushort2|ushort4|string|texture2D|texture3D|textureCube|sampler2D|sampler3D|samplerCube|framebuffer|void|class|block|struct|enum|interface)\b</string>
  145  					<key>name</key>
  146  					<string>storage.type.source.uno</string>

C:\RealtimeStudio\Uno\UnoDevelop\Source\Tests\Outracks.EditorService.Tests\SublimeTest\SublimeTest\MyApp.ux:
    3     	
    4      <Button ux:Name="hehe">
    5:     	<Rectangle CornerRadius="20">
    6      		<SolidColor Opacity="0.5" Color="1,0,0,1" />
    7:     	</Rectangle>
    8      	<Circle>
    9      		<LinearGradient>
   ..
   13      	</Circle>
   14  
   15:     	<Rectangle Margin="20" />
   16      </Button>    
   17    </Panel>	

C:\RealtimeStudio\Uno\UnoDevelop\Source\Tests\Outracks.EditorService.Tests\SublimeTest\SublimeTest\.CodeNinja\Cache\SublimeTest\MyApp.ux.g.uno:
   13          var node = new Fuse.Controls.Panel();
   14          hehe = new Fuse.Controls.Button();
   15:         var node2 = new Fuse.Shapes.Rectangle()
   16          {
   17              CornerRadius = 20f
   ..
   29          };
   30          var node7 = new Fuse.Drawing.SolidColor();
   31:         var node8 = new Fuse.Shapes.Rectangle();
   32          this.ClearColor = float4(1f, 1f, 1f, 1f);
   33          this.RootNode = node;

!================================================================================================================================================
10 Errors, 2 Warnings

"""
