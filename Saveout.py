#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta
from pymongo.code import Code
from Envelope import Envelope
from server import server
from collections import OrderedDict
import json
import os

class SaveOut(object):
    
    
    def writetopic(self,topic,since=0,limit=100,skip=0):
        #Write a topic out to .7z files
        
        e = Envelope()
        
        for envelope in server.mongos['default']['envelopes'].find({'envelope.stamps.time_added': {'$gt' : since },'envelope.payload.topictag' : topic },limit=limit,skip=skip,as_class=OrderedDict):
            envelope = server.formatEnvelope(envelope)
            envstr = json.dumps(envelope,separators=(',',':'))
            e.loadstring(envstr)
            
            topicdir = "TOPICS/Topic-" + topic
            
            # Make a dir if nec.
            if not os.path.isdir(topicdir):
                os.makedirs(topicdir)
                   
            if not os.path.exists(topicdir + "/" + e.payload.hash() + ".7zPluricEnvelope"):
                e.savefile(topicdir)
            
    def loaddir(self,directory):
        # Load in a directory full of archives.
        listing = os.listdir(directory)    
        e = Envelope()
        
        for infile in listing:
            e.loadfile(directory + "/" + infile)
            server.receiveEnvelope(e.text())

a = SaveOut()
#a.writetopic('sitecontent')  
a.loaddir('TOPICS/Topic-sitecontent')          
