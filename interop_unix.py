import socket
import threading

class InteropUnix:
	def __init__(self, on_recv):
		self.readWorker = None
		self.readWorkerStopEvent = None
		self.socket = None
		self.readFile = None
		self.on_recv = on_recv
		self.socketMutex = threading.Lock()

	def IsConnected(self):
		self.socketMutex.acquire()		
		isConnected = self.socket != None
		self.socketMutex.release()
		return isConnected

	def Connect(self):		
		try:			
			tmpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			tmpSocket.connect(("localhost", 12121))
		except OSError:
			print("Couldn't connect to fuse...")
			return

		self.socketMutex.acquire()			
		self.socket = tmpSocket
		self.socketMutex.release()	
		
		self.readFile = self.socket.makefile("r")
		self.StartPollMessages()				

	def Send(self, msg):
		if not self.IsConnected():
			return;

		try:
			msgInBytes = bytes(str(len(msg)) + "\n" + msg, "UTF-8")
			self.socketMutex.acquire()
			self.socket.sendall(msgInBytes)
			self.socketMutex.release()
		except:
			self.socketMutex.release()
			self.Disconnect()

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
		try:
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
		except:
			pass

	def Disconnect(self):		
		print("Disconnecting...")
		
		if self.readWorkerStopEvent != None:
			self.StopPollMessages()

		try:
			self.socketMutex.acquire()
			if self.socket != None:
				self.socket.shutdown(socket.SHUT_RDWR)
				self.socket.close()
			self.socketMutex.release()
		except:
			self.socketMutex.release()

		if self.readFile != None:
			self.readFile.close()
		
		self.readWorkerStopEvent = None
		self.readFile = None
		self.socket = None
