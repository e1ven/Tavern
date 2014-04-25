import scrypt
import base64
import libtavern.key

class LockedKey(libtavern.key.Key):

    """
    LockedKey extends Key to provide a version where the private key is encrypted.

    When you first create a lockedkey, you provide a password.
    This password is hashed using scrypt, and a 'passkey' (the hash) is generated.
    The private key is then encrypted using this passkey, by way of scrypt enc.

    This passkey is then given to the user as a cookie. It is not stored on the server.

    If this is stolen from the user, it will not let them log in, since it is not the original.
    If our DB is leaked, the keys will be unreadable without these passkeys.

    Implementation Note - We aren't using GPG passphrases for two reasons-
        1) We want to be able to support non GPG keys
        2) There is no crossplatform way of changing GPG keys via library ;(
    """

    def __init2__(self, pub=None, priv=None,password=None, encryptedprivkey=None, passkey=None):

        self.maxtime_verify = 5
        self.maxtime_create = 1
        self.encryptedprivkey = encryptedprivkey
        self.passkey = passkey
        self.privkey = priv
        self.pubkey = pub

        if self.passkey is None and password is not None:
            self.passkey = self.get_passkey(password)

        if self.passkey is not None and self.encryptedprivkey is not None:
            self.privkey = self._decryptprivkey(passkey=self.passkey)

        super().__init2__(pub=self.pubkey, priv=self.privkey)

    def lock(self, passkey=None):
        """
        Removes the Private Key from memory on a given object.
        :param passkey: The Passkey for this object
        :return True: Returns True on success, raises Exception on failure (should never fail)
        """
        if self.privkey is None and self.encryptedprivkey is not None:
            # Already locked!
            print("Already locked.")
            return True

        if passkey is not None:
            self.passkey = passkey

        if self.privkey is None and self.encryptedprivkey is None:
            raise Exception('KeyError', "Asked to lock an empty key")

        if self.privkey is not None and self.passkey is not None:
            self._encryptprivkey(privkey=self.privkey, passkey=self.passkey)
            self.privkey = None
            return True

        raise Exception('KeyError',"Asked to lock a key, but unable to do so.")

    def unlock(self, passkey=None):
        """
        Restores the Private Key (.privkey) attribute in the object
        :param passkey: The Passkey to unlock this private key.
        :return True: Returns True on success, raises Exception on failure
        """

        if passkey is not None:
            self.passkey = passkey
        if self.privkey is not None:
            # Already unlocked.
            return True

        # If we have everything necessary, become a priv/pub keypair.
        if self.privkey is None and self.passkey is not None and self.encryptedprivkey is not None:
            self.privkey = self._decryptprivkey(self.passkey)
            super().__init__(pub=self.pubkey, priv=self.privkey)
            return True

        if self.privkey is None:
            raise Exception('KeyError', 'Could not unlock key')


    def _encryptprivkey(self, privkey=None, password=None, passkey=None):
        """
        Internal-Only method to encrypt the private key.
        Uses the scrypt KDF to stretch the passkey, and then scrypt enc to encrypt/protect the key.
        Note - This does not remove the private key - Use .lock() for that.

        :param privkey: The Private Key to save and Protect
        :param password: The Password to encrypt the Private Key with
        :param passkey: The Passkey to encrypt the Private Key with
        :return: base64 encoded version of the encrypted private key
        """


        if privkey is None and self.privkey is None:
            raise Exception('KeyError','Invalid call to encryptedprivkey - No privkey found.')

        if password is None and passkey is None:
            raise Exception('KeyError','Invalid call to encryptedprivkey - No key or password')

        if passkey is None and password is not None:
            passkey = self.get_passkey(password)

        key = scrypt.encrypt(input=privkey,password=passkey,maxtime=self.maxtime_create)

        self.encryptedprivkey = base64.b64encode(key).decode('utf-8')
        return self.encryptedprivkey

    def _decryptprivkey(self, passkey):
        """
        Internal-Only method to decrypt the private key from the
        :param passkey: The passkey to use to decrypt self.encryptedprivkey
        :return string: The private key
        """
        if isinstance(passkey, str):
            passkey = passkey.encode('utf-8')

        byteprivatekey = base64.b64decode(self.encryptedprivkey.encode('utf-8'))

        result = scrypt.decrypt(input=byteprivatekey,password=passkey,maxtime=self.maxtime_verify)
        return result

    def get_passkey(self, password):
        """
        Use scrypt to hash the password according to a work factor defined in settings.
        :param password: The password to hash
        :return: base64 encoded version of the private key
        """

        if password is None:
            raise Exception("Password cannot be null.")

        # N - Overall CPU/Memory cost. Should be a power of two.
        # r - Memory cost - Adjusts blocksize
        # p - Number of parallel loops
        # Per http://www.tarsnap.com/scrypt/scrypt-slides.pdf
        # (N = 2^14, r = 8, p = 1) for < 100ms (interactive use), and
        # (N = 2^20, r = 8, p = 1) for < 5s (sensitive storage).

        N = self.server.serversettings.settings['auth']['scrypt']['N']
        r = self.server.serversettings.settings['auth']['scrypt']['r']
        p = self.server.serversettings.settings['auth']['scrypt']['p']

        if self.passkey is not None:
            return self.passkey

        pkey = base64.b64encode(scrypt.hash(password=password, salt=self.pubkey, N=N, r=r, p=p)).decode('utf-8')
        return pkey

    def changepass(self, oldpasskey, newpassword):
        """
        Changes the stored password.
        :param oldpasskey: The Old password
        :param newpassword: The New password
        :return: True, or Exception.
        """
        try:
            privkey = self._decryptprivkey(oldpasskey)
        except:
            raise Exception('KeyPassError',"Attempted to change password with incorrect password")

        self.encryptedprivkey = None
        self.encryptedprivkey = self._encryptprivkey(privkey=privkey, password=newpassword)
        self.passkey = None
        self.passkey = self.get_passkey(newpassword)
        return True

    def generate(self, password=None, passkey=None, random=False, autoexpire=False):
        """
        Generates a new set of public and private keys.
        Stores only the encrypted version of the key in the object.
        Must receive either a password, passkey, or random flag.

        :param string password: The password to encrypt the new privkey with
        :param string passkey: The passkey to encrypt the new privkey with
        :param True/False random: If True, generates a random password to encrypt with.
        :param autoexpire: Sets the expiration date for the key to next month.
        :return: Returns the new password if random == True, else returns None
        """

        if password is None and passkey is None and random is False:
            raise Exception(
                'KeyError',
                'Invalid call to generate() - Must include a password, passkey, or Random')

        if random is True:
            password = libtavern.utils.randstr(100)
            ret = password
        else:
            ret = None

        super().generate(autoexpire=autoexpire)
        if self.passkey is None and passkey is not None:
            self.passkey = passkey

        if self.passkey is None and password is not None:
            self.passkey = self.get_passkey(password=password)

        self.lock(passkey=self.passkey)
        return ret

    def to_dict(self):
        """
        Writes the key to a dictionary object. Does -not- save the privkey or passkey.
        :return: A dictionary version of the key
        """
        keydict = {}

        keydict['pubkey'] = self.pubkey
        keydict['generated'] = self.generated
        keydict['expires'] = self.expires
        keydict['encryptedprivkey'] = self.encryptedprivkey
        return keydict

    def from_dict(self,keydict,passkey=None):
        """
        Restores a key from a dictionary.
        """
        if passkey is None:
            self.__init2__(pub=keydict['pubkey'],encryptedprivkey=keydict['encryptedprivkey'])
        else:
            self.__init2__(pub=keydict['pubkey'],encryptedprivkey=keydict['encryptedprivkey'],passkey=passkey)

        self.expires = keydict['expires']
        self.generated = keydict['generated']
