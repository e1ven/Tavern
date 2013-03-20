import json
import imghdr
import platform
import time
from keys import *
import Image
import collections
from collections import OrderedDict
import pymongo
import pymongo.read_preferences
from gridfs import GridFS
import gridfs
from Envelope import Envelope
import sys
import markdown
import datetime
import bbcodepy
from bs4 import BeautifulSoup
import magic
try:
    from hashlib import md5 as md5_func
except ImportError:
    from md5 import new as md5_func
import psycopg2
from psycopg2.extras import RealDictConnection
from ServerSettings import serversettings
import TavernUtils
from TavernUtils import memorise


class FakeMongo():
    def __init__(self):

        # Create a connection to Postgres.
        self.conn = psycopg2.connect("dbname=" + serversettings.settings['dbname'] + " user=e1ven", connection_factory=psycopg2.extras.RealDictConnection)
        self.conn.autocommit = True

    def find(self, collection, query={}, limit=-1, skip=0, sortkey=None, sortdirection="ascending"):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)

        cur.callproc('find', [collection, jsonquery, limit, skip])
        results = []

        for row in cur.fetchall():
            results.append(json.loads(json.loads(row['find'], object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict), object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict))

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

    def find_one(self, collection, query={}):
        cur = self.conn.cursor()

        jsonquery = json.dumps(query)
        cur.callproc('find', [collection, jsonquery])
        res = cur.fetchone()

        if res is None:
            return None
        else:
            # strip out the extraneous data the server includes.
            dictres = json.loads(json.loads(res['find'], object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict), object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)

        return dictres

    def save(self, collection, query):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)
        result = cur.callproc('save', [collection, jsonquery])
        print("runing FakeMongo Save()")
        return result

    # TODO - Change insert to not insert dups. Probably in mongolike.
    def insert(self, collection, query):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)
        result = cur.callproc('save', [collection, jsonquery])
        print("runing FakeMongo insert()")

        return result

    def count(self,collection,query={}):
        cur = self.conn.cursor()
        jsonquery = json.dumps(query)

        cur.callproc('find', [collection, jsonquery])
        results = []

        return cur.rowcount

class MongoWrapper():
    def __init__(self, safe=True):

        if safe == True:
            # Slower, more reliable mongo connection.
            self.safeconn = pymongo.MongoClient(serversettings.settings['mongo-hostname'], serversettings.settings['mongo-port'], safe=True, journal=True, max_pool_size=serversettings.settings['mongo-connections'])
            self.mongo = self.safeconn[serversettings.settings['dbname']]
        else:
            # Create a fast, unsafe mongo connection. Writes might get lost.
            self.unsafeconn = pymongo.MongoClient(serversettings.settings['mongo-hostname'], serversettings.settings['mongo-port'], read_preference=pymongo.read_preferences.ReadPreference.SECONDARY_PREFERRED, max_pool_size=serversettings.settings['mongo-connections'])
            self.mongo = self.unsafeconn[
                serversettings.settings['dbname']]

    def find(self, collection, query={}, limit=0, skip=0, sortkey=None, sortdirection="ascending"):

        if sortdirection not in ['ascending', 'descending']:
            raise Exception(
                'Sort direction must be either ascending or descending')

        if sortkey is not None:
            if sortdirection == "ascending":
                direction = pymongo.ASCENDING
            else:
                direction = pymongo.DESCENDING
            res = self.mongo[collection].find(
                query, skip=skip, limit=limit).sort(sortkey, direction)
        else:
            res = self.mongo[collection].find(query, skip=skip, limit=limit)

        results = []

        for row in res:
            results.append(row)

        return results

    def find_one(self, collection, query={}):
        return self.mongo[collection].find_one(query)

    def save(self, collection, query):
        return self.mongo[collection].save(query)

    def insert(self, collection, query):
        return self.mongo[collection].insert(query)

    def map_reduce(self, collection, map, reduce, out):
        return self.mongo[collection].map_reduce(map=map, reduce=reduce, out=out)

    def count(self,collection,query={}):
        return self.mongo[collection].find(query).count()

class DBWrapper():
    def __init__(self, dbtype):

        if dbtype == "mongo":
            self.safe = MongoWrapper(True)
            self.unsafe = MongoWrapper(False)
        elif dbtype == "postgres":
            self.safe = FakeMongo()
            self.unsafe = FakeMongo()

        self.binarycon = pymongo.MongoClient(serversettings.settings['bin-mongo-hostname'], serversettings.settings['bin-mongo-port'], max_pool_size=serversettings.settings['mongo-connections'])
        self.binaries = self.binarycon[
            serversettings.settings['bin-mongo-db']]
        self.sessioncon = pymongo.MongoClient(serversettings.settings['sessions-mongo-hostname'], serversettings.settings['sessions-mongo-port'])
        self.session = self.sessioncon[
            serversettings.settings['sessions-mongo-db']]


def print_timing(func):
    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        print((t2 - t1) * 1000.0)
        return res
    return wrapper


class Server(object):

    class FancyDateTimeDelta(object):
        """
        Format the date / time difference between the supplied date and
        the current time using approximate measurement boundaries
        """

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
            #Round down. People don't want the exact time.
            #For exact time, reverse array.
            fmt = ""
            for period in ['millisecond', 'second', 'minute', 'hour', 'day', 'month', 'year']:
                value = getattr(self, period)
                if value:
                    if value > 1:
                        period += "s"

                    fmt = str(value) + " " + period
            return fmt + " ago"

    def getnextint(self, queuename, forcewrite=False):
        if not 'queues' in serversettings.settings:
            serversettings.settings['queues'] = {}

        if not queuename in serversettings.settings['queues']:
            serversettings.settings['queues'][queuename] = 0

        serversettings.settings['queues'][queuename] += 1

        if forcewrite == True:
            serversettings.saveconfig()

        return serversettings.settings['queues'][queuename]

    def __init__(self, settingsfile=None):
        self.cache = OrderedDict()
        self.logger = logging.getLogger('Tavern')
        self.mc = OrderedDict

        # Break out the settings into it's own file, so we can include it without including all of server
        # This does cause a few shenanigans while loading here, but hopefully it's minimal
        if settingsfile is None:
            if os.path.isfile(platform.node() + ".TavernServerSettings"):
                #Load Default file(hostnamestname)
                serversettings.loadconfig()
            else:
                #Generate New config
                self.logger.info("Generating new Config")
                self.ServerKeys = Keys()
                self.ServerKeys.generate()
        else:
            serversettings.loadconfig(settingsfile)

        if not 'pubkey' in serversettings.settings:
            serversettings.settings['pubkey'] = self.ServerKeys.pubkey
        if not 'privkey' in serversettings.settings:
            serversettings.settings['privkey'] = self.ServerKeys.privkey

        serversettings.updateconfig()
        serversettings.saveconfig()
        self.ServerKeys = Keys(pub=serversettings.settings['pubkey'],
                               priv=serversettings.settings['privkey'])

        self.db = DBWrapper(serversettings.settings['dbtype'])

        self.bin_GridFS = GridFS(self.db.binaries)
        serversettings.saveconfig()

        # Get a list of all the valid templates that can be used, to compare against later on.
        self.availablethemes = []
        for name in os.listdir('themes'):
            if os.path.isdir(os.path.join('themes', name)):
                if name[:1] != ".":
                    self.availablethemes.append(name)

        serversettings.settings['static-revision'] = int(time.time())

        self.fortune = TavernUtils.randomWords(fortunefile="data/fortunes")
        self.wordlist = TavernUtils.randomWords(fortunefile="data/wordlist")

        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        #logging.basicConfig(filename=serversettings.settings['logfile'],level=logging.DEBUG)

        # Cache our JS, so we can include it later.
        file = open("static/scripts/instance.min.js")
        self.logger.info("Cached JS")
        self.cache['instance.js'] = file.read()
        file.close()

    def init2(self):
        """
        Stuff that needs to be done later, so other pieces might be ready
        """
        self.external = embedis.embedis()
        from uasparser import UASparser
        self.logger.info("Loading Browser info")
        self.browserdetector = UASparser()

    def prettytext(self):
        newstr = json.dumps(
            serversettings.settings, indent=2, separators=(', ', ': '))
        return newstr

    def sorttopic(self, topic):
        if topic is not None:
            topic = topic.lower()
            topic = self.urlize(topic)
        else:
            topic = None
        return topic

    def error_envelope(self, error="Error"):
        e = Envelope()
        e.dict['envelope']['payload'] = OrderedDict()
        e.dict['envelope']['payload']['subject'] = "Error"
        e.dict['envelope']['payload']['topic'] = "Error"
        e.dict['envelope']['payload']['formatting'] = "markdown"
        e.dict['envelope']['payload']['class'] = "message"
        e.dict['envelope']['payload'][
            'body'] = "Oh, No, something's gone wrong.. \n\n " + error
        e.dict['envelope']['payload']['author'] = OrderedDict()
        e.dict['envelope']['payload']['author']['pubkey'] = "1234"
        e.dict['envelope']['payload']['author']['friendlyname'] = "ERROR!"
        e.dict['envelope']['payload']['author']['useragent'] = "Error Agent"
        e.dict['envelope']['payload']['author']['friendlyname'] = "Error"
        e.dict['envelope']['local']['time_added'] = 1297396876
        e.dict['envelope']['local']['author_wordhash'] = "ErrorMessage!"
        e.dict['envelope']['local']['sorttopic'] = "error"

        e.dict['envelope']['payload_sha512'] = e.payload.hash()
        e.dict = self.formatEnvelope(e.dict)
        return e

    def receiveEnvelope(self, envelope):
        c = Envelope()
        c.loadstring(importstring=envelope)

        #First, ensure we're dealing with a good Env, before we proceed
        if not c.validate():
            self.logger.info("Validation Error")
            self.logger.info(c.text())
            return False

        # First, pull the message.
        existing = self.db.unsafe.find_one(
            'envelopes', {'envelope.payload_sha512': c.payload.hash()})
        if existing is not None:
            self.logger.info("We already have that msg.")
            return c.dict['envelope']['payload_sha512']

        #If we don't have a local section, add one.
        #This isn't inside of validation since it's legal not to have one.
        #if 'local' not in c.dict['envelope']:
        c.dict['envelope']['local'] = OrderedDict()

        #Pull out serverstamps.
        stamps = c.dict['envelope']['stamps']

        serversTouched = 0

        # Count the parters the message has danced with.
        for stamp in stamps:
            if stamp['class'] == "server" or stamp['class'] == "server":
                serversTouched += 1

        utctime = time.time()

        # Sign the message to saw we saw it.
        signedpayload = self.ServerKeys.signstring(c.payload.text())
        myserverinfo = {'class': 'server', 'hostname': serversettings.settings['hostname'], 'time_added': int(utctime), 'signature': signedpayload, 'pubkey': self.ServerKeys.pubkey}
        stamps.append(myserverinfo)

        # If we are the first to see this, and it's enabled -- set outselves as the Origin.
        if serversettings.settings['mark-origin'] == True:
            if serversTouched == 0:
                myserverinfo = {'class': 'origin', 'hostname': serversettings.settings['hostname'], 'time_added': int(utctime), 'signature': signedpayload, 'pubkey': self.ServerKeys.pubkey}
                stamps.append(myserverinfo)

        # Copy a lowercase version of the topic into sorttopic, so that StarTrek and Startrek and startrek all show up together.
        if 'topic' in c.dict['envelope']['payload']:
            c.dict['envelope']['local']['sorttopic'] = self.sorttopic(
                c.dict['envelope']['payload']['topic'])

        c.dict['envelope']['stamps'] = stamps
        # Do NOT round UTC time, in LOCAL. This allows us to page properly, rather than using skip() which is expensive.
        c.dict['envelope']['local']['time_added'] = utctime

        if c.dict['envelope']['payload']['class'] == "message":
            # If the message referenes anyone, mark the original, for ease of finding it later.
            # Do this in the {local} block, so we don't waste bits passing this on.
            # Partners can calculate this when they receive it.

            if 'regarding' in c.dict['envelope']['payload']:
                repliedTo = Envelope()
                if repliedTo.loadmongo(mongo_id=c.dict['envelope']['payload']['regarding']):
                    self.logger.info(
                        " I am :: " + c.dict['envelope']['payload_sha512'])
                    self.logger.info(" Adding a cite on my parent :: " + repliedTo.dict['envelope']['payload_sha512'])
                    repliedTo.addcite(c.dict['envelope']['payload_sha512'])

            # It could also be that this message is cited BY others we already have!
            # Sometimes we received them out of order. Better check.
            for citedme in self.db.unsafe.find('envelopes', {'envelope.local.sorttopic': self.sorttopic(c.dict['envelope']['payload']['topic']), 'envelope.payload.regarding': c.dict['envelope']['payload_sha512']}):
                self.logger.info('found existing cite, bad order. ')
                self.logger.info(
                    " I am :: " + c.dict['envelope']['payload_sha512'])
                self.logger.info(" Found pre-existing cite at :: " +
                                 citedme['envelope']['payload_sha512'])
                citedme = self.formatEnvelope(citedme)
                c.addcite(citedme['envelope']['payload_sha512'])

        #Create the HTML version, and store it in local
        c.dict = self.formatEnvelope(c.dict)

        #Store our Envelope
        c.saveMongo()
        return  c.dict['envelope']['payload_sha512']

    def formatText(self, text=None, formatting='markdown'):
        if formatting == 'markdown':
            formatted = self.autolink(markdown.markdown(server.gfm(text), output_format="html5", safe_mode='escape', enable_attributes=False))
        elif formatting == 'bbcode':
            formatted = bbcodepy.Parser().to_html(text)
        elif formatting == "plaintext":
            formatted = "<pre>" + text + "</pre>"
        else:
            #If we don't know, you get Markdown
            formatted = self.autolink(markdown.markdown(self.gfm(text)))

        return formatted

    def find_top_parent(self, messageid):
        # Find the top level of a post that we currently have.

        # First, pull the message.
        envelope = self.db.unsafe.find_one('envelopes',
                                           {'envelope.payload_sha512': messageid})
        envelope = self.formatEnvelope(envelope)

        # IF we don't have a parent, or if it's null, return self./
        if not 'regarding' in envelope['envelope']['payload']:
            return messageid
        if envelope['envelope']['payload']['regarding'] is None:
            return messageid

        # If we do have a parent, Check to see if it's in our datastore.
        parentid = envelope['envelope']['payload']['regarding']
        parent = self.db.unsafe.find_one('envelopes',
                                         {'envelope.payload_sha512': parentid})
        if parent is None:
            return messageid

        # If it is, recurse
        return self.find_top_parent(parentid)

    def urlize(self, url):
        # I do NOT want to urlencode this, because that encodes the unicode characters.
        # Browsers are perfectly capable of handling these!
        url = re.sub('[/? ]', '-', url)
        url = re.sub(r'[^\w-]', '', url)
        return url

    def formatEnvelope(self, envelope):
        """
        Ensure an envelope has proper formatting.
        Supposed to be called when you receive an envelope, not on view.
        """
        attachmentList = []
        if 'subject' in envelope['envelope']['payload']:
            #First 50 characters, in a URL-friendly-manner
            temp_short = envelope['envelope']['payload'][
                'subject'][:50].rstrip()
            envelope['envelope']['local'][
                'short_subject'] = self.urlize(temp_short)
        if 'binaries' in envelope['envelope']['payload']:
            for binary in envelope['envelope']['payload']['binaries']:
                if 'sha_512' in binary:
                    fname = binary['sha_512']
                    try:
                        attachment = self.bin_GridFS.get_last_version(
                            filename=fname)
                        if 'filename' not in binary:
                            binary['filename'] = "unknown_file"
                        #In order to display an image, it must be of the right MIME type, the right size, it must open in
                        #Python and be a valid image.
                        attachment.seek(0)
                        detected_mime = magic.from_buffer(
                            attachment.read(serversettings.settings['max-upload-preview-size']), mime=True).decode('utf-8')
                        displayable = False
                        if attachment.length < serversettings.settings['max-upload-preview-size']:  # Don't try to make a preview if it's > 10M
                            if 'content_type' in binary:
                                if binary['content_type'].rsplit('/')[0].lower() == "image":
                                    attachment.seek(0)
                                    imagetype = imghdr.what(
                                        'ignoreme', h=attachment.read())
                                    acceptable_images = [
                                        'gif', 'jpeg', 'jpg', 'png', 'bmp']
                                    if imagetype in acceptable_images:
                                        #If we pass -all- the tests, create a thumb once.
                                        displayable = binary[
                                            'sha_512'] + "-thumb"
                                        if not self.bin_GridFS.exists(filename=displayable):
                                            attachment.seek(0)
                                            im = Image.open(attachment)

                                            # Check to see if we need to rotate the image
                                            # This is caused by iPhones saving the orientation

                                            if hasattr(im, '_getexif'):  # only present in JPEGs
                                                    e = im._getexif()       # returns None if no EXIF data
                                                    if e is not None:
                                                        exif = dict(e.items())
                                                        if 'Orientation' in exif:
                                                            orientation = exif[
                                                                'Orientation']

                                                            if orientation == 3:
                                                                image = im.transpose(Image.ROTATE_180)
                                                            elif orientation == 6:
                                                                image = im.transpose(Image.ROTATE_270)
                                                            elif orientation == 8:
                                                                image = im.transpose(Image.ROTATE_90)

                                            # resize if nec.
                                            if im.size[0] > 640:
                                                imAspect = float(im.size[1]) / float(im.size[0])
                                                newx = 640
                                                newy = int(640 * imAspect)
                                                im = im.resize((newx, newy), Image.ANTIALIAS)
                                            if im.size[1] > 480:
                                                imAspect = float(im.size[0]) / float(im.size[1])
                                                newy = 480
                                                newx = int(480 * imAspect)
                                                im = im.resize((newx, newy), Image.ANTIALIAS)

                                            thumbnail = self.bin_GridFS.new_file(filename=displayable)
                                            self.logger.info(displayable)
                                            im.save(thumbnail, format='png')
                                            thumbnail.close()
                        attachmentdesc = {'sha_512': binary['sha_512'], 'filename': binary['filename'], 'filesize': attachment.length, 'displayable': displayable, 'detected_mime': detected_mime}
                        attachmentList.append(attachmentdesc)
                    except gridfs.errors.NoFile:
                        self.logger.info("Error, attachment gone ;(")
        if 'body' in envelope['envelope']['payload']:
            if 'formatting' in envelope['envelope']['payload']:
                formattedbody = self.formatText(text=envelope['envelope']['payload']['body'], formatting=envelope['envelope']['payload']['formatting'])
            else:
                formattedbody = self.formatText(
                    text=envelope['envelope']['payload']['body'])
            envelope['envelope']['local']['formattedbody'] = formattedbody

        #Create an attachment list that includes the calculated filesize, since we can't trust the one from the client.
        #But since the file is IN the payload, we can't modify that one, either!
        envelope['envelope']['local']['attachmentlist'] = attachmentList
        envelope['envelope']['local']['author_wordhash'] = server.wordlist.wordhash(envelope['envelope']['payload']['author']['pubkey'])

        # Check for a medialink for FBOG, Pinterest, etc.
        # Leave off if it doesn't exist
        if len(attachmentList) > 0:
            medialink = None
            for attachment in attachmentList:
                if attachment['displayable'] is not False:
                    envelope['envelope']['local']['medialink'] = medialink
                    break

        # Check for any Embeddable (Youtube, Vimeo, etc) Links.
        # Don't check a given message more than once.
        # Iterate through the list of possible embeddables.

        foundurls = 0  # Don't embed too many URLs
        if 'body' in envelope['envelope']['payload']:
            if not 'embed' in envelope['envelope']['local']:
                envelope['envelope']['local']['embed'] = []
            if envelope['envelope']['local']['embed'] == []:
                # Don't check more than once.
                soup = BeautifulSoup(formattedbody)
                for href in soup.findAll('a'):
                    result = self.external.lookup(href.get('href'))
                    if result is not None and foundurls < serversettings.settings['maxembeddedurls']:
                        if not 'embed' in envelope['envelope']['local']:
                            envelope['envelope']['local']['embed'] = []
                        envelope['envelope']['local']['embed'].append(result)
                        foundurls += 1

        if '_id' in envelope:
            del(envelope['_id'])
        return envelope

    #Autolink from http://greaterdebater.com/blog/gabe/post/4
    def autolink(self, html):
        # match all the urls
        # this returns a tuple with two groups
        # if the url is part of an existing link, the second element
        # in the tuple will be "> or </a>
        # if not, the second element will be an empty string
        urlre = re.compile("(\(?https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])(\">|</a>)?")
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

    # Github flavored Markdown, from http://gregbrown.co.nz/code/githib-flavoured-markdown-python-implementation/
    #Modified to have more newlines. I like newlines.
    def gfm(self, text):
        # Extract pre blocks
        extractions = {}

        def pre_extraction_callback(matchobj):
            md5hash = md5_func(matchobj.group(0)).hexdigest()
            extractions[md5hash] = matchobj.group(0)
            return "{gfm-extraction-%s}" % md5hash
        pre_extraction_regex = re.compile(r'{gfm-extraction-338ad5080d68c18b4dbaf41f5e3e3e08}', re.MULTILINE | re.DOTALL)
        text = re.sub(pre_extraction_regex, pre_extraction_callback, text)

        # prevent foo_bar_baz from ending up with an italic word in the middle
        def italic_callback(matchobj):
            if len(re.sub(r'[^_]', '', matchobj.group(1))) > 1:
                return matchobj.group(1).replace('_', '\_')
            else:
                return matchobj.group(1)
        text = re.sub(r'(^(?! {4}|\t)\w+_\w+_\w[\w_]*)', italic_callback, text)

        # in very clear cases, let newlines become <br /> tags
        def newline_callback(matchobj):
            if len(matchobj.group(1)) == 1:
                return matchobj.group(0).rstrip() + '  \n'
            else:
                return matchobj.group(0)
        # text = re.sub(r'^[\w\<][^\n]*(\n+)', newline_callback, text)
        text = re.sub(r'[^\n]*(\n+)', newline_callback, text)

        # Insert pre block extractions
        def pre_insert_callback(matchobj):
            return extractions[matchobj.group(1)]
        text = re.sub(
            r'{gfm-extraction-([0-9a-f]{40})\}', pre_insert_callback, text)

        return text

server = Server()
from User import User
import embedis
server.init2()
