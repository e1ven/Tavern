
import json
import platform
import time
import collections
from collections import OrderedDict
import pymongo
import pymongo.read_preferences
from gridfs import GridFS
import sys
import markdown
import datetime
from libs import bbcodepy
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictConnection
import html
import queue
import multiprocessing
import logging
import os
import re
import libtavern

defaultsettings = libtavern.ServerSettings('cache.TavernSettings')


class FakeMongo():

    def __init__(self, host, port, name):

        # Create a connection to Postgres.
        self.conn = psycopg2.connect(
            dbname=name,
            user=server.serversettings.settings['postgres-user'],
            host=host,
            port=port,
            connection_factory=psycopg2.extras.RealDictConnection)
        self.conn.autocommit = True

    def find(self, collection,
             query={}, limit=-1, skip=0, sortkey=None, sortdirection="ascending"):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)
        cur.callproc('find', [collection, jsonquery, limit, skip])
        results = []

        # reconstruct the results
        for row in cur.fetchall():
            row = row['find']
            results.append(row)

        # Sort if necessary
        if sortdirection not in ['ascending', 'descending']:
            raise Exception(
                'Sort direction must be either ascending or descending')

        if sortkey is not None:
            arglist = sortkey.split(".")
            results = sorted(results, key=lambda e:
                             functools.reduce(lambda m, k: m[k], arglist, e))

        if sortdirection == "descending":
            results.reverse()

        return results

    def find_one(self, collection,
                 query={}, limit=-1, skip=0, sortkey=None, sortdirection="ascending"):
        result = self.find(
            collection=collection,
            query=query,
            limit=1,
            skip=skip,
            sortkey=sortkey,
            sortdirection=sortdirection)
        if len(result) == 0:
            return None
        else:
            return result[0]

    def save(self, collection, query):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)
        result = cur.callproc('save', [collection, jsonquery])
        return result

    # TODO - Change insert to not insert dups. Probably in mongolike.
    def insert(self, collection, query):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)
        result = cur.callproc('save', [collection, jsonquery])
        return result

    def count(self, collection, query={}):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)

        cur.callproc('find', [collection, jsonquery])
        results = []

        return cur.rowcount

    def drop_collection(self, collection):
        cur = self.conn.cursor()
        cur.callproc('drop_collection', [collection])

    def map_reduce(self, collection, map, reduce, out):
        cur = self.conn.cursor()
        query = {
            'mapreduce': collection,
            'map': map,
            'reduce': reduce,
            'out': out
        }
        jsonquery = json.dumps(query)
        cur.callproc('runcommand', [jsonquery])

        # Export out results.
        self.drop_collection(out)
        results = []
        rows = cur.fetchone()['runcommand']
        for row in rows:
            self.insert(out, row)

    def ensure_index(self, collection, index):
        # TODO - add logic to detect existing idex, and not try to re-create.
        cur = self.conn.cursor()
        cursor.execute(
            'CREATE INDEX idx_' +
            collection +
            ' ON col_' +
            collection +
            "(find_in_obj('data','" +
            index +
            "'));")
        cursor.execute()


class MongoWrapper():

    def __init__(self, host, port, name, safe=True):

        if safe:
            # Slower, more reliable mongo connection.
            self.safeconn = pymongo.MongoClient(
                host,
                port,
                safe=True,
                journal=True,
                max_pool_size=defaultsettings.settings['mongo-connections'])
            self.mongo = self.safeconn[name]
        else:
            # Create a fast, unsafe mongo connection. Writes might get lost.
            self.unsafeconn = pymongo.MongoClient(
                host,
                port,
                read_preference=pymongo.read_preferences.ReadPreference.SECONDARY_PREFERRED,
                max_pool_size=defaultsettings.settings['mongo-connections'])
            self.mongo = self.unsafeconn[name]

    def drop_collection(self, collection):
        self.mongo.drop_collection(collection)

    def find(self, collection,
             query={}, limit=0, skip=0, sortkey=None, sortdirection="ascending"):

        if sortdirection not in ['ascending', 'descending']:
            raise Exception(
                'Sort direction must be either ascending or descending')

        if sortkey is not None:
            if sortdirection == "ascending":
                direction = pymongo.ASCENDING
            else:
                direction = pymongo.DESCENDING
            res = self.mongo[collection].find(
                query, skip=skip, limit=limit, sort=[(sortkey, direction)])
        else:
            res = self.mongo[collection].find(query, skip=skip, limit=limit)

        results = []

        for row in res:
            results.append(row)

        return results

    def find_one(self, collection,
                 query={}, skip=0, sortkey=None, sortdirection="ascending"):

        if sortdirection not in ['ascending', 'descending']:
            raise Exception(
                'Sort direction must be either ascending or descending')

        if sortkey is not None:
            if sortdirection == "ascending":
                direction = pymongo.ASCENDING
            else:
                direction = pymongo.DESCENDING
            res = self.mongo[collection].find_one(
                query, skip=skip, sort=[(sortkey, direction)])

        else:
            res = self.mongo[collection].find_one(query, skip=skip)
        return res

    def save(self, collection, query):
        return self.mongo[collection].save(query)

    def insert(self, collection, query):
        return self.mongo[collection].insert(query)

    def map_reduce(self, collection, map, reduce, out):
        return (
            self.mongo[collection].map_reduce(map=map, reduce=reduce, out=out)
        )

    def count(self, collection, query={}):
        return self.mongo[collection].find(query).count()

    def ensure_index(self, collection, index):
        return self.mongo[collection].create_index(index)


class DBWrapper():

    def __init__(self, name, dbtype=None, host=None, port=None):

        if dbtype == "mongo":
            if host is None:
                host = server.serversettings.settings['mongo-hostname']
            if port is None:
                port = server.serversettings.settings['mongo-port']

            self.safe = MongoWrapper(
                safe=True,
                host=host,
                port=port,
                name=name)
            self.unsafe = MongoWrapper(
                safe=False,
                host=host,
                port=port,
                name=name)
        elif dbtype == "postgres":
            if host is None:
                host = server.serversettings.settings['postgres-hostname']
            if port is None:
                port = server.serversettings.settings['postgres-port']

            self.safe = FakeMongo(host=host, port=port, name=name)
            self.unsafe = FakeMongo(host=host, port=port, name=name)

        else:
            raise Exception('DBError', 'Invalid type of database')


def print_timing(func):
    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        print((t2 - t1) * 1000.0)
        return res
    return wrapper


class Server(libtavern.utils.instancer):

    # We want to share state across all Server instances.
    # This way we can create a new instance, anywhere, in any subclass, and
    # get the same settings/etc

    class FancyDateTimeDelta(object):

        """Format the date / time difference between the supplied date and the
        current time using approximate measurement boundaries."""

        def __init__(self, dt):
            now = datetime.datetime.now()
            delta = now - dt
            self.year = round(delta.days / 365)
            self.month = round(delta.days / 30 - (12 * self.year))
            if self.year > 0:
                self.day = 0
            else:
                self.day = delta.days % 30
            self.hour = round(delta.seconds / 3600)
            self.minute = round(delta.seconds / 60 - (60 * self.hour))
            self.second = delta.seconds - (self.hour * 3600) - \
                                          (60 * self.minute)
            self.millisecond = delta.microseconds / 1000

        def format(self):
            # Round down. People don't want the exact time.
            # For exact time, reverse array.
            fmt = ""
            for period in ['millisecond', 'second', 'minute', 'hour', 'day', 'month', 'year']:
                value = getattr(self, period)
                if value:
                    if value > 1:
                        period += "s"

                    fmt = str(value) + " " + period
            return fmt + " ago"

    def getnextint(self, queuename, forcewrite=False):
        if not 'queues' in self.serversettings.settings:
            self.serversettings.settings['queues'] = {}

        if not queuename in self.serversettings.settings['queues']:
            self.serversettings.settings['queues'][queuename] = 0

        self.serversettings.settings['queues'][queuename] += 1

        if forcewrite:
            self.serversettings.saveconfig()

        return self.serversettings.settings['queues'][queuename]

    def __init__(self, settingsfile=None, workingdir=None, slot='default'):

        super().__init__(slot)

        # Don't run this more than once.
        if self.__dict__.get('set') is True:
            return
        else:
            self.set = True

        self.logger = logging.getLogger('Tavern')

        # Should the server run in debug mode
        self.debug = False

        self.serversettings = libtavern.ServerSettings(settingsfile)
        if self.serversettings.updateconfig():
            self.serversettings.saveconfig()

        if not 'pubkey' in self.serversettings.settings or not 'privkey' in self.serversettings.settings:
            # Generate New config
            self.logger.info("Generating new Config")
            self.ServerKeys = libtavern.Key()
            self.ServerKeys.generate()

            # We can't encrypt this.. We'd need to store the key here on the machine...
            # If you're worried about it, encrypt the disk, or use a loopback.
            self.serversettings.settings['pubkey'] = self.ServerKeys.pubkey
            self.serversettings.settings['privkey'] = self.ServerKeys.privkey

            self.serversettings.updateconfig()
            self.serversettings.saveconfig()

        self.mc = OrderedDict
        self.unusedkeycache = multiprocessing.Queue(
            self.serversettings.settings['KeyGenerator']['num_pregens'])
        # Break out the settings into it's own file, so we can include it without including all of server
        # This does cause a few shenanigans while loading here, but hopefully
        # it's minimal

        self.ServerKeys = libtavern.Key(pub=self.serversettings.settings['pubkey'],
                              priv=self.serversettings.settings['privkey'])

        self.db = DBWrapper(
            name=self.serversettings.settings['dbname'],
            dbtype=self.serversettings.settings['dbtype'],
            host=self.serversettings.settings['mongo-hostname'],
            port=self.serversettings.settings['mongo-port'])
        self.sessions = DBWrapper(
            name=self.serversettings.settings['sessions-db-name'],
            dbtype=self.serversettings.settings['dbtype'],
            host=self.serversettings.settings['sessions-db-hostname'],
            port=self.serversettings.settings['sessions-db-port'])
        self.binaries = DBWrapper(
            name=self.serversettings.settings['bin-mongo-db'],
            dbtype='mongo',
            host=self.serversettings.settings['bin-mongo-hostname'],
            port=self.serversettings.settings['bin-mongo-port'])
        self.bin_GridFS = GridFS(self.binaries.unsafe.mongo)

        # Ensure we have Proper indexes.
        self.db.safe.ensure_index('envelope', 'envelope.local.time_added')
        self.db.safe.ensure_index('envelope', 'envelope.local.sorttopic')
        self.db.safe.ensure_index('envelope', 'envelope.local.payload_sha512')
        self.db.safe.ensure_index('envelope', 'envelope.payload.class')
        self.db.safe.ensure_index('envelope', 'envelope.payload.regarding')
        self.db.safe.ensure_index(
            'envelope',
            'envelope.payload.binaries.sha_512')
        self.db.safe.ensure_index('envelope', 'envelope.local.payload_sha512')
        self.db.safe.ensure_index('envelope', 'envelope.payload.author.pubkey')
        self.db.safe.ensure_index('envelope', 'envelope.payload.author.pubkey')
        self.db.safe.ensure_index('envelope', 'usertrusts.asking')
        self.db.safe.ensure_index('envelope', 'incomingtrust')

        self.binaries.safe.ensure_index('fs.files', 'filename')
        self.binaries.safe.ensure_index('fs.files', 'uploadDate')
        self.binaries.safe.ensure_index('fs.files', '_id')
        self.binaries.safe.ensure_index('fs.files', 'uploadDate')

        # Get a list of all the valid templates that can be used, to compare
        # against later on.
        self.availablethemes = []
        for name in os.listdir('themes'):
            if os.path.isdir(os.path.join('themes', name)):
                if name[:1] != ".":
                    self.availablethemes.append(name)

        self.serversettings.settings['static-revision'] = int(time.time())

        self.fortune = libtavern.utils.randomWords(fortunefile="data/fortunes")
        self.wordlist = libtavern.utils.randomWords(fortunefile="data/wordlist")

        # Define out logging options.
        formatter = logging.Formatter('[%(levelname)s] %(message)s')
        self.consolehandler = logging.StreamHandler()
        self.consolehandler.setFormatter(formatter)
        self.handler_file = logging.FileHandler(
            filename=self.serversettings.settings['logfile'])
        self.handler_file.setFormatter(formatter)

        self.logger.setLevel(self.serversettings.settings['loglevel'])
        level = self.serversettings.settings['loglevel']

        # Cache our JS, so we can include it later.
        file = open("static/scripts/instance.min.js")
        self.logger.info("Cached JS")
        libtavern.utils.TavernCache.cache['instance.js'] = file.read()
        file.close()
        self.guestacct = None

    def start(self):
        """Stuff that should be done when the server is running as a process,
        not just imported as a obj."""
        self.external = libtavern.Embedis()
        self.logger.info("Loading Browser info")
        self.browserdetector = libtavern.UASparser()

        # Start actually logging to file or console
        if self.debug:
            self.logger.setLevel("DEBUG")
            self.logger.addHandler(self.consolehandler)
      #      logging.getLogger('gnupg').setLevel("DEBUG")
            logging.getLogger('gnupg').addHandler(self.consolehandler)

        self.logger.addHandler(self.handler_file)

        print("Logging Server started at level: " +
              str(self.logger.getEffectiveLevel()))


        if not 'guestacct' in self.serversettings.settings:
            self.logger.info("Generating a Guest user acct.")
            self.guestacct = libtavern.User()
            self.guestacct.generate(AllowGuestKey=False)
            self.serversettings.settings['guestacct'] = {}
            self.serversettings.settings[
                'guestacct'][
                'pubkey'] = self.guestacct.Keys[
                'master'].pubkey
            self.serversettings.saveconfig()
            self.guestacct.savemongo()
        else:
            self.logger.info("Loading the Guest user acct.")
            self.guestacct = libtavern.User()
            self.guestacct.load_mongo_by_pubkey(
                self.serversettings.settings['guestacct']['pubkey'])

    def stop(self):
        """Stop all server procs."""
        self.logger.info("Shutting down Server instance")

    def prettytext(self):
        newstr = json.dumps(
            self.serversettings.settings, indent=2, separators=(', ', ': '))
        return newstr

    @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['sorttopic']['seconds'], maxsize=defaultsettings.settings['cache']['sorttopic']['size'])
    def sorttopic(self, topic):
        if topic is not None:
            topic = topic.lower()
            topic = self.urlize(topic)
        else:
            topic = None
        return topic

    @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['error_envelope']['seconds'], maxsize=defaultsettings.settings['cache']['error_envelope']['size'])
    def error_envelope(self, subject="Error", topic="sitecontent", body=None):

        if body is None:
            body = """
            Oh my, something seems to have happened that we weren't expecting.
            Hopefully this will get cleared up relatively quickly.
            If not, you might want to send a note to support@libtavern.is, with the URL, and notes on how you got here :/

            So sorry for the trouble.
            -The Barkeep
            """
        e = Envelope()
        e.dict['envelope']['payload'] = OrderedDict()
        e.dict['envelope']['payload']['subject'] = subject
        e.dict['envelope']['payload']['topic'] = topic
        e.dict['envelope']['payload']['formatting'] = "markdown"
        e.dict['envelope']['payload']['class'] = "message"
        e.dict['envelope']['payload'][
            'body'] = body
        e.dict['envelope']['payload']['author'] = OrderedDict()
        e.dict['envelope']['payload']['author']['pubkey'] = "1234"
        e.dict['envelope']['payload']['author']['friendlyname'] = "ERROR!"
        e.dict['envelope']['payload']['author']['useragent'] = "Error Agent"
        e.dict['envelope']['payload']['author']['friendlyname'] = "Error"
        e.addStamp(
            stampclass='author',
            keys=self.ServerKeys,
            friendlyname=defaultsettings.settings['hostname'])
        e.flatten()
        e.munge()
        e.dict['envelope']['local']['time_added'] = 1297396876
        e.dict['envelope']['local'][
            'author_wordhash'] = "Automatically generated message"
        e.dict['envelope']['local']['sorttopic'] = "error"
        e.dict['envelope']['local']['payload_sha512'] = e.payload.hash()
        return e

    # Cache to failfast on receiving dups
    @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['receiveEnvelope']['seconds'], maxsize=defaultsettings.settings['cache']['receiveEnvelope']['size'])
    def receiveEnvelope(self, envstr=None, env=None):
        """Receive an envelope for processing in the server.

        Can take either a string, or an envelope obj.

        """
        if envstr is None and env is None:
            raise Exception(
                'receiveEnvelope MUST receive an envelope. Really! ;)')

        if env is not None:
            # If we get an envelope, flatten it - The caller may not have.
            c = env.flatten()
        else:
            c = Envelope()
            c.loadstring(importstring=envstr)

        # Fill-out the message's local fields.
        c.munge()
        # Make sure the message is valid, meets our standards, and is good to
        # accept and save.
        if not c.validate():
            self.logger.info(
                "Received an Envelope which does not validate-  " + c.payload.hash())
            self.logger.debug(c.text())
            return False

        utctime = time.time()

        existing = self.db.unsafe.find_one(
            'envelopes', {'envelope.local.payload_sha512': c.dict['envelope']['local']['payload_sha512']})

        if existing is not None:
            self.logger.debug("We already have that msg.")
            return c.dict['envelope']['local']['payload_sha512']

        # Sign the message to saw we saw it.
        if self.serversettings.settings['mark-seen']:
            c.addStamp(
                stampclass='server',
                keys=self.ServerKeys,
                hostname=defaultsettings.settings['hostname'])

        # Store the time, in full UTC (with precision). This is used to skip
        # pages in the viewer later.
        c.dict['envelope']['local']['time_added'] = utctime

        if c.dict['envelope']['payload']['class'] == "message":

            # If the message referenes anyone, mark the original, for ease of finding it later.
            # Do this in the 'local' block, so we don't waste bits passing this on to others.
            # Partners can calculate this when they receive it.

            if 'regarding' in c.dict['envelope']['payload']:
                repliedTo = Envelope()
                if repliedTo.loadmongo(mongo_id=c.dict['envelope']['payload']['regarding']):
                    self.logger.debug(
                        " I am :: " + c.dict['envelope']['local']['payload_sha512'])
                    self.logger.debug(
                        " Adding a cite on my parent :: " +
                        repliedTo.dict[
                            'envelope'][
                            'local'][
                            'payload_sha512'])
                    repliedTo.addcite(
                        c.dict[
                            'envelope'][
                            'local'][
                            'payload_sha512'])
                    c.addAncestor(c.dict['envelope']['payload']['regarding'])

            print("id is :" + c.dict['envelope']['local']['payload_sha512'])

            # It could also be that this message is cited BY others we already have!
            # Sometimes we received them out of order. Better check.
            for citedict in self.db.unsafe.find('envelopes', {'envelope.payload.regarding': c.dict['envelope']['local']['payload_sha512']}):
                self.logger.debug('found existing cite, bad order. ')
                self.logger.debug(
                    " I am :: " + c.dict['envelope']['local']['payload_sha512'])
                self.logger.debug(" Found pre-existing cite at :: " +
                                  citedict['envelope']['local']['payload_sha512'])

                # If it's a message, write that in the reply, and in me.
                if citedict['envelope']['payload']['class'] == 'message':
                    citedme = Envelope()
                    citedme.loaddict(citedict)
                    c.addcite(
                        citedme.dict[
                            'envelope'][
                            'local'][
                            'payload_sha512'])
                    citedme.addAncestor(
                        c.dict[
                            'envelope'][
                            'local'][
                            'payload_sha512'])
                    citedme.saveMongo()

                # If it's an edit, write that in me.
                elif citedict['envelope']['payload']['class'] == 'messagerevision':
                    c.addEdit(citedict['envelope']['local']['payload_sha512'])

                elif citedict['envelope']['payload']['class'] == 'messagerating':
                    citedme = Envelope()
                    citedme.loaddict(citedict)
                    citedme.dict[
                        'envelope'][
                        'local'][
                        'regardingAuthor'] = c.dict[
                        'envelope'][
                        'payload'][
                        'author']
                    citedme.saveMongo()

        elif c.dict['envelope']['payload']['class'] == "messagerating":
            # If this is a rating, cache the AUTHOR of the rated message.
            regardingPost = self.db.unsafe.find_one(
                'envelopes',
                {'envelope.local.payload_sha512': c.dict['envelope']['payload']['regarding']})
            if regardingPost is not None:
                c.dict[
                    'envelope'][
                    'local'][
                    'regardingAuthor'] = regardingPost[
                    'envelope'][
                    'payload'][
                    'author']

        elif c.dict['envelope']['payload']['class'] == "messagerevision":
            # This is an edit to an existing message.

            regardingPost = self.db.unsafe.find_one(
                'envelopes',
                {'envelope.local.payload_sha512': c.dict['envelope']['payload']['regarding']})
            if regardingPost is not None:
                if 'priority' in c.dict['envelope']['payload']:
                    c.dict[
                        'envelope'][
                        'local'][
                        'priority'] = c.dict[
                        'envelope'][
                        'payload'][
                        'priority']
                else:
                    c.dict['envelope']['local']['priority'] = 0

                # Store this edit.
                # Save this message out to mongo, so we can then retrieve it in
                # addEdit().
                c.saveMongo()

                # Modify the original message.
                r = Envelope()
                r.loaddict(regardingPost)
                r.addEdit(c.dict['envelope']['local']['payload_sha512'])

                # Ensure we have the freshest version in memory.
                c.reloadmongo()
            else:
                self.logger.debug("Received an edit without the original")

        # Store our Envelope
        c.saveMongo()

        return c.dict['envelope']['local']['payload_sha512']

    @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['formatText']['seconds'], maxsize=defaultsettings.settings['cache']['formatText']['size'])
    def formatText(self, text=None, formatting='markdown'):

        # # Run the text through Tornado's escape to ensure you're not a badguy.
        # text = tornado.escape.xhtml_escape(text)
        if formatting == 'bbcode':
            formatted = bbcodepy.Parser().to_html(text)
        elif formatting == "plaintext":
            formatted = "<pre>" + text + "</pre>"
        else:
            # If we don't know, you get Markdown
            formatted = markdown.markdown(
                text,
                output_format="html5",
                safe_mode='escape',
                enable_attributes=False,
                extensions=['nl2br',
                            'footnotes',
                            'tables',
                            'headerid(level=3)'])
            # We can't use tornado.escape.linkify to linkify, since it ALSO
            # escapes everything.
            formatted = self.autolink(formatted)

        return formatted

    @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['getUsersPosts']['seconds'], maxsize=defaultsettings.settings['cache']['getUsersPosts']['size'])
    def getUsersPosts(self, pubkey, limit=1000):
        envelopes = []
        for envelope in self.db.safe.find('envelopes', {'envelope.local.author.pubkey': pubkey, 'envelope.payload.class': 'message'}, limit=limit, sortkey='envelope.local.time_added', sortdirection='descending'):
            messagetext = json.dumps(envelope, separators=(',', ':'))
            e = Envelope()
            e.loadstring(messagetext)
            envelopes.append(e)
        return envelopes

    def getOriginalMessage(self, messageid):

        env = Envelope()
        # First, pull the referenced message.
        if env.loadmongo(mongo_id=messageid):
            if env.dict['envelope']['payload']['class'] == 'message':
                return env.dict['envelope']['local']['payload_sha512']
            else:
                return env.dict['envelope']['payload']['regarding']

        return None

    def getTopMessage(self, messageid):
        # Find the top level of a post that we currently have.

        env = Envelope()
        # First, pull the referenced message.
        if env.loadmongo(mongo_id=messageid):
            # If we have no references, congrats, we're the top.
            if not 'regarding' in env.dict['envelope']['payload']:
                return env.dict['envelope']['local']['payload_sha512']
            if env.dict['envelope']['payload']['regarding'] is None:
                return env.dict['envelope']['local']['payload_sha512']
            # If we're here, it means we have a parent.
            # Recurse upstream
            result = self.getTopMessage(
                env.dict['envelope']['payload']['regarding'])

            # Don't blindly return it, since it might be None in broken chains.
            # In that case, return yourself.
            if result is not None:
                return result
            else:
                return env.dict['envelope']['local']['payload_sha512']
        else:
            return None

    def urlize(self, url):
        # I do NOT want to urlencode this, because that encodes the unicode characters.
        # Browsers are perfectly capable of handling these!
        url = re.sub('[/? ]', '-', url)
        url = re.sub(r'[^\w-]', '', url)
        return url

    # Autolink from http://greaterdebater.com/blog/gabe/post/4
    def autolink(self, html):
        # match all the urls
        # this returns a tuple with two groups
        # if the url is part of an existing link, the second element
        # in the tuple will be "> or </a>
        # if not, the second element will be an empty string
        urlre = re.compile(
            "(\(?https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])(\">|</a>)?")
        urls = urlre.findall(html)
        clean_urls = []

        # remove the duplicate matches
        # and replace urls with a link
        for url in urls:
            # ignore urls that are part of a link already
            if url[1]:
                continue
            c_url = url[0]
            # ignore parens if they enclose the entire url
            if c_url[0] == '(' and c_url[-1] == ')':
                c_url = c_url[1:-1]

            if c_url in clean_urls:
                continue  # We've already linked this url

            clean_urls.append(c_url)
            # substitute only where the url is not already part of a
            # link element.
            html = re.sub("(?<!(=\"|\">))" + re.escape(c_url),
                          "<a rel=\"noreferrer nofollow\" href=\"" +
                          c_url + "\">" + c_url + "</a>",
                          html)
        return html