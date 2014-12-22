import asyncore, socket
import threading
import sys

class Interop(asyncore.dispatcher):
	def __init__(self, on_recv, on_connect):
		asyncore.dispatcher.__init__(self)
		self.writeBuffer = bytes()
		self.writeBufferMutex = threading.Lock()
		self.readBuffer = bytes()
		self.__isConnected = False
		self.on_recv = on_recv
		self.on_connect = on_connect

	def handle_connect(self):
		print("Connected to Fuse.")
		self.__isConnected = True
		self.on_connect()

	def handle_close(self):
		print("Disconnected from Fuse.")
		self.__isConnected = False
		self.close()		

	def handle_read(self):
		self.readBuffer = self.readBuffer + self.recv(8192)
		self.parseReadData()

	def parseReadData(self):
		strData = self.readBuffer.decode("utf-8")
		firstNewLine = strData.find("\n")
		if firstNewLine <= 0:
			return

		lengthStr = strData[:firstNewLine]
		length = self.parseLength(lengthStr)
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
			print("Couldn't parse packet.")
			return 2147483647

	def handle_write(self):
		sent = self.send(self.writeBuffer)
		with self.writeBufferMutex:
			self.writeBuffer = self.writeBuffer[sent:]

	def IsConnected(self):
		return self.__isConnected

	def Connect(self):
		print("Trying to connect to fuse")
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)		
		self.connect(("localhost", 12122))

	def Send(self, msg):
		if not self.IsConnected():
			return;

		msgInBytes = bytes(str(len(msg)) + "\n" + msg, "UTF-8")

		with self.writeBufferMutex:
			self.writeBuffer = self.writeBuffer + msgInBytes		

	def Disconnect(self):
		self.handle_close()