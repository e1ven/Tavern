import libtavern.baseobj
import libtavern.utils
import libtavern.envelope
import copy

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

    def __init2__(self,topic=None):
        """
        Create a Topic.
        Called by __init__() automatically.
        """

        if isinstance(topic,Topic):
            # If we receive a topic obj, absorb it.
            self.topics = copy.deepcopy(topic.topics)
            self.sorttopics = copy.deepcopy(topic.sorttopics)
            return

        # The list of all topics we received
        self.topics = []

        # The 'sorttopic' version, case-matched, etc.
        self.sorttopics = []

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
        self.sorttopics.append(self._sorttopic(topic))
        self.topics.append(topic)


    @property
    def name(self):
        """Name of the topic"""
        if not hasattr(self,'_nameoverride'):
            return "+".join(self.topics)
        else:
            return self._nameoverride

    @name.setter
    def name(self,value):
        """Sets the display name of the topic, without changing the underlying topiclist.
        Use only with Extreme caution."""
        self._nameoverride = value

    @property
    def sortname(self):
        """Name of the topic"""
        return "+".join(self.sorttopics)


    def _create_filter(self,before=None,after=None,include_replies=True):
        """Internal method to create the search obj used by the rest of the class."""

        # Create our search. First off, the obvious.
        self.search = {'envelope.payload.class': 'message'}

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
        :param float before: Find only messages before this timestamp
        :param float after: Find only messages after this timestamp
        :return array: List of messages
        """

        subjects = []
        self._create_filter(before=before,after=after,include_replies=include_replies)
        for envelope in self.server.db.unsafe.find('envelopes', self.search, limit=maxposts, sortkey='envelope.local.time_added', sortdirection='ascending'):
            e = libtavern.envelope.Envelope()
            e.loaddict(envelope)
            subjects.append(e)
        return subjects

    def count(self,before=None,after=None,include_replies=True):
        """Count the messages in the current topic.

        :param float before: Count only messages before this timestamp
        :param float after: Count only messages after this timestamp
        :param bool include_replies: Should replies be included, or only top-level messages.
        :return int: Number of messages.
        """

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

    def toptopics(self, limit=10, skip=0):
        """
        Returns a list of the Top topics on the server, as generated by TopicList.py
        :param (int) limit: The maximum number of topics to return.
        :param skip int: Skip N topics before returning. Used for pagination.
        :return:Array: A list of Topic objects.
        """

        toptopics = []
        for quicktopic in self.server.db.unsafe.find('topiclist', skip=skip, sortkey='value', sortdirection='descending',limit=limit):
            toptopics.append(libtavern.topic.Topic(topic=quicktopic['_id']))
        return toptopics
