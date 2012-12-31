from keys import Keys
import scrypt
import base64


class lockedKey(object):
    """
    A securely locked away key, which uses a secret only stored in the client to unlock.
    If our DB is ever compromised, this will prevent bad guys from easily impersonating users.
    This also prevents us from evesdropping on private messages.

    Class is basically a wrapper around Keys.py

    We aren't just using gpg passphrases because there is no easy way to progratically change them.
    """

    def __init__(self, pub=None, priv=None, password=None, encryptedprivkey=None):
        self.maxtime_verify = 5
        self.maxtime_create = 1
        tempkey = Keys(pub=pub, priv=priv)
        self.pubkey = tempkey.pubkey
        tempkey.format_keys()
        self.pubkey = tempkey.pubkey

        if encryptedprivkey is not None:
            self.encryptedprivkey = encryptedprivkey

        if encryptedprivkey is None and password is not None and priv is not None:
            self.encryptedprivkey = self.__encryptprivkey(
                password=password, privkey=tempkey.privkey)

    def __encryptprivkey(self, password, privkey):
        """
        Internal-only method to encrypt the private key.
        """
        key = scrypt.encrypt(input=privkey, password=self.passkey(
            password), maxtime=self.maxtime_create)
        return base64.b64encode(key).decode('utf-8')

    def passkey(self, password):
        """
        Returns the hashed version of the password.
        Broken out into a method, so we can swap it if nec.
        """
        if password is None:
            raise Exception("Password cannot be null.")

        # N CPU cost parameter.  ( N should be a power of two > 1)
        # r Memory cost parameter.
        # p Parallelization parameter.
        # r*p should be < 2**30

        pkey = base64.b64encode(scrypt.hash(
            password=password, salt=self.pubkey, N=16384)).decode('utf-8')
        return pkey

    def privkey(self, passkey):
        """
        Decode and return the private key.
        """
        byteprivatekey = base64.b64decode(
            self.encryptedprivkey.encode('utf-8'))
        return scrypt.decrypt(input=byteprivatekey, password=passkey, maxtime=self.maxtime_verify)

    def changepass(self, oldpasskey, newpass):
        privkey = self.privkey(oldpasskey)
        self.encryptedprivkey = self.__encryptprivkey(
            password=newpass, privkey=privkey)

    def generate(self, password):
        """
        Generate a new set of keys.
        Store only the encrypted version
        """
        tempkey = Keys()
        tempkey.generate()
        tempkey.format_keys()
        self.pubkey = tempkey.pubkey
        self.encryptedprivkey = self.__encryptprivkey(
            password=password, privkey=tempkey.privkey)

    def format_keys(self):
        tempkey = Keys(pub=self.pubkey)
        tempkey.format_keys()
        self.pubkey = tempkey.pubkey

    def signstring(self, signstring, passkey):
        """
        Sign a given string, unlocking and then using the local private key file.
        """

        tempkey = Keys(pub=self.pubkey, priv=self.privkey(passkey))
        return tempkey.signstring(signstring=signstring)

    def verify_string(self, stringtoverify, signature, passkey):
        """
        Verify a given string, unlocking and then using the local private key file.
        """
        tempkey = Keys(pub=self.pubkey, priv=self.privkey(passkey))
        return  tempkey.verify_string(stringtoverify=stringtoverify, signature=signature)

    def encrypt(self, encryptstring, encrypt_to, passkey):
        """
        Encrypt a given string, after unlocking the local privkey to do so.
        """
        tempkey = Keys(pub=self.pubkey, priv=self.privkey(passkey))
        return tempkey.encrypt(encryptstring=encryptstring,encrypt_to=encrypt_to)

    def decrypt(self, decryptstring, passkey):
        """
        Decrypt a given string, after unlocking the local privkey to do so.
        """
        tempkey = Keys(pub=self.pubkey, priv=self.privkey(passkey))
        return tempkey.decrypt(decryptstring=decryptstring)
