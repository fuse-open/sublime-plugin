import json

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

class MsgParser:
	def Parse(message):
		messageParsed = json.loads(message)		
		messageType = messageParsed["MessageType"]
		dataType = messageParsed["Type"]
		data = messageParsed["Data"]

		if messageType == "Response":
			return Response(dataType, messageParsed["Id"], messageParsed["Status"], messageParsed["Errors"], data)
		elif messageType == "Event":
			return Event(dataType, data)
		else:
			print("Fuse: Message type unknown.")

		return None