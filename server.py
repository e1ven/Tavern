import os,json
import M2Crypto
import platform

def empty_callback ():
 return

M2Crypto.Rand.rand_seed (os.urandom (1024))

class Keys(object):
    def __init__(self,pub=None,priv=None):
        if priv == None:
            self.privkey_bio = M2Crypto.BIO.MemoryBuffer()
        else:
            self.privkey_bio = M2Crypto.BIO.MemoryBuffer(priv)
            self.privkey = priv
        if pub == None:
            self.pubkey_bio = M2Crypto.BIO.MemoryBuffer()
        else:
            self.pubkey_bio = M2Crypto.BIO.MemoryBuffer(pub)
            self.pubkey = pub
        
    def generate(self):
        Keys = M2Crypto.RSA.gen_key (4096, 65537,empty_callback)
        Keys.save_key_bio(self.privkey_bio,None)
        Keys.save_pub_key_bio(self.pubkey_bio)
        
        #TODO- use __get_addr__ to calc these OnDemand
        self.privkey = self.privkey_bio.read()        
        self.pubkey = self.pubkey_bio.read()
        

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
        else:
            self.loadconfig(settingsfile)

    def loadconfig(self,filename=None):
        if filename == None:
            filename = platform.node() + ".PluricServerSettings"
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.ServerSettings = json.loads(filecontents)
        self.ServerKeys = Keys(self.ServerSettings['pubkey'],self.ServerSettings['privkey'])
        filehandle.close()
            
    def saveconfig(self,filename=None):
        if filename == None:
            filename = self.ServerSettings['hostname'] + ".PluricServerSettings"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.ServerSettings,ensure_ascii=False,separators=(',',':'))) 
        filehandle.close()
         
#Seed the random number generator with 1024 random bytes (8192 bits)
M2Crypto.Rand.rand_seed (os.urandom (1024))

s = Server("Threepwood.savewave.com.PluricServerSettings")
print s.ServerKeys.pubkey
s.saveconfig()
