import json
import hashlib
import pylzma,sys
import os
from keys import *

class Container(object):

    class Message(object):
        def __init__(self):
            self.dict = []
        def __init__(self,initialdict):
            self.dict = initialdict
        def text(self): 
            newstr = json.dumps(self.dict,ensure_ascii=False,separators=(',',':'))
            return newstr   
        def hash(self):
            h = hashlib.sha512()
            h.update(self.text())
            #print "Hashing " + self.text()
            return h.hexdigest()         
            
        
    def __init__(self,importfile=None,importstring=None):
        
        if importfile != None:
           self.load(importfile)        
        else:
            if importstring != None:
                self.dict = json.loads(importstring)
            else:
                self.dict = ['pluric_container']['message']
        
        self.message = Container.Message(self.dict['pluric_container']['message'])
   
   
    def load(self,filename):
        
        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)

        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)
        filehandle = open(filename, 'r')
        filecontents = filehandle.read() 
        if (ext == '.7zPluricContainer'):
            #7zip'd JSON
            filecontents = pylzma.decompress(filecontents)
        self.dict = json.loads(filecontents)
        filehandle.close()
        
        
    def reload(self):
        self.load(self.message.hash() + ".7zPluricContainer")
            
    def text(self):
        newstr = json.dumps(self.dict,separators=(',',':'),encoding='utf8')
        return newstr

    def prettytext(self): 
        newstr = json.dumps(self.dict,indent=2,separators=(', ',': '))
        return newstr 
        
    def tofile(self):
        #Compress the whole internal container for saving.
        compressed = pylzma.compress(self.text(),dictionary=27,fastBytes=255)

        # print "Compressed size " + str(sys.getsizeof(compressed))
        # print "Full Size " + str(sys.getsizeof(self.dict))        
        
        #We want to name this file to the SHA512 of the MESSAGE contents, so it is consistant across servers.
        filehandle = open(self.message.hash() + ".7zPluricContainer",'w')
        filehandle.write(compressed)
        filehandle.close()
        
    