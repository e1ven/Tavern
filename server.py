import os,json
import M2Crypto
import platform
import time
from keys import *
import logging
import bcrypt
import collections
from collections import OrderedDict
import collections
import pymongo
from gridfs import GridFS
from Envelope import Envelope
import sys
class Server(object):

    def __init__(self,settingsfile=None):            
        self.ServerSettings = OrderedDict()
        if settingsfile == None:
            if os.path.isfile(platform.node() + ".PluricServerSettings"):
                #Load Default file(hostnamestname)
                self.loadconfig()
            else:
                #Generate New config   
                print "Generating new Config" 
                self.ServerKeys = Keys()
                self.ServerKeys.generate()
                self.ServerSettings = OrderedDict()
                self.ServerSettings['pubkey'] = self.ServerKeys.pubkey
                self.ServerSettings['privkey'] = self.ServerKeys.privkey
                self.ServerSettings['hostname'] = platform.node()
                self.ServerSettings['logfile'] = self.ServerSettings['hostname'] + '.log'
                self.ServerSettings['mongo-hostname'] = 'localhost'
                self.ServerSettings['mongo-port'] = 27017            
                self.ServerSettings['mongo-db'] = 'test'  
                self.ServerSettings['bin-mongo-hostname'] = 'localhost'
                self.ServerSettings['bin-mongo-port'] = 27017
                self.ServerSettings['bin-mongo-db'] = 'test'
                self.ServerSettings['uplaod-dir'] = '/opt/uploads'
                self.connection = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'])
                self.mongo = self.connection[self.ServerSettings['mongo-db']]             
                self.bin_connection = pymongo.Connection(self.ServerSettings['bin-mongo-hostname'], self.ServerSettings['bin-mongo-port'])
                self.bin_mongo = self.connection[self.ServerSettings['bin-mongo-db']]
                self.bin_GridFS = GridFS(self.bin_mongo)
                self.saveconfig()   
        else:
            self.loadconfig(settingsfile)
            
        #logging.basicConfig(filename=self.ServerSettings['logfile'],level=logging.DEBUG)
        logging.basicConfig(stream=sys.stdout,level=logging.DEBUG)
 
    def loadconfig(self,filename=None):
        print "Loading config from file."
        if filename == None:
            filename = platform.node() + ".PluricServerSettings"
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.ServerSettings = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        self.ServerKeys = Keys(pub=self.ServerSettings['pubkey'],priv=self.ServerSettings['privkey'])
        self.connection = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'])
        self.mongo = self.connection[self.ServerSettings['mongo-db']]
        self.ServerSettings['upload-dir'] = '/opt/uploads'
        self.ServerSettings['bin-mongo-hostname'] = 'localhost'
        self.ServerSettings['bin-mongo-port'] = 27017
        self.ServerSettings['bin-mongo-db'] = 'test'

        self.bin_connection = pymongo.Connection(self.ServerSettings['bin-mongo-hostname'], self.ServerSettings['bin-mongo-port'])
        self.bin_mongo = self.connection[self.ServerSettings['bin-mongo-db']]
        self.bin_GridFS = GridFS(self.bin_mongo)
        
        filehandle.close()
        self.saveconfig()

        
    def saveconfig(self,filename=None):
        if filename == None:
            filename = self.ServerSettings['hostname'] + ".PluricServerSettings"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.ServerSettings,ensure_ascii=False,separators=(u',',u':'))) 
        filehandle.close()

    def prettytext(self):
        newstr = json.dumps(self.ServerSettings,ensure_ascii=False,indent=2,separators=(u', ',u': '))
        return newstr
    

    def receiveEnvelope(self,envelope):
        c = Envelope(importstring=envelope)
        
        if c.dict.has_key('servers'):
            serverlist = c.dict['servers']
        else:
            serverlist = []
            
        
        #Search the server list to look for ourselves. Don't double-receive.
        for server in serverlist:            
            if server['pubkey'] == self.ServerKeys.pubkey:
                logging.debug("Found potential us. Let's verify.")
                Envelopekey = Keys(pub=self.ServerKeys.pubkey)
                if Envelopekey.verifystring(stringtoverify=c.message.text(),signature=server['signature']) == True:
                    #If we've gotten here, we've received the same message twice
                    logging.debug("It's a Me!")
                    #return
                else:
                    #Someone is imitating us. Bastards.
                    logging.error("It's a FAAAAAAKE!")
        
        
                    
        utctime = time.time()

        #Store a message hash in the message itself.
        c.dict['envelope']['message_sha512'] = c.message.hash()

        #Sign the message to saw we saw it.
        signedmessage = self.ServerKeys.signstring(c.message.text())
        myserverinfo = {u'hostname':self.ServerSettings['hostname'],u'time_seen':utctime,u'signature':signedmessage,u'pubkey': self.ServerKeys.pubkey}
    
        serverlist.append(myserverinfo)
        c.dict['envelope']['servers'] = serverlist
        #print c.prettytext()
        #logging.debug(c.prettytext())
        c.saveMongo(self.mongo)
        
server = Server()
from User import User
