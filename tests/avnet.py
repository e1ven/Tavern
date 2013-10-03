import random
import timeit
import sys
import numpy

# This a literal translation of the AVnet.
# I used inclusive ranges and lists because the original paper did, and I wanted to make sure I followed.

def sigma_not(start,end,seq):
    totalsum = 0
    current = start
    while current <= end:
        totalsum += seq(current)
        current += 1
    return totalsum


def pi_not(start,end,seq):
    totalprod = 1
    current = start
    while current <= end:
        totalprod *= seq(current)
        current += 1
    return totalprod


def irange(param1,param2=None,param3=None):
    """Inclusive range function"""
    if param2 is None and param3 is None:
        # 1 argument passed in
        return range(param1+1)
    elif param3 is None:
        # 2 args
        return range(param1,param2+1)
    else:
        return range(param1,param2+1,param3)

class list1(list):
    """One-based version of list."""

    def _zerobased(self, i):
        if type(i) is slice:
            return slice(self._zerobased(i.start),
                         self._zerobased(i.stop), i.step)
        else:
            if i is None or i < 0:
                return i
            elif not i:
                raise IndexError("element 0 does not exist in 1-based list")
            return i - 1

    def __getitem__(self, i):
        return list.__getitem__(self, self._zerobased(i))

    def __setitem__(self, i, value):
        list.__setitem__(self, self._zerobased(i), value)

    def __delitem__(self, i):
        list.__delitem__(self, self._zerobased(i))

    def __getslice__(self, i, j):
        return list.__getslice__(self, self._zerobased(i or 1),
                                 self._zerobased(j))

    def __setslice__(self, i, j, value):
        list.__setslice__(self, self._zerobased(i or 1),
                          self._zerobased(j), value)

    def index(self, value, start=1, stop=-1):
        return list.index(self, value, self._zerobased(start),
                          self._zerobased(stop)) + 1

    def pop(self, i):
        return list.pop(self, self._zerobased(i))



def small_prime_generator(max=1000):
    """
    Generate every small prime up to `max`
    """
    prime = []
    notprime = []
    for i in range(2,max):
        if i not in notprime:
            prime.append(i) 
            for j in range(i,max,i):
                notprime.append(j)
    return prime

def miller_rabin(n,rounds=64):
    """
    True if `n` passes `k` rounds of Miller-Rabin.
    """
    if n < 2:
        return False
    
    # Eliminate the easy ones with a table
    global small_primes

    if not 'small_primes' in globals():
        small_primes = small_prime_generator(50)
    for p in small_primes:
        if n % p == 0:
            return False

    # Do Miller-Robin (40 rounds) to determine likely prime
    s = n-1
    r = 1
    while s % 2 == 0:
        s //= 2
        r +=1 

    for _ in range(rounds):
        a = random.SystemRandom().randrange(2, n - 1)
        x = pow(a, s, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def gen_prime(bits):
    prime = False
    while prime is not True:
        number = random.SystemRandom().getrandbits(bits)
        # No evens
        if not number % 2:
            number = number +1
        prime = miller_rabin(number)
    return int(number)

def gen_dh_group(bits):
    """Generate a group of primes for DH style exchange"""
    while 1:
        # Generate random prime q until 2q+1 is also a prime. 
        q = int(gen_prime(bits))
        p = (2 * q) + 1
        if miller_rabin(p):
            # A generator of 2 will work for DH, but for our AVnet we need another.
            # Generate random values (g) until  g^2 != 1 mod p and g^q == 1 mod p
            g = random.SystemRandom().randrange(2, p - 1)
            if pow(g,2,p) != 1 and pow(g,q,p) !=1:
                break
    return (p, q, g)

def dh_test(bits=100,a=None,b=None,p=None,g=None):
    """Test DH exchange"""
    if p == None:
        p,q,g = gen_dh_group(bits)
    if g == None:
        g = 2

    if a is None:
        alice_priv = random.SystemRandom().getrandbits(bits)
    else:
        alice_priv = a

    alice_pub = G(g, alice_priv, p)

    if b is None:
        bob_priv = random.SystemRandom().getrandbits(bits)
    else:
        bob_priv = b
    bob_pub = G(g, bob_priv, p)

    alice_shared_secret = pow(bob_pub, alice_priv, p)
    bob_shared_secret = pow(alice_pub, bob_priv, p)

    if alice_shared_secret == bob_shared_secret:
        print(alice_shared_secret)
        print("Match")
    else:
        print("No Match")

def avnet():

    # number of participants
    n = 10
    bits = 10

    # Every participant agrees on a Generator function
    print("Generating DH")
    # p,q,g = (378019149936402528836294373203, 189009574968201264418147186601, 219179160367544848293941757544)
    p,q,g= gen_dh_group(bits)
    p = p
    q = q
    g = g
    G = lambda x: pow(g,x,p)
    
    # Every participant gets a number 
    global x  
    x = list1()
    global gx
    gx = list1()
    gy = list1()
    round2 = list1()
    yi = list1()
    ### ROUND 1
    # Loop through all participants (i)
    for i in irange(1,n):
        
        # Each participant selects a random number.
        R = random.SystemRandom().getrandbits(bits)
        # Store this for each participant as x
        x.append(R)
        gx.append(G(R))

    print("Round.. 1")
    ### When this round finishes, each participant computes the following:
    for i in irange(1,n):
        numerator = 1
        numA = numpy.zeros(0)

        for j in irange(1,i-1):
            numerator *= gx[j]
            numA = numpy.append(numA,gx[j])

        denominator = 1
        # Doing the appends is slow, but it's for testing
        numB = numpy.zeros(0)
        for j in irange(i+1,n):
            denominator *= gx[j]
            numB = numpy.append(numB,gx[j])

        gyi = numerator/denominator
        print("gyi")
        gy.append(gyi)
        print(gyi)


        #Yi
        a = 0
        for j in irange(1,i-1):
            a += x[j]
        b = 0
        for j in irange(i+1,n):
            b += x[j]
        y = a - b      
        yi.append(y)

        gyi2 = G(abs(y))
        print("gyi2")
        print(gyi2)

    print("----")
    # result = 0
    # # Test for 0
    # for i in irange(1,n):
    #     result += x[i] * y[i]
    #     #print("Calculating " + str(x[i])  + " * " + str(y[i]) +  " = " + str(result))
    # print("Final - " + str(result))

    ## This check isn't needed, since it's mathmatically guaranteed to be true.
    # total = 0
    # for i in x:
    #     for j in x:
    #         combined = i - j
    #         total += combined
    # print("Combined - " + str(combined))

    print("Round.. 2")

    #### Round 2
    # Every participant broadcasts a value G(cy) and a knowledge proof for c[i], where c[i] is either x[i] or a random value 
    # depending on whether participant Pi vetoes or not.

    # Since we have g^yi now, if we raise that to the C power, then mod p again, we should have it.

    for i in irange(1,n):

        VETO = False
        if i == 222222:
            VETO = True
        if VETO is True:
            c = random.SystemRandom().getrandbits(bits)
            print("Veto")
        else:
            c = x[i]

        gciyi = G(c*yi[i])
        print("y - " + str(yi[i]) + " c - " + str(c) + " gciyi - " + str(gciyi) )
        # print(gciyi)
        round2.append(gciyi)

    print("Calculate..")
    # To check the final message, each participant computes the following.
    # If no one vetos, it should == 1
    # OTOH, if anyone DOES veto, it should == !1

    lastnum = 1
    for i in round2:
        print(i)
        lastnum *= i
    print("Last - " + str(lastnum))



def main():
    #print(gen_dh_group(100))
    avnet()
    #print(small_primes)
if __name__ == "__main__":
    main()