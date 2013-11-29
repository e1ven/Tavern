# coding: utf-8
import random
import mpmath
from functools import reduce
from bitarray import bitarray


if mpmath.libmp.BACKEND == 'python':
    print("Warning - Using native-Python version of mpmath. Installing GMP will be faster")

N = 10      # number of cryptographers (instances)

mpmath.mp.prec = 1024 * N
mpmath.mp.dps = prec = 1000 # set Decimal Precision

class Cryptographer(object):

    def __init__(self,number,domessage = False):
        self.number = number
        self.domessage = domessage
        self.message = bitarray()
        self.messagesize = 1024
        
        self.receievedr1 = bitarray(self.messagesize)
        self.receievedr1.setall(0)

        self.receievedr2 = bitarray(self.messagesize)
        self.receievedr2.setall(0)

        self.secrets = []
    def randomBA(self):
        
        rnd = random.SystemRandom().getrandbits(self.messagesize)
        randombits = bitarray(map(int, '{:b}'.format(rnd)))
        # Convert int to bitarray by way of string :/
        #randombits = bitarray(bin(rnd)[2:])

        # leading 0s are being stripped in the conversion. Re-add them.
        while randombits.length() < self.messagesize:
            randombits.insert(0,False)
        return randombits

    def receiveround1(self,secret):
        """
        If I get a secret from someone, add it to my storedsecret xor chain
        """
        self.receievedr1 = self.receievedr1 ^ secret

    def receiveround2(self,secret):
        """
        If I get a secret from someone, add it to my storedsecret xor chain
        """

        self.receievedr2 = self.receievedr2 ^ secret
        self.secrets.append(secret)

    def round1(self,cryptos):
        """
        Generate a series of XOR strings to hand out
        """

        # Create a message, which is either real, or simulated/random data.
        if self.domessage is True:
            print("I'm gonna do it.")
            self.message.fromstring("This is a string, sent by " + str(self.number) + ":: " + random.choice(['apple','pear','banana','squirrel']))
            # Pad messagesize until we have a constant length
            while self.message.length() < self.messagesize:
                self.message.append(False)
        else:
            self.message = self.randomBA()

        secrets = []
        # Create N secrets - We'll pass these out to our other cryptographers
        for i in cryptos:
            randomstr = self.randomBA()
            secrets.append(randomstr)

        # XOR all the secrets together, to generate a key 
        # We will then XOR this against the message to give us our final shared value to pass out
        key = bitarray(self.messagesize)
        key.setall(0)
        for i in range(len(secrets) -1 ):
            key = key ^ secrets[i]

        if self.domessage == True:
            secrets[-1] = key ^ self.message
        else:
            secrets[-1] = key

        # Now that we've generated our secrets, pass them out.
        # Everyone should get one, even me.
        for i in range(len(cryptos)):
            cryptos[i].receiveround1(secrets[i])


    def round2(self,cryptos):
        """
        Pass everyone 1 secret
        """
        for crypto in cryptos:
            crypto.receiveround2(self.receievedr1)

    def verify(self):
        """
        Verify if there was a message - If so, print and return it
        """

        if self.receievedr2.any():
            st = self.receievedr2.tostring()
            print(st)
            return st
        else:
            return False
        


def main():
  
    cryptos = []
    number_vetos = 0      

    # N dining cryptographers are sitting at a table
    for i in range(N):

        # Give them a small chance of passing a messgae.
        # domessage = not bool(random.getrandbits(2))
        if i == 4:
            domessage = True
        else:
            domessage = False

        c = Cryptographer(i,domessage)
        cryptos.append(c) 



    for c in cryptos:
        c.round1(cryptos)

    for c in cryptos:
        c.round2(cryptos)

    for c in cryptos:
        c.verify()



if __name__ == '__main__':
    main()
