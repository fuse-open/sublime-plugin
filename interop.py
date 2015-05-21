import socket
import threading

class Interop:
	def __init__(self, on_recv, on_connect):
		self.readWorker = None
		self.readWorkerStopEvent = None
		self.readBuffer = bytes()
		self.socket = None
		self.on_connect = on_connect
		self.on_recv = on_recv

	def IsConnected(self):	
		isConnected = self.socket != None
		return isConnected

	def Connect(self):		
		try:			
			tmpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			tmpSocket.connect(("localhost", 12122))
		except OSError:
			tmpSocket.close()
			return
		
		self.socket = tmpSocket
		self.startPollMessages()
		self.on_connect()
		print("Connected to Fuse")		

	def Send(self, msg):
		if not self.IsConnected():
			return;

		try:
			msgInBytes = bytes(str(len(msg)) + "\n" + msg, "UTF-8")
			self.socket.sendall(msgInBytes)
		except:
			self.Disconnect()

	def startPollMessages(self):		
		self.readWorkerStopEvent = threading.Event()
		self.readWorker = threading.Thread(target = self.pollMessages)
		self.readWorker.daemon = True
		self.readWorker.start()

	def stopPollMessages(self):				
		self.readWorkerStopEvent.set()

	def pollMessages(self):
		try:
			while not self.readWorkerStopEvent.is_set():
				tmpData = self.socket.recv(4096)
				if len(tmpData) == 0:
					print("Lost connection")
					self.Disconnect()
					return

				self.readBuffer = self.readBuffer + tmpData
				self.parseReadData()
		except:
			self.Disconnect()
			return

	def parseReadData(self):
		strData = self.readBuffer.decode("utf-8")
		firstNewLine = strData.find("\n")
		if firstNewLine <= 0:
			return

		lengthStr = strData[:firstNewLine]
		length = self.parseLength(lengthStr)
		if length == -1:
			self.readBuffer = b"";
			return

		sizeOfLengthStr = len(bytes(lengthStr, "utf-8")) + 1
		if len(self.readBuffer) - sizeOfLengthStr < length:
			return 		

		tmpStr = self.readBuffer[sizeOfLengthStr:length + sizeOfLengthStr]
		message = tmpStr.decode("utf-8")
		self.readBuffer = self.readBuffer[sizeOfLengthStr + length:]
		self.on_recv(message)
		self.parseReadData()

	def parseLength(self, lenStr):
		try:
			return int(lenStr)
		except ValueError:
			print("Couldn't parse packet length, got " + lenStr)
			return -1

	def Disconnect(self):		
		if self.readWorkerStopEvent != None:
			self.stopPollMessages()

		try:
			if self.socket != None:
				self.socket.shutdown(socket.SHUT_RDWR)
				self.socket.close()		
		except:
			pass
		finally:
			self.socket = None
			self.readWorkerStopEvent = None
			self.readBuffer = bytes()		

			print("Disconnected")
