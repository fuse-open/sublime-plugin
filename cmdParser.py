import json

class CmdParser:
	def ParseCommand(cmdData):
		cmdName = cmdData["Command"]
		cmdValue = json.loads(cmdData["Arguments"])

		return (cmdName, cmdValue)