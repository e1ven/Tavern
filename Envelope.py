import json
import hashlib
import pylzma,sys
import os
from keys import *
import collections
from collections import *
json.encoder.c_make_encoder = None
import pymongo
import pprint

class Envelope(object):

    class Payload(object):
        def __init__(self,initialdict):
            self.dict = OrderedDict()
            self.dict = initialdict
        def hash(self):
            h = hashlib.sha512()
            h.update(self.text())
            #print "Hashing " + self.text()
            return h.hexdigest()
        def text(self): 
            newstr = json.dumps(self.dict,ensure_ascii=False,separators=(',',':'))
            return newstr  
        def validate(self):
            if not self.dict.has_key('author'):
                print "No Author Information"
                return False
            else:
                if not self.dict['author'].has_key('pubkey'):
                    print "No Pubkey line in Author info"
                    return False
            return True                
                          
    class Message(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                print "Super does not Validate"
                return False
            if not self.dict.has_key('subject'):
                print "No subject"
                return False
            if not self.dict.has_key('body'):
                print "No Body"
                return False
            if self.dict.has_key('topictag_list'):
                #You are allowed to have no topictags.
                #But you can have no more than 3.
                if len(self.dict['topictag_list']) > 3:
                    print "List too long"
                    return False
            return True  
    
    
    class PrivateMessage(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                print "Super does not Validate"
                return False
            if not self.dict.has_key('to'):
                print "No 'to' field"
                return False
            if self.dict.has_key('topictag_list'):
                print "Topictag not allowed in privmessage."
                return False
            return True
            
    class Rating(Payload):
         def validate(self):
             if not Envelope.Payload(self.dict).validate():
                 return False
             if not self.dict.has_key('rating'):
                 print "No rating number"
                 pprint.pprint(self.dict)
                 return False
             rvalue = self.dict['rating']
             if rvalue not in [-1,0,1]:
                 print "Evelope ratings must be either -1, 1, or 0."
                 return False
             return True
             
    class UserTrust(Payload):
        def validate(self):
              if not Envelope.Payload(self.dict).validate():
                  return False
              if not self.dict.has_key('pubkey'):
                  print "No pubkey to set trust for."
                  return False
              tvalue = self.dict['trust']
              if tvalue not in [-100,0,100]:
                  print "Message ratings must be either -100, 0, or 100"
                  return False
              return True             
                     
                  
    def validate(self):
        #Validate an Envelope
        
        
        if not self.dict.has_key('envelope'):
            print "Invalid Evelope. No Header"
            return False
        if not self.dict.has_key('sender_signature'):
            print "No sender signature. Invalid."
            return False        
        if not self.payload.validate():
            print "Payload does not validate."
            return False
        return True    
    class binary(object):
            def __init__(self,hash):
                self.dict = OrderedDict()
                self.dict['sha_512'] = hash
            
                
                
    def __init__(self):
        self.dict = OrderedDict()
        self.dict['envelope'] = OrderedDict()
        self.dict['envelope']['payload'] = OrderedDict()
        self.dict['envelope']['local'] = OrderedDict()
        self.dict['envelope']['local']['citedby'] = []

        self.payload = Envelope.Payload(self.dict['envelope']['payload'])
   
   
    def registerpayload(self):
        if self.dict['envelope'].has_key('payload'):
            if self.dict['envelope']['payload'].has_key('payload_type'):
                if self.dict['envelope']['payload']['payload_type'] == "message":
                    self.payload = Envelope.Message(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['payload_type'] == "rating":
                    self.payload = Envelope.Rating(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['payload_type'] == "usertrust":
                    self.payload = Envelope.UserTrust(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['payload_type'] == "privatemessage":
                    self.payload = Envelope.PrivateMessage(self.dict['envelope']['payload'])
                
    def loadstring(self,importstring):
        self.dict = json.loads(importstring,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        self.registerpayload()
        
   
    def loadfile(self,filename):
        
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
        self.registerpayload()
        filehandle.close()
        
    def loadmongo(self,mongo_id):
        from server import server
        env = server.mongos['default']['envelopes'].find_one({'_id':mongo_id},as_class=OrderedDict)
        if env == None:
            return False
        else:
            self.dict = env
            self.registerpayload()
            return True

        
    def reloadfile(self):
        self.loadfile(self.payload.hash() + ".7zPluricEnvelope")
        self.registerpayload()
        
            
    def text(self):
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict,separators=(',',':'),encoding='utf8')
        return newstr

    def prettytext(self): 
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict,indent=2,separators=(', ',': '))
        return newstr 
        
    def savefile(self):
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        
        #Compress the whole internal Envelope for saving.
        compressed = pylzma.compress(self.text(),dictionary=27,fastBytes=255)

        # print "Compressed size " + str(sys.getsizeof(compressed))
        # print "Full Size " + str(sys.getsizeof(self.dict))        
        
        #We want to name this file to the SHA512 of the payload contents, so it is consistant across servers.
        filehandle = open(self.payload.hash() + ".7zPluricEnvelope",'w')
        filehandle.write(compressed)
        filehandle.close()
        
    def saveMongo(self):
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        
        from server import server
        self.dict['_id'] = self.payload.hash()
        server.mongos['default']['envelopes'].save(self.dict)
    
