import M2Crypto,os,re,base64

def empty_callback ():
 return
 
 
#Setup Keys
Keys = M2Crypto.RSA.gen_key (4096, 65537,empty_callback)
privkey_bio = M2Crypto.BIO.MemoryBuffer()
pubkey_bio = M2Crypto.BIO.MemoryBuffer()


Keys.save_key_bio(privkey_bio,None)
Keys.save_pub_key_bio(pubkey_bio)

privkey = privkey_bio.read().encode('utf8')         
pubkey = pubkey_bio.read().encode('utf8') 

combinedkey = privkey + '\n' + pubkey
combinedkey = combinedkey.encode('utf8')    

plaintext = "ABCD1234"
SignEVP = M2Crypto.EVP.load_key_string(combinedkey)
SignEVP.sign_init()
SignEVP.sign_update(plaintext)
SignatureBytes = SignEVP.sign_final()
Signature = base64.b64encode(SignatureBytes)
print Signature
print "---"
print SignatureBytes.encode('base64')


pubkey_bio = M2Crypto.BIO.MemoryBuffer(pubkey.encode('utf8'))
PubKey = M2Crypto.RSA.load_pub_key_bio(pubkey_bio)
VerifyEVP = M2Crypto.EVP.PKey()
VerifyEVP.assign_rsa(PubKey)
VerifyEVP.verify_init()
VerifyEVP.verify_update(plaintext)
if VerifyEVP.verify_final(Signature.decode('base64')) == 1:
        print "Verifies"
else:
        print "Fails to Verify"
        
    
print "Pubkey - ###" + pubkey + "###"
print "B64Sig - ###" + Signature + "###"
print "Plaintext - ###" + plaintext + "###"

