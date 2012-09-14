#!/usr/bin/env python3
#
# Copyright 2012 Tavern
    

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.escape
import time
import datetime
import os
import socket
import json
from Envelope import Envelope
from collections import OrderedDict
import pymongo
from tornado.options import define, options
from server import server
import pygeoip
from keys import *
from User import User
from gridfs import GridFS
import hashlib
import urllib.request, urllib.parse, urllib.error
#import TopicList
from bs4 import BeautifulSoup
import rss
import pprint
import Image
import imghdr
import io
from TopicTool import TopicTool

import re
try: 
    from hashlib import md5 as md5_func
except ImportError:
    from md5 import new as md5_func

import cProfile



class BaseHandler(tornado.web.RequestHandler):
    
    """
    The BaseHandler is the baseclass for all objects in the webserver.
    It is not expected to ever be instantiated directly.
    It's main uses are:
        * Handle Cookies/logins
        * Allow modules to update just PARTS of the page
    """

    def __init__(self, *args, **kwargs):
        """
        Wrap the default RequestHandler with extra methods
        """    
        self.html = ""
        super(BaseHandler,self).__init__(*args,**kwargs)

        # Add in a random fortune
        self.set_header("X-Fortune", str(server.fortune.random()))
        # Do not allow the content to load in a frame.
        # Should help prevent certain attacks
        self.set_header("X-FRAME-OPTIONS", "DENY")
        # Don't try to guess content-type. 
        # This helps avoid JS sent in an image.
        self.set_header("X-Content-Type-Options","nosniff")
        
    def render_string(self, template_name, **kwargs):
        """
        Overwrite the default render_string to ensure the "server" variable is always available to templates
        """    
        args = dict(
             server=server,
             browser=self.browser
        )
        args.update(kwargs)
        return tornado.web.RequestHandler.render_string(self,template_name, **args) 


    def write(self,html):
        if hasattr(html, 'decode'):
            self.html += html.decode('utf-8')
        else:
             self.html += html
    def gettext(self):
        ptext = ""
        for a in self.pagetext:
            ptext = ptext + a
        self.write(ptext)
        

    def finish(self,divs=['limits'],message=None):
        if "js" in self.request.arguments:
            if "singlediv" in self.request.arguments:
                divs = [self.get_argument('singlediv')]
            #if JS is set at all, send the JS script version.

            # If we're a newbie, send the header, too; We probably don't have it yet.
            if 'time_privkey' in self.user.UserSettings:
                if int(time.time()) - self.user.UserSettings['time_privkey'] < 60:
                    divs.append('menu')

            for div in divs:
                super(BaseHandler, self).write(self.getjs(div))

        elif "getonly" in self.request.arguments:
            #Get ONLY the div content marked
            for div in divs:
                super(BaseHandler, self).write(self.getdiv(div))
        else:
            super(BaseHandler, self).write(self.html)
        super(BaseHandler,self).finish(message) 
   
    def getdiv(self,element):
        print("getting" + element)
        soup = BeautifulSoup(self.html)
        soupyelement = soup.find(id=element)
        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)
        print(soupytxt)
        return soupytxt
        
    def getjs(self,element):
        """ 
        Get the element text, remove all linebreaks, and escape it up.
        Then, send that as a document replacement
        Also, rewrite the document history in the browser, so the URL looks normal.
        """
        jsvar = self.request.uri.find("js=")
        if jsvar > -1:
            #This should always be true    
            #But Are there other params?
            nextvar = self.request.uri.find("&",jsvar)
            if nextvar > 0:
                #There are Additional Variables in this URL
                finish = "?" + self.request.uri[nextvar+1:len(self.request.uri)]
            else:
                #There are no other variables. Delete until End of string
                finish = ""
                
            modifiedurl = self.request.uri[0:self.request.uri.find("js=") -1] + finish

            #Also strip out the "timestamp" param
            jsvar = modifiedurl.find("timestamp=")
            if jsvar > -1:
                #This should always be true    
                #But Are there other params?
                nextvar = modifiedurl.find("&",jsvar)
                if nextvar > 0:
                    #There are Additional Variables in this URL
                    finish = "?" + modifiedurl[nextvar+1:len(modifiedurl)]
                else:
                    #There are no other variables. Delete until End of string
                    finish = ""
                modifiedurl = modifiedurl[0:modifiedurl.find("timestamp=") -1] + finish

        try:
            soup = BeautifulSoup(self.html)   
        except:
            print('malformed data: %r' % data)
            raise     
        soupyelement = soup.find(id=element)
        if soup.html is not None:
            newtitle = soup.html.head.title.string.rstrip().lstrip()
        else:
            print("Equals None?!")
            print(self.html)
            newtitle = soup.html.head.title.string.rstrip().lstrip()

        soupytxt = ""
        if soupyelement is not None:
            for child in soupyelement.contents:
                soupytxt += str(child)

        escapedtext = soupytxt.replace("\"","\\\"")
        escapedtext = escapedtext.replace("\n","")
        
        return ( '''var tavern_replace = function() 
                {
                    var stateObj = 
                    {
                        title: document.title,
                        url: window.location.pathname 
                    };
                    document.title = "''' + newtitle + ''' ";
                    if (typeof history.pushState !== "undefined")
                    {
                        window.history.pushState(stateObj, "","''' + modifiedurl + '''");
                    }
                    document.getElementById("''' + element + '''").innerHTML="''' + escapedtext + '''";
                    jQuery('#spinner').hide();
                };
                tavern_replace();
                tavern_replace = null;
                ''' + server.cache['instance.js'] 
                + 
                '''
                // Any other code here.
                '''
                )


    def chunks(self,s, n):
        """
        Produce `n`-character chunks from `s`.
        """
        for start in range(0, len(s), n):
            yield s[start:start+n]

    def setvars(self):
        """
        Saves out the current userobject to a cookie, or series of cookies.
        These are encrypted using the built-in Tornado cookie encryption.
        """
        # Zero out the stuff in 'local', since it's big.
        usersettings = self.user.UserSettings

        # Create the Cookie value, and sign it.
        signed = self.create_signed_value("tavern_preferences",json.dumps(usersettings,separators=(',',':')))

        # Chunk up the cookie value, so we can spread across multiple cookies.
        numchunks = 0
        for chunk in self.chunks(signed,3000):
            numchunks += 1
            self.set_cookie("tavern_preferences" + str(numchunks),chunk,httponly=True,expires_days=999)
        self.set_secure_cookie("tavern_preferences_count",str(numchunks),httponly=True,expires_days=999)
        server.logger.info("numchunks + " + str(numchunks))
        self.set_cookie('pubkey_sha1',self.user.UserSettings['pubkey_sha1'])

    def recentauth(self):
        """
        Ensure the user has authenticated recently.
        To be used for things like change-password.
        """
        currenttime = int(time.time())

        if currenttime  - self.user.UserSettings['lastauth'] > 300:
            server.logger.info("User has not logged in recently. ;( ")
            return False
        else:
            return True

    def getvars(self,ensurekeys=False):
        """
        Retrieve the basic user variables out of your cookies.
        """

        self.user = User()
        if self.get_secure_cookie("tavern_preferences_count") is not None:
            # Restore the signed cookie, across many chunks
            restoredcookie = ""
            for i in range(1,1 + int(self.get_secure_cookie("tavern_preferences_count"))):
                restoredcookie += self.get_cookie("tavern_preferences" + str(i))

            # Validate the cookie, and load if it passes
            decodedcookie = self.get_secure_cookie("tavern_preferences",value=restoredcookie)
            if not isinstance(decodedcookie, str):
                decodedcookie = decodedcookie.decode('utf-8')

            if decodedcookie is not None:
                self.user.load_string(decodedcookie)
            else:
                # We shouldn't get here.
                server.logger.info("Cookie doesn't validate. Deleting...")
                self.clear_cookie('tavern_preferences')
                self.clear_cookie('tavern_preferences1')
                self.clear_cookie('tavern_preferences2')
                self.clear_cookie('tavern_preferences3')
                self.clear_cookie('tavern_preferences_count')
                self.clear_cookie('tavern_passkey')
                self.clear_cookie('pubkey_sha1')

        # If there isn't already a cookie, make a very basic one.
        # Don't bother doing the keys, since that eats randomness.
        # Not an else, so we can be triggered by corrupt cookie above.
        if self.get_secure_cookie("tavern_preferences_count") is None:
            server.logger.info("Making cookies")
            self.user.generate(skipkeys=True)
            self.setvars()

        # If we've asked to make the keys.. Generate them.
        # This won't overwrite existing values, since user.generate() is additive.
        if ensurekeys == True:
            validkey = False
            if 'encryptedprivkey' in self.user.UserSettings:
                if self.user.UserSettings['encryptedprivkey'] is not None:
                    validkey = True
            if not validkey:
                server.logger.info("Making keys with a random password.")

                # Generate a random password with a random number of characters
                numcharacters = 100 + server.randrange(1,100)
                password = server.randstr(numcharacters)
                self.user.generate(skipkeys=False,password=password)

                # Save it out.
                self.setvars()
                self.user.savemongo()
                self.set_secure_cookie('tavern_passkey',self.user.Keys.passkey(password),httponly=True,expires_days=999) 
                self.user.passkey = self.user.Keys.passkey(password)

            if not hasattr(self.user,'passkey'):
                self.user.passkey = self.get_secure_cookie('tavern_passkey')
            if self.user.passkey == None:   
                self.user.passkey = self.get_secure_cookie('tavern_passkey')

        # Get the Browser version.
        if 'User-Agent' in self.request.headers:
            ua = self.request.headers['User-Agent']
            self.browser = server.browserdetector.parse(ua)


        # Check to see if we have support for datauris in our browser.
        # If we do, send the first ~10 pages with datauris.
        # After that switch back, since caching the images is likely to be better, if you're a recurrent reader
        if not 'datauri' in self.user.UserSettings:
            if server.randrange(1,10) == 5:
                self.user.UserSettings['datauri'] = False
        if 'datauri' in self.user.UserSettings:
            self.user.datauri = self.user.UserSettings['datauri']
        elif self.browser['ua_family'] == 'IE' and self.browser['ua_versions'][0] < 8:
            self.user.datauri = False
        elif self.browser['ua_family'] == 'IE' and self.browser['ua_versions'][0] >= 8:
            self.user.datauri = True
        else:
            self.user.datauri = True
        if 'datauri' in self.request.arguments:
            if self.get_argument("datauri").lower() == 'true':
                self.user.datauri = True
            elif self.get_argument("datauri").lower() == 'false':
                self.user.datauri = False


        return self.user.UserSettings['username']


class RSSHandler(BaseHandler):
    def get(self,action,param):
        if action =="topic":
            channel = rss.Channel('Tavern - ' + param,
                          'http://Tavern.com/rss/' + param,
                          'Tavern discussion about ' + param,
                          generator = 'Tavern',
                          pubdate = datetime.datetime.now())
            for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(param),'envelope.payload.class':'message'},limit=100,as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
                item = rss.Item(channel,
                    envelope['envelope']['payload']['subject'],
                    "http://Tavern.com/message/" + envelope['envelope']['local']['sorttopic'] + '/' + envelope['envelope']['local']['short_subject'] + "/" + envelope['envelope']['payload_sha512'],
                    envelope['envelope']['local']['formattedbody'])
                channel.additem(item)
            self.write(channel.toprettyxml())
                      
                          

class TriPaneHandler(BaseHandler):
    
    """ 
    The TriPane Handler is the beefiest handler in the project.
    It renders the main tri-panel interface, and only pushes out the parts that are needed.
    """            
    
    def get(self,param1=None,param2=None,param3=None):
        self.getvars()
               
        # We want to assign the parameters differently, depending on how many there are.
        # Normally, we'd just say get(action=None,param=None,bullshit=None)
        # But in this scenerio, we want the second param to be the text, if there are three, and have the ID as #3
        # But if there are only two, the second param should be the ID.

        # Count up our number of parameters.
        if param3 == None:
            if param2 == None:
                if param1 == None:
                    numparams = 0
                else:
                    numparams = 1
            else:
                numparams = 2
                param2 = tornado.escape.xhtml_escape(urllib.parse.unquote(param2))
        else:
            numparams = 3
            param3 = tornado.escape.xhtml_escape(urllib.parse.unquote(param3))


        #Decide what to do, based on the number of incoming actions.    
        if numparams < 2:
            # Defaults all around
            action = "topic"
            topic = "sitecontent"
        else:
            action = param1
            if action == "t" or action == "topic" or action == "topictag":
                action = "topic"
            elif action == "m" or action == "message":
                action = "message"
            else:
                action = "message"
            if action == "message":       
                if numparams == 2:
                    messageid = param2
                if numparams == 3:
                    messageid = param3
            elif action == "topic":
                topic = param2

        if "before" in self.request.arguments:
            # Used for multiple pages, because skip() is slow
            before = float(self.get_argument('before'))
        else:
            before = None

        if action == "topic":
            divs = ['left','center','right']
    
            if topic != 'sitecontent':
                canon="topic/" + topic 
                title=topic
            else:
                canon=""
                title="An anonymous, shared discussion"
            displayenvelope = TopicTool(topic).messages(server.inttime())[0]

        if action == "message":

            # We need both center and right, since the currently active message changes in the center.
            divs = ['center','right']

            displayenvelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : messageid },as_class=OrderedDict)
            if displayenvelope is not None:
                topic = displayenvelope['envelope']['payload']['topic']
                canon="message/" + displayenvelope['envelope']['local']['sorttopic'] + '/' + displayenvelope['envelope']['local']['short_subject'] + "/" + displayenvelope['envelope']['payload_sha512']
                title = displayenvelope['envelope']['payload']['subject']
            
        if displayenvelope is None:
            # Can't find a message ;(
            e = server.error_envelope("Can't find your message")
            displayenvelope = e.dict
            messageid = e.payload.hash()
            title = "Can't find your message"
            topic = "sitecontent"
            # Set the canon URL to be whatever we just got, since obviously we just got it.
            canon=self.request.path[1:]


        displayenvelope = server.formatEnvelope(displayenvelope)
        # Detect people accessing via odd URLs, but don't do it twice.
        # Check for a redirected flag.

        if 'redirected' in self.request.arguments:
            redirected = tornado.escape.xhtml_escape(self.get_argument("redirected"))
            if redirected == 'true':
                redirected = True
            else:
                redirected = False
        else:
            redirected = None

        if self.request.path[1:] != canon and redirected is None:
            if not "?" in canon:
                canonbubble = "?redirected=true"
            else:
                canonbubble = "&redirected=true"  
            server.logger.info("Redirecting URL " + self.request.path[1:] + " to " + canon )
     #       self.redirect("/" + canon + canonbubble, permanent=True)
     #       self.finish()

        #Gather up all the replies to this message, so we can send those to the template as well
        self.write(self.render_string('header.html',title=title,user=self.user,canon=canon,type="topic",rsshead=displayenvelope['envelope']['payload']['topic']))
        self.write(self.render_string('tripane.html',user=self.user,envelope=displayenvelope,before=before,topic=topic))
        self.write(self.render_string('footer.html'))  
           
        if action == "message" or action == "topic":
            self.finish(divs=divs)
        else:
            self.finish()
      
class TopicPropertiesHandler(BaseHandler):
    def get(self,topic):
        self.getvars()

        client_topic = tornado.escape.xhtml_escape(topic)

        mods = []
        for mod in server.mongos['default']['modlist'].find({'_id.topic':server.sorttopic(topic)},as_class=OrderedDict,max_scan=10000).sort('value.trust',direction=pymongo.DESCENDING):
            mod['_id']['moderator_pubkey_sha512'] = hashlib.sha512(mod['_id']['moderator'].encode('utf-8')).hexdigest() 
            mods.append(mod)

        toptopics = []
        for quicktopic in server.mongos['default']['topiclist'].find(limit=10,as_class=OrderedDict).sort('value',-1):
            toptopics.append(quicktopic)
        subjects = []
        for envelope in server.mongos['default']['envelopes'].find({'envelope.local.sorttopic' : server.sorttopic(topic),'envelope.payload.class':'message','envelope.payload.regarding':{'$exists':False}},limit=self.user.UserSettings['maxposts'],as_class=OrderedDict):
            subjects.append(envelope)

        title = "Properties for " + topic    
        self.write(self.render_string('header.html',title=title,user=self.user,rsshead=topic,type="topic"))
        self.write(self.render_string('topicprefs.html',user=self.user,topic=topic,toptopics=toptopics,subjects=subjects,mods=mods))
        self.write(self.render_string('footer.html'))  
        self.finish(divs=['right'])

class SiteContentHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)
        
        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)
        envelope = server.formatEnvelope(envelope)

            
        self.write(self.render_string('header.html',title="Tavern :: " + envelope['envelope']['payload']['subject'],user=self.user,canon="sitecontent/" + envelope['envelope']['payload_sha512'],rss="/rss/topic/" + envelope['envelope']['payload']['topic'],topic=envelope['envelope']['payload']['topic']))
        self.write(self.render_string('sitecontent.html',formattedbody=envelope['envelope']['local']['formattedbody'],envelope=envelope))
        self.write(self.render_string('footer.html'))
 
class AttachmentHandler(BaseHandler):
    def get(self,attachment):
        self.getvars()
        client_attachment_id = tornado.escape.xhtml_escape(attachment)
        envelopes = server.mongos['default']['envelopes'].find({'envelope.payload.binaries.sha_512' : client_attachment_id},as_class=OrderedDict)
        stack = []
        for envelope in envelopes:
            stack.append(envelope)

        self.write(self.render_string('header.html',title="Tavern Attachment " + client_attachment_id,user=self.user,rsshead=client_attachment_id,type="attachment"))
        self.write(self.render_string('attachments.html',attachment=client_attachment_id,stack=stack))
        self.write(self.render_string('footer.html'))

class PrivateMessageHandler(BaseHandler):        
    def get(self,message):
        self.getvars()
        client_message_id = tornado.escape.xhtml_escape(message)

        envelope = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512' : client_message_id },as_class=OrderedDict)

        usertrust = self.user.gatherTrust(envelope['envelope']['payload']['author']['pubkey'])
        
        envelope['envelope']['payload']['body'] = self.user.Keys.decryptToSelf(envelope['envelope']['payload']['body'])
        envelope['envelope']['payload']['subject'] = self.user.Keys.decryptToSelf(envelope['envelope']['payload']['subject'])

        if 'formatting' in envelope['envelope']['payload']:
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'],formatting=envelope['envelope']['payload']['formatting'])
        else:    
                formattedbody = server.formatText(text=envelope['envelope']['payload']['body'])

        self.write(self.render_string('header.html',title="Tavern :: " + envelope['envelope']['payload']['subject'],user=self.user,type="privatemessage",rsshead=None))
        self.write(self.render_string('singleprivatemessage.html',formattedbody=formattedbody,usertrust=usertrust,envelope=envelope))
        self.write(self.render_string('footer.html'))




class RegisterHandler(BaseHandler):
    def get(self):
        self.getvars()
        self.write(self.render_string('header.html',title="Register for an Account",user=self.user,type=None,rsshead=None))
        self.write(self.render_string('registerform.html'))
        self.write(self.render_string('footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',title='Register for an account',user=self.user,type=None,rsshead=None))

        client_newuser =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_newpass =  tornado.escape.xhtml_escape(self.get_argument("pass"))
        client_newpass2 = tornado.escape.xhtml_escape(self.get_argument("pass2"))
        if "email" in self.request.arguments:
            client_email = tornado.escape.xhtml_escape(self.get_argument("email"))
            if client_email == "":
                client_email = None
        else:
            client_email = None     
            
        if client_newpass != client_newpass2:
            self.write("I'm sorry, your passwords don't match.") 
            return

        if client_email is not None:
            users_with_this_email = server.mongos['default']['users'].find({"email":client_email.lower()},as_class=OrderedDict)
            if users_with_this_email.count() > 0:
                self.write("I'm sorry, this email address has already been used.")  
                return
            
        users_with_this_username = server.mongos['default']['users'].find({"username":client_newuser.lower()},as_class=OrderedDict)
        if users_with_this_username.count() > 0:
            self.write("I'm sorry, this username has already been taken.")  
            return    
            
        else:
            # Generate the user
            self.user.generate(username=client_newuser.lower(),password=client_newpass)

            if client_email is not None:
                self.user.UserSettings['email'] = client_email.lower()

            self.user.savemongo()

            # Save the passkey out to a separate cookie.
            self.set_secure_cookie("tavern_passkey",self.user.Keys.passkey(client_newpass),httponly=True,expires_days=999) 

            self.setvars()
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        self.getvars()  
        self.write(self.render_string('header.html',title="Login to your account",user=self.user,rsshead=None,type=None))
        self.write(self.render_string('loginform.html'))
        self.write(self.render_string('footer.html'))
    def post(self):
        self.getvars()
        self.write(self.render_string('header.html',title='Login to your account',user=self.user,rsshead=None,type=None))

        client_username =  tornado.escape.xhtml_escape(self.get_argument("username"))
        client_password =  tornado.escape.xhtml_escape(self.get_argument("pass"))

        login = False
        user = server.mongos['default']['users'].find_one({"username":client_username.lower()},as_class=OrderedDict)
        if user is not None:
            u = User()
            u.load_mongo_by_username(username=client_username.lower())
            
            # Allow four forms of password
            # Normal password
            # swapped case (caps lock)
            # First letter as upper if you initially signed up on mobile
            # First form lower, as if you're on mobile now.
            
            if u.verify_password(client_password):
                login = True
            elif u.verify_password(client_password.swapcase()):
                    login = True
            elif u.verify_password(client_password[:1].upper() + client_password[1:]):
                    login = True
            elif u.verify_password(client_password[:1].lower() + client_password[1:]):
                    login = True
            if login == True:
                self.user = u
                server.logger.info("Passkey - " + self.user.Keys.passkey(client_password))
                self.set_secure_cookie("tavern_passkey",self.user.Keys.passkey(client_password),httponly=True,expires_days=999) 

                self.user.UserSettings['lastauth'] = int(time.time())

                self.setvars()
                server.logger.info("Login Successful.")
                self.redirect('/')
            else:
                server.logger.info("Username/password fail.")
                self.redirect("http://Google.com")

class LogoutHandler(BaseHandler):
     def post(self):
         self.clear_all_cookies()
         self.redirect("/")

class UserHandler(BaseHandler):
    def get(self,pubkey):
        self.getvars()
        
        #Unquote it, then convert it to a TavernKey object so we can rebuild it.
        #Quoting destroys the newlines.
        pubkey = urllib.parse.unquote(pubkey)
        pubkey = Keys(pub=pubkey).pubkey

        u = User()
        u.UserSettings['pubkey']=pubkey
        u.generate(self,skipkeys=True)
        u.UserSettings['author_pubkey_sha1'] = hashlib.sha1(pubkey.encode('utf-8')).hexdigest() 

        envelopes = []
        for envelope in server.mongos['default']['envelopes'].find({'envelope.payload.author.pubkey':pubkey,'envelope.payload.class':'message'},as_class=OrderedDict).sort('envelope.local.time_added',pymongo.DESCENDING):
            envelopes.append(envelope)

        self.write(self.render_string('header.html',title="User page",user=self.user,rsshead=None,type=None))

        if pubkey == self.user.Keys.pubkey:
            if not 'author_pubkey_sha1' in self.user.UserSettings:
                self.user.UserSettings['author_pubkey_sha1'] = u.UserSettings['author_pubkey_sha1']
            self.write(self.render_string('mysettings.html',user=self.user))

        self.write(self.render_string('userpage.html',me=self.user,thatguy=u,envelopes=envelopes))
        
        self.write(self.render_string('showuserposts.html',envelopes=envelopes,thatguy=u))

        self.write(self.render_string('footer.html'))


class ChangeManySettingsHandler(BaseHandler):    
    def post(self):    
        self.getvars(ensurekeys=True)

        friendlyname = tornado.escape.xhtml_escape(self.get_argument('friendlyname'))
        maxposts = int(self.get_argument('maxposts'))
        maxreplies = int(self.get_argument('maxreplies'))
        if 'include_location' in self.request.arguments:
            include_location = True
        else:
            include_location = False
        if 'allowembed' in self.request.arguments:
            allowembed = 1
        else:
            allowembed = -1
                     
        self.user.UserSettings['friendlyname'] = friendlyname
        self.user.UserSettings['maxposts'] = maxposts
        self.user.UserSettings['maxreplies'] = maxreplies
        self.user.UserSettings['include_location'] = include_location
        self.user.UserSettings['allowembed'] = allowembed
        self.user.savemongo()
        self.setvars()

        server.logger.info("set")
        if "js" in self.request.arguments:
            self.finish(divs=['left'])
        else:
            keyurl = ''.join(self.user.Keys.pubkey.split())
            self.redirect('/user/' + keyurl)
                        
                 
class ChangeSingleSettingHandler(BaseHandler):

    def post(self,setting,option=None):    
        self.getvars(ensurekeys=True)
        redirect = True
        if setting == "followtopic":
            self.user.followTopic(tornado.escape.xhtml_escape(self.get_argument("topic")))
        elif setting == "unfollowtopic":
            self.user.unFollowTopic(tornado.escape.xhtml_escape(self.get_argument("topic")))
        elif setting == "showembeds":
            self.user.UserSettings['allowembed'] = 1
            server.logger.info("allowing embeds")
            if option == 'ajax':
                self.write('Tavern will now display all external media.')
                redirect = False
        elif setting == "dontshowembeds":
            self.user.UserSettings['allowembed'] = -1
            server.logger.info("forbidding embeds")
        else:
            server.logger.info("Warning, you didn't do anything!")      

        self.user.savemongo()
        self.setvars()
        if "js" in self.request.arguments:
            self.finish(divs=['left'])
        else:
            if redirect == True:
                self.redirect("/")
        

class RatingHandler(BaseHandler):
    def get(self,posthash):
        self.getvars()
        #Calculate the votes for that post. 
         
    def post(self):    
        self.getvars(ensurekeys=True)

        #So you may be asking yourself.. Self, why did we do this as a POST, rather than
        #Just a GET value, of the form server.com/msg123/voteup
        #The answer is xsrf protection.
        #We don't want people to link to the upvote button and trick you into voting up.

        
        client_hash =  tornado.escape.xhtml_escape(self.get_argument("hash"))        
        client_rating =  tornado.escape.xhtml_escape(self.get_argument("rating"))
        rating_val = int(client_rating)
        if rating_val not in [-1,0,1]:
            self.write("Invalid Rating.")
            return -1
        
        e = Envelope()
        e.payload.dict['class'] = "rating"
        e.payload.dict['rating'] = rating_val
        e.payload.dict['regarding'] = client_hash
            
        #Instantiate the user who's currently logged in
        
        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        #Send to the server
        server.receiveEnvelope(e.text())
        
        self.write("Your vote has been recorded. Thanks!")


class UserNoteHandler(BaseHandler):
    def get(self,user):
        self.getvars()
        #Show the Note for a user

    def post(self):    
        self.getvars(ensurekeys=True)

        client_pubkey = self.get_argument("pubkey")    
        client_note = self.get_argument("note")
        self.user.setNote(client_pubkey,client_note)
        server.logger.info("Note Submitted.")




class UserTrustHandler(BaseHandler):
    def get(self,user):
        self.getvars()
        #Calculate the trust for a user. 

    def post(self):    
        self.getvars(ensurekeys=True)

        trusted_pubkey = urllib.parse.unquote(self.get_argument("trusted_pubkey"))
        trusted_pubkey = Keys(pub=trusted_pubkey).pubkey 


        client_trust =  self.get_argument("trust")
        client_topic =  self.get_argument("topic")


        trust_val = int(client_trust)
        if trust_val not in [-100,0,100]:
            self.write("Invalid Trust Score.")
            return -1
        

        e = Envelope()
        e.payload.dict['class'] = "usertrust"
        e.payload.dict['trust'] = trust_val
        e.payload.dict['topic'] = client_topic   
        e.payload.dict['trusted_pubkey'] = trusted_pubkey

        #Instantiate the user who's currently logged in


        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release"


        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        
        #Send to the server
        server.receiveEnvelope(e.text())
        server.logger.info("Trust Submitted.")

        # Remove cached version of this trust.
        server.mongos['cache']['usertrusts'].remove({"asking":self.user.Keys.pubkey,"askingabout":trusted_pubkey})



class NewmessageHandler(BaseHandler):

    def options(self,regarding=None):
        self.set_header('Access-Control-Allow-Methods', 'OPTIONS, HEAD, GET, POST, PUT, DELETE')
        self.set_header('Access-Control-Allow-Origin','*')

    def get(self,topic=None,regarding=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Post a new message",user=self.user,rsshead=None,type=None))
         self.write(self.render_string('newmessageform.html',regarding=regarding,topic=topic,args=self.request.arguments,user=self.user))
         self.write(self.render_string('footer.html'))
         self.finish(divs=['right','single'])

    def post(self,flag=None):
        self.getvars(ensurekeys=True)
        filelist = []

        # We might be getting files either through nginx, or through directly.
        # If we get the file through Nginx, parse out the arguments.
        for argument in self.request.arguments:
            if argument.startswith("attached_file") and argument.endswith('.path'):
                individual_file = {}
                individual_file['basename'] = argument.rsplit('.')[0]
                individual_file['clean_up_file_afterward'] = True
                individual_file['filename'] = tornado.escape.xhtml_escape(self.get_argument(individual_file['basename'] + ".name"))
                individual_file['content_type'] =  tornado.escape.xhtml_escape(self.get_argument(individual_file['basename'] + ".content_type"))
                individual_file['path'] =  tornado.escape.xhtml_escape(self.get_argument(individual_file['basename'] + ".path"))
                individual_file['size'] =  tornado.escape.xhtml_escape(self.get_argument(individual_file['basename'] + ".size"))

                fs_basename = os.path.basename(individual_file['path'])
                individual_file['fullpath'] = server.ServerSettings['upload-dir'] + "/" + fs_basename

                individual_file['filehandle'] = open(individual_file['path'], 'rb+')
                hashname = str(individual_file['basename'] + '.sha512')

                # If we have the nginx_upload new enough to give us the SHA512 hash, use it.
                # If not, calc. it.
                if hashname in self.request.arguments:
                    individual_file['hash'] = tornado.escape.xhtml_escape(self.get_argument(individual_file['basename'] + ".sha512"))
                else:
                    while True:
                        buf = individual_file['filehandle'].read(0x100000)
                        if not buf:
                            break
                        SHA512.update(buf)
                    individual_file['hash'] = SHA512.hexdigest()
                individual_file['filehandle'].seek(0)
                filelist.append(individual_file)

        # If we get files directly, calculate what we need to know.
        for file_field in self.request.files:
            for individual_file in self.request.files[file_field]:
                #     You get these keys from Tornado
                #       body
                #       content_type
                #       filename

                individual_file['clean_up_file_afterward'] = False
                individual_file['filehandle'] = io.BytesIO()
                individual_file['filehandle'].write(individual_file['body'])
                individual_file['size'] =  len(individual_file['body'])
                SHA512 = hashlib.sha512()
                while True:
                    buf = individual_file['filehandle'].read(0x100000)
                    if not buf:
                        break
                    SHA512.update(buf)
                individual_file['filehandle'].seek(0)
                digest = SHA512.hexdigest()
                SHA512.update(individual_file['body'])
                individual_file['hash'] = SHA512.hexdigest()
                individual_file['filehandle'].seek(0)
                filelist.append(individual_file)

        print("foo")
        client_filepath = None     
        envelopebinarylist = []

        # Attach the files that are actually here, submitted alongside the message.
        for attached_file in filelist:
            #All the same, let's strip out all but the basename.           
            server.logger.info("Dealing with File " + attached_file['filename'] + " with hash " +  attached_file['hash'])
            if not server.bin_GridFS.exists(filename=attached_file['hash']):
                attached_file['filehandle'].seek(0)
                imagetype = imghdr.what('ignoreme',h=attached_file['filehandle'].read())
                acceptable_images = ['gif','jpeg','jpg','png','bmp']
                print(imagetype)
                if imagetype in acceptable_images:
                    attached_file['filehandle'].seek(0)
                    # If it's an image, open and re-save to strip EXIF data.
                    # Do so here, rather than in server, so that server->server messages aren't touched
                    Image.open(attached_file['filehandle']).save(attached_file['filehandle'],format=imagetype)
                attached_file['filehandle'].seek(0)
                oid = server.bin_GridFS.put(attached_file['filehandle'],filename=attached_file['hash'], content_type=individual_file['content_type'])
            server.logger.info("Creating Message")
            #Create a message binary.    
            bin = Envelope.binary(hash=attached_file['hash'])
            #Set the Filesize. Clients can't trust it, but oh-well.
            print('estimated size : ' + str(attached_file['size']  ))
            bin.dict['filesize_hint'] =  attached_file['size']
            bin.dict['content_type'] = attached_file['content_type']
            bin.dict['filename'] = attached_file['filename']
            envelopebinarylist.append(bin.dict)

            #Don't keep spare copies on the webservers
            attached_file['filehandle'].close()
            if attached_file['clean_up_file_afterward'] is True:
                os.remove(attached_file['fullpath'])

        # Support the Javascript upload handler.
        # return the JSON formatted reply it's looking for
        if flag == "fileonly":
            details = []
            for attached_file in filelist:
                detail = {}
                detail['name'] = attached_file['filename']
                detail['hash'] = attached_file['hash']
                detail['size'] = attached_file['size']
                detail['content_type'] = attached_file['content_type']

                detail['url'] = server.ServerSettings['downloadsurl'] + attached_file['hash'] 
                details.append(detail)
            details_json = json.dumps(details,separators=(',',':'))
            self.set_header("Content-Type","application/json")
            self.write(details_json)
            return

        # Add the binaries which are referenced only
        # The jQuery uploader will upload them seperately, so this isn't unusual.
        for argument in self.request.arguments:
            print(argument)
            if argument.startswith("referenced_file1") and argument.endswith('_name'):
                r = re.compile('referenced_file(.*?)_name')
                m = r.search(argument)
                binarycount = m.group(1)
                bin = Envelope.binary(hash= tornado.escape.xhtml_escape(self.get_argument('referenced_file' + binarycount + '_hash')))
                bin.dict['filesize_hint'] = tornado.escape.xhtml_escape(self.get_argument('referenced_file' + binarycount + '_size'))
                bin.dict['content_type'] = tornado.escape.xhtml_escape(self.get_argument('referenced_file' + binarycount + '_contenttype'))
                bin.dict['filename'] = tornado.escape.xhtml_escape(self.get_argument('referenced_file' + binarycount + '_name'))
                envelopebinarylist.append(bin.dict)

        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        # Pull in our Form variables. 
        # The reason for the uncertainty is the from can be used two ways; One for replies, one for new messages.
        # It acts differently in the two scenerios.
        if "topic" in self.request.arguments:
            client_topic = tornado.escape.xhtml_escape(self.get_argument("topic"))
            if client_topic == "":
                client_topic = None
        else:
            client_topic = None
        if "subject" in self.request.arguments:
            client_subject = tornado.escape.xhtml_escape(self.get_argument("subject"))
            if client_subject == "":
                client_subject = None  
        else:
            client_subject = None
        if "regarding" in self.request.arguments:
            client_regarding = tornado.escape.xhtml_escape(self.get_argument("regarding"))
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None
     




        e = Envelope()

        if client_regarding is not None:
            server.logger.info("Adding Regarding - " + client_regarding)
            e.payload.dict['regarding'] = client_regarding

            regardingmsg = server.mongos['default']['envelopes'].find_one({'envelope.payload_sha512':client_regarding},as_class=OrderedDict)
            e.payload.dict['topic'] = regardingmsg['envelope']['payload']['topic']
            e.payload.dict['subject'] = regardingmsg['envelope']['payload']['subject']
        else:
            e.payload.dict['topic'] = client_topic
            e.payload.dict['subject'] = client_subject

        e.payload.dict['formatting'] = "markdown"
        e.payload.dict['class'] = "message"
        e.payload.dict['body'] = client_body
       
        if len(envelopebinarylist) > 0:
            e.payload.dict['binaries'] = envelopebinarylist

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or 'include_location' in self.request.arguments:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip
            
            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"
                
            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])
        
        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist
        
        #Send to the server
        newmsgid = server.receiveEnvelope(e.text())
        if newmsgid != False:
            if client_regarding is not None:
                self.redirect('/message/' + server.find_top_parent(newmsgid) + "?jumpto=" + newmsgid, permanent=False)                
            else:
                self.redirect('/message/' + newmsgid, permanent=False)
        else:
            self.write("Failure to insert message.")

class MyPrivateMessagesHandler(BaseHandler):
    def get(self):
        self.getvars()

            
        messages = []
        self.user.load_mongo_by_username(self.user['username'])
        
        self.write(self.render_string('header.html',title="Welcome to the Tavern!",user=self.user,rsshead=None,type=None))
        for message in server.mongos['default']['envelopes'].find({'envelope.payload.to':self.user.Keys.pubkey},fields={'envelope.payload_sha512','envelope.payload.subject'},limit=10,as_class=OrderedDict).sort('value',-1):
            message['envelope']['payload']['subject'] = self.user.Keys.decryptToSelf(message['envelope']['payload']['subject'])
            messages.append(message)

        self.write(self.render_string('showprivatemessages.html',messages=messages))
        self.write(self.render_string('footer.html'))


class NewPrivateMessageHandler(BaseHandler):
    def get(self,urlto=None):
         self.getvars()
         self.write(self.render_string('header.html',title="Login to your account",user=self.user,rsshead=None,type=none))
         self.write(self.render_string('privatemessageform.html',urlto=urlto))
         self.write(self.render_string('footer.html'))

    def post(self,urlto=None):
        self.getvars(ensurekeys=True)


        client_to =  tornado.escape.xhtml_escape(self.get_argument("to"))
        if urlto is not None:
            client_to = tornado.escape.xhtml_escape(urlto)
            
        client_subject =  tornado.escape.xhtml_escape(self.get_argument("subject"))
        client_body =  tornado.escape.xhtml_escape(self.get_argument("body"))
        if "regarding" in self.request.arguments:
            client_regarding = tornado.escape.xhtml_escape(self.get_argument("regarding"))
            if client_regarding == "":
                client_regarding = None
        else:
            client_regarding = None

        #Instantiate the key of the user who we're sending to
        toKey = Keys(pub=client_to)
        toKey.format_keys()


        e = Envelope()
        e.payload.dict['class'] = "privatemessage"

        e.payload.dict['to'] = toKey.pubkey
        e.payload.dict['body'] = toKey.encryptToSelf(client_body)
        e.payload.dict['subject'] = toKey.encryptToSelf(client_subject)
        if client_regarding is not None:
            server.logger.info("Adding Regarding - " + client_regarding)
            e.payload.dict['regarding'] = client_regarding

        e.payload.dict['author'] = OrderedDict()
        e.payload.dict['author']['pubkey'] = self.user.Keys.pubkey
        e.payload.dict['author']['friendlyname'] = self.user.UserSettings['friendlyname']
        e.payload.dict['author']['useragent'] = "Tavern Web frontend Pre-release 0.1"
        if self.user.UserSettings['include_location'] == True or self.get_argument("include_location") == True:
            gi = pygeoip.GeoIP('/usr/local/share/GeoIP/GeoIPCity.dat')
            ip = self.request.remote_ip

            #Don't check from home.
            if ip == "127.0.0.1":
                ip = "8.8.8.8"

            gir = gi.record_by_name(ip)
            e.payload.dict['coords'] = str(gir['latitude']) + "," + str(gir['longitude'])

        #Sign this bad boy
        usersig = self.user.Keys.signstring(e.payload.text(),self.user.passkey)
        stamp = OrderedDict()
        stamp['class'] = 'author'
        stamp['pubkey'] = self.user.Keys.pubkey
        stamp['signature'] = usersig
        utctime = time.time()
        stamp['time_added'] = int(utctime)
        stamplist = []
        stamplist.append(stamp)
        e.dict['envelope']['stamps'] = stamplist

        #Send to the server
        server.receiveEnvelope(e.text())
    
class NullHandler(BaseHandler):
        # This is grabbed by nginx, and never called in prod.
    def get(self,url=None):
        return 
    def post(self,url=None):
        return

class BinariesHandler(tornado.web.RequestHandler):
    """
    Serves images/etc out of nginx.
    Really shouldn't be used in prod.
    Use the nginx handler instead
    """
    def get(self,hash,filename=None):
        server.logger.info("The gridfs_nginx plugin is a much better option than this method")
        self.set_header("Content-Type",'application/octet-stream')

        req = server.bin_GridFS.get_last_version(filename=hash)
        self.write(req.read())

class AvatarHandler(BaseHandler):
    """
    For users who aren't using nginx (like in dev), this will pull in the avatars
    """
    def get(self,avatar):
        server.logger.info("Bouncing to offsite avatar. Install the NGINX package to avoid this! ")
        self.redirect('https://robohash.org/' + avatar + "?" + "set="  + self.get_argument('set') + "&bgset=" + self.get_argument('bgset') + "&size=" + self.get_argument('size') )
        
def main():

    tornado.options.parse_command_line()
    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)
    server.logger.info("Starting Web Frontend for " + server.ServerSettings['hostname'])
    

    # Generate a default user, to use when no one is logged in.
    # This can't be done in the Server module, because it requires User, which requires Server, which can't then require User....
    if not 'guestacct' in server.ServerSettings:
        serveruser = User()
        serveruser.generate(skipkeys=False,password=server.ServerSettings['serverkey-password'])
        server.ServerSettings['guestacct'] = serveruser.UserSettings
        server.saveconfig()


    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "cookie_secret": server.ServerSettings['cookie-encryption'],
        "login_url": "/login",
        "xsrf_cookies": True,
        "template_path" : "templates",
        "autoescape" : "xhtml_escape"
    }
    application = tornado.web.Application([
        (r"/" ,TriPaneHandler),
        (r"/register" ,RegisterHandler),
        (r"/login" ,LoginHandler),
        (r"/showuserposts/(.*)" ,UserHandler),  
        (r"/user/(.*)" ,UserHandler),  
        (r"/logout" ,LogoutHandler),  
        (r"/rss/(.*)/(.*)" ,RSSHandler),
        (r"/newmessage" ,NewmessageHandler),
        (r"/uploadfile/(.*)" ,NewmessageHandler),
        (r"/reply/(.*)/(.*)" ,NewmessageHandler),
        (r"/reply/(.*)" ,NewmessageHandler),
        (r"/uploadnewmessage" ,NewmessageHandler), 
        (r"/vote" ,RatingHandler),
        (r"/usertrust",UserTrustHandler),  
        (r"/usernote",UserNoteHandler),  
        (r"/attachment/(.*)" ,AttachmentHandler), 
        (r"/topicinfo/(.*)",TopicPropertiesHandler),  
        (r"/changesetting/(.*)/(.*)" ,ChangeSingleSettingHandler),
        (r"/changesetting/(.*)" ,ChangeSingleSettingHandler),
        (r"/changesettings" ,ChangeManySettingsHandler),  
        (r"/showprivates" ,MyPrivateMessagesHandler), 
        (r"/uploadprivatemessage/(.*)" ,NewPrivateMessageHandler),
        (r"/uploadprivatemessage" ,NewPrivateMessageHandler),  
        (r"/privatemessage/(.*)" ,PrivateMessageHandler), 
        (r"/sitecontent/(.*)" ,SiteContentHandler),  
        (r"/avatar/(.*)" ,AvatarHandler),           
        (r"/binaries/(.*)/(.*)" ,BinariesHandler),             
        (r"/binaries/(.*)" ,BinariesHandler), 
        (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(os.path.dirname(__file__),"static/")}),
        (r"/(.*)/(.*)/(.*)" ,TriPaneHandler), 
        (r"/(.*)/(.*)" ,TriPaneHandler),
        (r"/(.*)" ,TriPaneHandler),           
    ], **settings)
    
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()
    server.logger.info(server.ServerSettings['hostname'] +' is ready for requests.')



if __name__ == "__main__":
    main()
