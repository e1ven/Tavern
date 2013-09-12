"""memorised module - container for the memorise python-memcache decorator"""

import itertools
from functools import wraps
import inspect
from collections import OrderedDict
import time
import json
import os
import hashlib
import time
from io import open
import hashlib
import random
try:
    import Server
    server = Server.Server()
except ImportError:
    print("server already loaded.")
# The random that comes with Python does not use /dev/urandom, it uses MT.
# Wrap random.SystemRandom so we always use expected randomness.
randrange =  random.SystemRandom().randrange

def proveWork(input,difficulty):
    """
    Produces a Proof-of-work SHA collision based on HashCash.
    This is useful for avoiding spam.
    """
    # Calculate the base hash, which we can then add to later.
    h = hashlib.sha256()
    h.update(input.encode('utf-8'))
    basehash = h.copy()

    # We'll always add a padding number, even if it's 0.
    # Even if a basestring matters, we ignore that.
    zerocount=0
    count = 0

    while zerocount < difficulty:
        newhash = basehash.copy()
        newhash.update(  str(count).encode('utf-8')  )

        # Get the raw bit string of the hash
        binver = bin(int(newhash.hexdigest(), 16))[2:]
        zerocount = 256 - len(binver)

        finalcount = count
        count +=1

    return finalcount

def checkWork(input,proof,difficulty):
    """
    Check a Proof-of-work calculation
    """
    print("Verifying Work")
    # Verify our hash
    fullstr = input + str(proof)
    verify = hashlib.sha256()
    verify.update(fullstr.encode('utf-8'))

    # Get us back to a binstring of length 256, containing only the bits
    binstr = bin(int(verify.hexdigest(), 16))[2:].zfill(256)

    # Generate a string of 0s the appropriate length.
    matchstr = ''.zfill(difficulty)

    if binstr[0:difficulty] == matchstr:
        print("Work Verifies")
        return True
    else:
        print("Work fails to verify")
        return False


def inttime():
    """
    Force 1 sec precision, so multiple requests per second cache.
    """
    return int(time.time())


def longtime():
    return str(time.time()).translate(str.maketrans('', '', '.'))


class randomWords():
    def __init__(self, fortunefile="data/fortunes"):
        self.fortunes = []
        fortunes = open(fortunefile, "r", encoding='utf-8')
        line = fortunes.readline()
        lines = 0
        while line:
            lines+= 1
            self.fortunes.append(line.rstrip().lstrip())
            line = fortunes.readline()
        print(str(lines) + " fortunes loaded.")
        fortunes.close()
        
    def random(self):
        """
        Return a Random Fortune from the stack
        """
        fortuneindex = randrange(0, len(self.fortunes) - 1)
        return self.fortunes[fortuneindex]

    def wordhash(self, st, slots=4):
        """
        Generate a WordHash, such as MinibarAvoureParapetedSlashings for a string
        """

        # Build a hash of the word
        hsh = hashlib.sha512()
        hsh.update(st.encode('utf-8'))
        hexdigest = hsh.hexdigest()

        chunksize = int(len(hexdigest) / slots)

        words = []

        for segment in chunks(hexdigest, chunksize):
            intversion = int(segment, 16)

            #figure out which array integer the word is in
            fortuneslot = intversion % len(self.fortunes)
            word = self.fortunes[fortuneslot]
            words.append(word)

        # Turn the words into a CamelCase term
        # Ensure we drop the remainder
        s = ""
        for word in words[:slots]:
            s += word.title()
        return s


def chunks(s, n):
    """Produce `n`-character chunks from `s`."""
    for start in range(0, len(s), n):
        yield s[start:start + n]



def randstr(length, printable=False):
    # Ensure it's self.logger.infoable.
    if printable == True:
        # TODO - Expand this using a python builtin.
        ran = ''.join(chr(randrange(65, 90)) for i in range(length))
    else:
        ran = ''.join(chr(randrange(48, 122)) for i in range(length))
    return ran


class TavernCache(object):
        def __init__(self):
            self.mc = OrderedDict()
            self.cache = {}
            self.queues = {}
TavernCache = TavernCache()


def getNext(typeofthing='general'):
    if typeofthing in TavernCache.queues:
        TavernCache.queues[typeofthing] = TavernCache.queues[typeofthing] + 1
    else:
        TavernCache.queues[typeofthing] = 0
    return TavernCache.queues[typeofthing]


def objresolve(obj, attrspec):
    for attr in attrspec.split("."):
        try:
            obj = obj[attr]
        except (TypeError, KeyError):
            obj = getattr(obj, attr)
    return obj



class instancer(object):
    _shared_state = {}

    def __init__(self,slot='default'):
        cn = type(self).__name__
        if not cn in self._shared_state:
            self._shared_state[cn] = {}
 
        if not slot in self._shared_state[cn]:
            self._shared_state[cn][slot] = {}
        
        self.__dict__ = self._shared_state[cn][slot]
 

class memorise(object):
        """Decorate any function or class method/staticmethod with a memcace
        enabled caching wrapper. Similar to the memoise pattern, this will push
        mutator operators into memcache.Client.set(), and pull accessor
        operations from memcache.Client.get().

        :Parameters:
          `parent_keys` : list
            A list of attributes in the parent instance or class to use for
            key hashing.
          `set` : string
            An attribute present in the parent instance or class to set
            to the same value as the cached return value. Handy for keeping
            models in line if attributes are accessed directly in other
            places, or for pickling instances.
          `ttl` : integer
            Tells memcached the time which this value should expire.
            We default to 0 == cache forever. None is turn off caching.


            If we pass a `taverncache` entry to the wrapped function, memorise will intercept it.
            taverncache='invalidate' will remove the entry from the cache, if it's there.
            taverncache='bypass' will ignore the stored entry, re-run the function, and re-store the result. 
        """

        def __init__(self, parent_keys=[], set=None, ttl=60, maxsize=None):
                # Instance some default values, and customisations
                self.parent_keys = parent_keys
                self.set = set
                self.ttl = ttl
                self.maxsize = maxsize

        def __call__(self, fn):
                @wraps(fn)
                def wrapper(*args, **kwargs):
                        # Get a list of arguement names from the func_code
                        # attribute on the function/method instance, so we can
                        # test for the presence of self or cls, as decorator
                        # wrapped instances lose frame and no longer contain a
                        # reference to their parent instance/class within this
                        # frame
                        argnames = fn.__code__.co_varnames[
                            :fn.__code__.co_argcount]
                        method = False
                        static = False
                        taverncache = None
                        if len(argnames) > 0:
                                if argnames[0] == 'self' or argnames[0] == 'cls':
                                    method = True
                                if argnames[0] == 'cls':
                                    static = True


                        arg_values_hash = []
                        # Grab all the keyworded and non-keyworded arguements so
                        # that we can use them in the hashed memcache key
                        for i, v in sorted(itertools.chain(zip(argnames, args), iter(kwargs.items()))):
                                if i not in ['self','cls','taverncache']:
                                                arg_values_hash.append(
                                                    "%s=%s" % (i, v))
                                elif i == 'taverncache':
                                    taverncache = v

                        if 'taverncache' in kwargs:
                            kwargs.pop('taverncache')

                        class_name = None
                        if method:
                                keys = []
                                if len(self.parent_keys) > 0:
                                        for key in self.parent_keys:
                                                tempkey = {}
                                                tempkey[key] = objresolve(
                                                    args[0], key)
                                                keys.append(tempkey)
                                keys = json.dumps(keys, separators=(',', ':'))
                                if static:
                                # Get the class name from the cls argument
                                        class_name = args[0].__name__
                                else:
                                # Get the class name from the self argument
                                        class_name = args[0].__class__.__name__
                                module_name = inspect.getmodule(
                                    args[0]).__name__
                                parent_name = "%s.%s[%s]::" % (
                                    module_name, class_name, keys)
                        else:
                                # Function passed in, use the module name as the
                                # parent
                                parent_name = inspect.getmodule(fn).__name__
                        # Create a unique hash of the function/method call
                        key = "%s%s(%s)" % (parent_name,
                                            fn.__name__, ",".join(arg_values_hash))


                        # If taverncache is set to 'invalidate', don't run the function..
                        # Instead, just drop the result from the cache.
                        if taverncache == 'invalidate':
                            if key in TavernCache.mc:
                                val = TavernCache.mc.pop(key)
                                return val['value']
                            else:
                                return False 


                        # Check to see if we have a valid/current cached result.
                        usecached = False
                        if key in TavernCache.mc:
                            output = TavernCache.mc[key]['value']
                            if self.ttl is None or (time.time() - TavernCache.mc[key]['timeset']) < self.ttl:
                                output = TavernCache.mc[key]['value']
                                usecached = True

                        # 'taverncache=bypass' will skip the cached value, and end up restoring.
                        if usecached == False or taverncache == 'bypass':
                            output = fn(*args, **kwargs)
                            if output is None:
                                set_value = memcache_none()
                            else:
                                set_value = output

                            # We're going to store a key.
                            # Make room if nec; This shouldn't run more than once, but the while will ensure
                            # That if we get out of whack, this will correct it.
                            if self.maxsize is not None:
                                while len(TavernCache.mc) >= self.maxsize:
                                    TavernCache.mc.popitem(last=False)
                            TavernCache.mc[key] = {'value':
                                                   set_value, 'timeset': time.time()}

                        if output.__class__ is memcache_none:
                                # Because not-found keys return
                                # a None value, we use the
                                # memcache_none stub class to
                                # detect these, and make a
                                # distinction between them and
                                # actual None values
                                output = None
                        if self.set:
                                # Set an attribute of the parent
                                # instance/class to the output value,
                                # this can help when other code
                                # accesses attribures directly, or you
                                # want to pickle the instance
                                set_attr = getattr(fn.__class__, self.set)
                                set_attr = output
                        return output
                return wrapper


class memcache_none:
        """Stub class for storing None values in memcache,
        so we can distinguish between None values and not-found
        entries.
        """
        pass