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
import bleach

import libtavern.serversettings
import libtavern.key
import libtavern.utils
import libtavern.embedis
import libtavern.uasparser
import libtavern.user
import libtavern.keygen
import libtavern.envelope

class FakeMongo(libtavern.baseobj.Baseobj):
    #TODO http://initd.org/psycopg/docs/pool.html ??
    def __init2__(self, host, port, name,connections):

        # Create a connection to Postgres.
        self.conn = psycopg2.connect(
            dbname=name,
            user=self.server.serversettings.settings['postgres']['default']['user'],
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


class MongoWrapper(libtavern.baseobj.Baseobj):

    def __init2__(self, host, port, name,connections,safe=True):
        if safe:
            # Slower, more reliable mongo connection.
            self.safeconn = pymongo.MongoClient(
                host,
                port,
                safe=True,
                journal=True,
                max_pool_size=connections)
            self.mongo = self.safeconn[name]
        else:
            # Create a fast, unsafe mongo connection. Writes might get lost.
            self.unsafeconn = pymongo.MongoClient(
                host,
                port,
                read_preference=pymongo.read_preferences.ReadPreference.SECONDARY_PREFERRED,
                max_pool_size=connections)
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
            res = self.mongo[collection].find(query, skip=skip, limit=limit, sort=[(sortkey, direction)])
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


class DBWrapper(libtavern.baseobj.Baseobj):

    def __init2__(self, name, dbtype, host, port,connections):

        if dbtype == "mongo":
            self.safe = MongoWrapper(
                safe=True,
                host=host,
                port=port,
                name=name,
                connections=connections,
                server=self.server)
            self.unsafe = MongoWrapper(
                safe=False,
                host=host,
                port=port,
                name=name,
                connections=connections,
                server=self.server)
        elif dbtype == "postgres":
            self.safe = FakeMongo(host=host, port=port, name=name,connections=connections,server=server)
            self.unsafe = FakeMongo(host=host, port=port, name=name,conections=connections,server=server)
        else:
            raise Exception('DBError', 'Invalid type of database')

class Server(libtavern.utils.instancer):

    # We want to share state across all Server instances.
    # This way we can create a new instance, anywhere, in any subclass, and
    # get the same settings/etc

    def __init__(self, slot='default'):
        """
        Create the basic structures of the Server (DB, logging, etc)
        Postpone most intensive activity (Keygen, Users, etc) until `.start()` is run
        """

        super().__init__(slot)

        # Don't run __init__ more than once, since we return the same one.
        if self.__dict__.get('set') is True:
            return
        else:
            self.set = True

        # Save our instance name
        self.slot = slot

        # Create a logger, so we can write to console/log/etc
        self.logger = logging.getLogger(slot)

        # Load in the most recent config file
        self.serversettings = libtavern.serversettings.ServerSettings(slot=slot)

        # Restore our logger level to the version in our conf file.
        self.logger.setLevel(self.serversettings.settings['loglevel'])

        # Define the console logging options.
        formatter = logging.Formatter('[%(levelname)s] %(message)s')

        self.consolehandler = logging.StreamHandler()
        self.consolehandler.setFormatter(formatter)
        self.logger.addHandler(self.consolehandler)

        self.handler_file = logging.FileHandler(filename=self.serversettings.settings['logfile'])
        self.handler_file.setFormatter(formatter)
        self.logger.addHandler(self.handler_file)

        # Create a queue of unused LockedKeys, since they are slow to gen-on-the-fly
        self.unusedkeycache = multiprocessing.Queue(
            self.serversettings.settings['KeyGenerator']['num_pregens'])

        # Create our Keygenerator
        self.keygen = libtavern.keygen.KeyGenerator(server=self)

        # Find the DB-info
        dbtype = self.serversettings.settings['DB']['default']['type']
        self.db = DBWrapper(
            name=self.serversettings.settings[dbtype]['default']['name'],
            dbtype=dbtype,
            host=self.serversettings.settings[dbtype]['default']['hostname'],
            port=self.serversettings.settings[dbtype]['default']['port'],
            connections=self.serversettings.settings[dbtype]['default']['connections'],
            server=self)


        dbtype = self.serversettings.settings['DB']['sessions']['type']
        self.sessions = DBWrapper(
            name=self.serversettings.settings[dbtype]['sessions']['name'],
            dbtype=dbtype,
            host=self.serversettings.settings[dbtype]['sessions']['hostname'],
            port=self.serversettings.settings[dbtype]['sessions']['port'],
            connections=self.serversettings.settings[dbtype]['sessions']['connections'],
            server=self)

        dbtype = self.serversettings.settings['DB']['binaries']['type']
        self.binaries = DBWrapper(
            name=self.serversettings.settings[dbtype]['binaries']['name'],
            dbtype=dbtype,
            host=self.serversettings.settings[dbtype]['binaries']['hostname'],
            port=self.serversettings.settings[dbtype]['binaries']['port'],
            connections=self.serversettings.settings[dbtype]['binaries']['connections'],
            server=self)

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

        # Get a list of all the valid web templates that can be used, to compare
        # against later on.
        self.availablethemes = []
        basethemedir = 'webtav/themes'
        for name in os.listdir(basethemedir):
            if os.path.isdir(os.path.join(basethemedir, name)):
                if name[:1] != ".":
                    self.availablethemes.append(name)

        self.serversettings.settings['static-revision'] = libtavern.utils.gettime(format='longstr')

        self.fortune = libtavern.utils.randomWords(fortunefile="datafiles/header-fortunes")
        self.wordlist = libtavern.utils.randomWords(fortunefile="datafiles/wordlist")


        self.logger.debug("Tavern Server (" + slot + ") is loaded at logging level : " +
              str(self.logger.getEffectiveLevel()))

    def start(self):
        """
        Stuff that should be done when the server is running as a process,
        not just imported as a obj.
        """

        self.external = libtavern.embedis.Embedis(server=self)
        self.logger.info("Loading Browser info")
        self.browserdetector = libtavern.uasparser.UASparser(server=self)
        
        # Start pregenerating random keys to assign out.
        self.keygen.start()


        # Create a Default acct.
        # All new users inherit settings from this user.

        if self.serversettings.settings['defaultuser']['pubkey'] is not None:
            self.defaultuser = libtavern.user.User()
            self.defaultuser.load_mongo_by_pubkey(self.serversettings.settings['defaultuser']['pubkey'])
            self.defaultuser.passkey = self.serversettings.settings['defaultuser']['passkey']
        else:
            self.logger.info("Generating Default User (This may take a moment) ")
            self.defaultuser = libtavern.user.User()
            self.defaultuser.ensure_keys(AllowGuestKey=False)
            self.defaultuser.save_mongo(overwriteguest=True)
            self.serversettings.settings['defaultuser']['pubkey'] = self.defaultuser.Keys['master'].pubkey
            self.serversettings.settings['defaultuser']['passkey'] =  self.defaultuser.passkey
            self.serversettings.saveconfig()

        # Create a Guest account.
        # This account controls settings for users who haven't created an acct yet.
        # It is separate from the Default user so that we can customize the settings for non-logged in users.

        if self.serversettings.settings['guestuser']['pubkey'] is not None:
            self.guestuser = libtavern.user.User()
            self.guestuser.load_mongo_by_pubkey(self.serversettings.settings['guestuser']['pubkey'])
            self.guestuser.passkey = self.serversettings.settings['guestuser']['passkey']
        else:
            self.logger.info("Generating Guest User (This may take a moment) ")
            self.guestuser = libtavern.user.User()
            self.guestuser.ensure_keys(AllowGuestKey=False)
            self.guestuser.save_mongo(overwriteguest=True)
            self.serversettings.settings['guestuser']['pubkey'] = self.guestuser.Keys['master'].pubkey
            self.serversettings.settings['guestuser']['passkey'] = self.guestuser.passkey
            self.serversettings.saveconfig()


        # Create a Server account.
        # This account is used to sign stamps and messages generated by this server.

        if self.serversettings.settings['serveruser']['pubkey'] is not None:
            self.serveruser = libtavern.user.User()
            self.serveruser.load_mongo_by_pubkey(self.serversettings.settings['serveruser']['pubkey'])
            self.serveruser.passkey = self.serversettings.settings['serveruser']['passkey']
        else:
            self.logger.info("Generating Internal Server User (This may take a moment) ")
            self.serveruser = libtavern.user.User()
            self.serveruser.ensure_keys(AllowGuestKey=False)
            self.serveruser.save_mongo()
            self.serversettings.settings['serveruser']['pubkey'] = self.serveruser.Keys['master'].pubkey
            self.serversettings.settings['serveruser']['passkey'] = self.serveruser.passkey
            self.serversettings.saveconfig()


        self.logger.info("Tavern Server is now running, using logging level : " +
              str(self.logger.getEffectiveLevel()) + ".  Enjoy!")

    def stop(self):
        """Stop all server procs."""
        self.logger.info("Tavern Server (" + self.slot + ") is stopping.")
        self.keygen.stop()

 #   @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['error_envelope']['seconds'], maxsize=defaultsettings.settings['cache']['error_envelope']['size'])
    def error_envelope(self, subject="Error", topic="sitecontent", body=None):

        if body is None:
            body = """
            Oh my, something seems to have happened that we weren't expecting.
            Hopefully this will get cleared up relatively quickly.
            If not, you might want to send a note to support@libtavern.is, with the URL, and notes on how you got here :/

            So sorry for the trouble.
            -The Barkeep
            """
        e = libtavern.envelope.Envelope(server=self)
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
            passkey=self.serveruser.passkey,
            keys=self.serveruser.Keys['master'],
            friendlyname=self.serversettings.settings['hostname'])
        e.flatten()
        e.munge()
        e.dict['envelope']['local']['time_added'] = 1297440000
        e.dict['envelope']['local'][
            'author_wordhash'] = "Automatically generated message"
        e.dict['envelope']['local']['sorttopic'] = "error"
        e.dict['envelope']['local']['payload_sha512'] = e.payload.hash()
        return e

    # Cache to failfast on receiving dups
#    @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['receiveEnvelope']['seconds'], maxsize=defaultsettings.settings['cache']['receiveEnvelope']['size'])
    def receive_envelope(self, env=None):
        """
        Receives an envelope, validates it, and saves it to the DB.
        :param Envelope env: The new Envelope object to receive and process
        :return: The URL of the newly submitted message.
        """
        if not env:
            raise Exception('receiveEnvelope MUST receive an envelope. Really! ;)')

        # Fill-out the message's local fields.
        env.munge()
        # Make sure the message is valid, meets our standards, and is good to
        # accept and save.
        if not env.validate():
            self.logger.info("Received an Envelope which does not validate-  " + env.payload.hash())
            self.logger.debug(env.text())
            return False

        existing = self.db.unsafe.find_one('envelopes', {'envelope.local.payload_sha512': env.dict['envelope']['local']['payload_sha512']})
        if existing is not None:
            self.logger.debug("We already have that msg.")
            return self.url_for(envelope=c)

        # Sign the message to saw we saw it.
        if self.serversettings.settings['mark-seen']:
            env.addStamp(
                stampclass='server',
                passkey=self.serveruser.passkey,
                keys=self.serveruser.Keys['master'],
                hostname=self.serversettings.settings['hostname'])

        # Store the time, in full UTC (with precision). This is used to skip pages in the viewer later.
        env.dict['envelope']['local']['time_added'] = libtavern.utils.gettime(format='longstr')

        # If this env references another env, add this id to the original.
        # This lets us easily retrieve all children later without a db search.
        if 'regarding' in env.dict['envelope']['payload']:
            original = libtavern.envelope.Envelope(server=self)
            if original.loadmongo(mongo_id=env.dict['envelope']['payload']['regarding']):
                self.logger.debug(" I am :: " + env.dict['envelope']['local']['payload_sha512'])
                self.logger.debug(" Adding a cite on my parent :: " + original.dict['envelope']['local']['payload_sha512'])

                original.add_cite(env.dict['envelope']['local']['payload_sha512'])
                env.add_ancestor(env.dict['envelope']['payload']['regarding'])

                # A message edit has two factors - Time, and Class
                if env.dict['envelope']['payload']['class'] == "messagerevision":
                    original.add_edit(env.dict['envelope']['local']['payload_sha512'])

        # Messages may not arrive in order. We might receive a reply before the original, or an edit before the post.
        # Check the existing messages to see if anyone referenced -us-.
        for citedict in self.db.unsafe.find('envelopes', {'envelope.payload.regarding': env.dict['envelope']['local']['payload_sha512']}):
            self.logger.debug(" I am :: " + env.dict['envelope']['local']['payload_sha512'])
            self.logger.debug(" Found pre-existing cite at :: " + citedict['envelope']['local']['payload_sha512'])

            # If we find one, handle it according to what class it is.
            if citedict['envelope']['payload']['class'] == 'message':
                citedme = libtavern.envelope.Envelope(server=self)
                citedme.loaddict(citedict)
                env.add_cite(citedme.dict['envelope']['local']['payload_sha512'])
                citedme.add_ancestor(env.dict['envelope']['local']['payload_sha512'])

            elif citedict['envelope']['payload']['class'] == 'messagerevision':
                env.add_edit(citedict['envelope']['local']['payload_sha512'])

            elif citedict['envelope']['payload']['class'] == 'messagerating':
                citedme = libtavern.envelope.Envelope(server=self)
                citedme.loaddict(citedict)
                citedme.dict['envelope']['local']['regardingAuthor'] = c.dict['envelope']['payload']['author']
                citedme.saveMongo()


        # Store our Envelope
        c.saveMongo()

        return self.url_for(envelope=c)

#    @libtavern.utils.memorise(ttl=defaultsettings.settings['cache']['formatText']['seconds'], maxsize=defaultsettings.settings['cache']['formatText']['size'])
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

                # Enable linebreaks, tables, and ````fenced code similar to GFM
                # Force all headers to be H3+ for SEO and styling.
                extensions=['nl2br',
                            'tables',
                            'fenced_code',
                            'headerid(level=3)'])

            # Setup which tags, attributes, etc are allowed for our formatter.
            # strip = False means that unknown tags should be encoded, such as &lt
            # strip_comments is at the very least because of SSI
            tags=['h1','h2','h3','p','br','strong','code','pre','ul','li','ol','a','em','table','thead','tr','th']
            attributes = {'a': ['href']}
            formatted = bleach.clean(text=formatted,tags=tags,attributes=attributes,styles=[],strip=False,strip_comments=True)

            # We want to linkify the text.
            def set_rel(attrs, new=False):
                """Set all links to have nofollow and noreferrer"""
                attrs['rel'] = 'nofollow noreferrer'
                return attrs

            formatted = bleach.linkify(text=formatted,skip_pre=True,parse_email=False,callbacks=[set_rel])

        return formatted

    def get_all_user_posts(self, pubkey, limit=1000):
        envelopes = []
        for envelope in self.db.safe.find('envelopes', {'envelope.local.author.pubkey': pubkey, 'envelope.payload.class': 'message'}, limit=limit, sortkey='envelope.local.time_added', sortdirection='descending'):
            messagetext = libtavern.utils.to_json(envelope)
            e = libtavern.envelope.Envelope(server=self)
            e.loadstring(messagetext)
            envelopes.append(e)
        return envelopes


    def getTopMessage(self, messageid):
        # Find the top level of a post that we currently have.

        env = libtavern.envelope.Envelope(server=self)
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

    def url_for(self,envelope=None,topic=None,user=None,pubkey=None,static=None,base=True,fqdn=False):
        """Return the canonical URL for a given token
        """
        if static:
            url = "/static/" + self.urlize(static)
        elif topic:
            if isinstance(topic,libtavern.topic.Topic):
                if len(topic.topics):
                    url = '/t/' + topic.sortname
                else:
                    url = '/all'
            elif isinstance(topic,str):
                topicobj = libtavern.topic.Topic(topic=topic)
                url = self.url_for(topic=topicobj)
            else:
                raise Exception("url_for must be given a Topic object or str")

        elif envelope:
            if isinstance(envelope, libtavern.envelope.Envelope):
                url =  "/t/" + envelope.dict['envelope']['local']['sorttopic'] + '/' + \
                             envelope.dict['envelope']['local']['short_subject'] + "/" + \
                             envelope.dict['envelope']['local']['payload_sha512']
            else:
                raise Exception("url_for must be given an Envelope object.")
        elif user:
            if isinstance(user,libtarvern.user.User):
                url =  "/u/" + ''.join(user.Keys['master'].pubkey.split())
            else:
                raise Exception("User must be user object")
        elif pubkey:
            if isinstance(pubkey,str):
                key = libtavern.key.Key(pub=pubkey)
                url =  "/u/" + ''.join(key.pubkey.split())
        elif base:
            url = "/"
        else:
            raise Exception('Nothing to get URL for.')

        if fqdn:
            url = self.serversettings.settings['webtav']['main_url'] + url

        # Don't allow a trailing slash. This is for resources, not dirs!
        url.rstrip('\\')

        return url