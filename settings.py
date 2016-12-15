import sublime

def getSetting(key,default=None):
	s = sublime.load_settings("Fuse.sublime-settings")
	return s.get(key, default)

def getFusePathFromSettings():
	path = getSetting("fuse_path_override")
	if path == "" or path == None:
		return "fuse"
	else:
		return path+"/fuse"

def setSetting(key,value):
	s = sublime.load_settings("Fuse.sublime-settings")
	s.set(key, value)
	sublime.save_settings("Fuse.sublime-settings")
