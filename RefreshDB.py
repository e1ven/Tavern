#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta
from pymongo.code import Code
from Envelope import Envelope
from server import server
from collections import OrderedDict
import json
import os

# e = Envelope()
# for envelope in server.mongos['default']['envelopes'].find({},as_class=OrderedDict):
#   envelope = server.formatEnvelope(envelope)
#   envelope['local'] = ''
#   envstr = json.dumps(envelope,separators=(',',':'))
#   e.loadstring(envstr)
            

#   # Make a dir if nec.
#   if not os.path.isdir('MSGDUMP'):
#      os.makedirs('MSGDUMP')
                   
#   if not os.path.exists('MSGDUMP'+ "/" + e.payload.hash() + ".7zTavernEnvelope"):
#       e.savefile('MSGDUMP')
            
listing = os.listdir('MSGDUMP')    
e = Envelope()

#Reload it all back in, so it gets processed        
for infile in listing:
  e.loadfile('MSGDUMP'+ "/" + infile)
  server.receiveEnvelope(e.text())
