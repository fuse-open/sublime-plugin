import sublime

def GetSetting(key,default=None):
	s = sublime.load_settings("Fuse.sublime-settings")
	return s.get(key, default)