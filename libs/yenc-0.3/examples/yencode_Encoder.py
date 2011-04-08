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
 # $Id: yencode_Encoder.py,v 1.2 2004/02/18 23:09:30 cvs Exp $
 # 
##=============================================================================


import sys
import os
import os.path
import yenc
import getopt
from stat import *
from binascii import crc32

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:], "o:")
	except getopt.GetoptError:
		usage()
	file_out = sys.stdout
	for o,a in opts:
		if o == '-o':
			file_out = open(a,"w")
	if args:
		filename = args[0]
		if os.access( filename, os.F_OK | os.R_OK ):
			file_in = open(filename,"r")
		else:
			print "couldn't access %s" % filename
			sys.exit(2)
	else:
		usage()
	crc = hex( crc32( open(filename,"r").read() ) )[2:]
	name = os.path.split(filename)[1]
	size = os.stat(filename)[ST_SIZE]
	file_out.write("=ybegin line=128 size=%d crc32=%s name=%s\r\n" % (size, crc, name) )
	file_in = open(filename, "r")
	encoder = yenc.Encoder(file_out)
	while True:
		data_in = file_in.read(1024)
		encoder.feed(data_in)
		encoder.flush()
		if len(data_in) < 1024: break
	encoder.terminate()
	encoder.flush()
	file_out.write("=yend size=%d crc32=%s\r\n" % (size, encoder.getCrc32()) )
	

def usage():
	print "Usage: yencode2.py <-o outfile> filename"
	sys.exit(1)
	
if __name__ == "__main__":
	main()
