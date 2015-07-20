import sublime
import os

def getSetting(key,default=None):
	s = sublime.load_settings("Fuse.sublime-settings")
	return s.get(key, default)

def isSupportedSyntax(syntaxName):	
	return syntaxName == "Uno" or syntaxName == "UX"

def getExtension(path):
	base = os.path.basename(path)
	return os.path.splitext(base)[0]

def getRowCol(view, pos):
	rowcol = view.rowcol(pos)
	rowcol = (rowcol[0] + 1, rowcol[1] + 1)
	return {"Line": rowcol[0], "Character": rowcol[1]}