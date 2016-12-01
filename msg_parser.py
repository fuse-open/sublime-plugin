import json, threading, logging

class Message:
	def __init__(self, messageType):
		self.messageType = messageType

class Request(Message):
	def __init__(self, name, id, arguments):
		super(Request, self).__init__("Request")
		self.name = name
		self.id = id
		self.arguments = arguments

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

		interop.send("Request", 
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

		if res['name'] == "Hello":
			logging.getLogger(__name__).info("Got Hello response")
		if (res["response"] != None and res["response"].errors != None and len(res["response"].errors) > 0):
			logging.getLogger(__name__).info("Errors in response: '%s'", str(res["response"].errors))
		return res["response"]

	def sendRequestAsync(self, interop, requestName, arguments, callback):
		curId = 0
		with self.id_lock:
			self.curId += 1
			curId = self.curId

		self.requestsPending[curId] = {"name": requestName, "callback": lambda res : self.callCallback(curId, res, callback)} 

		interop.send("Request", 
			json.dumps(
			{
				"Id": curId,
				"Name": requestName,
				"Arguments": arguments
			}))

	def sendEvent(self, interop, eventName, data):
		interop.send("Event", 
			json.dumps(
			{
				"Name": eventName,
				"Data": data
			}))

	def sendResponse(self, interop, id, status, result={}, errors=[]):
		interop.send("Response",
			json.dumps(
			{
				"Id": id,
				"Status": status,
				"Result": result,
				"Errors": errors
			}))

	def callCallback(self, curId, response, callback):
		self.requestsPending.pop(curId)
		callback(response)

	def parse(self, message):
		messageParsed = json.loads(message[1])		
		messageType = message[0];		

		if messageType == "Response":
			resId = messageParsed["Id"]
			if resId in self.requestsPending:
				name = self.requestsPending[resId]["name"]
				response = Response(name, messageParsed["Id"], messageParsed["Status"], messageParsed["Errors"], messageParsed["Result"])
				if "event" in self.requestsPending[resId].keys():
					self.requestsPending[resId]["response"] = response
					self.requestsPending[resId]["event"].set()
				else:
					self.requestsPending[resId]["callback"](response)
		elif messageType == "Event":
			return Event(messageParsed["Name"], messageParsed["Data"])
		elif messageType == "Request":
			return Request(messageParsed["Name"], messageParsed["Id"], messageParsed["Arguments"])
		else:
			logging.getLogger(__name__).info("Fuse: Message type '" + messageType + "' unknown.")

		return None
