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

mult = lambda x,y: x*y

class Diffie(object):
    p = 378019149936402528836294373203
    q = 189009574968201264418147186601
    g = 219179160367544848293941757544

    def verify(self,bits=100):
        """Test DH exchange"""

        alice_priv = random.SystemRandom().getrandbits(bits)
        alice_pub = pow(self.g, alice_priv, self.p)
        bob_priv = random.SystemRandom().getrandbits(bits)
        bob_pub = pow(self.g, bob_priv, self.p)

        alice_shared_secret = pow(bob_pub, alice_priv, self.p)
        bob_shared_secret = pow(alice_pub, bob_priv, self.p)

        # Reply with T/F if the key works.
        return  alice_shared_secret == bob_shared_secret


class Cryptographer(object):

    def __init__(self,number,veto = False,bits=1024):
        self.number = number
        self.veto = veto
        self.bits=bits

    def compute_gx(self):
        self.x = random.SystemRandom().getrandbits(self.bits)          # generating a big random number x (less than q)
        self.gx = mpmath.power(Diffie.g, self.x)

    def compute_gy(self,table):
        # Compute gy
        gxs = [c.give_gx() for c in table]                          # participants are sharing their gx

        numerator = 1
        for j in range(self.number):
            numerator *= gxs[j]

        denominator = 1
        for j in range(self.number+1,len(gxs)):
            denominator *= gxs[j]

        self.gy = mpmath.mpf(numerator)/mpmath.mpf(denominator)

        # Generate c
        if self.veto:
            self.c = random.randint(Diffie.q>>3, Diffie.q-1   ) # a big random number which could be x (generated the same way)
        else:
            self.c = self.x

        self.gcy = mpmath.power(self.gy,self.c)
        # if self.gcy >= 1:
        #     print(self.number)    
    def any_veto(self,table):

        r = 1
        for c in table:
            r *= c.give_gcy()
        limit = mpmath.power(mpmath.mpf(0.1),(mpmath.mp.dps/2))

        if abs(r-1)>limit:
            return True
        else:
            return False

        # return abs(r-1)>limit and True or False
    
    # Interactions between cryptographers
    def give_gx(self):
        return self.gx 
        
    def give_gcy(self):
        return self.gcy
                
def AVBit():

    # Create our DH keys
    a = Diffie()
    a.verify()
    
    cryptos = []
    number_vetos = 0        
    # N dining cryptographers are sitting at a table
    for i in range(N):

        # Give them a small  chance of vetoing.
        veto = not bool(random.getrandbits(5))
        if veto:
            number_vetos +=1
        c = Cryptographer(i,veto)
        cryptos.append(c)


    # print('Round 1')
    [c.compute_gx() for c in cryptos]
    
    # print('Round 2')
    [c.compute_gy(cryptos) for c in cryptos]
        
    # Check to see if anyone Vetoed.
    if cryptos[0].any_veto(cryptos):
        print('At least one person was observed to veto. - Actual count was ' + str(number_vetos) + ' vetoers.')
        return True

    else:
        print('No people were observed to veto. - Actual count was ' + str(number_vetos) + ' vetoers.')
        return False

def main():

    vetos = bitarray()

    for i in range(100):

        # Determine if anyone vetos for each bit.
        a = AVBit()
        vetos.append(a)

        # Print status.
        if i % 10 == 0:
            print(i)
    print(vetos)        

if __name__ == '__main__':
    main()
