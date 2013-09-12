import key
import scrypt
import base64
import time
import TavernUtils
import functools

class LockedKey(key.Key):

    """
    A securely locked away key, which uses a secret only stored in the client to unlock.
    If our DB is ever compromised, this will prevent bad guys from easily impersonating users.
    This also prevents us from evesdropping on private messages.

    Class is basically a wrapper around Keys.py

    We aren't just using gpg passphrases because there is no easy way to progratically change them.
    """

    # access_privatekey is an empty function that is called before every function that requires privatekey access.
    # We're adding it here so that objects that extend Key can overwrite it, and unlock the privatekey in some way.

    def __init__(self, pub=None, priv=None, password=None, encryptedprivkey=None):
        self.maxtime_verify = 5
        self.maxtime_create = 1
        self.encryptedprivkey = encryptedprivkey
        self.passkey = None

        super().__init__(pub=pub,priv=priv)

    def lock(self,passkey=None):
        """
        Remove the private key from Python obj
        """
        if self.privkey is None and self.encryptedprivkey is not None:
            # Already locked!
            print("Already locked.")
            return True

        if passkey is not None:
            self.passkey = passkey

        if self.privkey is None and self.encryptedprivkey is None:
            raise Exception('KeyError',"Asked to lock an empty key")

        if self.privkey is not None and self.passkey is not None:
            self._encryptprivkey(privkey=self.privkey,passkey=self.passkey)   
            self.privkey = None
            return True

        raise Exception('KeyError',"Asked to lock a key, but unable to do so.")

    def unlock(self,passkey=None):
        """
        Sets self.privkey to be the public key, if possible
        """
        if passkey is not None:
            self.passkey = passkey

        if self.privkey is not None:
            # Already unlocked.
            return True

        # If we have everything necessary, become a priv/pub keypair.
        if self.privkey is None and self.passkey is not None and self.encryptedprivkey is not None:
            self.privkey = self._decryptprivkey(self.passkey)
            super().__init__(pub=self.pubkey,priv=self.privkey)
            return True

        if self.privkey is None:
            raise Exception('KeyError', 'Could not unlock key')

    def _encryptprivkey(self, privkey=None, password=None,passkey=None):
        """
        Internal-only method to encrypt the private key.
        This is using the scrypt KDF to encrypt the privatekey.
        """

        if privkey is None and self.privkey is None:
            raise Exception('KeyError', 'Invalid call to encryptedprivkey - No privkey found.')

        if password is None and passkey is None:
            raise Exception('KeyError', 'Invalid call to encryptedprivkey - No key or password')

        if passkey is None and password is not None:
            passkey = self.get_passkey(password)

        key = scrypt.encrypt(input=privkey, password=passkey, maxtime=self.maxtime_create)

        self.encryptedprivkey = base64.b64encode(key).decode('utf-8')
        return self.encryptedprivkey

    def _decryptprivkey(self, passkey):
        """
        Decode and return the private key.
        """
        if isinstance(passkey,str):
            passkey = passkey.encode('utf-8')

        byteprivatekey = base64.b64decode(
            self.encryptedprivkey.encode('utf-8'))

        result =  scrypt.decrypt(input=byteprivatekey, password=passkey, maxtime=self.maxtime_verify)
        return result


    def get_passkey(self, password):
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
        # Defaults to N=16384, r=8, p=1, buflen=64

        # Per http://www.tarsnap.com/scrypt/scrypt-slides.pdf
        # (N = 2^14, r = 8, p = 1) for < 100ms (interactive use), and
        # (N = 2^20, r = 8, p = 1) for < 5s (sensitive storage).

        if self.passkey is not None:
            return self.passkey

        print("Calling scrypt hash...")
        pkey = base64.b64encode(scrypt.hash(
            password=password, salt=self.pubkey, N=16384,r=8,p=1)).decode('utf-8')
        return pkey


    def changepass(self, oldpasskey, newpassword):
        privkey = self._decryptprivkey(oldpasskey)
        self.encryptedprivkey = None
        self.encryptedprivkey = self._encryptprivkey(privkey=privkey,
            password=newpassword)
        self.passkey = None
        self.passkey = self.get_passkey(newpassword)
        return self.encryptedprivkey

    def generate(self, password=None,passkey=None,random=False,autoexpire=False):
        """
        Generate a new set of keys.
        Store only the encrypted version
        """

        if password is None and passkey is None and random is False:
            raise Exception('KeyError', 'Invalid call to generate() - Must include a password, passkey, or Random')

        if random is True:
            password = TavernUtils.randstr(100)
            print("Generating a lockedkey with a random password")
            ret = password
        else:
            ret = None

        super().generate(autoexpire=autoexpire)
        if self.passkey is None and passkey is not None:
            self.passkey = passkey

        if self.passkey is None and password is not None:
            self.passkey = self.get_passkey(password=password)
        
        self.lock(passkey = self.passkey)
        return ret
