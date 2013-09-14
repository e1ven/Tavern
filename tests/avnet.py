import random
import timeit
# This a literal translation of the AVnet.
# I used inclusive ranges and lists because the original paper did, and I wanted to make sure I followed.

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



def primegenerator():
  D = {}
  q = 2  # first integer to test for primality.

  while True:
    if q not in D:
      # not marked composite, must be prime  
      yield q 

      #first multiple of q not already marked
      D[q * q] = [q] 
    else:
      for p in D[q]:
        D.setdefault(p + q, []).append(p)
      # no longer need D[q], free memory
      del D[q]

    q += 1

# http://stackoverflow.com/questions/14613304/rabin-miller-strong-pseudoprime-test-implementation-wont-work
def miller_rabin(n, k=40):
    """
    Return True if n passes k rounds of the Miller-Rabin primality
    test (and is probably prime). Return False if n is proved to be
    composite.
    """
    if n < 2: return False
    for p in small_primes:
        if n < p * p:
            return True
        if n % p == 0:
            return False
    r, s = 0, n - 1
    while s % 2 == 0:
        r += 1
        s //= 2
    for _ in range(k):
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
        p = (2 * q)
        a = (p/2)
        if a != q:
            print(repr(a))
            print(repr(q))
            raise Exception("Noooo!")
        if miller_rabin(p):
            # A generator of 2 will provide just as much security as any other, and is cheaper.
            g = 2
            break
    return (p, q, g)


def main():

    # Setup a global small_primes list
    global small_primes
    small_primes = []
    primgen = primegenerator()
    for _ in range(1,1000):
        small_primes.append(primgen.__next__())

    # # number of participants
    # n = 10

    # # Every participant gets a number
    # i = list1()
    # for loop in irange(1,10):
    #     i.append(loop)

    # # Every participant agrees on a Generator function
    # nonce = random.SystemRandom().randrange(100,200)

    print(gen_dh_group(100))
    #print(small_primes)
if __name__ == "__main__":
    main()