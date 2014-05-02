import base64
import scrypt
import logging
import libtavern.utils
import libtavern.baseobj
import enum
import datetime
import nacl.public
import nacl.signing
import nacl.utils
import copy

class Text64(object):
    """
    Converts a binary string to/from a base64url UTF-8 string.
    The resulting string will not have == padding, so it is safe to use in URL query params
    """
    @staticmethod
    def encode(data):
        """
        Encodes to base64url, and removes padding.
        :param data: The incoming binary string to be encoded
        :return: base64url encoded unicode string
        """
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip("=")

    @staticmethod
    def decode(data):
        """
        Decodes the base64url string to the binary representation.
        Will re-add padding as necessary.
        :param data: The incoming unicode base64url string
        :return: The binary that was encoded in `data`
        """
        # Convert the data to binary representation
        bdata = data.encode('utf-8')
        # Restore missing padding
        missing_padding = 4 - len(bdata) % 4
        if missing_padding:
            bdata += b'='* missing_padding
        return base64.urlsafe_b64decode(bdata)

class Usage(enum.Enum):
    signing = 1
    encryption = 2
    sign_encrypt = 3

class Algorithm(enum.Enum):
    ecdh25519 = 22
    ed25519 = 23

def verify_signature(text,signature,signing_key):
    """
    Verify the a given string was signed by the public key offered.
    :param str text: The original text, which the signature supposedly signed.
    :param str signature: The base64url signature to be verified
    :param str signing_key: The pubkey which supposedly created this signature
    :return: True/False
    """
    # The .verify() function requires that the signature and original message
    # are -both- encoded with the same encoder.
    verify_key = nacl.signing.VerifyKey(key=signing_key, encoder=Text64)

    # Convert everything back to raw binary for verification.
    # The verification will either return the str, or raise BadSignatureError
    try:
        verification = verify_key.verify(smessage=text.encode('utf-8'),signature=Text64.decode(signature),encoder=nacl.encoding.RawEncoder)
    except nacl.exceptions.BadSignatureError:
        raise Exceptions.BadSignature

    return verification.decode('utf-8')

class LockedKey(libtavern.baseobj.Baseobj):
    """
    An owner of a Keypair that you must unlock.
    """
    def __init2__(self,**kwargs):
        """Create a LockedKey, which has a KeyPair inside of it."""
        self.maxtime_verify = 5
        self.maxtime_create = 1
        if kwargs.get()
        self.usage = usage
        # Pull out the encrypted_private_key. We only need that locally.
        if keydict:
            enc_priv_key = keydict.pop('encrypted_private_key')
            self.encrypted_private_key = Text64.decode(enc_priv_key)
        self._keydict = Keypair(usage=self.usage,keydict=keydict).to_dict(include_private=False)


    def unlock(self,passkey):
        """
        Unlock the Keypair so you can access the Private key.
        :param passkey: The passkey for this LockedKey
        :return Keypair: The unlocked keypair
        """
        tmpdict = copy.copy(self._keydict)
        try:
            tmpdict['private'] = scrypt.decrypt(input=self.encrypted_private_key,password=passkey,maxtime=self.maxtime_verify)
        except scrypt.error:
            raise Exceptions.InvalidPasskey

        return Keypair(keydict=tmpdict)


    def get_passkey(self, password):
        """
        Use scrypt to hash the password according to a work factor defined in settings.
        :param password: The password to hash
        :return: base64url encoded version of the private key
        """

        # N - Overall CPU/Memory cost. Should be a power of two.
        # r - Memory cost - Adjusts blocksize
        # p - Number of parallel loops
        # Per http://www.tarsnap.com/scrypt/scrypt-slides.pdf
        # (N = 2^14, r = 8, p = 1) for < 100ms (interactive use), and
        # (N = 2^20, r = 8, p = 1) for < 5s (sensitive storage).

        N = self.server.serversettings.settings['auth']['scrypt']['N']
        r = self.server.serversettings.settings['auth']['scrypt']['r']
        p = self.server.serversettings.settings['auth']['scrypt']['p']

        keypair = Keypair(keydict=self._keydict)
        return Text64.encode(scrypt.hash(password=password, salt=keypair.public, N=N, r=r, p=p))

    def generate(self,passkey=None,autoexpire=False):
        """
        Generates a new random Keypair, and encrypts the privatekey with a random password.
        :return: The random password encrypting the Private Key.
        """

        # Create our password and the passkey if not given
        if not passkey:
            password = libtavern.utils.randstr(100)
            passkey = self.get_passkey(password)
        # Create a newly generated Keypair
        keypair = Keypair(usage=self.usage,autoexpire=autoexpire)
        self.encrypted_private_key = scrypt.encrypt(input=keypair.private,password=passkey,maxtime=self.maxtime_create)
        self._keydict = keypair.to_dict(include_private=False)
        return passkey

    def to_dict(self):
        """
        Retrieve the dictionary storing the Keypair with an encrypted version of the private key.
        :return dict: Dictionary suitable for re-creating a LockedKey.
        """
        mydict = copy.copy(self._keydict)
        mydict['encrypted_private_key'] = Text64.encode(self.encrypted_private_key)
        return mydict

    def change_pass(self, oldpasskey, newpassword):
        """
        Changes the stored password.
        :param oldpasskey: The old passkey (Note! Not the old password!)
        :param newpassword: The New password
        :return: True, or Exception.
        """
        try:
            keypair = self.unlock(passkey=oldpasskey)
        except:
            raise Exceptions.InvalidPasskey
        newpasskey = self.get_passkey(password=newpassword)
        self.encrypted_private_key = scrypt.encrypt(input=keypair.private,password=newpasskey,maxtime=self.maxtime_create)

    @property
    def expired(self):
        """
        Passthrough function to Keypair.
        """
        return Keypair(keydict=self.to_dict()).expired

    @property
    def public(self):
        """
        Passthrough function to Keypair.
        """
        return Keypair(keydict=self.to_dict()).public


class Keypair(object):
    def __init__(self,usage=None,autoexpire=False,public=None,private=None,keydict=None):
        """
        Creates a pair of private and public keys.
        These can be either signing keys, or encryption keys.
        """
        if usage:
            if not isinstance(usage,Usage):
                raise Exception("The Keypair usage must be set to either Usage.signing, Usage.encryption, or Usage.sign_encrypt")
        elif not any([public,private,keydict]):
                raise Exception("This Keypair must contain either a type, or an existing key..")

        self.usage = usage
        self.logger = logging.getLogger('default')
        self.generated = None

        if keydict is not None:
            # If we passed in a dictionary, load that version of the key.
            self.from_dict(keydict)
        else:
            # Load key if possible, generate if necessary.
            if self.usage == Usage.signing:
                self.algorithm = Algorithm.ed25519
                if private:
                    self._private = nacl.signing.SigningKey(seed=private,encoder=Text64)
                    self._public = self._private.verify_key
                elif public:
                    self._public = nacl.signing.VerifyKey(key=public,encoder=Text64)
                    self._private = None
                else:
                    self._private = nacl.signing.SigningKey.generate()
                    self._public = self._private.verify_key
                    self.generated = libtavern.utils.gettime(format='timestamp')

            elif self.usage == Usage.encryption:
                self.algorithm = Algorithm.ecdh25519
                if private:
                    self._private = nacl.public.PrivateKey(private_key=private,encoder=Text64)
                    self._public = self._private.public_key
                elif public:
                    self._public = nacl.public.PublicKey(public_key=public,encoder=Text64)
                    self._private = None
                else:
                    self._private = nacl.public.PrivateKey.generate()
                    self._public = self._private.public_key
                    self.generated = libtavern.utils.gettime(format='timestamp')
            else:
                self.logger.info("Key is not of an recognized usage type")
                raise Exceptions.IndecipherableKeyException

        # Create static versions of the KeyObjects, to store/use outside the class.
        if self._private:
            self.private = self._private.encode(encoder=Text64)
        else:
            self.private = None
        self.public = self._public.encode(encoder=Text64)

        if autoexpire:
            # We want the key to expire on the last second of NEXT month.
            # So if it's currently Oct 15, we want the answer Nov31-23:59:59
            # This makes it harder to pin down keys by when they were
            # generated, since it's not based on current time
            # Calculate this by advancing the date until the month changes 2x
            # then go to midnight, then back one second.

            tmpdate = libtavern.utils.gettime(format='datetime')
            while tmpdate.month == libtavern.utils.gettime(format='datetime').month:
                tmpdate += datetime.timedelta(days=1)
            next_month = tmpdate

            while tmpdate.month == next_month.month:
                tmpdate += datetime.timedelta(days=1)

            beginning_of_day = datetime.datetime(year=tmpdate.year,day=tmpdate.day,month=tmpdate.month,microsecond=0,tzinfo=datetime.timezone.utc)
            expires_on = beginning_of_day -  datetime.timedelta(seconds=1)

            self.expires = int(expires_on.timestamp())
        else:
            self.expires = False

    @property
    def expired(self):
        """
        Has this key already expired? Are we past self.expires?
        :return: True/False
        """
        if self.expires:
            return libtavern.utils.gettime(format='timestamp') > self.expires
        return False

    def to_dict(self,include_private=False):
        """
        Save the information from a KeyPair into a dict.
        Does not include the private key without `include_private`
        """
        keydict = {}
        keydict['public'] = self.public
        keydict['generated'] = self.generated
        keydict['expires'] = self.expires
        keydict['algorithm'] = self.algorithm.value
        keydict['usage'] = self.usage.value
        if include_private is True:
            keydict['private'] = self.private
        else:
            keydict['private'] = None
        return keydict

    def from_dict(self,keydict):
        """
        Restores a key from a dictionary.
        """
        self.expires = keydict['expires']
        self.generated = keydict['generated']
        self.usage = Usage(keydict['usage'])
        self.algorithm = Algorithm(keydict['algorithm'])
        self.public = keydict['public']
        self.private = keydict['private']

        # Load in our keys by way of a tmp key, so it process __init__
        tmpkey = Keypair(usage=self.usage,private=self.private,public=self.public)
        self.private = tmpkey.private
        self.public = tmpkey.public
        self._private = tmpkey._private
        self._public = tmpkey._public

    def sign(self,text):
        """
        Sign a string, and return the signature.
        :param str text: The unicode string to sign.
        :return str: The requested signature, in base64url
        """
        if self.usage not in [Usage.signing,Usage.sign_encrypt]:
            self.logger.debug("That Key is not capable of performing that function.")
            raise Exceptions.InvalidKeyTypeException

        signed_msg = self._private.sign(text.encode('utf-8'))
        return Text64.encode(signed_msg.signature)

    def encrypt(self, text, recipient):
        """Encrypt a message to a specific recipient"""

        recipient_key = nacl.public.PublicKey(public_key=recipient,encoder=Text64)
        box = nacl.public.Box(private_key=self._private,public_key=recipient_key)

        message = text.encode('utf-8')
        nonce = nacl.utils.random(nacl.public.Box.NONCE_SIZE)
        encrypted = box.encrypt(plaintext=message, nonce=nonce)
        return Text64.encode(encrypted)

    def decrypt(self, encrypted,sender):
        """Return the plaintext of an encrypted message"""
        sender_key = nacl.public.PublicKey(public_key=sender,encoder=Text64)
        box = nacl.public.Box(private_key=self._private,public_key=sender_key)
        try:
            return box.decrypt(encrypted,encoder=libtavern.crypto.Text64).decode('utf-8')
        except nacl.exceptions.CryptoError:
            raise Exceptions.WrongKeyException

    def encrypt_file(self, newfile):
        """Encrypt a file, to the key of the specified recipient"""
        pass

    #@privatekeyaccess
    def decrypt_file(self, tmpfile):
        pass

class Exceptions(object):
    class InvalidKeyTypeException(Exception):
        """When an encryption key is scheduled for signing, or vice versa"""
        pass
    class IndecipherableKeyException(Exception):
        """The key can't be understood"""
        pass
    class NoUsageSpecifiedException(Exception):
        """Keys must have a usage type (or None)"""
        pass
    class WrongKeyException(Exception):
        """That key does not decode this text"""
        pass
    class BadSignature(Exception):
        """That key does not decode this text"""
        pass
    class InvalidPassword(Exception):
        """The Password provided does not open the encrypted private key."""
        pass
    class InvalidPasskey(Exception):
        """The Passkey provided does not open the encrypted private key."""
        pass