import struct
import threading

class Interop:
	def __init__(self, on_recv):
		self.inputPipe = None
		self.outputPipe = None
		self.pipeWorker = None
		self.pipeWorkerStopEvent = None
		self.on_recv = on_recv

	def IsConnected(self):
		return self.inputPipe != None and self.outputPipe != None;

	def Connect(self):
		print("Connecting...")
		self.inputPipe = open(r'\\.\pipe\FuseOutput', "rb")
		self.outputPipe = open(r"\\.\pipe\FuseInput", "wb")
		self.StartPollMessages()

	def Send(self, msg):
		msgInBytes = bytes(str(len(msg)) + "\n" + msg, "UTF-8")
		self.outputPipe.write(msgInBytes)
		self.outputPipe.seek(0)

	def StartPollMessages(self):		
		self.pipeWorkerStopEvent = threading.Event()
		self.pipeWorker = threading.Thread(target = self.PollMessage)
		self.pipeWorker.daemon = True
		self.pipeWorker.start()

		print("Starting to poll messages")

	def StopPollMessages(self):				
		self.pipeWorkerStopEvent.set()
		print ("Stopping message poll")		

	def PollMessage(self):
		while not self.pipeWorkerStopEvent.is_set():
			if self.inputPipe is None:
				break

			lengthStr = self.inputPipe.readline()			
			if len(lengthStr) == 0 or lengthStr == "":
				self.pipeWorkerStopEvent.set()
				break

			length = int(lengthStr)

			msg = self.inputPipe.read(length)
			if len(msg) == 0 or msg == "":
				self.pipeWorkerStopEvent.set()
				break

			self.on_recv(msg.decode("utf-8"))

	def Disconnect(self):		
		print("Disconnecting...")
		self.StopPollMessages()
		if self.outputPipe:
			self.outputPipe.close()
			self.outputPipe = None
		if self.inputPipe:
			self.inputPipe.close()
			self.inputPipe = None