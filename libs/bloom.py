"""
Implementation of a Bloom filter in Python.

The Bloom filter is a space-efficient probabilistic data structure that is
used to test whether an element is a member of a set. False positives are
possible, but false negatives are not. Elements can be added to the set, but
not removed. The more elements that are added to the set, the larger the
probability of false positives.

Uses SHA-1 from Python's hashlib, but you can swap that out with any other
160-bit hash function. Also keep in mind that it starts off very sparse and
become more dense (and false-positive-prone) as you add more elements.

Forked from python-hashes by sangelone, under the MIT license.
"""


import math
import hashlib

class bloomfilter(object):
    def __init__(self, value=None, capacity=3000, false_positive_rate=0.01):
        """
        Calculates a Bloom filter with the specified parameters.
        Initalizes with a string or list/set/tuple of strings.

        'value' is the initial string or list of strings to hash,
        'capacity' is the expected upper limit on items inserted, and
        'false_positive_rate' is self-explanatory but the smaller it is, the larger your hashes!

        """
        self.hash = 0
        self.hashbits, self.num_hashes = self._optimal_size(capacity, false_positive_rate)

        # If it's a string, allow it.
        # If not, it must be an iterable of strings.
        if value is not None:
            self.add(value)

      
    def _hashes(self, item):
      """
      To create the hash functions we use the SHA-1 hash of the
      string and chop that up into 20 bit values and then
      mod down to the length of the Bloom filter.
      """
      if isinstance(item, str):
        item = item.encode('utf-8')
      m = hashlib.sha1()
      m.update(item)
      digits = m.hexdigest()

      # Add another 160 bits for every 8 (20-bit long) hashes we need
      for i in range(int(self.num_hashes / 8)):
          m.update(str(i))
          digits += m.hexdigest()

      hashes = [int(digits[i*5:i*5+5], 16) % self.hashbits for i in range(self.num_hashes)]
      return hashes  

    def _optimal_size(self, capacity, false_positive_rate):
        """Calculates minimum number of bits in filter array and
        number of hash functions given a number of enteries (maximum)
        and the desired error rate (falese positives).
        
        Example:
            m, k = self._optimal_size(3000, 0.01)   # m=28756, k=7
        """
        m = math.ceil((capacity * math.log(false_positive_rate)) / math.log(1.0 / (math.pow(2.0, math.log(2.0)))))
        k = math.ceil(math.log(2.0) * m / capacity)
        return (int(m), int(k))

    
    def add(self, item):
        "Add an item (string) to the filter. Cannot be removed later!"

        # We can only add strings. 
        if not isinstance(item,(str,bytes)):
          # if it's not a string, is it a list of strings?
          if hasattr(item,'__iter__'):
            if isinstance(item.__iter__().__next__(),(str,bytes)):
              for each in item:
                self.add(each)

        # If we're still here, abort.
        # We could typecast most objects to a string, and have this work, but that's likely to silently eat errors.
        # Better that we ensure we're deliberate.
        if not isinstance(item,(str,bytes)):
          raise Exception('BloomError', 'Only strings/bytes can be added to the filter.')

        # We need a bytestring to hash
        if isinstance(item, str):
          item = item.encode('utf-8')

        for pos in self._hashes(item):
          self.hash |= (2 ** pos)

    def __contains__(self, name):
        "This function is used by the 'in' keyword"

        if not isinstance(name,(str,bytes)):
          raise Exception('BloomError', 'Only strings/bytes can be checked against the filter.')

        retval = True
        for pos in self._hashes(name):
            retval = retval and bool(self.hash & (2 ** pos))
        return retval

    def merge(self,newbloom):
      "Merge my bloomfilter with another bloomfilter"

      if newbloom.hashbits != self.hashbits:
        raise Exception('BloomError', 'Bloomfilters must be the same size to merge.')
      if newbloom.num_hashes != self.num_hashes:
        raise Exception('BloomError', 'Bloomfilters must have the same number of hashes.')

      # Create a new obj to store the joined results in. 
      # Ignore the constructor, we'll be setting it manually.
      tmpbloom = bloomfilter()
      tmpbloom.hashbits = self.hashbits
      tmpbloom.num_hashes = self.num_hashes
      tmpbloom.hash = self.hash | newbloom.hash

      return tmpbloom