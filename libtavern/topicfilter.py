import json
import pymongo
import time
from collections import OrderedDict
import sys
import libtavern.baseobj
import libtavern.utils
import libtavern.envelope

class TopicFilter(libtavern.baseobj.Baseobj):

    """Break some of the common topic handling routines out into a tool, so
    that they can be cached.

    Shouldn't be instantiated directly.

    """

    def __init2__(self,topic=None,topics=None,unfiltered=False):
        """
        Create a TopicFilter. Called by __init__() automatically.
        :param str topic: The topic we should be filtering on.
        :param list topics: The topics we should filter on.
        :param bool unfiltered: Show messages from all topics
        :raise ('TopicError','Must Specify either a topic or a list of topics'):
        """

        # The list of all topics we received
        self.topics = []

        # The 'sorttopic' version, case-matched, etc.
        self.sorttopics = []

        if topics is not None:
            for tp in topics:
                st_ver = self.server.sorttopic(tp)
                self.sorttopics.append(st_ver)
                self.topics.append(tp)
        if topic is not None:
            st_ver = self.server.sorttopic(topic)
            self.topics.append(topic)
            self.sorttopics.append(st_ver)

        self.filtered = not unfiltered

        self.search = {}

    def set_topic(self,topic=None,topics=None,unfiltered=False):
        """Re-init the method.
        Used so that the response can have an empty filter, then config it as-needed.
        """
        self.__init2__(topic,topics,unfiltered)

    def _create_filter(self,before=None,after=None,include_replies=True):
        """Internal method to create the search obj used by the rest of the class."""

        # Create our search. First off, the obvious.
        self.search = {'envelope.payload.class': 'message'}

        if self.filtered:
            if len(self.sorttopics) > 0:
                self.search.update({'envelope.local.sorttopic': {'$in': self.sorttopics}})
        if before:
            self.search.update({'envelope.local.time_added': {'$lt': before}})
        if after:
            self.search.update({'envelope.local.time_added': {'$gt': after}})
        if not include_replies:
            self.search.update({'envelope.payload.regarding': {'$exists': False}})


    def messages(self,maxposts,before=None,after=None,include_replies=True):
        """Retrieve the messages in the specified topics.

        :param int maxposts: Max number of posts to return
        :param before: Find only messages before this timestamp
        :type before: integer or float
        :param after: Find only messages after this timestamp
        :type after: integer or float
        :return: List of messages
        :rtype: array
        """

        subjects = []
        self._create_filter(before=before,after=after,include_replies=include_replies)
        for envelope in self.server.db.unsafe.find('envelopes', self.search, limit=maxposts, sortkey='envelope.local.time_added', sortdirection='descending'):
            e = libtavern.envelope.Envelope()
            e.loaddict(envelope)
            subjects.append(e)
        return subjects

    def count(self,before=None,after=None,include_replies=True):

        self._create_filter(before=before,after=after,include_replies=include_replies)
        return self.server.db.unsafe.count('envelopes',self.search)


    def get_first_after(self, maxposts, after):
        """Get the earliest dated message, after `after`
        :param int maxposts: Max number of posts to return
        :param after: Find only messages after
        :type after: integer or float

        """
        sorttopic = self.server.sorttopic(topic)
        subjects = []
        if topic != "all":
            for envelope in self.server.db.unsafe.find('envelopes', {'envelope.local.sorttopic': sorttopic, 'envelope.payload.class': 'message', 'envelope.payload.regarding': {'$exists': False}, 'envelope.local.time_added': {'$gt': after}}, limit=maxposts + 1, sortkey='envelope.local.time_added', sortdirection='ascending'):
                subjects.append(envelope)
        else:
            for envelope in self.server.db.unsafe.find('envelopes', {'envelope.payload.class': 'message', 'envelope.payload.regarding': {'$exists': False}, 'envelope.local.time_added': {'$gt': after}}, limit=maxposts + 1, sortkey='envelope.local.time_added', sortdirection='ascending'):
                subjects.append(envelope)

        # Adding 1 to maxposts above, because we're going to use this to get the 10 posts AFTER the date we return from this function.
        # This is also the reason why, if we don't have maxposts posts, we
        # subtract 1 below. This ensures that we get ALL the posts in the
        # range.
        if len(subjects) > 0:
            if len(subjects) <= maxposts:
                ret = subjects[-1]['envelope']['local']['time_added'] + 1
            else:
                ret = subjects[-1]['envelope']['local']['time_added']
        else:
            ret = libtavern.utils.gettime(format='timestamp')

        return ret

    def moreafter(self, before, topic, maxposts):
        sorttopic = self.server.sorttopic(topic)
        if topic != "all":
            count = len(
                self.server.db.unsafe.find('envelopes',
                                      {'envelope.local.sorttopic': sorttopic,
                                       'envelope.payload.class': 'message',
                                       'envelope.payload.regarding':
                                       {'$exists': False},
                                       'envelope.local.time_added': {'$lt': before}}))
        else:
            count = len(
                self.server.db.unsafe.find('envelopes',
                                      {'envelope.payload.class': 'message',
                                       'envelope.payload.regarding':
                                       {'$exists': False},
                                       'envelope.local.time_added': {'$lt': before}}))
        return count

    def toptopics(self, limit=10, skip=0,counts=False):
        """
        Returns a tuple of (Topicname,messagecount)
        """
        toptopics = []
        for quicktopic in self.server.db.unsafe.find('topiclist', skip=skip, sortkey='value', sortdirection='descending'):
            if counts:
                toptopics.append(  (quicktopic['_id'],int(quicktopic['value'])) )
            else:
                toptopics.append(quicktopic['_id'])
        return toptopics