"""memorised module - container for the memorise python-memcache decorator"""
__author__ = 'Colin Davis <colin [at] e1ven [dot] com>'
__docformat__ = 'restructuredtext en'
__version__ = '2.0.0'

import itertools
from functools import wraps
import inspect
from collections import OrderedDict
import time

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
        """

        def __init__(self, parent_keys=[], set=None, ttl=60,maxsize=None):
                # Instance some default values, and customisations
                self.parent_keys = parent_keys
                self.set = set
                self.ttl = ttl
                self.mc = OrderedDict()
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
                        argnames = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                        method = False
                        static = False
                        if len(argnames) > 0:
                                if argnames[0] == 'self' or argnames[0] == 'cls':
                                        method = True
                                        if argnames[0] == 'cls':
                                                static = True

                        arg_values_hash = []
                        # Grab all the keyworded and non-keyworded arguements so
                        # that we can use them in the hashed memcache key
                        for i,v in sorted(itertools.chain(zip(argnames, args), iter(kwargs.items()))):
                                if i != 'self':
                                        if i != 'cls':
                                                arg_values_hash.append("%s=%s" % (i,v))

                        class_name = None
                        if method:
                                keys = []
                                if len(self.parent_keys) > 0:
                                        for key in self.parent_keys:
                                                keys.append("%s=%s" % (key, getattr(args[0], key)))
                                keys = ','.join(keys)
                                if static:
                                # Get the class name from the cls argument
                                        class_name = args[0].__name__
                                else:
                                # Get the class name from the self argument
                                        class_name = args[0].__class__.__name__
                                module_name = inspect.getmodule(args[0]).__name__
                                parent_name = "%s.%s[%s]::" % (module_name, class_name, keys)
                        else:
                                # Function passed in, use the module name as the
                                # parent
                                parent_name = inspect.getmodule(fn).__name__
                        # Create a unique hash of the function/method call
                        key = "%s%s(%s)" % (parent_name, fn.__name__, ",".join(arg_values_hash))


                        # Check to see if we have the value, we're inside the TTL, and we're not over maxsize.
                        # If not true to both, then re-calculate and store.

                        usecached = False
                        if key in self.mc:
                            output = self.mc[key]['value']
                            if self.ttl is None or (time.time() - self.mc[key]['timeset']) < self.ttl:
                                output = self.mc[key]['value']
                                usecached = True

                        if usecached == False:
                            output = fn(*args, **kwargs)
                            if output is None:
                                set_value = memcache_none()
                            else:
                                set_value = output


                            # We're going to store a key.
                            # Make room if nec; This shouldn't run more than once, but the while will ensure
                            # That if we get out of whack, this will correct it.

                            if self.maxsize is not None:
                                while len(self.mc) >= self.maxsize:
                                    self.mc.popitem(last=False)
                            self.mc[key] = { 'value':set_value, 'timeset':time.time() }


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