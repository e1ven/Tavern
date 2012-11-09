#/!usr/local/bin/python3

import time
from TavernCache import TavernCache, memorise

@memorise()
def test(a=4):
    print("1234")
    return 9999


print(test(a=5))
print(test(a=5))
print(test(a=5))

print(TavernCache.mc)
print(test(a=5,forcerecache=True))
print(TavernCache.mc)
