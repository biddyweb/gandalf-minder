from serial import Serial
import time
from time import sleep
from binascii import unhexlify, hexlify
import struct
from avalonHashData import calculateAvalonHashData

start = 0
ser = Serial(port='COM1', baudrate=115200, timeout=0.5)

# low level serial port functions
def writeByte(byte):
	ser.write([byte])

def readByte():
	result = ser.read(1)
	if len(result) == 0:
		return -1
	else:
		return result[0]

# high level communication functions
def sendWord(word):
	print('%08x' % word)
	for i in range(0, 8):
		writeByte(word & 0xf)
		word >>= 4

def sendWords(words):
	for word in words: sendWord(word)

def reset():
	writeByte(0x20)
	sleep(0.3)
	writeByte(0x21)
	sleep(0.3)

def setIdle():
	writeByte(0x10)

# config clock, hash data and start nonce
def configAsic():
	# clock config, comments copied from datasheet
	r = 0
	f = 19
	od = 3
	clock = [
		1 << 0 |  # Bit[0]:Reserved, should be 1.
		1 << 1 |  # Bit[1]:clock  configuration  effect  bit,  if  this  bit  is  0,  all  clock  configuration at current transaction is ineffective.
		1 << 2 |  # Bit[2]:clock frequency effect bit, set to 1 if there are clock divider changes.
		0 << 3 |  # Bit[3]:clock gate, hash unit working clock will be gated it set to 1.
		1 << 4 |  # Bit[4]:clock will divided by 2 if set to 1
		0 << 5 |  # bit[5]:clock switch, hash unit working clock will switch to XCLKIN if set to 1.
		0 << 6 |  # Bit[6]:enable/disable core clock output to PAD, when set to 1, core clock output to PAD CORE_CLOCKOUT is disabled.
		0 << 7 |  # Bit[15:7]:Reserved, should be 0x00000
		r << 16 |  # bit[20:16] clock input divider R
		f << 21 |  # bit[27:21] clock feedback divider F
		od << 28  # bit[29:28] clock output divider OD
		, 0 ]
	# hash unit working clock frequency = XCLKIN frequency * (F+1)/((R+1)*(2^OD)).
	# F, R and OD configuration should satisfy the following three conditions:
	# 10MHz <= XCLKIN/(R+1) <= 50MHz
	# 500MHz <= XCLKIN*(F+1)/(R+1) <= 1000MHz
	# 62.5MHz <= XCLKIN*(F+1)/((R+1)*(2^OD)) <= 1000MHz
	sendWords(clock)
	
	startNonce = expectedNonce - 0x200
	sendWords(calculateAvalonHashData(datastr))
	sendWord(startNonce)
	sendWord(startNonce)
	sendWord(startNonce)

def readWords():
	while True:
		byte = 0
		word = 0
		global start
		end = time.time()
		if end - start > 80:
			print("timeout")
			return
		for i in range(32):
			bit = readByte()
			if bit >= 0:
				word >>= 1
				if bit: word |= 0x80000000
			else:
				break
		if word != 0:
			end = time.time()
			print(end - start)
			start = end
			print('%08x' % (word - 0x180))

def avalonTest():
	# open serial port
	print('testing Avalon chip')
	print()

	# clear receive buffer
	while ser.inWaiting(): readByte()

	# Avalon test
	setIdle()
	reset()
	print('sending:')
	configAsic()
	setIdle()
	global start
	start = time.time()
	print()

	print('receiving:')

	readWords()

	# set reset to 0 at program end
	writeByte(0x20)

# testdata from http://pastebin.com/9p1LALYQ
#datastr = "00000001ab02cd818b9e567ee21793cddef299feb29ad444a41b85b8000008a300000000c2b620e3758dfcff8bdb2304ae42b91e1e950e71aff797d7b09288fc2b12fcf14dd7f5c71a44b9f200000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000"
datastr = "00000002b15704f4ecae05d077e54f6ec36da7f20189ef73b77603225ae56d2b00000000bcf59695a4e35a2f7535e1a86b306a3b08c212bf0b833764018fe39f01919381510c28111c0e8a3700000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000"
# expectedNonce = 0x42a14695
expectedNonce = 0xb2367128

avalonTest()
