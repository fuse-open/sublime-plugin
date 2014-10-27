import sublime, sublime_plugin

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
	
	def __CreateViewModel(self):
		self.__output = "- Errors -\n"

	def AddError(self, cmd):
		filePath = cmd["Path"]
		startLine = cmd["StartPosition"]["Line"]
		message = cmd["Message"]		

		self.__output += "\n{Path}:\n   {Line}: - {Message} -\n".format(Path = filePath, Line = startLine, Message = message)
		self.Show()

	def Show(self):
		window = sublime.active_window()
		window.run_command("build_results", { "data": self.__output })

class BuildResultsCommand(sublime_plugin.WindowCommand):
	def run(self, data):		
		window = self.window
		view = window.create_output_panel("FuseBuildResults")
		view.set_read_only(False)
		view.set_name("Fuse - Build Results")		
		view.set_syntax_file("Packages/Fuse/Build Results.tmLanguage")		
		view.run_command("append", {"characters": data})

		view.fold(FileRegions(view))
		view.set_read_only(True)
		window.run_command("show_panel", {"panel": "output.FuseBuildResults"})

class GotoLocationCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		window = view.window()
		sel = view.sel()[0]
		scope = view.scope_name(sel.a)

		if scope.find(".name.") > -1:
			filePath = view.substr(view.extract_scope(sel.a))
			window.open_file(filePath+":0", sublime.ENCODED_POSITION)
		else:
			allLocations = view.find_by_selector("constant.numeric.line-number.match.find-in-files")
			foundSelLoc = None
			for location in allLocations:
				if view.line(location).contains(sel):
					foundSelLoc = location
					break

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
					if region.intersects(foundRegion) == True:
						filePath = view.substr(view.extract_scope(region.a+1))
						line = view.substr(foundSelLoc)						
						window.open_file(filePath+":" + line, sublime.ENCODED_POSITION)
						break



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
