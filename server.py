import os,json
import hashlib
import M2Crypto
import imghdr
import platform
import time
from keys import *
from PIL import Image
import logging
import bcrypt
import string
import random
import collections
from collections import OrderedDict
import collections
import pymongo
from gridfs import GridFS
from Envelope import Envelope
import sys
import pprint
from postmarkup import render_bbcode
import markdown
import imghdr
import datetime
import re

class Server(object):
    class FancyDateTimeDelta(object):
        """
        Format the date / time difference between the supplied date and
        the current time using approximate measurement boundaries
        """

        def __init__(self, dt):
            now = datetime.datetime.now()
            delta = now - dt
            self.year = delta.days / 365
            self.month = delta.days / 30 - (12 * self.year)
            if self.year > 0:
                self.day = 0
            else: 
                self.day = delta.days % 30
            self.hour = delta.seconds / 3600
            self.minute = delta.seconds / 60 - (60 * self.hour)
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
        
        if settingsfile == None:
            if os.path.isfile(platform.node() + ".PluricServerSettings"):
                #Load Default file(hostnamestname)
                self.loadconfig()
            else:
                #Generate New config   
                print "Generating new Config" 
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
        
            #Ensure we have a "Guest" user
            #We can un-logged-in settings in this acct.
            users_with_this_username = self.mongos['default']['users'].find({"username":"Guest"},as_class=OrderedDict)
            if users_with_this_username.count() < 1:
                guest = OrderedDict()
                guest['username'] = "Guest"
                guest['friendlyname'] = "Guest"
                guest['hashedpass'] = bcrypt.hashpw(''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for x in range(100)), bcrypt.gensalt(12))
                
                gkeys = Keys()
                gkeys.generate()
                guest['privkey'] = gkeys.privkey
                guest['pubkey'] = gkeys.pubkey  
                guest['_id'] = guest['pubkey']
                self.mongos['default']['users'].save(guest)
        
        else:
            self.loadconfig(settingsfile)
            
        #logging.basicConfig(filename=self.ServerSettings['logfile'],level=logging.DEBUG)
        logging.basicConfig(stream=sys.stdout,level=logging.DEBUG)
 
    def loadconfig(self,filename=None):
        print "Loading config from file."
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

        
    def saveconfig(self,filename=None):
        if filename == None:
            filename = self.ServerSettings['hostname'] + ".PluricServerSettings"                
        filehandle = open(filename,'w')   
        filehandle.write(json.dumps(self.ServerSettings,separators=(u',',u':'))) 
        filehandle.close()

    def prettytext(self):
        newstr = json.dumps(self.ServerSettings,indent=2,separators=(u', ',u': '))
        return newstr
    


    def receiveEnvelope(self,envelope):
        c = Envelope()
        c.loadstring(importstring=envelope)
        
        #First, ensure we're dealing with a good Env, before we proceed
        if not c.validate():
            print "Validation Error"
            return False
        
        #If we don't have a local section, add one.
        #This isn't inside of validation since it's legal not to have one.
        if not c.dict['envelope'].has_key('local'):
            c.dict['envelope']['local'] = OrderedDict()    
        
        #Pull out serverstamps.    
        serverlist = []    
        stamps = c.dict['envelope']['stamps']
        for stamp in stamps:
            if stamp['class'] == "server":
                serverlist.append[stamp]

        #Search the server list to look for ourselves. 
        #If we find ourselves, abort. We don't want to double-process
        for server in serverlist:            
            if server['pubkey'] == self.ServerKeys.pubkey:
                #Potential Us. Let's Verify it really is.
                if Keys(pub=self.ServerKeys.pubkey).verifystring(stringtoverify=c.payload.text(),signature=server['pubkey']) == True:
                    #It's a Me!
                    #Don't double-process. Abort.
                    return False
                else:
                    #Someone is imitating us. Bastards.
                    logging.error("It's a FAAAAAAKE!")
                    #We should log this more, and look for trends, etc. For now, just suck it up, and process the message.
        
        utctime = time.time()
        #Sign the message to saw we saw it.
        signedpayload = self.ServerKeys.signstring(c.payload.text())
        myserverinfo = {'class':'server','hostname':self.ServerSettings['hostname'],'time_added':int(utctime),'signature':signedpayload,'pubkey': self.ServerKeys.pubkey}
        stamps.append(myserverinfo)
        
        c.dict['envelope']['stamps'] = stamps
        c.dict['envelope']['local']['time_added']  = int(utctime) 
        
        if c.dict['envelope']['payload']['class'] == "message":       
            #If the message referenes anyone, mark the original, for ease of finding it later.
            #Do this in the {local} block, so we don't waste bits passing this on. 
            #Partners can calculate this when they receive it.

            if c.dict['envelope']['payload'].has_key('regarding'):
                repliedTo = Envelope()
                if repliedTo.loadmongo(mongo_id=c.dict['envelope']['payload']['regarding']):
                    repliedTo.dict['envelope']['local']['citedby'].append(c.dict['envelope']['payload_sha512'])
                    repliedTo.saveMongo()
                
        #Create the HTML version, and store it in local        
        c.dict = self.formatEnvelope(c.dict)
                    
        #Store our Envelope
        c.saveMongo()
        return  c.dict['envelope']['payload_sha512']
        
    def formatText(self,text=None,formatting='markdown'):    
        if formatting == 'bbcode':
                formatted = render_bbcode(text)
        elif formatting == 'markdown':
                formatted = self.autolink(markdown.markdown(self.gfm(text)))
        elif formatting == "plaintext":
                formatted = "<pre>" + text + "</pre>"
        else:
                #If we don't know, you get Markdown
                formatted = self.autolink(markdown.markdown(self.gfm(text)))
                
        return formatted
        
    def formatEnvelope(self,envelope):
        attachmentList = []
        displayableAttachmentList = []
        
        if envelope['envelope']['payload'].has_key('subject'):
            #First 50 characters, in a URL-friendly-manner
            temp_short = envelope['envelope']['payload']['subject'][:50]
            temp_short = re.sub(r'[^a-zA-Z0-9 ]+', '', temp_short)
            envelope['envelope']['local']['short_subject'] = "-".join(temp_short.split())
        if envelope['envelope']['payload'].has_key('binaries'):
            for binary in envelope['envelope']['payload']['binaries']:
                if binary.has_key('sha_512'):
                    fname = binary['sha_512']
                    attachment = self.bin_GridFS.get_version(filename=fname)
                    if not binary.has_key('filename'):
                        binary['filename'] = "unknown_file"
                    #In order to display an image, it must be of the right MIME type, the right size, it must open in
                    #Python and be a valid image.
                    attachmentdesc = {'sha_512' : binary['sha_512'], 'filename' : binary['filename'], 'filesize' : attachment.length }
                    attachmentList.append(attachmentdesc)
                    if attachment.length < 512000:
                        if binary.has_key('content_type'):
                            if binary['content_type'].rsplit('/')[0].lower() == "image":
                                imagetype = imghdr.what('ignoreme',h=attachment.read())
                                acceptable_images = ['gif','jpeg','jpg','png','bmp']
                                if imagetype in acceptable_images:
                                    #If we pass -all- the tests, create a thumb once.
                                    if not self.bin_GridFS.exists(filename=binary['sha_512'] + "-thumb"):
                                        attachment.seek(0) 
                                        im = Image.open(attachment)
                                        img_width, img_height = im.size
                                        if ((img_width > 150) or (img_height > 150)): 
                                            im.thumbnail((150, 150), Image.ANTIALIAS)
                                        thumbnail = self.bin_GridFS.new_file(filename=binary['sha_512'] + "-thumb")
                                        im.save(thumbnail,format='png')    
                                        thumbnail.close()
                                    displayableAttachmentList.append(binary['sha_512'])
        if envelope['envelope']['payload'].has_key('body'):                            
            if envelope['envelope']['payload'].has_key('formatting'):
                    formattedbody = self.formatText(text=envelope['envelope']['payload']['body'],formatting=envelope['envelope']['payload']['formatting'])
            else:    
                    formattedbody = self.formatText(text=envelope['envelope']['payload']['body'])
            envelope['envelope']['local']['formattedbody'] = formattedbody
                
        envelope['envelope']['local']['displayableattachmentlist'] = displayableAttachmentList            
        #Create an attachment list that includes the calculated filesize, since we can't trust the one from the client.
        #But since the file is IN the payload, we can't modify that one, either!
        envelope['envelope']['local']['attachmentlist'] = attachmentList
        if envelope.has_key('_id'):            
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
                          "<a rel=\"nofollow\" href=\"" + c_url + "\">" + c_url + "</a>",
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
