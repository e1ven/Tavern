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
 # $Id: setup.py,v 1.2 2004/02/18 23:05:05 cvs Exp $
 # 
##=============================================================================



from distutils.core import setup, Extension

setup(	
	name		= "yenc",
	version		= "0.3",
	author		= "Alessandro Duca",
	author_email	= "alessandro.duca@gmail.com",
	url		= "http://www.golug.it/yenc.html",
	description	= "yEnc Module for Python",
	license		= "GPL",
	package_dir	= { '': 'lib' },
	py_modules	= ["yenc"],
	ext_modules	= [Extension("_yenc",["src/_yenc.c"],extra_compile_args=["-O2","-g"])]
	)

