import os
import json
import hashlib
import imghdr
import platform
import time
from keys import *
import Image
import logging
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
import re
import bbcodepy
from bs4 import BeautifulSoup
import magic


def print_timing(func):
    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        print((t2 - t1) * 1000.0)
        return res
    return wrapper


class Fortuna():
    def __init__(self, fortunefile="fortunes"):
        self.fortunes = []
        fortunes = open(fortunefile, "r")
        line = fortunes.readline()
        while line:
            self.fortunes.append(line.rstrip().lstrip())
            line = fortunes.readline()

    def random(self):
        """
        Return a Random Fortune from the stack
        """
        fortuneindex = server.randrange(0, len(self.fortunes) - 1)
        return self.fortunes[fortuneindex]


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

    def randrange(self, start, stop):
        """
        The random that comes with Python is blocking.
        Re-create the randrange function, using /dev/urandom
        Only use this for not critical functions, like random header fortunes ;)
        """

        # os.urandom generates X bytes of randomness
        # If it's a small number requested, look up the fewest bits needed.
        # If it's a larger number, calculate the fewest.
        # This saves bits on the server ;)
        diff = abs(stop - start) + 1
        if diff < 255:
            bytes = 1
        elif diff <= 65535:
            bytes = 2
        elif diff <= 16777215:
            bytes = 3
        elif diff <= 4294967295:
            bytes = 4
        else:
            # If it's this big, calculate it out.
            num = 4294967295
            bytes = 3
            while num <= diff:
                bytes += 1
                integerstring = ''
                for i in range(0, (bytes * 8)):
                    integerstring += '1'
                num = int(integerstring, 2)

        randnum = int.from_bytes(os.urandom(bytes), 'big')
        rightsize = randnum % diff
        return start + rightsize

    def randstr(self, length, printable=False):
        # Ensure it's self.logger.infoable.
        if printable == True:
            # TODO - Expand this using a python builtin.
            ran = ''.join(chr(self.randrange(65, 90)) for i in range(length))
        else:
            ran = ''.join(chr(self.randrange(48, 122)) for i in range(length))
        return ran

    def __init__(self, settingsfile=None):
        self.ServerSettings = OrderedDict()
        self.mongocons = OrderedDict()
        self.mongos = OrderedDict()
        self.cache = OrderedDict()
        self.logger = logging.getLogger('Tavern')
        self.mc = OrderedDict

        if settingsfile is None:
            if os.path.isfile(platform.node() + ".TavernServerSettings"):
                #Load Default file(hostnamestname)
                self.loadconfig()
            else:
                #Generate New config
                self.logger.info("Generating new Config")
                self.ServerKeys = Keys()
                self.ServerKeys.generate()
                self.ServerSettings = OrderedDict()
        else:
            self.loadconfig(settingsfile)

        self.logger.info("Generating any missing config values")

        if not 'pubkey' in self.ServerSettings:
            self.ServerSettings['pubkey'] = self.ServerKeys.pubkey
        if not 'privkey' in self.ServerSettings:
            self.ServerSettings['privkey'] = self.ServerKeys.privkey
        if not 'hostname' in self.ServerSettings:
            self.ServerSettings['hostname'] = platform.node()
        if not 'logfile' in self.ServerSettings:
            self.ServerSettings[
                'logfile'] = self.ServerSettings['hostname'] + '.log'
        if not 'mongo-hostname' in self.ServerSettings:
            self.ServerSettings['mongo-hostname'] = 'localhost'
        if not 'mongo-port' in self.ServerSettings:
            self.ServerSettings['mongo-port'] = 27017
        if not 'mongo-db' in self.ServerSettings:
            self.ServerSettings['mongo-db'] = 'Tavern'
        if not 'bin-mongo-hostname' in self.ServerSettings:
            self.ServerSettings['bin-mongo-hostname'] = 'localhost'
        if not 'bin-mongo-port' in self.ServerSettings:
            self.ServerSettings['bin-mongo-port'] = 27017
        if not 'bin-mongo-db' in self.ServerSettings:
            self.ServerSettings['bin-mongo-db'] = 'Tavern-Binaries'
        if not 'sessions-mongo-hostname' in self.ServerSettings:
            self.ServerSettings['sessions-mongo-hostname'] = 'localhost'
        if not 'sessions-mongo-port' in self.ServerSettings:
            self.ServerSettings['sessions-mongo-port'] = 27017
        if not 'sessions-mongo-db' in self.ServerSettings:
            self.ServerSettings['sessions-mongo-db'] = 'Tavern-Sessions'

        if not 'cache' in self.ServerSettings:
            self.ServerSettings['cache'] = {}

        if not 'user-trust' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['user-trust'] = {}
            self.ServerSettings['cache']['user-trust']['seconds'] = 300
            self.ServerSettings['cache']['user-trust']['size'] = 10000

        if not 'user-ratings' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['user-ratings'] = {}
            self.ServerSettings['cache']['user-ratings']['seconds'] = 300
            self.ServerSettings['cache']['user-ratings']['size'] = 10000

        if not 'avatarcache' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['avatarcache'] = {}
            self.ServerSettings['cache']['avatarcache']['size'] = 100000
            self.ServerSettings['cache']['avatarcache']['seconds'] = None

        if not 'embedded' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['embedded'] = {}
            self.ServerSettings['cache']['embedded']['size'] = 1000
            self.ServerSettings['cache']['embedded']['seconds'] = 3600

        if not 'user-note' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['user-note'] = {}
            self.ServerSettings['cache']['user-note']['size'] = 10000
            self.ServerSettings['cache']['user-note']['seconds'] = 60

        if not 'subjects-in-topic' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['subjects-in-topic'] = {}
            self.ServerSettings['cache']['subjects-in-topic']['size'] = 1000
            self.ServerSettings['cache']['subjects-in-topic']['seconds'] = 30

        if not 'toptopics' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['toptopics'] = {}
            self.ServerSettings['cache']['toptopics']['size'] = 1
            self.ServerSettings['cache']['toptopics']['seconds'] = 3600

        if not 'frontpage' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['frontpage'] = {}
            self.ServerSettings['cache']['frontpage']['size'] = 1000
            self.ServerSettings['cache']['frontpage']['seconds'] = 3600

        if not 'uasparser' in self.ServerSettings['cache']:
            self.ServerSettings['cache']['uasparser'] = {}
            self.ServerSettings['cache']['uasparser']['size'] = 1000
            self.ServerSettings['cache']['uasparser']['seconds'] = 36000

        if not 'upload-dir' in self.ServerSettings:
            self.ServerSettings['upload-dir'] = '/opt/uploads'

        if not 'max-upload-preview-size' in self.ServerSettings:
            self.ServerSettings['max-upload-preview-size'] = 10485760

        if not 'cookie-encryption' in self.ServerSettings:
            self.ServerSettings['cookie-encryption'] = self.randstr(255)
        if not 'serverkey-password' in self.ServerSettings:
            self.ServerSettings['serverkey-password'] = self.randstr(255)
        if not 'embedserver' in self.ServerSettings:
            self.ServerSettings['embedserver'] = 'http://embed.is'
        if not 'downloadsurl' in self.ServerSettings:
            self.ServerSettings['downloadsurl'] = '/binaries/'
        if not 'maxembeddedurls' in self.ServerSettings:
            self.ServerSettings['maxembeddedurls'] = 10

        if not 'mongo-connections' in self.ServerSettings:
            self.ServerSettings['mongo-connections'] = 10

        # Create a fast, unsafe mongo connection. Writes might get lost.
        self.mongocons['unsafe'] = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'], read_preference=pymongo.read_preferences.ReadPreference.SECONDARY_PREFERRED, max_pool_size=self.ServerSettings['mongo-connections'])
        self.mongos['unsafe'] = self.mongocons['unsafe'][
            self.ServerSettings['mongo-db']]

        # Slower, more reliable mongo connection.
        self.mongocons['safe'] = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'], safe=True, journal=True, max_pool_size=self.ServerSettings['mongo-connections'])
        self.mongos['safe'] = self.mongocons['safe'][
            self.ServerSettings['mongo-db']]

        self.mongocons['binaries'] = pymongo.Connection(self.ServerSettings['bin-mongo-hostname'], self.ServerSettings['bin-mongo-port'], max_pool_size=self.ServerSettings['mongo-connections'])
        self.mongos['binaries'] = self.mongocons['binaries'][
            self.ServerSettings['bin-mongo-db']]
        self.mongocons['sessions'] = pymongo.Connection(self.ServerSettings['sessions-mongo-hostname'], self.ServerSettings['sessions-mongo-port'])
        self.mongos['sessions'] = self.mongocons['sessions'][
            self.ServerSettings['sessions-mongo-db']]
        self.bin_GridFS = GridFS(self.mongos['binaries'])
        self.saveconfig()

        # Get a list of all the valid templates that can be used, to compare against later on.
        self.availablethemes = []
        for name in os.listdir('themes'):
            if os.path.isdir(os.path.join('themes', name)):
                if name[:1] != ".":
                    self.availablethemes.append(name)

        self.ServerSettings['static-revision'] = int(time.time())
        self.fortune = Fortuna()

        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
        #logging.basicConfig(filename=self.ServerSettings['logfile'],level=logging.DEBUG)

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

    def loadconfig(self, filename=None):
        if filename is None:
            filename = platform.node() + ".TavernServerSettings"
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.ServerSettings = json.loads(filecontents, object_pairs_hook=collections.OrderedDict, object_hook=collections.OrderedDict)
        self.ServerKeys = Keys(pub=self.ServerSettings['pubkey'],
                               priv=self.ServerSettings['privkey'])

        filehandle.close()
        self.saveconfig()

    def saveconfig(self, filename=None):
        if filename is None:
            filename = self.ServerSettings['hostname'] + \
                ".TavernServerSettings"
        filehandle = open(filename, 'w')
        filehandle.write(
            json.dumps(self.ServerSettings, separators=(',', ':')))
        filehandle.close()

    def prettytext(self):
        newstr = json.dumps(
            self.ServerSettings, indent=2, separators=(', ', ': '))
        return newstr

    def sorttopic(self, topic):
        topic = topic.lower()
        topic = self.urlize(topic)
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
        e.dict['envelope']['local']['author_pubkey_sha1'] = "000000000000000000000000000000000000000000000000000000000000"
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
        existing = self.mongos['unsafe']['envelopes'].find_one({'envelope.payload_sha512': c.payload.hash()}, as_class=OrderedDict)
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
        myserverinfo = {'class': 'server', 'hostname': self.ServerSettings['hostname'], 'time_added': int(utctime), 'signature': signedpayload, 'pubkey': self.ServerKeys.pubkey}
        stamps.append(myserverinfo)

        # If we are the first to see this, also set outselves as the Origin.
        if serversTouched == 0:
            myserverinfo = {'class': 'origin', 'hostname': self.ServerSettings['hostname'], 'time_added': int(utctime), 'signature': signedpayload, 'pubkey': self.ServerKeys.pubkey}
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
            for citedme in self.mongos['unsafe']['envelopes'].find({'envelope.local.sorttopic': self.sorttopic(c.dict['envelope']['payload']['topic']), 'envelope.payload.regarding': c.dict['envelope']['payload_sha512']}, as_class=OrderedDict):
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

    def inttime(self):
        """
        Force 1 sec precision, so multiple requests per second cache.
        """
        return int(time.time())

    def formatText(self, text=None, formatting='markdown'):
        if formatting == 'markdown':
            formatted = self.autolink(markdown.markdown(self.gfm(text)))
        elif formatting == 'bbcode':
            formatted = bbcodepy.Parser().to_html(text)
        elif formatting == 'html':
            VALID_TAGS = ['strong', 'em', 'p', 'ul', 'li', 'br']
            soup = BeautifulSoup(text)
            for tag in soup.findAll(True):
                if tag.name not in VALID_TAGS:
                    tag.hidden = True
            formatted = soup.renderContents()
        elif formatting == "plaintext":
            formatted = "<pre>" + text + "</pre>"
        else:
            #If we don't know, you get Markdown
            formatted = self.autolink(markdown.markdown(self.gfm(text)))

        return formatted

    def find_top_parent(self, messageid):
        # Find the top level of a post that we currently have.

        # First, pull the message.
        envelope = self.mongos['unsafe']['envelopes'].find_one(
            {'envelope.payload_sha512': messageid}, as_class=OrderedDict)
        envelope = self.formatEnvelope(envelope)

        # IF we don't have a parent, or if it's null, return self./
        if not 'regarding' in envelope['envelope']['payload']:
            return messageid
        if envelope['envelope']['payload']['regarding'] is None:
            return messageid

        # If we do have a parent, Check to see if it's in our datastore.
        parentid = envelope['envelope']['payload']['regarding']
        parent = self.mongos['unsafe']['envelopes'].find_one(
            {'envelope.payload_sha512': parentid}, as_class=OrderedDict)
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
                            attachment.read(self.ServerSettings['max-upload-preview-size']), mime=True).decode('utf-8')
                        displayable = False
                        if attachment.length < self.ServerSettings['max-upload-preview-size']:  # Don't try to make a preview if it's > 10M
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
        envelope['envelope']['local']['author_pubkey_sha1'] = hashlib.sha1(envelope['envelope']['payload']['author']['pubkey'].encode('utf-8')).hexdigest()

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
                    if result is not None and foundurls < self.ServerSettings['maxembeddedurls']:
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
            hash = md5_func(matchobj.group(0)).hexdigest()
            extractions[hash] = matchobj.group(0)
            return "{gfm-extraction-%s}" % hash
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
