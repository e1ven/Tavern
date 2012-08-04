import json
import pymongo
import Envelope
import time
from decorators import memorise
from server import server
from collections import OrderedDict

class TopicTool(object):
    """
    Break some of the common topic handling routines out into a tool, so that they can be cached.
    """

    def __init__(self,topic='all',maxposts=50):
        self.sorttopic = server.sorttopic(topic)
        self.topic = topic
        self.maxposts = maxposts

    @memorise(parent_keys=['sorttopic','maxposts'],ttl=server.ServerSettings['cache']['subjects-in-topic']['seconds'],maxsize=server.ServerSettings['cache']['subjects-in-topic']['size'])
    def messages(self,before=time.time()):
        subjects = []
        if self.topic != "all":
            for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : self.sorttopic,'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}},limit=self.maxposts,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                subjects.append(envelope)
        else:
            for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}},limit=self.maxposts,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                subjects.append(envelope)
        return subjects

    @memorise(parent_keys=['sorttopic','maxposts'],ttl=server.ServerSettings['cache']['subjects-in-topic']['seconds'],maxsize=server.ServerSettings['cache']['subjects-in-topic']['size'])
    def count(self,before=time.time()):
        if self.topic != "all":
            count = server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : self.sorttopic,'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}}).count()
        else:
            count = server.mongos['default']['envelopes'].find({'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False},'envelope.local.time_added':{'$lt':before}}).count()
        return count

    @memorise(ttl=server.ServerSettings['cache']['toptopics']['seconds'],maxsize=server.ServerSettings['cache']['toptopics']['size'])
    def toptopics(self):
        toptopics = []
        for quicktopic in server.mongos['default']['topiclist'].find(limit=14,as_class=OrderedDict).sort('value',-1):
            toptopics.append(quicktopic)
        return toptopics
