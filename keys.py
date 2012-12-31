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
# We're not using  @memorise because we don't WANT cached copies of the keys hanging around, even though it'd be faster ;()


class Keys(object):

    def __init__(self, pub=None, priv=None):
        """
        Create a Key object.
        Pass in either pub=foo, or priv=foo, to use pre-existing keys.
        """
        self.logger = logging.getLogger('Tavern')
        self.pubkey = pub
        self.privkey = priv
        self.format_keys()

        self.gnuhome = tempfile.mkdtemp()
        self.gpg = gnupg.GPG(gnupghome=self.gnuhome,
            options="--no-emit-version --no-comments --no-default-keyring")
        self.gpg.encoding = 'utf-8'
        keyimport = None
        if self.privkey is not None:
            keyimport = self.gpg.import_keys(self.privkey)
        elif self.pubkey is not None:
            keyimport = self.gpg.import_keys(self.pubkey)
        if keyimport is not None:
                if keyimport.count > 0:
                    self.fingerprint = keyimport.fingerprints[0]

    def __del__(self):
        """
        Clean up after ourselves.
        In this case, remove the tempdir used to store gnukeys.
        """
        shutil.rmtree(self.gnuhome)

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
            self.privkey = self.privkey.replace("-----BEGINPGPPRIVATEKEYBLOCK-----", "-----BEGIN PGP PRIVATE KEY BLOCK-----")
            self.privkey = self.privkey.replace("-----ENDPGPPRIVATEKEYBLOCK-----", "-----END PGP PRIVATE KEY BLOCK-----")

        if self.privkey is not None:
            if "-----BEGIN PGP PRIVATE KEY BLOCK-----" in self.privkey:
                noHeaders = self.privkey[self.privkey.find("-----BEGIN PGP PRIVATE KEY BLOCK-----") + 36:self.privkey.find("-----END PGP PRIVATE KEY BLOCK-----")]
            else:
                self.logger.info("USING NO HEADER VERSION OF PRIVKEY")
                noHeaders = self.privkey
            noBreaks = "".join(noHeaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]
            self.privkey = "-----BEGIN PGP PRIVATE KEY BLOCK-----\n" + \
                withLinebreaks + "\n-----END PGP PRIVATE KEY BLOCK-----"

        if self.pubkey is not None:
            self.pubkey = self.pubkey.replace("-----BEGINPGPPUBLICKEYBLOCK-----", "-----BEGIN PGP PUBLIC KEY BLOCK-----")
            self.pubkey = self.pubkey.replace("-----ENDPGPPUBLICKEYBLOCK-----", "-----END PGP PUBLIC KEY BLOCK-----")

            if "-----BEGIN PGP PUBLIC KEY BLOCK-----" in self.pubkey:
                noHeaders = self.pubkey[self.pubkey.find("-----BEGIN PGP PUBLIC KEY BLOCK-----") + 36:self.pubkey.find("-----END PGP PUBLIC KEY BLOCK-----")]
            else:
                self.logger.info("USING NO HEADER VERSION OF PUBKEY")
                noHeaders = self.pubkey
            noBreaks = "".join(noHeaders.split())
            withLinebreaks = "\n".join(re.findall("(?s).{,64}", noBreaks))[:-1]
            self.pubkey = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n" + \
                withLinebreaks + "\n-----END PGP PUBLIC KEY BLOCK-----"

    def generate(self):
        """
        Replaces whatever keys currently might exist with new ones.
        """
        self.logger.info("MAKING A KEY.")
        key_options = self.gpg.gen_key_input(key_type="RSA", key_length=2048)
        key = self.gpg.gen_key(key_options)
        self.pubkey = self.gpg.export_keys(key.fingerprint)
        self.privkey = self.gpg.export_keys(key.fingerprint, True)

        self.fingerprint = key.fingerprint
        self.format_keys()

    def signstring(self, signstring):
        """
        Sign a string, and return back the Base64 Signature.
        """
        hashed_str = hashlib.sha512(signstring.encode('utf-8')).digest()
        encoded_hashed_str = base64.b64encode(hashed_str).decode('utf-8')
        signed_data = self.gpg.sign(
            encoded_hashed_str, keyid=self.fingerprint).data.decode('utf-8')
        return signed_data

    def verify_string(self, stringtoverify, signature):
        """
        Verify the passed in string matches the passed signature.
        We're expanding the GPG signatures a bit, so that we can verify the message matches
        Not just the signature.
        """
        verify = self.gpg.verify(signature)

        # Make sure that this is a valid signature from Someone.
        if verify.valid != True:
            self.logger.info("This key does not match")
            return False

        # Verify that it's from the user we're interested in at the moment.
        if verify.pubkey_fingerprint != self.fingerprint:
            self.logger.info("Key matches *A* user, but not the desired user.")
            return False

        # Find out the text that was originally signed
        gpg_header = "-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA1\n"
        gpg_footer = "\n-----BEGIN PGP SIGNATURE-----\n"
        startpos = signature.find(gpg_header) + len(gpg_header)
        endpos = signature.find(gpg_footer)

        if startpos > -1 and endpos > -1:
            signedtext = signature[startpos + 1:endpos]
        else:
            self.logger.info("Cannot recognize key format")
            return False

        # Make sure a fresh hash matches the one from the signature
        currenthash = hashlib.sha512(stringtoverify.encode('utf-8')).digest()
        encoded_currenthash = base64.b64encode(currenthash).decode('utf-8')

        if encoded_currenthash != signedtext:
            print("The correct user signed a string, but it was not the expected string.")
            return False
        else:
            return True

    def encrypt(self, encryptstring,encrypt_to):
        """
        Encrypt a string, to the gpg key of the specified recipient)
        """

        # In order for this to work, we need to temporarily import B's key into A's keyring.
        # We then do the encryptions, and immediately remove it.
        recipient = Keys(pub=encrypt_to)
        recipient.format_keys()
        self.gpg.import_keys(recipient.pubkey)
        encrypted_string =  str(self.gpg.encrypt(data=encryptstring,recipients=[recipient.fingerprint],always_trust=True,armor=True))
        self.gpg.delete_keys(recipient.fingerprint)
        return encrypted_string

    def decrypt(self, decryptstring):
       # self.gpg.
       decrypted_string = self.gpg.decrypt(decryptstring).data.decode('utf-8')
       return decrypted_string

    def test_signing(self):
        """
        Verify the signing/verification engine works as expected
        """
        self.format_keys()
        return self.verify_string(stringtoverify="ABCD1234", signature=self.signstring("ABCD1234"))


    def test_encryption(self):
        self.format_keys()
        recipient = Keys()
        recipient.generate()
        test_string = "foo"
        enc = self.encrypt(encryptstring=test_string,encrypt_to=recipient.pubkey)
        decrypted_string = recipient.decrypt(enc)
        if test_string == decrypted_string: 
            return True
        else:
            return False
       

