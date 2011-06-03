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
import pprint
class Server(object):

    def __init__(self,settingsfile=None):            
        self.ServerSettings = OrderedDict()
        self.mongocons = OrderedDict()
        self.mongos = OrderedDict()
        
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
                self.mongocons['default'] = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'])
                self.mongos['default'] =  self.mongocons['default'][self.ServerSettings['mongo-db']]             
                self.mongocons['binaries'] = pymongo.Connection(self.ServerSettings['bin-mongo-hostname'], self.ServerSettings['bin-mongo-port'])
                self.mongos['binaries'] = self.mongocons['binaries'][self.ServerSettings['bin-mongo-db']]
                self.bin_GridFS = GridFS(self.mongos['binaries'])
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
        self.ServerSettings['upload-dir'] = '/opt/uploads'
        self.ServerSettings['bin-mongo-hostname'] = 'localhost'
        self.ServerSettings['bin-mongo-port'] = 27017
        self.ServerSettings['bin-mongo-db'] = 'test'

        self.mongocons['default'] = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'])
        self.mongos['default'] =  self.mongocons['default'][self.ServerSettings['mongo-db']]             
        self.mongocons['binaries'] = pymongo.Connection(self.ServerSettings['bin-mongo-hostname'], self.ServerSettings['bin-mongo-port'])
        self.mongos['binaries'] = self.mongocons['binaries'][self.ServerSettings['bin-mongo-db']]
        self.bin_GridFS = GridFS(self.mongos['binaries'])
        
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
        c = Envelope()
        c.loadstring(importstring=envelope)
        if c.dict.has_key('servers'):
            serverlist = c.dict['servers']
        else:
            serverlist = []
        if not c.validate():
            print "Validation Error"
            return False
                
        #Search the server list to look for ourselves. Don't double-receive.
        for server in serverlist:            
            if server['pubkey'] == self.ServerKeys.pubkey:
                logging.debug("Found potential us. Let's verify.")
                Envelopekey = Keys(pub=self.ServerKeys.pubkey)
                if Envelopekey.verifystring(stringtoverify=c.payload.text(),signature=server['signature']) == True:
                    logging.debug("It's a Me!")
                    #return
                else:
                    #Someone is imitating us. Bastards.
                    logging.error("It's a FAAAAAAKE!")
                    return False
        
        utctime = time.time()
        #Sign the message to saw we saw it.
        signedpayload = self.ServerKeys.signstring(c.payload.text())
        myserverinfo = {u'hostname':self.ServerSettings['hostname'],u'time_seen':utctime,u'signature':signedpayload,u'pubkey': self.ServerKeys.pubkey}

        serverlist.append(myserverinfo)
        c.dict['envelope']['servers'] = serverlist
        #Determine Message type, by which primary key it has. 
        #While there is no *technical* reason you couldn't have more than one message per envelope, or a message and a vote, it is invalid.
        #The reason for this is that envelopes are low-overhead, and make splitting it up by other servers later, easier.
        #So, we only allow one, to ensure cleanness of the echosystem.
        
        if c.dict['envelope']['payload']['payload_type'] == "message":       
            #If the message referenes anyone, mark the original, for ease of finding it later.
            #Do this in the [local] block, so we don't waste bits passing this on.
            #If the message doesn't exist, don't mark it ;)
            if c.dict['envelope']['payload'].has_key('regarding'):
                repliedTo = Envelope()
                if repliedTo.loadmongo(mongo_id=c.dict['envelope']['payload']['regarding']):
                
                    repliedTo.dict['envelope']['local']['citedby'].append(c.message.hash())
                    print "Adding messagehash " + c.payload.hash() + " to " + c.dict['envelope']['payload']['regarding']
                    print "NewHash: " + repliedTo.payload.hash()   
                    repliedTo.saveMongo()
                    
        if c.dict['envelope']['payload']['payload_type'] == "messagerating":   
            print "This is a rating"    
        #Store our file
        c.saveMongo()
        
server = Server()
from User import User
