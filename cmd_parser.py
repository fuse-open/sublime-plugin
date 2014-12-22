import json

class CmdParser:
	def ParseCommand(cmdData):
		cmdParsed = json.loads(cmdData)
		cmdName = cmdParsed["Command"]
		cmdValue =  json.loads(cmdParsed["Arguments"])

		return (cmdName, cmdValue)