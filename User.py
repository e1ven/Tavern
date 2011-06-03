import os,json
import M2Crypto
import platform
from Envelope import *
import time
from keys import *
import logging
import bcrypt
from collections import OrderedDict
import pymongo
from server import server

class User(object):
      
    def __init__(self):
        self.UserSettings = OrderedDict()

    def generate(self,email=None,hashedpass=None,pubkey=None,username=None):
        self.UserSettings['username'] = username
        self.UserSettings['friendlyname'] = username
        #username is specific to this service.
        #Move it to <local> ?
        #Friendlyname is the displayedname
        self.UserSettings['email'] = email
        self.UserSettings['hashedpass'] = hashedpass
        self.Keys = Keys()
        self.Keys.generate()
        self.UserSettings['privkey'] = self.Keys.privkey
        self.UserSettings['pubkey'] = self.Keys.pubkey
        
        gmttime = time.gmtime()
        gmtstring = time.strftime("%Y-%m-%dT%H:%M:%SZ",gmttime)
    
        self.UserSettings['time_created'] = gmtstring
            
    def load_file(self,filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.UserSettings = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        filehandle.close()    
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
        
    def savefile(self,filename=None):
        if filename == None:
            filename = self.UserSettings['username'] + ".PluricUser"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.UserSettings,ensure_ascii=False,separators=(u',',u':'))) 
        filehandle.close()
    
    def load_mongo_by_pubkey(self,pubkey):
        user = server.mongo['users'].find_one({"pubkey":pubkey},as_class=OrderedDict)
        self.UserSettings = user
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])


    def load_mongo_by_username(self,username):
        #Local server Only
        user = server.mongo['users'].find_one({"username":username},as_class=OrderedDict)
        self.UserSettings = user
        self.Keys = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
 

    def savemongo(self):
        self.UserSettings['_id'] = self.UserSettings['pubkey']
        server.mongo['users'].save(self.UserSettings) 
            
