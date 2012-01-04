import os
import re
import string
import hashlib
import base64
from tomcrypt import cipher,rsa

 
class Keys(object):
    
    def __init__(self,pub=None,priv=None):  
        """
        Create a Key object.
        Pass in either pub=foo, or priv=foo, to use pre-existing keys.
        """
        
        self.pubkey = pub
        self.privkey = priv
        
        if priv == None and pub != None:
            self.key = rsa.Key(pub,hash='sha512',padding="pss")
            self.pubkey = self.key.public.as_string()
            print("Going with Pubkey Only")
        if priv != None:
            self.key = rsa.Key(priv,hash='sha512',padding="pss")
            self.pubkey = self.key.public.as_string()
            self.privkey = self.key.as_string()
            print("Full Key")
            
            
             
    def format_keys(self):
        """ 
        Ensure the keys are in the proper format, with linebreaks. 
        linebreaks are every 64 characters, and we have a header/footer.
        """   
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
        """
        Replaces whatever keys currently might exist with new ones.
        """
        self.key = rsa.Key(2048,hash='sha512',padding="pss")
        self.pubkey = self.key.public.as_string()
        self.privkey = self.key.as_string()
        self.format_keys()

    def signstring(self,signstring):
        """
        Sign a string, and return back the Base64 Signature.
        """
        # It seems with PyTomCrypt, you need to manually hash things before signing.
        # The Salt Length == 64 == the length of SHA512. If you use sha1, change this to 20, etc.
    
        digest = hashlib.sha512(signstring.encode('utf-8')).digest()
        bsigned = self.key.sign(digest,hash='sha512',padding="pss",saltlen=64)
        return base64.b64encode(bsigned).decode('utf-8')

    def verify_string(self,stringtoverify,signature):  
        """
        Verify the passed in string matches the passed signature
        """
        
        # It's pretty stupid we need to manually digest, but.. Cest la vie.
        # Maybe a new version of pyTomCrypto will do this for us.
                   
        digested = hashlib.sha512(stringtoverify.encode('utf-8')).digest()
        binarysig = base64.b64decode(signature.encode('utf-8'))
        return self.key.verify(digested,binarysig,padding="pss",hash="sha512",saltlen=64)
        
    def encrypt(self,encryptstring):
        return base64.b64encode(self.key.encrypt(encryptstring.encode('utf-8'),hash='sha512',padding="pss")).decode('utf-8')
        
    def decrypt(self,decryptstring):
        return self.key.decrypt(base64.b64decode(decryptstring.encode('utf-8')),hash='sha512',padding="pss").decode('utf-8')

    def test_signing(self):
        """
        Verify the signing/verification engine works as expected
        """
        self.format_keys()
        return self.verify_string(stringtoverify="ABCD1234",signature=self.signstring("ABCD1234"))
