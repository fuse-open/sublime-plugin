import os

def isSupportedSyntax(syntaxName):	
	return syntaxName == "Uno" or syntaxName == "UX"

def getSyntax(view):
	try:
		return view.settings().get("syntax").split("/")[-1].split(".")[0]
	except:
		return ""

def getExtension(path):
	if path is None:
		return ""
		
	base = os.path.basename(path)
	ext = os.path.splitext(base)

	if ext is None:
		return ""
	else:
		return ext[1].strip(".")

def getRowCol(view, pos):
	rowcol = view.rowcol(pos)
	rowcol = (rowcol[0] + 1, rowcol[1] + 1)
	return {"Line": rowcol[0], "Character": rowcol[1]}
