import json, threading

class Message:
	def __init__(self, messageType):
		self.messageType = messageType

class Response(Message):
	def __init__(self, type, id, status, errors, data):
		super(Response, self).__init__("Response")
		self.type = type
		self.id = id
		self.status = status
		self.errors = errors
		self.data = data

class Event(Message):
	def __init__(self, type, data):
		super(Event, self).__init__("Event")
		self.type = type
		self.data = data

class MsgManager:
	curId = 0
	requestsPending = {}

	def __init__(self):
		self.id_lock = threading.RLock()		

	def sendRequest(self, interop, requestName, arguments, timeout=2):
		curId = 0
		with self.id_lock:
			self.curId += 1
			curId = self.curId

		waitForResponse = threading.Event()
		self.requestsPending[curId] = {"name": requestName, "event": waitForResponse} 

		interop.Send("Request", 
		json.dumps(
		{
			"Id": curId,
			"Name": requestName,
			"Arguments": arguments
		}))

		waitResult = waitForResponse.wait(timeout)
		res = self.requestsPending[curId]
		self.requestsPending.pop(curId)
		if not waitResult:
			return None

		return res["response"]

	def parse(self, message):
		messageParsed = json.loads(message[1])		
		messageType = message[0];		

		if messageType == "Response":
			resId = messageParsed["Id"]
			if resId in self.requestsPending:
				name = self.requestsPending[resId]["name"]			
				self.requestsPending[resId]["response"] = Response(name, messageParsed["Id"], messageParsed["Status"], messageParsed["Errors"], messageParsed["Result"])
				self.requestsPending[resId]["event"].set()
		elif messageType == "Event":
			return Event(messageParsed["Name"], messageParsed["Data"])
		else:
			print("Fuse: Message type unknown.")

		return None