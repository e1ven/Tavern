import os,json
import hashlib
import imghdr
import platform
import time
from keys import *
import Image
import logging
import string
import random
import collections
from collections import OrderedDict
import collections
import pymongo
from gridfs import GridFS
import gridfs
from Envelope import Envelope
import sys
import pprint
import markdown
import imghdr
import datetime
import re
import bbcodepy
import embedis
from urllib.parse import urlparse,parse_qs
from bs4 import BeautifulSoup
import urllib.request, urllib.parse, urllib.error

class Fortuna():
    def __init__(self,fortunefile="fortunes"):
        self.fortunes = []            
        fortunes = open(fortunefile, "r")
        line = fortunes.readline()
        while line:
            self.fortunes.append(line.rstrip().lstrip())
            line = fortunes.readline()
        print("Fortunes Loaded.")
    def random(self):
        return random.choice(self.fortunes)


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
            self.second = delta.seconds - ( self.hour * 3600) - (60 * self.minute) 
            self.millisecond = delta.microseconds / 1000

        def format(self):
            #Round down. People don't want the exact time.
            #For exact time, reverse array.
            fmt = ""
            for period in ['millisecond','second','minute','hour','day','month','year']:
                value = getattr(self, period)
                if value:
                    if value > 1:
                        period += "s"

                    fmt = str(value) + " " + period
            return fmt + " ago"



    def __init__(self,settingsfile=None):            
        self.ServerSettings = OrderedDict()
        self.mongocons = OrderedDict()
        self.mongos = OrderedDict()
        self.cache = OrderedDict()

        if settingsfile == None:
            if os.path.isfile(platform.node() + ".PluricServerSettings"):
                #Load Default file(hostnamestname)
                self.loadconfig()
            else:
                #Generate New config   
                print("Generating new Config") 
                self.ServerKeys = Keys()
                self.ServerKeys.generate()
                self.ServerSettings = OrderedDict()
                self.ServerSettings['pubkey'] = self.ServerKeys.pubkey
                self.ServerSettings['privkey'] = self.ServerKeys.privkey
                self.ServerSettings['hostname'] = platform.node()
                self.ServerSettings['logfile'] = self.ServerSettings['hostname'] + '.log'
                self.ServerSettings['mongo-hostname'] = 'localhost'
                self.ServerSettings['mongo-port'] = 27017            
                self.ServerSettings['mongo-db'] = 'test'  
                self.ServerSettings['bin-mongo-hostname'] = 'localhost'
                self.ServerSettings['bin-mongo-port'] = 27017
                self.ServerSettings['bin-mongo-db'] = 'test'
                self.ServerSettings['cache-mongo-hostname'] = 'localhost'
                self.ServerSettings['cache-mongo-port'] = 27017
                self.ServerSettings['cache-mongo-db'] = 'test'
                self.ServerSettings['sessions-mongo-hostname'] = 'localhost'
                self.ServerSettings['sessions-mongo-port'] = 27017
                self.ServerSettings['sessions-mongo-db'] = 'test'
                
                self.ServerSettings['upload-dir'] = '/opt/uploads'
                self.mongocons['default'] = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'])
                self.mongos['default'] =  self.mongocons['default'][self.ServerSettings['mongo-db']]             
                self.mongocons['binaries'] = pymongo.Connection(self.ServerSettings['bin-mongo-hostname'], self.ServerSettings['bin-mongo-port'])
                self.mongos['binaries'] = self.mongocons['binaries'][self.ServerSettings['bin-mongo-db']]
                self.mongocons['cache'] = pymongo.Connection(self.ServerSettings['cache-mongo-hostname'], self.ServerSettings['cache-mongo-port'])
                self.mongos['cache'] = self.mongocons['cache'][self.ServerSettings['cache-mongo-db']]
                self.mongocons['sessions'] =  pymongo.Connection(self.ServerSettings['sessions-mongo-hostname'], self.ServerSettings['sessions-mongo-port'])
                self.mongos['sessions'] = self.mongocons['sessions'][self.ServerSettings['sessions-mongo-db']]
                self.bin_GridFS = GridFS(self.mongos['binaries'])

                self.saveconfig()   


        else:
            self.loadconfig(settingsfile)
        
        self.ServerSettings['static-revision'] = int(time.time())

        #logging.basicConfig(filename=self.ServerSettings['logfile'],level=logging.DEBUG)
        logging.basicConfig(stream=sys.stdout,level=logging.DEBUG)
        self.fortune = Fortuna()

        # Cache our JS, so we can include it later.
        file = open("static/scripts/instance.js")
        print("Cached JS")
        self.cache['instance.js'] = file.read()
        file.close()


    def loadconfig(self,filename=None):
        print("Loading config from file.")
        if filename == None:
            filename = platform.node() + ".PluricServerSettings"
        filehandle = open(filename, 'r')
        filecontents = filehandle.read()
        self.ServerSettings = json.loads(filecontents,object_pairs_hook=collections.OrderedDict,object_hook=collections.OrderedDict)
        self.ServerKeys = Keys(pub=self.ServerSettings['pubkey'],priv=self.ServerSettings['privkey'])
        self.connection = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'])
        self.mongocons['default'] = pymongo.Connection(self.ServerSettings['mongo-hostname'], self.ServerSettings['mongo-port'])
        self.mongos['default'] =  self.mongocons['default'][self.ServerSettings['mongo-db']]             
        self.mongocons['binaries'] = pymongo.Connection(self.ServerSettings['bin-mongo-hostname'], self.ServerSettings['bin-mongo-port'])
        self.mongos['binaries'] = self.mongocons['binaries'][self.ServerSettings['bin-mongo-db']]
        self.mongocons['cache'] = pymongo.Connection(self.ServerSettings['cache-mongo-hostname'], self.ServerSettings['cache-mongo-port'])
        self.mongos['cache'] = self.mongocons['cache'][self.ServerSettings['cache-mongo-db']]
        self.mongocons['sessions'] =  pymongo.Connection(self.ServerSettings['sessions-mongo-hostname'], self.ServerSettings['sessions-mongo-port'])
        self.mongos['sessions'] = self.mongocons['sessions'][self.ServerSettings['sessions-mongo-db']]
        self.bin_GridFS = GridFS(self.mongos['binaries'])
        filehandle.close()
        self.saveconfig()

    def getSortedMessages(topic=None):
        messagesInTopic = server.mongos['default']['envelopes'].find( {"envelope.payload.class" : "message","envelope.payload.topic" : topic})

        messagedate = e["envelope"]["local"]["time_added"]

        numberOfStories = server.mongos['default']['envelopes'].find( {"envelope.payload.class" : "message","envelope.payload.topic" : topic,"envelope.local.time_added": {'$gt': messagedate }} ).count()

        print("Original Date")
        print(messagedate)
        print("num since")
        print(numberOfStories)

    
    def saveconfig(self,filename=None):
        if filename == None:
            filename = self.ServerSettings['hostname'] + ".PluricServerSettings"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.ServerSettings,separators=(',',':'))) 
        filehandle.close()

    def prettytext(self):
        newstr = json.dumps(self.ServerSettings,indent=2,separators=(', ',': '))
        return newstr
    
    def sorttopic(self,topic):
        topic = topic.lower()
        topic = self.urlize(topic) 
        return topic

    def error_envelope(self,error="Error"):
        e = Envelope()
        e.dict['envelope']['payload'] = OrderedDict()
        e.dict['envelope']['payload']['subject'] = "Error"
        e.dict['envelope']['payload']['topic'] = "Error"
        e.dict['envelope']['payload']['formatting'] = "markdown"
        e.dict['envelope']['payload']['class'] = "message"
        e.dict['envelope']['payload']['body'] = "Oh, No, something's gone wrong.. \n\n "  + error
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
        

    def receiveEnvelope(self,envelope):
        c = Envelope()
        c.loadstring(importstring=envelope)
        
        #First, ensure we're dealing with a good Env, before we proceed
        if not c.validate():
            print("Validation Error")
            print(c.text())
            return False

                # First, pull the message.
        existing = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : c.payload.hash() },as_class=OrderedDict)
        if existing is not None:
            print("We already have that msg.")  
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
        myserverinfo = {'class':'server','hostname':self.ServerSettings['hostname'],'time_added':int(utctime),'signature':signedpayload,'pubkey': self.ServerKeys.pubkey}
        stamps.append(myserverinfo)
        
        # If we are the first to see this, also set outselves as the Origin.
        if serversTouched == 0:
            myserverinfo = {'class':'origin','hostname':self.ServerSettings['hostname'],'time_added':int(utctime),'signature':signedpayload,'pubkey': self.ServerKeys.pubkey}
            stamps.append(myserverinfo)
        
        
        # Copy a lowercase version of the topic into sorttopic, so that StarTrek and Startrek and startrek all show up together.
        if 'topic' in c.dict['envelope']['payload']:
            c.dict['envelope']['local']['sorttopic'] = self.sorttopic(c.dict['envelope']['payload']['topic'])

        c.dict['envelope']['stamps'] = stamps
        c.dict['envelope']['local']['time_added']  = int(utctime) 
        
        if c.dict['envelope']['payload']['class'] == "message":       
          # If the message referenes anyone, mark the original, for ease of finding it later.
          # Do this in the {local} block, so we don't waste bits passing this on. 
          # Partners can calculate this when they receive it.

          if 'regarding' in c.dict['envelope']['payload']:
            repliedTo = Envelope()
            if repliedTo.loadmongo(mongo_id=c.dict['envelope']['payload']['regarding']):
              print(" I am :: " + c.dict['envelope']['payload_sha512'])
              print(" Adding a cite on my parent :: " + repliedTo.dict['envelope']['payload_sha512'])
              repliedTo.addcite(c.dict['envelope']['payload_sha512'])

          # It could also be that this message is cited BY others we already have!
          # Sometimes we received them out of order. Better check.
          for citedme in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic': self.sorttopic(c.dict['envelope']['payload']['topic']),'envelope.payload.regarding':c.dict['envelope']['payload_sha512']},as_class=OrderedDict):
            print('found existing cite, bad order. ')
            print(" I am :: " + c.dict['envelope']['payload_sha512'])
            print(" Found pre-existing cite at :: " + citedme['envelope']['payload_sha512']) 
            citedme = self.formatEnvelope(citedme)
            c.addcite(citedme['envelope']['payload_sha512'])
      
                    


 
        #Create the HTML version, and store it in local        
        c.dict = self.formatEnvelope(c.dict)
                    
        #Store our Envelope
        c.saveMongo()
        return  c.dict['envelope']['payload_sha512']
        
    def formatText(self,text=None,formatting='markdown'):    
        if formatting == 'markdown':
            formatted = self.autolink(markdown.markdown(self.gfm(text)))
        elif formatting == 'bbcode':
            formatted =  bbcodepy.Parser().to_html(text)    
        elif formatting == 'html':
            VALID_TAGS = ['strong', 'em', 'p', 'ul', 'li', 'br']
            soup = BeautifulSoup(text)
            for tag in soup.findAll(True):
                if tag.name not in VALID_TAGS:
                    tag.hidden = True
            formatted =  soup.renderContents()
        elif formatting == "plaintext":
                formatted = "<pre>" + text + "</pre>"
        else:
                #If we don't know, you get Markdown
                formatted = self.autolink(markdown.markdown(self.gfm(text)))
                
        return formatted
        
    def find_top_parent(self,messageid):
        # Find the top level of a post that we currently have.
        
        # First, pull the message.
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : messageid },as_class=OrderedDict)
        envelope = server.formatEnvelope(envelope)
        
    
        # IF we don't have a parent, or if it's null, return self./
        if not 'regarding' in envelope['envelope']['payload']:
            return messageid
        if envelope['envelope']['payload']['regarding'] is None:
           return messageid
           
        # If we do have a parent, Check to see if it's in our datastore.
        parentid = envelope['envelope']['payload']['regarding']
        parent = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : parentid },as_class=OrderedDict)
        if parent is None:
            return messageid
            
        # If it is, recurse
        return self.find_top_parent(parentid)    


    def urlize(self,url):   
        url = "-".join(url.split())
        url = urllib.parse.quote(url)
        return url 

    def formatEnvelope(self,envelope):
        attachmentList = []        
        if 'subject' in envelope['envelope']['payload']:
            #First 50 characters, in a URL-friendly-manner
            temp_short = envelope['envelope']['payload']['subject'][:50].rstrip()
            temp_short = re.sub(r'[^a-zA-Z0-9 ]+', '', temp_short)
            envelope['envelope']['local']['short_subject'] = self.urlize(temp_short)
        if 'binaries' in envelope['envelope']['payload']:
            for binary in envelope['envelope']['payload']['binaries']:
                if 'sha_512' in binary:
                    fname = binary['sha_512']
                    try:
                        attachment = self.bin_GridFS.get_last_version(filename=fname)
                        if 'filename' not in binary:
                            binary['filename'] = "unknown_file"
                        #In order to display an image, it must be of the right MIME type, the right size, it must open in
                        #Python and be a valid image.
                        displayable = False;
                        if attachment.length < 1024000:  #Don't try to make a preview if it's > 1M
                            if 'content_type' in binary:
                                if binary['content_type'].rsplit('/')[0].lower() == "image":
                                    imagetype = imghdr.what('ignoreme',h=attachment.read())
                                    acceptable_images = ['gif','jpeg','jpg','png','bmp']
                                    if imagetype in acceptable_images:
                                        #If we pass -all- the tests, create a thumb once.
                                        if not self.bin_GridFS.exists(filename=binary['sha_512'] + "-thumb"):
                                            attachment.seek(0) 
                                            im = Image.open(attachment)
                                            img_width, img_height = im.size
                                            if ((img_width > 150 ) or (img_height > 150 )): 
                                                im = im.resize((150, 150),Image.ANTIALIAS)
                                            thumbnail = self.bin_GridFS.new_file(filename=displayable)
                                            im.save(thumbnail,format='png')    
                                            thumbnail.close()
                                        displayable=binary['sha_512'] + "-thumb"
                        attachmentdesc = {'sha_512' : binary['sha_512'], 'filename' : binary['filename'], 'filesize' : attachment.length, 'displayable': displayable }
                        attachmentList.append(attachmentdesc)
                    except gridfs.errors.NoFile:
                        print("Error, attachment gone ;(")
        if 'body' in envelope['envelope']['payload']:                            
            if 'formatting' in envelope['envelope']['payload']:
                    formattedbody = self.formatText(text=envelope['envelope']['payload']['body'],formatting=envelope['envelope']['payload']['formatting'])
            else:    
                    formattedbody = self.formatText(text=envelope['envelope']['payload']['body'])
            envelope['envelope']['local']['formattedbody'] = formattedbody
                
        #Create an attachment list that includes the calculated filesize, since we can't trust the one from the client.
        #But since the file is IN the payload, we can't modify that one, either!
        envelope['envelope']['local']['attachmentlist'] = attachmentList
        envelope['envelope']['local']['author_pubkey_sha1'] = hashlib.sha1(envelope['envelope']['payload']['author']['pubkey'].encode('utf-8')).hexdigest()        
        
        # Check for any Embeddable (Youtube, Vimeo, etc) Links.
        # Don't check a given message more than once.
        # Iterate through the list of possible embeddables.

        if 'body' in envelope['envelope']['payload']:
            if not 'embed' in envelope['envelope']['local']:
                envelope['envelope']['local']['embed'] = []
            if envelope['envelope']['local']['embed'] == []:
                # Don't check more than once.
                soup = BeautifulSoup(formattedbody)
                emb = embedis.embedis()
                for href in soup.findAll('a'):
                    result = emb.lookup(href.get('href'))
                    if result is not None:
                        if not 'embed' in envelope['envelope']['local']:
                            envelope['envelope']['local']['embed'] = []
                        envelope['envelope']['local']['embed'].append(result)

            if envelope['envelope']['local']['embed'] == []:
                envelope['envelope']['local']['embed'] = ["<span class='embeddables'></span>"]

        if '_id' in envelope:            
            del(envelope['_id'])        
        return envelope

    #Autolink from http://greaterdebater.com/blog/gabe/post/4
    def autolink(self,html):
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
            if url[1]: continue
            c_url = url[0]
            # ignore parens if they enclose the entire url
            if c_url[0] == '(' and c_url[-1] == ')':
                c_url = c_url[1:-1]

            if c_url in clean_urls: continue # We've already linked this url

            clean_urls.append(c_url)
            # substitute only where the url is not already part of a
            # link element.
            html = re.sub("(?<!(=\"|\">))" + re.escape(c_url), 
                          "<a rel=\"noreferrer nofollow\" href=\"" + c_url + "\">" + c_url + "</a>",
                          html)
        return html

    # Github flavored Markdown, from http://gregbrown.co.nz/code/githib-flavoured-markdown-python-implementation/
    #Modified to have more newlines. I like newlines.
    def gfm(self,text):
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
        text = re.sub(r'{gfm-extraction-([0-9a-f]{40})\}', pre_insert_callback, text)

        return text        
        
server = Server()
from User import User
