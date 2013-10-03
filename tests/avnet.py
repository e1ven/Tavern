import random
import timeit
import sys
import math
# This a literal translation of the AVnet.
# I used inclusive ranges and lists because the original paper did, and I wanted to make sure I followed.

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
    bits = 100

    # Every participant agrees on a Generator function
    print("Generating DH")
    p,q,g = (378019149936402528836294373203, 189009574968201264418147186601, 219179160367544848293941757544)
    #p,q,g= gen_dh_group(10)
    G = lambda x: pow(g,x,p)

    # Every participant gets a number   
    x = []
    round1 = []
    round2 = []

    ### ROUND 1
    # Loop through all participants (i)
    for i in range(n):
        # Each participant selects a random number.
        R = random.SystemRandom().getrandbits(bits)
        # Store this for each participant as x
        x.append(R)

    print("Round.. 1")
    ### When this round finishes, each participant computes the following:
    for i in range(n):

        numeratorList = []
        numerator = 1
        for j in range(i-1):
            numerator *= G(x[j])
        denominatorList = []
        denominator = 1
        for j in range(i+1,n):
            denominator *= G(x[j])
        gyi = numerator/denominator
        print("gyi - " +  str(gyi))

        print("girl")
        gciyi = pow(gyi,x[j])
        print(gciyi)
        print("Scout")

    print("Round.. 2")

    # #### Round 2
    # # Every participant broadcasts a value G(cy) and a knowledge proof for c[i], where c[i] is either x[i] or a random value 
    # # depending on whether participant Pi vetoes or not.

    # # Remember, for multiplying exponents (a^n)^m = a^(nm)

    # for i in irange(1,n):

    #     VETO = False

    #     if VETO is True:
    #         c = random.SystemRandom().getrandbits(bits)
    #     else:
    #         c = x[i]

    #     round2.append(pow(round1[i],c))
    #     print(round2[i])


def main():
    #print(gen_dh_group(100))
    avnet()
    #print(small_primes)
if __name__ == "__main__":
    main()