import socket
import threading

class InteropUnix:
	def __init__(self, on_recv):
		self.readWorker = None
		self.readWorkerStopEvent = None
		self.socket = None
		self.readFile = None
		self.on_recv = on_recv

	def IsConnected(self):
		return self.socket != None

	def Connect(self):
		print("Connecting to fuse...")
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.connect(("localhost", 12000))
			self.readFile = self.socket.makefile("r")
			self.StartPollMessages()
		except OSError:
			print("Couldn't connect to fuse...")

	def Send(self, msg):
		try:
			msgInBytes = bytes(str(len(msg)) + "\n" + msg, "UTF-8")
			self.socket.sendall(msgInBytes)
		except:
			pass
			#self.Disconnect()

	def StartPollMessages(self):		
		self.readWorkerStopEvent = threading.Event()
		self.readWorker = threading.Thread(target = self.PollMessage)
		self.readWorker.daemon = True
		self.readWorker.start()

		print("Starting to poll messages")

	def StopPollMessages(self):				
		self.readWorkerStopEvent.set()
		print ("Stopping message poll")

	def PollMessage(self):
		while not self.readWorkerStopEvent.is_set():
			lengthStr = self.readFile.readline()
			if len(lengthStr) == 0 or lengthStr == "":
				self.readWorkerStopEvent.set()
				break

			length = int(lengthStr)
			msg = self.readFile.read(length)
			if len(msg) == 0 or msg == "":
				self.readWorkerStopEvent.set()
				break

			self.on_recv(msg)

	def Disconnect(self):		
		print("Disconnecting...")
		
		if self.readWorkerStopEvent != None:
			self.readWorkerStopEvent.set()
		
		if self.readFile != None:
			self.readFile.close()
		
		if self.socket != None:
			self.socket.close()
		
		self.readWorkerStopEvent = None
		self.readFile = None
		self.socket = None