import os,re
import string,hashlib,base64
import Crypto.PublicKey.RSA as RSA
import Crypto.Hash.MD5 as MD5
 
class Keys(object):

    def __init__(self,pub=None,priv=None):    
        self.pubkey = pub
        self.privkey = priv
        
        if priv == None and pub != None:
            self.key = RSA.importKey(pub)
            
        if priv != None and pub != None:
            combinedkey = pub + priv
            self.key = RSA.importKey(combinedkey)
        
        if priv != None and pub == None:
            print("Weirdness. Don't do that.")
            return False   
            
            
             
    def formatkeys(self):
        #Format the priv and pub keys
        #Make sure we have proper linebreaks every 64 characters, and a header/footer
        
        #Strip out the headers
        #Strip out the linebreaks
        #Re-Add the Linebreaks
        #Re-add the headers
        
        #Check for compressed versions-
        if self.privkey is not None:
            self.privkey = self.privkey.replace("-----BEGINRSAPRIVATEKEY-----","-----BEGIN RSA PRIVATE KEY-----")
            self.privkey = self.privkey.replace("-----ENDRSAPRIVATE KEY-----","-----END RSA PRIVATE KEY-----")

        if self.pubkey is not None:
            self.pubkey = self.pubkey.replace("-----BEGINPUBLICKEY-----","-----BEGIN PUBLIC KEY-----")
            self.pubkey = self.pubkey.replace("-----ENDPUBLICKEY-----","-----END PUBLIC KEY-----")
            
        if self.privkey is not None:
            if "-----BEGIN RSA PRIVATE KEY-----" in self.privkey:
                noHeaders=self.privkey[self.privkey.find("-----BEGIN RSA PRIVATE KEY-----")+31:self.privkey.find("-----END RSA PRIVATE KEY-----")]
            else:
                print("USING NO HEADER VERSION OF PRIVKEY")
                noHeaders = self.privkey
            noBreaks = "".join(noHeaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]            
            self.privkey = "-----BEGIN RSA PRIVATE KEY-----\n" + withLinebreaks + "\n-----END RSA PRIVATE KEY-----"        
        else:
            print("No PRIVKEY")
            
        if self.pubkey is not None:
            if "-----BEGIN PUBLIC KEY-----" in self.pubkey:
                noHeaders=self.pubkey[self.pubkey.find("-----BEGIN PUBLIC KEY-----")+26:self.pubkey.find("-----END PUBLIC KEY-----")]
            else:
                print("USING NO HEADER VERSION OF PUBKEY")
                noHeaders=self.pubkey
            noBreaks = "".join(noHeaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]
            self.pubkey = "-----BEGIN PUBLIC KEY-----\n" + withLinebreaks + "\n-----END PUBLIC KEY-----" 


    def generate(self):
        self.key = RSA.generate(4096)
        self.pubkey = str(self.key.publickey().exportKey(),encoding='latin1')
        self.privkey  = str(self.key.exportKey(),encoding='latin1')

    def signstring(self,signstring):
        
        # Second Parameter is not needed for RSA.        
        return self.key.sign(signstring.encode('utf-8'),'')

    def verifystring(self,stringtoverify,signature):
        return self.key.verify(stringtoverify.encode('utf-8'),signature)

    def encryptToSelf(self,encryptstring):
        return base64.b64encode(self.key.encrypt(encryptstring.encode('utf-8'),'')[0]).decode('utf-8')

    def decryptToSelf(self,decryptstring):
        return self.key.decrypt(base64.b64decode(decryptstring.encode('utf-8'))).decode('utf-8')

    def dokeysmatch(self):
        self.formatkeys()
        return self.verifystring(stringtoverify="ABCD1234",signature=self.signstring("ABCD1234"))