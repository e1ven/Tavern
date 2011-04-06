#!/usr/bin/env python
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
 # $Id: test.py,v 1.2 2004/02/18 23:11:46 cvs Exp $
 # 
##=============================================================================

import yenc
import os
import sys
import time
from binascii import crc32
from stat import *

def main():
	os.system("dd if=/dev/urandom of=sampledata bs=1M count=1")
	file_in = open("sampledata","r")
	file_out = open("sampledata.out","w")
	data = file_in.read()
	file_in.seek(0,0)
	size = len(data)
	crc = hex(crc32(data))[2:]
	print "initial file crc: %s dec: %d" % (crc, crc32(data))
	del(data)
	print "Starting encoding test:"
	startime = time.time()
	bytes_out, crc_out = yenc.encode(file_in, file_out, size)
	secs = time.time() - startime
	print "Bytes out:", bytes_out, "output crc:", crc_out
	if crc != crc_out:
		print "crc error, 1Mb block encoding"
		sys.exit(1)
	elif bytes_out != size:
		print "size error, 1Mb block encoding"
		sys.exit(1)
	else:
		print "crc and size, 1Mb block encoding ok. %f secs." % secs

	file_in.close()
	file_out.close()
	os.unlink("sampledata")
	file_in = open("sampledata.out","r")
	file_out = open("sampledata","w")
	print "Starting decoding test:"
	startime = time.time()
	bytes_out, crc_out = yenc.decode(file_in, file_out, size)
	secs = time.time() - startime
	print "Bytes out:", bytes_out, "output crc:", crc_out
	if crc != crc_out:
		print "crc error, 1Mb block decoding"
		sys.exit(1)
	elif bytes_out != size:
		print "size error, 1Mb block decoding"
		sys.exit(1)
	else:
		print "crc and size, 1Mb block decoding ok. %f secs." % secs
	os.unlink("sampledata")
	os.unlink("sampledata.out")

if __name__ == "__main__":
	main()
