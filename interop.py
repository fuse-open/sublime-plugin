import socket, traceback, threading, queue
from .log import log

class Interop:
	def __init__(self, on_recv, on_connect, on_not_connected):
		self.readWorker = None
		self.readWorkerStopEvent = None
		self.readBuffer = bytes()
		self.socket = None
		self.on_connect = on_connect
		self.on_recv = on_recv
		self.on_not_connected = on_not_connected
		self.sendWorker = None
		self.sendQueue = queue.Queue()		
		self.sendDataEvent = None
		self.sendWorkerStopEvent = None

	def isConnected(self):	
		isConnected = self.socket != None
		return isConnected

	def connect(self):		
		try:			
			host = "localhost"
			port = 12122
			log().info("Connecting to %s:%d" % (host, port))
			tmpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			tmpSocket.connect((host, port))
		except OSError:
			log().info("Failed to connect to %s:%d" % (host, port))
			tmpSocket.close()
			return
		
		self.socket = tmpSocket
		self.startPullMessages()
		self.startSendMessages()
		self.on_connect()
		log().info("Connected to Fuse")

	def send(self, type, msg):
		if not self.isConnected():
			self.on_not_connected()
			if not self.isConnected():
				return

		self.sendQueue.put((type, msg), True)
		self.sendDataEvent.set()

	def startSendMessages(self):
		self.sendDataEvent = threading.Event()
		self.sendWorkerStopEvent = threading.Event()
		self.sendWorker = threading.Thread(target = self.sendMessages)
		self.sendWorker.daemon = True
		self.sendWorker.start()

	def sendMessages(self):
		try:
			while not self.sendWorkerStopEvent.is_set():
				while not self.sendQueue.empty():
					msgTupple = self.sendQueue.get_nowait()
					type = msgTupple[0]
					msg = msgTupple[1]
					msgInBytes = bytes(type + "\n" + str(len(msg)) + "\n" + msg, "UTF-8")
					self.socket.sendall(msgInBytes)

				self.sendDataEvent.wait()
				self.sendDataEvent.clear()
		except:
			self.disconnect()

	def stopSendMessages(self):
		self.sendWorkerStopEvent.set()
		self.sendDataEvent.set()

	def startPullMessages(self):		
		self.readWorkerStopEvent = threading.Event()
		self.readWorker = threading.Thread(target = self.pullMessages)
		self.readWorker.daemon = True
		self.readWorker.start()

	def stopPullMessages(self):				
		self.readWorkerStopEvent.set()

	def pullMessages(self):
		try:
			while not self.readWorkerStopEvent.is_set():
				tmpData = self.socket.recv(4096)
				if len(tmpData) == 0:
					log().info("Lost connection")
					self.disconnect()
					return

				self.readBuffer = self.readBuffer + tmpData
				self.parseReadData()
		except:
			self.disconnect()
			return

	def parseReadData(self):
		strData = self.readBuffer.decode("utf-8")
		
		firstNewLine = strData.find("\n")
		secondNewLine = strData.find("\n", firstNewLine+1)
		if firstNewLine <= 0 or secondNewLine <= 0:
			return

		typeStr = strData[:firstNewLine]
		lengthStr = strData[firstNewLine+1:secondNewLine]

		length = self.parseLength(lengthStr)
		if length == -1:
			self.readBuffer = b"";
			return

		sizeOfTypeStr = len(bytes(typeStr, "utf-8")) + 1
		sizeOfLengthStr = len(bytes(lengthStr, "utf-8")) + 1
		
		if len(self.readBuffer) - sizeOfLengthStr - sizeOfTypeStr < length:
			return 				

		tmpStr = self.readBuffer[sizeOfLengthStr + sizeOfTypeStr:length + sizeOfLengthStr + sizeOfTypeStr]
		message = (typeStr, tmpStr.decode("utf-8"))
		self.readBuffer = self.readBuffer[sizeOfLengthStr + length + sizeOfTypeStr:]
		self.on_recv(message)
		self.parseReadData()

	def parseLength(self, lenStr):
		try:
			return int(lenStr)
		except ValueError:
			log().info("Couldn't parse packet length, got " + lenStr)
			return -1

	def disconnect(self):		
		log().info("Disconnecting")
		if self.readWorkerStopEvent != None:
			self.stopPullMessages()

		if self.sendWorkerStopEvent != None:
			self.stopSendMessages()

		try:
			if self.socket != None:
				self.socket.shutdown(socket.SHUT_RDWR)
				self.socket.close()		
		except:
			pass
		finally:
			self.socket = None
			self.readWorkerStopEvent = None
			self.readWorker = None
			self.readBuffer = bytes()		

			self.sendWorkerStopEvent = None
			self.sendWorker = None
			self.sendDataEvent = None

			log().info("Disconnected")
