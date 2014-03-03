import libtavern.baseobj
import libtavern.utils
import libtavern.envelope

def sorttopic(topic):
    if topic is not None:
        topic = Topic(topic)
        return topic.sortname
    else:
        topic = None
    return topic

class Topic(libtavern.baseobj.Baseobj):
    """
    A Topic is a collection of messages with a common subject.
    """

    def __init2__(self,topic=None,topics=None,unfiltered=None):
        """
        Create a Topic.
        Called by __init__() automatically.
        """

        # The list of all topics we received
        self.topics = []

        # The 'sorttopic' version, case-matched, etc.
        self.sorttopics = []

        if unfiltered is not None:
            self.filtered = not unfiltered

        if topics is not None:
            for tp in topics:
                self.add(tp)

        if topic is not None:
            self.add(topic)

        self.search = {}

    def _sorttopic(self,topic):
        if topic is not None:
            topic = topic.lower()
            topic = self.server.urlize(topic)
            return topic
        else:
            return None

    def add(self,topic):
        """Add a topic"""
        st = self._sorttopic(topic)
        self.sorttopics.append(st)
        self.topics.append(topic)
        self.filtered = True


    @property
    def name(self):
        """Name of the topic"""
        return "+".join(self.topics)

    @property
    def sortname(self):
        """Name of the topic"""
        return "+".join(self.sorttopics)


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


    def messages(self,maxposts=100,before=None,after=None,include_replies=True):
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
        for envelope in self.server.db.unsafe.find('envelopes', self.search, limit=maxposts, sortkey='envelope.local.time_added', sortdirection='ascending'):
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
        sorttopic = self._sorttopic(topic)
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
        sorttopic = self._sorttopic(topic)
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
        for quicktopic in self.server.db.unsafe.find('topiclist', skip=skip, sortkey='value', sortdirection='descending',limit=limit):
            toptopics.append(libtavern.topic.Topic(topic=quicktopic['_id']))
        return toptopics
