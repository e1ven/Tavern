import os
import re
import string
import hashlib
import base64
import logging
import functools
import gnupg
import tempfile
import shutil
import time
import functools
import datetime
import calendar
import time
import libtavern


# We're not using  @memorise because we don't WANT cached copies of the
# keys hanging around, even though it'd be faster ;()


class Key(object):

    def privatekeyaccess(fn):
        """privatekeyaccess is an wrapper decorator.

        It will call the unlock() function in the obj if it has one.
        This allows us to define a separate unlock for each type of key,
        and call them from the parent.

        """
        @functools.wraps(fn)
        def wrapper(cls, *args, **kwargs):
            passkey = None
            # If our original class has an unlock function, call it.
            if hasattr(cls, 'unlock'):
                # If we passed in a passkey parameter, remove it, and pass it
                # to the unlock instead.
                if 'passkey' in kwargs:
                    passkey = kwargs.pop('passkey')
                    cls.unlock(pk)
                else:
                    cls.unlock()
            result = fn(cls, *args, **kwargs)
            # Now, relock it back up.
            if hasattr(cls, 'lock'):
                if passkey is not None:
                    cls.lock(passkey)
                else:
                    cls.lock()
            return result
        return wrapper

    def __init__(self, pub=None, priv=None):
        """Create a Key object.

        Pass in either pub=foo, or priv=foo, to use pre-existing keys.

        """
        self.logger = logging.getLogger('Tavern')
        self.pubkey = pub
        self.privkey = priv
        self.expires = None
        self.gnuhome = tempfile.mkdtemp(dir='tmp/gpgfiles')

        # Pass in options to anonymize where possible, and use sane-defaults
        options = ''

        self.gpg = gnupg.GPG(verbose=False, gnupghome=self.gnuhome, options='--options tmp/gpgfiles/gpg.conf -vv')
        self.gpg.encoding = 'utf-8'

        self._format_keys()
        keyimport = None
        if self.privkey is not None:
            keyimport = self.gpg.import_keys(self.privkey)
        elif self.pubkey is not None:
            keyimport = self.gpg.import_keys(self.pubkey)
        if keyimport is not None:
            if keyimport.count > 0:
                self.fingerprint = keyimport.fingerprints[0]
                self._setKeyDetails()

    def __del__(self):
        """Clean up after ourselves.

        In this case, remove the tempdir used to store gnukeys.

        """

        # Try to delete it as a pubkey first.
        # If that complains, delete it like a privkey

        for tmpkey in self.gpg.list_keys():
            # Detect if we have a privkey
            is_privkey = self.privkey is not None
            # Then try to delete it, using the value we got.
            result = self.gpg.delete_keys(tmpkey['fingerprint'], secret=is_privkey)

            # If we were wrong about the status, go ahead and delete the privkey anyway, then the pubkey
            if result.status != 'ok':
                self.gpg.delete_keys(tmpkey['fingerprint'], secret=True)
                self.gpg.delete_keys(tmpkey['fingerprint'], secret=False)

            if shutil is not None:
                shutil.rmtree(self.gnuhome, ignore_errors=True, onerror=None)

    def _setKeyDetails(self):
        """Set the format of the key.

        Format types via https://tools.ietf.org/html/rfc4880#section-9.1

        """

        self.keydetails = {}
        self.keydetails['format'] = 'gpg'
        self.keydetails['uids'] = []

        if len(self.gpg.list_keys()) > 1:
            raise Exception(
                "KeyError",
                "There are too many keys in this keyring - I'm not sure what's going on anymore.")

        details = self.gpg.list_keys()[0]

        if self.fingerprint != details['fingerprint']:
            raise Exception('KeyError', 'Key not found in keyring.')

        self.keydetails['length'] = details['length']
        self.keydetails['expires'] = details['expires']

        for uid in self.gpg.list_keys()[0]['uids']:
            self.keydetails['uids'].append(uid)

        if details['algo'] == '1' or 'R':
            self.keydetails['algorithm'] = 'RSA'
            self.keydetails['sign'] = True
            self.keydetails['encrypt'] = True
        elif details['algo'] == '2' or 'r':
            self.keydetails['algorithm'] = 'RSA'
            self.keydetails['sign'] = False
            self.keydetails['encrypt'] = True
        elif details['algo'] == '3' or 's':
            self.keydetails['algorithm'] = 'RSA'
            self.keydetails['sign'] = True
            self.keydetails['encrypt'] = False
        elif details['algo'] == '16' or 'g':
            self.keydetails['algorithm'] = 'ElGamal'
            self.keydetails['sign'] = False
            self.keydetails['encrypt'] = True
        elif details['algo'] == '20' or 'G':
            self.keydetails['algorithm'] = 'ElGamal'
            self.keydetails['sign'] = True
            self.keydetails['encrypt'] = True
        elif details['algo'] == '17' or 'D':
            self.keydetails['algorithm'] = 'DSA'
            self.keydetails['sign'] = True
            self.keydetails['encrypt'] = False
        elif details['algo'] == '18' or 'e':
            self.keydetails['algorithm'] = 'ECDH'
            self.keydetails['sign'] = False
            self.keydetails['encrypt'] = True
        elif details['algo'] == '19' or 'e':
            self.keydetails['algorithm'] = 'ECDSA'
            self.keydetails['sign'] = True
            self.keydetails['encrypt'] = False
        elif details['algo'] == '_' or '?':
            self.keydetails['algorithm'] = 'Unknown'
            self.keydetails['sign'] = False
            self.keydetails['encrypt'] = False

    def _format_keys(self):
        """Ensure the keys are in the proper format, with linebreaks.

        linebreaks are every 64 characters, and we have a header/footer.

        """
        # Strip out the headers
        # Strip out the linebreaks
        # Re-Add the Linebreaks
        # Re-add the headers
        # Check for compressed versions-
        if self.privkey is not None:
            self.privkey = self.privkey.replace(
                "-----BEGINPGPPRIVATEKEYBLOCK-----",
                "-----BEGIN PGP PRIVATE KEY BLOCK-----")
            self.privkey = self.privkey.replace(
                "-----ENDPGPPRIVATEKEYBLOCK-----",
                "-----END PGP PRIVATE KEY BLOCK-----")

            if "-----BEGIN PGP PRIVATE KEY BLOCK-----" in self.privkey:
                noheaders = self.privkey.replace(
                    '-----BEGIN PGP PRIVATE KEY BLOCK-----',
                    '').lstrip()
                noheaders = noheaders.replace(
                    '-----END PGP PRIVATE KEY BLOCK-----',
                    '').rstrip()
            else:
                noheaders = self.privkey

            noBreaks = "".join(noheaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]
            self.privkey = "-----BEGIN PGP PRIVATE KEY BLOCK-----\n" + \
                withLinebreaks + "\n-----END PGP PRIVATE KEY BLOCK-----"

        if self.pubkey is not None:
            self.pubkey = self.pubkey.replace(
                "-----BEGINPGPPUBLICKEYBLOCK-----",
                "-----BEGIN PGP PUBLIC KEY BLOCK-----")
            self.pubkey = self.pubkey.replace(
                "-----ENDPGPPUBLICKEYBLOCK-----",
                "-----END PGP PUBLIC KEY BLOCK-----")

            if "-----BEGIN PGP PUBLIC KEY BLOCK-----" in self.pubkey:
                noheaders = self.pubkey.replace(
                    "-----BEGIN PGP PUBLIC KEY BLOCK-----",
                    '').lstrip()
                noheaders = noheaders.replace(
                    "-----END PGP PUBLIC KEY BLOCK-----",
                    '').rstrip()
            else:
                noheaders = self.pubkey
            noBreaks = "".join(noheaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]
            self.pubkey = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n" + \
                withLinebreaks + "\n-----END PGP PUBLIC KEY BLOCK-----"
            self.minipubkey = noBreaks

    def isValid(self):
        """Does this key have an 'expires' variable set in the past?"""
        if vars(self).get('expires') is not None:
            return time.time() < self.expires
        else:
            print("Does not expire")
            return True

    def generate(self, autoexpire=False):
        """Replaces whatever keys currently might exist with new ones."""
        self.logger.debug("MAKING A KEY.")
        # We don't want to use gen_key_input here because the library insists on having an email and name, when those aren't needed.
        # The OpenPGP spec just demands SOMETHING as an ID. We'll use the comment field, and give it "TAVERN" so they are all identical.

        # TODO - Replace this with values from tavernSettings after #198
        keystr = 'Key-Type: RSA\nKey-Length: 3072\nName-Real: TAVERN\n%commit'

        key = self.gpg.gen_key(keystr)
        self.pubkey = self.gpg.export_keys(key.fingerprint)
        self.privkey = self.gpg.export_keys(key.fingerprint, True)
        self.fingerprint = key.fingerprint
        self._format_keys()
        self._setKeyDetails()
        self.generated = int(time.time())

        if autoexpire:
            # If this key should expire, we want to do it at the end of NEXT month.
            # So if it's currently Oct 15, we want the answer Nov31-23:59:59
            # This makes it harder to pin down keys by when they were
            # generated, since it's not based on current time

            number_of_days_this_month = calendar.monthrange(
                datetime.datetime.now().year,
                datetime.datetime.now().month)[1]
            number_of_days_next_month = calendar.monthrange(
                datetime.datetime.now().year,
                datetime.datetime.now().month + 1)[1]
            two_months = datetime.datetime.now() + datetime.timedelta(
                days=number_of_days_this_month + number_of_days_next_month)
            expiresdate = datetime.date(
                two_months.year,
                two_months.month,
                1) - datetime.timedelta(
                days=1)
            expiresdatetime = datetime.datetime.combine(
                expiresdate, datetime.time.max)
            self.expires = calendar.timegm(expiresdatetime.utctimetuple())

    @privatekeyaccess
    def signstring(self, signstring):
        """Sign a string, and return back the Base64 Signature."""
        hashed_str = hashlib.sha512(signstring.encode('utf-8')).digest()
        encoded_hashed_str = base64.b64encode(hashed_str).decode('utf-8')
        signed_data = self.gpg.sign(
            encoded_hashed_str, keyid=self.fingerprint).data.decode('utf-8')

        if not signed_data:
            raise Exception("KeyError", "Signing Error")
        return signed_data

    def verify_string(self, stringtoverify, signature):
        """Verify the passed in string matches the passed signature.

        We're expanding the GPG signatures a bit, so that we can verify
        the message matches Not just the signature.

        """
        verify = self.gpg.verify(signature)

        # Make sure that this is a valid signature from Someone.
        if verify.valid is not True:
            self.logger.info("This key does not match")
            return False

        # Verify that it's from the user we're interested in at the moment.
        if verify.pubkey_fingerprint != self.fingerprint:
            self.logger.info("Key matches *A* user, but not the desired user.")
            return False

        # We need to isolate the original text, so we can verify it.
        # Break off each chunk that we know has to be there, one piece at a time.
        # We don't look for the exact hash, since it could be several.
        gpg_header = "-----BEGIN PGP SIGNED MESSAGE-----"
        hash_header = "Hash: "
        gpg_pos = signature.find(gpg_header)
        hash_pos = signature.find(hash_header, gpg_pos)

        start_pos = signature.find('\n', hash_pos)

        gpg_footer = "\n-----BEGIN PGP SIGNATURE-----\n"
        end_pos = signature.find(gpg_footer)

        if start_pos > -1 and end_pos > -1:
            signedtext = signature[start_pos + 1:end_pos].lstrip()
        else:
            self.logger.info("Cannot recognize key format")
            return False

        # Make sure a fresh hash matches the one from the signature
        currenthash = hashlib.sha512(stringtoverify.encode('utf-8')).digest()
        encoded_currenthash = base64.b64encode(currenthash).decode('utf-8')

        if encoded_currenthash != signedtext:
            print(
                "The correct user signed a string, but it was not the expected string.")
            return False
        else:
            return True

    @privatekeyaccess
    def encrypt(self, encryptstring, encrypt_to):
        """Encrypt a string, to the gpg key of the specified recipient)"""

        # In order for this to work, we need to temporarily import B's key into A's keyring.
        # We then do the encryptions, and immediately remove it.
        recipient = Key(pub=encrypt_to)
        recipient._format_keys()
        self.gpg.import_keys(recipient.pubkey)
        encrypted_string = str(
            self.gpg.encrypt(data=encryptstring,
                             recipients=[recipient.fingerprint],
                             always_trust=True,
                             armor=True))
        self.gpg.delete_keys(recipient.fingerprint)
        return encrypted_string

    @privatekeyaccess
    def decrypt(self, decryptstring):
        # self.gpg.
        decrypted = self.gpg.decrypt(decryptstring)

        if decrypted.ok is not True:
            return False
        decrypted_string = decrypted.data.decode('utf-8')
        return decrypted_string
    
    def testius(self):
        print(libtavern.utils.longtime)

    @privatekeyaccess
    def encrypt_file(self, newfile):
        """Encrypt a string, to the gpg key of the specified recipient)"""

        # In order for this to work, we need to temporarily import B's key into A's keyring.
        # We then do the encryptions, and immediately remove it.
        recipient = Key(pub=encrypt_to)
        recipient._format_keys()
        self.gpg.import_keys(recipient.pubkey)

        tmpfilename = "tmp/gpgfiles/" + libtavern.utils.longtime(
        ) + libtavern.utils.randstr(50, printable=True)

        self.gpg.encrypt_file(
            stream=oldfile,
            recipients=[recipient.fingerprint],
            always_trust=True,
            armor=True,
            output=tmpfilename)
        self.gpg.delete_keys(recipient.fingerprint)
        return tmpfilename

    @privatekeyaccess
    def decrypt_file(self, tmpfile):

        tmpfilename = "tmp/gpgfiles/" + libtavern.utils.longtime(
        ) + libtavern.utils.randstr(50, printable=True)
        self.gpg.decrypt_file(tmpfile, output=tmpfilename)
        return tmpfilename

    def test_signing(self):
        """Verify the signing/verification engine works as expected."""
        self._format_keys()
        return (
            self.verify_string(
                stringtoverify="ABCD1234",
                signature=self.signstring("ABCD1234"))
        )

    def test_encryption(self):
        self._format_keys()
        recipient = Key()
        recipient.generate()
        test_string = "foo"
        enc = self.encrypt(
            encryptstring=test_string, encrypt_to=recipient.pubkey)
        decrypted_string = recipient.decrypt(enc)
        if test_string == decrypted_string:
            return True
        else:
            return False

    def unlock(privkey=None):
        print("Don't run me.")
