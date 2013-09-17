# Example from http://blog.markloiseau.com/2013/01/diffie-hellman-tutorial-in-python/ 
# for testing the DH groups.
#!/usr/bin/env python

from binascii import hexlify
import hashlib

import random
secure_random = random.SystemRandom().getrandbits

class DiffieHellman(object):
    """
    An implementation of the Diffie-Hellman protocol.
    This class uses the 6144-bit MODP Group (Group 17) from RFC 3526.
    This prime is sufficient to generate an AES 256 key when used with a 540+ bit
    exponent.
    """

    prime = 233172704936600506538617975596170741822594089451305598516045006493456811551614505396001416287572251861674561594546676573151898301121211776952494783127435615365133303790300324634262013876208239501607408501267045874718688091007473950238765006824045294927228005944955637615349030182378815934432307311010873986067  
    generator = 2

    def __init__(self):
        """
        Generate the public and private keys.
        """
        self.privateKey = self.genPrivateKey(576)
        self.publicKey = self.genPublicKey()

    def genPrivateKey(self, bits):
        """
        Generate a private key using a secure random number generator.
        """
        return secure_random(bits)

    def genPublicKey(self):
        """
        Generate a public key X with g**x % p.
        """
        return pow(self.generator, self.privateKey, self.prime)

    def checkPublicKey(self, otherKey):
        """
        Check the other party's public key to make sure it's valid.
        Since a safe prime is used, verify that the Legendre symbol is equal to one.
        """
        print((self.prime))
        if(otherKey > 2 and otherKey < self.prime - 1):
            print("In if")
            print(otherKey)
            print("----")
            print((pow(otherKey, (self.prime - 1)//2, self.prime)))
            print("####")
            if(pow(otherKey, (self.prime - 1)//2, self.prime) == 1):
                return True
        return False

    def genSecret(self, privateKey, otherKey):
        """
        Check to make sure the public key is valid, then combine it with the
        private key to generate a shared secret.
        """
        if(self.checkPublicKey(otherKey) == True):
            sharedSecret = pow(otherKey, privateKey, self.prime)
            return sharedSecret
        else:
            raise Exception("Invalid public key.")

    def genKey(self, otherKey):
        """
        Derive the shared secret, then hash it to obtain the shared key.
        """
        self.sharedSecret = self.genSecret(self.privateKey, otherKey)
        s = hashlib.sha256()
        s.update(str(self.sharedSecret).encode('utf-8'))
        self.key = s.digest()

    def getKey(self):
        """
        Return the shared secret key
        """
        return self.key

    def showParams(self):
        """
        Show the parameters of the Diffie Hellman agreement.
        """
        print("Parameters:")
        print()
        print("Prime: ", self.prime)
        print("Generator: ", self.generator)
        print("Private key: ", self.privateKey)
        print("Public key: ", self.publicKey)
        print()

    def showResults(self):
        """
        Show the results of a Diffie-Hellman exchange.
        """
        print("Results:")
        print()
        print("Shared secret: ", self.sharedSecret)
        print("Shared key: ", hexlify(self.key))
        print()

if __name__=="__main__":
    """
    Run an example Diffie-Hellman exchange 
    """

    a = DiffieHellman()
    b = DiffieHellman()

    a.genKey(b.publicKey)
    b.genKey(a.publicKey)

    if(a.getKey() == b.getKey()):
        print("Shared keys match.")
        print("Key:", hexlify(a.key))
    else:
        print("Shared secrets didn't match!")
        print("Shared secret: ", a.genSecret(b.publicKey))
        print("Shared secret: ", b.genSecret(a.publicKey))
