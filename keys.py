import os,re
import string

 #Stub this out for now.
 
class Keys(object):
    def empty_callback ():
        return

    def __init__(self,pub=None,priv=None):
        #The point of doing the split, and the replaces, below, is to ensure we have no whitespace in the public keys.
        #Just the straight key, as a long string. No \r or \n
        self.Keys = "ff"
        self.pubkey = "Pub"
        self.privkey = "priv"
        
    def formatkeys(self):
     #Format the priv and pub keys
     #Make sure we have proper linebreaks every 64 characters, and a header/footer

     #Strip out the headers
     #Strip out the linebreaks
     #Re-Add the Linebreaks
     #Re-add the headers
     print("foo")



    def generate(self):

        #TODO- use __get_addr__ to calc these OnDemand
        self.privkey = "Pub"      
        self.pubkey = "priv" 

        self.combinedkey = self.privkey + '\n' + self.pubkey
        self.combinedkey = self.combinedkey.encode('utf8')    
        self.formatkeys()

    def signstring(self,signstring):
        return "StringSignature"

    def verifystring(self,stringtoverify,signature):
        return True

    def encryptToSelf(self,encryptstring):
        return "true"

    def decryptToSelf(self,decryptstring):
        return "true"

    def dokeysmatch(self):
        self.formatkeys()
        return self.verifystring(stringtoverify="ABCD1234",signature=self.signstring("ABCD1234"))