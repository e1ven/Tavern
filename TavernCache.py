"""memorised module - container for the memorise python-memcache decorator"""

import itertools
from functools import wraps
import inspect
from collections import OrderedDict
import time
import json


class TavernCache(object):
        def __init__(self):
            self.mc = OrderedDict()
            self.store = OrderedDict()
TavernCache = TavernCache()


def storething(*args, ttl=60, maxsize=None, value, key=None):
    if key is None:
        key = json.dumps(args, separators=(',', ':'))
    if maxsize is not None:
        while len(TavernCache.store) >= maxsize:
            TavernCache.store.popitem(last=False)
    TavernCache.store[key] = {'value': value, 'timeset': time.time()}
    print(TavernCache.store)


def getthing(*args, ttl=60, key=None):
    if key is None:
        key = json.dumps(args, separators=(',', ':'))
    output = None
    if key in TavernCache.store:
        if ttl is None or (time.time() - TavernCache.store[key]['timeset']) < ttl:
            output = TavernCache.store[key]['value']
    return output


def objresolve(obj, attrspec):
    for attr in attrspec.split("."):
        try:
            obj = obj[attr]
        except (TypeError, KeyError):
            obj = getattr(obj, attr)
    return obj


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

            If the original function has a "forcerecache" paramater, re will respect it.
        """

        def __init__(self, parent_keys=[], recache=True, set=None, ttl=60, maxsize=None):
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
                        forcerecache = False
                        if len(argnames) > 0:
                                if argnames[0] == 'self' or argnames[0] == 'cls':
                                        method = True
                                        if argnames[0] == 'cls':
                                                static = True

                        arg_values_hash = []
                        # Grab all the keyworded and non-keyworded arguements so
                        # that we can use them in the hashed memcache key
                        for i, v in sorted(itertools.chain(zip(argnames, args), iter(kwargs.items()))):
                                if i != 'self':
                                        if i != 'cls':
                                            if i != 'forcerecache':
                                                arg_values_hash.append(
                                                    "%s=%s" % (i, v))
                                            else:
                                                forcerecache = v

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
                        # Check to see if we have the value, we're inside the TTL, and we're not over maxsize.
                        # If not true to both, then re-calculate and store.

                        usecached = False
                        if key in TavernCache.mc:
                            output = TavernCache.mc[key]['value']
                            if self.ttl is None or (time.time() - TavernCache.mc[key]['timeset']) < self.ttl:
                                output = TavernCache.mc[key]['value']
                                usecached = True

                        if usecached == False or forcerecache == True:
                            # Allow the caller to send in a "forcerecache" entry
                            # This will cause us to NOT use the cache

                            if 'forcerecache' in kwargs:
                                kwargs.pop('forcerecache')
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
