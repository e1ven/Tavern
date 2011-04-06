import json
import hashlib
import pylzma,sys
import os

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
            
            
    def __init__(self): 
        self.dict = ['pluric_container']['message']
        self.message = Container.Message(self.dict['pluric_container']['message'])
        
        
    def __init__(self,importfile):
        
        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(importfile)

        filehandle = open(importfile, 'r')
        filecontents = filehandle.read() 
        if (ext == '.PluricContainer'):
            #7zip'd JSON
            filecontents = pylzma.decompress(filecontents)
            print filecontents
        self.dict = json.loads(filecontents)
        filehandle.close()
        self.message = Container.Message(self.dict['pluric_container']['message'])
        
    def text(self): 
        newstr = json.dumps(self.dict,ensure_ascii=False,separators=(',',':'))
        return newstr

    def prettytext(self): 
        newstr = json.dumps(self.dict,ensure_ascii=False,indent=2,separators=(', ',': '))
        return newstr 
        
    def tofile(self):
        #Compress the whole internal container for saving.
        compressed = pylzma.compress(self.text(),dictionary=27,fastBytes=255)

        # print "Compressed size " + str(sys.getsizeof(compressed))
        # print "Full Size " + str(sys.getsizeof(self.dict))        
        
        #We want to name this file to the SHA512 of the MESSAGE contents, so it is consistant across servers.
        filehandle = open(self.message.hash() + ".PluricContainer",'w')
        filehandle.write(compressed)
        filehandle.close()
        
    
        
cont1 = Container('52dfc8ea26abc1c6a23e57b413116f17799a861e1403db5aa4b7c2d6e572c52e0f9885d0fcc4ca5c3cb92d84280c1646ace0f99dbaafefa3c189eadf5ac9cd8f.PluricContainer')
print cont1.prettytext()
print "---------"
print cont1.message.text()
cont1.tofile()
