from server import *
from container import *

#Seed the random number generator with 1024 random bytes (8192 bits)
M2Crypto.Rand.rand_seed (os.urandom (1025))

s = Server("Threepwood.savewave.com.PluricServerSettings")
s.saveconfig()
c = Container(importfile='52dfc8ea26abc1c6a23e57b413116f17799a861e1403db5aa4b7c2d6e572c52e0f9885d0fcc4ca5c3cb92d84280c1646ace0f99dbaafefa3c189eadf5ac9cd8f.7zPluricContainer')
s.receivecontainer(c.text())
