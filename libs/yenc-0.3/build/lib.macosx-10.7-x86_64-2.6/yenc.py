##=============================================================================
 #
 # Copyright (C) 2003, 2004 Alessandro Duca <alessandro.duca@gmail.com>
 #
 # This program is free software; you can redistribute it and/or
 # modify it under the terms of the GNU General Public License
 # as published by the Free Software Foundation; either version 2
 # of the License, or (at your option) any later version.
 # 
 # This program is distributed in the hope that it will be useful,
 # but WITHOUT ANY WARRANTY; without even the implied warranty of
 # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
 # 
 # See the GNU General Public License for more details.
 # 
 # You should have received a copy of the GNU General Public License
 # along with this program; if not, write to the Free Software
 # Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 #
 #=============================================================================
 #
 # $Id: yenc.py,v 1.2 2004/02/18 23:08:15 cvs Exp $
 # 
##=============================================================================


import sys
from cStringIO import StringIO
import _yenc

E_ERROR		= 64
E_CRC32		= 65
E_PARMS		= 66

class Error(Exception):
	""" 	Class for specific yenc errors
	"""

	def __init__(self, value="", code=E_ERROR):
		self.value = value
		
	def __str__(self):
		return "yenc.Error: %s\n" % self.value, self.value


def _checkArgsType(file_in, file_out, bytes):
	""" 	Internal checkings, not to be used from outside this module
	"""
	
	if bytes < 0: raise Error("No. of bytes can't be negative", E_PARMS)
	if type(file_in) == str:
		if file_in == "-":
			if bytes == 0: raise Error("No. of bytes is 0 or not \
				specified while reading from stdin", E_PARMS)
			file_in = sys.stdin
		else: file_in = open(file_in,"rb")
	if type(file_out) == str:
		if file_out == "-": file_out = sys.stdout
		else: file_out = open(file_out,"wb")
	return file_in, file_out, bytes


def encode(file_in, file_out, bytes=0):
	"""	encode(file_in, file_out, bytes=0): write "bytes" encoded bytes from
		file_in to file_out, if "bytes" is 0 encodes bytes until EOF
	"""
	
	file_in, file_out, bytes = _checkArgsType(file_in, file_out, bytes)
	encoded, crc32 = _yenc.encode(file_in, file_out, bytes)
	crc_hex = hex(crc32)[2:]
	return encoded, crc_hex


def decode(file_in, file_out, bytes=0, crc_in=""):
	""" 	decode(file_in, file_out, bytes=0): write "bytes" decoded bytes from
		file_in to file_out, if "bytes" is 0 decodes bytes until EOF
	"""
	
	file_in, file_out, bytes = _checkArgsType(file_in, file_out, bytes)
	decoded, crc32 = _yenc.decode(file_in, file_out, bytes)
	crc_hex = hex(crc32)[2:]
	if crc_in and not cmp(crc_hex,crc_in.lower()):
		raise Error("crc32 error", E_CRC32)
	else:
		return decoded, crc_hex


class Encoder:
	""" 	class Encoder: facility class for encoding one string at time
	"""
	
	def __init__(self, output_file = None):
		self._buffer = StringIO()
		self._column = 0
		self._output_file = output_file
		self._crc = -1
		self._encoded = 0
		self._terminated = 0

	def __del__(self):
		if(self._output_file):
			self._output_file.flush()
			self._output_file.close()
	
	def feed(self, data):
		"""	Encode some data and write the encoded data 
			into the internal buffer
		"""
		if self._terminated:
			raise IOError("Encoding already terminated")
		encoded, self._crc, self._column = _yenc.encode_string(data, 
							self._crc, self._column)
		self._encoded = self._encoded + len(encoded)
		self._buffer.write(encoded)
		return len(encoded)
	
	def terminate(self):
		"""	Appends the terminal CRLF sequence to the encoded data
		"""
		self._terminated = 1
		self._buffer.write("\r\n")
	
	def flush(self):
		"""	Writes the content of the internal buffer on the file
			passed as argument to the constructor
		"""
		if self._output_file:
			self._output_file.write(self._buffer.getvalue())
			self._buffer = StringIO()
		else:
			raise ValueError("Output file is 'None'")
	
	def getEncoded(self):
		"""	Returns the data in the internal buffer
		"""
		if not self._output_file:
			return self._buffer.getvalue()
		else:
			raise ValueError("Output file is not 'None'")
	
	def getSize(self):
		"""	Returns the total number of encoded bytes (not the size of
			the buffer)
		"""
		return self._encoded

	def getCrc32(self):
		"""	Returns the calculated crc32 string for the clear
			encoded data
		"""
		return "%08x" % (self._crc ^ -1)


class Decoder:
	""" class Decoder: facility class for decoding one string at time
	"""
	
	def __init__(self, output_file = None):
		self._buffer = StringIO()
		self._escape = 0
		self._output_file = output_file
		self._crc = -1
		self._decoded = 0
	
	def __del__(self):
		if(self._output_file):
			self._output_file.flush()
			self._output_file.close()
	
	def feed(self, data):
		"""	Encode some data and write the encoded data 
			into the internal buffer
		"""
		decoded, self._crc, self._escape = _yenc.decode_string(data, self._crc, self._escape)
		self._decoded = self._decoded + len(decoded)
		self._buffer.write(decoded)
		return len(decoded)
	
	def flush(self):
		"""	Writes the content of the internal buffer on the file
			passed as argument to the constructor
		"""
		if self._output_file:
			self._output_file.write(self._buffer.getvalue())
			self._buffer = StringIO()
		else:
			raise ValueError("Output file is 'None'")
	
	def getDecoded(self):
		"""	Returns the data in the internal buffer
		"""
		if not self._output_file:
			return self._buffer.getvalue()
		else:
			raise ValueError("Output file is not 'None'")

	def getSize(self):
		"""	Returns the total number of decoded bytes (not the size of
			the buffer)
		"""
		return self._decoded
	
	def getCrc32(self):
		"""	Returns the calculated crc32 string for the decoded data
		"""
		return "%08x" % (self._crc ^ -1)

