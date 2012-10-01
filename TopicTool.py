import json
import pymongo
import Envelope
import time
from TavernCache import memorise
from server import server
from collections import OrderedDict
import sys

class TopicTool(object):
    """
    Break some of the common topic handling routines out into a tool, so that they can be cached.
    """

    def __init__(self,topic='all',maxposts=50):
        self.sorttopic = server.sorttopic(topic)
        self.topic = topic
        self.maxposts = maxposts

    @memorise(parent_keys=['sorttopic','maxposts'],ttl=server.ServerSettings['cache']['subjects-in-topic']['seconds'],maxsize=server.ServerSettings['cache']['subjects-in-topic']['size'])
    def messages(self,before,countonly=False):
        """
        Get all messages in a topic, no later than `before`
        """
        subjects = []
        if self.topic != "all":
            for envelope in server.mongos['unsafe']['envelopes'].find({'envelope.local.sorttopic' : self.sorttopic,'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}},limit=self.maxposts,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                subjects.append(envelope)
        else:
            for envelope in server.mongos['unsafe']['envelopes'].find({'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}},limit=self.maxposts,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                subjects.append(envelope)

        if countonly == True:
            print(len(subjects))
            return len(subjects)
        else:
            return subjects


    @memorise(parent_keys=['sorttopic','maxposts'],ttl=server.ServerSettings['cache']['subjects-in-topic']['seconds'],maxsize=server.ServerSettings['cache']['subjects-in-topic']['size'])
    def getbackdate(self,after,countonly=False):
        """
        Get the earliest dated message, before `after`
        """


        subjects = []
        if self.topic != "all":
            for envelope in server.mongos['unsafe']['envelopes'].find({'envelope.local.sorttopic' : self.sorttopic,'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$gt':after}},limit=self.maxposts +1 ,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.ASCENDING):
                subjects.append(envelope)
        else:
            for envelope in server.mongos['unsafe']['envelopes'].find({'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$gt':after}},limit=self.maxposts +1 ,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.ASCENDING):
                subjects.append(envelope)
        
        # Adding 1 to self.maxposts above, because we're going to use this to get the 10 posts AFTER the date we return from this function.
        # This is also the reason why, if we don't have maxposts posts, we subtract 1 below. This ensures that we get ALL the posts in the range.
        if len(subjects) > 0:
            if len (subjects) <= self.maxposts:
                ret = subjects[-1]['envelope']['local']['time_added'] +1
                print("ret")
            else:
                ret = subjects[-1]['envelope']['local']['time_added']
        else:
            ret = server.inttime()
        if countonly == True:
            return len(subjects) - 1
        else:   
            return ret




    @memorise(parent_keys=['sorttopic','maxposts'],ttl=server.ServerSettings['cache']['subjects-in-topic']['seconds'],maxsize=server.ServerSettings['cache']['subjects-in-topic']['size'])
    def moreafter(self,before):
        if self.topic != "all":
            count = server.mongos['unsafe']['envelopes'].find({'envelope.local.sorttopic' : self.sorttopic,'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}}).count()
        else:
            count = server.mongos['unsafe']['envelopes'].find({'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}}).count()
        return count

    @memorise(ttl=server.ServerSettings['cache']['toptopics']['seconds'],maxsize=server.ServerSettings['cache']['toptopics']['size'])
    def toptopics(self):
        toptopics = []
        for quicktopic in server.mongos['unsafe']['topiclist'].find(limit=14,as_class=OrderedDict).sort('value',-1):
            toptopics.append(quicktopic)
        return toptopics
