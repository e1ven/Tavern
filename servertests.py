from container import *

cont1 = Container('52dfc8ea26abc1c6a23e57b413116f17799a861e1403db5aa4b7c2d6e572c52e0f9885d0fcc4ca5c3cb92d84280c1646ace0f99dbaafefa3c189eadf5ac9cd8f.7zPluricContainer')
print cont1.prettytext()
print "---------"
print cont1.message.text()
cont1.tofile()