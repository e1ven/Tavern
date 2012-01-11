import json
import hashlib
import sys
import os
from keys import *
import collections
from collections import *
json.encoder.c_make_encoder = None
import pymongo
import pprint
import pylzma


class Envelope(object):
        
    class Payload(object):
        def __init__(self,initialdict):
            self.dict = OrderedDict()
            self.dict = initialdict
        def format(self):
            keylist = list(self.dict.keys())
            newdict = OrderedDict()
            for key in sorted(keylist):
                newdict[key] = self.dict[key]
            self.dict = newdict
        def hash(self):
            self.format()
            h = hashlib.sha512()
            h.update(self.text().encode('utf-8'))
            # print "Hashing --" + self.text() + "--"
            return h.hexdigest()
        def text(self): 
            self.format()
            newstr = json.dumps(self.dict,separators=(',',':'))
            return newstr  
        def validate(self):
            if 'author' not in self.dict:
                print("No Author Information")
                return False
            else:
                if 'pubkey' not in self.dict['author']:
                    print("No Pubkey line in Author info")
                    return False
            self.format()
            return True                
                          
    class Message(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                print("Super does not Validate")
                return False
            if 'subject' not in self.dict:
                print("No subject")
                return False
            if 'body' not in self.dict:
                print("No Body")
                return False
            if 'topictag' not in self.dict:
                print("No Topictags")
                return False
            if len(self.dict['topictag']) > 3:
                print("Topictag List too long")
                return False                    
            if 'formatting' not in self.dict:
                print("No Formatting")
                return False            
            return True  
    
    
    class PrivateMessage(Payload):
        def validate(self):
            if not Envelope.Payload(self.dict).validate():
                print("Super does not Validate")
                return False
            if 'to' not in self.dict:
                print("No 'to' field")
                return False
            if 'topictag_list' in self.dict:
                print("Topictag not allowed in privmessage.")
                return False
            return True
            
    class Rating(Payload):
         def validate(self):
             if not Envelope.Payload(self.dict).validate():
                 print("Super fails")
                 return False
             if 'rating' not in self.dict:
                 print("No rating number")
                 return False
             rvalue = self.dict['rating']
             if rvalue not in [-1,0,1]:
                 print("Evelope ratings must be either -1, 1, or 0.")
                 return False
             return True
             
    class UserTrust(Payload):
        def validate(self):
              if not Envelope.Payload(self.dict).validate():
                  return False
              if 'pubkey' not in self.dict:
                  print("No pubkey to set trust for.")
                  return False
              tvalue = self.dict['trust']
              if tvalue not in [-100,0,100]:
                  print("Message ratings must be either -100, 0, or 100")
                  return False
              return True             
                    
                      
    def validate(self):
        #Validate an Envelope   
        #print(self.text())        
        
        #Check headers 
        if 'envelope' not in self.dict:
            print("Invalid Envelope. No Header")
            return False
            
        if self.dict['envelope']['payload_sha512'] != self.payload.hash():
            print("Possible tampering. SHA doesn't match. Abort.")
            return False
           
        #Ensure we have 1 and only 1 author signature stamp        
        stamps = self.dict['envelope']['stamps']
        foundauthor = 0
        for stamp in stamps:
            if (stamp['class'] == "author"):
                foundauthor += 1
        if foundauthor == 0:
            print("No author stamp.")
            return False    
        if foundauthor > 1:
            print("Too Many author stamps")
            return False
        
        #Ensure Every stamp validates.
        stamps = self.dict['envelope']['stamps']
        for stamp in stamps:
            stampkey = Keys(pub=stamp['pubkey'])
            #print(type(self.payload.text()))
            #print(self.payload.text())
            #print(type(stamp['signature']))
            #print(stamp['signature'])
            if stampkey.verify_string(stringtoverify=self.payload.text(),signature=stamp['signature']) != True:
                    print("Signature Failed to verify for stamp :: " + stamp['class'] + " :: " + stamp['pubkey'])
                    return False

        #Do this last, so we don't waste time if the stamps are bad.
        if not self.payload.validate():
                print("Payload does not validate.")
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
        self.dict['envelope']['stamps'] = []
        
        self.payload = Envelope.Payload(self.dict['envelope']['payload'])
   
   
    def registerpayload(self):
        if 'payload' in self.dict['envelope']:
            if 'class' in self.dict['envelope']['payload']:
                if self.dict['envelope']['payload']['class'] == "message":
                    self.payload = Envelope.Message(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "rating":
                    self.payload = Envelope.Rating(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "usertrust":
                    self.payload = Envelope.UserTrust(self.dict['envelope']['payload'])
                elif self.dict['envelope']['payload']['class'] == "privatemessage":
                    self.payload = Envelope.PrivateMessage(self.dict['envelope']['payload'])
                
    def loadstring(self,importstring):
        self.dict = json.loads(importstring,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        self.registerpayload()
        
   
    def loadfile(self,filename):
        
        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)

        #Determine the file extension to see how to parse it.
        basename,ext = os.path.splitext(filename)
        filehandle = open(filename, 'rb')
        filecontents = filehandle.read() 
        if (ext == '.7zPluricEnvelope'):
            #7zip'd JSON
            filecontents = pylzma.decompress(filecontents)
            filecontents = filecontents.decode('utf-8')
        filehandle.close()
        self.loadstring(filecontents)
        
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
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        #pprint.pprint(self.dict)
        newstr = json.dumps(self.dict,separators=(',',':'))
        return newstr

    def prettytext(self):
        self.payload.format() 
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        newstr = json.dumps(self.dict,indent=2,separators=(', ',': '))
        return newstr 
        
    def savefile(self,directory='.'):
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        
        #Compress the whole internal Envelope for saving.
        compressed = pylzma.compress(self.text(),dictionary=27,fastBytes=255)
        # print "Compressed size " + str(sys.getsizeof(compressed))
        # print "Full Size " + str(sys.getsizeof(self.dict))        

        #We want to name this file to the SHA512 of the payload contents, so it is consistant across servers.
        filehandle = open(directory + "/" + self.payload.hash() + ".7zPluricEnvelope",'wb')
        filehandle.write(compressed)
        filehandle.close()
        
    def saveMongo(self):
        self.payload.format()
        self.dict['envelope']['payload'] = self.payload.dict
        self.dict['envelope']['payload_sha512'] = self.payload.hash()
        
        from server import server
        self.dict['_id'] = self.payload.hash()
        server.mongos['default']['envelopes'].save(self.dict)
    
