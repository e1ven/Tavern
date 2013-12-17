import json
import pymongo
import time
from collections import OrderedDict
import sys
import libtavern

class TopicTool(object):

    """Break some of the common topic handling routines out into a tool, so
    that they can be cached.

    Shouldn't be instantiated directly.

    """

   # @libtavern.utils.memorise(ttl=libtavern.server.serversettings.settings['cache']['subjects-in-topic']['seconds'], maxsize=libtavern.server.serversettings.settings['cache']['subjects-in-topic']['size'])
    def messages(self, topic, maxposts, before=None):
        """Get all messages in a topic, no later than `before`"""
        if topic == 'all':
            sorttopic = {'envelope.local.sorttopic': {'$exists': False}}
        elif isinstance(topic, str):
            sorttopic = {'envelope.local.sorttopic': topic}
        elif isinstance(topic, list):
            for t in topic:
                topics.append(libtavern.server.sorttopic(t))
            sorttopic = {'envelope.local.sorttopic': {'$in': topics}}
        else:
            sorttopic = {}

        # Don't do this in the def, so that our cache is respected.
        if before is None:
            before = libtavern.utils.inttime()

        # Append our search topic query.
        subjects = []
        search = {'envelope.payload.class': 'message',
                  'envelope.payload.regarding': {'$exists': False},
                  'envelope.local.time_added': {'$lt': before}}
        search.update(sorttopic)
        for envelope in libtavern.server.db.unsafe.find('envelopes', search, limit=maxposts, sortkey='envelope.local.time_added', sortdirection='descending'):
            e = Envelope()
            e.loaddict(envelope)
            subjects.append(e)

        return subjects

   # @libtavern.utils.memorise(ttl=libtavern.server.serversettings.settings['cache']['subjects-in-topic']['seconds'], maxsize=libtavern.server.serversettings.settings['cache']['subjects-in-topic']['size'])
    def getbackdate(self, topic, maxposts, after):
        """Get the earliest dated message, before `after`"""
        sorttopic = libtavern.server.sorttopic(topic)
        subjects = []
        if topic != "all":
            for envelope in libtavern.server.db.unsafe.find('envelopes', {'envelope.local.sorttopic': sorttopic, 'envelope.payload.class': 'message', 'envelope.payload.regarding': {'$exists': False}, 'envelope.local.time_added': {'$gt': after}}, limit=maxposts + 1, sortkey='envelope.local.time_added', sortdirection='ascending'):
                subjects.append(envelope)
        else:
            for envelope in libtavern.server.db.unsafe.find('envelopes', {'envelope.payload.class': 'message', 'envelope.payload.regarding': {'$exists': False}, 'envelope.local.time_added': {'$gt': after}}, limit=maxposts + 1, sortkey='envelope.local.time_added', sortdirection='ascending'):
                subjects.append(envelope)

        # Adding 1 to maxposts above, because we're going to use this to get the 10 posts AFTER the date we return from this function.
        # This is also the reason why, if we don't have maxposts posts, we
        # subtract 1 below. This ensures that we get ALL the posts in the
        # range.
        if len(subjects) > 0:
            if len(subjects) <= maxposts:
                ret = subjects[-1]['envelope']['local']['time_added'] + 1
                print("ret")
            else:
                ret = subjects[-1]['envelope']['local']['time_added']
        else:
            ret = libtavern.utils.inttime()

        return ret

  #  @libtavern.utils.memorise(ttl=libtavern.server.serversettings.settings['cache']['subjects-in-topic']['seconds'], maxsize=libtavern.server.serversettings.settings['cache']['subjects-in-topic']['size'])
    def moreafter(self, before, topic, maxposts):
        sorttopic = libtavern.server.sorttopic(topic)
        if topic != "all":
            count = len(
                libtavern.server.db.unsafe.find('envelopes',
                                      {'envelope.local.sorttopic': sorttopic,
                                       'envelope.payload.class': 'message',
                                       'envelope.payload.regarding':
                                       {'$exists': False},
                                       'envelope.local.time_added': {'$lt': before}}))
        else:
            count = len(
                libtavern.server.db.unsafe.find('envelopes',
                                      {'envelope.payload.class': 'message',
                                       'envelope.payload.regarding':
                                       {'$exists': False},
                                       'envelope.local.time_added': {'$lt': before}}))
        return count

  #  @libtavern.utils.memorise(ttl=libtavern.server.serversettings.settings['cache']['toptopics']['seconds'], maxsize=libtavern.server.serversettings.settings['cache']['toptopics']['size'])
    def toptopics(self, limit=10, skip=0):
        toptopics = []
        for quicktopic in libtavern.server.db.unsafe.find('topiclist', skip=skip, sortkey='value', sortdirection='descending'):
            toptopics.append(quicktopic['_id'])
        return toptopics

  #  @libtavern.utils.memorise(ttl=libtavern.server.serversettings.settings['cache']['topiccount']['seconds'], maxsize=libtavern.server.serversettings.settings['cache']['topiccount']['size'])
    def topicCount(self, topic, after=0, before=None, toponly=True):

        # Don't do this in the def, so that our cache is respected.
        if before is None:
            before = libtavern.utils.inttime()

        sorttopic = libtavern.server.sorttopic(topic)
        if toponly:
            count = libtavern.server.db.unsafe.count(
                'envelopes',
                {'envelope.local.time_added': {'$lt': before},
                 'envelope.local.time_added': {'$gt': after},
                 'envelope.payload.regarding': {'$exists': False},
                 'envelope.local.sorttopic': sorttopic})
        else:
            count = libtavern.server.db.unsafe.count(
                'envelopes',
                {'envelope.local.time_added': {'$lt': before},
                 'envelope.local.time_added': {'$gt': after},
                 'envelope.local.sorttopic': sorttopic})
        return count

# Only create one, and re-use it.
topictool = TopicTool()