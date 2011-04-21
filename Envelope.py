import json
import hashlib
import pylzma,sys
import os
from keys import *
import collections
from collections import *
json.encoder.c_make_encoder = None
import pymongo


class Envelope(object):

    class Message(object):
        def __init__(self,initialdict):
            self.dict = OrderedDict()
            self.dict = initialdict
        def text(self): 
            newstr = json.dumps(self.dict,ensure_ascii=False,separators=(',',':'))
            return newstr   
        def hash(self):
            h = hashlib.sha512()
            h.update(self.text())
            #print "Hashing " + self.text()
            return h.hexdigest()     
        def validate(subject,body,user,topictag_list,to_list,regarding,coords):
            if hasattr(self.dict,'subject') == False:
                print "No subject"
                return False
            if hasattr(self.dict,'body') == False:
                print "No Body"
                return False
            if hasattr(self.dict,'topictag_list') == False:
                #You are allowed to have no topictags.
                #But you can have no more than 3.
                if self.dict['topictag_list'].len() > 3:
                    print "List too long"
                    return False
            if hasattr(self.dict,'author') == False:
                print "No Author Information"
                return False
            else:
                if hasattr(self.dict['author'],'from') == False:
                    print "No From line"
                    return False
                
    def __init__(self,importfile=None,importstring=None):
        
        if importfile != None:
           self.load(importfile)        
        else:
            if importstring != None:
                self.dict = json.loads(importstring,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
            else:
                self.dict = OrderedDict()
                self.dict['pluric_envelope'] = OrderedDict()
                self.dict['pluric_envelope']['message'] = OrderedDict()
        
        self.message = Envelope.Message(self.dict['pluric_envelope']['message'])
   
   
    def load(self,filename):
        
        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)

        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)
        filehandle = open(filename, 'r')
        filecontents = filehandle.read() 
        if (ext == '.7zPluricEnvelope'):
            #7zip'd JSON
            filecontents = pylzma.decompress(filecontents)
        self.dict = OrderedDict()
        self.dict = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        filehandle.close()
        
        
    def reload(self):
        self.load(self.message.hash() + ".7zPluricEnvelope")
            
    def text(self):
        newstr = json.dumps(self.dict,separators=(',',':'),encoding='utf8')
        return newstr

    def prettytext(self): 
        newstr = json.dumps(self.dict,indent=2,separators=(', ',': '))
        return newstr 
        
    def tofile(self):
        #Compress the whole internal Envelope for saving.
        compressed = pylzma.compress(self.text(),dictionary=27,fastBytes=255)

        # print "Compressed size " + str(sys.getsizeof(compressed))
        # print "Full Size " + str(sys.getsizeof(self.dict))        
        
        #We want to name this file to the SHA512 of the MESSAGE contents, so it is consistant across servers.
        filehandle = open(self.message.hash() + ".7zPluricEnvelope",'w')
        filehandle.write(compressed)
        filehandle.close()
        
    def toMongo(self,mongo):
        self.dict['_id'] = self.message.hash()
        mongo['envelop1'].insert(self.dict)
    