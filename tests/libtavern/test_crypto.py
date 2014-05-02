import libtavern.utils
import libtavern.crypto
from nose.tools import *
import unittest
import nacl.exceptions
import time

KEY_LENGTH = 43

class Text64Test(unittest.TestCase):
    def test_encode(self):
        """Ensure we can encode to Text64"""
        teststr = "This is a test"
        binstr = teststr.encode('utf-8')
        eq_(libtavern.crypto.Text64.encode(binstr),'VGhpcyBpcyBhIHRlc3Q')

    def test_decode(self):
        """Ensure we can decode Text64"""
        encoded = 'VGhpcyBpcyBhIHRlc3Q'
        eq_(libtavern.crypto.Text64.decode('VGhpcyBpcyBhIHRlc3Q'),b'This is a test')

    def test_base64_padding(self):
        """Ensure the Base64 padding (===) stripping functions"""
        # teststr -> base64.b64encode(b'1234') ->  b'MTIzNA=='
        # Strip off the ==, convert to UTF-8
        eq_(libtavern.crypto.Text64.decode('MTIzNA'),b'1234')
        eq_(libtavern.crypto.Text64.decode('MTIzNA='),b'1234')
        eq_(libtavern.crypto.Text64.decode('MTIzNA=='),b'1234')
        eq_(libtavern.crypto.Text64.decode('MTIzNA================'),b'1234')

    def test_back_and_forth(self):
        """Convert a string in, then out"""
        teststr = "abcd this is a Test"
        binstr = teststr.encode('utf-8')
        eq_(libtavern.crypto.Text64.decode(libtavern.crypto.Text64.encode(binstr)).decode('utf-8'),teststr)

def test_verify_signature():
    """Ensure that a good signature verifies"""
    text = "Can we verify signed text?"
    key = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.signing)
    sig = key.sign(text)
    result = libtavern.crypto.verify_signature(signature=sig,text=text,signing_key=key.public)
    eq_(text,result)

@raises(libtavern.crypto.Exceptions.BadSignature)
def test_verify_signature_fails():
    """Ensure a bad signature fails to verify"""
    text = "Can we verify signed text?"
    key1 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.signing)
    key2 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.signing)
    sig = key1.sign(text)
    libtavern.crypto.verify_signature(signature=sig,text=text,signing_key=key2.public)

class TestKeyPair(unittest.TestCase):
    def test_generate_signing(self):
        """Generate a private and public key"""
        key = libtavern.crypto.Keypair(libtavern.crypto.Usage.signing)
        ok_(key != None)
        ok_(key.private != None)
        ok_(key.public != None)
        ok_(key.private != key.public)
        ok_(len(key.private) == KEY_LENGTH)
        ok_(len(key.public) == KEY_LENGTH)

    def test_autoexpire(self):
        """Verify the expiration component of the key"""
        key = libtavern.crypto.Keypair(libtavern.crypto.Usage.signing,autoexpire=True)
        ok_(key.expires != None)
        ok_(key.expires > time.time(),"Key should be valid right now")
        ok_(key.expires > time.time() + 2332800, "Key should be valid in 27 days")
        ok_(key.expires < time.time() + 5443200, "Key should not be valid in 32 days")

    def test_to_dict(self):
        """Verify the export to a dict"""
        key = libtavern.crypto.Keypair(libtavern.crypto.Usage.signing,autoexpire=True)
        keydict = key.to_dict(include_private=True)
        eq_(keydict['expires'],key.expires)
        ok_(len(keydict['private']) == KEY_LENGTH)
        ok_(len(keydict['public']) == KEY_LENGTH)

        keydict = key.to_dict(include_private=False)
        eq_(keydict['expires'],key.expires)
        ok_(len(keydict['public']) == KEY_LENGTH)
        ok_(keydict.get('private',) == None)

        eq_(keydict,key.to_dict())

    def test_from_dict_NoPrivkey(self):
        """Verify going to/from a dict"""
        testdict = {'usage': 1,
                    'algorithm': 23,
                    'generated': 1398737948,
                    'public': 'O8t6s1KWpFHBXCePR17WnH7ChQGBcmwLXzdPLA209Mc',
                    'expires': False,
                    'private': None}
        key = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.signing,keydict=testdict)
        eq_(testdict,key.to_dict(include_private=True))

    def test_from_dict_Privkey(self):
        """Verify going to/from a dict"""
        testdict = {'usage': 1,
                    'algorithm': 23,
                    'generated': 1398737948,
                    'public': 'O8t6s1KWpFHBXCePR17WnH7ChQGBcmwLXzdPLA209Mc',
                    'expires': False,
                    'private': 'Am_-hhSKX2FoOFHBbgSq7xbPDxF-IiOC6exIvlTxgHM'}
        key = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.signing,keydict=testdict)
        eq_(testdict,key.to_dict(include_private=True))

    def test_expired(self):
        """Ensure we report on expired keys"""
        key = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.signing)
        key.expires = key.generated - 10
        ok_(key.expired)

    def test_encrypt(self):
        """Ensure we can encrypt strings"""
        text = "This is plaintext"
        key1 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.encryption)
        key2 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.encryption)
        encrypted = key1.encrypt(text,key2.public)

        # Our message will be exactly 40 bytes longer than the original
        # message as it stores authentication information and nonce alongside it.
        ok_(len(text.encode('utf-8')) + 40 == len(libtavern.crypto.Text64.decode(encrypted)))

    def test_decrypt(self):
        """Ensure we can decrypt strings"""
        text = "This is plaintext"
        key1 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.encryption)
        key2 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.encryption)
        encrypted = key1.encrypt(text,key2.public)
        decrypted = key2.decrypt(encrypted,key1.public)
        print(decrypted)
        eq_(text,decrypted)

    @raises(libtavern.crypto.Exceptions.WrongKeyException)
    def test_baddecrypt(self):
        """Try decrypting with the wrong key."""
        text = "This is plaintext"
        key1 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.encryption)
        key2 = libtavern.crypto.Keypair(usage=libtavern.crypto.Usage.encryption)
        encrypted = key1.encrypt(text,key2.public)
        _ = key2.decrypt(encrypted,key2.public)

class TestLockedKey(unittest.TestCase):
    def test_init(self):
        """Ensure we can create a locked key, and restore it using the passkey"""
        lk = libtavern.crypto.LockedKey(usage=libtavern.crypto.Usage.signing)
        passkey = lk.generate()
        lkdict = lk.unlock(passkey).to_dict(include_private=True)
        ok_(lkdict['private'],"Ensure the Key restores properly")
        ok_(len(lkdict['private']) == KEY_LENGTH,"Ensure we have a key of the proper length")

        lkdict1 = lk.to_dict()
        eq_(lkdict1['private'],None,"Ensure we have NO private key unless unlocked.")