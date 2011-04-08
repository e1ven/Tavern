import os,json
import M2Crypto
import platform
from container import *
import time
from keys import *
import logging
import bcrypt

class User(object):
    def __init__(self,username=None,password=None,filename=None):
        
        if filename == None:
            self.UserSettings = {}
            self.UserSettings['username'] = username
            self.UserSettings['hashedPassword'] = bcrypt.hashpw(password, bcrypt.gensalt(12))
            self.Keys = Keys()
            self.Keys.generate()
            self.UserSettings['privkey'] = self.Keys.privkey
            self.UserSettings['pubkey'] = self.Keys.pubkey
            
            gmttime = time.gmtime()
            gmtstring = time.strftime("%Y-%m-%dT%H:%M:%SZ",gmttime)
            
            self.UserSettings['time_created'] = gmtstring
            
            
        else:
            self.loaduser(filename)
            
    def loaduser(self,filename):
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.UserSettings = json.loads(filecontents)
        filehandle.close()    
        self.UserSettings = Keys(pub=self.UserSettings['pubkey'],priv=self.UserSettings['privkey'])
        
    def saveuser(self,filename=None):
        if filename == None:
            filename = self.UserSettings['username'] + ".PluricUser"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.UserSettings,ensure_ascii=False,separators=(u',',u':'))) 
        filehandle.close()
        
class Server(object):

    def __init__(self,settingsfile=None):            
        self.ServerSettings = {}

        if settingsfile == None:
            if os.path.isfile(platform.node() + ".PluricServerSettings"):
                #Load Default file(hostname)
                self.loadconfig()
            else:
                #Generate New config    
                self.ServerKeys = Keys()
                self.ServerKeys.generate()
                self.ServerSettings['pubkey'] = self.ServerKeys.pubkey
                self.ServerSettings['privkey'] = self.ServerKeys.privkey
                self.ServerSettings['hostname'] = platform.node()
                self.ServerSettings['logfile'] = self.ServerSettings['hostname'] + '.log'
        else:
            self.loadconfig(settingsfile)
        logging.basicConfig(filename=self.ServerSettings['logfile'],level=logging.DEBUG)
        #logging.basicConfig(stream=sys.stdout,level=logging.DEBUG)
 
    def loadconfig(self,filename=None):
        if filename == None:
            filename = platform.node() + ".PluricServerSettings"
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.ServerSettings = json.loads(filecontents)
        self.ServerKeys = Keys(pub=self.ServerSettings['pubkey'],priv=self.ServerSettings['privkey'])
        filehandle.close()
            
    def saveconfig(self,filename=None):
        if filename == None:
            filename = self.ServerSettings['hostname'] + ".PluricServerSettings"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.ServerSettings,ensure_ascii=False,separators=(u',',u':'))) 
        filehandle.close()

    def prettytext(self):
        newstr = json.dumps(self.ServerSettings,ensure_ascii=False,indent=2,separators=(u', ',u': '))
        return newstr
    

    def receivecontainer(self,container):
        c = Container(importstring=container)
        
        if c.dict.has_key('servers'):
            serverlist = c.dict['servers']
        else:
            serverlist = []
            
        
        #Search the server list to look for ourselves. Don't double-receive.
        for server in serverlist:            
            if server['pubkey'] == self.ServerKeys.pubkey:
                logging.debug("Found potential us. Let's verify.")
                containerkey = Keys(pub=self.ServerKeys.pubkey)
                if containerkey.verifystring(stringtoverify=c.message.text(),signature=server['signature']) == True:
                    #If we've gotten here, we've received the same message twice
                    logging.debug("It's a Me!")
                    #return
                else:
                    #Someone is imitating us. Bastards.
                    logging.error("It's a FAAAAAAKE!")
        
        
                    
        gmttime = time.gmtime()
        gmtstring = time.strftime("%Y-%m-%dT%H:%M:%SZ",gmttime) 
        #Pluric has an exact time string per ISO Spec.

        #Store a message hash in the message itself.
        c.dict['pluric_container']['message_sha512'] = c.message.hash()

        #Sign the message to saw we saw it.
        signedmessage = self.ServerKeys.signstring(c.message.text())
        myserverinfo = {u'hostname':self.ServerSettings['hostname'],u'time_seen':gmtstring,u'signature':signedmessage,u'pubkey': self.ServerKeys.pubkey}
    
        serverlist.append(myserverinfo)
        c.dict[u'servers'] = serverlist
        #print c.prettytext()
        #logging.debug(c.prettytext())
        c.tofile()
