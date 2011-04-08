import M2Crypto

class Keys(object):
    def __init__(self,pub=None,priv=None):
        self.Keys = M2Crypto.RSA
        if priv == None:
            self.privkey_bio = M2Crypto.BIO.MemoryBuffer()
        else:
            self.privkey_bio = M2Crypto.BIO.MemoryBuffer(priv.encode('utf8'))
            self.privkey = priv.encode('utf8')
        if pub == None:
            self.pubkey_bio = M2Crypto.BIO.MemoryBuffer()
        else:
            self.pubkey_bio = M2Crypto.BIO.MemoryBuffer(pub.encode('utf8'))
            self.pubkey = pub.encode('utf8')
      
      
        # Define the combined key if we have both variables.
        # Otherwise... Don't.
        if hasattr(self, 'privkey') and hasattr(self, 'pubkey'):
            self.combinedkey = self.privkey + '\n' + self.pubkey
            self.combinedkey = self.combinedkey.encode('utf8')    
            self.combinedkey_bio = M2Crypto.BIO.MemoryBuffer(self.combinedkey)
            self.Keys.load_key_string(self.combinedkey)      
        
    def generate(self):
        self.Keys = M2Crypto.RSA.gen_key (4096, 65537,empty_callback)
        self.Keys.save_key_bio(self.privkey_bio,None)
        self.Keys.save_pub_key_bio(self.pubkey_bio)
        
        #TODO- use __get_addr__ to calc these OnDemand
        self.privkey = self.privkey_bio.read()        
        self.pubkey = self.pubkey_bio.read()

    def signstring(self,signstring):
        SignEVP = M2Crypto.EVP.load_key_string(self.combinedkey)
        SignEVP.sign_init()
        SignEVP.sign_update(signstring)
        StringSignature = SignEVP.sign_final().encode('base64')
        return StringSignature
        
    def verifystring(self,stringtoverify,signature):
        decodedSignature = signature.decode('base64')
        PubKey = M2Crypto.RSA.load_pub_key_bio(self.pubkey_bio)
        VerifyEVP = M2Crypto.EVP.PKey()
        VerifyEVP.assign_rsa(PubKey)
        VerifyEVP.verify_init()
        VerifyEVP.verify_update(stringtoverify)
        if VerifyEVP.verify_final(decodedSignature) == 1:
            return True
        else:
            return False
        